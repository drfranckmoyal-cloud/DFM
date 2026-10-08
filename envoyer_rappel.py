from connexion import service_drive
from sessions import session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from datetime import datetime, date
import base64
import courrier
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "ce rappel reclamerait un reglement que le praticien ne doit pas.")
_MARQUE = S.get("marque") or S.get("organisme") or ""
_SIGNATURE = S.get("signature_mail") or S.get("formateur") or ""
JOURS_AVANT = 20
debut = datetime.strptime(S["date_debut"], "%Y-%m-%d").date()
reste = (debut - date.today()).days
print(f"-> Session : {S['nom_formation']} ({S['code']})")
print(f"-> Formation le {debut.strftime('%d/%m/%Y')}, dans {reste} jour(s).")
if reste > JOURS_AVANT:
    print(f"-> Trop tot (envoi a J-{JOURS_AVANT}). Rien a faire.")
    exit()
if reste < 0:
    print("-> La formation est passee. Rien a faire.")
    exit()
print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
concernes = [l for l in lignes if l["mail2_envoye_le"] and not l["rappel_le"]]
if not concernes:
    print("-> Aucun rappel a envoyer.")
    exit()
print(f"-> {len(concernes)} rappel(s) a envoyer.")
# La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
# ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
# au demarrage du script, meme quand aucun mail n'etait a envoyer.
#
# CELLE DU DRIVE A SUIVI LE 18/08/2026 : les pieces jointes passent par la
# couche « documents », qui les garde en cache. Elles partaient jusque-la
# telechargees a chaque envoi — et ont cesse de partir le jour ou
# l'autorisation Google est tombee.
logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
print("-> Telechargement des pieces jointes...")
pieces = []
# Le reglement interieur de l'organisme part avec la convocation, quelle que
# soit la session : l'indicateur 1 attend qu'il soit REMIS avant l'entree en
# formation, et un mail envoye en garde la trace. Il vient en premier, avant
# les articles a lire, parce que c'est la piece qui engage.
# Ajoute au debut de la liste plutot que dans pieces_rappel de chaque session :
# une piece qui vaut pour tout l'organisme n'a pas a etre recopiee session par
# session, ni a etre oubliee sur la prochaine.
_ids = []
_ri = str(S.get("reglement_interieur_id") or "").strip()
if _ri:
    _ids.append(_ri)
for _p in (S.get("pieces_rappel") or []):
    if _p and _p not in _ids:      # jamais deux fois la meme piece
        _ids.append(_p)
import documents as _doc
for pj_id in _ids:
    contenu = _doc.piece_par_ident(pj_id)
    if not contenu:
        # Une piece introuvable ne doit pas empecher la convocation de partir :
        # le stagiaire a besoin de ses horaires plus que de son PDF.
        print(f"   ! piece {pj_id} illisible, ignoree.")
        continue
    nom = _doc.nom_piece(pj_id) or ("piece-%s.pdf" % pj_id[:8])
    pieces.append((nom, contenu))
    print(f"   . {nom}")
compte = 0
for ligne in concernes:
    prenom = ligne["prenom"]
    nom_prenom = f"{prenom} {ligne['nom']}".strip()
    print(f"-> Envoi a {nom_prenom}...")
    bloc_reglement = ""
    if not ligne["paiement_recu_le"]:
        # PAS DE LIEN, PAS DE BOUTON — 04/10/2026. Ce bouton pointait vers
        # S['stripe_lien'] sans verifier qu'il existe : sur une session creee sans
        # lien de paiement — et rien ne permettait d'en ajouter un apres coup — le
        # praticien recevait un « Regler ma formation » qui ne menait nulle part.
        # Un bouton mort sur une demande d'argent est pire que pas de bouton ; le
        # virement juste en dessous, lui, fonctionne toujours.
        _lien_stripe = (S.get("stripe_lien") or "").strip()
        _bouton_stripe = ""
        if _lien_stripe:
            _bouton_stripe = (
                '    <div style="text-align:center;margin:16px 0;">\n'
                '      <a href="' + _lien_stripe + '" style="display:inline-block;'
                'background:#635BFF;color:#fff;padding:12px 26px;text-decoration:none;'
                'border-radius:6px;font-weight:600;font-size:14px;">'
                'R&eacute;gler ma formation</a>\n    </div>')
        bloc_reglement = f"""
  <div style="background:#fdf6ec;border:1px solid #f5dda6;border-radius:10px;padding:18px;margin:24px 0;">
    <p style="margin:0 0 12px;font-size:14px;"><strong>Ton r&egrave;glement ne nous est pas encore parvenu.</strong><br>
    Merci de le finaliser avant la formation ({S['tarif']} &euro;, d&eacute;jeuners inclus).</p>
{_bouton_stripe}
    <p style="margin:12px 0 6px;font-size:13px;"><strong>Ou par virement</strong> &mdash; motif : {S['nom_formation']} + Nom Pr&eacute;nom</p>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <tr><td style="padding:6px 9px;background:#fff;border:1px solid #f0e2c4;font-weight:600;width:90px;">Titulaire</td>
          <td style="padding:6px 9px;background:#fff;border:1px solid #f0e2c4;">{S.get('organisme') or ''}</td></tr>
      <tr><td style="padding:6px 9px;background:#fff;border:1px solid #f0e2c4;font-weight:600;">IBAN</td>
          <td style="padding:6px 9px;background:#fff;border:1px solid #f0e2c4;">{S.get('iban') or ''}</td></tr>
      <tr><td style="padding:6px 9px;background:#fff;border:1px solid #f0e2c4;font-weight:600;">BIC</td>
          <td style="padding:6px 9px;background:#fff;border:1px solid #f0e2c4;">{S.get('bic') or ''}</td></tr>
    </table>
    <p style="margin:11px 0 0;font-size:11px;color:#9a7a3f;font-style:italic;">Si c'est une erreur de notre part, n'h&eacute;site pas &agrave; nous le pr&eacute;ciser.</p>
  </div>"""
    import mails as _mails
    _modele = _mails.pour_formation(S.get("formation", ""), "rappel")
    _ctx = _mails.contexte(S, ligne, {"bloc_reglement": bloc_reglement})
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
    for nom_fichier, contenu in pieces:
        pj = MIMEApplication(contenu, _subtype="pdf")
        pj.add_header("Content-Disposition", "attachment", filename=nom_fichier)
        message.attach(pj)
    # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail. C'est
    # l'organisme DE LA SESSION qui decide d'ou part le mail : deux entites,
    # deux adresses, et un mail parti sous la mauvaise identite ne se rattrape pas.
    courrier.envoyer(message, __import__('sessions').organisme_de(CODE))
    suivi.marquer(ligne, "rappel_le", code=CODE, detail=ligne["mail"])
    print("   Rappel envoye et enregistre.")
    compte += 1
print(f"-> Termine : {compte} rappel(s) envoye(s).")
