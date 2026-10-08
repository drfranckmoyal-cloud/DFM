"""Les veilles du critere 6, et la maniere de les tenir sans y penser.

POURQUOI CE MODULE EXISTE. Les indicateurs 23, 24 et 25 sont les seuls du
referentiel qu'aucun logiciel ne peut remplir a votre place : ils demandent que
VOUS lisiez, suiviez, et en tiriez quelque chose. Le 06/08/2026, les quatre
registres du critere 6 etaient vides, et trois de ces indicateurs comptaient
parmi les sept « absents ». Ils ne demandent pourtant aucun developpement :
seulement des lignes ecrites, et de quoi ne pas oublier de les ecrire.

CE QUE L'AUDITEUR VERIFIE, ET CE QUI FAIT ECHOUER LA PLUPART DES ORGANISMES :

  1. Que la veille EXISTE            des sources nommees, pas une intention.
  2. Qu'elle est REGULIERE           un rythme, pas trois relevés la veille de
                                     l'audit, tous dates du meme jour.
  3. Qu'elle est EXPLOITEE           « Mineure : absence d'exploitation de la
                                     veille mise en place. » C'est ecrit tel
                                     quel dans le guide, pour 23, 24 et 25.

Le troisieme point est celui qui coute. Un abonnement a une newsletter ne
prouve rien ; ce qui prouve, c'est : « j'ai lu ceci, et j'ai change cela. »
D'ou un champ « exploitation » que ce module traite comme le champ principal,
et non comme un commentaire facultatif.

L'INDICATEUR 22 N'EST PAS UNE VEILLE. Il porte sur VOTRE formation continue —
ce que vous suivez, pas ce que vous surveillez. Il est range ici parce qu'il
releve de la meme discipline : consigner au fil de l'eau. Ses champs sont
differents, et le module le dit plutot que de faire semblant.
"""
import os
from datetime import date, datetime, timedelta

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "veille_sources.json")

# Un fichier a part, et non celui des consignations Qualiopi : ce dernier
# aplatit toutes ses valeurs (`for v in tout.values() for x in v`) pour compter
# les entrees. Une cle supplementaire y serait parcourue comme une liste
# d'entrees et fausserait les comptes.

# Rythme attendu par axe, en jours. Ce ne sont pas des regles du referentiel —
# il n'en donne aucune — mais un rythme tenable qui, tenu, ne se discute pas.
_RYTHME = {"veille_legale": 90, "veille_metiers": 120,
           "veille_pedago": 180, "formation_continue": 365}

AXES = [
    {"cle": "formation_continue", "court": "Formation continue", "indicateur": 22,
     "titre": "Votre formation continue",
     "sous_titre": "Ce que VOUS avez suivi — pas ce que vous surveillez",
     "icone": "ti-school", "couleur": "#a855f7",
     "gravite": "Majeure si aucune démarche n'est démontrée",
     "attendu": "Sans salarié, le guide demande au prestataire indépendant de démontrer "
                "sa propre démarche de formation continue.",
     "verifie": "Des formations réellement suivies, avec leurs justificatifs, et ce "
                "qu'elles ont changé dans votre pratique ou dans vos formations.",
     "champs": "formation"},
    {"cle": "veille_legale", "court": "Légale", "indicateur": 23,
     "titre": "Veille légale et réglementaire",
     "sous_titre": "Le droit de la formation professionnelle",
     "icone": "ti-scale", "couleur": "#2a5fd6",
     "gravite": "Mineure sans exploitation · Majeure si aucune veille n'existe",
     "attendu": "Démontrer la mise en place d'une veille légale et réglementaire, sa "
                "prise en compte et sa communication en interne.",
     "verifie": "Ce que vous suivez, à quel rythme, et surtout ce que vous en avez "
                "tiré : un texte lu qui n'a rien changé doit dire pourquoi.",
     "champs": "veille"},
    {"cle": "veille_metiers", "court": "Métiers", "indicateur": 24,
     "titre": "Veille métiers et compétences",
     "sous_titre": "L'évolution de la pratique dentaire",
     "icone": "ti-dental", "couleur": "#0f9e6a",
     "gravite": "Mineure sans exploitation · Majeure si aucune veille n'existe",
     "attendu": "Démontrer la veille sur les évolutions des compétences, des métiers et "
                "des emplois dans vos secteurs d'intervention, et son impact éventuel "
                "sur les prestations.",
     "verifie": "Que la veille porte sur VOS secteurs — l'odontologie et le métier "
                "d'assistant(e) dentaire — et pas sur la formation en général.",
     "champs": "veille"},
    {"cle": "veille_pedago", "court": "Pédagogique", "indicateur": 25,
     "titre": "Veille pédagogique et technologique",
     "sous_titre": "Méthodes, outils, formats, matériel",
     "icone": "ti-bulb", "couleur": "#d4890a",
     "gravite": "Mineure sans exploitation · Majeure si aucune veille n'existe",
     "attendu": "Démontrer la veille sur les innovations pédagogiques et technologiques "
                "permettant une évolution des prestations.",
     "verifie": "Le guide cite EXPLICITEMENT la veille pédagogique pour les publics en "
                "situation de handicap : un axe sans elle est incomplet.",
     "champs": "veille"},
]

