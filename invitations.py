# -*- coding: utf-8 -*-
"""Les invitations lancees AVANT toute inscription.

Franck invite quelqu'un en donnant son adresse, rien de plus. La personne
recoit le formulaire d'inscription habituel, le remplit elle-meme — c'est elle
qui connait son nom, sa fonction, ses contraintes alimentaires — et sa ligne
nait dans le suivi DEJA marquee « invitee », sans somme a payer.

POURQUOI UN REGISTRE DANS DFM, ET PAS UN JETON DANS LE LIEN. Le lien du
formulaire est public et voyage par mail : un « &invite=1 » colle au bout
s'ajoute en trois secondes, se transmet, et offrirait une place gratuite a qui
veut. Ici c'est DFM qui sait qui il a invite. Le lien reste le lien ordinaire,
et une invitation transferee a un tiers ne lui donne rien : il s'inscrira sous
sa propre adresse, et paiera comme tout le monde.

L'ADRESSE EST LA CLE, comme partout dans DFM : deux inscrits ne partagent
jamais une adresse. Elle est rangee en minuscules — une invitation envoyee a
« Nom@Exemple.fr » doit reconnaitre l'inscription faite depuis
« nom@exemple.fr ».

UNE INVITATION SE CONSOMME. Des que l'inscription est reprise, elle porte sa
date de reprise et ne s'applique plus : si la meme personne se reinscrit un an
plus tard sur une autre session, elle n'herite pas de la gratuite de celle-ci.
Elle reste au registre, elle n'est pas effacee — c'est la trace de qui a ete
invite, par qui, et quand.
"""
import os as _os
import re as _re
from datetime import datetime

import fichiers

_DOSSIER = _os.path.dirname(_os.path.abspath(__file__))
FICHIER = _os.path.join(_DOSSIER, "invitations.json")

# Volontairement permissive : elle ecarte la faute de frappe evidente (pas
# d'arobase, pas de point apres) sans pretendre valider une adresse, ce que
# seul un envoi reussi fait vraiment.
_FORME = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _propre(mail):
    return str(mail or "").strip().lower()


def forme_valide(mail):
    return bool(_FORME.match(_propre(mail)))


def lister(code_session):
    """Les invitations de cette session, la plus recente d'abord."""
    lot = (fichiers.lire(FICHIER, {}).get(code_session) or {})
    sortie = []
    for mail, d in lot.items():
        e = dict(d or {})
        e["mail"] = mail
        sortie.append(e)
    sortie.sort(key=lambda e: e.get("le") or "", reverse=True)
    return sortie


def en_attente(code_session):
    """Les invitations qui n'ont pas encore donne d'inscription."""
    return [e for e in lister(code_session) if not e.get("reprise_le")]


def pour(code_session, mail):
    """L'invitation EN ATTENTE de cette adresse, ou None.

    C'est la question que pose l'import : « cette inscription qui arrive
    repond-elle a une invitation ? »
    """
    m = _propre(mail)
    d = (fichiers.lire(FICHIER, {}).get(code_session) or {}).get(m)
    if not d or d.get("reprise_le"):
        return None
    e = dict(d)
    e["mail"] = m
    return e


def poser(code_session, mail, par=""):
    """Inscrit l'invitation au registre.

    Rend (nouvelle, quand) : nouvelle vaut faux quand on renvoie le mail a
    quelqu'un de deja invite. La DATE D'ORIGINE est alors conservee — c'est
    elle qui devient « invitee depuis le » sur la fiche, et un renvoi ne doit
    pas faire croire a une invitation du jour.
    """
    m = _propre(mail)
    quand = datetime.now().strftime("%d/%m/%Y %H:%M")
    with fichiers.modifier(FICHIER, {}) as tout:
        lot = tout.setdefault(code_session, {})
        deja = lot.get(m) or {}
        nouvelle = (not deja) or bool(deja.get("reprise_le"))
        if nouvelle:
            lot[m] = {"le": quand, "par": par or "", "reprise_le": "",
                      "renvois": 0, "dernier_envoi": quand}
        else:
            deja["renvois"] = int(deja.get("renvois") or 0) + 1
            deja["dernier_envoi"] = quand
            lot[m] = deja
    return nouvelle, (lot[m].get("le") or quand)


def consommer(code_session, mail, numero=None):
    """Note que l'invitation a donne une inscription, et ne s'applique plus."""
    m = _propre(mail)
    quand = datetime.now().strftime("%d/%m/%Y %H:%M")
    with fichiers.modifier(FICHIER, {}) as tout:
        d = (tout.get(code_session) or {}).get(m)
        if not d:
            return False
        d["reprise_le"] = quand
        if numero is not None:
            d["ligne"] = numero
    return True


def retirer(code_session, mail):
    """Annule une invitation lancee par erreur, avant toute inscription.

    Apres l'inscription, il n'y a plus rien a retirer ici : c'est la case
    « invitee » de la ligne qui commande, et elle se retire depuis la fiche.
    """
    m = _propre(mail)
    with fichiers.modifier(FICHIER, {}) as tout:
        lot = tout.get(code_session) or {}
        if m not in lot:
            return False
        if lot[m].get("reprise_le"):
            return False
        del lot[m]
        if not lot:
            tout.pop(code_session, None)
    return True
