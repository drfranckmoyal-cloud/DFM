"""Le registre des formateurs et les pieces qui justifient leur qualite.

POURQUOI CE MODULE EXISTE. L'indicateur 21 demande a l'organisme de prouver que
ceux qui interviennent en sont capables — CV, diplomes, attestations. DFM
connaissait le NOM du formateur et rien d'autre. Un nom dans une convention ne
prouve rien.

UNE PERSONNE, UN DOSSIER, PLUSIEURS ORGANISMES. Le registre etait cloisonne
jusqu'au 19/08/2026 : la meme personne y figurait autant de fois qu'elle
intervenait d'organismes, avec des pieces distinctes. La theorie disait qu'un
dossier partage serait « indefendable en audit ». La pratique a dit le
contraire : Franck MOYAL avait son CV et son diplome sous DSF, et une fiche
VIDE sous Smileclub. Deux dossiers pour un seul homme, dont un incomplet — et
c'est l'incomplet qu'un auditeur Smileclub aurait regarde.

Un CV ne change pas selon l'entite qui vous emploie. Il vit donc une fois.

LE RATTACHEMENT, LUI, RESTE PAR ORGANISME. Chaque organisme declare qui
intervient pour lui, et sur quelles formations :

    {identifiant: {nom, prenom, ..., cv, diplome, photo, autres,
                   organismes: {dsf: {formations: [...]}, ...}}}

Les formations sont communes aux deux entites ; dire « Franck enseigne Usures »
sans dire POUR QUI ferait pointer DSF vers l'intervenant de Smileclub. C'est la
meme famille de defaut que le cloisonnement corrige le 04/08/2026.

CE MODULE NE DETRUIT RIEN. Retirer une piece la deplace dans « documents/_corbeille »,
d'ou elle se reprend a la main — et cette corbeille-la n'expire pas.
"""
import json
import os
import re
import unicodedata

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "formateurs.json")

NOM_DOSSIER = "Dossier formateur"
PLAFOND = 20 * 1024 * 1024
PLAFOND_PHOTO = 5 * 1024 * 1024

# Les deux pieces qu'un auditeur reclame en premier. Leur absence n'empeche
# rien dans DFM : elle est SIGNALEE, ce qui est la seule chose utile.
OBLIGATOIRES = (("cv", "CV"), ("diplome", "Diplôme"))


# --------------------------------------------------------------- le registre

def _tout():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)


def _organisme(ident=None):
    if ident:
        return ident
    try:
        import profil
        return profil.actif()
    except Exception:
        return ""


def _identifiant(nom, prenom, existants):
    base = unicodedata.normalize("NFKD", ("%s-%s" % (prenom, nom)).lower())
    base = base.encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "formateur"
    ident, n = base, 2
    while ident in existants:
        ident, n = "%s-%d" % (base, n), n + 1
    return ident


def lister(organisme=None):
    """Les formateurs RATTACHES a cet organisme, manques deja calcules."""
    o = _organisme(organisme)
    sortie = [_enrichir(f, o) for f in _tout().values()
              if o in (f.get("organismes") or {})]
    sortie.sort(key=lambda f: (f.get("nom") or "").lower())
    return sortie


def tous(organisme=None):
    """TOUTES les personnes connues, rattachees ou non a cet organisme.

    Sert a l'ecran qui propose d'ajouter un intervenant deja enregistre
    ailleurs : sans cette liste, on recreerait la personne — et son dossier
    repartirait vide, ce qui est exactement le defaut qu'on vient de corriger.
    """
    o = _organisme(organisme)
    sortie = []
    for f in _tout().values():
        d = _enrichir(f, o)
        d["rattache"] = o in (f.get("organismes") or {})
        d["autres_organismes"] = sorted(x for x in (f.get("organismes") or {}) if x != o)
        sortie.append(d)
    sortie.sort(key=lambda f: (f.get("nom") or "").lower())
    return sortie


