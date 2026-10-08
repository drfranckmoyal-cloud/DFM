"""Base de contacts : prospects et annotations des apprenants.

POURQUOI CE MODULE EXISTE. Les apprenants vivent dans le classeur de suivi,
qui reste la source de verite des inscriptions — conventions, reglements et
factures en dependent. Les prospects n'ont rien a y faire : ni session, ni
convention, ni reglement. Ils vivent ici, dans Supabase.

L'ecran « Bases de donnees » joint les deux a l'affichage. Une personne, une
fiche, quel que soit le cote d'ou elle vient.

UNE FICHE PEUT AUSSI N'ETRE QU'UNE ANNOTATION. Un apprenant connu du seul
classeur qui recoit un marqueur obtient ici une fiche ne portant que sa cle de
rapprochement et ses marqueurs — pas une copie de son identite, qui resterait
a se desynchroniser. Aucune information n'existe a deux endroits.

CE QUI PROTEGE L'ACCES. La table est creee avec la securite au niveau des
lignes ACTIVEE et sans aucune regle : seule la cle secrete y accede, et une
cle publique n'y lirait rien. Voir la note de securite dans README-CONTACTS.

LE CATALOGUE DES MARQUEURS EST LOCAL (marqueurs.json), leur ATTRIBUTION est
dans Supabase. C'est le choix de l'utilisateur, et il se defend : le catalogue
est minuscule et se consulte a chaque affichage, l'attribution doit se filtrer
cote serveur. Le lien se fait par une cle stable — « ancien-apprenant » — et
non par le libelle, de sorte qu'un renommage ne casse rien.
"""
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import reseau
from datetime import datetime

import doublons

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_MARQUEURS = os.path.join(_DOSSIER, "marqueurs.json")

TABLE = "Contacts"

# Marqueurs presents au premier lancement : les marqueurs sont POSES A LA MAIN,
# et rien d'autre n'a sa place ici.
#
# « Deja forme » n'y figure pas, alors que l'utilisateur l'avait cite. Ce n'est
# pas un oubli : avec sa definition — avoir deja suivi une formation — c'est
# une QUALITE CALCULEE depuis le classeur, au meme titre qu'« Apprenant ». La
# poser a la main l'aurait condamnee a se perimer, puisque personne ne pense a
# marquer quelqu'un le lendemain de sa premiere formation. Un groupe faux ne
# se voit pas : il cible simplement les mauvaises personnes.
# Le calcul se fait dans l'ecran, voir qualites().
CATALOGUE_INITIAL = [
    {"cle": "cemedis", "libelle": "Cemedis", "couleur": "#4f7ef8"},
]


# Les fonctions d'un apprenant. UNE SEULE SOURCE : le menu de saisie, la
# convention et le ciblage des envois lisent cette liste. Ecrite a deux endroits,
# elle aurait fini par diverger — « Assistante » ici, « Assistant-e » la, et un
# filtre qui ne trouve plus personne.
#
# QUATRE FONCTIONS, ET DEUX FAMILLES. Les deux premieres nomment le METIER —
# c'est ce qu'attend une convention de formation. Les deux suivantes nomment le
# STATUT dans l'entreprise, cadre ou non-cadre : une session client peut reunir
# des profils que « chirurgien-dentiste » ne decrit pas, et le statut conditionne
# la prise en charge chez certains financeurs.
# CE QUI EST PROPOSE. Deux fonctions, et deux seulement — decide par Franck le
# 22/08/2026. C'est ce qu'on offre dans les ecrans et les formulaires.
FONCTIONS = [
    "Chirurgien-dentiste",
    "Assistant-e dentaire",
]

# CE QUI EST RECONNU, plus large que ce qui est propose.
#
# POURQUOI DEUX LISTES. Une valeur ancienne, ou venue d'un formulaire publie
# avant la simplification, doit continuer a SE LIRE — sinon une convention deja
# editee cesserait de se relire, et un inscrit d'hier deviendrait illisible. Elle
# ne s'offre simplement plus a la saisie. « Etudiant » reste dans ce cas :
# Franck l'a retire des formulaires le 22/08/2026, mais il vit encore dans les
# conventions deja produites.
FONCTIONS_CONNUES = FONCTIONS + [
    "Étudiant-e en chirurgie dentaire",
    "Employé cadre",
    "Employé non-cadre",
]

# LA CSP NE SE SAISIT PAS, ELLE SE DEDUIT.
#
# Le portail OPCO exige une categorie socio-professionnelle par salarie, et c'est
# un AXE DIFFERENT de la fonction : « Cadre » ne dit pas le metier, « assistante
# dentaire » ne dit pas le statut. Mais chez CEMEDIS le lien est constant — un
# chirurgien-dentiste est cadre, une assistante ne l'est pas — donc on ne demande
# rien de plus a personne : on deduit.
#
# LES LIBELLES SONT CEUX DU PORTAIL, pas les notres. « non-cadre » n'existe pas
# dans sa liste (Ouvrier, Employé, Technicien / agent de maitrise, Cadre,
# Ingenieur, Profession liberale, Autre) : une assistante y est « Employé ».
# Ecrire « non-cadre » aurait produit un dossier refuse a la lecture.
CSP_PAR_FONCTION = {
    "Chirurgien-dentiste":  "Cadre",
    "Assistant-e dentaire": "Employé",
}


