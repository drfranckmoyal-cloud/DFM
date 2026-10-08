"""Lecture de fichiers de listes : CSV, TSV, TXT et XLSX.

AUCUNE BIBLIOTHEQUE EXTERIEURE. Un .xlsx est une archive zip contenant du XML,
et Python sait ouvrir les deux. Installer openpyxl aurait ajoute une dependance
de plus a reinstaller le jour d'une panne — et le Python d'Apple, qui sert de
filet a DFM, ne l'a pas.

CE QUE CE MODULE NE FAIT PAS : deviner a quoi servent les colonnes. Il rend le
tableau tel qu'il est, fidelement. La reconnaissance est le travail d'ailleurs.

TROIS PIEGES DU MONDE REEL, rencontres sur un vrai export de formulaire :

  1. Un TELEPHONE saisi sans espace devient un NOMBRE pour le tableur, qui lui
     mange son zero initial : « 0934701336 » ressort en « 934701336 ». On rend
     ici les chiffres tels qu'ils restent ; c'est a l'import de retablir le
     zero, en connaissance de cause.
  2. Un nombre entier ressort en notation scientifique — « 9.34701336E8 ». Le
     rendre tel quel donnerait un telephone illisible.
  3. Une DATE est un nombre de jours depuis 1900. Sans lire les styles, un
     horodateur s'affiche « 45954.69 ».
"""
import csv
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

FORMATS_CONNUS = (".csv", ".tsv", ".txt", ".xlsx")
FORMATS_REFUSES = {
    ".xls": "l'ancien format binaire d'Excel. Ouvrez-le et faites « Enregistrer sous » en .xlsx.",
    ".numbers": "le format d'Apple Numbers. Faites « Fichier → Exporter vers → Excel » ou « CSV ».",
    ".pdf": "un PDF n'est pas un tableau, c'est une image de tableau.",
    ".doc": "un document de traitement de texte.",
    ".docx": "un document de traitement de texte.",
    ".pages": "un document de traitement de texte.",
}
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class Illisible(Exception):
    pass


# --------------------------------------------------------------------------
# XLSX
# --------------------------------------------------------------------------
def _colonne(reference):
    """« BC12 » -> 54. Les cellules vides sont absentes du XML : sans cette
    lecture, une ligne trouee decalerait toutes les colonnes suivantes."""
    n = 0
    for c in reference:
        if not c.isalpha():
            break
        n = n * 26 + (ord(c.upper()) - 64)
    return n - 1


def _texte_si(noeud):
    """Une chaine partagee peut etre decoupee en fragments <r> quand une partie
    est en gras. Les concatener, sinon on ne lit que le premier morceau."""
    return "".join(t.text or "" for t in noeud.iter(_NS + "t"))


def _nombre_lisible(brut):
    """« 9.34701336E8 » -> « 934701336 », « 12.50 » -> « 12.5 »."""
    try:
        v = float(brut)
    except (TypeError, ValueError):
        return brut or ""
    if v == int(v) and abs(v) < 10 ** 15:
        return str(int(v))
    return repr(v)


def _date_lisible(brut):
    try:
        v = float(brut)
    except (TypeError, ValueError):
        return brut or ""
    # 1899-12-30 : le tableur croit que 1900 etait bissextile, ce decalage
    # de deux jours est la convention universelle pour retomber juste.
    d = datetime(1899, 12, 30) + timedelta(days=v)
    return d.strftime("%d/%m/%Y %H:%M" if v % 1 else "%d/%m/%Y")


def _styles_dates(z):
    """Indices de style qui designent une date. Sans cela un horodateur
    s'afficherait « 45954.69 » dans l'apercu."""
    dates = set()
    try:
        racine = ET.fromstring(z.read("xl/styles.xml"))
    except Exception:
        return dates
    perso = {}
    for f in racine.iter(_NS + "numFmt"):
        perso[f.get("numFmtId")] = (f.get("formatCode") or "").lower()
    xfs = racine.find(_NS + "cellXfs")
    if xfs is None:
        return dates
    for i, xf in enumerate(xfs.findall(_NS + "xf")):
        ident = xf.get("numFmtId") or "0"
        code = perso.get(ident, "")
        if (14 <= int(ident) <= 22) or (45 <= int(ident) <= 47) \
                or re.search(r"[dmy]", code) and "[" not in code:
            dates.add(str(i))
    return dates


