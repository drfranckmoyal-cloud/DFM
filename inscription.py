"""Le formulaire public d'inscription : ce que DFM publie, ce qu'il relit.

POURQUOI CE MODULE EXISTE. Les inscriptions arrivaient par un formulaire Google
dont les reponses tombaient dans un classeur, un formulaire PAR SESSION, cree a
la main. C'etait le dernier maillon Google du parcours, et le seul que rien ne
remplacait.

DEUX SENS, ET DEUX SEULEMENT.
  publier(code)  — DFM pousse une session vers la page publique
  relever()      — DFM va chercher les demandes recues

LE CLOISONNEMENT EST PORTE PAR L'ORGANISME. Chaque session publiee emporte le
sien ; la page ne montre que celles de l'organisme de son lien, et la fonction
Netlify le verifie une seconde fois de son cote. Deux entites, deux Qualiopi :
un praticien ne doit jamais voir sur le formulaire de l'une les formations de
l'autre.

RIEN N'EST PUBLIE SANS QU'ON LE DEMANDE. Une session existe dans DFM bien avant
d'etre ouverte aux inscriptions ; la publier est un geste, pas un effet de bord.
"""
import json
import urllib.parse
import urllib.error
import urllib.request

TABLE_ORG = "Organismes_publics"
TABLE_SESS = "Sessions_inscription"
TABLE_INSC = "Inscriptions"


def _sb(chemin, methode="GET", corps=None, prefer=None):
    import config
    import reseau
    url = config.SUPABASE_URL.rstrip("/") + "/rest/v1/" + chemin
    entetes = {"apikey": config.SUPABASE_KEY,
               "Authorization": "Bearer " + config.SUPABASE_KEY,
               "Content-Type": "application/json"}
    if prefer:
        entetes["Prefer"] = prefer
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    requete = urllib.request.Request(url, data=donnees, headers=entetes, method=methode)
    with urllib.request.urlopen(requete, timeout=30, context=reseau.contexte()) as r:
        texte = r.read().decode("utf-8")
        return json.loads(texte) if texte.strip() else []


def lien(code_session):
    """L'adresse du formulaire pour cette session. "" si elle n'en a pas.

    IL SE CALCULE, IL NE SE STOCKE PAS : rien a creer a la naissance d'une
    session, rien a reparer si une adresse change, et le onzieme organisme aura
    le sien sans qu'on y pense.
    """
    import sessions as _s
    try:
        if _s.est_client(code_session):
            return ""          # le centre saisit ses participants lui-meme
        S = _s.session(code_session)
        base = (S.get("url_signature") or "").rstrip("/")
        org = _s.organisme_de(code_session) or ""
        if not base or not org:
            return ""
        return "%s/inscription.html?of=%s&s=%s" % (base, org, code_session)
    except Exception:
        return ""


def _occupees(code_session):
    """Combien de places sont prises. Sert au « il reste 3 places »."""
    import suivi
    try:
        lignes = suivi.lire_lignes_de(code_session)
    except Exception:
        return 0
    return len([l for l in lignes
                if not l["annule_le"]
                and "recontact" not in (l["demande"] or "").lower()
                and not (l["file_attente_le"] and not l["promu_le"])])


def publier_organisme(organisme):
    """Pousse l'identite d'un organisme : logo, marque, contacts."""
    import base64
    import profil
    p = profil.charger(organisme) or {}
    logo = ""
    try:
        octets = profil.logo(organisme)
        # LE LOGO VOYAGE ENCODE DANS LA LIGNE, pas par une adresse. Un lien
        # supposerait un fichier accessible publiquement quelque part — c'est
        # exactement ce qu'on vient de supprimer du Drive.
        if octets and len(octets) <= 400 * 1024:
            logo = "data:image/png;base64," + base64.b64encode(octets).decode()
    except Exception:
        pass
    _sb(TABLE_ORG, "POST", [{
        "organisme": organisme,
        "marque": p.get("marque") or organisme,
        "accroche": p.get("accroche_of") or "",
        "mail_contact": p.get("mail_contact") or "",
        "telephone_contact": p.get("telephone_contact") or "",
        "logo": logo,
    }], "resolution=merge-duplicates")
    return True


