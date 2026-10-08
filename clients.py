"""Base clients : les structures qui achetent une formation pour leurs praticiens.

DISTINCTE DE LA BASE APPRENANTS. Un client est une personne morale — un centre
de sante, un cabinet de groupe. Il ne se forme pas : il achete. Ce sont ses
praticiens qui se forment, et ceux-la sont des apprenants ordinaires.

STOCKAGE LOCAL, dans clients.json. Quelques dizaines d'enregistrements, jamais
filtres en masse, mais lus a la creation d'une session : Supabase y ajouterait
une dependance reseau pour vingt lignes. Ecriture atomique, comme marqueurs.json.

CHAQUE CLIENT CREE SON MARQUEUR. Poser le marqueur du centre sur les fiches de
ses praticiens est le geste attendu ; le faire a la main pour chaque client
serait une corvee et un oubli. Le marqueur est de type « client » : il ne se
melange pas a ceux que l'utilisateur cree lui-meme.

SUPPRIMER UN CLIENT NE SUPPRIME PAS SON MARQUEUR — jamais, et sans proposition.
Il se detache et redevient un marqueur ordinaire. Les praticiens qui le portent
le gardent : ils ont bien ete formes par ce centre, meme si l'on cesse de
travailler avec lui. C'est a l'utilisateur de le retirer, fiche par fiche, s'il
le decide.
"""
import json
import os
import re
import unicodedata
from datetime import datetime

import contacts as C

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "clients.json")

# Ce qu'une structure doit porter. La raison sociale seule est obligatoire :
# un client saisi dans l'urgence avec le seul nom du centre vaut mieux qu'un
# client qu'on renonce a saisir parce qu'il manque le FINESS.
CHAMPS = [
    # DEUX NOMS, ET C'EST VOULU. Le nom d'usage est celui qu'on emploie —
    # « Centre Bagneux » — et c'est lui qui s'affiche partout, qui nomme le
    # marqueur et qui sert a chercher. La raison sociale est le nom de la
    # personne morale ; elle ne sert qu'aux DOCUMENTS CONTRACTUELS, ou nommer
    # la structure autrement que par son nom legal fragiliserait l'acte.
    ("nom_usage", "Nom d'usage", True),
    # « Denomination » est le terme des associations loi 1901, « raison
    # sociale » celui des societes. Les deux sont nommes pour que personne ne
    # se demande si le champ le concerne.
    ("raison_sociale", "Raison sociale ou dénomination", True),
    ("adresse", "Adresse du siège", False),
    # SIRET et non SIREN : les clients sont majoritairement des associations
    # loi 1901, et c'est le SIRET — 14 chiffres, etablissement compris — qui
    # figure sur une convention et sur une facture.
    ("siret", "SIRET", False),
    # Une convention de formation nomme les deux parties de la meme facon :
    # « represente par X, en sa qualite de Y ». Le nom seul ne suffit pas a
    # rediger l'acte — c'est la fonction qui etablit que la personne engage
    # la structure.
    ("representant", "Représentant légal", False),
    ("representant_fonction", "Fonction du représentant", False),
    # UNE SEULE adresse mail. Deux champs — l'un pour la signature, l'autre
    # pour la facture — invitaient a se demander lequel remplir, et a n'en
    # remplir qu'un. Le client n'a qu'un interlocuteur : c'est lui.
    ("mail", "Adresse mail (signature, factures, échanges)", False),
    ("telephone", "Téléphone du client", False),
    # La prise en charge OPCO est PLAFONNEE PAR ANNEE CIVILE. C'est ce plafond
    # qui dit si une structure peut encore commander cette annee, ou s'il vaut
    # mieux reporter en janvier.
    ("plafond_opco", "Plafond annuel OPCO", False),
]
# Fonctions courantes, proposees plutot que saisies. « Autre » ouvre un champ
# libre : une association loi 1901 peut avoir un tresorier signataire, un
# secretaire general, un gerant.
CHOIX = {"representant_fonction": ["Président", "Présidente", "Directeur", "Directrice"],
         "plafond_opco": ["15 000 €", "30 000 €"]}
# Listes fermees : aucun « Autre… » n'y est propose. Le plafond OPCO ne prend
# que ces deux valeurs ; en ouvrir une troisieme par megarde fausserait le
# suivi sans que rien ne le signale.
# Aucune liste fermee. Le plafond OPCO a d'abord ete bride a deux valeurs ;
# la reprise du fichier des centres en a fait apparaitre une troisieme —
# 7 500 € — et rien ne garantit qu'il n'y en aura pas d'autres. Les deux
# valeurs courantes restent proposees, « Autre… » ouvre la saisie.
CHOIX_STRICT = set()


def plafond(fiche):
    """Le plafond en euros, 0 si non renseigne. On lit les chiffres plutot que
    de stocker un nombre a cote du libelle : une seule valeur, donc aucun
    risque qu'elles divergent."""
    chiffres = re.sub(r"[^0-9]", "", (fiche or {}).get("plafond_opco") or "")
    return int(chiffres) if chiffres else 0
OBLIGATOIRES = [c for c, _, o in CHAMPS if o]


