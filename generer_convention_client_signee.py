"""Convention CLIENT signee : le document contresigne, renvoye au centre.

    python3 generer_convention_client_signee.py <code_session>

UN SEUL DOCUMENT, comme la convention d'origine : la signature apposee est
celle du representant legal, pas celle d'un praticien. Le PDF est range dans
les conventions SIGNEES de l'organisme, puis envoye au client par mail.

CE QUI DECLENCHE : la trace posee par relever_signature_client.py. Sans
signature relevee, ce script ne fait rien. Il ne va pas interroger Supabase
lui-meme pour savoir SI le client a signe — c'est le role de la relevee, et
deux endroits qui decident la meme chose finissent par se contredire.

IDEMPOTENT : la trace « convention_client_signee_envoyee_le » empeche le
renvoi a chaque passage du pipeline, comme pour la convention initiale.

NON BLOQUANT : un echec ici ne doit pas arreter le pipeline.
"""
import base64
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from googleapiclient.http import MediaInMemoryUpload

from connexion import service_drive
import convention
from sessions import session, balises_identite, est_client, client_de, cle_nom, date_fr
import config
import suivi
import mails
import dossiers

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CODE = ARGS[0] if ARGS else None
FORCER = "--forcer" in sys.argv
S = session(CODE)
print(f"-> Session : {S['nom_formation']} ({S['code']})")

if not est_client(CODE):
    print("-> Session individuelle : chaque praticien a sa propre convention signee.")
    raise SystemExit(0)

import sessions as _S
_BRUTES = _S._charger_json(_S._FICHIER_S)
_fiche_brute = dict(_BRUTES.get(CODE) or {})

signee_le = str(_fiche_brute.get("convention_client_signee_le") or "").strip()
if not signee_le:
    print("-> Le client n'a pas encore signe. Rien a editer.")
    raise SystemExit(0)

deja = str(_fiche_brute.get("convention_client_signee_envoyee_le") or "").strip()
if deja and not FORCER:
    print(f"-> Convention signee deja envoyee le {deja}. Rien n'est renvoye.")
    print("   Pour un renvoi volontaire : --forcer")
    raise SystemExit(0)

import clients as CL
fiche_client = CL.client(client_de(CODE)) or {}
raison = (fiche_client.get("raison_sociale") or "").strip()
if not raison:
    print("-> Client introuvable ou sans raison sociale. Rien a editer.")
    raise SystemExit(0)

manques = CL.complet(fiche_client)
if manques:
    print("-> Fiche client incomplete : " + ", ".join(manques))
    raise SystemExit(0)

lignes = [l for l in suivi.lire_lignes_de(CODE) if not l["annule_le"]]
if not lignes:
    print("-> Aucun participant. Convention non editee.")
    raise SystemExit(0)

# MEME REGLE QU'A L'EDITION : la contresignature ne rattrape pas une fonction
# manquante en l'inventant.
_sans = [(l["prenom"] + " " + l["nom"]).strip()
         for l in lignes if not (l.get("fonction") or "").strip()]
if _sans:
    print("-> Fonction manquante pour : %s" % ", ".join(_sans[:6]))
    print("   La convention contresignee n'est pas editee.")
    raise SystemExit(0)
participants = [((l["prenom"] + " " + l["nom"]).strip(),
                 (l.get("fonction") or "").strip())
                for l in lignes]
try:
    unitaire = float(str(S.get("tarif") or 0).replace(",", ".").replace(" ", ""))
except ValueError:
    unitaire = 0.0
total = unitaire * len(participants)
print(f"-> {len(participants)} participant(s), {total:.0f} EUR. Signee le {signee_le}.")


# LA LIGNE « drive = service_drive() » A ETE RETIREE LE 18/08/2026. Elle
# ouvrait une session Google au demarrage du script SANS QUE LA VARIABLE SOIT
# JAMAIS RELUE — meme reliquat que la connexion Gmail retiree avant elle.
# Consequence, le jour ou l'autorisation a ete revoquee : le script mourait
# a son chargement, avant meme de savoir s'il avait quelque chose a faire.

# L'IMAGE DE SIGNATURE, reprise dans Supabase. On la retrouve par le meme
# rapprochement normalise que la relevee : casse, accents et parentheses ne
# doivent pas empecher de reconnaitre le signataire.
from supabase import create_client
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
_formes = [f for f in dict.fromkeys([S.get("nom_formation") or "",
                                     S.get("titre_complet") or ""]) if f]
reponse = supabase.table("Signatures").select("*").in_(
    "formation", _formes).order("created_at", desc=True).execute()