_PAR_CLE = {a["cle"]: a for a in AXES}


def axe(cle):
    return _PAR_CLE.get(cle)


# --------------------------------------------------------------------------
# LE CATALOGUE. Proposer des sources plutot qu'une page blanche : le premier
# obstacle a une veille n'est pas la discipline, c'est de savoir quoi suivre.
# Chacune est nommee, situee, et accompagnee de ce qu'elle apporte a CET
# indicateur — un auditeur demande pourquoi telle source, pas seulement
# laquelle. Rien n'est pre-coche : une source qu'on ne lit pas est un mensonge
# de plus dans le dossier.
# --------------------------------------------------------------------------
CATALOGUE = {
    "veille_legale": [
        {"nom": "Ministère du Travail — formation professionnelle",
         "url": "https://travail-emploi.gouv.fr/formation-professionnelle",
         "quoi": "Textes et actualités officiels. La source de référence quand l'auditeur "
                 "demande d'où vient l'information.", "rythme": "Trimestriel"},
        {"nom": "Centre Inffo — Le Quotidien de la formation",
         "url": "https://www.centre-inffo.fr",
         "quoi": "Le suivi le plus complet du droit de la formation. Newsletter gratuite ; "
                 "c'est la source la plus souvent citée en audit.", "rythme": "Mensuel"},
        {"nom": "France compétences",
         "url": "https://www.francecompetences.fr",
         "quoi": "Financement, RNCP, répertoire spécifique, niveaux de prise en charge.",
         "rythme": "Trimestriel"},
        {"nom": "Légifrance — code du travail, sixième partie",
         "url": "https://www.legifrance.gouv.fr",
         "quoi": "Le texte lui-même, notamment L.6353-1 qui régit vos attestations.",
         "rythme": "Semestriel"},
        {"nom": "Votre organisme certificateur — newsletters et webinaires",
         "url": "",
         "quoi": "Évolutions du référentiel et des guides de lecture. Un webinaire suivi "
                 "est une preuve de veille ET d'exploitation.", "rythme": "À chaque envoi"},
        {"nom": "Agence nationale du DPC",
         "url": "https://www.agencedpc.fr",
         "quoi": "Règles d'enregistrement et de financement des actions DPC — elles "
                 "conditionnent une partie de vos sessions.", "rythme": "Trimestriel"},
        {"nom": "Votre OPCO — notes de prise en charge",
         "url": "",
         "quoi": "Ce que le financeur accepte et les pièces qu'il exige. C'est aussi ce "
                 "qui décide du contenu de vos conventions.", "rythme": "Trimestriel"},
    ],
    "veille_metiers": [
        {"nom": "ADF — Association dentaire française",
         "url": "https://www.adf.asso.fr",
         "quoi": "Le congrès annuel de novembre et ses séances. Une participation "
                 "documentée couvre à la fois cet indicateur et le 22.", "rythme": "Annuel"},
        {"nom": "Ordre national des chirurgiens-dentistes",
         "url": "https://www.ordre-chirurgiens-dentistes.fr",
         "quoi": "Déontologie, exercice, évolutions du champ de compétence.",
         "rythme": "Trimestriel"},
        {"nom": "Haute Autorité de santé — odontologie",
         "url": "https://www.has-sante.fr",
         "quoi": "Recommandations de bonne pratique. Une recommandation nouvelle qui "
                 "modifie un contenu de formation est l'exploitation idéale.",
         "rythme": "Semestriel"},
        {"nom": "Sociétés savantes (SOP, SFPD, SFE, SFMBCB…)",
         "url": "",
         "quoi": "Journées et publications sur votre champ clinique. À nommer "
                 "précisément : celles dont vous êtes réellement membre.", "rythme": "Trimestriel"},
        {"nom": "Revues professionnelles",
         "url": "",
         "quoi": "L'Information Dentaire, Clinic, Réalités Cliniques, Le Fil Dentaire. "
                 "Citez les numéros et les articles utilisés.", "rythme": "Mensuel"},
        {"nom": "Syndicats (Les CDF, FSDL, UD)",
         "url": "",
         "quoi": "Conventions, nomenclature, conditions d'exercice.", "rythme": "Trimestriel"},
        {"nom": "Métier d'assistant(e) dentaire — référentiel et apprentissage",
         "url": "",
         "quoi": "Vos formations s'ouvrent aux assistant(e)s : l'évolution de leur "
                 "référentiel de compétences relève directement de cet indicateur.",
         "rythme": "Semestriel"},
    ],
    "veille_pedago": [
        {"nom": "Ressource Handicap Formation — Agefiph",
         "url": "https://www.agefiph.fr",
         "quoi": "ESSENTIEL : le guide cite explicitement la veille pédagogique pour les "
                 "publics en situation de handicap. Cette source vaut aussi pour "
                 "l'indicateur 26.", "rythme": "Semestriel"},
        {"nom": "Centre Inffo — dossier handicap et innovation pédagogique",
         "url": "https://www.centre-inffo.fr",
         "quoi": "Formats, AFEST, modalités mixtes, accessibilité pédagogique.",
         "rythme": "Trimestriel"},
        {"nom": "Pédagogie des sciences de la santé (SIFEM, colloques universitaires)",
         "url": "https://sifem.net",
         "quoi": "Simulation, apprentissage par problème, évaluation des acquis — "
                 "directement transposable à vos travaux pratiques.", "rythme": "Annuel"},
        {"nom": "Simulation et enseignement pré-clinique en odontologie",
         "url": "",
         "quoi": "Fantômes, simulateurs haptiques, flux numérique appliqué à "
                 "l'enseignement. Le lien entre pédagogie et technologie de votre métier.",
         "rythme": "Semestriel"},
        {"nom": "Outils : plateformes de quiz, visioconférence, LMS",
         "url": "",
         "quoi": "Ce que vous testez et pourquoi vous l'adoptez ou non. Un outil écarté, "
                 "avec sa raison, est une exploitation valable.", "rythme": "Semestriel"},
        {"nom": "Matériel et techniques enseignées",
         "url": "",
         "quoi": "L'arrivée d'un matériau ou d'un protocole qui change ce que vous "
                 "montrez en travaux pratiques.", "rythme": "Semestriel"},
    ],
    "formation_continue": [
        {"nom": "DPC — actions suivies",
         "url": "https://www.mondpc.fr",
         "quoi": "Vos propres actions DPC, avec leur numéro et leur attestation. La "
                 "preuve la plus solide pour cet indicateur.", "rythme": "Annuel"},
        {"nom": "Congrès suivis comme participant",
         "url": "",
         "quoi": "ADF, journées de sociétés savantes. Distinguez ce que vous suivez de "
                 "ce que vous animez : l'indicateur porte sur le premier.", "rythme": "Annuel"},
        {"nom": "Formation de formateur et pédagogie",
         "url": "",
         "quoi": "Se former à former. C'est ce qui répond le mieux à l'attendu, et c'est "
                 "presque toujours ce qui manque.", "rythme": "Bisannuel"},
        {"nom": "Publications et communications",
         "url": "",
         "quoi": "Articles, conférences, travaux. Une production compte comme entretien "
                 "des compétences.", "rythme": "Au fil"},
    ],
}


