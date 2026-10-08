from connexion import service_drive
from sessions import session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import base64
import courrier
import sys
import suivi
import journal
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "la facture part au client, pas a chaque praticien.")
_MARQUE = S.get("marque") or S.get("organisme") or ""
_SIGNATURE = S.get("signature_mail") or S.get("formateur") or ""
# LA LIGNE « drive = service_drive() » A ETE RETIREE LE 18/08/2026. Elle
# ouvrait une session Google au demarrage du script SANS QUE LA VARIABLE SOIT
# JAMAIS RELUE — meme reliquat que la connexion Gmail retiree avant elle.
# Consequence, le jour ou l'autorisation a ete revoquee : le script mourait
# a son chargement, avant meme de savoir s'il avait quelque chose a faire.
# La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
# ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
# au demarrage du script, meme quand aucun mail n'etait a envoyer.
print(f"-> Session : {S['nom_formation']} ({S['code']})")
print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
a_envoyer = [l for l in lignes if l["facture_le"] and l["lien_facture"] and not l["facture_envoyee_le"]]
a_envoyer = [l for l in a_envoyer if "/d/" in l["lien_facture"]]
if not a_envoyer:
    print("-> Aucune facture a envoyer.")
    exit()
print(f"-> {len(a_envoyer)} facture(s) a envoyer.")
logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
compte = 0
for ligne in a_envoyer:
    prenom = ligne["prenom"]
    nom_prenom = f"{prenom} {ligne['nom']}".strip()
    print(f"-> Envoi a {nom_prenom}...")
    # Le local d'abord, l'ancienne adresse Drive en repli.
    import documents
    facture_bytes = documents.depuis_lien(ligne["lien_facture"])
    if not facture_bytes:
        print("   Facture introuvable, ni en local ni dans le Drive.")
        continue
    import mails as _mails
    _modele = _mails.pour_formation(S.get("formation", ""), "facture")
    _ctx = _mails.contexte(S, ligne, {})
    _rendu = _mails.rendre(_modele, _ctx)
    html = _rendu["html"]
    # Dimensions du logo lues dans le fichier et posees en HTML ET en CSS :
    # sans elles, Outlook affiche l'image a sa taille reelle et Gmail mobile
    # l'etire. Voir mails.poser_logo.
    html = _mails.poser_logo(html, logo_bytes)
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    import mails as _m_exp
    _exp = _m_exp.expediteur(S if "S" in dir() else None)
    if _exp:
        message["From"] = _exp
    message["Subject"] = _rendu["objet"]
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(html, "html"))
    message.attach(corps)
    logo = MIMEImage(logo_bytes)
    logo.add_header("Content-ID", "<logo>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    message.attach(logo)
    pj = MIMEApplication(facture_bytes, _subtype="pdf")
    pj.add_header("Content-Disposition", "attachment", filename=f"Facture - {nom_prenom}.pdf")
    message.attach(pj)
    # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail. C'est
    # l'organisme DE LA SESSION qui decide d'ou part le mail : deux entites,
    # deux adresses, et un mail parti sous la mauvaise identite ne se rattrape pas.
    courrier.envoyer(message, __import__('sessions').organisme_de(CODE))
    suivi.ecrire(ligne["_numero"], "facture_envoyee_le", suivi.aujourdhui(), CODE)
    try:
        qui = (ligne["prenom"] or "").strip() + " " + (ligne["nom"] or "").strip().upper()
        journal.ecrire("Facture envoyée", qui.strip(), ligne["mail"], "", S["code"])
    except Exception:
        pass
    print("   Facture envoyee.")
    compte += 1
print(f"-> Termine : {compte} facture(s) envoyee(s).")