def csp(fonction):
    """La categorie socio-professionnelle qui decoule d'une fonction, ou "".

    Rend "" plutot que de deviner : une CSP inventee sur un dossier OPCO est
    une declaration fausse, et le dossier vaut mieux incomplet que faux.
    """
    return CSP_PAR_FONCTION.get((fonction or "").strip(), "")
FONCTION_DEFAUT = FONCTIONS[0]

# Un PROSPECT est un chirurgien-dentiste, et rien d'autre. Les assistantes, les
# cadres et les non-cadres existent dans la base parce que leur employeur est
# client ; ils ne sont pas pour autant des cibles de prospection. Ils restent
# visibles dans la liste complete et sur la fiche de leur client, et
# deviendraient apprenants comme les autres s'ils suivaient une formation.
#
# LISTE POSITIVE, PAS UNE EXCLUSION. Enumerer ce qui sort obligerait a y penser
# a chaque fonction ajoutee ; enumerer ce qui entre fait qu'une nouvelle
# fonction est hors prospection par defaut, ce qui est le comportement sur.
PROSPECTABLES = ("Chirurgien-dentiste",)


def _forme(valeur):
    """Forme comparable d'une fonction : sans accent, sans ponctuation, sans
    espaces multiples. « Employe cadre », « employé-cadre » et « EMPLOYÉ CADRE »
    designent la meme chose et doivent se reconnaitre."""
    import unicodedata
    s = unicodedata.normalize("NFD", str(valeur or "")).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return " ".join(s.split())


def fonction_valide(valeur):
    """Rend la fonction reconnue, ou une chaine VIDE.

    ELLE NE COMBLE PLUS. La version precedente ramenait tout ce qu'elle ne
    reconnaissait pas — le vide compris — sur « Chirurgien-dentiste », et sa
    justification etait ecrite ici meme : « un participant sans fonction
    bloquerait l'edition de la convention ». Franck a tranche le 22/08/2026 que
    la convention DOIT bloquer plutot que d'inventer. La raison d'etre du repli
    a donc disparu, et le repli avec elle.

    Ce que ca change : une valeur inconnue rend "" et se voit, au lieu de
    devenir silencieusement un chirurgien-dentiste sur un acte signe.

    LA COMPARAISON IGNORE LES ACCENTS ET LA PONCTUATION depuis l'ajout de
    « Employé cadre » et « Employé non-cadre ». Avec deux fonctions, un repli
    sur le defaut etait sans consequence ; avec quatre, « Employe cadre » saisi
    sans accent aurait fait d'un salarie un chirurgien-dentiste sur sa
    convention, sans que rien ne le signale.
    """
    v = _forme(valeur)
    if not v:
        return ""
    for f in FONCTIONS_CONNUES:
        if v == _forme(f):
            return f
    for f, autres in SYNONYMES.items():
        if v in autres:
            return f
    return ""


# Les formes qu'une meme fonction prend selon qui la saisit. Sans elles,
# « assistante dentaire » — la forme la plus naturelle — tombait sur le defaut
# et faisait d'une assistante un chirurgien-dentiste. Les cles sont deja
# normalisees par _forme() : accents, tirets et casse n'ont plus a y figurer.
SYNONYMES = {
    "Chirurgien-dentiste": {"dentiste", "chirurgien dentiste", "docteur",
                            "praticien", "cd"},
    "Assistant-e dentaire": {"assistante dentaire", "assistant dentaire",
                             "assistante", "assistant", "ad"},
    "Étudiant-e en chirurgie dentaire": {
        "etudiant e en chirurgie dentaire", "etudiant en chirurgie dentaire",
        "etudiante en chirurgie dentaire", "etudiant", "etudiante",
        "etudiant dentaire", "etudiante dentaire", "interne"},
    "Employé cadre": {"cadre", "employe cadre", "salarie cadre", "statut cadre"},
    "Employé non-cadre": {"non cadre", "employe non cadre", "salarie non cadre",
                          "statut non cadre", "employe"},
}


class Indisponible(Exception):
    """Supabase injoignable, ou table absente. Distingue d'une erreur de code :
    l'ecran doit pouvoir le dire a l'utilisateur plutot que planter."""


