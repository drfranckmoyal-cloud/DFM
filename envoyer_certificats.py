"""Le mail de fin de formation : attestation, certificat, code promo, demande d'avis.

48 HEURES APRES LA FIN, A TOUS LES INSCRITS, avec ou sans reponse aux
questionnaires — regle de Franck du 08/11/2026. Pour TOUTES les formations :
celles qui n'ont pas de certificat recoivent l'attestation seule.

    python3 envoyer_certificats.py <code>                  a ceux qui n'ont pas encore leur attestation
    python3 envoyer_certificats.py <code> a@b.fr,c@d.fr    a ceux-la seulement, meme deja servis
    python3 envoyer_certificats.py <code> --essai adresse  un exemplaire d'essai, au nom de Franck MOYAL

LE GUET DES QUESTIONNAIRES LE LANCE, le lendemain du dernier jour a l'heure
reglee (voir certificat.a_envoyer_maintenant). Le texte est le modele de mail
« certificat », modifiable dans l'editeur de modeles.

L'ATTESTATION PART DANS CE MAIL, et elle est notee envoyee : la fenetre
« Envoyer les attestations » de la fiche de session ne la reproposera pas, sauf
pour un renvoi volontaire. Une attestation encore sans resultat part telle
quelle ; elle sera refaite et reproposee des que l'evaluation de sortie
arrivera (voir generer_attestations.py).

L'ESSAI N'ECRIT RIEN : ni suivi, ni journal, ni etat. Il fabrique un
certificat et une attestation au nom de Franck MOYAL, a la volee, et les
envoie a l'adresse donnee, objet precede de « [ESSAI] ».
"""
import sys
import urllib.parse
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import attestation as _att
import certificat as _cert
import courrier
import documents
import journal
import mails as _mails
import pdf as _pdf
import suivi
from sessions import organisme_de, session

ARGS = sys.argv[1:]
CODE = ARGS[0] if ARGS else None
ESSAI = ARGS[ARGS.index("--essai") + 1].strip().lower() if "--essai" in ARGS else ""
CIBLES = [] if ESSAI else [m.strip().lower() for m in (ARGS[1].split(",") if len(ARGS) > 1 else [])
                           if m.strip()]
S = session(CODE)
ORG = organisme_de(S["code"])
print(f"-> Session : {S['nom_formation']} ({S['code']})")

AVEC_CERTIFICAT = bool(_cert.fond(S["code"]))
if not AVEC_CERTIFICAT:
    print("-> Pas de certificat pour cette formation : l'attestation part seule.")


def remise_fidelite():
    """Le code de fidelite n'est propose que s'il est actif chez cet organisme."""
    try:
        import codes_promo
        r = codes_promo.trouver(ORG, "REMISE10")
        return "1" if (r and r.get("actif", True)) else ""
    except Exception:
        return ""


def lien_satisfaction(mail):
    return ((S.get("url_signature") or "") + "/questionnaire.html?s=" + S["code"]
            + "&type=satisfaction&m=" + urllib.parse.quote(mail))


def ont_repondu():
    """Les adresses qui ont deja rendu le questionnaire de satisfaction."""
    try:
        import inscription as I
        r = I._sb("Questionnaires?session_code=eq.%s&type=eq.satisfaction&select=mail"
                  % urllib.parse.quote(S["code"]))
        return {(x.get("mail") or "").strip().lower() for x in r}
    except Exception as e:
        print(f"   (reponses de satisfaction illisibles : {e} — tout le monde recevra la demande)")
        return set()


logo_bytes = __import__("profil").logo(ORG)
logo_data = _pdf.image_en_ligne(logo_bytes, "image/png") if logo_bytes else ""
modele = _mails.pour_formation(S.get("formation", ""), "certificat")
if not modele:
    print("-> Modele de mail « certificat » introuvable.")
    exit()


def envoyer(ligne, certificat_bytes, attestation_bytes, repondu, essai=False):
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    mail = (ligne.get("mail") or "").strip()
    ctx = _mails.contexte(S, ligne, {
        "certificat": "1" if certificat_bytes else "",
        "sans_certificat": "" if certificat_bytes else "1",
        "documents_fin": "Ton certificat et ton attestation" if certificat_bytes else "Ton attestation",
        "remise_fidelite": remise_fidelite(),
        "lien_satisfaction": lien_satisfaction(mail),
        "satisfaction_a_faire": "" if repondu else "1",
        "satisfaction_faite": "1" if repondu else "",
    })
    rendu = _mails.rendre(modele, ctx)
    message = MIMEMultipart("related")
    message["To"] = mail
    exp = _mails.expediteur(S)
    if exp:
        message["From"] = exp
    message["Subject"] = ("[ESSAI] " if essai else "") + rendu["objet"]
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(_mails.poser_logo(rendu["html"], logo_bytes), "html"))
    message.attach(corps)
    if logo_bytes:
        logo = MIMEImage(logo_bytes)
        logo.add_header("Content-ID", "<logo>")
        logo.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(logo)
    for octets, nom in ((certificat_bytes, _cert.nom_fichier(ligne)),
                        (attestation_bytes, f"Attestation - {nom_prenom}.pdf")):
        if not octets:
            continue
        pj = MIMEApplication(octets, _subtype="pdf")
        pj.add_header("Content-Disposition", "attachment", filename=nom)
        message.attach(pj)
    # LA PORTE « courrier » : c'est l'organisme DE LA SESSION qui envoie.
    courrier.envoyer(message, ORG)