def _lire_xlsx(chemin):
    try:
        z = zipfile.ZipFile(chemin)
    except Exception as e:
        raise Illisible("Ce fichier .xlsx est illisible : " + str(e)[:80])
    partagees = []
    if "xl/sharedStrings.xml" in z.namelist():
        racine = ET.fromstring(z.read("xl/sharedStrings.xml"))
        partagees = [_texte_si(si) for si in racine.findall(_NS + "si")]
    styles_dates = _styles_dates(z)
    feuilles = sorted(n for n in z.namelist()
                      if n.startswith("xl/worksheets/") and n.endswith(".xml"))
    if not feuilles:
        raise Illisible("Ce classeur ne contient aucune feuille.")
    racine = ET.fromstring(z.read(feuilles[0]))
    lignes, largeur = [], 0
    for tr in racine.iter(_NS + "row"):
        cellules = {}
        for c in tr.findall(_NS + "c"):
            v = c.find(_NS + "v")
            t = c.get("t") or ""
            if t == "inlineStr":
                texte = _texte_si(c)
            elif v is None or v.text is None:
                texte = ""
            elif t == "s":
                i = int(v.text)
                texte = partagees[i] if 0 <= i < len(partagees) else ""
            elif t in ("str", "b", "e"):
                texte = v.text
            elif (c.get("s") or "0") in styles_dates:
                texte = _date_lisible(v.text)
            else:
                texte = _nombre_lisible(v.text)
            cellules[_colonne(c.get("r") or "A1")] = (texte or "").strip()
        if not cellules:
            lignes.append([])
            continue
        haut = max(cellules) + 1
        largeur = max(largeur, haut)
        lignes.append([cellules.get(i, "") for i in range(haut)])
    return [l + [""] * (largeur - len(l)) for l in lignes], len(feuilles)


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------
def _decoder(octets):
    """L'encodage n'est presque jamais declare. On essaie du plus sur au plus
    permissif ; le dernier ne peut pas echouer, au prix de quelques caracteres
    approximatifs — mieux qu'un refus de lire."""
    for codage in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return octets.decode(codage), codage
        except UnicodeDecodeError:
            continue
    return octets.decode("latin-1", "replace"), "latin-1 (approximatif)"


def _lire_csv(chemin):
    texte, codage = _decoder(open(chemin, "rb").read())
    echantillon = texte[:8000]
    try:
        dialecte = csv.Sniffer().sniff(echantillon, delimiters=";,\t|")
        separateur = dialecte.delimiter
    except Exception:
        # Le renifleur echoue sur les fichiers a une seule colonne : on tranche
        # par le comptage, ce qui est plus robuste qu'un echec.
        premiere = echantillon.splitlines()[0] if echantillon.splitlines() else ""
        separateur = max(";,\t|", key=premiere.count)
        if premiere.count(separateur) == 0:
            separateur = ","
    lignes = [[(c or "").strip() for c in l]
              for l in csv.reader(io.StringIO(texte), delimiter=separateur)]
    largeur = max((len(l) for l in lignes), default=0)
    return [l + [""] * (largeur - len(l)) for l in lignes], codage, separateur


# --------------------------------------------------------------------------
# Ou commencent vraiment les donnees
# --------------------------------------------------------------------------
# LES EN-TETES NE SONT PAS TOUJOURS EN PREMIERE LIGNE. Un vrai fichier de
# l'utilisateur commencait par un bandeau de titre, puis un decompte, et les
# en-tetes n'arrivaient qu'en troisieme ligne. Resultat : la ligne d'en-tetes
# elle-meme etait importee comme un contact, nomme « NOM Prenom ».
# On cherche donc la ligne qui RESSEMBLE LE PLUS a des en-tetes dans les
# premieres lignes, plutot que de supposer la premiere.
_VOCABULAIRE = ("nom", "prenom", "mail", "email", "courriel", "tel", "telephone",
                "portable", "mobile", "gsm", "ville", "adresse", "contact", "origine",
                "societe", "cabinet", "fonction", "date", "commentaire", "code postal")


