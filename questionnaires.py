SEUIL_DEFAUT = 70
EVALUATIONS = {
    "usures": {
        "titre": "Évaluation des connaissances — Usures",
        "seuil": 70,
        "objectifs": {
            "A": "Connaître les différents types d'usure et leur étiologie",
            "B": "Maîtriser la méthodologie de prise en charge globale",
            "C": "Choisir le matériau de restauration adapté",
        },
        "questions": [
            {"id": "u01", "objectif": "A", "type": "qcm", "poids": 1,
             "enonce": "L'abrasion dentaire correspond à :",
             "propositions": ["Une usure mécanique exclusivement",
                              "Une usure chimique exclusivement",
                              "Une combinaison d'usure mécanique et érosive",
                              "Une usure par contact dent contre dent"],
             "reponse": 0,
             "explication": "L'abrasion est mécanique et d'origine exogène. Le contact dent contre dent est l'attrition, l'origine chimique est l'érosion."},
            {"id": "u02", "objectif": "A", "type": "qcm", "poids": 1,
             "enonce": "L'usure due exclusivement au contact dent contre dent se nomme :",
             "propositions": ["Abrasion", "Attrition", "Érosion", "Abfraction"],
             "reponse": 1,
             "explication": "L'attrition désigne l'usure par contact des surfaces dentaires entre elles."},
            {"id": "u03", "objectif": "A", "type": "vf", "poids": 1,
             "enonce": "Certains médicaments peuvent favoriser les risques d'usure.",
             "propositions": ["Vrai", "Faux"], "reponse": 0,
             "explication": "Principalement par hyposialie, qui prive la dent de son tampon salivaire. Certaines formes acides agissent aussi directement."},
            {"id": "u04", "objectif": "A", "type": "vf", "poids": 2,
             "enonce": "Dans les usures érosives, on peut observer un différentiel de niveau entre les restaurations présentes et la surface de la dent.",
             "propositions": ["Vrai", "Faux"], "reponse": 0,
             "explication": "Les matériaux de restauration ne se dissolvent pas et émergent progressivement en relief. C'est un signe d'appel majeur."},
            {"id": "u05", "objectif": "A", "type": "vf", "poids": 1,
             "enonce": "Les régimes végétariens et végan augmentent le risque d'usure érosive.",
             "propositions": ["Vrai", "Faux"], "reponse": 0,
             "explication": "Consommation accrue d'agrumes, de crudités et de boissons acides."},
            {"id": "u06", "objectif": "A", "type": "vf", "poids": 1,
             "enonce": "La grossesse augmente les risques d'usure.",
             "propositions": ["Vrai", "Faux"], "reponse": 0,
             "explication": "Reflux gastro-œsophagiens et vomissements, surtout au premier trimestre."},
            {"id": "u07", "objectif": "B", "type": "qcm", "poids": 2,
             "enonce": "L'augmentation de dimension verticale dans le traitement de l'usure a pour but principal :",
             "propositions": ["De compenser la DVO perdue",
                              "De créer l'espace prothétique nécessaire au projet esthétique et fonctionnel",
                              "De traiter le bruxisme",
                              "De corriger la classe squelettique"],
             "reponse": 1,
             "explication": "L'usure est compensée par l'égression continue : la DVO est rarement réellement perdue. On augmente pour créer de la place."},
            {"id": "u08", "objectif": "B", "type": "qcm", "poids": 2,
             "enonce": "Par rotation mandibulaire, l'augmentation de dimension verticale :",
             "propositions": ["Aggrave une classe II et compense une classe III",
                              "Aggrave une classe III et compense une classe II",
                              "N'a aucun effet sur la classe squelettique",
                              "A un effet variable selon l'âge du patient"],
             "reponse": 0,
             "explication": "La mandibule tourne vers le bas et l'arrière : le décalage antéro-postérieur d'une classe II s'accentue, celui d'une classe III se réduit."},
            {"id": "u09", "objectif": "B", "type": "qcm", "poids": 1,
             "enonce": "Pour une augmentation de 3 mm au niveau de la tige incisive, l'augmentation obtenue dans les secteurs postérieurs est d'environ :",
             "propositions": ["1 mm", "2 mm", "3 mm", "4 mm"],
             "reponse": 0,
             "explication": "L'ouverture se répartit selon un axe de rotation condylien : le gain postérieur vaut environ un tiers du gain antérieur."},
            {"id": "u10", "objectif": "B", "type": "qcm", "poids": 2,
             "enonce": "Pour une réhabilitation d'usure, la position mandibulaire de référence est :",
             "propositions": ["L'OIM", "Une position déprogrammée",
                              "La position de repos", "La position de déglutition"],
             "reponse": 1,
             "explication": "L'OIM sur des dents usées est une position adaptative, construite sur la pathologie. La déprogrammation permet de repartir d'une référence articulaire fiable."},
            {"id": "u11", "objectif": "B", "type": "vf", "poids": 1,
             "enonce": "La réhabilitation des faces palatines du secteur antérieur maxillaire est indispensable en cas d'augmentation de DVO, pour restaurer le guidage antérieur.",
             "propositions": ["Vrai", "Faux"], "reponse": 0,
             "explication": "Sans reconstruction palatine, le guidage antérieur est perdu et les contraintes se reportent sur les secteurs postérieurs."},
            {"id": "u12", "objectif": "C", "type": "qcm", "poids": 2,
             "enonce": "Chez le patient bruxomane, le composite est :",
             "propositions": ["Contre-indiqué",
                              "Un matériau de choix, réparable et respectueux de l'antagoniste",
                              "Réservé aux secteurs postérieurs",
                              "Utilisable uniquement après port d'une gouttière"],
             "reponse": 1,
             "explication": "Le composite s'use sans abraser l'antagoniste et se répare au fauteuil, deux atouts majeurs chez le bruxomane."},
        ],
    },
}
SATISFACTION = {
    "titre": "Questionnaire de satisfaction",
    "axes": {"avant": "Avant la formation", "pendant": "Pendant la formation",
             "apres": "Résultats et suites"},
    "notes": [
        {"id": "s01", "axe": "avant", "libelle": "Clarté des informations reçues avant la formation"},
        {"id": "s02", "axe": "avant", "libelle": "Qualité de l'accueil et des conditions matérielles"},
        {"id": "s03", "axe": "pendant", "libelle": "Adéquation du contenu aux objectifs annoncés"},
        {"id": "s04", "axe": "pendant", "libelle": "Qualité de l'animation et des explications"},
        {"id": "s05", "axe": "pendant", "libelle": "Équilibre entre théorie et pratique"},
        {"id": "s06", "axe": "pendant", "libelle": "Qualité des supports remis"},
        {"id": "s07", "axe": "apres", "libelle": "Atteinte de vos attentes personnelles"},
        {"id": "s08", "axe": "apres", "libelle": "Applicabilité immédiate dans votre pratique"},
    ],
    "recommandation": {"id": "s09",
                       "libelle": "Recommanderiez-vous cette formation à un confrère ?"},
    "adaptation": {"id": "s10",
                   "libelle": "Aviez-vous un besoin particulier d'adaptation ?",
                   "propositions": ["Non concerné", "Oui, pris en compte",
                                    "Oui, partiellement pris en compte",
                                    "Oui, non pris en compte"]},
    "ouvertes": [
        {"id": "s11", "libelle": "Ce qui vous a le plus apporté"},
        {"id": "s12", "libelle": "Ce que nous devrions améliorer"},
    ],
}
def _bibliotheque():
    try:
        import modeles
        return modeles
    except Exception:
        return None
