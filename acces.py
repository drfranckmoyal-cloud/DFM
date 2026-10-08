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


# ═══════════════════════════════════════════════════════════════════════
#  LES COMPTES — 08/10/2026
# ═══════════════════════════════════════════════════════════════════════
#
# CE MODULE DISAIT, TROIS MOIS DURANT, QU'INVENTER DES COMPTES SERAIT
# CONSTRUIRE POUR UN BESOIN QUI N'EXISTE PAS. C'etait vrai : un proprietaire,
# une installation. Le besoin existe maintenant pour deux raisons, et c'est
# pour elles seules qu'on les ajoute :
#
#   1. Le journal d'audit disait « DFM a fait », jamais « untel a fait ». Une
#      piste d'audit sans auteur prouve qu'une action a eu lieu, pas qui en
#      repond.
#   2. Une installation livree a quelqu'un d'autre a plusieurs mains dessus,
#      et toutes n'ont pas a toucher l'identite de l'organisme ni ses comptes.
#
# RIEN NE CHANGE TANT QU'AUCUN COMPTE N'EXISTE. L'ecran de connexion continue
# de ne demander qu'un mot de passe, exactement comme avant. La bascule se fait
# a la creation du premier compte, et pas une seconde plus tot : personne ne
# doit se retrouver devant un champ « identifiant » qu'il ne s'attendait pas a
# voir, et surtout pas enferme dehors.

ROLES = {
    "gerant": "Gérant",          # tout, y compris les comptes et l'identite
    "assistante": "Assistante",  # tout le quotidien, rien de structurel
}
ROLE_DEFAUT = "assistante"


def _nettoyer_identifiant(valeur):
    garde = "".join(c for c in (valeur or "").strip().lower()
                    if c.isalnum() or c in "._-")
    return garde[:32]


def _bruts():
    d = _charger()
    liste = d.get("utilisateurs")
    return liste if isinstance(liste, list) else []


def _poser(liste):
    d = _charger()
    d["utilisateurs"] = liste
    _ecrire(d)


def utilisateurs():
    """Les comptes, sans rien qui ressemble a un secret."""
    return [{k: v for k, v in u.items() if k not in ("sel", "empreinte")}
            for u in _bruts()]


def comptes_ouverts():
    """Y a-t-il au moins un compte actif ? C'est ce qui decide de la bascule."""
    return any(u.get("actif", True) for u in _bruts())


def utilisateur(identifiant):
    i = _nettoyer_identifiant(identifiant)
    for u in _bruts():
        if u.get("identifiant") == i:
            return {k: v for k, v in u.items() if k not in ("sel", "empreinte")}
    return None


def _gerants_actifs(liste=None):
    return [u for u in (liste if liste is not None else _bruts())
            if u.get("role") == "gerant" and u.get("actif", True)]


def creer_utilisateur(identifiant, nom, mot_de_passe, role=ROLE_DEFAUT):
    """Rend (ok, message)."""
    from datetime import datetime
    i = _nettoyer_identifiant(identifiant)
    if len(i) < 3:
        return False, "L'identifiant doit faire au moins trois caractères (lettres, chiffres, point, tiret)."
    if role not in ROLES:
        return False, "Rôle inconnu."
    if len(mot_de_passe or "") < 10:
        return False, "Dix caractères au minimum pour le mot de passe."
    liste = _bruts()
    if any(u.get("identifiant") == i for u in liste):
        return False, "Cet identifiant est déjà pris."
    sel, h = empreinte(mot_de_passe)
    liste.append({"identifiant": i, "nom": (nom or "").strip() or i,
                  "role": role, "actif": True, "sel": sel, "empreinte": h,
                  "cree_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
                  "derniere_connexion": ""})
    _poser(liste)
    return True, "Compte « %s » créé." % i


def modifier_utilisateur(identifiant, nom=None, role=None, actif=None, mot_de_passe=None):
    """Rend (ok, message). REFUSE DE RETIRER LE DERNIER GERANT — sans quoi
    l'installation se retrouve sans personne pour gerer les comptes, et il faut
    repasser par la ligne de commande sur le serveur."""
    i = _nettoyer_identifiant(identifiant)
    liste = _bruts()
    cible = None
    for u in liste:
        if u.get("identifiant") == i:
            cible = u
            break
    if cible is None:
        return False, "Compte inconnu."
    futur = dict(cible)
    if nom is not None:
        futur["nom"] = (nom or "").strip() or i
    if role is not None:
        if role not in ROLES:
            return False, "Rôle inconnu."
        futur["role"] = role
    if actif is not None:
        futur["actif"] = bool(actif)
    reste = [u for u in liste if u.get("identifiant") != i] + [futur]
    if not _gerants_actifs(reste):
        return False, "C'est le dernier gérant actif : DFM refuse de le retirer."
    if mot_de_passe is not None:
        if len(mot_de_passe) < 10:
            return False, "Dix caractères au minimum pour le mot de passe."
        futur["sel"], futur["empreinte"] = empreinte(mot_de_passe)
    cible.clear()
    cible.update(futur)
    _poser(liste)
    return True, "Compte « %s » mis à jour." % i


def supprimer_utilisateur(identifiant):
    i = _nettoyer_identifiant(identifiant)
    liste = _bruts()
    reste = [u for u in liste if u.get("identifiant") != i]
    if len(reste) == len(liste):
        return False, "Compte inconnu."
    if not _gerants_actifs(reste):
        return False, "C'est le dernier gérant actif : DFM refuse de le supprimer."
    _poser(reste)
    return True, "Compte « %s » supprimé." % i


def authentifier(identifiant, mot_de_passe):
    """Rend la fiche du compte, ou None. Le temps de calcul est le meme pour un
    identifiant inconnu que pour un mot de passe faux : sans cela, la duree de
    la reponse dirait quels identifiants existent."""
    import hmac as _hmac
    i = _nettoyer_identifiant(identifiant)
    cible = None
    for u in _bruts():
        if u.get("identifiant") == i and u.get("actif", True):
            cible = u
            break
    sel = (cible or {}).get("sel") or "0" * 32
    _, h = empreinte(mot_de_passe or "", sel)
    if cible and _hmac.compare_digest(h, cible.get("empreinte") or ""):
        return {k: v for k, v in cible.items() if k not in ("sel", "empreinte")}
    return None


def noter_connexion(identifiant):
    from datetime import datetime
    i = _nettoyer_identifiant(identifiant)
    liste = _bruts()
    for u in liste:
        if u.get("identifiant") == i:
            u["derniere_connexion"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            _poser(liste)
            return
