"""Ce que les durees de conservation declarees recouvrent reellement.

POURQUOI CE MODULE EXISTE. DFM laisse declarer trois durees — journal,
reponses aux questionnaires, sessions archivees — et ces valeurs ne sont lues
NULLE PART. Elles sont exactes et honnetes : leur libelle dit « duree declaree »
et l'aide precise qu'aucune purge n'existe. Mais un engagement que personne ne
peut ni produire ni verifier ne vaut rien devant un controleur, et ne sert a
rien pour agir.

CE MODULE NE SUPPRIME RIEN, ET N'EN A PAS LES MOYENS. Il ne fait que COMPTER ce
qui depasse la duree declaree, pour que la decision reste humaine. Une purge
automatique sur des pieces de formation serait irrattrapable, et le RGPD
n'exige pas d'automatisme : il exige une duree definie, justifiable, et
appliquee. Compter est ce qui permet d'appliquer.

CE QU'IL COMPTE, PAR ORGANISME, les deux etant deux responsables de traitement
distincts.
"""
from datetime import date, datetime


CATEGORIES = [
    ("conservation_journal", 36, "Journal d'activités",
     "Chaque action réalisée dans DFM, avec sa date et la personne concernée.",
     "Piste d'audit Qualiopi. Trois ans couvrent un cycle de certification complet."),
    ("conservation_reponses", 36, "Réponses aux questionnaires",
     "Évaluations des acquis, satisfaction et à froid, nominatives.",
     "Preuve de l'atteinte des objectifs — indicateur 11. Données personnelles."),
    ("conservation_sessions", 60, "Sessions et pièces de formation",
     "Conventions, feuilles d'émargement, attestations, factures.",
     "Cinq ans : durée attendue pour les pièces d'un organisme de formation."),
]


def _duree(cle, defaut):
    try:
        import parametres
        v = (parametres.charger() or {}).get(cle)
        return int(v) if str(v or "").strip() else defaut
    except Exception:
        return defaut


def _date_de(quand):
    """La date derriere une chaine, quelle que soit sa forme.

    DFM horodate en ISO dans le journal, en ISO avec « T » cote Supabase, et en
    francais dans les fiches de session. Les trois cohabitent : une seule forme
    acceptee ferait passer des elements pour non datables.
    """
    t = str(quand or "").strip()
    if not t:
        return None
    for forme, taille in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%dT%H:%M:%S", 19),
                          ("%Y-%m-%d", 10), ("%d/%m/%Y %H:%M", 16), ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(t[:taille], forme).date()
        except Exception:
            continue
    return None


def _mois_depuis(quand):
    d = _date_de(quand)
    if d is None:
        return None
    a = date.today()
    return (a.year - d.year) * 12 + (a.month - d.month) - (1 if a.day < d.day else 0)


def _plus_vieux(dates):
    """La date la PLUS ANCIENNE, sur la date elle-meme et non sur son texte.

    Comparer les chaines melangerait « 2026-07-27 » et « 27/07/2026 », et
    designerait l'element le plus recent une fois sur deux.
    """
    valides = [(_date_de(q), q) for _, q in dates if _date_de(q) is not None]
    return min(valides)[1] if valides else ""


def _journal(feuille, mois):
    from connexion import service_sheets
    try:
        v = service_sheets().spreadsheets().values().get(
            spreadsheetId=feuille, range="'Journal'!A2:A20000").execute().get("values", [])
    except Exception as e:
        return {"lisible": False, "souci": str(e)[:140]}
    ages = [(_mois_depuis(x[0]), x[0]) for x in v if x and str(x[0]).strip()]
    return {"lisible": True, "total": len(ages),
            "depasses": len([m for m, _ in ages if m is not None and m > mois]),
            "plus_ancien": _plus_vieux(ages)}


def _reponses(codes, mois):
    """Les questionnaires Supabase des sessions de CET organisme.

    Supabase est commun aux deux organismes : filtrer sur leurs codes de session
    est le seul moyen de ne pas compter les reponses du voisin.
    """
    try:
        import config
        from supabase import create_client
        sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        r = sb.table("Questionnaires").select("created_at,session_code").execute()
        lignes = r.data or []
    except Exception as e:
        return {"lisible": False, "souci": str(e)[:140]}
    ages = [(_mois_depuis(x.get("created_at")), x.get("created_at"))
            for x in lignes if (x.get("session_code") or "") in codes]
    return {"lisible": True, "total": len(ages),
            "depasses": len([m for m, _ in ages if m is not None and m > mois]),
            "plus_ancien": _plus_vieux(ages)}


def _sessions(fiches, mois):
    ages = []
    for f in fiches:
        d = (f.get("date_fin") or f.get("date_debut") or "").strip()
        if d:
            ages.append((_mois_depuis(d), d))
    return {"lisible": True, "total": len(ages),
            "depasses": len([m for m, _ in ages if m is not None and m > mois]),
            "plus_ancien": _plus_vieux(ages)}


def _en_annees(mois):
    """« 36 » -> « 3 ans ». « 30 » -> « 2 ans et 6 mois ». « 8 » -> « ».

    Une duree se pense en annees dans une politique de conservation ; « 3.0 ans »
    se lit comme une mesure, pas comme un engagement.
    """
    a, m = divmod(int(mois or 0), 12)
    if not a:
        return ""
    texte = "%d an%s" % (a, "s" if a > 1 else "")
    return texte + (" et %d mois" % m if m else "")


def etat():
    """Pour chaque organisme et chaque categorie : la duree declaree et ce qui la depasse."""
    import profil
    import sessions as _s

    sortie = []
    for p in profil.lister():
        ident = p["id"] if isinstance(p, dict) else p
        fiche = profil.charger(ident) or {}
        feuille = fiche.get("sheet_suivi") or ""
        siennes = [f for c, f in _s.SESSIONS.items()
                   if (f.get("organisme") or "") == ident]
        codes = {c for c, f in _s.SESSIONS.items() if (f.get("organisme") or "") == ident}

        lignes = []
        for cle, defaut, titre, quoi, pourquoi in CATEGORIES:
            mois = _duree(cle, defaut)
            if cle == "conservation_journal":
                m = _journal(feuille, mois) if feuille else {"lisible": False,
                                                             "souci": "aucun classeur de suivi"}
            elif cle == "conservation_reponses":
                m = _reponses(codes, mois)
            else:
                m = _sessions(siennes, mois)
            lignes.append({"cle": cle, "titre": titre, "quoi": quoi, "pourquoi": pourquoi,
                           "mois": mois, "en_annees": _en_annees(mois), **m})
        sortie.append({"organisme": ident,
                       "marque": fiche.get("marque") or ident,
                       "raison_sociale": fiche.get("organisme") or "",
                       "siret": fiche.get("siret") or "",
                       "categories": lignes,
                       # Un depassement n'est pas une faute : c'est un point a
                       # trancher, et le trancher est precisement l'engagement.
                       "a_traiter": sum(l.get("depasses") or 0 for l in lignes)})
    return sortie
