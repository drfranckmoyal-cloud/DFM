"""Envoyer un mail. Une porte, pas un fournisseur.

POURQUOI CE MODULE EXISTE. Dix-sept endroits construisaient leur message puis
appelaient l'API Gmail eux-memes : encodage en base64, « userId=me », jeton
OAuth. Chacun savait donc que DFM envoie par Gmail — ce qui est exactement ce
qu'il faut ignorer pour pouvoir en changer.

CE MODULE EST UNE PORTE. L'appelant dit « envoie ce message pour cet
organisme » et n'apprend jamais par ou il part.

CE QUE RESOUT LE PASSAGE EN SMTP, meme en restant chez Google. L'API demande un
jeton OAuth qui expire ; le 16/08/2026, expire et sans terminal pour repondre,
DFM a ouvert UNE FENETRE DE CONNEXION TOUTES LES DEUX SECONDES et la machine
etait inutilisable. SMTP s'authentifie a chaque envoi, sans jeton, sans fenetre.

TOUT EST PARAMETRE, RIEN N'EST CABLE SUR GMAIL. Serveur, port, identifiant et
adresse d'expedition sont des reglages par organisme. Le jour ou Smileclub et
DSF auront leur propre nom de domaine, ces trois champs changent et le reste ne
bouge pas.

LE REPLI SUR L'API EST VOLONTAIRE. Tant qu'aucun mot de passe SMTP n'est
installe, l'envoi repart par l'API comme avant. La bascule se fait organisme par
organisme, le jour ou vous etes pret, et se defait en retirant le mot de passe.

LES MOTS DE PASSE NE SONT PAS DANS LES PROFILS. Ils vivent dans « smtp.json »,
traite comme « credentials.json » : exclu des sauvegardes par defaut, parce
qu'une archive qu'on depose sans y penser ne doit pas emporter de quoi envoyer
du courrier en votre nom.
"""
import json
import os
import smtplib
import ssl

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_SECRETS = os.path.join(_DOSSIER, "smtp.json")

# Reglages par defaut, quand rien n'est reconnu.
DEFAUTS = {"serveur": "smtp.gmail.com", "port": 587, "tls": True}

# --------------------------------------------------------------------------
# LES FOURNISSEURS CONNUS
#
# LA MECANIQUE N'A JAMAIS ETE PROPRE A GMAIL : ce module ne connait qu'un
# serveur, un port, un identifiant et un mot de passe. Gmail n'etait qu'une
# valeur par defaut. Ce qui manquait, c'est que l'ECRAN le sache : il parlait
# de « compte Google » et de « mot de passe d'application » a tout le monde,
# alors que chez la plupart des hebergeurs ces notions n'existent pas — on
# donne simplement le mot de passe de la boite.
#
# « special » designe les fournisseurs qui EXIGENT un mot de passe dedie et
# une validation en deux etapes. Chez les autres, le mot de passe habituel de
# la boite suffit, et annoncer le contraire enverrait l'utilisateur chercher
# une page qui n'existe pas.
FOURNISSEURS = {
    "gmail.com":     {"nom": "Google", "serveur": "smtp.gmail.com", "port": 587,
                      "special": "google"},
    "googlemail.com": {"nom": "Google", "serveur": "smtp.gmail.com", "port": 587,
                       "special": "google"},
    "outlook.com":   {"nom": "Microsoft", "serveur": "smtp-mail.outlook.com", "port": 587,
                      "special": "microsoft"},
    "hotmail.com":   {"nom": "Microsoft", "serveur": "smtp-mail.outlook.com", "port": 587,
                      "special": "microsoft"},
    "hotmail.fr":    {"nom": "Microsoft", "serveur": "smtp-mail.outlook.com", "port": 587,
                      "special": "microsoft"},
    "live.fr":       {"nom": "Microsoft", "serveur": "smtp-mail.outlook.com", "port": 587,
                      "special": "microsoft"},
    "yahoo.fr":      {"nom": "Yahoo", "serveur": "smtp.mail.yahoo.com", "port": 587,
                      "special": "yahoo"},
    "yahoo.com":     {"nom": "Yahoo", "serveur": "smtp.mail.yahoo.com", "port": 587,
                      "special": "yahoo"},
    "orange.fr":     {"nom": "Orange", "serveur": "smtp.orange.fr", "port": 587},
    "wanadoo.fr":    {"nom": "Orange", "serveur": "smtp.orange.fr", "port": 587},
    "free.fr":       {"nom": "Free", "serveur": "smtp.free.fr", "port": 587},
    "sfr.fr":        {"nom": "SFR", "serveur": "smtp.sfr.fr", "port": 587},
    "laposte.net":   {"nom": "La Poste", "serveur": "smtp.laposte.net", "port": 587},
    "ovh.net":       {"nom": "OVH", "serveur": "ssl0.ovh.net", "port": 587},
    "gandi.net":     {"nom": "Gandi", "serveur": "mail.gandi.net", "port": 587},
    "infomaniak.com": {"nom": "Infomaniak", "serveur": "mail.infomaniak.com", "port": 587},
    "ionos.fr":      {"nom": "IONOS", "serveur": "smtp.ionos.fr", "port": 587},
}


