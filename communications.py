"""Les modeles de communication : messages qui ne dependent d'aucune session.

POURQUOI UNE FAMILLE A PART. Les mails du parcours — convention, facture,
attestation — portent des balises de session : titre de formation, dates,
montant, lien de signature. Une communication n'a rien de tout cela. Les
melanger dans le meme editeur reviendrait a proposer des balises qui ne
seraient jamais remplies, et un message partirait un jour avec des trous.

UNE SEULE BALISE ICI : {{marque}}, le nom de l'organisme qui envoie. Aucune
personnalisation du destinataire — mesure du 04/08/2026, 174 contacts sur 181
n'ont pas de prenom — et pas de bloc de signature : c'est l'organisme qui
communique, pas une personne.

LE PIED N'EST PAS DANS LE MODELE. Identite, mention d'origine et lien de
desinscription sont ajoutes a l'envoi par campagnes.pied(). Un modele ne peut
donc pas les omettre, meme ecrit a la hate.
"""
import json
import os
import re
import unicodedata
from datetime import datetime

_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "communications.json")

BALISES = ["{{marque}}"]

# Les blocs proposes pour une communication. Volontairement PLUS COURT que le
# catalogue des mails de parcours : ni signature — c'est l'organisme qui ecrit,
# pas une personne — ni tableau, ni texte automatique, qui n'ont pas de sens
# hors d'une session.
BLOCS = ["texte", "image", "colonnes", "bouton", "encadre", "espace", "lien"]

MODELE_NEUF = [
    {"type": "texte", "contenu": "Bonjour,\n\nVotre message ici."},
]

# PIECES JOINTES : deux poids, deux mesures.
#
# Une piece ATTACHEE part avec chaque exemplaire du message. Sur 178
# destinataires, un PDF d'un mega represente 178 megas expedies : l'envoi
# s'allonge, et les filtres anti-spam regardent de travers un mail lourd
# adresse a beaucoup de monde.
#
# Un LIEN ne pese rien, se telecharge quand le destinataire le decide, et
# permet de corriger le document apres l'envoi sans renvoyer le mail.
#
# D'ou le seuil : au-dela, DFM recommande le lien. Il ne l'impose pas — c'est
# votre courrier.
SEUIL_PIECE = 1 * 1024 * 1024      # 1 Mo
PLAFOND_PIECE = 10 * 1024 * 1024   # 10 Mo, au-dela Gmail refuse souvent


def poids_lisible(octets):
    o = float(octets or 0)
    for unite in ("o", "Ko", "Mo"):
        if o < 1024 or unite == "Mo":
            return ("%.0f %s" if unite == "o" else "%.1f %s") % (o, unite)
        o /= 1024
    return "%.1f Mo" % o


def poids_total(pieces):
    return sum(int(p.get("taille") or 0) for p in (pieces or [])
               if (p.get("mode") or "jointe") == "jointe")


def tout():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)


def cle(titre):
    """« Programme du second semestre » -> « programme-du-second-semestre »."""
    s = unicodedata.normalize("NFD", str(titre or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]
    return s or datetime.now().strftime("modele-%Y%m%d%H%M%S")


def lister():
    """Les modeles, le plus recemment modifie d'abord."""
    return sorted(tout().values(), key=lambda m: m.get("modifie_le") or "", reverse=True)


def un(identifiant):
    return tout().get(identifiant)


def enregistrer(identifiant, titre, objet, blocs=None, corps="", pieces=None):
    """Cree ou met a jour. Rend l'identifiant retenu.

    LE MESSAGE EST FAIT DE BLOCS, pas de HTML tape a la main. Un mail n'est pas
    une page web : Outlook ignore flexbox, grid, et la moitie du CSS moderne.
    Les blocs produisent un HTML a base de tableaux et de styles en ligne, seul
    terrain sur lequel tous les clients s'accordent.

    LE HTML RENDU EST STOCKE A COTE. C'est lui que l'envoi utilise : recalculer
    au moment de partir exposerait a un changement de moteur entre l'apercu et
    l'envoi reel.

    L'identifiant NE CHANGE PAS au renommage : une campagne archivee garde une
    reference utile, et renommer un modele ne doit rien casser.
    """
    import mails
    d = tout()
    ident = (identifiant or "").strip() or cle(titre)
    ancien = d.get(ident) or {}
    blocs = blocs if isinstance(blocs, list) else (ancien.get("blocs") or [])
    rendu = (corps or "").strip() or mails.html_depuis_blocs(blocs)
    d[ident] = {
        "id": ident,
        "titre": (titre or "").strip() or "Sans titre",
        "objet": (objet or "").strip(),
        "blocs": blocs,
        "corps": rendu,
        "pieces": pieces if isinstance(pieces, list) else (ancien.get("pieces") or []),
        "cree_le": ancien.get("cree_le") or datetime.now().strftime("%d/%m/%Y %H:%M"),
        "modifie_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    _ecrire(d)
    return ident


def supprimer(identifiant):
    d = tout()
    if identifiant in d:
        del d[identifiant]
        _ecrire(d)
        return True
    return False
