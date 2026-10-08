from connexion import service_drive
from sessions import session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
import courrier
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "sans formulaire, il n'y a pas de file d'attente.")
_MARQUE = S.get("marque") or S.get("organisme") or ""
_SIGNATURE = S.get("signature_mail") or S.get("formateur") or ""
print(f"-> Session : {S['nom_formation']} ({S['code']})")
print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
_ENCADRE_COMPLET = ("<div style=\"background:#fdf6ec; border:1px solid #f5dda6; border-radius:10px; padding:16px; margin:22px 0;\">"
  "<p style=\"margin:0; font-size:14px;\"><strong>Le nombre maximum de participants est atteint</strong> pour cette session. "
  "Ta demande est donc plac&eacute;e en <strong>file d'attente</strong>.</p></div>")
_ENCADRE_CLOS = ("<div style=\"background:#fdf6ec; border:1px solid #f5dda6; border-radius:10px; padding:16px; margin:22px 0;\">"
  "<p style=\"margin:0; font-size:14px;\"><strong>Les inscriptions &agrave; cette session sont cl&ocirc;tur&eacute;es.</strong> "
  "Ta demande est bien enregistr&eacute;e et plac&eacute;e en <strong>file d'attente</strong>.</p></div>")
_SUITE_COMPLET = ("<p>Concr&egrave;tement, ton inscription n'est pas encore valid&eacute;e, mais elle reste enregistr&eacute;e : "
  "en cas de d&eacute;sistement, nous te recontacterons en priorit&eacute; pour te proposer la place lib&eacute;r&eacute;e.</p>")
_SUITE_CLOS = ("<p>Concr&egrave;tement, ton inscription n'est pas valid&eacute;e &agrave; ce stade. "
  "Nous revenons vers toi rapidement : soit une place se lib&egrave;re sur cette session, "
  "soit nous te proposons la prochaine date.</p>")
def _statut_session():
    # L'ETAT VIENT DE LA BASE LOCALE, plus de deux cents lignes d'onglet Google.
    try:
        import sessions as _sess
        e = _sess.etat(S["code"])
        if e.get("terminee_le"):
            return "terminee"
        return e.get("statut_session") or "ouverte"
    except Exception:
        pass
    return "ouverte"
_STATUT = _statut_session()
_CLOTUREE = _STATUT in ("cloturee", "terminee")
_CONTACT = S.get("mail_contact") or ""
_ENCADRE = _ENCADRE_CLOS if _CLOTUREE else _ENCADRE_COMPLET
_SUITE = _SUITE_CLOS if _CLOTUREE else _SUITE_COMPLET
a_prevenir = [l for l in lignes if l["file_attente_le"] and not l["mail_attente_le"]
              and not l["annule_le"]]
if not a_prevenir:
    print("-> Personne a prevenir.")
    exit()
print(f"-> {len(a_prevenir)} personne(s) a prevenir.")
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
for ligne in a_prevenir:
    prenom = ligne["prenom"]
    nom_prenom = f"{prenom} {ligne['nom']}".strip()
    print(f"-> Envoi a {nom_prenom}...")
    import mails as _mails
    _modele = _mails.pour_formation(S.get("formation", ""), "attente")
    _ctx = _mails.contexte(S, ligne, {"encadre": _ENCADRE, "suite": _SUITE})
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
    # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail. C'est
    # l'organisme DE LA SESSION qui decide d'ou part le mail : deux entites,
    # deux adresses, et un mail parti sous la mauvaise identite ne se rattrape pas.
    courrier.envoyer(message, __import__('sessions').organisme_de(CODE))
    suivi.ecrire(ligne["_numero"], "mail_attente_le", suivi.aujourdhui(), CODE)
    # Ce script ecrit avec ecrire() et non marquer() : sans cet appel explicite,
    # « Mail file d'attente envoye » etait declare, avec sa phrase et son icone,
    # mais jamais produit. Neuvieme evenement muet, de la meme famille que C9.
    try:
        import journal as _j
        _j.ecrire("Mail file d'attente envoyé", nom_prenom, ligne["mail"], "", S["code"])
    except Exception:
        pass
    print("   Mail envoye.")
    compte += 1
print(f"-> Termine : {compte} mail(s) envoye(s).")