# ---------------------------------------------------------------------------
# L'ESSAI
# ---------------------------------------------------------------------------
if ESSAI:
    ligne = {c: "" for c in suivi.COL}
    ligne.update({"prenom": "Franck", "nom": "MOYAL", "mail": ESSAI, "fonction": "Chirurgien-dentiste"})
    print(f"-> Essai pour {ESSAI} : certificat et attestation fabriques a la volee...")
    cert = _cert.fabriquer(S["code"], ligne) if AVEC_CERTIFICAT else None
    donnees = _att.valider_par_le_responsable(_att.pour(S["code"], ligne, logo_data))
    attest = _pdf.depuis_html(_att.html(donnees))
    envoyer(ligne, cert, attest, repondu=False, essai=True)
    print("   Essai envoye.")
    exit()


# ---------------------------------------------------------------------------
# L'ENVOI REEL
# ---------------------------------------------------------------------------
lignes = _cert.beneficiaires(S["code"])
if CIBLES:
    lignes = [l for l in lignes if (l["mail"] or "").strip().lower() in CIBLES]
else:
    lignes = [l for l in lignes if not l["attestation_envoyee_le"]]
if not lignes:
    print("-> Personne a qui envoyer.")
    if not CIBLES:
        _cert.poser_envoi(S["code"], envoye_le=datetime.now().strftime("%d/%m/%Y %H:%M"))
    exit()
print(f"-> {len(lignes)} mail(s) a envoyer.")
repondus = ont_repondu()
compte, rates = 0, []
for ligne in lignes:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    print(f"-> {nom_prenom}...")
    cert = _cert.existant(S["code"], ligne) if AVEC_CERTIFICAT else None
    if AVEC_CERTIFICAT and not cert:
        # Fabrique a la volee et range : le passage du matin a pu manquer.
        try:
            cert = _cert.fabriquer(S["code"], ligne)
            documents.ranger(S["code"], "certificat", _cert.nom_fichier(ligne), cert)
        except Exception as e:
            print(f"   ECHEC du certificat : {e}")
            rates.append(nom_prenom)
            continue
    attest = documents.lire(documents.reference(S["code"], "attestation", f"Attestation - {nom_prenom}.pdf")) \
        or (documents.depuis_lien(ligne["lien_attestation"]) if ligne.get("lien_attestation") else None)
    if not attest:
        print("   Attestation pas encore fabriquee : ce mail attendra.")
        rates.append(nom_prenom)
        continue
    try:
        envoyer(ligne, cert, attest, repondu=(ligne["mail"] or "").strip().lower() in repondus)
    except Exception as e:
        print(f"   ECHEC de l'envoi : {e}")
        rates.append(nom_prenom)
        continue
    suivi.ecrire(ligne["_numero"], "attestation_envoyee_le", suivi.aujourdhui(), S["code"])
    try:
        journal.ecrire("Certificat envoyé" if cert else "Attestation envoyée",
                       (ligne["prenom"].strip() + " " + ligne["nom"].strip().upper()).strip(),
                       ligne["mail"] + (" — avec l'attestation" if cert else "")
                       + " — envoi de fin de formation", "", S["code"])
    except Exception:
        pass
    print("   Certificat envoye." if cert else "   Attestation envoyee.")
    compte += 1

# LE PASSAGE EST NOTE MEME S'IL Y A DES RATES. Sans cela, le guet le relancerait
# chaque minute — le defaut qui a rempli le journal de 557 lignes le 05/11/2026.
# Les rates se renvoient a la main, depuis la fenetre des attestations.
if not CIBLES:
    _cert.poser_envoi(S["code"], envoye_le=datetime.now().strftime("%d/%m/%Y %H:%M"))
if rates:
    print(f"-> NON ENVOYES ({len(rates)}) : " + ", ".join(rates))
print(f"-> Termine : {compte} mail(s) envoye(s).")
