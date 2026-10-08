"""Importer une liste de structures clientes depuis un tableau Numbers ou CSV.

    python3 importer_clients.py <fichier>            # montre ce qui serait fait
    python3 importer_clients.py <fichier> --ecrire   # le fait

POURQUOI CE SCRIPT EXISTE. Saisir vingt-sept structures a la main, c'est vingt-
sept occasions de se tromper sur un SIRET — et un SIRET faux sur une convention
la fragilise. Le fichier vient d'une base, il fait plus autorite qu'une saisie.

IL NE CREE PAS DE DOUBLON. Le rapprochement se fait sur le SIRET, qui identifie
une personne morale et ne se partage pas. Une structure deja connue est MISE A
JOUR en gardant son identifiant et son marqueur : ses factures, ses sessions et
les praticiens qui la portent restent rattaches.

IL N'IMPORTE PAS LES MOTS DE PASSE. Le fichier source contient les identifiants
du portail OPCO ; ils n'ont rien a faire dans une base clients, et DFM n'a aucun
champ pour les recevoir.
"""
import os
import sys

import clients

MAIL_UNIQUE = "opcocemedis@gmail.com"

# Colonne du fichier -> champ DFM. Le nom d'usage devient le nom affiche
# partout ; la raison sociale ne sert qu'aux documents contractuels.
CORRESPONDANCE = {
    "Nom du centre": "nom_usage",
    "Raison sociale": "raison_sociale",
    "Adresse du siège": "adresse",
    "SIRET": "siret",
    "Représentant légal": "representant",
    "Fonction du représentant": "representant_fonction",
    "Téléphone": "telephone",
    "Plafond OPCO": "plafond_opco",
}
# Colonnes volontairement ignorees, et pourquoi.
IGNOREES = {
    "Adresse mail de contact": "remplacee par l'adresse unique",
    "Identifiant du portail OPCO EP": "identifiant d'un portail tiers",
    "Mot de passe du portail OPCO EP": "SECRET — n'entre pas dans DFM",
    "Adresse mail exploitée par l'OPCO": "adresse d'un tiers",
    "ID OPCO-EP": "identifiant d'un portail tiers",
}


def _euros(brut):
    """Normalise un plafond : « 30000.0 » devient « 30 000 EUR », ecrit pareil
    pour tous. Le champ est libre, mais une seule ecriture le rend comparable.

    ATTENTION AU SEPARATEUR DECIMAL. Numbers rend les nombres en flottants :
    « 30000.0 ». Retirer les caracteres non chiffres donnerait « 300000 », soit
    un plafond DIX FOIS TROP HAUT — assez pour laisser passer une commande qui
    aurait du etre refusee. Defaut vu en simulation le 06/08/2026 sur les 27
    structures, avant toute ecriture. On lit le nombre, on ne le rabote pas.
    """
    t = str(brut or "").strip()
    if not t:
        return ""
    for c in (" ", "\xa0", "\u202f", "\u20ac", "EUR"):
        t = t.replace(c, "")
    t = t.replace(",", ".")
    try:
        n = int(round(float(t)))
    except ValueError:
        return str(brut).strip()
    return "{:,}".format(n).replace(",", "\u202f") + " \u20ac"


def lire(chemin):
    """Rend (entetes, lignes). Accepte le .numbers et le .csv."""
    if chemin.lower().endswith(".numbers"):
        from numbers_parser import Document
        table = Document(chemin).sheets[0].tables[0]
        brut = table.rows(values_only=True)
    else:
        import csv
        with open(chemin, encoding="utf-8-sig") as f:
            brut = [l for l in csv.reader(f, delimiter=";")]
    entetes = [str(x or "").strip() for x in brut[0]]
    return entetes, brut[1:]


