"""Sceller le journal pour que toute alteration se voie.

CE QUE CELA PROUVE, ET CE QUE CELA NE PROUVE PAS. Il faut le dire d'emblee :
la cle du scelle vit sur la machine du proprietaire de l'installation. Elle ne
prouve donc RIEN CONTRE LUI — il peut recalculer toute la chaine. Ce n'est pas
un coffre-fort, c'est un plomb.

Ce qu'elle prouve reellement, et qui vaut la peine :

1. L'ALTERATION ACCIDENTELLE se voit. Ce n'est pas theorique dans DFM :
   l'onglet Journal de DSF a ete decale de cinq colonnes depuis sa creation
   sans que rien ne le signale, et le journal a ete illisible pendant des
   semaines. Une chaine l'aurait dit le premier jour.
2. LA SUPPRESSION D'UNE LIGNE se voit — c'est le point. Un scelle pose ligne
   par ligne, sans chainage, laisse retirer une entree genante sans trace.
   Ici chaque entree scelle le RANG et l'empreinte de la precedente : retirer
   la ligne 50 rompt tout ce qui suit.
3. UNE MODIFICATION PAR UN TIERS se voit — un classeur Google se partage, et
   la piste d'audit n'a pas a etre la seule chose que l'on ne verifie jamais.
4. ON PEUT LE MONTRER. « 185 entrees, chaine intacte » est une phrase qu'un
   auditeur comprend, et qu'aucun ecran de DFM ne savait dire.

LA CLE EST DISTINCTE DU MOT DE PASSE. Changer le mot de passe d'acces ne doit
pas invalider dix-huit mois de journal.

DEUX APPELS PAR ENTREE. Le rang d'une ligne n'est connu qu'apres l'avoir
ajoutee : on ajoute, Google repond « ligne 186 », on scelle. C'est le prix de
la resistance a l'ecriture concurrente — dfm.py et Flask ecrivent parfois en
meme temps, et un chainage calcule AVANT l'ajout forkerait la chaine en
signalant une fraude la ou il n'y a qu'un croisement.
"""
import hashlib
import hmac
import json
import os
import secrets

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "scellement.json")

COLONNE = "J"           # la colonne du scelle dans l'onglet Journal
_LONGUEUR = 20          # 80 bits : de quoi rendre une collision hors de portee
_RACINE = "0" * _LONGUEUR   # l'ancetre de la premiere ligne


def _etat():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire_etat(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)
    try:
        os.chmod(_FICHIER, 0o600)
    except Exception:
        pass


def cle():
    """La cle de scellement, creee au premier usage et jamais reecrite.

    La perdre rendrait tout le journal invérifiable : le fichier est donc en
    0600 et fait partie de ce qu'il faut sauvegarder, au meme titre que
    credentials.json.
    """
    d = _etat()
    k = d.get("cle")
    if not k:
        k = secrets.token_hex(32)
        d["cle"] = k
        _ecrire_etat(d)
    return k.encode("utf-8")


LARGEUR = 9             # colonnes A a I : le contenu scelle, hors scelle lui-meme


def empreinte(rang, valeurs, precedent):
    """Le scelle d'une ligne : son rang, son contenu, et son ancetre.

    Le rang entre dans le calcul pour que retirer une ligne — ce qui decale
    toutes les suivantes — se voie, et pas seulement pour que modifier une
    ligne se voie.

    LA NORMALISATION EST FAITE ICI, jamais chez l'appelant. Google supprime les
    cellules vides en fin de ligne : une entree ecrite avec neuf valeurs peut
    revenir avec six. Scelle a l'ecriture sur six et verifie plus tard sur neuf,
    elle serait declaree alteree sans que personne n'y ait touche — une fausse
    alerte sur une piste d'audit est pire que pas d'alerte du tout.
    """
    plates = [str(v or "") for v in (valeurs or [])][:LARGEUR]
    plates += [""] * (LARGEUR - len(plates))
    corps = "\x1f".join([str(rang)] + plates + [str(precedent or "")])
    return hmac.new(cle(), corps.encode("utf-8"), hashlib.sha256).hexdigest()[:_LONGUEUR]


def demarrage(feuille=""):
    """Depuis quand cette feuille est scellee, et comment.

    « pose_le » dit quand le scelle a ete appose sur les entrees ANCIENNES.
    Cette date doit rester visible : un scelle pose apres coup n'atteste que de
    l'etat du jour ou il a ete pose, jamais de ce qui s'est passe avant.
    """
    return (_etat().get("feuilles") or {}).get(feuille or "", {})


def noter_demarrage(feuille, jusqu_a_la_ligne, pose_le):
    d = _etat()
    d.setdefault("feuilles", {})[feuille] = {"retroactif_jusqu_a": jusqu_a_la_ligne,
                                             "pose_le": pose_le}
    _ecrire_etat(d)