# --------------------------------------------------------------------------
# Acces a Supabase
# --------------------------------------------------------------------------
# Volontairement autonome plutot qu'importe depuis app.py : contacts.py est
# importe PAR app.py, l'inverse creerait un cycle. Douze lignes dupliquees
# valent mieux qu'un import circulaire.
def _appel(chemin, methode="GET", corps=None, prefer=None):
    # PAS DE CONFIGURATION N'EST PAS UNE PANNE — 19/08/2026. Sans config.py,
    # l'import levait ModuleNotFoundError, qui passait a travers disponible()
    # — lequel n'attrape qu'Indisponible — et cinq ecrans rendaient 500.
    #
    # C'est le cas NORMAL d'une installation neuve : un developpeur qui recoit
    # DFM n'a pas encore de projet Supabase. Il doit voir « ce n'est pas
    # configure », pas une trace d'erreur.
    try:
        from config import SUPABASE_URL, SUPABASE_KEY
    except ImportError:
        raise Indisponible(
            "Supabase n'est pas configuré : le fichier config.py est absent. "
            "Il doit contenir SUPABASE_URL et SUPABASE_KEY. "
            "Sans lui, DFM fonctionne — seules les pages publiques "
            "(inscription, signature, réclamations) restent hors service.")
    if not (str(SUPABASE_URL or "").strip() and str(SUPABASE_KEY or "").strip()):
        raise Indisponible(
            "Supabase n'est pas configuré : SUPABASE_URL ou SUPABASE_KEY est vide "
            "dans config.py.")
    url = SUPABASE_URL.rstrip("/") + "/rest/v1/" + chemin
    entetes = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY,
               "Content-Type": "application/json"}
    if prefer:
        entetes["Prefer"] = prefer
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    requete = urllib.request.Request(url, data=donnees, headers=entetes, method=methode)
    try:
        with urllib.request.urlopen(requete, timeout=30, context=reseau.contexte()) as r:
            texte = r.read().decode("utf-8")
            total = r.headers.get("Content-Range") or ""
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("message") or ""
        except Exception:
            pass
        if e.code == 404 or "PGRST205" in detail:
            raise Indisponible("La table « " + TABLE + " » n'existe pas encore dans Supabase.")
        raise Indisponible("Supabase a refuse la requete (" + str(e.code) + ") " + detail[:120])
    except Exception as e:
        raise Indisponible("Supabase injoignable : " + str(e)[:120])
    return (json.loads(texte) if texte.strip() else []), total


_DISPONIBLE_VU = [0.0]


def disponible():
    """Vrai si la table repond. Sert a afficher un ecran utile plutot qu'une
    trace d'erreur tant que le SQL de creation n'a pas ete execute.

    LA REPONSE POSITIVE EST GARDEE UNE MINUTE — 08/10/2026. C'etait un aller-
    retour complet avant CHAQUE affichage de l'ecran Contacts, pour une
    question dont la reponse ne change pas plusieurs fois par minute : 0,2 s
    sur les 0,9 s de la page.

    UNE PANNE RESTE VISIBLE. Si Supabase tombe pendant la minute gardee, la
    requete suivante leve Indisponible de toute facon et l'ecran affiche
    l'explication — le cache ne cache donc jamais une panne, il evite
    seulement de la chercher deux fois de suite.
    """
    import time as _t
    if _t.time() - _DISPONIBLE_VU[0] < 60:
        return True, ""
    try:
        _appel(TABLE + "?select=id&limit=1")
        _DISPONIBLE_VU[0] = _t.time()
        return True, ""
    except Indisponible as e:
        _DISPONIBLE_VU[0] = 0.0
        return False, str(e)


# --------------------------------------------------------------------------
# Normalisation et identite
# --------------------------------------------------------------------------
def norm_mail(valeur):
    return (valeur or "").strip().lower()


def norm_tel(valeur):
    """Les 9 derniers chiffres, indicatif ignore. Rend "" pour un numero trop
    court ou visiblement bidon — meme regle que la recherche de doublons, pour
    qu'un rapprochement signale la-bas soit un rapprochement fait ici."""
    return doublons.telephone(valeur)


def cle_marqueur(libelle):
    """« Congres ADF 2026 » -> « congres-adf-2026 ». Stable au renommage.

    Le trait de tete des cles reservees est PRESERVE. Sans cela « _apprenant »
    devenait « apprenant » en passant ici : le filtre ne trouvait plus rien et
    la synchronisation croyait devoir re-marquer les memes fiches a chaque
    passage, sans jamais y parvenir. Une panne parfaitement muette."""
    brut = str(libelle or "")
    s = unicodedata.normalize("NFD", brut).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]
    return ("_" + s) if brut.startswith("_") else s


def contactable(fiche):
    """Une fiche sans mail ni telephone existe — un inscrit reste un inscrit —
    mais on ne peut rien lui envoyer. L'ecran doit le dire, pas la masquer."""
    return bool(norm_mail(fiche.get("mail")) or norm_tel(fiche.get("telephone")))


def nom_affiche(fiche):
    """SNC — sans nom connu — plutot qu'une ligne vide qui ne se cherche pas."""
    plein = ((fiche.get("prenom") or "").strip() + " " + (fiche.get("nom") or "").strip()).strip()
    return plein or "SNC"