def _reference(code_formation, cle):
    try:
        from sessions import FORMATIONS
    except Exception:
        return None
    return (FORMATIONS.get(code_formation) or {}).get(cle)
def pour_formation(code_formation):
    bib = _bibliotheque()
    ref = _reference(code_formation, "modele_evaluation")
    if ref and bib:
        f = bib.modele("evaluation", ref)
        if f:
            return f
    return EVALUATIONS.get(code_formation)
def satisfaction_pour(code_formation):
    bib = _bibliotheque()
    ref = _reference(code_formation, "modele_satisfaction")
    if ref and bib:
        f = bib.modele("satisfaction", ref)
        if f:
            return f
    return SATISFACTION
FROID = {
    "titre": "Trois mois après : et dans votre pratique ?",
    "axes": {"mise": "Mise en pratique", "effet": "Effets constatés"},
    "notes": [
        {"id": "f01", "axe": "mise", "libelle": "J'ai mis en application ce que j'ai appris"},
        {"id": "f02", "axe": "mise", "libelle": "Les acquis étaient transposables à mes cas cliniques"},
        {"id": "f03", "axe": "mise", "libelle": "J'ai disposé du matériel et du temps nécessaires"},
        {"id": "f04", "axe": "effet", "libelle": "Ma pratique a évolué depuis la formation"},
        {"id": "f05", "axe": "effet", "libelle": "Je me sens plus à l'aise sur ces situations cliniques"},
        {"id": "f06", "axe": "effet", "libelle": "Avec le recul, la formation répondait à mes attentes"},
    ],
    "recommandation": {"id": "f09",
                       "libelle": "Avec trois mois de recul, recommanderiez-vous cette formation ?"},
    "adaptation": None,
    "ouvertes": [
        {"id": "f11", "libelle": "Un cas concret où cette formation vous a servi"},
        {"id": "f12", "libelle": "Ce qui vous a manqué pour aller plus loin"},
    ],
}
def froid_pour(code_formation):
    bib = _bibliotheque()
    ref = _reference(code_formation, "modele_froid")
    if ref and bib:
        f = bib.modele("froid", ref)
        if f:
            return f
    return FROID