# --------------------------------------------------------------------------
# Les sources DECLAREES : celles que vous suivez vraiment.
# --------------------------------------------------------------------------
def _organisme(ident=None):
    """LES QUATRE AXES SONT COMMUNS AUX DEUX ORGANISMES.

    Ce module ne connait donc qu'un seul emplacement, quel que soit l'organisme
    actif : ce qui est declare depuis Smileclub existe depuis DSF, et
    inversement. La veille legale, l'evolution du metier et la formation
    continue d'une meme personne ne changent pas selon l'entete du papier.

    Le partage se fait par un rangement UNIQUE, pas par recopie : il n'y a rien
    a resynchroniser quand une source est retiree ou un relevé corrigé.
    """
    import qualiopi
    return qualiopi.COMMUN


def _tout():
    import fichiers
    d = fichiers.lire(_FICHIER, {})
    return d if isinstance(d, dict) else {}


def sources(cle, organisme=None):
    o = _organisme(organisme)
    return list(((_tout().get(o) or {}).get(cle)) or [])


def ajouter_source(cle, valeurs, organisme=None):
    """Declare une source suivie. Le nom suffit ; le reste aide l'auditeur."""
    if cle not in _PAR_CLE:
        return None, "Axe de veille inconnu."
    nom = str(valeurs.get("nom") or "").strip()
    if not nom:
        return None, "Donnez un nom à la source."
    import fichiers
    o = _organisme(organisme)
    with fichiers.modifier(_FICHIER, {}) as tout:
        liste = tout.setdefault(o, {}).setdefault(cle, [])
        if any((s.get("nom") or "").strip().lower() == nom.lower() for s in liste):
            return None, "Cette source est déjà déclarée."
        # Le premier rang libre, pas la longueur : apres un retrait, deux
        # sources auraient porte le meme identifiant.
        import qualiopi as _q
        s = {"id": "%s-%d" % (cle, _q._rang_libre(liste, cle)), "nom": nom,
             "url": str(valeurs.get("url") or "").strip(),
             "quoi": str(valeurs.get("quoi") or "").strip(),
             "rythme": str(valeurs.get("rythme") or "").strip(),
             "depuis": date.today().isoformat()}
        liste.append(s)
    return s, ""