def _horodate():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _preparer(fiche):
    """Fiche entrante -> colonnes de la table. Les deux colonnes normalisees
    sont calculees ici et nulle part ailleurs : c'est ce qui garantit qu'un
    rapprochement retrouve bien ce qu'un import a ecrit."""
    d = {
        "nom": (fiche.get("nom") or "").strip(),
        "prenom": (fiche.get("prenom") or "").strip(),
        "mail": (fiche.get("mail") or "").strip(),
        "telephone": (fiche.get("telephone") or "").strip(),
        "ville": (fiche.get("ville") or "").strip(),
        "source": (fiche.get("source") or "").strip(),
        "lot_import": (fiche.get("lot_import") or "").strip(),
        "marqueurs": sorted({cle_marqueur(m) for m in (fiche.get("marqueurs") or []) if m}),
        "ne_plus_contacter": bool(fiche.get("ne_plus_contacter")),
        "fonction": (fiche.get("fonction") or "").strip(),
    }
    d["mail_norm"] = norm_mail(d["mail"])
    d["tel_norm"] = norm_tel(d["telephone"])
    return d


# --------------------------------------------------------------------------
# Catalogue des marqueurs — fichier local
# --------------------------------------------------------------------------
def _ecrire_json(chemin, contenu):
    """Ecriture atomique : le fichier definitif n'est jamais tronque en cours
    de route. Une coupure laisse l'ancien intact, jamais un fichier a moitie
    ecrit — c'est-a-dire illisible."""
    import fichiers
    fichiers.ecrire(chemin, contenu)


# Une couleur par marqueur, DEDUITE DE SON IDENTIFIANT. Pas de choix a faire :
# personne n'a envie de choisir une couleur, et un marqueur garde ainsi la
# meme partout — liste, fiche, import — sans qu'on ait a la stocker.
PALETTE = ["#4f7ef8", "#0f9e6a", "#d4890a", "#635BFF", "#c2492f",
           "#0f8f9e", "#a3489e", "#6e7f1e", "#c43b6b", "#3f7a3f"]


def couleur_marqueur(rang):
    """La couleur suit le RANG dans le catalogue, pas un calcul sur le nom.

    Une empreinte du libelle paraissait elegante, mais sur dix couleurs elle
    en donnait la meme a trois marqueurs sur quatre — ce qui annule l'interet
    de la couleur. Par rang, les dix premiers marqueurs sont tous distincts.
    Elle est FIXEE A LA CREATION et conservee : ajouter ou retirer un marqueur
    ne doit pas repeindre les autres, sinon on ne les reconnait plus."""
    return PALETTE[int(rang) % len(PALETTE)]


def marqueurs():
    try:
        with open(_MARQUEURS, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list) and d:
            return [dict(m, couleur=m.get("couleur") or couleur_marqueur(i))
                    for i, m in enumerate(d)]
    except Exception:
        pass
    _ecrire_json(_MARQUEURS, CATALOGUE_INITIAL)
    return list(CATALOGUE_INITIAL)


def marqueur(cle):
    for m in marqueurs():
        if m["cle"] == cle:
            return m
    return None


def creer_marqueur(libelle, couleur=""):
    libelle = (libelle or "").strip()
    if not libelle:
        raise ValueError("Un marqueur doit avoir un libelle.")
    cle = cle_marqueur(libelle)
    if not cle:
        raise ValueError("Ce libelle ne donne aucun identifiant utilisable.")
    if est_reserve(cle):
        raise ValueError("Ce nom est reserve a DFM.")
    tout = marqueurs()
    if any(m["cle"] == cle for m in tout):
        raise ValueError("Un marqueur porte deja ce nom.")
    # Couleur attribuee d'office : l'utilisateur ne veut pas avoir a la choisir.
    tout.append({"cle": cle, "libelle": libelle,
                 "couleur": couleur or couleur_marqueur(len(tout))})
    _ecrire_json(_MARQUEURS, tout)
    return cle


def renommer_marqueur(cle, libelle, couleur=None):
    """Le libelle change, la cle NON : les fiches restent rattachees."""
    tout = marqueurs()
    for m in tout:
        if m["cle"] == cle:
            m["libelle"] = (libelle or "").strip() or m["libelle"]
            if couleur:
                m["couleur"] = couleur
            _ecrire_json(_MARQUEURS, tout)
            return True
    return False


def typer_marqueur(cle, type_marqueur="", client=""):
    """Range un marqueur dans une famille. Deux familles seulement :

      « client » — cree d'office avec une structure de la base clients, il
                   porte son nom et ne se melange pas aux autres ;
      ""         — libre, cree par l'utilisateur.

    Retirer le type ne supprime RIEN : le marqueur redevient simplement libre.
    C'est ce qui se passe quand un client est supprime — ses praticiens gardent
    le marqueur, parce qu'ils ont bien ete formes par ce centre."""
    tout = marqueurs()
    for m in tout:
        if m["cle"] == cle:
            if type_marqueur:
                m["type"] = type_marqueur
                m["client"] = client
            else:
                m.pop("type", None)
                m.pop("client", None)
            _ecrire_json(_MARQUEURS, tout)
            return True
    return False


