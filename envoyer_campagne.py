"""Envoi d'une campagne de communication.

    python3 envoyer_campagne.py <identifiant_campagne>
    python3 envoyer_campagne.py <identifiant_campagne> --essai=adresse@exemple.fr

LANCE EN TACHE DE FOND par l'ecran Messagerie : quelques centaines de mails
prennent plusieurs minutes, et une requete web ne doit pas rester suspendue
pendant ce temps.

REPREND OU IL S'EST ARRETE. Chaque destinataire servi est inscrit au registre
AVANT de passer au suivant. Relancer la meme campagne ne reexpedie a personne :
c'est le seul comportement acceptable quand l'interruption est probable et
qu'un mail parti ne se rappelle pas.

L'ESSAI ne consomme rien et ne marque rien : il rend le message tel qu'il
partira, avec le pied et le lien de desinscription, mais a une seule adresse.
"""
import base64
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

from connexion import service_drive
import campagnes as K
import contacts as C
import mails

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
IDENT = ARGS[0] if ARGS else ""
ESSAI = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--essai=")), "")

fiche = K.tout().get(IDENT)
if not fiche:
    print("-> Campagne inconnue : " + str(IDENT), file=sys.stderr)
    raise SystemExit(1)

# L'IDENTITE DE L'ORGANISME QUI A CREE LA CAMPAGNE, pas celle du profil actif.
# Meme regle que partout ailleurs : une campagne DSF reste une campagne DSF,
# meme relancee un jour ou Smileclub est selectionne.
import profil
_organisme = fiche.get("organisme") or ""
O = (profil.charger(_organisme) if _organisme else profil.charger()) or {}
try:
    import sessions as _s
    O.setdefault("url_signature", _s.COMMUN.get("url_signature") or "")
    # L'ADRESSE SE COMPOSE DEPUIS LE PROFIL VISE, elle ne se replie plus sur
    # les donnees communes : celles-ci suivent l'organisme ACTIF, si bien
    # qu'un mail Smileclub portait l'adresse de DSF (61 rue Balard) au lieu
    # de la sienne (4 rue Joseph Granier). Constate le 23/08/2026.
    O.setdefault("adresse_organisme",
                 profil.adresse_complete(O, repli=False) or "")
except Exception:
    pass

print("-> Campagne %s — « %s »" % (IDENT, fiche.get("objet") or ""))
print("   organisme : %s" % (O.get("marque") or _organisme or "?"))

# « drive = service_drive() » retire le 18/08/2026 : les pieces jointes passent
# par la couche « documents », qui les garde en cache.

# LES PIECES SONT TELECHARGEES UNE SEULE FOIS, pas a chaque destinataire : sur
# 178 envois, les reprendre du Drive chaque fois multiplierait les requetes et
# le temps par autant.
PIECES = []
for _p in (fiche.get("pieces") or []):
    if (_p.get("mode") or "jointe") != "jointe":
        continue
    try:
        import documents as _doc
        _octets = _doc.piece_par_ident(_p["drive"])
        if not _octets:
            raise RuntimeError("piece absente du cache et Drive injoignable")
        PIECES.append((_p.get("nom") or _doc.nom_piece(_p["drive"]) or "piece", _octets))
    except Exception as _e:
        print("   (piece « %s » illisible, non jointe : %s)" % (_p.get("nom"), str(_e)[:60]))
if PIECES:
    _poids = sum(len(c) for _, c in PIECES)
    print("   %d piece(s) jointe(s), %.1f Ko par envoi" % (len(PIECES), _poids / 1024.0))

logo = None
try:
    # LE LOGO DE L'ORGANISME DE LA CAMPAGNE, pas celui du profil actif. Meme
    # regle que l'expediteur plus bas — mais elle avait ete oubliee ici : un
    # mail Smileclub partait avec le logo de DSF des que DSF etait selectionne.
    # Constate le 23/08/2026 sur un essai reel, texte Smileclub, logo DSF.
    logo = __import__("profil").logo(_organisme or None)
except Exception:
    pass