def un(ident, organisme=None):
    f = _tout().get(ident)
    return _enrichir(f, _organisme(organisme)) if f else None


def rattacher(ident, organisme=None, formations=None):
    """Declare qu'une personne deja connue intervient pour cet organisme."""
    o = _organisme(organisme)
    if not o:
        return None, "Aucun organisme actif."
    tout = _tout()
    f = tout.get(ident)
    if not f:
        return None, "Ce formateur n'existe pas."
    orgs = f.setdefault("organismes", {})
    if o in orgs:
        return _enrichir(f, o), ""
    orgs[o] = {"formations": list(formations or [])}
    _ecrire(tout)
    return _enrichir(f, o), ""


def _enrichir(fiche, organisme=None):
    """Ajoute ce qui se deduit : nom affichable, pieces manquantes, formations.

    LES FORMATIONS SONT CELLES DE L'ORGANISME DEMANDE. Le dossier est partage,
    le rattachement ne l'est pas : les rendre a plat melangerait les
    intervenants des deux entites sur une meme formation.
    """
    d = dict(fiche or {})
    orgs = d.get("organismes") or {}
    d["formations"] = list((orgs.get(organisme) or {}).get("formations") or []) \
        if organisme else []
    d["organismes_lies"] = sorted(orgs)
    civilite = (d.get("civilite") or "").strip()
    nom = ((d.get("prenom") or "") + " " + (d.get("nom") or "")).strip()
    d["nom_complet"] = ((civilite + " " + nom).strip()) or "Sans nom"
    d["manques"] = [libelle for cle, libelle in OBLIGATOIRES
                    if not str(d.get(cle) or "").strip()]
    d["sans_formation"] = not (d.get("formations") or [])
    d["a_photo"] = bool(str(d.get("photo") or "").strip())
    d["initiales"] = ((d.get("prenom") or " ")[:1] + (d.get("nom") or " ")[:1]).upper().strip()
    d.setdefault("photo", "")
    d.setdefault("autres", [])
    d.setdefault("formations", [])
    return d


def ajouter(nom, prenom, civilite="", fonction="", formations=None, organisme=None):
    o = _organisme(organisme)
    if not o:
        return None, "Aucun organisme actif."
    if not (nom or "").strip() and not (prenom or "").strip():
        return None, "Un formateur a besoin d'un nom."
    tout = _tout()
    ident = _identifiant(nom, prenom, tout)
    tout[ident] = {"id": ident, "nom": (nom or "").strip().upper(),
                   "prenom": (prenom or "").strip(), "civilite": (civilite or "").strip(),
                   "fonction": (fonction or "").strip(),
                   "organismes": {o: {"formations": list(formations or [])}},
                   "cv": "", "diplome": "", "photo": "", "autres": []}
    _ecrire(tout)
    return _enrichir(tout[ident], o), ""


_MODIFIABLES = ("nom", "prenom", "civilite", "fonction", "formations")


def enregistrer(ident, valeurs, organisme=None):
    """Met a jour la fiche. Liste blanche : les references des pieces
    ne se modifient QUE par depot ou retrait, jamais par un formulaire."""
    o = _organisme(organisme)
    tout = _tout()
    fiche = tout.get(ident)
    if not fiche:
        return None, "Ce formateur n'existe pas."
    for cle in _MODIFIABLES:
        if cle not in valeurs:
            continue
        v = valeurs[cle]
        if cle == "formations":
            # LES FORMATIONS S'ECRIVENT DANS LE RATTACHEMENT DE CET ORGANISME,
            # pas sur la personne : modifier la liste depuis Smileclub ne doit
            # rien changer a ce que DSF a declare.
            orgs = fiche.setdefault("organismes", {})
            orgs.setdefault(o, {})["formations"] = [str(x) for x in (v or [])]
        elif cle == "nom":
            fiche[cle] = str(v or "").strip().upper()
        else:
            fiche[cle] = str(v or "").strip()
    _ecrire(tout)
    return _enrichir(fiche, o), ""