def marqueurs_par_famille():
    """{"client": [...], "libre": [...]} — pour que la barre de filtres les
    presente separement plutot que dans une seule rangee ou vingt centres
    noieraient les trois marqueurs que l'utilisateur a crees lui-meme."""
    familles = {"client": [], "libre": []}
    for m in marqueurs():
        if est_reserve(m["cle"]):
            continue
        familles["client" if m.get("type") == "client" else "libre"].append(m)
    return familles


def supprimer_marqueur(cle):
    """Retire le marqueur du catalogue SEULEMENT. Les fiches qui le portent
    doivent avoir ete traitees avant, par l'appelant, qui aura montre combien
    elles sont : supprimer un marqueur porte par 400 fiches est une
    suppression de donnees, elle ne se decide pas ici."""
    tout = [m for m in marqueurs() if m["cle"] != cle]
    _ecrire_json(_MARQUEURS, tout)
    return True


def compter_par_marqueur():
    """{cle: nombre de fiches}. UNE requete, et non une par marqueur.

    C'ETAIT UN COMPTAGE PAR MARQUEUR : vingt-sept allers-retours a Supabase
    pour afficher vingt-sept petits nombres. Chacun ne rapatriait rien — seul
    l'en-tete de comptage etait lu — mais chacun coutait son aller-retour :
    3,4 secondes sur les 4,2 que mettait l'ecran Contacts a s'afficher (mesure
    du 08/10/2026). Le travail etait minuscule, l'attente ne l'etait pas.

    ON RAPATRIE DESORMAIS LA SEULE COLONNE « marqueurs » et on compte en
    memoire. Cent quatre-vingt-quinze fiches tiennent dans une reponse ; le
    reseau n'est traverse qu'une fois.

    LA PAGINATION N'EST PAS UNE PRECAUTION DE STYLE. PostgREST plafonne le
    nombre de lignes rendues. Sans elle, le jour ou la base depassera ce
    plafond, les fiches au-dela ne seraient comptees nulle part : les totaux
    deviendraient faux SANS RIEN DIRE, ce qui est pire qu'une page lente.
    """
    return tableau_de_bord()[0]


def tableau_de_bord():
    """Les six chiffres du bandeau Contacts, EN UNE SEULE REQUETE.
    Rend (comptes_par_marqueur, bandeau).

    C'ETAIT SIX ALLERS-RETOURS : le total, quatre comptages filtres cote
    serveur, et le comptage par marqueur. Aucun ne rapatriait de lignes, mais
    chacun coutait son aller-retour — 0,6 seconde a eux seuls sur un ecran qui
    en mettait 0,9 (mesure du 08/10/2026).

    LE FILTRAGE COTE SERVEUR GARDE TOUTE SA RAISON D'ETRE POUR « lister » :
    il evite de rapatrier cinq mille fiches pour en afficher cinquante. Ici
    c'est l'inverse — on compte TOUTE la base — et la parcourir une fois coute
    moins cher que de l'interroger six fois.

    LES REGLES SONT CELLES DE « lister », A LA LETTRE. Se decaler d'une seule
    afficherait un chiffre faux a cote d'une liste juste : l'ecart serait
    invisible, et c'est exactement ce qu'on ne peut pas se permettre.
    """
    par_marqueur = {m["cle"]: 0 for m in marqueurs()}
    connus = set(par_marqueur)
    tb = {"total": 0, "apprenants": 0, "prospects": 0,
          "contactables": 0, "injoignables": 0, "marques": 0}
    colonnes = "marqueurs,fonction,ne_plus_contacter,mail_norm,tel_norm"
    lot, depuis = 1000, 0
    try:
        while True:
            lignes, _ = _appel(TABLE + "?select=" + colonnes
                               + "&limit=%d&offset=%d" % (lot, depuis))
            for ligne in lignes:
                tb["total"] += 1
                portes = ligne.get("marqueurs") or []
                for cle in portes:
                    if cle in connus:
                        par_marqueur[cle] += 1
                if RESERVE_APPRENANT in portes:
                    tb["apprenants"] += 1
                else:
                    # « prospect » : pas apprenant, et chirurgien-dentiste —
                    # fonction vide comprise, comme la regle serveur.
                    f = ligne.get("fonction")
                    if f is None or f == "" or f in PROSPECTABLES:
                        tb["prospects"] += 1
                if ligne.get("ne_plus_contacter") is False:
                    tb["contactables"] += 1
                if ligne.get("mail_norm") == "" and ligne.get("tel_norm") == "":
                    tb["injoignables"] += 1
            if len(lignes) < lot:
                break
            depuis += lot
    except Indisponible:
        return ({m["cle"]: 0 for m in marqueurs()},
                {"total": 0, "apprenants": 0, "prospects": 0,
                 "contactables": 0, "injoignables": 0, "marques": 0})
    tb["marques"] = sum(par_marqueur.values())
    return par_marqueur, tb


