"""Importer les employes d'une structure cliente depuis un export de paie.

    python3 importer_employes.py <fichier.csv>            # montre ce qui serait fait
    python3 importer_employes.py <fichier.csv> --ecrire   # le fait

CE QU'IL FAIT. Chaque salarie devient un contact DFM, portant le marqueur de
son employeur — c'est ce marqueur qui permettra de lui proposer une formation
et de retrouver, plus tard, qui a ete forme pour quel centre.

CE QU'IL N'IMPORTE PAS. Un export de paie contient des salaires, des matricules
et des dates d'entree. Rien de tout cela n'entre dans DFM : une base de
contacts de formation n'a aucune raison de detenir la remuneration de qui que
ce soit, et le RGPD demande de s'en tenir a ce qui sert.

IL NE FUSIONNE JAMAIS SUR UNE PRESOMPTION. Le rapprochement passe par
contacts.rapprocher(), qui compare l'adresse puis le telephone — jamais le nom
seul. Un salarie deja connu est complete, pas duplique.
"""
import csv
import os
import sys

import contacts as C

# --------------------------------------------------------------------------
# Ce qui n'entre pas dans la base
# --------------------------------------------------------------------------
# L'entretien et le menage ne suivent pas les formations dentaires : les faire
# entrer gonflerait la base de gens qu'on ne solliciterait jamais, et chaque
# envoi groupe leur parviendrait pour rien. Regle posee par Franck le
# 06/08/2026, sur categorie ET sur intitule de poste, parce que deux fiches de
# paie portent un intitule d'entretien sans categorie renseignee.
CATEGORIES_ECARTEES = {"technicien_entretien"}
EMPLOIS_ECARTES = ("agent d'entretien", "agent de menage", "agent de ménage",
                   "technicien d'entretien")

# Salaries a ne pas importer, nommement. Sert aux cas particuliers qu'aucune
# regle ne couvre — ici une collision avec une fiche de test en service.
NOMMEMENT_ECARTES = {("MOYAL", "Franck")}


def fonction_de(ligne):
    """La fonction DFM d'un salarie.

    Deux categories de paie se traduisent directement en metier : le reste se
    classe sur le STATUT, cadre ou non-cadre, qui est l'autre grille utile —
    et la seule disponible pour un comptable ou une secretaire medicale.
    """
    categorie = (ligne.get("categorie_poste_rh") or "").strip().lower()
    if categorie == "chirurgien_dentiste":
        return "Chirurgien-dentiste"
    if categorie == "assistant_dentaire":
        return "Assistant-e dentaire"
    cadre = (ligne.get("statut_cadre") or "").strip().lower()
    return "Employé cadre" if cadre.startswith("cadre") else "Employé non-cadre"


def _ecartee(ligne):
    """Rend le motif d'ecart, ou "" si la ligne est a importer."""
    nom = (ligne.get("nom") or "").strip()
    prenom = (ligne.get("prenom") or "").strip()
    if (nom, prenom) in NOMMEMENT_ECARTES:
        return "écarté nommément"
    if (ligne.get("categorie_poste_rh") or "").strip().lower() in CATEGORIES_ECARTEES:
        return "entretien"
    emploi = (ligne.get("emploi_silae") or "").strip().lower()
    if any(e in emploi for e in EMPLOIS_ECARTES):
        return "entretien (d'après l'intitulé de poste)"
    if not (ligne.get("email") or "").strip():
        # DFM exige un moyen de joindre : sans adresse ni telephone, la fiche
        # ne pourrait ni recevoir une convocation ni etre rapprochee.
        return "sans adresse mail"
    return ""


def preparer(chemin, marqueurs):
    """(a_creer, a_completer, ecartees). Rien n'est ecrit."""
    with open(chemin, encoding="utf-8-sig") as f:
        lignes = [r for r in csv.DictReader(f, delimiter=";")
                  if (r.get("nom") or "").strip()]

    a_creer, a_completer, ecartees = [], [], []
    vus = set()
    for r in lignes:
        motif = _ecartee(r)
        if motif:
            ecartees.append((r, motif))
            continue
        mail = (r.get("email") or "").strip()
        cle = mail.lower()
        if cle in vus:
            # Deux salaries sur la meme adresse : DFM identifie par l'adresse,
            # le second deviendrait le premier. On l'ecarte plutot que de
            # fusionner deux personnes.
            ecartees.append((r, "adresse déjà portée par un autre salarié du fichier"))
            continue
        vus.add(cle)

        entite = (r.get("entite") or "").strip()
        marqueur = marqueurs.get(entite)
        if not marqueur:
            ecartees.append((r, "aucun client DFM pour l'entité « %s »" % entite))
            continue

        fiche = {
            "nom": (r.get("nom") or "").strip().upper(),
            "prenom": (r.get("prenom") or "").strip(),
            "mail": mail,
            "ville": (r.get("etablissement") or "").strip().title(),
            "fonction": fonction_de(r),
            "source": "Import employés %s" % entite,
            "lot_import": os.path.basename(chemin),
            "marqueurs": [marqueur],
        }
        existant = C.rapprocher(mail, "")
        (a_completer if existant else a_creer).append(
            {"fiche": fiche, "existant": existant, "entite": entite})
    return a_creer, a_completer, ecartees


def principal():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    chemin = sys.argv[1]
    if not os.path.exists(chemin):
        raise SystemExit("Fichier introuvable : " + chemin)
    ecrire = "--ecrire" in sys.argv

    import clients
    # L'entite du fichier de paie porte le nom d'usage du client dans DFM.
    marqueurs = {f["nom_usage"]: f["marqueur"] for f in clients.tous().values()}
    marqueurs.setdefault("X-LAB", marqueurs.get("X-LAB", ""))

    a_creer, a_completer, ecartees = preparer(chemin, marqueurs)

    print()
    print("  IMPORT D'EMPLOYES")
    print("  " + "-" * 68)
    print("  Fichier : %s" % os.path.basename(chemin))
    if not ecrire:
        print("  SIMULATION — rien n'est ecrit. Relancez avec --ecrire.")
    print()
    print("  %d a creer, %d deja connu(s), %d ecarte(s)"
          % (len(a_creer), len(a_completer), len(ecartees)))
    print()

    if ecartees:
        print("  ECARTES")
        for r, motif in ecartees:
            print("     %-26s %-16s %-34s %s"
                  % (r["nom"][:26], r["prenom"][:16], (r["emploi_silae"] or "")[:34], motif))
        print()

    if a_creer:
        print("  A CREER")
        for x in a_creer:
            f = x["fiche"]
            print("     %-26s %-16s %-22s %-30s %s"
                  % (f["nom"][:26], f["prenom"][:16], f["fonction"],
                     f["mail"][:30], x["entite"]))
        print()
    for x in a_completer:
        e = x["existant"]
        print("  DEJA CONNU  %s %s (%s) — marqueur ajoute, fonction mise a jour"
              % (e.get("nom"), e.get("prenom"), e.get("mail")))

    if not ecrire:
        print("  Relancez avec --ecrire pour appliquer.")
        return

    crees = C.creer_en_lot([x["fiche"] for x in a_creer]) if a_creer else []
    for x in a_completer:
        C.completer(x["existant"]["id"], x["fiche"])
    print("  %d cree(s), %d complete(s)." % (len(crees), len(a_completer)))
    try:
        import journal
        journal.ecrire("Contacts importés",
                       detail="%d employé(s) depuis %s"
                              % (len(crees) + len(a_completer), os.path.basename(chemin)))
    except Exception:
        pass


if __name__ == "__main__":
    principal()