def supprimer(ident, organisme=None):
    """Detache le formateur de CET organisme. Rend (ok, nom, formations_perdues).

    Les PIECES restent sur le disque.

    Volontaire : les justificatifs d'un formateur ayant reellement anime des
    sessions passees restent des preuves, meme s'il n'intervient plus.
    """
    o = _organisme(organisme)
    tout = _tout()
    fiche = tout.get(ident)
    if not fiche or o not in (fiche.get("organismes") or {}):
        return False, "Ce formateur n'intervient pas pour cet organisme.", []
    enrichie = _enrichir(fiche, o)
    nom = enrichie["nom_complet"]
    # CE QUI EST PERDU EST RENDU A L'APPELANT, pour qu'il l'inscrive au journal.
    # Detacher efface les formations declarees par CET organisme : rattacher la
    # personne ensuite la ramene sans elles. Constate le 19/08/2026 — meme
    # lecon que le remplacement d'un document le meme jour : ce qu'un geste
    # efface doit rester ecrit quelque part.
    formations = list(enrichie.get("formations") or [])
    # ON DETACHE, ON NE DETRUIT PAS. La personne reste connue des autres
    # organismes, et son dossier avec elle. Ne plus intervenir pour DSF n'efface
    # pas ce qu'on a anime pour Smileclub.
    del fiche["organismes"][o]
    _ecrire(tout)
    return True, nom, formations


# ------------------------------------------------------------ les pieces
#
# ELLES VIVENT SUR LE DISQUE, plus dans le Drive.
#
# CHANGE LE 18/08/2026. Le Drive etait ici la SEULE voie, pas un miroir : le
# jour ou l'autorisation Google a ete revoquee, deposer un CV est devenu
# impossible et la fiche affichait « dossier incomplet » sans qu'aucun geste
# puisse la completer. Une preuve de competence ne doit pas dependre d'un jeton.
#
# LE REGISTRE GARDE LES ANCIENS IDENTIFIANTS DRIVE. Ils ne ressemblent pas a une
# reference locale — ils n'ont pas de barre oblique — et rendent None : la piece
# s'affiche comme MANQUANTE, ce que le module a toujours fait d'une piece
# introuvable. On ne les efface pas : ils disent ou chercher si le Drive revient.

def _est_reference(x):
    """Une reference locale porte des barres obliques ; un identifiant Drive, non."""
    return "/" in str(x or "")


def _piece(ref):
    """Ce qu'il faut pour afficher une piece. None si elle n'est pas la."""
    if not _est_reference(ref):
        return None
    import documents
    d = documents.fiche_formateur(ref)
    if not d:
        return None
    # L'adresse porte l'identifiant du formateur : c'est lui qui permet a la
    # route de verifier que la piece appartient bien a ce dossier. Sans ce
    # controle, une reference etant un chemin, l'adresse d'une piece servirait
    # a lire n'importe quel document de DFM.
    # « _formateurs/<identifiant>/<nom> » : l'identifiant est le deuxieme
    # morceau depuis que le chemin ne porte plus l'organisme.
    bouts = str(ref).split("/")
    d["ident"] = bouts[1] if len(bouts) > 2 and bouts[0] == "_formateurs" else (
        bouts[2] if len(bouts) > 3 else "")
    # « id » EST la reference. L'ecran s'en sert pour demander un retrait, et
    # retirer() la recherche telle quelle dans la fiche : deux noms pour une
    # meme valeur eviteraient une conversion de plus, et donc un oubli de plus.
    d["id"] = ref
    d["lien"] = "/formateur/%s/piece?ref=%s" % (_quote(d["ident"]), _quote(ref))
    return d


def _quote(x):
    import urllib.parse
    return urllib.parse.quote(str(x or ""), safe="")


