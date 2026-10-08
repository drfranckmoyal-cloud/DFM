"""Envoi de la convention client au representant legal, pour signature en ligne.

UN SEUL MAIL, a UNE SEULE adresse : celle du client. Les praticiens ne recoivent
rien — ils ne signent pas, ils se forment.

    python3 envoyer_mail_signature_client.py <code_session>

LE LIEN DE SIGNATURE est celui des sessions individuelles, avec le representant
legal a la place du praticien. La page affiche deja la marque, les dates, le
lieu et le montant depuis l'adresse : rien de nouveau a construire cote site.
Le MONTANT transmis est le TOTAL, pas le tarif unitaire — c'est ce que le
centre s'engage a regler.

CE SCRIPT NE MARQUE RIEN DANS LE SUIVI. Les colonnes du suivi decrivent un
parcours individuel ; l'envoi d'une convention collective n'y a pas sa place.
La trace est dans le journal, rattachee a la session.
"""
import base64
import sys
import urllib.parse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from connexion import service_drive
from sessions import session, est_client, client_de
import documents
import suivi
import mails

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CODE = ARGS[0] if ARGS else None
FORCER = "--forcer" in sys.argv
S = session(CODE)
print(f"-> Session : {S['nom_formation']} ({S['code']})")

if not est_client(CODE):
    print("-> Session individuelle : chaque praticien recoit la sienne.")
    raise SystemExit(0)

import clients as CL
cl = CL.client(client_de(CODE)) or {}
if not cl:
    print("-> Client introuvable dans la base. Rien n'est envoye.")
    raise SystemExit(0)
if not (cl.get("mail") or "").strip():
    print("-> Le client n'a pas d'adresse mail : la convention ne peut pas partir.")
    print("   Completez sa fiche dans la Base clients.")
    raise SystemExit(0)

lignes = [l for l in suivi.lire_lignes_de(CODE) if not l["annule_le"]]
if not lignes:
    print("-> Aucun apprenant saisi. Rien n'est envoye.")
    raise SystemExit(0)

try:
    total = float(str(S.get("tarif") or 0).replace(",", ".").replace(" ", "")) * len(lignes)
except ValueError:
    total = 0.0

# IDEMPOTENCE. Ce script tourne a CHAQUE passage du pipeline, et le pipeline
# traite TOUTES les sessions (dfm.py). Sans garde, le centre recevait sa
# convention une fois de plus a chaque execution — c'est ainsi qu'un client a
# recu deux mails, l'un de DSF l'autre de Smileclub, pour deux sessions
# distinctes portant le meme client.
#
# Le parcours individuel se protege par les colonnes du suivi. Ici la trace vit
# sur la fiche de session : les colonnes du suivi decrivent un parcours
# individuel, une convention collective n'y a pas sa place.
#
# L'EMPREINTE retient ce qui change le document : le nombre de participants et
# le montant. Si l'un des deux bouge — un praticien ajoute apres coup — la
# convention n'est plus la meme et doit repartir. Un renvoi volontaire reste
# possible avec --forcer.
import sessions as _S
_BRUTES = _S._charger_json(_S._FICHIER_S)
_fiche_brute = dict(_BRUTES.get(CODE) or {})
empreinte = "%d participant(s), %.0f EUR" % (len(lignes), total)
envoyee_le = str(_fiche_brute.get("convention_client_envoyee_le") or "").strip()
if envoyee_le and not FORCER:
    if _fiche_brute.get("convention_client_empreinte") == empreinte:
        print("-> Convention deja envoyee le %s (%s)." % (envoyee_le, empreinte))
        print("   Rien n'est renvoye. Pour un renvoi volontaire : --forcer")
        raise SystemExit(0)
    print("-> Deja envoyee le %s, mais la convention a change :" % envoyee_le)
    print("   avant %s -> maintenant %s. Nouvel envoi."
          % (_fiche_brute.get("convention_client_empreinte") or "?", empreinte))

# LA LIGNE « drive = service_drive() » A ETE RETIREE LE 18/08/2026. Elle
# ouvrait une session Google au demarrage du script SANS QUE LA VARIABLE SOIT
# JAMAIS RELUE — meme reliquat que la connexion Gmail retiree avant elle.
# Consequence, le jour ou l'autorisation a ete revoquee : le script mourait
# a son chargement, avant meme de savoir s'il avait quelque chose a faire.

# LA CONVENTION PART EN PIECE JOINTE, comme le programme.
#
# Elle voyageait avant sous forme de LIEN vers le Drive, que la page de
# signature affichait en bouton « Lire ma convention avant de signer ». Ce lien
# supposait le document lisible par quiconque en connaissait l'adresse. Les
# partages publics ont ete retires le 16/08/2026 et le bouton menait depuis a
# une page d'erreur Google : le representant legal signait sans avoir pu lire.
#
# La piece jointe supprime le probleme au lieu de le deplacer.
cible = "Convention - " + (cl.get("raison_sociale") or "client") + ".pdf"
convention_bytes = documents.lire(documents.reference(CODE, "convention", cible))
if not convention_bytes:
    print("   ATTENTION : aucune convention preparee. Lancez d'abord")
    print("   generer_convention_client.py, sinon le centre signera sans avoir lu.")

