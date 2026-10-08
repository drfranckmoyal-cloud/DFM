"""Reconnaissance des colonnes d'un fichier de liste, avant import.

DEUX SIGNAUX, ET LE SECOND L'EMPORTE : l'intitule de la colonne, et son
CONTENU. Les intitules mentent — « Colonne 3 », « Champ1 », ou pas d'intitule
du tout. Une colonne dont 80 % des valeurs contiennent une arobase est une
colonne d'adresses, quel que soit son titre.

RIEN N'EST IMPORTE ICI. Ce module propose, compte et explique. L'ecriture ne
se fait qu'apres validation, et la proposition est corrigeable colonne par
colonne — se tromper de colonne sur trois mille lignes ne doit pas etre
rattrapable seulement par une suppression.
"""
import re
import unicodedata

import contacts as C

CHAMPS = ("mail", "telephone", "nom", "prenom", "ville", "ignore")
LIBELLES = {"mail": "Adresse mail", "telephone": "Téléphone", "nom": "Nom",
            "prenom": "Prénom", "ville": "Ville", "ignore": "Ignorée"}

_MOTS = {
    "mail": ("mail", "email", "e mail", "courriel", "adresse mail", "adresse e mail", "mel"),
    "telephone": ("tel", "telephone", "portable", "mobile", "gsm", "numero telephone",
                  "num tel", "phone"),
    # Une colonne qui porte le nom ET le prenom va dans « nom », TELLE QUELLE.
    # On ne decoupe plus : la saisie est ce qu'elle est, et deviner l'ordre
    # produisait des inversions invisibles sur les lignes sans majuscules.
    "nom": ("nom", "nom de famille", "last name", "surname", "nom famille",
            "nom prenom", "prenom nom", "nom complet", "nom et prenom",
            "identite", "participant", "praticien", "contact", "name",
            "full name", "nom du praticien", "nom du participant"),
    "prenom": ("prenom", "first name", "given name"),
    "ville": ("ville", "commune", "localite", "city", "ville d exercice"),
}


def _plat(v):
    s = unicodedata.normalize("NFD", str(v or "")).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


# --------------------------------------------------------------------------
# Reconnaissance du contenu
# --------------------------------------------------------------------------
def est_mail(v):
    v = (v or "").strip()
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$", v))


def est_telephone(v):
    """Une DATE n'est pas un telephone. « 24/10/2025 16:43 » prive de ses
    separateurs donne douze chiffres, ce qui rentrait dans la fourchette : la
    colonne « Horodateur » d'un export de formulaire etait reconnue comme la
    colonne des numeros. Ni la barre oblique ni les deux-points n'existent
    dans un numero de telephone."""
    brut = str(v or "")
    if re.search(r"[/:]", brut):
        return False
    n = re.sub(r"\D", "", brut)
    return 9 <= len(n) <= 15 and not est_mail(v)


def est_nom(v):
    """Du texte, sans arobase ni majorite de chiffres. Volontairement large :
    c'est le plus faible des trois signaux, il ne sert qu'a departager."""
    v = (v or "").strip()
    if not v or est_mail(v) or est_telephone(v):
        return False
    lettres = sum(1 for c in v if c.isalpha())
    return lettres >= 2 and lettres >= len(v) / 2


def normaliser_telephone(v):
    """Retablit le zero initial mange par le tableur.

    Un numero saisi sans espace devient un NOMBRE pour Excel, qui supprime son
    zero de tete : « 0682560087 » ressort « 682560087 ». Neuf chiffres
    commencant par 1 a 9 sont donc un numero francais ampute — on le lui rend.
    Verifie sur un export reel : 10 numeros sur 87 etaient dans ce cas."""
    brut = (v or "").strip()
    if not brut:
        return ""
    if brut.startswith("+"):
        return brut
    n = re.sub(r"\D", "", brut)
    if len(n) == 9 and n[0] in "123456789":
        return "0" + n
    return brut


# decouper_nom() a ete retiree. Elle rendait « Aaron Bitton » en nom « Aaron »,
# prenom « Bitton », parce qu'aucun signal ne dit dans quel ordre une personne
# a tape son propre nom. Sur 83 lignes reelles, 60 n'avaient aucune majuscule
# pour trancher. On enregistre desormais TEL QUEL : ce qui est saisi est ce qui
# est garde, sans interpretation.