# --------------------------------------------------------------------------
# Lecture
# --------------------------------------------------------------------------
def _echapper(valeur):
    """PostgREST : la virgule et la parenthese separent les conditions."""
    return re.sub(r"[,()*]", " ", str(valeur or "")).strip()


def lister(recherche="", filtre_marqueurs=None, joignables=None, exclure_npc=False,
           qualite="", fonction="", depuis=0, limite=200, tri="nom.asc"):
    """Le filtrage se fait COTE SERVEUR. C'est toute la raison du choix de
    Supabase : selectionner 800 fiches parmi 5 000 sans en rapatrier 5 000.

    qualite  : "apprenant", "prospect", ou "" pour tout le monde.
    fonction : "Chirurgien-dentiste", "Assistant-e dentaire", ou "" pour tous.
               Sert au CIBLAGE : une communication peut ne concerner que les
               assistantes, ou que les praticiens."""
    conditions = ["select=*", "order=" + tri, "limit=" + str(int(limite)),
                  "offset=" + str(int(depuis))]
    if fonction:
        # Les fiches anterieures a ce champ ont une fonction VIDE. Filtrer sur
        # la fonction par defaut doit donc les inclure, sinon la moitie de la
        # base disparaitrait d'un ciblage « chirurgiens-dentistes ».
        # La valeur part dans une URL : « Assistant-e dentaire » contient une
        # espace, que PostgREST refuse telle quelle. Encodage obligatoire.
        _f = urllib.parse.quote(fonction, safe="")
        if fonction == FONCTION_DEFAUT:
            conditions.append("or=(fonction.eq." + _f + ",fonction.is.null,fonction.eq.)")
        else:
            conditions.append("fonction=eq." + _f)
    if qualite == "apprenant":
        conditions.append("marqueurs=cs.{" + RESERVE_APPRENANT + "}")
    elif qualite == "prospect":
        conditions.append("marqueurs=not.cs.{" + RESERVE_APPRENANT + "}")
        # Seuls les chirurgiens-dentistes sont des prospects.
        #
        # LA FONCTION VIDE COMPTE COMME CHIRURGIEN-DENTISTE. 179 fiches sur 200
        # sont anterieures a l'existence de ce champ : les exclure ferait
        # disparaitre 90 % de la base des prospects du jour au lendemain. C'est
        # la meme convention que le filtre par fonction quelques lignes plus
        # haut, ou FONCTION_DEFAUT inclut deja les fiches sans valeur.
        _dedans = ",".join("fonction.eq." + urllib.parse.quote(f, safe="")
                           for f in PROSPECTABLES)
        conditions.append("or=(fonction.is.null,fonction.eq.,%s)" % _dedans)
    for cle in (filtre_marqueurs or []):
        conditions.append("marqueurs=cs.{" + cle_marqueur(cle) + "}")
    if exclure_npc:
        conditions.append("ne_plus_contacter=is.false")
    if joignables is True:
        conditions.append("or=(mail_norm.neq.,tel_norm.neq.)")
    elif joignables is False:
        conditions.append("mail_norm=eq.")
        conditions.append("tel_norm=eq.")
    r = _echapper(recherche)
    if r:
        motif = "*" + r.replace(" ", "*") + "*"
        conditions.append("or=(nom.ilike." + motif + ",prenom.ilike." + motif
                          + ",mail.ilike." + motif + ",telephone.ilike." + motif
                          + ",ville.ilike." + motif + ")")
    lignes, total = _appel(TABLE + "?" + "&".join(conditions), prefer="count=exact")
    nombre = int((total or "0/0").split("/")[-1] or 0)
    return lignes, nombre


def par_id(identifiant):
    lignes, _ = _appel(TABLE + "?select=*&id=eq." + str(int(identifiant)) + "&limit=1")
    return lignes[0] if lignes else None


def rapprocher(mail="", telephone=""):
    """La fiche existante qui designe la meme personne, ou None.

    Deux criteres seulement, dans cet ordre : meme adresse, puis meme numero.
    Le rapprochement par NOM SEUL est volontairement absent — deux confreres
    peuvent etre homonymes, et un import ne doit jamais fusionner sur une
    presomption. Ce cas reste signale dans la recherche de doublons, ou il se
    tranche a l'oeil."""
    m, t = norm_mail(mail), norm_tel(telephone)
    if m:
        lignes, _ = _appel(TABLE + "?select=*&mail_norm=eq." + urllib.parse.quote(m) + "&limit=1")
        if lignes:
            return lignes[0]
    if t:
        lignes, _ = _appel(TABLE + "?select=*&tel_norm=eq." + t + "&limit=1")
        if lignes:
            return lignes[0]
    return None