def retirer_source(cle, ident, organisme=None):
    import fichiers
    o = _organisme(organisme)
    with fichiers.modifier(_FICHIER, {}) as tout:
        liste = (tout.get(o) or {}).get(cle) or []
        reste = [s for s in liste if s.get("id") != ident]
        if len(reste) == len(liste):
            return False
        tout[o][cle] = reste
    return True


# --------------------------------------------------------------------------
# LES JUSTIFICATIFS. Une attestation de DPC, le programme d'un congres, la
# capture d'un texte : la preuve la plus solide de ces indicateurs est souvent
# un fichier, pas un lien.
#
# ILS SONT RANGES EN LOCAL, a cote du registre, et non dans le Drive comme les
# autres depots de DFM. Trois raisons : le registre de veille est deja local,
# ces pieces doivent rester consultables sans reseau ni jeton Google — le
# 14/08/2026 a montre ce que vaut cette dependance —, et le Drive fait partie
# de ce dont le chantier « s'affranchir de Google » veut se defaire.
#
# CLOISONNES PAR ORGANISME. La veille de Smileclub n'est pas celle de DSF, et
# un auditeur qui verifie l'un ne doit pas tomber sur les pieces de l'autre.
# --------------------------------------------------------------------------
JUSTIFICATIFS = os.path.join(_DOSSIER, "justificatifs")

# L'index des remontees : chemin local -> identifiant et adresse dans le Drive.
# Il vit A COTE des fichiers plutot que dans les entrees du registre, parce
# qu'une remontee peut avoir lieu LONGTEMPS apres la consignation — le jour ou
# Google redevient joignable. Figer une adresse dans l'entree obligerait a
# rouvrir le registre pour la corriger.
_INDEX = os.path.join(JUSTIFICATIFS, "_index.json")

# Le dossier Drive, A LA RACINE et non dans l'arborescence d'un organisme : la
# veille est commune aux deux, la ranger sous l'un serait trompeur lors d'un
# audit de l'autre.
DOSSIER_DRIVE = "Veille Qualiopi"

# 20 Mo : un scan de programme de congres tient largement dedans, et une video
# deposee par erreur ne remplit pas le disque en silence.
TAILLE_MAX = 20 * 1024 * 1024

EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "heic", "webp", "gif",
              "doc", "docx", "odt", "txt", "md", "eml", "msg", "zip",
              "xls", "xlsx", "ods", "ppt", "pptx", "csv"}


def _sous_dossier(cle, organisme=None):
    """Le dossier d'un axe. `cle` et l'organisme viennent de listes fermees :
    aucun morceau de nom ne provient de ce que tape l'utilisateur."""
    o = _organisme(organisme) or "sans-organisme"
    d = os.path.join(JUSTIFICATIFS, _sain(o), _sain(cle))
    os.makedirs(d, exist_ok=True)
    return d


