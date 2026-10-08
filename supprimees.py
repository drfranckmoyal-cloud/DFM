"""Retrouver les sessions supprimees et leurs pieces.

POURQUOI CE MODULE EXISTE. Supprimer une session retire son entree de
sessions.json, mais NE DETRUIT RIEN : l'onglet de suivi est renomme
« ZZ-supprimee-… » quand il porte des inscrits, et les documents restent sur le
Drive. C'est prudent, et c'est ce qu'il fallait faire.

Le defaut etait ailleurs : plus aucun ecran ne savait que ces onglets
existaient. Les preuves survivaient, mais devenaient introuvables — un
controleur Qualiopi demandant le dossier d'une formation supprimee mettait
l'organisme en defaut alors que tout etait conserve.

CE MODULE NE FAIT QUE LIRE. Aucune ecriture, aucune restauration : ce n'est pas
une corbeille, c'est une piece d'archive. Restaurer supposerait de decider quoi
faire d'un code de session peut-etre reutilise depuis, et cette decision-la ne
se prend pas dans un ecran.

IL PARCOURT LES DEUX ORGANISMES, sans tenir compte du profil actif : une
session supprimee n'appartient plus a rien, et la chercher la ou l'on se trouve
serait la manquer une fois sur deux.
"""
import re

_PREFIXE = "ZZ-supprimee-"


def _organismes():
    try:
        import profil
        sortie = []
        for p in profil.lister():
            ident = p["id"] if isinstance(p, dict) else p
            fiche = profil.charger(ident) or {}
            if fiche:
                sortie.append((ident, fiche))
        return sortie
    except Exception:
        return []


def _code_probable(onglet):
    """« ZZ-supprimee-Usures-nov26 » -> « usures-nov26 ».

    Le nom de l'onglet est bati sur « <Formation>-<code_session> » ; le code de
    session d'origine ne s'y retrouve pas toujours a l'identique, d'ou le mot
    « probable ». Il sert a chercher les dossiers Drive, jamais a decider.
    """
    reste = onglet[len(_PREFIXE):] if onglet.startswith(_PREFIXE) else onglet
    return reste.lower()


def lister():
    """Les sessions supprimees dont il reste une trace, la plus recente d'abord.

    Rend, pour chacune : l'organisme, le nom de l'onglet, le nombre d'inscrits,
    leurs noms, et les dossiers Drive qui portent encore ses pieces.
    """
    # LES INSCRITS CONSERVES VIENNENT DE LA BASE. Cette fonction balayait les
    # onglets des deux classeurs Google pour retrouver ceux prefixes
    # « ZZ-supprimee- », puis lisait chacun : l'ecran tombait entierement des
    # que Google ne repondait pas. Ces inscrits ont ete repris dans la base avec
    # leur onglet pour code — precisement pour ne pas les confondre avec ceux
    # d'une session vivante.
    import base as _base
    sorties = []
    par_organisme = {}
    for org, code, _n in _base.suivi_sessions():
        if code.startswith(_PREFIXE):
            par_organisme.setdefault(org, []).append(code)
    for ident, fiche in _organismes():
        for titre in sorted(par_organisme.get(ident, [])):
            lignes = [d for _numero, d in _base.suivi_lire(ident, titre)
                      if str(d.get("horodateur") or "").strip()]
            sorties.append({
                "feuille": fiche.get("sheet_suivi") or "",
                "organisme": ident,
                "organisme_nom": fiche.get("marque") or ident,
                "onglet": titre,
                "nom_lisible": titre[len(_PREFIXE):],
                "code_probable": _code_probable(titre),
                "inscrits": len(lignes),
                "lignes": lignes,
                "gens": [((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip()
                         for l in lignes],
            })
    return sorted(sorties, key=lambda s: s["nom_lisible"], reverse=True)


def une(onglet):
    return next((s for s in lister() if s["onglet"] == onglet), None)


def dossiers_drive(fiche_supprimee):
    """Les dossiers Drive qui portent encore les pieces de cette session.

    Cherches PAR NOM sous les dossiers de production de l'organisme concerne :
    la session n'existe plus, on n'a donc plus d'identifiant a suivre. C'est le
    seul endroit de DFM ou la recherche par nom reste la bonne methode, faute
    de mieux.
    """
    from connexion import service_drive
    import dossiers as _dos
    dr = service_drive()
    try:
        import profil
        o = profil.charger(fiche_supprimee["organisme"]) or {}
    except Exception:
        o = {}
    trouves = []
    attendu = fiche_supprimee["nom_lisible"].lower()
    for cle, libelle in (("dossier_conventions", "Conventions générées"),
                         ("dossier_signees", "Conventions signées"),
                         ("dossier_factures", "Factures"),
                         ("dossier_attestations", "Attestations"),
                         ("dossier_emargement", "Émargement")):
        parent = (o.get(cle) or "").strip()
        if not parent:
            continue
        try:
            enfants = dr.files().list(
                q="'%s' in parents and trashed=false" % parent,
                fields="files(id,name,mimeType)", pageSize=200).execute().get("files", [])
        except Exception:
            continue
        for f in enfants:
            if attendu not in f["name"].lower():
                continue
            nb = 0
            if f["mimeType"].endswith("folder"):
                try:
                    nb = len(dr.files().list(q="'%s' in parents and trashed=false" % f["id"],
                                             fields="files(id)", pageSize=200
                                             ).execute().get("files", []))
                except Exception:
                    nb = 0
            trouves.append({"rubrique": libelle, "nom": f["name"], "id": f["id"],
                            "pieces": nb,
                            "lien": "https://drive.google.com/drive/folders/" + f["id"]
                                    if f["mimeType"].endswith("folder")
                                    else "https://drive.google.com/file/d/" + f["id"] + "/view"})
    return trouves