# Ce n'est PAS un praticien qui signe : c'est la structure, par son representant.
# Le site affichait « Praticien » en dur — juste pour les sessions individuelles,
# faux ici. Le libelle voyage donc dans le lien, comme la marque et le contact.
signataire = (cl.get("raison_sociale") or "").strip()
params = urllib.parse.urlencode({
    "marque": S.get("marque") or "", "contact": S.get("mail_contact") or "",
    "tel": S.get("telephone_contact") or "", "libelle": "Client",
    "praticien": signataire, "session": S["code"],
    "formation": S.get("titre_complet") or S["nom_formation"],
    "dates": S.get("date_texte") or "", "lieu": S.get("adresse") or "",
    "montant": f"{total:.0f}",
    # PLUS DE PARAMETRE « convention » : sans lui, la page masque son bouton.
    # Le document est dans le mail.
})
lien = S["url_signature"] + "/?" + params

nb = len(lignes)
corps = f"""<p><strong>Bonjour,</strong></p>
<p>Nous vous remercions de votre confiance pour la formation<br>
&laquo;&nbsp;<strong>{S.get('titre_complet') or S['nom_formation']}</strong>&nbsp;&raquo;,
qui aura lieu le <strong>{S.get('date_texte') or ''}</strong>.</p>
<p>Vous trouverez ci-joint le programme. La convention de formation
professionnelle etablie au nom de <strong>{cl.get('raison_sociale')}</strong> porte sur
<strong>{nb} participant{'s' if nb > 1 else ''}</strong>, pour un montant total de
<strong>{total:.0f}&nbsp;&euro; TTC</strong>.</p>
<p>Pour la valider, il vous suffit de la signer en ligne, en un clic :</p>
<div style="text-align:center; margin: 28px 0;">
  <a href="{lien}" style="display:inline-block; background:#0f9e6a; color:#fff;
     padding:14px 32px; text-decoration:none; border-radius:8px; font-weight:600;
     font-size:15px;">Signer la convention</a>
</div>
<p style="font-size:13px; color:#5b6172;">La signature est effectuee par le representant
legal de la structure. Vous pouvez consulter le document avant de signer.</p>
<p>Pour toute question, repondez simplement a ce message.</p>
<p style="margin-top:24px;">Bien a vous,<br>
<strong>{S.get('signature_mail') or S.get('formateur') or ''}, {S.get('marque') or ''}</strong></p>"""

html = mails.ENVELOPPE.replace("{CORPS}", corps).replace("{{marque}}", S.get("marque") or "")
logo_bytes = None
try:
    logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    html = mails.poser_logo(html, logo_bytes)
except Exception:
    pass

message = MIMEMultipart("related")
message["To"] = cl["mail"]
message["Subject"] = "Convention de formation à signer - " + (S.get("titre_complet") or S["nom_formation"])
expediteur = mails.expediteur(S)
if expediteur:
    message["From"] = expediteur
corps_mime = MIMEMultipart("alternative")
corps_mime.attach(MIMEText(html, "html"))
message.attach(corps_mime)
if logo_bytes:
    logo = MIMEImage(logo_bytes)
    logo.add_header("Content-ID", "<logo>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    message.attach(logo)
# LE PROGRAMME PASSE PAR LA COUCHE, comme dans le parcours individuel : lu en
# local, le Drive n'etant interroge que sur sa date de modification.
programme = documents.piece("programme", CODE)
if programme:
    pj = MIMEApplication(programme, _subtype="pdf")
    pj.add_header("Content-Disposition", "attachment",
                  filename=f"Programme {S['nom_formation']}.pdf")
    message.attach(pj)
else:
    print("   (programme non joint : introuvable)")
if convention_bytes:
    conv = MIMEApplication(convention_bytes, _subtype="pdf")
    conv.add_header("Content-Disposition", "attachment", filename=cible)
    message.attach(conv)

print(f"-> Envoi a {cl['mail']} ({signataire})...")
# L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session decide
# d'ou part le mail : c'est le meme cloisonnement que pour les documents.
import courrier
import sessions as _s_org
courrier.envoyer(message, _s_org.organisme_de(CODE))
print(f"   Envoye. {nb} participant(s), {total:.0f} EUR.")

# La trace, ecrite APRES l'envoi : si Gmail refuse, rien n'est note et le
# prochain passage reessaiera. On ne recopie jamais une fiche vide par-dessus
# une fiche existante — d'ou le test sur _fiche_brute.
if _fiche_brute:
    _fiche_brute["convention_client_envoyee_le"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    _fiche_brute["convention_client_empreinte"] = empreinte
    _S.enregistrer_session(CODE, _fiche_brute)
    print("   Trace ecrite : cette convention ne repartira pas toute seule.")
else:
    print("   ATTENTION : fiche de session introuvable, la trace n'a pas ete ecrite.")

try:
    import journal
    journal.ecrire("Convention client envoyée", cl.get("raison_sociale") or "",
                   f"{cl['mail']} — {nb} participant(s), {total:.0f} EUR", "", S["code"])
except Exception:
    pass
raise SystemExit(0)