# --------------------------------------------------------------------------
# Proposition
# --------------------------------------------------------------------------
def _par_intitule(plat):
    """Le libelle LE PLUS SPECIFIQUE l'emporte, jamais le premier trouve.

    « NOM Prénom » contient « prenom », et un appariement au premier mot le
    classait donc en colonne de prenoms — alors que l'expression complete
    « nom prenom » designe une colonne qui porte les deux. On compare la
    longueur de l'expression reconnue, et on exige des mots entiers pour que
    « nom » ne se declenche pas sur « nom de la formation »."""
    trouve, longueur = "", 0
    for champ, expressions in _MOTS.items():
        for expr in expressions:
            if re.search(r"(?:^| )" + re.escape(expr) + r"(?:$| )", plat) and len(expr) > longueur:
                trouve, longueur = champ, len(expr)
    return trouve


def _score_contenu(valeurs):
    remplies = [v for v in valeurs if (v or "").strip()]
    if not remplies:
        return {}
    n = float(len(remplies))
    return {"mail": sum(1 for v in remplies if est_mail(v)) / n,
            "telephone": sum(1 for v in remplies if est_telephone(v)) / n,
            "nom": sum(1 for v in remplies if est_nom(v)) / n}


def reconnaitre(entetes, lignes, echantillon=60):
    """Rend une proposition par colonne, avec sa raison. Ne decide rien."""
    colonnes = []
    pris = set()
    scores = []
    for i, titre in enumerate(entetes):
        valeurs = [(l[i] if i < len(l) else "") for l in lignes[:echantillon]]
        sc = _score_contenu(valeurs)
        p = _plat(titre)
        par_titre = _par_intitule(p)
        scores.append((i, titre, valeurs, sc, par_titre))

    # Le contenu tranche en premier, et seulement s'il est franc.
    for i, titre, valeurs, sc, par_titre in scores:
        champ, raison = "", ""
        if sc.get("mail", 0) >= 0.6:
            champ, raison = "mail", "%d %% des valeurs sont des adresses" % round(sc["mail"] * 100)
        elif sc.get("telephone", 0) >= 0.6:
            champ, raison = "telephone", "%d %% des valeurs sont des numéros" % round(sc["telephone"] * 100)
        elif par_titre:
            champ, raison = par_titre, "reconnue par son intitulé"
        elif sc.get("nom", 0) >= 0.7 and "nom" not in pris:
            champ, raison = "nom", "du texte, aucune autre colonne ne porte le nom"
        if champ and champ != "ignore" and champ in pris:
            champ, raison = "ignore", "une autre colonne porte déjà « %s »" % LIBELLES.get(champ, champ)
        if not champ:
            champ, raison = "ignore", "aucun contenu reconnaissable"
        if champ != "ignore":
            pris.add(champ)
        remplies = len([v for v in valeurs if (v or "").strip()])
        colonnes.append({
            "index": i, "titre": titre or "Colonne %d" % (i + 1),
            "champ": champ, "raison": raison,
            "exemples": [v for v in valeurs if (v or "").strip()][:3],
            "remplies": remplies, "vues": len(valeurs),
        })
    return colonnes


def apercu(entetes, lignes, colonnes, combien=6):
    """Ce que donneraient les premieres lignes, une fois la proposition
    appliquee. C'est ce que l'utilisateur regarde avant de valider — et c'est
    la seule facon de voir qu'un decoupage de nom part de travers."""
    plan = {c["champ"]: c for c in colonnes if c["champ"] != "ignore"}
    sortie = []
    for l in lignes[:combien]:
        sortie.append(_fiche(l, plan))
    return sortie


def _fiche(ligne, plan):
    def val(champ):
        c = plan.get(champ)
        if not c:
            return ""
        i = c["index"]
        return (ligne[i] if i < len(ligne) else "").strip()

    return {"nom": val("nom"), "prenom": val("prenom"), "mail": val("mail"),
            "telephone": normaliser_telephone(val("telephone")), "ville": val("ville")}


