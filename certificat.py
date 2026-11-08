# -*- coding: utf-8 -*-
"""Le certificat de fin de formation, a remettre en plus de l'attestation.

POURQUOI IL EXISTE — 08/11/2026, demande de Franck : « on va mettre en place la
generation automatique de diplomes, on commence avec Usures ». L'attestation
est la piece reglementaire (article L.6353-1) ; le certificat est le document
qu'on garde, qu'on encadre, qu'on montre. Il ne la remplace pas : il part
AVEC elle, dans le meme mail, et seulement si elle part.

LE MODELE EST DESSINE DANS CANVA, PAS ICI. Franck a compose le certificat
(« CERTIFICAT USURES », design DAG419MkBkg). DFM n'en garde que le FOND — tout
sauf le nom, les dates et le « DR » — exporte en image a 300 points par pouce,
et il y ecrit lui-meme ce qui change d'une personne a l'autre. Aucun appel a
Canva au moment de fabriquer : le serveur n'y a pas acces, et un certificat ne
doit pas dependre d'un service tiers pour sortir.

UN FOND PAR ORGANISME ET PAR FORMATION :
    identite/<organisme>/certificats/<formation>.jpg
Le titre de la formation et le logo sont dans l'image ; une formation sans
fond n'a pas de certificat, et rien ne change pour elle. DSF n'en a pas : le
fond d'Usures porte le logo Smileclub, et une session DSF d'Usures ne doit
jamais le recevoir — deux entites, deux identites.

LA DISPOSITION EST CELLE DU MODELE CANVA, en pixels Canva (page de 1123 sur
794, soit exactement un A4 paysage en pixels CSS). Un autre fond dessine sur
le meme modele — Masterclass, avec son titre — la reutilise telle quelle.

« DR » NE S'ECRIT QUE DEVANT UN PRATICIEN. Le modele le portait en dur ; une
assistante dentaire aurait recu un certificat au nom du « DR ». DFM l'ecrit
lui-meme, selon la fonction de la personne.
"""
import os
from datetime import date

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_STATIQUE = os.path.join(_DOSSIER, "static")

# La disposition du modele Canva « CERTIFICAT USURES », relevee le 08/11/2026.
DISPOSITION = {
    # Le nom, centre au-dessus du filet bleu (x 259 a 879, y 442).
    "nom": {"gauche": 259, "largeur": 620, "bas": 443, "taille": 63.6,
            "couleur": "#38527d", "espacement": 0.052},
    # Les dates, sous « Dates: » en bas a droite : le libelle est dans le fond.
    "dates": {"gauche": 848, "haut": 681, "largeur": 262, "taille": 24,
              "couleur": "#000001", "alignement": "left", "prefixe": ""},
}
# UNE DISPOSITION PAR MODELE, quand le modele differe — 08/11/2026. Celui de la
# Masterclass (« Certificat MASTECLASS Compo ») centre un nom plus grand sur la
# page, et ecrit « Date: » et la date sur UNE ligne alignee a droite : le
# libelle n'est pas dans le fond, DFM l'ecrit avec la date.
DISPOSITIONS = {
    "masterclass": {
        "nom": {"gauche": 182, "largeur": 760, "bas": 443, "taille": 74.8,
                "couleur": "#38527d", "espacement": 0.052},
        "dates": {"gauche": 691.5, "haut": 651.7, "largeur": 375.7, "taille": 24,
                  "couleur": "#000001", "alignement": "right", "prefixe": "Date: "},
    },
}


def disposition(code_formation):
    return DISPOSITIONS.get(code_formation or "", DISPOSITION)

# Chasses des glyphes, en fraction de corps, mesurees sur les polices le
# 08/11/2026 (fontTools). Elles servent a REDUIRE le corps d'un nom trop long
# pour tenir sur le filet : le serveur n'a pas fontTools, et un PDF ne
# s'ajuste pas tout seul. Un caractere absent compte large : mieux vaut un nom
# un peu petit qu'un nom qui deborde.
_BEBAS = {
    "A": .401, "B": .404, "C": .383, "D": .406, "E": .363, "F": .344, "G": .391,
    "H": .42, "I": .192, "J": .265, "K": .414, "L": .344, "M": .538, "N": .427,
    "O": .4, "P": .386, "Q": .4, "R": .403, "S": .372, "T": .364, "U": .402,
    "V": .382, "W": .557, "X": .406, "Y": .394, "Z": .362, " ": .16, "-": .27,
    "'": .188, ".": .188,
}
_QUESTRIAL = {
    "D": .703, ":": .203, "0": .55, "1": .55, "2": .55, "3": .55, "4": .55, "5": .55, "6": .55,
    "7": .55, "8": .55, "9": .55, " ": .213, "-": .36, ",": .22, ".": .203,
    "a": .595, "b": .595, "c": .544, "d": .595, "e": .557, "f": .307, "g": .595,
    "h": .566, "i": .205, "j": .205, "k": .502, "l": .205, "m": .868, "n": .566,
    "o": .564, "p": .595, "q": .595, "r": .345, "s": .482, "t": .326, "u": .566,
    "v": .489, "w": .746, "x": .482, "y": .497, "z": .458,
}
_SANS_ACCENT = str.maketrans("ÀÂÄÁÃÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝŸàâäáãçéèêëíìîïñóòôöõúùûüýÿ",
                             "AAAAACEEEEIIIINOOOOOUUUUYYaaaaaceeeeiiiinooooouuuuyy")
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre")