def publier(code_session, ouverte=True):
    """Publie une session sur le formulaire public. Rend (ok, explication)."""
    import sessions as _s
    if code_session not in _s.SESSIONS:
        return False, "Session inconnue."
    if _s.est_client(code_session):
        return False, ("Session client : ses participants sont saisis par le centre, "
                       "elle n'a pas de formulaire public.")
    S = _s.session(code_session)
    org = _s.organisme_de(code_session) or ""
    if not org:
        return False, "Session sans organisme : impossible de cloisonner la publication."

    fcode = _s.SESSIONS[code_session].get("formation") or ""
    form = _s.FORMATIONS.get(fcode) or {}
    try:
        publier_organisme(org)
        _sb(TABLE_SESS, "POST", [{
            "code_session": code_session,
            "organisme": org,
            "formation": S.get("nom_formation") or "",
            "titre": S.get("titre_complet") or S.get("nom_formation") or "",
            "date_texte": S.get("date_texte") or "",
            "date_debut": S.get("date_debut") or None,
            "lieu": S.get("adresse") or "",
            "tarif": str(S.get("tarif") or ""),
            "couleur": form.get("couleur") or "#4f7ef8",
            "descriptif": form.get("descriptif_inscription") or "",
            "places_max": int(S.get("places_max") or 0),
            "occupees": _occupees(code_session),
            "ouverte": bool(ouverte),
        }], "resolution=merge-duplicates")
    except urllib.error.HTTPError as e:
        return False, "Supabase : " + e.read().decode("utf-8")[:200]
    except Exception as e:
        return False, str(e)[:200]
    return True, ("Formulaire ouvert." if ouverte else "Formulaire fermé.")


def oublier(code_session):
    """Efface les lignes PUBLIQUES d'une session : formulaire et questionnaires.

    POURQUOI CETTE FONCTION EXISTE. Supprimer une session nettoyait la base de DFM,
    son etat et sa fiche — mais PAS ces deux tables. Elles survivaient, indexees sur
    le code de session. Le 04/10/2026, une session recreee avec un code deja
    utilise a donc herite de l'etat de la precedente : quatre jalons coches a tort,
    et surtout les QUATRE PARTICIPANTS DE TEST de l'ancienne session servis par la
    page publique des questionnaires, avec leurs adresses mail.

    ELLE N'EFFACE PAS LES INSCRIPTIONS RECUES. La table « Inscriptions » porte ce
    que des gens ont rempli : elle n'est pas un etat de publication, c'est une
    donnee, et elle reste. Seules disparaissent les deux lignes qui DECRIVENT la
    publication.

    NE LEVE JAMAIS. Appelee pendant une suppression, son echec ne doit pas laisser
    la session a moitie supprimee. Elle rend la liste de ce qui a ete efface.
    """
    efface = []
    for table in (TABLE_SESS, "Sessions_publiques"):
        cle = "code_session" if table == TABLE_SESS else "session_code"
        try:
            r = _sb("%s?%s=eq.%s&select=%s"
                    % (table, cle, urllib.parse.quote(code_session), cle))
            if not r:
                continue
            _sb("%s?%s=eq.%s" % (table, cle, urllib.parse.quote(code_session)), "DELETE")
            efface.append(table)
        except Exception:
            pass
    return efface


def fermer(code_session):
    """Retire une session du formulaire, sans effacer ce qu'elle a recu."""
    return publier(code_session, ouverte=False)


def etat(code_session):
    """Ou en est la publication d'une session : {publiee, ouverte, occupees}."""
    try:
        r = _sb("%s?code_session=eq.%s&select=ouverte,occupees,maj"
                % (TABLE_SESS, urllib.parse.quote(code_session)))
    except Exception:
        return {"publiee": False, "ouverte": False}
    if not r:
        return {"publiee": False, "ouverte": False}
    return {"publiee": True, "ouverte": bool(r[0].get("ouverte")),
            "occupees": r[0].get("occupees"), "maj": r[0].get("maj") or ""}


def en_attente(organisme=None):
    """Les demandes recues et pas encore reprises dans le suivi."""
    q = "%s?importee_le=is.null&select=*&order=horodateur.asc" % TABLE_INSC
    if organisme:
        q += "&organisme=eq." + urllib.parse.quote(organisme)
    try:
        return _sb(q)
    except Exception:
        return []


def marquer_importee(ident):
    """Marque une demande comme reprise. Sans cela, elle reviendrait."""
    from datetime import datetime
    _sb("%s?id=eq.%s" % (TABLE_INSC, int(ident)), "PATCH",
        {"importee_le": datetime.now().astimezone().isoformat()})
