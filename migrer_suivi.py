"""Rapatrie le suivi des inscrits dans la base locale.

    python3 migrer_suivi.py [--vraiment]

SANS --vraiment, RIEN N'EST ECRIT.

LES NUMEROS DE LIGNE SONT CONSERVES. « _numero » circule dans tout DFM et sert
de cle a suivi.ecrire ; le renumeroter casserait tout ce qui le detient deja.

TOUS LES ONGLETS DE SUIVI SONT REPRIS, y compris ceux des sessions supprimees
(prefixes « ZZ-supprimee- ») : ils contiennent les inscrits conserves lors d'une
suppression, et ce sont des pieces de dossier.

RIEN N'EST SUPPRIME dans le classeur. Il devient le miroir.

REJOUABLE : une ligne deja presente est remplacee par la meme.
"""
import sys

import base
import profil
import suivi
from connexion import service_sheets

VRAIMENT = "--vraiment" in sys.argv
ORGANISMES = ("mon-organisme", "dsf")

# Les onglets qui ne sont PAS du suivi.
PAS_DU_SUIVI = {"Sessions", "Journal", "Feuille 1"}


def _onglets(feuille):
    m = service_sheets().spreadsheets().get(
        spreadsheetId=feuille, fields="sheets.properties.title").execute()
    return [s["properties"]["title"] for s in m.get("sheets", [])]


def _code_de(onglet, sessions_connues):
    """Le code de session d'un onglet. L'onglet porte le NOM, pas le code.

    On s'appuie sur la fiche de session, jamais sur une transformation du nom :
    « Usures-apdpcnov26 » ne se devine pas depuis « usures-apdpcnov26 » sans
    supposer une regle de casse qui n'est ecrite nulle part.
    """
    for code, S in sessions_connues.items():
        if (S.get("onglet_suivi") or "") == onglet:
            return code
    return ""


def main():
    print("-> %s\n" % ("MIGRATION REELLE" if VRAIMENT
                       else "SIMULATION — rien ne sera ecrit (--vraiment pour agir)"))
    import sessions as _s
    fiches = {c: _s.session(c) for c in _s.SESSIONS}
    total_lignes = total_onglets = orphelins = 0

    for org in ORGANISMES:
        feuille = (profil.charger(org) or {}).get("sheet_suivi") or ""
        if not feuille:
            print("   %s : aucun classeur declare, ignore.\n" % org)
            continue
        print("== %s ==" % org)
        try:
            onglets = _onglets(feuille)
        except Exception as e:
            print("   LECTURE IMPOSSIBLE : %s\n" % str(e)[:140])
            continue

        for onglet in onglets:
            if onglet in PAS_DU_SUIVI:
                continue
            code = _code_de(onglet, fiches)
            if not code:
                # Onglet de session supprimee : on le range sous un code derive
                # du nom d'onglet, pour ne rien perdre et ne rien confondre.
                code = onglet
                orphelins += 1
            try:
                v = service_sheets().spreadsheets().values().get(
                    spreadsheetId=feuille, range=f"'{onglet}'!A2:AX1000"
                ).execute().get("values", [])
            except Exception as e:
                print("   %-34s LECTURE IMPOSSIBLE : %s" % (onglet, str(e)[:70]))
                continue

            lignes = [(i + 2, l) for i, l in enumerate(v) if l and str(l[0] or "").strip()]
            marque = "" if code != onglet else "  (session supprimee)"
            print("   %-34s %3d inscrit(s)%s" % (onglet[:34], len(lignes), marque))
            total_onglets += 1
            total_lignes += len(lignes)

            if VRAIMENT:
                for numero, brute in lignes:
                    complete = list(brute) + [""] * max(0, len(suivi.COL) - len(brute))
                    d = {cle: str(complete[idx] or "") for cle, idx in suivi.COL.items()}
                    base.suivi_ajouter(org, code, d, numero=numero)
        print()

    if VRAIMENT:
        print("-> Termine. %d inscrit(s) sur %d onglet(s), dont %d de sessions supprimees."
              % (total_lignes, total_onglets, orphelins))
        print("   Base : %s (%d Ko)" % (base.CHEMIN, base.etat()["octets"] // 1024))
        print("   Le classeur n'a PAS ete modifie.")
    else:
        print("-> %d inscrit(s) sur %d onglet(s) seraient repris, dont %d de sessions"
              % (total_lignes, total_onglets, orphelins))
        print("   supprimees. Relancez avec --vraiment.")


if __name__ == "__main__":
    main()