# --------------------------------------------------------------------------
# Ecriture
# --------------------------------------------------------------------------
def creer(fiche):
    d = _preparer(fiche)
    if not (d["mail_norm"] or d["tel_norm"]):
        raise ValueError("Il faut au minimum une adresse mail ou un telephone.")
    d["cree_le"] = d["maj_le"] = _horodate()
    lignes, _ = _appel(TABLE, "POST", [d], prefer="return=representation")
    return lignes[0] if lignes else None


def creer_en_lot(fiches):
    """Un seul aller-retour pour tout un paquet. Les imports arrivent par
    milliers de lignes : une requete par contact prendrait des minutes."""
    corps = []
    for f in fiches:
        d = _preparer(f)
        if not (d["mail_norm"] or d["tel_norm"]):
            continue
        d["cree_le"] = d["maj_le"] = _horodate()
        corps.append(d)
    if not corps:
        return []
    lignes, _ = _appel(TABLE, "POST", corps, prefer="return=representation")
    return lignes


def modifier(identifiant, champs):
    """N'ecrit QUE les champs fournis. Les colonnes normalisees sont refaites
    des que leur source bouge, sans quoi un rapprochement chercherait sur une
    valeur perimee."""
    d = {}
    for cle in ("nom", "prenom", "mail", "telephone", "ville", "source",
                "lot_import", "fonction"):
        if cle in champs:
            d[cle] = (champs[cle] or "").strip()
    if "mail" in d:
        d["mail_norm"] = norm_mail(d["mail"])
    if "telephone" in d:
        d["tel_norm"] = norm_tel(d["telephone"])
    if "marqueurs" in champs:
        d["marqueurs"] = sorted({cle_marqueur(m) for m in (champs["marqueurs"] or []) if m})
    if "ne_plus_contacter" in champs:
        d["ne_plus_contacter"] = bool(champs["ne_plus_contacter"])
    if not d:
        return None
    d["maj_le"] = _horodate()
    lignes, _ = _appel(TABLE + "?id=eq." + str(int(identifiant)), "PATCH", d,
                       prefer="return=representation")
    return lignes[0] if lignes else None


def _comparable(champ, valeur):
    """La forme sous laquelle deux valeurs se comparent pour dire si elles
    DIFFERENT vraiment.

    Sans cela, « 06 11 22 33 44 » et « 0611223344 » remontaient comme une
    divergence alors que c'est le meme numero. Sur un import de plusieurs
    milliers de lignes, le compte rendu se serait rempli de fausses alertes,
    et un rapport qui crie au loup finit par ne plus etre lu."""
    if champ == "telephone":
        return norm_tel(valeur)
    if champ == "mail":
        return norm_mail(valeur)
    return doublons.plat(valeur)      # casse, accents, tirets, espaces


def completer(identifiant, fiche):
    """Ne remplit QUE ce qui est vide, et rend la liste des divergences.

    La regle de l'import : ne jamais ecraser. Une valeur differente de celle
    deja connue n'est pas une correction, c'est une question — elle remonte
    dans le compte rendu, ou l'utilisateur tranche sur le petit nombre de cas
    qui le meritent."""
    actuel = par_id(identifiant)
    if not actuel:
        return None, []
    a_poser, divergences = {}, []
    for cle in ("nom", "prenom", "mail", "telephone", "ville"):
        neuf = (fiche.get(cle) or "").strip()
        if not neuf:
            continue
        ancien = (actuel.get(cle) or "").strip()
        if not ancien:
            a_poser[cle] = neuf
        elif _comparable(cle, ancien) != _comparable(cle, neuf):
            divergences.append({"champ": cle, "connu": ancien, "fichier": neuf})
    neufs = {cle_marqueur(m) for m in (fiche.get("marqueurs") or []) if m}
    ensemble = sorted(set(actuel.get("marqueurs") or []) | neufs)
    if ensemble != sorted(actuel.get("marqueurs") or []):
        a_poser["marqueurs"] = ensemble
    if not a_poser:
        return actuel, divergences
    return modifier(identifiant, a_poser), divergences


def poser_marqueurs(identifiants, cles, retirer=False):
    """Pose ou retire des marqueurs sur une selection. Lecture puis ecriture
    fiche par fiche : PostgREST ne sait pas modifier un tableau en place, et
    un remplacement en masse ecraserait les marqueurs deja poses."""
    cles = {cle_marqueur(c) for c in (cles or []) if c}
    if not cles:
        return 0
    touches = 0
    for i in identifiants:
        actuel = par_id(i)
        if not actuel:
            continue
        avant = set(actuel.get("marqueurs") or [])
        apres = (avant - cles) if retirer else (avant | cles)
        if apres != avant:
            modifier(i, {"marqueurs": sorted(apres)})
            touches += 1
    return touches


