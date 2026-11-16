# -*- coding: utf-8 -*-
"""Les envois retenus : une facture ou une attestation prete, qui ne part pas
toute seule — 16/11/2026.

POURQUOI. Le passage du matin envoie toute facture rangee sur une ligne et pas
encore envoyee ; le mail de fin de formation part a tous. Rien ne permettait de
dire « celle-ci est prete, mais attends ». Cas reels, tous du 16/11/2026 :
- Cosme Etievant, oublie de la liste de la masterclass d'octobre et ajoute
  apres coup : sa facture est faite, Franck decidera quand elle part ;
- Quitterie de Villaucourt : sa facture corrigee remplace celle deja envoyee,
  et ne doit pas repartir sans son accord.

CE QUE CA RETIENT. Les envois AUTOMATIQUES seulement. Une selection explicite
depuis l'ecran (renvoi d'une attestation coche par coche) reste le choix du
responsable : elle passe.

LACHER UNE RETENUE, c'est la retirer : l'envoi part au passage suivant, comme
s'il n'avait jamais ete retenu.

Fichier : retenues.json, hors depot (des adresses de praticiens), sauvegarde.
    {"<session>": {"<mail en minuscules>": {"facture": "16/11/2026 — motif"}}}
"""
import os
from datetime import datetime

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER = os.path.join(DOSSIER, "retenues.json")
QUOI = ("facture", "attestation")


def _cle(mail):
    return (mail or "").strip().lower()


def _lire():
    import fichiers
    d = fichiers.lire(FICHIER, {})
    return d if isinstance(d, dict) else {}


def tout():
    return _lire()


def motif(code, mail, quoi):
    """Le motif de la retenue, ou "" quand rien n'est retenu."""
    return str(((_lire().get(code) or {}).get(_cle(mail)) or {}).get(quoi) or "")


def retenu(code, mail, quoi):
    return bool(motif(code, mail, quoi))


def retenir(code, mail, quoi, pourquoi):
    if quoi not in QUOI:
        raise ValueError("Envoi inconnu : %s" % quoi)
    if not _cle(mail):
        raise ValueError("Une retenue se pose sur une adresse.")
    import fichiers
    texte = "%s — %s" % (datetime.now().strftime("%d/%m/%Y"), (pourquoi or "retenu").strip())
    with fichiers.modifier(FICHIER, {}) as d:
        d.setdefault(code, {}).setdefault(_cle(mail), {})[quoi] = texte
    return texte


def lacher(code, mail, quoi):
    """Retire la retenue. Rend True si elle existait."""
    import fichiers
    with fichiers.modifier(FICHIER, {}) as d:
        fiche = (d.get(code) or {}).get(_cle(mail)) or {}
        if quoi not in fiche:
            return False
        del fiche[quoi]
        if not fiche:
            del d[code][_cle(mail)]
        if not d.get(code):
            d.pop(code, None)
        return True


def filtrer(code, lignes, quoi):
    """Les lignes dont l'envoi n'est pas retenu. Annonce celles qui le sont."""
    gardees = []
    for l in lignes:
        m = motif(code, l.get("mail"), quoi)
        if m:
            print("   (%s retenue pour %s %s : %s)" % (quoi, l.get("prenom", ""), l.get("nom", ""), m))
            continue
        gardees.append(l)
    return gardees