def fond(code_session):
    """Le chemin du fond de cette session, ou None : pas de fond, pas de certificat."""
    import sessions as _s
    org = _s.organisme_de(code_session) or ""
    formation = (_s.SESSIONS.get(code_session) or {}).get("formation") or ""
    if not org or not formation:
        return None
    p = os.path.join(_DOSSIER, "identite", org, "certificats", formation + ".jpg")
    return p if os.path.exists(p) else None


def _chasse(texte, table, espacement=0.0, defaut=0.6):
    t = str(texte or "").translate(_SANS_ACCENT)
    return sum(table.get(c, table.get(c.upper(), defaut)) + espacement for c in t)


def corps_qui_tient(texte, table, taille, largeur, espacement=0.0):
    """Le corps le plus grand, jusqu'a `taille`, auquel `texte` tient dans `largeur`."""
    em = _chasse(texte, table, espacement)
    if em <= 0:
        return taille
    return round(min(taille, largeur / em), 1)


def dates_courtes(jours):
    """« 4 et 5 novembre 2026 » : ce qui tient sous « Dates: ».

    Le texte long de la session (« mercredi 4 et jeudi 5 novembre 2026 »)
    deborderait de la page a cet endroit. Un cycle etale sur l'annee s'ecrit
    par ses bornes.
    """
    d = sorted({j for j in (jours or []) if j})
    if not d:
        return ""
    dts = [date.fromisoformat(j) for j in d]

    def jour(x):
        return "1er" if x.day == 1 else str(x.day)

    def liste(nombres):
        return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " et " + nombres[-1]

    groupes = []
    for x in dts:
        if groupes and (groupes[-1][0].year, groupes[-1][0].month) == (x.year, x.month):
            groupes[-1].append(x)
        else:
            groupes.append([x])
    if len(groupes) > 2:
        a, b = dts[0], dts[-1]
        return "du %s %s%s au %s %s %d" % (
            jour(a), MOIS[a.month - 1], "" if a.year == b.year else " %d" % a.year,
            jour(b), MOIS[b.month - 1], b.year)
    meme_annee = len({g[0].year for g in groupes}) == 1
    morceaux = []
    for g in groupes:
        m = "%s %s" % (liste([jour(x) for x in g]), MOIS[g[0].month - 1])
        if not meme_annee:
            m += " %d" % g[0].year
        morceaux.append(m)
    texte = " et ".join(morceaux)
    return texte + (" %d" % dts[0].year if meme_annee else "")


def _praticien(ligne):
    import contacts as _C
    f = _C.fonction_ou_defaut((ligne or {}).get("fonction")).lower()
    return "dentiste" in f and "assistant" not in f


def nom_affiche(ligne):
    """« NOM Prénom », comme le champ du modele Canva ; la police met en capitales."""
    nom = ((ligne or {}).get("nom") or "").strip().upper()
    prenom = ((ligne or {}).get("prenom") or "").strip()
    return " ".join(x for x in (nom, prenom) if x)


def _police(nom):
    import base64
    p = os.path.join(_STATIQUE, nom)
    with open(p, "rb") as f:
        return "data:font/woff2;base64," + base64.b64encode(f.read()).decode()


def pour(code_session, ligne):
    """Le dossier d'un certificat, pret pour le gabarit. None si pas de fond."""
    import base64
    import jours as _J
    import sessions as _s
    chemin = fond(code_session)
    if not chemin:
        return None
    S = _s.session(code_session)
    with open(chemin, "rb") as f:
        image = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    titre = "DR" if _praticien(ligne) else ""
    nom = nom_affiche(ligne)
    D = disposition((_s.SESSIONS.get(code_session) or {}).get("formation"))
    # Le « DR » et le nom forment UNE ligne, centree sur le filet : c'est elle
    # qui doit tenir. L'ecart entre les deux vaut une demi-ligne.
    complet = (titre + "  " + nom) if titre else nom
    taille_nom = corps_qui_tient(complet, _BEBAS, D["nom"]["taille"], D["nom"]["largeur"],
                                 D["nom"]["espacement"])
    dates = D["dates"].get("prefixe", "") + dates_courtes(_J.resume(S).get("jours"))
    taille_dates = corps_qui_tient(dates, _QUESTRIAL, D["dates"]["taille"], D["dates"]["largeur"])
    return {
        "fond": image, "titre": titre, "nom": nom, "dates": dates,
        "taille_nom": taille_nom, "taille_dates": taille_dates, "d": D,
        "police_nom": [_police("bebas-neue-latin.woff2"), _police("bebas-neue-latin-ext.woff2")],
        "police_dates": [_police("questrial-latin.woff2"), _police("questrial-latin-ext.woff2")],
        "session": code_session,
    }