def preparer(chemin):
    """Les fiches pretes a ecrire, et ce qui a ete ecarte."""
    entetes, brut = lire(chemin)
    manquantes = [c for c in CORRESPONDANCE if c not in entetes]
    if manquantes:
        raise SystemExit("Colonnes absentes du fichier : " + ", ".join(manquantes))

    connus = clients.tous()
    # Le SIRET identifie la personne morale. On indexe dessus, pas sur le nom :
    # une meme structure change de nom d'usage, jamais de SIRET.
    par_siret = {(f.get("siret") or "").strip(): i
                 for i, f in connus.items() if (f.get("siret") or "").strip()}

    fiches, ecartees = [], []
    for n, r in enumerate(brut, start=2):
        v = {entetes[i]: str(r[i] or "").strip() for i in range(min(len(entetes), len(r)))}
        if not v.get("Raison sociale"):
            if any(v.values()):
                ecartees.append((n, "ligne sans raison sociale", v))
            continue
        siret = v.get("SIRET", "")
        if len(siret) != 14 or not siret.isdigit():
            ecartees.append((n, "SIRET invalide (%r)" % siret, v))
            continue
        fiche = {dfm: v.get(col, "") for col, dfm in CORRESPONDANCE.items()}
        fiche["plafond_opco"] = _euros(fiche["plafond_opco"])
        fiche["mail"] = MAIL_UNIQUE
        fiches.append({"ligne": n, "fiche": fiche,
                       "existant": par_siret.get(siret, "")})
    return fiches, ecartees


def ecarts(ancien, neuf):
    """Ce qui change reellement, champ par champ. Sert a montrer avant d'ecrire."""
    sortie = []
    for cle, libelle, _ in clients.CHAMPS:
        a, b = (ancien.get(cle) or "").strip(), (neuf.get(cle) or "").strip()
        if b and a != b:
            sortie.append((libelle, a or "—", b))
    return sortie


def principal():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    chemin = sys.argv[1]
    if not os.path.exists(chemin):
        raise SystemExit("Fichier introuvable : " + chemin)
    ecrire = "--ecrire" in sys.argv

    fiches, ecartees = preparer(chemin)
    connus = clients.tous()
    neuves = [x for x in fiches if not x["existant"]]
    majs = [x for x in fiches if x["existant"]]

    print()
    print("  IMPORT DE STRUCTURES CLIENTES")
    print("  " + "-" * 66)
    print("  Fichier : %s" % os.path.basename(chemin))
    if not ecrire:
        print("  SIMULATION — rien n'est ecrit. Relancez avec --ecrire.")
    print()
    print("  %d a creer, %d a mettre a jour, %d ecartee(s)"
          % (len(neuves), len(majs), len(ecartees)))
    print("  Adresse mail imposee a toutes : %s" % MAIL_UNIQUE)
    print()

    for n, motif, v in ecartees:
        print("  ECARTEE  ligne %d — %s" % (n, motif))
    if ecartees:
        print()

    for x in majs:
        ancien = connus[x["existant"]]
        d = ecarts(ancien, x["fiche"])
        print("  MISE A JOUR  %s" % x["existant"])
        print("               identifiant et marqueur conserves — factures et "
              "sessions restent rattachees")
        for libelle, a, b in d:
            print("     %-28s %s" % (libelle, a))
            print("     %-28s -> %s" % ("", b))
        if not d:
            print("     (rien ne change)")
        print()

    if neuves:
        print("  A CREER :")
        for x in neuves:
            f = x["fiche"]
            print("     %-26s %-52s %s  %s"
                  % (f["nom_usage"][:26], f["raison_sociale"][:52],
                     f["siret"], f["plafond_opco"]))
        print()

    if not ecrire:
        print("  Relancez avec --ecrire pour appliquer.")
        return

    faits = 0
    for x in majs:
        clients.modifier(x["existant"], dict(connus[x["existant"]], **x["fiche"]))
        faits += 1
    for x in neuves:
        try:
            clients.creer(x["fiche"])
            faits += 1
        except ValueError as e:
            print("  REFUSEE  %s : %s" % (x["fiche"]["nom_usage"], e))
    print("  %d fiche(s) ecrite(s). Total en base : %d." % (faits, len(clients.tous())))
    try:
        import journal
        journal.ecrire("Clients importés",
                       detail="%d structure(s) depuis %s" % (faits, os.path.basename(chemin)))
    except Exception:
        pass


if __name__ == "__main__":
    principal()