def pieces(ident, organisme=None):
    """Les pieces du formateur, rangees par role.

    Une piece effacee du disque rend None : le registre garde sa reference,
    l'ecran affiche le manque. Mieux vaut un manque visible qu'un lien mort.
    """
    f = un(ident, organisme)
    if not f:
        return {}
    return {"cv": _piece(f.get("cv")), "diplome": _piece(f.get("diplome")),
            "photo": _piece(f.get("photo")),
            "autres": [p for p in (_piece(x) for x in (f.get("autres") or [])) if p]}


def deposer(ident, role, nom, contenu, mimetype="", organisme=None):
    """Depose une piece. role : « cv », « diplome », « photo » ou « autre »."""
    if role not in ("cv", "diplome", "photo", "autre"):
        return None, "Type de pièce inconnu."
    if role == "photo":
        # Une photo qui n'est pas une image casserait silencieusement l'affichage :
        # mieux vaut le dire au depot qu'a l'ouverture de la fiche.
        if not (mimetype or "").startswith("image/"):
            return None, "La photo doit être une image (PNG, JPG…)."
        if len(contenu or b"") > PLAFOND_PHOTO:
            return None, ("Image trop lourde (%s). Une photo de profil n'a pas besoin "
                          "de dépasser 5 Mo." % _lisible(len(contenu)))
    if len(contenu or b"") > PLAFOND:
        return None, ("Fichier trop lourd (%s). Au-delà de 20 Mo, rangez-le "
                      "directement dans le dossier de l'organisme." % _lisible(len(contenu)))
    tout = _tout()
    fiche = tout.get(ident)
    if fiche is None:
        return None, "Ce formateur n'existe pas."

    # LE NOM DU FICHIER PORTE SON ROLE. Deux CV deposes l'un apres l'autre
    # ecrasaient le premier s'ils s'appelaient pareil ; et « scan.pdf » ne dit
    # a personne ce qu'il prouve. Le dossier d'un formateur se lit sans l'ouvrir.
    import os as _os
    racine, ext = _os.path.splitext(nom or "piece")
    if role in ("cv", "diplome"):
        nom_range = "%s - %s%s" % (role.upper() if role == "cv" else "Diplôme",
                                   _enrichir(fiche)["nom_complet"], ext)
    elif role == "photo":
        nom_range = "Photo - %s%s" % (_enrichir(fiche)["nom_complet"], ext)
    else:
        nom_range = nom or "piece"

    import documents
    ref, souci = documents.ranger_formateur(ident, nom_range, contenu)
    if not ref:
        return None, souci
    if role == "autre":
        fiche.setdefault("autres", [])
        if ref not in fiche["autres"]:
            fiche["autres"].append(ref)
    else:
        # CV, diplome et photo n'ont qu'une place : deposer remplace.
        # L'ancienne piece passe par la corbeille, jamais par la suppression —
        # c'est peut-etre elle qui prouvait une session deja animee.
        ancienne = fiche.get(role)
        if _est_reference(ancienne) and ancienne != ref:
            try:
                documents.ecarter_formateur(ancienne)
            except Exception:
                pass
        fiche[role] = ref
    _ecrire(tout)
    return _piece(ref), ""


def retirer(ident, id_piece, organisme=None):
    """Detache la piece de la fiche et la met a la corbeille.

    Refuse toute piece qui n'est pas rattachee A CE formateur : une reference
    erronee, et l'on ecarterait une convention.
    """
    tout = _tout()
    fiche = tout.get(ident)
    if not fiche:
        return False, "Ce formateur n'existe pas."
    connus = ([fiche.get("cv"), fiche.get("diplome"), fiche.get("photo")]
              + list(fiche.get("autres") or []))
    if id_piece not in [x for x in connus if x]:
        return False, "Cette pièce n'appartient pas au dossier de ce formateur."
    nom = id_piece
    if _est_reference(id_piece):
        import documents
        ok, nom = documents.ecarter_formateur(id_piece)
        if not ok:
            # La piece n'est plus sur le disque : on detache quand meme, sinon
            # la fiche garderait pour toujours une reference vers rien.
            nom = id_piece.rsplit("/", 1)[-1]
    for role in ("cv", "diplome", "photo"):
        if fiche.get(role) == id_piece:
            fiche[role] = ""
    fiche["autres"] = [x for x in (fiche.get("autres") or []) if x != id_piece]
    _ecrire(tout)
    return True, nom


