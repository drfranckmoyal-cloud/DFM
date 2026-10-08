"""Fusionne les registres de formateurs par organisme en un registre partage.

CE QUE CHANGE CETTE MIGRATION. Jusqu'au 19/08/2026 le registre etait
« {organisme: {identifiant: fiche}} » : la meme personne y figurait autant de
fois qu'elle intervenait d'organismes, avec des pieces distinctes. Consequence
constatee : Franck MOYAL avait son CV et son diplome sous DSF, et une fiche vide
sous Smileclub — deux dossiers pour un seul homme, dont un incomplet.

CE QU'ELLE NE CHANGE PAS. Le RATTACHEMENT AUX FORMATIONS reste par organisme.
Les formations sont communes aux deux entites ; dire « Franck enseigne Usures »
sans dire pour QUI ferait pointer DSF vers l'intervenant de Smileclub. Chaque
organisme garde donc sa propre liste de formations par formateur.

    {identifiant: {nom, prenom, civilite, fonction, cv, diplome, photo, autres,
                   organismes: {dsf: {formations: [...]},
                                mon-organisme: {formations: [...]}}}}

REGLE DE FUSION, quand la meme personne existe dans plusieurs registres :
  - une PIECE l'emporte sur une absence de piece, jamais l'inverse ;
  - un CHAMP rempli l'emporte sur un champ vide ;
  - a egalite, l'organisme qui a le dossier le plus complet fait foi ;
  - les organismes SUPPRIMES sont retires de la liste des rattachements, mais
    la personne et ses pieces sont conservees — elle a peut-etre anime des
    sessions passees, et l'indicateur 21 se prouve apres coup.

    python3 migrer_formateurs.py --blanc    # montre, n'ecrit rien
    python3 migrer_formateurs.py            # applique
"""
import json
import os
import shutil
import sys

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "formateurs.json")

CHAMPS_IDENTITE = ("nom", "prenom", "civilite", "fonction")
CHAMPS_PIECES = ("cv", "diplome", "photo")


def _score(fiche):
    """A quel point ce dossier est complet. Sert a departager deux versions."""
    n = sum(1 for c in CHAMPS_PIECES if str(fiche.get(c) or "").strip())
    n += sum(1 for c in CHAMPS_IDENTITE if str(fiche.get(c) or "").strip())
    return n + len(fiche.get("autres") or []) + len(fiche.get("formations") or [])


def fusionner(ancien, vivants):
    """Rend (nouveau_registre, rapport). N'ecrit rien."""
    par_personne = {}
    for org, gens in (ancien or {}).items():
        for ident, f in (gens or {}).items():
            par_personne.setdefault(ident, []).append((org, dict(f or {})))

    neuf, rapport = {}, []
    for ident, versions in par_personne.items():
        # La version la plus complete sert de base.
        versions_triees = sorted(versions, key=lambda x: -_score(x[1]))
        base = dict(versions_triees[0][1])
        source = versions_triees[0][0]

        # Puis on comble ce qui manque avec les autres, sans jamais ecraser.
        comble = []
        for org, f in versions_triees[1:]:
            for c in CHAMPS_IDENTITE + CHAMPS_PIECES:
                if not str(base.get(c) or "").strip() and str(f.get(c) or "").strip():
                    base[c] = f[c]
                    comble.append("%s (depuis %s)" % (c, org))
            for x in (f.get("autres") or []):
                base.setdefault("autres", [])
                if x not in base["autres"]:
                    base["autres"].append(x)

        # Le rattachement aux formations reste PAR ORGANISME.
        organismes, ecartes = {}, []
        for org, f in versions:
            if org in vivants:
                organismes[org] = {"formations": list(f.get("formations") or [])}
            else:
                ecartes.append(org)
        base.pop("formations", None)
        base.pop("dossier", None)          # identifiant du dossier Drive, sans objet
        base["organismes"] = organismes
        base.setdefault("autres", [])
        neuf[ident] = base
        rapport.append({"ident": ident, "versions": [o for o, _ in versions],
                        "base": source, "comble": comble, "ecartes": ecartes,
                        "organismes": sorted(organismes)})
    return neuf, rapport


def deplacer_pieces(neuf, blanc=True):
    """Sort les pieces de « <organisme>/_formateurs/ » vers « _formateurs/ ».

    Le fichier est DEPLACE, pas copie : deux exemplaires du meme CV finiraient
    par diverger. La reference inscrite sur la fiche suit dans le meme geste.
    """
    import documents
    faits, soucis = [], []
    for ident, f in neuf.items():
        for cle in list(CHAMPS_PIECES) + ["autres"]:
            valeurs = f.get(cle) if cle == "autres" else [f.get(cle)]
            neuves = []
            for ref in (valeurs or []):
                ref = str(ref or "").strip()
                if not ref or "/" not in ref:
                    neuves.append(ref)
                    continue
                nom = ref.rsplit("/", 1)[-1]
                cible = "/".join(("_formateurs", documents._sain(ident), documents._sain(nom)))
                if ref == cible:
                    neuves.append(ref)
                    continue
                src = os.path.join(documents.RACINE, ref)
                dst = os.path.join(documents.RACINE, cible)
                if not os.path.exists(src):
                    soucis.append("%s : fichier absent (%s)" % (ident, ref))
                    neuves.append(ref)          # on garde la reference : elle dit ou chercher
                    continue
                if not blanc:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                faits.append("%s -> %s" % (ref, cible))
                neuves.append(cible)
            if cle == "autres":
                f["autres"] = neuves
            else:
                f[cle] = neuves[0] if neuves else ""
    return faits, soucis


def main():
    blanc = "--blanc" in sys.argv[1:]
    print("=" * 66)
    print("  Fusion des registres de formateurs  %s" % ("(A BLANC)" if blanc else ""))
    print("=" * 66)

    ancien = json.load(open(_FICHIER, encoding="utf-8"))
    if not ancien or not isinstance(next(iter(ancien.values()), None), dict):
        print("  Registre vide ou illisible.")
        return 1
    # Deja migre ? Un registre partage a des fiches avec « organismes ».
    if any("organismes" in (v or {}) for v in ancien.values()):
        print("  Ce registre est deja partage. Rien a faire.")
        return 0

    import profil
    vivants = {p["id"] if isinstance(p, dict) else p for p in profil.lister()}
    print("  Organismes existants : %s" % ", ".join(sorted(vivants)))
    print()

    neuf, rapport = fusionner(ancien, vivants)
    for r in rapport:
        print("  %s" % r["ident"])
        print("      present dans   : %s" % ", ".join(r["versions"]))
        print("      dossier retenu : %s" % r["base"])
        if r["comble"]:
            print("      complete par   : %s" % ", ".join(r["comble"]))
        if r["ecartes"]:
            print("      rattachements retires (organismes supprimes) : %s" % ", ".join(r["ecartes"]))
        print("      rattache a     : %s" % (", ".join(r["organismes"]) or "aucun organisme"))

    print()
    faits, soucis = deplacer_pieces(neuf, blanc=blanc)
    print("  %d piece(s) %s :" % (len(faits), "a deplacer" if blanc else "deplacee(s)"))
    for f in faits:
        print("      %s" % f)
    for s in soucis:
        print("      ATTENTION %s" % s)

    if blanc:
        print()
        print("  Rien n'a ete ecrit. Relancez sans --blanc pour appliquer.")
        return 0

    import fichiers
    fichiers.ecrire(_FICHIER, neuf)
    print()
    print("  Registre ecrit : %d formateur(s) partage(s)." % len(neuf))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
