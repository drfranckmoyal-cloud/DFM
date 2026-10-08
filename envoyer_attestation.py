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
# Liste de destinataires transmise par la fenetre de validation de l'interface.
CIBLES = [m.strip().lower() for m in (sys.argv[2].split(",") if len(sys.argv) > 2 else []) if m.strip()]
S = session(CODE)
_MARQUE = S.get("marque") or S.get("organisme") or ""
_SIGNATURE = S.get("signature_mail") or S.get("formateur") or ""
print(f"-> Session : {S['nom_formation']} ({S['code']})")
print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
a_envoyer = [l for l in lignes if l["lien_attestation"] and "/d/" in l["lien_attestation"]]
if CIBLES:
    # Selection explicite depuis l'interface : on honore le choix, meme si
    # l'attestation a deja ete envoyee. C'est un renvoi volontaire.
    a_envoyer = [l for l in a_envoyer if (l["mail"] or "").strip().lower() in CIBLES]
else:
    a_envoyer = [l for l in a_envoyer if not l["attestation_envoyee_le"]]
if not a_envoyer:
    print("-> Aucune attestation a envoyer.")
    exit()
print(f"-> {len(a_envoyer)} attestation(s) a envoyer.")
# LA LIGNE « drive = service_drive() » A ETE RETIREE LE 18/08/2026. Elle
# ouvrait une session Google au demarrage du script SANS QUE LA VARIABLE SOIT
# JAMAIS RELUE — meme reliquat que la connexion Gmail retiree avant elle.
# Consequence, le jour ou l'autorisation a ete revoquee : le script mourait
# a son chargement, avant meme de savoir s'il avait quelque chose a faire.
# La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
# ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
# au demarrage du script, meme quand aucun mail n'etait a envoyer.
logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
compte = 0
for ligne in a_envoyer:
    prenom = ligne["prenom"]
    nom_prenom = f"{prenom} {ligne['nom']}".strip()
    print(f"-> Envoi a {nom_prenom}...")
    # LE LOCAL D'ABORD, l'ancienne adresse Drive en repli : les attestations
    # emises avant la couche « documents » n'ont pas de copie locale.
    import documents
    _nom = f"Attestation - {nom_prenom}.pdf"
    attestation_bytes = documents.lire(documents.reference(CODE, "attestation", _nom)) \
        or documents.depuis_lien(ligne["lien_attestation"])
    if not attestation_bytes:
        print("   Attestation introuvable, ni en local ni dans le Drive.")
        continue
    import mails as _mails
    _modele = _mails.pour_formation(S.get("formation", ""), "attestation")
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
    pj = MIMEApplication(attestation_bytes, _subtype="pdf")
    pj.add_header("Content-Disposition", "attachment", filename=f"Attestation - {nom_prenom}.pdf")
    message.attach(pj)
    # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail. C'est
    # l'organisme DE LA SESSION qui decide d'ou part le mail : deux entites,
    # deux adresses, et un mail parti sous la mauvaise identite ne se rattrape pas.
    courrier.envoyer(message, __import__('sessions').organisme_de(CODE))
    suivi.ecrire(ligne["_numero"], "attestation_envoyee_le", suivi.aujourdhui(), CODE)
    try:
        qui = (ligne["prenom"] or "").strip() + " " + (ligne["nom"] or "").strip().upper()
        journal.ecrire("Attestation envoyée", qui.strip(), ligne["mail"], "", S["code"])
    except Exception:
        pass
    print("   Attestation envoyee.")
    compte += 1
print(f"-> Termine : {compte} attestation(s) envoyee(s).")