def _expediteur():
    """L'adresse d'ou part la communication. Le meme mecanisme que les mails du
    parcours : elle suit l'organisme, jamais le compte connecte."""
    try:
        return mails.expediteur({"mail_contact": O.get("mail_contact") or "",
                                 "marque": O.get("marque") or ""})
    except Exception:
        return ""


def envoyer_a(contact):
    """Un envoi. Rend "" si tout va bien, le motif sinon."""
    adresse = (contact.get("mail") or "").strip()
    if not adresse or "@" not in adresse:
        return "adresse inexploitable"
    html = K.rendre(fiche.get("corps") or "", contact, O)
    message = MIMEMultipart("related")
    message["To"] = adresse
    message["Subject"] = fiche.get("objet") or ""
    exp = _expediteur()
    if exp:
        message["From"] = exp
    # LIST-UNSUBSCRIBE : Gmail et Outlook affichent alors LEUR bouton de
    # desinscription, en haut du message. C'est plus visible qu'un lien en pied,
    # et les fournisseurs en tiennent compte dans leur jugement anti-spam.
    try:
        import desinscription as D
        message["List-Unsubscribe"] = "<%s>" % D.lien(contact.get("id"),
                                                      O.get("url_signature") or "")
        message["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    except Exception:
        pass
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    message.attach(alt)
    if logo:
        img = MIMEImage(logo)
        img.add_header("Content-ID", "<logo>")
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(img)
    for nom, contenu in PIECES:
        pj = MIMEApplication(contenu)
        pj.add_header("Content-Disposition", "attachment", filename=nom)
        message.attach(pj)
    try:
        # L'ENVOI PASSE PAR LA PORTE « courrier ». Une campagne appartient a un
        # organisme — celui de sa fiche — et part de son adresse, jamais de
        # celle du compte connecte.
        import courrier
        courrier.envoyer(message, _organisme)
        return ""
    except Exception as e:
        return str(e)[:120]


# --------------------------------------------------------------------------
if ESSAI:
    # Un contact fictif, mais un identifiant REEL : le lien de desinscription
    # doit etre verifiable. On prend le premier vise, sinon l'essai ne
    # prouverait rien sur le pied du message.
    vises = fiche.get("vises") or []
    modele = {"id": vises[0] if vises else 0, "mail": ESSAI}
    print("-> Essai vers %s..." % ESSAI)
    souci = envoyer_a(modele)
    print("   " + (souci or "Envoye. Rien n'a ete marque : l'essai ne consomme pas la campagne."))
    raise SystemExit(1 if souci else 0)

reste = K.reste_a_servir(IDENT)
if not reste:
    print("-> Tous les destinataires ont deja recu. Rien a faire.")
    raise SystemExit(0)
print("-> %d destinataire(s) sur %d restent a servir." % (reste and len(reste), len(fiche.get("vises") or [])))

envoyes = rates = 0
for n, cid in enumerate(reste, 1):
    contact = None
    try:
        contact = C.par_id(cid)
    except Exception:
        contact = None
    if not contact:
        K.marquer_servi(IDENT, cid, "fiche introuvable")
        rates += 1
        continue
    # Ultime garde-fou : quelqu'un a pu se desinscrire PENDANT l'envoi. Le
    # ciblage date du clic, l'envoi dure plusieurs minutes.
    if contact.get("ne_plus_contacter"):
        K.marquer_servi(IDENT, cid, "desinscrit entre-temps")
        rates += 1
        continue
    souci = envoyer_a(contact)
    K.marquer_servi(IDENT, cid, souci)
    if souci:
        rates += 1
        print("   %d/%d  %-34s ECHEC : %s" % (n, len(reste), (contact.get("mail") or "")[:34], souci))
    else:
        envoyes += 1
        if n % 25 == 0 or n == len(reste):
            print("   %d/%d envoye(s)" % (n, len(reste)))
    time.sleep(K.PAUSE)

print("-> Termine : %d envoye(s), %d en echec." % (envoyes, rates))
try:
    import journal
    journal.ecrire("Campagne envoyée", "", "%s — %d destinataire(s)"
                   % (fiche.get("objet") or "", envoyes), "", "")
except Exception:
    pass