def supprimer(identifiants):
    """Suppression definitive. L'appelant DOIT avoir demande confirmation en
    annoncant le nombre : rien ici ne rattrape un clic de trop."""
    ids = [str(int(i)) for i in identifiants]
    if not ids:
        return 0
    _appel(TABLE + "?id=in.(" + ",".join(ids) + ")", "DELETE")
    return len(ids)


def supprimer_lot(lot):
    """Annulation d'un import : retire les fiches qu'il a CREEES.

    Ne defait pas les completions apportees aux fiches deja presentes — celles
    ci n'ont recu que du vide comble, et les rendre a leur vide n'aurait aucun
    sens. Les marqueurs poses par l'import, eux, se retirent separement."""
    lot = (lot or "").strip()
    if not lot:
        return 0
    lignes, total = _appel(TABLE + "?select=id&lot_import=eq." + urllib.parse.quote(lot),
                           prefer="count=exact")
    n = len(lignes)
    if n:
        _appel(TABLE + "?lot_import=eq." + urllib.parse.quote(lot), "DELETE")
    return n


def compter():
    _, total = _appel(TABLE + "?select=id&limit=1", prefer="count=exact")
    return int((total or "0/0").split("/")[-1] or 0)


# --------------------------------------------------------------------------
# Les apprenants, vus depuis la base de contacts
# --------------------------------------------------------------------------
# UNE PERSONNE, UNE FICHE. Pour que la recherche, le filtrage et la pagination
# se fassent a un seul endroit — cote serveur, ou c'est rapide — chaque
# apprenant possede aussi une fiche ici. Ce n'est pas un second fichier de
# reference : le CLASSEUR RESTE LA SOURCE DE VERITE. La synchronisation recopie
# l'identite dans ce sens uniquement, et jamais l'inverse ; l'ecran des
# contacts n'ecrit rien dans le classeur.
#
# La qualite d'apprenant est portee par un marqueur RESERVE, « _apprenant ».
# Le trait de tete le distingue des marqueurs poses a la main : il n'apparait
# pas dans le catalogue, ne se cree ni ne se supprime, mais il beneficie de
# l'index qui rend le filtrage instantane — sans colonne supplementaire, donc
# sans nouvelle intervention dans le tableau de bord Supabase.
RESERVE_APPRENANT = "_apprenant"


def est_reserve(cle):
    return (cle or "").startswith("_")


def synchroniser_apprenants(identites):
    """Aligne les fiches sur les inscrits du classeur. Idempotente.

    identites : [{nom, prenom, mail, telephone, ville, fonction}], une par personne.

    Volontairement en trois requetes et non en trois par personne : une lecture
    de l'index existant, une creation groupee, puis les seules corrections
    necessaires. A quelques centaines d'apprenants, l'ecart se compte en
    minutes."""
    existantes, _ = _appel(TABLE + "?select=id,nom,prenom,mail,telephone,ville,fonction,mail_norm,tel_norm,marqueurs")
    par_mail = {l["mail_norm"]: l for l in existantes if l.get("mail_norm")}
    par_tel = {l["tel_norm"]: l for l in existantes if l.get("tel_norm")}

    a_creer, a_marquer, a_completer = [], [], []
    for ident in identites:
        m, t = norm_mail(ident.get("mail")), norm_tel(ident.get("telephone"))
        if not (m or t):
            continue          # sans coordonnee, aucune cle de rapprochement
        fiche = par_mail.get(m) if m else None
        if fiche is None and t:
            fiche = par_tel.get(t)
        if fiche is None:
            d = dict(ident)
            d["marqueurs"] = [RESERVE_APPRENANT]
            d["source"] = "classeur"
            a_creer.append(d)
            continue
        if RESERVE_APPRENANT not in (fiche.get("marqueurs") or []):
            a_marquer.append(fiche)
        # Le classeur fait foi : ce qu'il sait et que la fiche ignore descend.
        # « fonction » descend comme le reste : le classeur fait foi pour ce que
        # la fiche ignore encore. Une fonction deja saisie a la main sur la fiche
        # n'est JAMAIS ecrasee — c'est la regle de tous les champs ici.
        manques = {c: (ident.get(c) or "").strip()
                   for c in ("nom", "prenom", "mail", "telephone", "ville", "fonction")
                   if (ident.get(c) or "").strip() and not (fiche.get(c) or "").strip()}
        if manques:
            a_completer.append((fiche["id"], manques))

    crees = creer_en_lot(a_creer) if a_creer else []
    for fiche in a_marquer:
        modifier(fiche["id"], {"marqueurs": sorted(set(fiche.get("marqueurs") or [])
                                                   | {RESERVE_APPRENANT})})
    for identifiant, manques in a_completer:
        modifier(identifiant, manques)
    return {"crees": len(crees), "marques": len(a_marquer), "completes": len(a_completer),
            "vus": len(identites)}