def deviner(adresse):
    """Le fournisseur derriere une adresse. Toujours un dictionnaire.

    « connu » a False pour un NOM DE DOMAINE PROPRE — le cas de tous ceux qui
    ont leur propre adresse, et donc le cas le plus probable le jour ou DFM
    servira quelqu'un d'autre. On ne devine alors rien : c'est l'hebergeur qui
    donne le serveur, et lui inventer une valeur ferait echouer l'envoi en
    laissant croire que le mot de passe est faux.
    """
    domaine = str(adresse or "").split("@")[-1].strip().lower()
    f = FOURNISSEURS.get(domaine)
    if not f:
        # LES SOUS-DOMAINES COMPTENT : « mail.monof.ovh.net » est chez OVH.
        # Le point est OBLIGATOIRE dans le suffixe — sans lui, « notgmail.com »
        # se terminerait par « gmail.com » et serait pris pour du Google.
        for d, v in FOURNISSEURS.items():
            if domaine.endswith("." + d):
                f = v
                break
    if f:
        return dict(f, connu=True, domaine=domaine, tls=True,
                    special=f.get("special", ""))
    return {"connu": False, "domaine": domaine, "nom": "", "special": "",
            "serveur": "", "port": 587, "tls": True}


def _secrets():
    try:
        with open(FICHIER_SECRETS, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def reglages(organisme=None):
    """Les reglages d'envoi d'un organisme. {} si l'envoi SMTP n'est pas installe.

    L'IDENTIFIANT VAUT L'ADRESSE PAR DEFAUT. Chez Gmail, on s'authentifie avec
    l'adresse elle-meme ; separer les deux ne sert que le jour ou un serveur
    demande un identifiant different, et ce jour-la le champ existe.
    """
    import profil
    if not organisme:
        try:
            organisme = profil.actif()
        except Exception:
            organisme = ""
    s = (_secrets().get(organisme) or {})
    mot = str(s.get("mot_de_passe") or "").strip()
    if not mot:
        return {}
    p = profil.charger(organisme) or {}
    adresse = str(s.get("adresse") or p.get("mail_contact") or "").strip()
    if not adresse or "@" not in adresse:
        return {}
    return {"serveur": str(s.get("serveur") or DEFAUTS["serveur"]),
            "port": int(s.get("port") or DEFAUTS["port"]),
            "tls": bool(s.get("tls", DEFAUTS["tls"])),
            "identifiant": str(s.get("identifiant") or adresse),
            "mot_de_passe": mot,
            "adresse": adresse,
            "organisme": organisme}


def installe(organisme=None):
    """L'envoi SMTP est-il pret pour cet organisme ?"""
    return bool(reglages(organisme))


def envoyer(message, organisme=None):
    """Envoie un message MIME deja construit. Leve si l'envoi echoue.

    ON LEVE PLUTOT QUE DE RENDRE FAUX. Les appelants entourent deja l'envoi
    d'un try : un mail qui ne part pas doit interrompre ce qui suit, sans quoi
    le suivi noterait « facture envoyee » pour un courrier reste a quai.
    """
    r = reglages(organisme)
    if not r:
        return _par_api(message)

    # L'ENVELOPPE PORTE L'ADRESSE AUTHENTIFIEE. L'en-tete « From » peut afficher
    # « Smileclub Formations <...> » ; c'est l'enveloppe que le serveur controle,
    # et lui mentir fait refuser le message.
    destinataires = []
    for entete in ("To", "Cc", "Bcc"):
        v = message.get(entete)
        if v:
            destinataires += [a.strip() for a in str(v).split(",") if a.strip()]
    if not destinataires:
        raise ValueError("Message sans destinataire.")
    if message.get("Bcc"):
        del message["Bcc"]

    # LE CONTEXTE VIENT DE « reseau », JAMAIS DE ssl DIRECTEMENT. Le Python de
    # python.org arrive sans aucune autorite de certification : un contexte par
    # defaut echoue sur « CERTIFICATE_VERIFY_FAILED », et l'envoi n'a plus lieu.
    # Constate le 18/08/2026 au premier essai reel — le module existait deja,
    # avec ce diagnostic ecrit dedans, et je ne m'en etais pas servi.
    import reseau
    contexte = reseau.contexte()
    try:
        if r["tls"]:
            with smtplib.SMTP(r["serveur"], r["port"], timeout=30) as s:
                s.ehlo()
                s.starttls(context=contexte)
                s.ehlo()
                s.login(r["identifiant"], r["mot_de_passe"])
                s.sendmail(r["adresse"], destinataires, message.as_bytes())
        else:
            with smtplib.SMTP_SSL(r["serveur"], r["port"], timeout=30,
                                  context=contexte) as s:
                s.login(r["identifiant"], r["mot_de_passe"])
                s.sendmail(r["adresse"], destinataires, message.as_bytes())
        return True
    except Exception as _e:
        # LE SMTP PEUT ETRE MURE, ET LE MUR N'EST PAS CHEZ NOUS. Scaleway ferme en
        # sortie les ports 25, 465, 587 et 2525 : mesure le 23/08/2026, aucun
        # courrier ne part du serveur, et l'echec se presente comme un simple
        # delai depasse. L'API Google passe en HTTPS, qui n'est pas bloque.
        #
        # EN SECOURS, JAMAIS EN PREMIER : le jour ou le port s'ouvre, ou ou un vrai
        # service d'expedition est installe, rien ici ne change.
        #
        # LE VERROU D'IDENTITE NE SE CONTOURNE PAS. L'API envoie sous le compte du
        # jeton. Si ce compte n'est pas l'adresse de l'organisme, le message
        # partirait sous la mauvaise entite juridique — deux societes, deux
        # Qualiopi, deux responsabilites. On prefere l'echec franc au courrier
        # parti sous le mauvais nom.
        voulue = str(r.get("adresse") or "").strip().lower()
        compte = compte_google()
        if not voulue or not compte or voulue != compte:
            print("   (SMTP injoignable, et le secours est refuse : le compte Google "
                  "est « %s » pour une adresse d'organisme « %s »)"
                  % (compte or "inconnu", voulue or "inconnue"))
            raise
        print("   (SMTP injoignable : %s — envoi par l'API Google sous %s)"
              % (str(_e)[:70], compte))
        return _par_api(message)


def compte_google():
    """L'adresse du compte Google auquel le jeton donne acces. "" si inconnue.

    Lue une fois et gardee : elle ne change pas en cours d'execution, et
    l'interroger a chaque envoi ajouterait un appel reseau par destinataire.
    """
    global _COMPTE_GOOGLE
    if _COMPTE_GOOGLE is None:
        # PAR DRIVE, PAS PAR GMAIL. Le jeton porte « gmail.send » et rien de plus :
        # « users().getProfile » exige une permission de lecture que DFM n'a pas, et
        # echouait donc toujours — le verrou refusait alors tout envoi de secours.
        # « drive.about() » rend la meme adresse avec la permission deja accordee.
        _COMPTE_GOOGLE = ""
        for _lire in (_compte_par_drive, _compte_par_gmail):
            try:
                _COMPTE_GOOGLE = _lire()
            except Exception:
                _COMPTE_GOOGLE = ""
            if _COMPTE_GOOGLE:
                break
    return _COMPTE_GOOGLE


def _compte_par_drive():
    from connexion import service_drive
    return str((service_drive().about().get(fields="user(emailAddress)").execute()
                .get("user") or {}).get("emailAddress") or "").strip().lower()


def _compte_par_gmail():
    from connexion import service_gmail
    return str(service_gmail().users().getProfile(userId="me").execute()
               .get("emailAddress") or "").strip().lower()


_COMPTE_GOOGLE = None


def _par_api(message):
    """Le chemin d'origine, tant que le SMTP n'est pas installe."""
    import base64
    from connexion import service_gmail
    brut = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service_gmail().users().messages().send(
        userId="me", body={"raw": brut}).execute()
    return True


def essai(organisme=None, destinataire=""):
    """Envoie un message d'essai. Rend (reussi, explication).

    Sert a verifier l'installation SANS toucher a une vraie inscription : un
    reglage d'envoi ne se teste pas sur le courrier d'un client.
    """
    r = reglages(organisme)
    if not r:
        return False, ("Aucun mot de passe SMTP pour « %s ». L'envoi passe encore "
                       "par l'API Google." % (organisme or "l'organisme actif"))
    from email.mime.text import MIMEText
    from email.header import Header
    import profil
    p = profil.charger(r["organisme"]) or {}
    m = MIMEText("Cet essai confirme que DFM sait envoyer du courrier "
                 "par SMTP pour cet organisme.\n\n"
                 "Serveur : %s:%s\nExpediteur : %s\n"
                 % (r["serveur"], r["port"], r["adresse"]), "plain", "utf-8")
    m["Subject"] = str(Header("DFM — essai d'envoi", "utf-8"))
    m["From"] = str(Header(p.get("marque") or r["organisme"], "utf-8")) + \
                " <" + r["adresse"] + ">"
    m["To"] = (destinataire or r["adresse"]).strip()
    try:
        envoyer(m, r["organisme"])
        return True, "Essai parti a %s depuis %s." % (m["To"], r["adresse"])
    except smtplib.SMTPAuthenticationError:
        return False, ("Identifiant ou mot de passe refuse. Chez Gmail il faut un "
                       "MOT DE PASSE D'APPLICATION, pas le mot de passe du compte, "
                       "et la validation en deux etapes doit etre active.")
    except Exception as e:
        return False, "Envoi impossible : %s" % str(e)[:200]


def etat():
    """Ou en est l'installation, organisme par organisme."""
    import profil
    sortie = []
    try:
        liste = [p["id"] if isinstance(p, dict) else p for p in profil.lister()]
    except Exception:
        liste = []
    for org in liste:
        r = reglages(org)
        p = profil.charger(org) or {}
        sortie.append({"organisme": org,
                       "marque": p.get("marque") or org,
                       "smtp": bool(r),
                       "serveur": r.get("serveur", ""),
                       "adresse": r.get("adresse", p.get("mail_contact") or ""),
                       "par": "SMTP" if r else "API Google"})
    return sortie


# --------------------------------------------------------------------------
# TROUVER LE SERVEUR D'ENVOI TOUT SEUL
#
# « Demandez a votre hebergeur son serveur SMTP » est un aveu d'impuissance :
# celui qui ne connait rien ne sait pas ou chercher, ni quoi demander, ni
# reconnaitre la reponse. Or l'information est PUBLIQUE et deductible.
#
# DEUX PISTES, dans cet ordre :
#   1. Les enregistrements MX du domaine disent QUI heberge le courrier.
#      « mx1.ovh.net » -> OVH, « aspmx.l.google.com » -> Google Workspace.
#   2. A defaut, les conventions : smtp.<domaine>, mail.<domaine>.
#
# ET ON VERIFIE. Chaque candidat est teste par une vraie connexion : proposer
# une adresse qui ne repond pas ferait echouer l'envoi en laissant croire que
# le mot de passe est faux — exactement le piege qu'on veut eviter.
# --------------------------------------------------------------------------

# Ce qu'on lit dans un enregistrement MX, et le serveur d'envoi correspondant.
_MX_VERS_SMTP = [
    ("google.com",      "smtp.gmail.com",         "Google Workspace"),
    ("googlemail.com",  "smtp.gmail.com",         "Google Workspace"),
    ("ovh.net",         "ssl0.ovh.net",           "OVH"),
    ("ovh.com",         "ssl0.ovh.net",           "OVH"),
    ("gandi.net",       "mail.gandi.net",         "Gandi"),
    ("outlook.com",     "smtp.office365.com",     "Microsoft 365"),
    ("protection.outlook.com", "smtp.office365.com", "Microsoft 365"),
    ("infomaniak.ch",   "mail.infomaniak.com",    "Infomaniak"),
    ("infomaniak.com",  "mail.infomaniak.com",    "Infomaniak"),
    ("ionos.fr",        "smtp.ionos.fr",          "IONOS"),
    ("ionos.com",       "smtp.ionos.com",         "IONOS"),
    ("1and1.fr",        "smtp.ionos.fr",          "IONOS"),
    ("o2switch.net",    "mail.o2switch.net",      "o2switch"),
    ("lws.fr",          "mail.lws-hosting.com",   "LWS"),
    ("hostinger.com",   "smtp.hostinger.com",     "Hostinger"),
    ("zoho.com",        "smtp.zoho.eu",           "Zoho"),
    ("zoho.eu",         "smtp.zoho.eu",           "Zoho"),
    ("mailo.com",       "mail.mailo.com",         "Mailo"),
]


def _mx(domaine):
    """Les serveurs de courrier declares par le domaine. [] si rien."""
    import subprocess
    try:
        r = subprocess.run(["dig", "+short", "+time=3", "+tries=1", "MX", domaine],
                           capture_output=True, text=True, timeout=8)
    except Exception:
        return []
    sortie = []
    for l in (r.stdout or "").splitlines():
        bouts = l.strip().rstrip(".").split()
        if len(bouts) == 2 and bouts[0].isdigit():
            sortie.append((int(bouts[0]), bouts[1].lower()))
    return [h for _p, h in sorted(sortie)]


def _repond(hote, port=587, delai=5):
    """Un serveur SMTP repond-il vraiment a cette adresse ?"""
    try:
        with smtplib.SMTP(hote, port, timeout=delai) as s:
            s.ehlo()
            return True
    except Exception:
        return False


def chercher_serveur(adresse):
    """Cherche le serveur d'envoi d'une adresse. Rend un dictionnaire.

    {trouve, serveur, port, hebergeur, comment} — « comment » explique d'ou
    vient la reponse, parce qu'une trouvaille inexpliquee ne se verifie pas.
    """
    domaine = str(adresse or "").split("@")[-1].strip().lower()
    if not domaine or "." not in domaine:
        return {"trouve": False, "serveur": "", "port": 587, "hebergeur": "",
                "comment": "Adresse incomplète."}

    connu = deviner(adresse)
    if connu.get("connu"):
        return {"trouve": True, "serveur": connu["serveur"], "port": connu["port"],
                "hebergeur": connu["nom"],
                "comment": "Fournisseur reconnu à l'adresse."}

    # 1. QUI heberge le courrier de ce domaine ?
    for hote in _mx(domaine):
        for motif, smtp_, nom in _MX_VERS_SMTP:
            if hote.endswith(motif):
                if _repond(smtp_):
                    return {"trouve": True, "serveur": smtp_, "port": 587,
                            "hebergeur": nom,
                            "comment": "Votre domaine confie son courrier à %s." % nom}
                return {"trouve": True, "serveur": smtp_, "port": 587,
                        "hebergeur": nom,
                        "comment": "Votre domaine confie son courrier à %s "
                                   "(serveur non joignable d'ici, à essayer)." % nom}

    # 2. Les conventions, verifiees une par une.
    for prefixe in ("smtp.", "mail.", "ssl0.", ""):
        hote = prefixe + domaine
        if _repond(hote):
            return {"trouve": True, "serveur": hote, "port": 587, "hebergeur": "",
                    "comment": "Trouvé en interrogeant « %s » : il répond." % hote}

    return {"trouve": False, "serveur": "", "port": 587, "hebergeur": "",
            "comment": "Aucun serveur d'envoi n'a répondu pour « %s »." % domaine}
