# -*- coding: utf-8 -*-
"""Prevenir Franck quand DFM ne va pas. Par mail, pas par un bandeau.

POURQUOI CE MODULE EXISTE. Deux pannes en trois jours ont ete decouvertes par
hasard, parce que Franck a voulu travailler :

  18/10 — une inscription sans fiche pendant un jour. Il l'a su en lisant un
          bandeau d'alerte qu'il aurait pu ne pas remarquer.
  20/10 — six heures sans aucun inscrit ni aucune session a l'ecran, la base
          repondant « malformed » a chaque lecture. Rien ne l'a dit.

Un bandeau suppose qu'on ouvre DFM et qu'on le remarque. Ce n'est pas une
alerte, c'est un espoir. Ce module ecrit, a l'adresse de contact de
l'organisme.

IL NE DEPEND PAS DE LA BASE. C'est la condition pour qu'il serve justement
quand la base est en cause : l'etat des alertes deja envoyees est un fichier,
et l'envoi passe par « courrier », qui n'a besoin que du jeton Google.

PAS DEUX FOIS LA MEME. Une alerte qui se repete toutes les dix minutes finit
par etre filtree, et ce jour-la elle ne sert plus a rien. Une meme alerte ne
repart qu'au bout de six heures, ou si son contenu a change.
"""
import io
import json
import os
from datetime import datetime

DOSSIER = os.path.dirname(os.path.abspath(__file__))
MEMOIRE = os.path.join(DOSSIER, "etat_alertes.json")
HEURES_PAR_DEFAUT = 6


def _memoire():
    try:
        return json.load(io.open(MEMOIRE, encoding="utf-8"))
    except Exception:
        return {}


def _noter(cle, signature):
    d = _memoire()
    d[cle] = {"signature": signature,
              "le": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    try:
        io.open(MEMOIRE, "w", encoding="utf-8").write(
            json.dumps(d, ensure_ascii=False, indent=1))
    except Exception:
        pass


def oublier(cle):
    """Le souci est passe : la prochaine alerte repartira sans attendre."""
    d = _memoire()
    if cle in d:
        d.pop(cle)
        try:
            io.open(MEMOIRE, "w", encoding="utf-8").write(
                json.dumps(d, ensure_ascii=False, indent=1))
        except Exception:
            pass


def deja_envoyee(cle, signature, heures=HEURES_PAR_DEFAUT):
    d = _memoire().get(cle) or {}
    if d.get("signature") != signature:
        return False
    try:
        quand = datetime.strptime(d.get("le") or "", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return (datetime.now() - quand).total_seconds() < heures * 3600


def prevenir(cle, objet, paragraphes, organisme="mon-organisme",
            heures=HEURES_PAR_DEFAUT, quoi_faire=""):
    """Ecrit a l'organisme. Rend l'adresse touchee, ou "".

    `cle` identifie le genre d'alerte (« base-illisible »), pour ne pas
    confondre deux soucis differents dans la memoire.
    """
    signature = "|".join(paragraphes)
    if deja_envoyee(cle, signature, heures):
        return ""
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import courrier
        import profil
        fiche = profil.charger(organisme) or {}
        vers = (fiche.get("mail_contact") or "").strip()
        if not vers:
            return ""
        corps = ('<div style="font:15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;'
                 'color:#1a1d26;max-width:36em">'
                 + "".join("<p>%s</p>" % p for p in paragraphes)
                 + (('<p style="background:#fdf6ec;border:1px solid #f5dda6;'
                     'border-radius:9px;padding:12px 14px"><b>Ce qu\'il y a à '
                     'faire&nbsp;:</b><br>%s</p>' % quoi_faire) if quoi_faire else "")
                 + '<p style="color:#6b7280;font-size:12.5px">Message automatique de '
                   'DFM. Il ne part qu\'en cas de souci, et au plus une fois toutes '
                   'les %d heures.</p></div>' % heures)
        message = MIMEMultipart("alternative")
        message["To"] = vers
        message["Subject"] = objet
        try:
            import mails as _mails
            exp = _mails.expediteur({"organisme": organisme})
            if exp:
                message["From"] = exp
        except Exception:
            pass
        message.attach(MIMEText(corps, "html"))
        courrier.envoyer(message, organisme)
        _noter(cle, signature)
        return vers
    except Exception as e:
        print("   (alerte non envoyee : %s)" % str(e)[:100])
        return ""
