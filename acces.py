"""Qui a le droit d'ouvrir DFM.

POURQUOI CE MODULE EXISTE. Jusqu'au 05/08/2026, les 151 routes de DFM etaient
ouvertes a quiconque atteignait l'adresse. Sans consequence sur une machine
personnelle ; catastrophique des la premiere publication : 181 contacts avec
noms, adresses et telephones, 86 routes qui ecrivent, 35 qui suppriment.

CE N'EST PAS UN SYSTEME DE COMPTES. Un seul mot de passe, celui du proprietaire
de l'installation. DFM gere DEUX organismes, pas deux utilisateurs — inventer
des comptes maintenant serait construire pour un besoin qui n'existe pas.

LE MOT DE PASSE N'EST PAS STOCKE. Seule son empreinte l'est, salee et derivee
par PBKDF2. Un fichier de configuration qui fuit ne donne pas le mot de passe.

TANT QU'AUCUN MOT DE PASSE N'EST DEFINI, DFM reste ouvert — c'est le cas sur
une machine personnelle, et imposer une connexion la ou elle ne sert a rien
ferait perdre du temps a chaque lancement. La protection s'active en posant
DFM_MOT_DE_PASSE dans l'environnement, ou en lancant `python3 mot_de_passe.py`.
"""
import base64
import hashlib
import hmac
import os
import secrets

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "acces.json")

# 240 000 iterations : le compromis retenu par l'OWASP pour PBKDF2-SHA256 en
# 2023. Assez lent pour decourager une attaque par dictionnaire, assez rapide
# pour ne pas se sentir a la connexion.
_TOURS = 240_000
_DUREE = 12 * 3600          # une session dure une journee de travail


def _charger():
    import json
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)
    try:
        os.chmod(_FICHIER, 0o600)      # lisible par le seul proprietaire
    except Exception:
        pass


def empreinte(mot_de_passe, sel=None):
    sel = sel or secrets.token_hex(16)
    cle = hashlib.pbkdf2_hmac("sha256", (mot_de_passe or "").encode("utf-8"),
                              sel.encode("utf-8"), _TOURS)
    return sel, base64.b64encode(cle).decode()


def definir(mot_de_passe):
    """Pose ou remplace le mot de passe. Rend (ok, message)."""
    m = (mot_de_passe or "").strip()
    if len(m) < 10:
        return False, "Dix caractères au minimum — c'est la seule barrière devant vos données."
    sel, h = empreinte(m)
    d = _charger()
    d["sel"] = sel
    d["empreinte"] = h
    # Le secret de signature des sessions change avec le mot de passe : toute
    # session ouverte avant devient caduque, ce qui est le comportement voulu
    # quand on change un mot de passe.
    d["secret"] = secrets.token_hex(32)
    _ecrire(d)
    return True, "Mot de passe enregistré."


def protege():
    """DFM demande-t-il un mot de passe ? Faux tant qu'aucun n'est defini."""
    return bool(_charger().get("empreinte"))


def verifier(mot_de_passe):
    d = _charger()
    if not d.get("empreinte"):
        return True
    _, h = empreinte(mot_de_passe or "", d.get("sel") or "")
    return hmac.compare_digest(h, d["empreinte"])


def secret():
    """La cle qui signe les cookies de session ET les jetons anti-CSRF."""
    d = _charger()
    s = d.get("secret")
    if not s:
        s = secrets.token_hex(32)
        d["secret"] = s
        _ecrire(d)
    return s


def duree():
    return _DUREE
