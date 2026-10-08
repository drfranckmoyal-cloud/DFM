"""Rapatrie l'etat de vie des sessions dans la base locale.

    python3 migrer_sessions.py [--vraiment]

SANS --vraiment, RIEN N'EST ECRIT : le script lit et montre ce qu'il reprendrait.

CE QUI EST REPRIS : les neuf colonnes d'ETAT — statut, cloture, emargement
genere et signe et leurs liens, fin, report, alerte. Pas le nom de la formation,
pas les dates, pas le nombre de places : ceux-la vivent dans sessions.json, et
les recopier ferait deux verites.

LES SESSIONS SUPPRIMEES SONT REPRISES AUSSI. L'onglet garde des lignes de
sessions qui n'existent plus dans sessions.json — trois sur six le 17/08/2026.
Leur etat part quand meme dans la base : jeter une trace parce qu'elle est
devenue orpheline, c'est perdre ce qui expliquait la suppression.

RIEN N'EST SUPPRIME dans le classeur. Il devient le miroir.
"""
import sys

import base
import profil
from connexion import service_sheets

ONGLET = "Sessions"
VRAIMENT = "--vraiment" in sys.argv
ORGANISMES = ("mon-organisme", "dsf")

# L'ordre des colonnes de l'onglet, A a N.
COLONNES = ["code_session", "nom_formation", "date_debut", "date_fin",
            "statut_session", "cloture_le", "emargement_genere_le",
            "lien_emargement", "emargement_signe_le", "lien_emargement_signe",
            "places_max", "terminee_le", "report_le", "alerte_cloture_le"]


def main():
    print("-> %s\n" % ("MIGRATION REELLE" if VRAIMENT
                       else "SIMULATION — rien ne sera ecrit (--vraiment pour agir)"))
    import sessions as _s
    total = orphelines = 0
    for org in ORGANISMES:
        feuille = (profil.charger(org) or {}).get("sheet_suivi") or ""
        if not feuille:
            print("   %s : aucun classeur declare, ignore.\n" % org)
            continue
        print("== %s ==" % org)
        try:
            v = service_sheets().spreadsheets().values().get(
                spreadsheetId=feuille, range=f"'{ONGLET}'!A2:N200"
            ).execute().get("values", [])
        except Exception as e:
            print("   LECTURE IMPOSSIBLE : %s\n" % str(e)[:140])
            continue

        for l in v:
            if not l or not str(l[0] or "").strip():
                continue
            d = dict(zip(COLONNES, list(l) + [""] * len(COLONNES)))
            code = str(d["code_session"]).strip()
            connue = code in _s.SESSIONS
            if not connue:
                orphelines += 1
            valeurs = {c: str(d.get(c) or "") for c in base.CHAMPS_ETAT}
            renseignes = [c for c, x in valeurs.items() if x]
            print("   %-24s %s" % (code, "" if connue else "(supprimee)"))
            for c in renseignes:
                print("      %-22s %s" % (c, valeurs[c][:46]))
            if not renseignes:
                print("      (aucun etat)")
            if VRAIMENT:
                # miroir=False : on ne renvoie pas au classeur ce qui en vient.
                base.etat_poser_plusieurs(org, code, valeurs)
            total += 1
        print()

    if VRAIMENT:
        print("-> Termine. %d session(s) reprise(s), dont %d supprimee(s)."
              % (total, orphelines))
        print("   Base : %s (%d Ko)" % (base.CHEMIN, base.etat()["octets"] // 1024))
        print("   Le classeur n'a PAS ete modifie : il devient le miroir.")
    else:
        print("-> %d session(s) seraient reprises, dont %d supprimee(s)."
              % (total, orphelines))
        print("   Relancez avec --vraiment.")


if __name__ == "__main__":
    main()
