import json
import os
from datetime import datetime as _datetime
import re
_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bibliotheque.json")
_TYPES = ("evaluation", "satisfaction", "froid")
def charger():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            tout = json.load(f)
    except Exception:
        tout = {}
    for t in _TYPES:
        if not isinstance(tout.get(t), dict):
            tout[t] = {}
    return tout
def enregistrer(tout):
    import fichiers
    fichiers.ecrire(_FICHIER, tout)
def lister(type_):
    tout = charger()
    sortie = []
    for cle, fiche in (tout.get(type_) or {}).items():
        f = dict(fiche)
        f["id"] = cle
        sortie.append(f)
    sortie.sort(key=lambda x: (x.get("titre") or "").lower())
    return sortie
def modele(type_, identifiant):
    if not identifiant:
        return None
    fiche = (charger().get(type_) or {}).get(identifiant)
    if not fiche:
        return None
    f = dict(fiche)
    f["id"] = identifiant
    return f
def nouvel_id(type_, titre):
    base = re.sub(r"[^a-z0-9]+", "-", (titre or "modele").lower()).strip("-") or "modele"
    tout = charger()
    existants = tout.get(type_) or {}
    if base not in existants:
        return base
    n = 2
    while (base + "-" + str(n)) in existants:
        n += 1
    return base + "-" + str(n)
def sauver(type_, identifiant, fiche):
    tout = charger()
    if not identifiant:
        identifiant = nouvel_id(type_, fiche.get("titre"))
    # Date de derniere modification : sans elle, impossible de savoir dans la
    # bibliotheque lequel de deux modeles proches est le plus recent.
    fiche = dict(fiche)
    fiche["modifie_le"] = _datetime.now().strftime("%d/%m/%Y %H:%M")
    tout.setdefault(type_, {})[identifiant] = fiche
    enregistrer(tout)
    return identifiant
def supprimer(type_, identifiant):
    tout = charger()
    if identifiant in (tout.get(type_) or {}):
        del tout[type_][identifiant]
        enregistrer(tout)
        return True
    return False
def utilise_par(type_, identifiant):
    try:
        from sessions import FORMATIONS
    except Exception:
        return []
    cle = {"evaluation": "modele_evaluation", "satisfaction": "modele_satisfaction",
           "froid": "modele_froid"}.get(type_, "modele_satisfaction")
    return [code for code, f in FORMATIONS.items() if (f or {}).get(cle) == identifiant]
