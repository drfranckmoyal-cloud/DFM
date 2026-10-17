# -*- coding: utf-8 -*-
"""Un mot aux sept convoques du 15/10 : leurs articles n'etaient pas les bons.

    venv/bin/python mot_articles_usures.py            # qui, et quoi — sans envoyer
    venv/bin/python mot_articles_usures.py --executer

POURQUOI CE SCRIPT EXISTE. Le 15/10/2026, la convocation J-20 d'Usures novembre
est partie a sept inscrits avec les articles de la MASTERCLASS : les pieces de
rappel de la formation Usures contenaient des copies des articles de composite.
La cause est corrigee — les quatre articles 3STEP/ACE ont remplace les trois
autres — mais sept personnes ont deja recu les mauvais. Elles n'ont pas a le
decouvrir en ouvrant les PDF la veille de la formation.

ON NE RENVOIE PAS LA CONVOCATION. Horaires, adresse et modalites d'acces etaient
justes : les repeter noierait le seul message qui compte. Ce mot ne porte que
les quatre articles, et dit en une phrase pourquoi il arrive.
"""
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

import courrier
import documents as _doc
import journal
import mails as _mails
import profil
import sessions as _s
import suivi

CODE = "usures-nov26"
JOUR = "15/10/2026"          # la convocation fautive
EXEC = "--executer" in sys.argv

S = _s.session(CODE)
ORG = _s.organisme_de(CODE)
ARTICLES = ["3STEP1.pdf", "3STEP2.pdf", "3STEP3.pdf", "ace-classification-1.pdf"]

pieces = []
for ref in (S.get("pieces_rappel") or []):
    nom = _doc.nom_piece(ref) or ""
    if nom not in ARTICLES:
        continue              # modalites d'acces : elles etaient justes, on ne les repete pas
    contenu = _doc.piece_par_ident(ref)
    if contenu:
        pieces.append((nom, contenu))
if len(pieces) != len(ARTICLES):
    print("REFUS : %d article(s) sur %d sont lisibles. Rien n'est envoye."
          % (len(pieces), len(ARTICLES)))
    raise SystemExit(1)

cibles = [l for l in suivi.lire_lignes_de(CODE)
          if str(l.get("rappel_le") or "").startswith(JOUR) and l.get("mail")]
print("-> %d destinataire(s), %d article(s) joints :" % (len(cibles), len(pieces)))
for nom, c in pieces:
    print("   . %-30s %6d Ko" % (nom, len(c) // 1024))

logo = None
try:
    logo = profil.logo(ORG)
except Exception:
    pass

for ligne in cibles:
    prenom = (ligne.get("prenom") or "").strip()
    qui = (prenom + " " + (ligne.get("nom") or "")).strip()
    print("-> %s <%s>" % (qui, ligne["mail"]))
    if not EXEC:
        continue
    html = (
        '<div style="font:15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;'
        'color:#1a1d26;max-width:34em">'
        '<img src="cid:logo" alt="" style="height:44px;margin-bottom:18px">'
        "<p>Bonjour %s,</p>"
        "<p>Les articles joints à ta convocation de mercredi n'étaient pas les bons&nbsp;: "
        "c'étaient ceux d'une autre formation. Désolé pour la confusion.</p>"
        "<p><b>Voici les quatre articles à lire avant les deux journées sur les usures.</b></p>"
        "<p>Le reste de la convocation — adresse, horaires, modalités d'accès — "
        "était juste&nbsp;: tu peux t'y fier.</p>"
        "<p>À très bientôt,<br>%s</p></div>"
        % (prenom or "", S.get("signature_mail") or S.get("formateur") or "")
    )
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    exp = _mails.expediteur(S)
    if exp:
        message["From"] = exp
    message["Subject"] = "Les bons articles à lire · " + (S.get("nom_formation") or "")
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(_mails.poser_logo(html, logo), "html"))
    message.attach(corps)
    if logo:
        img = MIMEImage(logo)
        img.add_header("Content-ID", "<logo>")
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(img)
    for nom, contenu in pieces:
        pj = MIMEApplication(contenu, _subtype="pdf")
        pj.add_header("Content-Disposition", "attachment", filename=nom)
        message.attach(pj)
    try:
        courrier.envoyer(message, ORG)
        journal.ecrire("Articles du rappel renvoyés", qui,
                       ligne["mail"] + " — les articles du %s n'étaient pas ceux d'Usures" % JOUR,
                       "", CODE)
        print("   envoye.")
    except Exception as e:
        print("   ECHEC : %s" % str(e)[:120])

print("Termine." if EXEC else "SIMULATION : rien n'est parti. Relancer avec --executer.")