def octets_photo(ident, organisme=None):
    """Le contenu binaire de la photo, pour la servir depuis DFM."""
    f = un(ident, organisme)
    ref = str((f or {}).get("photo") or "").strip()
    if not _est_reference(ref):
        return None, ""
    import documents
    p = documents.chemin(ref)
    if not p:
        return None, ""
    import mimetypes
    try:
        with open(p, "rb") as fh:
            return fh.read(), (mimetypes.guess_type(p)[0] or "image/jpeg")
    except Exception:
        return None, ""


def octets_vignette(ident, ref, organisme=None):
    """L'image d'apercu d'une piece, MAIS SEULEMENT SI ELLE EST A CE FORMATEUR."""
    f = un(ident, organisme)
    if not f:
        return None
    connus = [f.get("cv"), f.get("diplome"), f.get("photo")] + list(f.get("autres") or [])
    if ref not in [x for x in connus if x]:
        return None
    import documents
    return documents.vignette(ref)


def octets_piece(ident, ref, organisme=None):
    """Les octets d'une piece, MAIS SEULEMENT SI ELLE EST A CE FORMATEUR.

    Sans ce controle, la reference etant un chemin, l'adresse d'une piece
    servirait a lire n'importe quel document de DFM.
    """
    f = un(ident, organisme)
    if not f:
        return None, "", ""
    connus = [f.get("cv"), f.get("diplome"), f.get("photo")] + list(f.get("autres") or [])
    if ref not in [x for x in connus if x]:
        return None, "", ""
    import documents, mimetypes, os as _os
    p = documents.chemin(ref)
    if not p:
        return None, "", ""
    try:
        with open(p, "rb") as fh:
            return (fh.read(), mimetypes.guess_type(p)[0] or "application/octet-stream",
                    _os.path.basename(p))
    except Exception:
        return None, "", ""


def _lisible(octets):
    o = float(octets or 0)
    for unite in ("o", "Ko", "Mo"):
        if o < 1024 or unite == "Mo":
            return ("%d %s" if unite == "o" else "%.1f %s") % (o, unite)
        o /= 1024
    return "%d o" % octets



# ------------------------------------------------- formations sans formateur

def pour_formation(code_formation, organisme=None):
    """Le ou les formateurs designes pour cette formation, dans cet organisme."""
    return [f for f in lister(organisme) if code_formation in (f.get("formations") or [])]


def orphelines(organisme=None):
    """Les formations de la bibliotheque qu'aucun formateur ne couvre.

    Une formation sans formateur designe est un trou dans l'indicateur 21 : on
    ne peut prouver la competence de personne pour la delivrer.
    """
    try:
        from sessions import FORMATIONS
    except Exception:
        return []
    couvertes = set()
    for f in lister(organisme):
        couvertes.update(f.get("formations") or [])
    return [{"code": c, "nom": (FORMATIONS[c].get("nom_formation") or c)}
            for c in FORMATIONS if c not in couvertes]


def alertes(organisme=None):
    """Ce qui manque, en une liste de phrases prete a afficher."""
    sortie = []
    for f in lister(organisme):
        if f["manques"]:
            sortie.append("%s : %s manquant%s"
                          % (f["nom_complet"], " et ".join(f["manques"]).lower(),
                             "s" if len(f["manques"]) > 1 else ""))
        if f["sans_formation"]:
            sortie.append("%s n'est rattaché à aucune formation" % f["nom_complet"])
    for o in orphelines(organisme):
        sortie.append("La formation « %s » n'a aucun formateur désigné" % o["nom"])
    return sortie