def _aplat(v):
    import unicodedata
    s = unicodedata.normalize("NFD", str(v or "")).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def _score_entete(ligne):
    """Combien de cellules de cette ligne ressemblent a un intitule."""
    remplies = [c for c in ligne if (c or "").strip()]
    if len(remplies) < 2:
        return 0                      # un titre seul sur sa ligne n'est pas un en-tete
    points = 0
    for c in remplies:
        p = _aplat(c)
        if not p or len(p) > 42:
            continue
        if "@" in (c or "") or re.fullmatch(r"[\d\s.+()-]{8,}", (c or "").strip()):
            return 0                  # ce sont des donnees, pas des intitules
        if any(m == p or (" " + m + " ") in (" " + p + " ") for m in _VOCABULAIRE):
            points += 2
        elif len(p.split()) <= 3:
            points += 1
    return points


def _trouver_entete(lignes, profondeur=8):
    """(rang de la ligne d'en-tetes, intitules) ou (-1, []) s'il n'y en a pas."""
    meilleur, rang = 0, -1
    for i, l in enumerate(lignes[:profondeur]):
        s = _score_entete(l)
        if s > meilleur:
            meilleur, rang = s, i
    if rang < 0 or meilleur < 2:
        return -1, []
    ligne = lignes[rang]
    return rang, [(c or "").strip() or "Colonne %d" % (i + 1) for i, c in enumerate(ligne)]


# --------------------------------------------------------------------------
# Entree unique
# --------------------------------------------------------------------------
def lire(chemin, max_lignes=100000):
    """Rend {"lignes", "entetes", "avec_entetes", "format", "detail"}.

    La premiere ligne est prise pour des en-tetes si elle ne ressemble PAS a
    des donnees — pas d'arobase, pas de suite de chiffres. Un fichier sans
    en-tetes existe, et lui manger sa premiere personne serait pire que de
    nommer les colonnes « Colonne 1 »."""
    if not os.path.exists(chemin):
        raise Illisible("Fichier introuvable.")
    ext = os.path.splitext(chemin)[1].lower()
    if ext in FORMATS_REFUSES:
        raise Illisible("Format non lu — c'est " + FORMATS_REFUSES[ext])
    if ext not in FORMATS_CONNUS:
        raise Illisible("Extension inconnue « %s ». Formats lus : %s."
                        % (ext, ", ".join(FORMATS_CONNUS)))

    if ext == ".xlsx":
        lignes, nb_feuilles = _lire_xlsx(chemin)
        detail = "classeur Excel, %d feuille(s), la premiere est lue" % nb_feuilles
    else:
        lignes, codage, sep = _lire_csv(chemin)
        nom_sep = {";": "point-virgule", ",": "virgule", "\t": "tabulation", "|": "barre"}
        detail = "texte %s, separateur %s" % (codage, nom_sep.get(sep, repr(sep)))

    lignes = [l for l in lignes if any((c or "").strip() for c in l)][:max_lignes]
    if not lignes:
        raise Illisible("Le fichier ne contient aucune ligne remplie.")

    rang, entetes = _trouver_entete(lignes)
    if rang < 0:
        entetes = ["Colonne %d" % (i + 1) for i in range(len(lignes[0]))]
        corps, avec, preambule = lignes, False, 0
    else:
        corps, avec, preambule = lignes[rang + 1:], True, rang
    if preambule:
        detail += ", %d ligne(s) de titre ignorée(s) avant les en-têtes" % preambule
    return {"lignes": corps, "entetes": entetes, "avec_entetes": avec,
            "preambule": preambule, "format": ext.lstrip("."), "detail": detail}
