from connexion import service_drive
from sessions import session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import base64
import urllib.parse
import sys
import courrier
import documents
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "seul le representant legal signe, il ne recoit pas ce mail.")
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
a_contacter = [l for l in lignes if suivi.calculer_statut(l) == "A contacter"]
if not a_contacter:
    print("-> Personne a contacter. Rien a faire.")
    exit()
print(f"-> {len(a_contacter)} praticien(s) a contacter :")
for l in a_contacter:
    print(f"   . {l['prenom']} {l['nom']} ({l['mail']})")
print("-> Lecture du programme et du logo...")
# LE PROGRAMME PASSE PAR LA COUCHE. C'est la piece la plus lourde de DFM —
# 5,44 Mo — et elle repartait du Drive a chaque execution. Elle est desormais
# lue en local ; seule sa date de modification est demandee au Drive.
programme_bytes = documents.piece("programme", CODE)
if not programme_bytes:
    print("   ATTENTION : programme introuvable. Les mails partiront sans.")
logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
for ligne in a_contacter:
    prenom = ligne["prenom"]
    nom_prenom = f"{prenom} {ligne['nom']}".strip()
    if ligne["promu_le"]:
        intro = f"""<p>Une place vient de se lib&eacute;rer pour la formation<br>
  &laquo; <strong>{S['titre_complet']}</strong> &raquo;, qui aura lieu le <strong>{S['date_texte']}</strong>.</p>
  <p>Tu &eacute;tais en file d'attente : <strong>nous te la proposons en priorit&eacute;</strong>.</p>"""
    else:
        intro = f"""<p>Merci pour ta demande d'inscription &agrave; la formation<br>
  &laquo; <strong>{S['titre_complet']}</strong> &raquo;,<br>
  qui aura lieu le <strong>{S['date_texte']}</strong>.</p>"""
    # LA CONVENTION PART EN PIECE JOINTE, comme le programme juste au-dessus.
    #
    # Elle voyageait avant sous forme de LIEN vers le Drive, affiche par la page
    # de signature en bouton « Lire ma convention avant de signer ». Ce lien
    # exigeait que le document soit lisible par n'importe qui en connaissant
    # l'adresse — un partage public sur une piece nominative. Les partages ont
    # ete retires le 16/08/2026, et le bouton menait depuis a une page d'erreur
    # Google : le praticien signait sans avoir pu lire.
    #
    # La piece jointe supprime le probleme au lieu de le deplacer : rien de
    # public, le signataire garde son exemplaire, et cela fonctionne meme si
    # Google est injoignable.
    convention_bytes = documents.lire(
        documents.reference(CODE, "convention", f"Convention a signer - {nom_prenom}.pdf"))
    if not convention_bytes:
        # NON BLOQUANT, mais dit franchement : le mail part, et le praticien
        # signera sans avoir lu. C'est a l'utilisateur de decider si ca passe.
        print("   ATTENTION : aucune convention preparee pour "
              f"{nom_prenom}. Lancez generer_convention_apercu.py,")
        print("   sinon cette personne signera sans avoir lu son engagement.")
    # La page de signature n'avait que le nom et la formation : dates, lieu et
    # montant y etaient ecrits en dur sur ceux d'Usures. Ils viennent desormais
    # de la fiche de session, comme tout le reste.
    params = urllib.parse.urlencode({
        # L'identite de l'organisme voyage AUSSI dans ce lien : le site de
        # signature sert les deux, et son en-tete etait ecrit en dur.
        "marque": S.get("marque") or "",
        "contact": S.get("mail_contact") or "", "tel": S.get("telephone_contact") or "",
        "praticien": nom_prenom, "session": S["code"],
        "formation": S.get("titre_complet") or S["nom_formation"],
        "dates": S.get("date_texte") or "",
        "lieu": S.get("adresse") or "",
        "montant": S.get("tarif") or "",
        # PLUS DE PARAMETRE « convention » : la page masque son bouton quand il
        # est absent — « un bouton mort serait pire que pas de bouton », dit son
        # propre commentaire. Le document est desormais dans le mail.
    })
    params_annul = urllib.parse.urlencode({"marque": S.get("marque") or "", "accroche": S.get("accroche_of") or "", "contact": S.get("mail_contact") or "", "tel": S.get("telephone_contact") or "", "praticien": nom_prenom, "formation": S.get("titre_complet") or S["nom_formation"], "session": S["code"], "debut": S["date_debut"]})
    lien_annulation = f"{S['url_signature']}/annulation.html?{params_annul}"
    lien_signature = f"{S['url_signature']}/?{params}"
    import mails as _mails
    _modele = _mails.pour_formation(S.get("formation", ""), "signature")
    _ctx = _mails.contexte(S, ligne, {"intro": intro, "lien_signature": lien_signature, "lien_annulation": lien_annulation})
    _rendu = _mails.rendre(_modele, _ctx, promu=bool(ligne.get("promu_le")))
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
    piece = MIMEApplication(programme_bytes, _subtype="pdf")
    piece.add_header("Content-Disposition", "attachment", filename=f"Programme {S['nom_formation']}.pdf")
    message.attach(piece)
    if convention_bytes:
        conv = MIMEApplication(convention_bytes, _subtype="pdf")
        conv.add_header("Content-Disposition", "attachment",
                        filename=f"Convention a signer - {nom_prenom}.pdf")
        message.attach(conv)
    print(f"-> Envoi a {nom_prenom}...")
    # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail. C'est
    # l'organisme DE LA SESSION qui decide d'ou part le mail : deux entites,
    # deux adresses, et un mail parti sous la mauvaise identite ne se rattrape pas.
    courrier.envoyer(message, _sessions.organisme_de(CODE))
    # Detail = destinataire : c'est ce qui permet de prouver a qui le mail est parti.
    suivi.marquer(ligne, "mail1_envoye_le", code=CODE, detail=ligne["mail"])
    print("   Envoye et enregistre dans le suivi.")
print(f"-> Termine : {len(a_contacter)} mail(s) envoye(s).")