import os as _os
import json as _json
from datetime import datetime as _dt
_DOSSIER_FIGES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                               "questionnaires_figes")
def _chemin_fige(code_session):
    if not _os.path.isdir(_DOSSIER_FIGES):
        _os.makedirs(_DOSSIER_FIGES, exist_ok=True)
    return _os.path.join(_DOSSIER_FIGES, str(code_session) + ".json")
def fige(code_session):
    """Modeles figes pour cette session, ou None s'il n'y en a pas.

    Absence = session preparee avant la mise en place du dispositif. L'appelant
    doit alors retomber sur la bibliotheque, sans reconstituer d'instantane :
    un document fabrique apres coup n'est pas une preuve."""
    try:
        with open(_chemin_fige(code_session), encoding="utf-8") as f:
            d = _json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None
def figer(code_session, code_formation, ordre=None):
    """Enregistre les modeles COMPLETS servant a cette session, cle de
    correction comprise, au moment de la preparation.

    Sans cet instantane, corriger une session passee revient a la corriger avec
    le modele d'aujourd'hui : changer une bonne reponse modifierait
    retroactivement le score et le corrige d'une session deja tenue.

    Volontairement LOCAL : publier la cle de correction dans Supabase
    l'exposerait a qui sait interroger l'API.

    N'ECRASE JAMAIS. Si un instantane existe et que les modeles ont change
    depuis, l'ancien est archive dans "versions". Si rien n'a change, le
    fichier n'est pas reecrit."""
    courant = {
        "session": code_session,
        "formation": code_formation,
        "fige_le": _dt.now().strftime("%d/%m/%Y %H:%M"),
        "ordre": list(ordre or []),
        "evaluation": pour_formation(code_formation),
        "satisfaction": satisfaction_pour(code_formation),
        "froid": froid_pour(code_formation),
    }
    def _comparable(d):
        return _json.dumps({c: d.get(c) for c in ("evaluation", "satisfaction", "froid")},
                           ensure_ascii=False, sort_keys=True)
    ancien = fige(code_session)
    if ancien and _comparable(ancien) == _comparable(courant):
        return ancien
    versions = []
    if ancien:
        versions = ancien.pop("versions", []) or []
        versions.append(ancien)
    courant["versions"] = versions
    import fichiers
    fichiers.ecrire(_chemin_fige(code_session), courant)
    return courant
def seuil_defaut():
    try:
        import parametres
        return int(parametres.valeur("seuil_reussite", 70))
    except Exception:
        return SEUIL_DEFAUT
def evaluation(code_formation):
    return pour_formation(code_formation)
def modele_session(code_session, code_formation, quoi="evaluation"):
    """Modele qui a REELLEMENT servi a cette session.

    Rend l'instantane pris a la preparation quand il existe, sinon le modele
    actuel de la bibliotheque. Sans cela, corriger une session passee
    reviendrait a la corriger avec le modele d'aujourd'hui : modifier une
    bonne reponse changerait retroactivement un score deja communique.

    Le repli sur la bibliotheque concerne les sessions preparees avant la mise
    en place du figeage. On ne reconstitue rien : un document fabrique apres
    coup ne serait pas une preuve."""
    d = fige(code_session)
    if d and d.get(quoi):
        return d[quoi]
    if quoi == "satisfaction":
        return satisfaction_pour(code_formation)
    if quoi == "froid":
        return froid_pour(code_formation)
    return pour_formation(code_formation)
def corriger_avec(modele, reponses):
    """Corrige des reponses contre un modele explicite — celui de l'instantane
    de session, en general. Voir modele_session()."""
    q = modele
    if not q:
        return None
    total = 0
    obtenu = 0
    par_objectif = {}
    detail = []
    for question in q["questions"]:
        poids = question.get("poids", 1)
        obj = question.get("objectif", "?")
        if obj not in par_objectif:
            par_objectif[obj] = {"total": 0, "obtenu": 0}
        total += poids
        par_objectif[obj]["total"] += poids
        donnee = reponses.get(question["id"])
        juste = (donnee is not None and int(donnee) == question["reponse"])
        if juste:
            obtenu += poids
            par_objectif[obj]["obtenu"] += poids
        detail.append({"id": question["id"], "objectif": obj,
                       "donnee": donnee, "attendu": question["reponse"], "juste": juste})
    scores = {}
    for obj, v in par_objectif.items():
        scores[obj] = round(100.0 * v["obtenu"] / v["total"]) if v["total"] else 0
    return {"score": round(100.0 * obtenu / total) if total else 0,
            "obtenu": obtenu, "total": total,
            "par_objectif": scores, "detail": detail}
def corriger(code_formation, reponses):
    """Corrige contre le modele ACTUEL de la bibliotheque.
    Pour une session donnee, preferer corriger_avec(modele_session(...), ...)."""
    return corriger_avec(pour_formation(code_formation), reponses)
