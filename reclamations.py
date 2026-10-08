"""Le registre des reclamations.

POURQUOI CE MODULE EXISTE. L'indicateur 31 ne demande pas de n'avoir aucune
reclamation — il demande de savoir en traiter une, et de le PROUVER. Un
organisme qui declare « nous n'en avons jamais eu » sans registre est
exactement dans la situation qu'un auditeur regarde de pres.

DFM avait une adresse de reclamation et un delai de reponse annonce, tous deux
inscrits dans la fiche de l'organisme. Rien ne permettait de tracer ce qui
arrivait ensuite : reception, traitement, reponse, cloture. C'est cette suite
qui constitue la preuve.

UN REGISTRE PAR ORGANISME. DSF et Smileclub sont certifies separement : une
reclamation adressee a l'un ne regarde pas l'autre.

RIEN NE SE SUPPRIME. Une reclamation classee reste au registre : c'est
precisement ce qu'on presente. Seule la SAISIE se corrige.
"""
import json
import os
from datetime import date, datetime

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "reclamations.json")

ORIGINES = [
    ("apprenant", "Apprenant"),
    ("client", "Client (entreprise, centre)"),
    ("formateur", "Formateur ou sous-traitant"),
    ("financeur", "Financeur (OPCO, ANDPC)"),
    ("autre", "Autre"),
]

# Une reclamation n'est ni « bonne » ni « mauvaise » : elle est ouverte, ou
# close, et la maniere dont elle s'est close est une information a part.
ISSUES = [
    ("fondee", "Fondée — correction apportée"),
    ("partielle", "Partiellement fondée"),
    ("non_fondee", "Non fondée — explication donnée"),
    ("sans_suite", "Sans suite — désistement"),
]


def _tout():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)


def _organisme(ident=None):
    if ident:
        return ident
    try:
        import profil
        return profil.actif()
    except Exception:
        return ""


def _aujourdhui():
    return date.today().strftime("%Y-%m-%d")


def _jour(brut):
    t = str(brut or "").strip()
    for forme in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t[:10], forme).date()
        except Exception:
            continue
    return None


def _fr(brut):
    d = _jour(brut)
    return d.strftime("%d/%m/%Y") if d else ""


def _delai_annonce(organisme=None):
    try:
        import profil
        v = (profil.charger(_organisme(organisme)) or {}).get("reclamations_delai")
        return int(v) if str(v or "").strip() else 15
    except Exception:
        return 15


def _numero(fiches, annee):
    """« R2026-003 ». Numerotation continue par annee, comme les factures :
    un registre dont les numeros sautent se lit comme un registre incomplet."""
    prefixe = "R%d-" % annee
    pris = [f["numero"] for f in fiches.values()
            if str(f.get("numero") or "").startswith(prefixe)]
    suite = 0
    for n in pris:
        try:
            suite = max(suite, int(n.split("-")[-1]))
        except Exception:
            pass
    return "%s%03d" % (prefixe, suite + 1)


def _enrichir(f, delai):
    """Ajoute ce qui se deduit : etat, retard, dates lisibles."""
    d = dict(f or {})
    recue = _jour(d.get("recue_le"))
    close = _jour(d.get("close_le"))
    d["recue_fr"] = _fr(d.get("recue_le"))
    d["accusee_fr"] = _fr(d.get("accusee_le"))
    d["close_fr"] = _fr(d.get("close_le"))
    d["ouverte"] = not close
    d["jours"] = (close - recue).days if (recue and close) else (
        (date.today() - recue).days if recue else None)
    d["delai_annonce"] = delai
    # « En retard » se juge sur le delai QUE VOUS AVEZ ANNONCE, pas sur une
    # norme generale : c'est cet engagement-la que l'auditeur verifie.
    d["en_retard"] = bool(d["ouverte"] and d["jours"] is not None and d["jours"] > delai)
    d["issue_libelle"] = dict(ISSUES).get(d.get("issue") or "", "")
    d["origine_libelle"] = dict(ORIGINES).get(d.get("origine") or "", "")
    return d


def lister(organisme=None, closes=True):
    """Les reclamations, la plus recente d'abord."""
    o = _organisme(organisme)
    delai = _delai_annonce(o)
    fiches = [_enrichir(f, delai) for f in (_tout().get(o) or {}).values()]
    if not closes:
        fiches = [f for f in fiches if f["ouverte"]]
    fiches.sort(key=lambda f: str(f.get("recue_le") or ""), reverse=True)
    return fiches