def _identifiant(nom):
    s = unicodedata.normalize("NFD", str(nom or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def _ecrire(tout):
    """Ecriture atomique : une coupure laisse l'ancien fichier intact, jamais
    un fichier a moitie ecrit."""
    import fichiers
    fichiers.ecrire(_FICHIER, tout)


def tous():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return {}
    except Exception:
        return {}
    # Reprise silencieuse des fiches ecrites avant le passage SIREN -> SIRET :
    # la valeur est conservee plutot que perdue, meme si un SIREN n'a que neuf
    # chiffres. L'utilisateur completera, il ne resaisira pas.
    for fiche in d.values():
        if "siren" in fiche and not fiche.get("siret"):
            fiche["siret"] = fiche.pop("siren")
        if fiche.get("representant_qualite") and not fiche.get("representant_fonction"):
            fiche["representant_fonction"] = fiche["representant_qualite"]
        # Les deux anciennes adresses fusionnent : celle du representant
        # d'abord, c'est elle qui signait ; la comptable a defaut.
        if not fiche.get("mail"):
            fiche["mail"] = fiche.get("representant_mail") or fiche.get("facturation_mail") or ""
        if not fiche.get("telephone"):
            fiche["telephone"] = fiche.get("facturation_tel") or ""
        if not fiche.get("nom_usage"):
            fiche["nom_usage"] = fiche.get("raison_sociale") or ""
        for perime in ("siren", "representant_qualite", "representant_mail",
                       "facturation_nom", "facturation_mail", "facturation_tel", "finess"):
            fiche.pop(perime, None)
    return d


def liste():
    return sorted(tous().values(),
                  key=lambda c: (c.get("nom_usage") or c.get("raison_sociale") or "").upper())


def client(identifiant):
    return tous().get(identifiant)


def _nettoyer(donnees):
    d = {cle: (donnees.get(cle) or "").strip() for cle, _, _ in CHAMPS}
    # Fiches ecrites avant l'existence du nom d'usage : la raison sociale en
    # tient lieu, pour qu'aucune fiche ne se retrouve sans nom affichable.
    if not d.get("nom_usage"):
        d["nom_usage"] = d.get("raison_sociale") or ""
    return d


def creer(donnees):
    fiche = _nettoyer(donnees)
    if not fiche["raison_sociale"]:
        raise ValueError("La raison sociale est obligatoire.")
    ident = _identifiant(fiche["nom_usage"])
    if not ident:
        raise ValueError("Cette raison sociale ne donne aucun identifiant utilisable.")
    tout = tous()
    if ident in tout:
        raise ValueError("Un client porte déjà ce nom.")
    # Le marqueur suit le client, et porte son nom. S'il existe deja — parce
    # que l'utilisateur l'avait cree a la main — on le REPREND plutot que d'en
    # fabriquer un second qui ferait doublon dans la barre de filtres.
    cle_marqueur = C.cle_marqueur(fiche["nom_usage"])
    if not C.marqueur(cle_marqueur):
        C.creer_marqueur(fiche["nom_usage"])
    C.typer_marqueur(cle_marqueur, "client", ident)
    fiche.update({"id": ident, "marqueur": cle_marqueur,
                  "cree_le": datetime.now().strftime("%d/%m/%Y"),
                  "maj_le": datetime.now().strftime("%d/%m/%Y")})
    tout[ident] = fiche
    _ecrire(tout)
    return fiche


def modifier(identifiant, donnees):
    tout = tous()
    fiche = tout.get(identifiant)
    if not fiche:
        raise ValueError("Client introuvable.")
    neuf = _nettoyer(donnees)
    if not neuf["raison_sociale"]:
        raise ValueError("La raison sociale est obligatoire.")
    # Renommer le client renomme SON marqueur, sans changer la cle : les fiches
    # qui le portent restent rattachees.
    if neuf["nom_usage"] != (fiche.get("nom_usage") or fiche.get("raison_sociale")) \
            and fiche.get("marqueur"):
        C.renommer_marqueur(fiche["marqueur"], neuf["nom_usage"])
    fiche.update(neuf)
    fiche["maj_le"] = datetime.now().strftime("%d/%m/%Y")
    tout[identifiant] = fiche
    _ecrire(tout)
    return fiche


def supprimer(identifiant):
    """Retire le client. LE MARQUEUR RESTE, et redevient ordinaire.

    Aucune fiche de contact n'est touchee : les praticiens gardent le marqueur.
    C'est un choix explicite de l'utilisateur — supprimer un client ne doit pas
    effacer le fait que ces praticiens ont ete formes par ce centre."""
    tout = tous()
    fiche = tout.pop(identifiant, None)
    if not fiche:
        return None
    if fiche.get("marqueur"):
        C.typer_marqueur(fiche["marqueur"], "", "")     # il redevient libre
    _ecrire(tout)
    return fiche


def par_marqueur(cle):
    for f in tous().values():
        if f.get("marqueur") == cle:
            return f
    return None


def complet(fiche):
    """Ce qui manque pour editer une convention et une facture au nom du centre.
    Signale, ne bloque pas : on peut creer un client incomplet et le completer
    avant d'emettre les documents."""
    manques = []
    for cle in ("adresse", "siret", "representant", "representant_fonction", "mail"):
        if not (fiche.get(cle) or "").strip():
            manques.append(dict((c, l) for c, l, _ in CHAMPS)[cle].split(" —")[0].split(" (")[0])
    return manques