def html(donnees):
    from flask import render_template
    import app as _app
    with _app.app.app_context():
        return render_template("certificat.html", c=donnees)


def nom_fichier(ligne):
    return "Certificat - %s %s.pdf" % ((ligne.get("prenom") or "").strip(),
                                       (ligne.get("nom") or "").strip())


def fabriquer(code_session, ligne):
    """Les octets du PDF, ou None si la formation n'a pas de certificat."""
    import pdf as _pdf
    d = pour(code_session, ligne)
    if not d:
        return None
    return _pdf.depuis_html(html(d))


def beneficiaires(code_session):
    """Les inscrits qui ont droit a un certificat : actifs, ni simples demandes
    de rappel, ni en attente. La meme regle que pour l'attestation."""
    import suivi
    return [l for l in suivi.lire_lignes_de(code_session)
            if not l["annule_le"]
            and "recontact" not in (l["demande"] or "").lower()
            and suivi.calculer_statut(l) not in suivi.PAS_ENCORE_INSCRIT]


def present(code_session, ligne):
    """Le certificat de cette personne est-il fabrique ? Sans le lire."""
    import documents
    return bool(documents.chemin(documents.reference(code_session, "certificat",
                                                     nom_fichier(ligne))))


def lien(code_session, ligne):
    """Le lien Drive du certificat, comme pour les autres pieces ; a defaut —
    copie Drive pas encore partie —, l'adresse ou DFM le sert lui-meme."""
    import documents
    l = documents.lien(documents.reference(code_session, "certificat", nom_fichier(ligne)))
    return l or "/session/%s/certificat/%s" % (code_session, (ligne or {}).get("mail") or "")


def existant(code_session, ligne):
    """Les octets du certificat deja range pour cette personne, ou None."""
    import documents
    return documents.lire(documents.reference(code_session, "certificat", nom_fichier(ligne)))


# ---------------------------------------------------------------------------
# LE MAIL DU LENDEMAIN — 08/11/2026
#
# Le certificat part le lendemain du dernier jour, a l'heure reglee dans les
# parametres (« heure_certificat »), avec l'attestation, un code pour la
# prochaine formation et la demande d'avis. Le guet des questionnaires le
# declenche ; envoyer_certificats.py le compose et l'envoie.
#
# UN ENVOI SE RETIENT, comme un questionnaire : « auto » a faux, et rien ne
# part. Une session dont le lendemain est passe depuis plus de sept jours ne
# part pas toute seule — un mail de remerciement trois semaines apres la
# formation n'a plus de sens, et un deploiement ne doit pas reveiller d'anciens
# envois. L'etat vit dans certificats_etat.json : {code: {auto, envoye_le}}.
# ---------------------------------------------------------------------------
ETAT = os.path.join(_DOSSIER, "certificats_etat.json")
RETARD_MAX_JOURS = 7


def etat_envoi(code_session):
    import fichiers
    d = (fichiers.lire(ETAT, {}) or {}).get(code_session) or {}
    return {"auto": d.get("auto", True), "envoye_le": d.get("envoye_le") or ""}


def poser_envoi(code_session, **valeurs):
    import fichiers
    with fichiers.modifier(ETAT, {}) as tout:
        d = tout.setdefault(code_session, {})
        d.update(valeurs)
    return etat_envoi(code_session)


def moment_envoi(code_session):
    """Le lendemain du dernier jour, a l'heure reglee. None sans journees."""
    from datetime import datetime, timedelta
    import jours as _J
    import sessions as _s
    try:
        fin = _J.resume(_s.session(code_session)).get("date_fin")
    except Exception:
        fin = None
    if not fin:
        return None
    try:
        import parametres
        heure = str(parametres.valeur("heure_certificat", "12:30") or "12:30")
    except Exception:
        heure = "12:30"
    try:
        h, m = (int(x) for x in heure.split(":")[:2])
    except ValueError:
        h, m = 12, 30
    return datetime.strptime(fin, "%Y-%m-%d") + timedelta(days=1, hours=h, minutes=m)


def a_envoyer_maintenant(code_session, maintenant=None):
    """(oui, raison) : le mail du lendemain doit-il partir maintenant ?"""
    from datetime import datetime
    if not fond(code_session):
        return False, "pas de certificat pour cette formation"
    e = etat_envoi(code_session)
    if e["envoye_le"]:
        return False, "deja envoye le " + e["envoye_le"]
    if not e["auto"]:
        return False, "envoi retenu"
    moment = moment_envoi(code_session)
    if not moment:
        return False, "session sans journees"
    maintenant = maintenant or datetime.now()
    if maintenant < moment:
        return False, "prevu le " + moment.strftime("%d/%m/%Y a %H:%M")
    if (maintenant - moment).days > RETARD_MAX_JOURS:
        return False, "trop tard pour partir seul"
    return True, ""
