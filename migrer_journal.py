"""Rapatrie le journal des classeurs Google dans la base locale.

    python3 migrer_journal.py [--vraiment]

SANS --vraiment, RIEN N'EST ECRIT : le script lit, verifie la chaine de scelles
telle qu'elle est dans le classeur, et dit ce qu'il ferait. Une piste d'audit ne
se deplace pas a l'aveugle.

LES RANGS SONT CONSERVES A L'IDENTIQUE. Le scelle d'une ligne se calcule sur son
rang, son contenu et le scelle de la ligne precedente. Renumeroter en arrivant
invaliderait toute la chaine — la migration casserait elle-meme la preuve
qu'elle est censee mettre a l'abri.

RIEN N'EST SUPPRIME dans le classeur. Il reste tel quel, et devient le miroir.

CE SCRIPT EST REJOUABLE. Une entree deja presente est remplacee par la meme :
le relancer apres un echec partiel ne cree pas de doublon.
"""
import sys

import base
import profil
import scellement
from connexion import service_sheets

ONGLET = "Journal"
VRAIMENT = "--vraiment" in sys.argv

# Les deux entites, chacune son classeur et sa propre chaine de scelles.
ORGANISMES = ("mon-organisme", "dsf")


def _lire(feuille):
    """Les lignes du journal d'un classeur, avec leur rang reel."""
    v = service_sheets().spreadsheets().values().get(
        spreadsheetId=feuille, range=f"'{ONGLET}'!A2:J100000"
    ).execute().get("values", [])
    # Le rang commence a 2 : la ligne 1 est l'en-tete. On garde l'index reel,
    # y compris pour les lignes vides, sinon tout ce qui suit se decale.
    return [(i + 2, l) for i, l in enumerate(v)]


def _verifier(feuille):
    """L'etat de la chaine, tel que DFM le calcule LUI-MEME.

    ON N'ECRIT PAS UNE SECONDE VERIFICATION. J'en avais redige une, et elle
    accusait une ligne intacte : elle sautait les entrees non scellees SANS
    faire avancer l'ancetre, alors que la pose prend le scelle de la ligne
    physiquement au-dessus, vide compris. C'est un defaut deja diagnostique et
    corrige ici le 05/08/2026 — je l'avais recree a l'identique. Deux
    implementations d'une meme regle finissent par diverger, et sur une piste
    d'audit la divergence s'appelle une fausse accusation.
    """
    import journal as _j
    fiches = _j.verifier(feuille) or []
    return fiches[0] if fiches else {}


def main():
    print("-> %s\n" % ("MIGRATION REELLE" if VRAIMENT
                       else "SIMULATION — rien ne sera ecrit (--vraiment pour agir)"))
    total = 0
    for org in ORGANISMES:
        feuille = (profil.charger(org) or {}).get("sheet_suivi") or ""
        if not feuille:
            print("   %s : aucun classeur declare, ignore.\n" % org)
            continue
        print("== %s ==" % org)
        try:
            lignes = _lire(feuille)
        except Exception as e:
            print("   LECTURE IMPOSSIBLE : %s\n" % str(e)[:140])
            continue
        pleines = [(r, l) for r, l in lignes if l and str(l[0] or "").strip()]
        print("   %d ligne(s) de journal" % len(pleines))
        if pleines:
            print("   rangs %d a %d" % (pleines[0][0], pleines[-1][0]))

        f = _verifier(feuille)
        print("   chaine dans le classeur : %d scellee(s), %d sans scelle"
              % (f.get("scellees", 0), f.get("non_scellees", 0)))
        rupture = f.get("rupture")
        if rupture:
            print("   RUPTURE au rang %s — %s, %s, %s"
                  % (rupture.get("rang"), rupture.get("quand"),
                     rupture.get("quoi"), rupture.get("qui")))
            print("   Les lignes sont reprises TELLES QUELLES : la migration ne")
            print("   repare rien et ne masque rien. Le defaut reste visible apres.")
        elif f.get("non_scellees"):
            print("   Aucune rupture. Les entrees sans scelle n'attestent rien,")
            print("   mais ne rompent pas la chaine : elles sont reprises aussi.")

        if VRAIMENT:
            for rang, l in pleines:
                corps = [str(x or "") for x in l[:scellement.LARGEUR]]
                corps += [""] * (scellement.LARGEUR - len(corps))
                scelle = l[scellement.LARGEUR] if len(l) > scellement.LARGEUR else ""
                base.journal_ajouter(org, corps, rang=rang, scelle=str(scelle or ""))
            print("   -> %d entree(s) ecrite(s) dans la base." % len(pleines))
        total += len(pleines)
        print()

    if VRAIMENT:
        print("-> Termine. %d entree(s) au total." % total)
        print("   Base : %s (%d Ko)" % (base.CHEMIN, base.etat()["octets"] // 1024))
        print("   Le classeur n'a PAS ete modifie : il devient le miroir.")
    else:
        print("-> %d entree(s) seraient reprises. Relancez avec --vraiment." % total)


if __name__ == "__main__":
    main()
