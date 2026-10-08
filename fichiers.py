"""Lire et ecrire les fichiers JSON de DFM sans que deux processus se marchent dessus.

DEUX DEFAUTS, PAS UN SEUL.

1. L'ECRITURE N'ETAIT PAS ATOMIQUE. `open(chemin, "w")` VIDE le fichier avant
   d'ecrire quoi que ce soit. Entre les deux, le fichier est vide sur le disque.
   Une coupure la — processus tue, machine eteinte, disque plein — et tout est
   perdu. Sur campagnes.json, perdre le fichier c'est perdre la liste de ceux
   qui ont deja recu : la campagne relancee repart a tout le monde.

2. RIEN N'EMPECHAIT DEUX ECRITURES SIMULTANEES. DFM tourne dans plusieurs
   processus a la fois : Flask, le pipeline dfm.py, et envoyer_campagne.py qui
   ecrit APRES CHAQUE DESTINATAIRE. Chacun lit tout le fichier, modifie sa
   part, reecrit tout. Deux qui se croisent, et le second efface le travail du
   premier sans que rien ne le signale.

CE MODULE REGLE LES DEUX. On ecrit dans un fichier temporaire du meme dossier,
puis on le renomme : os.replace est atomique, le fichier est soit l'ancien soit
le nouveau, jamais un entre-deux. Et modifier() prend un verrou pour toute la
duree lecture-modification-ecriture, ce qui est la seule maniere correcte de
faire un read-modify-write partage.

LE VERROU EST CONSULTATIF et repose sur fcntl, absent de Windows. Sans lui,
l'ecriture reste atomique — on perd la protection contre l'entrelacement, pas
celle contre la corruption. DFM tourne sur macOS ; la degradation est prevue
pour ne rien casser ailleurs, pas pour etre confortable.
"""
import json
import os
import tempfile
from contextlib import contextmanager

try:
    import fcntl
except Exception:                                   # Windows
    fcntl = None

# Au-dela, on considere que le detenteur est mort sans relacher. Un envoi de
# campagne ecrit par destinataire : chaque prise dure quelques millisecondes.
ATTENTE = 20


@contextmanager
def _verrou(chemin):
    """Verrou exclusif sur un fichier voisin, jamais sur le fichier lui-meme.

    Verrouiller le fichier de donnees obligerait a l'ouvrir, donc a le creer
    s'il n'existe pas, et surtout empecherait le renommage atomique.
    """
    if fcntl is None:
        yield
        return
    chemin_v = chemin + ".verrou"
    f = None
    try:
        f = open(chemin_v, "a+")
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if f is not None:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            f.close()


def lire(chemin, defaut=None):
    """Le contenu, ou le defaut. Ne leve jamais : un fichier absent est normal."""
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return {} if defaut is None else defaut
    if defaut is not None and not isinstance(d, type(defaut)):
        return defaut
    return d


def ecrire(chemin, donnees):
    """Ecrit d'un bloc : le fichier n'est jamais a moitie ecrit.

    Le temporaire est cree DANS LE MEME DOSSIER : os.replace n'est atomique
    qu'a l'interieur d'un meme systeme de fichiers.
    """
    dossier = os.path.dirname(os.path.abspath(chemin)) or "."
    fd, provisoire = tempfile.mkstemp(dir=dossier, prefix=".", suffix=".ecriture")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())        # le contenu est sur le disque, pas en cache
        os.replace(provisoire, chemin)
        provisoire = ""
    finally:
        if provisoire and os.path.exists(provisoire):
            try:
                os.remove(provisoire)
            except Exception:
                pass


@contextmanager
def modifier(chemin, defaut=None):
    """Lecture, modification et ecriture sous un seul verrou.

        with fichiers.modifier(FICHIER, {}) as d:
            d["cle"] = valeur

    Ecrit a la sortie du bloc, sauf si le bloc leve : une exception au milieu
    d'une modification ne doit pas enregistrer un etat a moitie change.
    """
    with _verrou(chemin):
        d = lire(chemin, defaut)
        yield d
        ecrire(chemin, d)


def ecrire_texte(chemin, texte):
    """Comme ecrire(), pour un contenu qui n'est pas du JSON.

    Sert au jeton OAuth et au fichier de l'organisme actif : deux fichiers
    minuscules dont la perte arrete tout, et que rien ne protegeait.
    """
    dossier = os.path.dirname(os.path.abspath(chemin)) or "."
    fd, provisoire = tempfile.mkstemp(dir=dossier, prefix=".", suffix=".ecriture")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texte)
            f.flush()
            os.fsync(f.fileno())
        os.replace(provisoire, chemin)
        provisoire = ""
    finally:
        if provisoire and os.path.exists(provisoire):
            try:
                os.remove(provisoire)
            except Exception:
                pass


def ecrire_octets(chemin, octets):
    """Comme ecrire_texte(), pour un contenu binaire.

    Sert aux images du profil — signature, tampon. Une image a demi ecrite
    ne se voit pas dans un dossier : elle se decouvre sur une convention
    partie sans signature.
    """
    dossier = os.path.dirname(os.path.abspath(chemin)) or "."
    fd, provisoire = tempfile.mkstemp(dir=dossier, prefix=".", suffix=".ecriture")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(octets)
            f.flush()
            os.fsync(f.fileno())
        os.replace(provisoire, chemin)
        provisoire = ""
    finally:
        if provisoire and os.path.exists(provisoire):
            try:
                os.remove(provisoire)
            except Exception:
                pass
