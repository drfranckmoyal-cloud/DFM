"""Rattacher une signature ou une annulation a SA session.

LE PROBLEME. Les tables Supabase — Signatures, Annulations, Questionnaires —
sont communes aux deux organismes et filtrees par le seul NOM DE FORMATION.
Or « Usures » est dispensee par DSF et par Smileclub, et le sera plusieurs fois
par an chez chacun. Deux enregistrements portant le meme nom de praticien et le
meme nom de formation etaient donc indiscernables : la relevee prenait le plus
recent, sans garantie qu'il vienne de la bonne session.

Mesure du 04/08/2026 : Bruce WAYNE et Peter PARKER sont inscrits sur « Usures »
des DEUX cotes, et Bruce WAYNE porte quatre signatures pour cette formation.

LA SOLUTION. Le code de session voyage desormais dans le lien de signature et
s'enregistre avec la preuve. Ce module trie ce qui revient de Supabase.

CE QUI EXISTAIT AVANT N'EST PAS PERDU. Les enregistrements anterieurs n'ont pas
de code de session : on ne peut pas les attribuer, mais on ne peut pas non plus
les jeter — ce sont de vraies signatures de vrais praticiens. Ils restent donc
candidats, apres ceux qui portent le bon code.
"""


def lire(avec_session, sans_session):
    """Interroge Supabase AVEC la colonne « session », et sans elle si elle
    n'existe pas encore.

    Sans ce repli, elargir la requete cassait toutes les relevees tant que le
    SQL n'avait pas ete execute dans la console Supabase : le code et la base
    doivent pouvoir avancer separement. Une fois la colonne ajoutee, le repli
    ne se declenche plus jamais.
    """
    try:
        return avec_session()
    except Exception as e:
        if "session" not in str(e).lower():
            raise
        print("   (colonne « session » absente de Supabase : relevee sur le seul")
        print("    nom de formation, comme avant. Voir le SQL a executer.)")
        return sans_session()


def _code(enr):
    return str((enr or {}).get("session") or "").strip()


def par_session(enregistrements, code_session):
    """Trie les enregistrements du plus au moins surement rattachables.

    1. Ceux qui portent EXACTEMENT ce code de session.
    2. Ceux qui n'en portent aucun — anterieurs au 04/08/2026.

    Ceux qui portent le code d'une AUTRE session sont ecartes : ils
    appartiennent a un autre dossier, et rien ne justifie de s'en servir.
    """
    liste = list(enregistrements or [])
    code = str(code_session or "").strip()
    if not code:
        return liste
    exacts = [x for x in liste if _code(x) == code]
    anonymes = [x for x in liste if not _code(x)]
    return exacts + anonymes


def ecartes(enregistrements, code_session):
    """Ceux qui appartiennent visiblement a une autre session. Sert a le DIRE
    plutot qu'a les faire disparaitre en silence : une signature ecartee est
    une information, pas un dechet."""
    code = str(code_session or "").strip()
    if not code:
        return []
    return [x for x in (enregistrements or []) if _code(x) and _code(x) != code]