def une(ident, organisme=None):
    o = _organisme(organisme)
    f = (_tout().get(o) or {}).get(ident)
    return _enrichir(f, _delai_annonce(o)) if f else None


def ajouter(valeurs, organisme=None):
    """Inscrit une reclamation au registre.

    SOUS VERROU : la numerotation R2026-001, 002… se calcule sur ce qui est
    deja au registre. Deux ajouts simultanes — un depot releve par la
    synchronisation pendant une saisie a la main — attribueraient le meme
    numero, et un registre a numeros doubles ne se defend pas.
    """
    import fichiers
    o = _organisme(organisme)
    if not o:
        return None, "Aucun organisme actif."
    objet = str(valeurs.get("objet") or "").strip()
    if not objet:
        return None, "Une réclamation a besoin d'un objet."
    recue = str(valeurs.get("recue_le") or "").strip() or _aujourdhui()
    with fichiers.modifier(_FICHIER, {}) as tout:
        fiches = tout.setdefault(o, {})
        annee = (_jour(recue) or date.today()).year
        numero = _numero(fiches, annee)
        ident = numero.lower().replace("-", "")
        fiche = {
            "id": ident, "numero": numero,
            "recue_le": recue,
            "origine": str(valeurs.get("origine") or "apprenant").strip(),
            "qui": str(valeurs.get("qui") or "").strip(),
            "mail": str(valeurs.get("mail") or "").strip(),
            "session": str(valeurs.get("session") or "").strip(),
            "objet": objet,
            "description": str(valeurs.get("description") or "").strip(),
            "accusee_le": "", "traitement": "", "close_le": "", "issue": "",
            "amelioration": "",
        }
        if valeurs.get("depot"):
            fiche["depot"] = str(valeurs["depot"])
        fiches[ident] = fiche
    return _enrichir(fiche, _delai_annonce(o)), ""


_MODIFIABLES = ("recue_le", "origine", "qui", "mail", "session", "objet",
                "description", "accusee_le", "traitement", "close_le", "issue",
                "amelioration")


def enregistrer(ident, valeurs, organisme=None):
    """Met a jour une reclamation, sous verrou comme l'ajout.

    Les controles de cloture sont faits AVANT d'ecrire : une exception dans le
    bloc laisse le fichier intact, ce qui est exactement ce qu'on veut d'une
    cloture refusee.
    """
    import fichiers
    o = _organisme(organisme)
    rendu = None
    with fichiers.modifier(_FICHIER, {}) as tout:
        fiche = (tout.get(o) or {}).get(ident)
        if not fiche:
            return None, "Cette réclamation n'existe pas."
        essai = dict(fiche)
        for cle in _MODIFIABLES:
            if cle in valeurs:
                essai[cle] = str(valeurs[cle] or "").strip()
        # Clore sans dire comment ne prouve rien : on refuse la cloture muette.
        if essai.get("close_le") and not essai.get("issue"):
            return None, "Précisez l'issue avant de clore la réclamation."
        if essai.get("close_le") and not essai.get("traitement"):
            return None, "Décrivez le traitement avant de clore la réclamation."
        fiche.update(essai)
        rendu = dict(fiche)
    return _enrichir(rendu, _delai_annonce(o)), ""


def lien(organisme=None, contact_ligne=None):
    """L'adresse de la page publique de reclamation, prete a mettre dans un mail.

    Les parametres portent ce qu'une page statique ne peut pas savoir : la
    marque a afficher, le delai annonce, l'adresse de repli, et l'organisme
    auquel rattacher le depot.
    """
    from urllib.parse import urlencode
    try:
        import profil
        o = _organisme(organisme)
        f = profil.charger(o) or {}
    except Exception:
        return ""
    base = (f.get("site_reclamation") or "https://gestion-des-formations.netlify.app").rstrip("/")
    q = {"of": o, "marque": f.get("marque") or f.get("organisme") or "",
         "delai": _delai_annonce(o),
         "contact": f.get("reclamations_contact") or f.get("mail_contact") or ""}
    if isinstance(contact_ligne, dict):
        nom = ((contact_ligne.get("prenom") or "") + " " +
               (contact_ligne.get("nom") or "")).strip()
        if nom:
            q["qui"] = nom
        if contact_ligne.get("mail"):
            q["mail"] = contact_ligne["mail"]
        if contact_ligne.get("_session"):
            q["session"] = contact_ligne["_session"]
    return base + "/reclamation.html?" + urlencode({k: v for k, v in q.items() if v})