def _sain(t):
    return "".join(c for c in str(t or "") if c.isalnum() or c in "-_") or "x"


def deposer_justificatif(cle, nom_fichier, octets, organisme=None):
    """Range un fichier et rend le chemin RELATIF a inscrire dans l'entree.

    Rend (None, souci) plutot que de lever : l'appelant est un ecran, et un
    depot refuse doit s'expliquer, pas planter.
    """
    if cle not in _PAR_CLE:
        return None, "Axe de veille inconnu."
    if not octets:
        return None, "Fichier vide."
    if len(octets) > TAILLE_MAX:
        return None, ("Fichier trop lourd (%.1f Mo). La limite est de %d Mo."
                      % (len(octets) / 1048576.0, TAILLE_MAX // 1048576))
    from werkzeug.utils import secure_filename
    propre = secure_filename(os.path.basename(nom_fichier or "")) or "piece"
    ext = propre.rsplit(".", 1)[-1].lower() if "." in propre else ""
    if ext not in EXTENSIONS:
        return None, ("Type de fichier non accepté (%s). Acceptés : %s."
                      % (ext or "sans extension", ", ".join(sorted(EXTENSIONS))))
    dossier = _sous_dossier(cle, organisme)
    # On ne remplace JAMAIS un fichier existant : deux justificatifs peuvent
    # legitimement porter le meme nom, et ecraser le premier detruirait une
    # preuve deja consignee.
    base, suffixe = (propre.rsplit(".", 1) + [""])[:2]
    final, n = propre, 1
    while os.path.exists(os.path.join(dossier, final)):
        n += 1
        final = "%s-%d.%s" % (base, n, suffixe) if suffixe else "%s-%d" % (base, n)
    with open(os.path.join(dossier, final), "wb") as f:
        f.write(octets)
    rel = os.path.relpath(os.path.join(dossier, final), JUSTIFICATIFS).replace(os.sep, "/")
    # LE DEPOT NE DEPEND PAS DE GOOGLE. On ecrit en local, puis on tente la
    # remontee. Si le jeton est expire ou le reseau absent, le justificatif est
    # quand meme enregistre et attend la prochaine remontee : perdre une piece
    # parce que Google ne repond pas serait le pire des comportements.
    lien, souci_drive = pousser(rel)
    return {"chemin": rel, "nom": final, "taille": len(octets),
            "lien": lien, "drive": bool(lien), "souci_drive": souci_drive}, ""


# --------------------------------------------------------------------------
# La remontee dans le Drive.
# --------------------------------------------------------------------------
def _index():
    import fichiers
    d = fichiers.lire(_INDEX, {})
    return d if isinstance(d, dict) else {}


def _dossier_drive(drive):
    """L'identifiant du dossier « Veille Qualiopi », cree au besoin.

    Cherche par NOM a la racine, et retient l'identifiant : sans cela, un
    dossier renomme ou deplace a la main en ferait creer un second.
    """
    import fichiers
    idx = _index()
    connu = (idx.get("_dossier") or {}).get("id")
    if connu:
        try:
            f = drive.files().get(fileId=connu, fields="id,trashed").execute()
            if not f.get("trashed"):
                return connu
        except Exception:
            pass
    q = ("name='%s' and mimeType='application/vnd.google-apps.folder' "
         "and 'root' in parents and trashed=false" % DOSSIER_DRIVE)
    trouves = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    ident = trouves[0]["id"] if trouves else drive.files().create(
        body={"name": DOSSIER_DRIVE, "mimeType": "application/vnd.google-apps.folder"},
        fields="id").execute()["id"]
    with fichiers.modifier(_INDEX, {}) as d:
        d["_dossier"] = {"id": ident, "nom": DOSSIER_DRIVE}
    return ident


def pousser(rel):
    """Remonte un justificatif dans le Drive. Rend (adresse, souci).

    N'echoue jamais bruyamment : l'appelant a deja le fichier en local.
    """
    plein = chemin_justificatif(rel)
    if not plein:
        return "", "Fichier introuvable en local."
    deja = _index().get(rel)
    if deja and deja.get("lien"):
        return deja["lien"], ""
    try:
        import fichiers
        import mimetypes
        from connexion import service_drive
        from googleapiclient.http import MediaInMemoryUpload
        drive = service_drive()
        parent = _dossier_drive(drive)
        with open(plein, "rb") as f:
            octets = f.read()
        type_mime = mimetypes.guess_type(plein)[0] or "application/octet-stream"
        # Le nom porte l'axe : dans un dossier plat, « attestation.pdf » seul
        # ne dit pas de quelle veille il releve.
        axe, nom = (rel.split("/", 2) + ["", ""])[1:3]
        f = drive.files().create(
            body={"name": "%s — %s" % (axe, nom), "parents": [parent]},
            media_body=MediaInMemoryUpload(octets, mimetype=type_mime),
            fields="id,webViewLink").execute()
        lien = f.get("webViewLink") or ("https://drive.google.com/file/d/%s/view" % f["id"])
        with fichiers.modifier(_INDEX, {}) as d:
            d[rel] = {"id": f["id"], "lien": lien, "le": date.today().isoformat()}
        return lien, ""
    except Exception as e:
        return "", str(e)[:200]


def lien_drive(rel):
    return (_index().get(rel) or {}).get("lien") or ""


def en_attente():
    """Les justificatifs presents en local et absents du Drive."""
    idx = _index()
    manque = []
    for racine, _, fichiers_ in os.walk(JUSTIFICATIFS):
        for n in fichiers_:
            if n.startswith("_"):
                continue
            rel = os.path.relpath(os.path.join(racine, n), JUSTIFICATIFS).replace(os.sep, "/")
            if not (idx.get(rel) or {}).get("lien"):
                manque.append(rel)
    return sorted(manque)


def remonter_en_attente():
    """Rattrape ce que Google n'avait pas pu recevoir. Rend (montes, soucis)."""
    montes, soucis = [], []
    for rel in en_attente():
        lien, souci = pousser(rel)
        (montes if lien else soucis).append(rel if lien else "%s : %s" % (rel, souci))
    return montes, soucis


def chemin_justificatif(rel):
    """Le chemin absolu d'un justificatif, ou None s'il sort du dossier.

    La verification n'est pas theorique : ce chemin vient d'un fichier JSON,
    donc d'une valeur qu'un editeur de texte peut avoir modifiee.
    """
    if not rel:
        return None
    plein = os.path.abspath(os.path.join(JUSTIFICATIFS, str(rel)))
    racine = os.path.abspath(JUSTIFICATIFS)
    if not plein.startswith(racine + os.sep) or not os.path.exists(plein):
        return None
    return plein


def catalogue_restant(cle, organisme=None):
    """Le catalogue, prive de ce qui est deja declare."""
    pris = {(s.get("nom") or "").strip().lower() for s in sources(cle, organisme)}
    return [c for c in CATALOGUE.get(cle, [])
            if (c["nom"] or "").strip().lower() not in pris]


# --------------------------------------------------------------------------
# L'etat d'un axe : ce qui est en place, ce qui manque, ce qui vieillit.
# --------------------------------------------------------------------------
def _jour(v):
    t = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            continue
    return None


def _fr(v):
    d = _jour(v)
    return d.strftime("%d/%m/%Y") if d else ""


def entrees(cle, organisme=None):
    """Les relevés consignés, du plus recent au plus ancien."""
    import qualiopi
    liste = []
    for e in qualiopi.consignations(cle, organisme) or []:
        d = dict(e)
        d["quand_fr"] = _fr(e.get("quand"))
        d["_d"] = _jour(e.get("quand"))
        d["sans_exploitation"] = not (e.get("exploitation") or "").strip()
        # L'adresse Drive se relit a l'affichage plutot qu'a l'ecriture : une
        # piece deposee sans reseau la recevra lors d'une remontee ulterieure.
        d["drive"] = lien_drive(e.get("fichier") or "") if e.get("fichier") else ""
        liste.append(d)
    liste.sort(key=lambda x: x["_d"] or date.min, reverse=True)
    # L'ECART AVEC LE RELEVE PRECEDENT — APRES LE TRI, sans quoi il porterait
    # sur l'ordre d'arrivee et n'aurait aucun sens. C'est la regularite que le
    # guide juge, et elle ne se lit pas dans une colonne de dates : « 12 jours
    # plus tard » se comprend d'un coup, « 04/08 » puis « 16/08 » demande un
    # calcul.
    for i, d in enumerate(liste):
        plus_ancien = liste[i + 1] if i + 1 < len(liste) else None
        d["ecart"] = ((d["_d"] - plus_ancien["_d"]).days
                      if d["_d"] and plus_ancien and plus_ancien["_d"] else None)
    return liste


def etat(cle, organisme=None):
    """Tout ce qu'un ecran doit montrer pour un axe, alertes comprises."""
    a = _PAR_CLE.get(cle)
    if not a:
        return None
    decl = sources(cle, organisme)
    ent = entrees(cle, organisme)
    dernier = next((e["_d"] for e in ent if e["_d"]), None)
    depuis = (date.today() - dernier).days if dernier else None
    rythme = _RYTHME.get(cle, 120)
    sans_expl = [e for e in ent if e["sans_exploitation"]]

    # L'indicateur 22 n'est pas une veille : lui servir le vocabulaire de la
    # veille rendrait les messages faux, et un message faux ne se corrige pas,
    # il s'ignore.
    formation = a["champs"] == "formation"
    alertes = []
    if not decl:
        alertes.append({"ton": "rouge", "texte":
            "Aucun axe déclaré. Commencez par dire ce que vous suivez : DPC, congrès, "
            "formation de formateur." if formation else
            "Aucune source déclarée. C'est ce qui fait dire « aucune veille n'existe » — "
            "la non-conformité majeure de cet indicateur."})
    if not ent:
        alertes.append({"ton": "rouge", "texte":
            "Aucune formation consignée. C'est l'unique preuve attendue pour cet "
            "indicateur, et il est classé majeur." if formation else
            "Aucun relevé. Une liste de sources sans relevé ne prouve rien."})
    elif depuis is not None and depuis > rythme:
        alertes.append({"ton": "orange", "texte":
            ("Dernière formation il y a %d jours." if formation else
             "Dernier relevé il y a %d jours. Le rythme attendu ici est de %d jours.")
            % ((depuis,) if formation else (depuis, rythme))})
    if sans_expl:
        alertes.append({"ton": "orange", "texte":
            ("%d formation%s sans apport renseigné. Une formation suivie dont on ne dit "
             "rien ne démontre pas l'entretien des compétences."
             if formation else
             "%d relevé%s sans exploitation. C'est précisément ce que l'auditeur vérifie : "
             "« absence d'exploitation de la veille mise en place » est une non-conformité.")
            % (len(sans_expl), "s" if len(sans_expl) > 1 else "")})
    # Trois relevés saisis le même jour se voient : c'est le reflexe de la veille
    # d'audit, et il se retourne contre celui qui l'a eu.
    if len(ent) >= 3:
        jours_distincts = {e["_d"] for e in ent if e["_d"]}
        if len(jours_distincts) == 1:
            alertes.append({"ton": "orange", "texte":
                "Tous les relevés portent la même date. Une veille se démontre par sa "
                "régularité ; un rattrapage groupé se repère au premier coup d'œil."})

    attente = [r for r in en_attente() if r.split("/")[1:2] == [cle]]
    if attente:
        alertes.append({"ton": "orange", "texte":
            "%d justificatif%s enregistré%s ici mais pas encore remonté%s dans le Drive : "
            "il%s n'est%s consultable que depuis cet ordinateur."
            % ((len(attente),) + (("s",) * 3 if len(attente) > 1 else ("",) * 3)
               + (("s", "nt") if len(attente) > 1 else ("", "")))})

    return {"axe": a, "cle": cle, "sources": decl, "entrees": ent,
            "en_attente": attente,
            "catalogue": catalogue_restant(cle, organisme),
            "nb_sources": len(decl), "nb_entrees": len(ent),
            "sans_exploitation": len(sans_expl),
            "dernier": _fr(dernier.isoformat()) if dernier else "",
            "depuis_jours": depuis, "rythme": rythme,
            "alertes": alertes,
            "solide": bool(decl) and bool(ent) and not sans_expl
                      and (depuis is None or depuis <= rythme)}


def tableau(organisme=None):
    """Les quatre axes, pour l'ecran d'ensemble."""
    return [etat(a["cle"], organisme) for a in AXES]


def resume(organisme=None):
    t = tableau(organisme)
    return {"axes": len(t), "solides": len([x for x in t if x["solide"]]),
            "sans_source": len([x for x in t if not x["nb_sources"]]),
            "sans_releve": len([x for x in t if not x["nb_entrees"]]),
            "relevés_total": sum(x["nb_entrees"] for x in t)}