attendue = cle_nom(raison)
import preuves
# TRI PAR SESSION : une signature portant le code d'une AUTRE session est
# ecartee. « Usures » est dispensee par les deux organismes, et le nom de
# formation ne suffisait pas a distinguer les dossiers.
_classees = preuves.par_session(reponse.data, CODE)
trouvees = [x for x in _classees if cle_nom(x.get("praticien")) == attendue]
if not trouvees:
    print("-> Signature introuvable dans Supabase alors que la fiche la dit posee.")
    print("   La trace et la base divergent : rien n'est edite.")
    raise SystemExit(0)

# LA SIGNATURE ARRIVE DEJA EN « data: » depuis Supabase. L'ancien script la
# deposait dans le Drive PUIS la rendait publique, uniquement pour qu'un Google
# Docs puisse l'afficher : deux appels reseau et un fichier expose, pour une
# image qu'on avait sous la main. En HTML elle s'insere telle quelle.
_signature = (trouvees[0].get("signature_images") or "").strip()
if not _signature.startswith("data:"):
    print("-> La signature relevee n'est pas une image exploitable. Rien n'est edite.")
    raise SystemExit(0)

try:
    contenu, souci = convention.fabriquer(CODE, signature_client=_signature)
    if not contenu:
        print("-> " + souci)
        raise SystemExit(0)
except SystemExit:
    raise
except Exception as e:
    print("   ECHEC de la fabrication : %s" % str(e)[:160], file=sys.stderr)
    raise SystemExit(0)