def relever(organisme=None):
    """Rapatrie dans le registre les reclamations deposees sur la page publique.

    Idempotent : chaque depot Supabase porte un identifiant, conserve dans la
    fiche. Relever deux fois ne cree pas deux entrees — sans quoi une
    reclamation apparaitrait en double a chaque synchronisation.

    L'ACCUSE DE RECEPTION est date du depot : la page confirme a l'ecran, avec
    le delai annonce, et invite a en garder une trace. C'est cette confirmation
    qui fait foi ; la redater a la releve ferait courir le delai a partir du
    moment ou VOUS avez regarde, ce qui n'est pas l'engagement pris.
    """
    try:
        import config
        from supabase import create_client
        sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        recus = (sb.table("Reclamations").select("*").execute().data) or []
    except Exception as e:
        # Le cas courant n'est pas une panne, c'est une table pas encore creee.
        # Le dire en clair evite de chercher une panne la ou il manque une etape.
        if "Reclamations" in str(e) or "PGRST205" in str(e):
            return 0, ("La table « Reclamations » n'existe pas encore dans Supabase. "
                       "Créez-la avant de relever : le registre reste utilisable à la main "
                       "en attendant.")
        return 0, "Supabase : %s" % str(e)[:160]

    import fichiers
    o = _organisme(organisme)
    nouvelles = 0
    # Le verrou couvre TOUTE la releve : la synchronisation tourne dans un
    # processus, l'ecran Reclamations dans un autre. L'idempotence repose sur
    # la liste des depots deja connus, qu'il faut lire et reecrire sans qu'un
    # autre processus s'intercale — sinon un depot entre deux fois.
    with fichiers.modifier(_FICHIER, {}) as tout:
        fiches = tout.setdefault(o, {})
        connus = {str(f.get("depot")) for f in fiches.values() if f.get("depot")}
        for r in recus:
            ident_depot = str(r.get("id") or "")
            if not ident_depot or ident_depot in connus:
                continue
            # Un depot sans organisme — page atteinte hors d'un lien DFM —
            # revient a l'organisme actif : mieux vaut une reclamation mal
            # etiquetee, qu'on rectifie d'un clic, qu'une reclamation perdue.
            sien = (r.get("organisme") or "").strip()
            if sien and sien != o:
                continue
            recue = str(r.get("created_at") or "")[:10] or _aujourdhui()
            annee = (_jour(recue) or date.today()).year
            numero = _numero(fiches, annee)
            cle = numero.lower().replace("-", "")
            fiches[cle] = {
                "id": cle, "numero": numero, "depot": ident_depot,
                "recue_le": recue,
                "origine": (r.get("origine") or "apprenant").strip(),
                "qui": (r.get("qui") or "").strip(),
                "mail": (r.get("mail") or "").strip(),
                "session": (r.get("session") or "").strip(),
                "objet": (r.get("objet") or "").strip(),
                "description": (r.get("description") or "").strip(),
                "accusee_le": recue,
                "traitement": "", "close_le": "", "issue": "", "amelioration": "",
            }
            connus.add(ident_depot)
            nouvelles += 1
    return nouvelles, ""


def bilan(organisme=None):
    """De quoi repondre a un auditeur en une phrase, et voir ce qui traine."""
    fiches = lister(organisme)
    closes = [f for f in fiches if not f["ouverte"]]
    delais = [f["jours"] for f in closes if f["jours"] is not None]
    return {
        "total": len(fiches),
        "ouvertes": len([f for f in fiches if f["ouverte"]]),
        "en_retard": len([f for f in fiches if f["en_retard"]]),
        "closes": len(closes),
        "delai_moyen": round(sum(delais) / len(delais), 1) if delais else None,
        "delai_annonce": _delai_annonce(organisme),
        "annee": date.today().year,
        "cette_annee": len([f for f in fiches
                            if str(f.get("recue_le") or "").startswith(str(date.today().year))]),
    }