def preparer(entetes, lignes, colonnes):
    """Transforme tout le fichier, sans rien ecrire. Rend les fiches
    exploitables, celles ecartees avec leur motif, et les doublons INTERNES au
    fichier — deux lignes du meme fichier qui designent la meme personne, cas
    frequent et qu'il vaut mieux fondre avant d'interroger la base."""
    plan = {c["champ"]: c for c in colonnes if c["champ"] != "ignore"}
    retenues, ecartees = [], []
    par_cle, internes = {}, 0
    for numero, l in enumerate(lignes, 1):
        f = _fiche(l, plan)
        cle = C.norm_mail(f["mail"]) or C.norm_tel(f["telephone"])
        if not cle:
            ecartees.append({"ligne": numero, "motif": "ni adresse mail ni téléphone exploitable",
                             "apercu": " · ".join(x for x in l if x)[:70]})
            continue
        if cle in par_cle:
            internes += 1
            garde = par_cle[cle]
            for champ in ("nom", "prenom", "mail", "telephone", "ville"):
                if not garde[champ] and f[champ]:
                    garde[champ] = f[champ]
            continue
        par_cle[cle] = f
        retenues.append(f)
    sans_nom = len([f for f in retenues if not f["nom"] and not f["prenom"]])
    return {"retenues": retenues, "ecartees": ecartees,
            "doublons_internes": internes, "sans_nom": sans_nom,
            "avec_mail": len([f for f in retenues if f["mail"]]),
            "avec_tel": len([f for f in retenues if f["telephone"]]),
            "lues": len(lignes)}


# --------------------------------------------------------------------------
# Ecriture
# --------------------------------------------------------------------------
def executer(retenues, marqueurs, lot, source=""):
    """Ecrit les fiches. NE REMPLIT QUE CE QUI EST VIDE, n'ecrase jamais.

    Une valeur du fichier differente de celle deja connue n'est pas une
    correction : c'est une question. Elle remonte dans le compte rendu, sur le
    petit nombre de cas qui la meritent, et l'utilisateur tranche la. Ecraser
    en masse effacerait sans bruit un travail de saisie.

    Les marqueurs, eux, s'ajoutent TOUJOURS — y compris aux fiches deja
    connues. C'est le sens de l'operation : un contact deja present qui figure
    dans la liste du congres doit porter le marqueur du congres.

    Un seul aller-retour de lecture, une creation groupee, puis les seules
    corrections necessaires."""
    marqueurs = sorted({C.cle_marqueur(m) for m in (marqueurs or []) if m})
    existantes, _ = C._appel(C.TABLE + "?select=id,nom,prenom,mail,telephone,ville,mail_norm,tel_norm,marqueurs")
    par_mail = {l["mail_norm"]: l for l in existantes if l.get("mail_norm")}
    par_tel = {l["tel_norm"]: l for l in existantes if l.get("tel_norm")}

    a_creer, divergences, completes, inchanges = [], [], 0, 0
    for f in retenues:
        m, t = C.norm_mail(f["mail"]), C.norm_tel(f["telephone"])
        connue = par_mail.get(m) if m else None
        if connue is None and t:
            connue = par_tel.get(t)
        if connue is None:
            d = dict(f)
            d["marqueurs"] = marqueurs
            d["lot_import"] = lot
            d["source"] = source
            a_creer.append(d)
            continue
        a_poser = {}
        for champ in ("nom", "prenom", "mail", "telephone", "ville"):
            neuf = (f.get(champ) or "").strip()
            if not neuf:
                continue
            ancien = (connue.get(champ) or "").strip()
            if not ancien:
                a_poser[champ] = neuf
            elif C._comparable(champ, ancien) != C._comparable(champ, neuf):
                divergences.append({"id": connue["id"],
                                    "qui": C.nom_affiche(connue), "champ": champ,
                                    "connu": ancien, "fichier": neuf})
        ensemble = sorted(set(connue.get("marqueurs") or []) | set(marqueurs))
        if ensemble != sorted(connue.get("marqueurs") or []):
            a_poser["marqueurs"] = ensemble
        if a_poser:
            C.modifier(connue["id"], a_poser)
            completes += 1
        else:
            inchanges += 1

    crees = []
    for i in range(0, len(a_creer), 200):      # par paquets : une requete geante
        crees += C.creer_en_lot(a_creer[i:i + 200])   # se fait refuser au-dela
    return {"crees": len(crees), "completes": completes, "inchanges": inchanges,
            "divergences": divergences, "lot": lot}