pdf = contenu
try:

    # Rangement dans les conventions SIGNEES de l'organisme de la session.
    # Le rangement passe par la couche « documents » : elle connait le
    # sous-dossier « -PDF » des conventions signees, et pousse la copie.
    import documents
    cible = "Convention SIGNEE - " + raison + ".pdf"
    ref, lien, _souci = documents.ranger(CODE, "convention_signee", cible, pdf)
    if not ref:
        print("   ECHEC : " + _souci, file=sys.stderr)
        raise SystemExit(0)
    print("-> Convention signee prete : " + lien)

    # ENVOI AU CENTRE, avec le PDF en piece jointe : le client doit conserver
    # son exemplaire sans dependre d'un lien Drive.
    # LA FACTURE, recuperee avant de composer le mail. Elle est editee par
    # generer_facture_client.py, qui tourne juste avant dans le pipeline.
    #
    # SI ELLE MANQUE, ON N'ENVOIE RIEN. Un mail annoncant une facture absente
    # obligerait a un second envoi et brouillerait le dossier du centre. Comme
    # aucune trace n'est ecrite, le passage suivant reprendra les deux pieces
    # ensemble — c'est le comportement voulu, pas un abandon.
    _facture_num = str(_fiche_brute.get("facture_client_numero") or "").strip()
    _facture_lien = str(_fiche_brute.get("facture_client_lien") or "").strip()
    _facture_pdf, _facture_nom = None, ""
    if _facture_num and _facture_lien:
        _facture_nom = "Facture %s - %s.pdf" % (_facture_num, raison)
        # LA FACTURE VIENT DE LA COUCHE. On tente d'abord le rangement local
        # par sa reference ; le lien Drive ne sert que pour les factures
        # emises AVANT ce module.
        _facture_pdf = documents.lire(
            documents.reference(CODE, "facture", _facture_nom))
        if not _facture_pdf:
            _facture_pdf = documents.depuis_lien(_facture_lien)
        if not _facture_pdf:
            print("   Facture %s introuvable, ni en local ni dans le Drive." % _facture_num)
    if not _facture_pdf:
        print("-> Facture absente : le mail ne part pas.")
        print("   Lancez generer_facture_client.py, puis relancez celui-ci.")
        print("   (aucune trace ecrite : le prochain passage reprendra les deux pieces)")
        raise SystemExit(0)

    adresse = (fiche_client.get("mail") or "").strip()
    if not adresse:
        print("   Le client n'a pas d'adresse mail : le document reste sur le Drive.")
    else:
        # LA VOIE DE RECLAMATION MANQUAIT AU CLIENT. Constate le 23/08/2026 :
        # seul le mail d'attestation la portait, donc seuls les APPRENANTS la
        # recevaient. Le centre qui signe et qui paie — un beneficiaire au sens
        # de l'indicateur 31 — ne la voyait nulle part.
        #
        # Elle part avec la contresignature parce que c'est le mail qui CLOT
        # l'engagement : le moment ou le client sait ce qu'il a achete, ce qu'il
        # doit, et desormais comment se plaindre.
        try:
            import reclamations as _rec
            _lien_rec = _rec.lien(contact_ligne={
                "nom": S.get("client_representant") or "",
                "mail": adresse,
                "_session": S.get("code") or ""})
        except Exception:
            _lien_rec = ""
        _delai_rec = str(S.get("reclamations_delai") or "").strip() or "15"
        # SANS LIEN, PAS D'ENCADRE. Un bouton « Adresser une reclamation » qui ne
        # mene nulle part serait pire que son absence.
        _bloc_reclamation = ("" if not _lien_rec else (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"'
            ' style="margin:22px 0 0;border:1px solid #dfe3ec;border-radius:9px;background:#f7f8fb">'
            '<tr><td style="padding:15px 18px">'
            '<p style="margin:0 0 7px;font-size:15px;font-weight:bold;color:#1a1d2e">'
            'Une remarque sur cette formation&nbsp;?</p>'
            '<p style="margin:0 0 12px;font-size:14px;line-height:1.55;color:#3d4250">'
            'Dites-le-nous&nbsp;: nous accusons r&eacute;ception et vous r&eacute;pondons sous '
            '<strong>' + _delai_rec + ' jours</strong>.</p>'
            '<p style="margin:0"><a href="' + _lien_rec + '"'
            ' style="display:inline-block;background:#4f7ef8;color:#ffffff;text-decoration:none;'
            'font-size:14px;font-weight:bold;padding:10px 20px;border-radius:7px">'
            'Adresser une r&eacute;clamation</a></p>'
            '</td></tr></table>'))

        corps = f"""<p><strong>Bonjour,</strong></p>
<p>Nous vous confirmons la bonne reception de votre convention de formation
signee le <strong>{date_fr(signee_le)}</strong>, pour la formation<br>
&laquo;&nbsp;<strong>{S.get('titre_complet') or S['nom_formation']}</strong>&nbsp;&raquo;
du <strong>{S.get('date_texte') or ''}</strong>.</p>
<p>Vous trouverez ci-joint votre exemplaire contresigne, portant sur
<strong>{len(participants)} participant{'s' if len(participants) > 1 else ''}</strong>
pour un montant total de <strong>{total:.0f}&nbsp;&euro; TTC</strong>.</p>
<p>Vous trouverez egalement ci-joint la <strong>facture {_facture_num}</strong>,
d'un montant de <strong>{total:.0f}&nbsp;&euro; TTC</strong>, a regler par virement.</p>
<p>Pour toute question, repondez simplement a ce message.</p>
{_bloc_reclamation}
<p style="margin-top:24px;">Bien a vous,<br>
<strong>{S.get('signature_mail') or S.get('formateur') or ''}, {S.get('marque') or ''}</strong></p>"""
        html = mails.ENVELOPPE.replace("{CORPS}", corps).replace(
            "{{marque}}", S.get("marque") or "")
        logo_bytes = None
        try:
            logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
            html = mails.poser_logo(html, logo_bytes)
        except Exception:
            pass
        message = MIMEMultipart("related")
        message["To"] = adresse
        message["Subject"] = "Votre convention signée - " + (
            S.get("titre_complet") or S["nom_formation"])
        exp = mails.expediteur(S)
        if exp:
            message["From"] = exp
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html, "html"))
        message.attach(alt)
        if logo_bytes:
            img = MIMEImage(logo_bytes)
            img.add_header("Content-ID", "<logo>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            message.attach(img)
        pj = MIMEApplication(pdf, _subtype="pdf")
        pj.add_header("Content-Disposition", "attachment", filename=cible)
        message.attach(pj)

        # LA FACTURE, dans le MEME mail. Les deux pieces vont ensemble dans le
        # dossier du centre ; deux envois a dix minutes d'intervalle, c'est deux
        # occasions d'en classer un de travers.
        if _facture_pdf:
            pjf = MIMEApplication(_facture_pdf, _subtype="pdf")
            pjf.add_header("Content-Disposition", "attachment", filename=_facture_nom)
            message.attach(pjf)
            print("   Facture %s jointe au meme envoi." % _facture_num)
        print(f"-> Envoi a {adresse} ({raison})...")
        # L'ENVOI PASSE PAR LA PORTE « courrier », plus par l'API Gmail.
        import courrier as _courrier
        import sessions as _s_org
        _courrier.envoyer(message, _s_org.organisme_de(CODE))
        print("   Envoye.")

        # Trace ecrite APRES l'envoi : si Gmail refuse, on reessaiera.
        if _fiche_brute:
            _fiche_brute["convention_client_signee_envoyee_le"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            _fiche_brute["convention_client_signee_lien"] = lien
            _S.enregistrer_session(CODE, _fiche_brute)
            print("   Trace ecrite : ce document ne repartira pas tout seul.")
    try:
        import journal
        journal.ecrire("Convention client signée envoyée", raison,
                       f"{len(participants)} participant(s) — {total:.0f} EUR", "", S["code"])
    except Exception:
        pass
except Exception as e:
    print(f"   ECHEC : {str(e)[:160]}", file=sys.stderr)
raise SystemExit(0)
