from connexion import service_drive
from sessions import session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import base64
import urllib.parse
import courrier
import sys
import documents
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "ce mail porte la convention individuelle et le RIB du praticien.")
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
a_envoyer = [l for l in lignes if suivi.calculer_statut(l) == "Mail 2 a envoyer"]
if not a_envoyer:
    print("-> Aucun mail de confirmation a envoyer.")
    exit()
print(f"-> {len(a_envoyer)} mail(s) de confirmation a envoyer.")
print("-> Lecture des pieces communes...")
logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
# LE RIB ET LE PLAN D'ACCES PASSENT PAR LA COUCHE. Ils etaient retelecharges a
# chaque envoi ; ils sont desormais lus en local, et le Drive n'est interroge
# que sur leur DATE DE MODIFICATION — un Ko au lieu de six cent cinquante.
rib_bytes = documents.piece("rib", CODE)
acces_bytes = documents.piece("acces", CODE)
for _nom, _o in (("RIB", rib_bytes), ("plan d'acces", acces_bytes)):
    if not _o:
        print(f"   ATTENTION : {_nom} introuvable. Le mail partira sans.")
compte = 0
for ligne in a_envoyer:
    prenom = ligne["prenom"]
    nom_prenom = f"{prenom} {ligne['nom']}".strip()
    print(f"-> Traitement de {nom_prenom}...")
    params_annul = urllib.parse.urlencode({"marque": S.get("marque") or "", "accroche": S.get("accroche_of") or "", "contact": S.get("mail_contact") or "", "tel": S.get("telephone_contact") or "", "praticien": nom_prenom, "formation": S.get("titre_complet") or S["nom_formation"], "session": S["code"], "debut": S["date_debut"]})
    lien_annulation = f"{S['url_signature']}/annulation.html?{params_annul}"
    convention_bytes = None
    lien = ligne["lien_pdf"]
    if lien and "/d/" in lien:
        import documents
        convention_bytes = documents.depuis_lien(lien)
        print("   Convention recuperee.")
    else:
        print("   ATTENTION : lien du PDF absent. Mail sans la convention.")
    import mails as _mails
    _modele = _mails.pour_formation(S.get("formation", ""), "confirmation")
    _ctx = _mails.contexte(S, ligne, {"lien_annulation": lien_annulation})
    _rendu = _mails.rendre(_modele, _ctx, promu=False)
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
    if convention_bytes:
        pj_conv = MIMEApplication(convention_bytes, _subtype="pdf")
        pj_conv.add_header("Content-Disposition", "attachment", filename=f"Convention signee - {nom_prenom}.pdf")
        message.attach(pj_conv)
    pj_rib = MIMEApplication(rib_bytes, _subtype="pdf")
    pj_rib.add_header("Content-Disposition", "attachment", filename=f"RIB - {S.get('organisme') or 'organisme'}.pdf")
    message.attach(pj_rib)
    pj_acces = MIMEApplication(acces_bytes, _subtype="pdf")
    pj_acces.add_header("Content-Disposition", "attachment", filename="Informations d'acces.pdf")
    message.attach(pj_acces)
    # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail. C'est
    # l'organisme DE LA SESSION qui decide d'ou part le mail : deux entites,
    # deux adresses, et un mail parti sous la mauvaise identite ne se rattrape pas.
    courrier.envoyer(message, __import__('sessions').organisme_de(CODE))
    suivi.marquer(ligne, "mail2_envoye_le", code=CODE, detail=ligne["mail"])
    print("   Mail envoye et enregistre dans le suivi.")
    compte += 1
print(f"-> Termine : {compte} mail(s) de confirmation envoye(s).")
