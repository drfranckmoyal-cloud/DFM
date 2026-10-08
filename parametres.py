import json
import os
_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parametres.json")
SECTIONS = [
    ("general", "Général", "ti-world",
     "Langue, formats et fuseau horaire."),
    ("affichage", "Affichage", "ti-layout",
     "Comment les écrans se présentent à l'ouverture."),
    ("gestion", "Règles de gestion", "ti-adjustments",
     "Les valeurs par défaut appliquées à vos formations et sessions."),
    ("automatismes", "Automatismes", "ti-robot",
     "Ce que DFM fait seul, et à quel moment."),
    ("conservation", "Conservation des données", "ti-archive",
     "Durées que vous déclarez, à titre documentaire. DFM ne supprime rien de lui-même : "
     "aucune purge automatique n'existe, et il n'en est pas prévu. Le règlement européen "
     "attend une durée définie et justifiable — c'est ce que vous inscrivez ici."),
    ("technique", "Connexions techniques", "ti-plug",
     "Identifiants des services connectés. À ne modifier qu'en connaissance de cause."),
]
SCHEMA = [
    {"cle": "delai_reglement", "section": "gestion", "type": "nombre", "defaut": 20,
     "libelle": "Délai de règlement", "unite": "jours avant la formation",
     "aide": "Mentionné dans le mail de confirmation. Au-delà, le règlement est considéré en retard."},
    {"cle": "heures_par_jour", "section": "gestion", "type": "nombre", "defaut": 7,
     "libelle": "Durée d'une journée de formation", "unite": "heures",
     "aide": "Écrite entre parenthèses après chaque journée sur la convention et "
             "l'attestation, et multipliée par le nombre de journées pour donner la "
             "durée totale. Les horaires d'arrivée et de départ n'entrent pas dans ce "
             "calcul : une journée vaut cette durée, quels que soient ses horaires."},
    {"cle": "seuil_reussite", "section": "gestion", "type": "nombre", "defaut": 70,
     "libelle": "Seuil de réussite des évaluations", "unite": "%",
     "aide": "En dessous, les objectifs sont considérés partiellement atteints. Chaque questionnaire peut avoir le sien."},
    {"cle": "capacite_defaut", "section": "gestion", "type": "nombre", "defaut": 14,
     "libelle": "Places par défaut", "unite": "participants",
     "aide": "Proposé à la création d'une session, modifiable au cas par cas."},
    {"cle": "delai_froid", "section": "gestion", "type": "nombre", "defaut": 90,
     "libelle": "Évaluation à froid", "unite": "jours après la formation",
     "aide": "Quand l'évaluation à froid est proposée par défaut."},
    {"cle": "relance_cloture", "section": "gestion", "type": "nombre", "defaut": 10,
     "libelle": "Relance de clôture", "unite": "semaines après la formation",
     "aide": "Délai après lequel DFM vous rappelle de déclarer une session terminée."},
    {"cle": "releve_heures", "section": "automatismes", "type": "nombre", "defaut": 6,
     "libelle": "Relève des questionnaires", "unite": "heures",
     "aide": "Fréquence de récupération des réponses. Elle a lieu aussi à l'ouverture des écrans concernés."},
    {"cle": "heure_init", "section": "automatismes", "type": "heure", "defaut": "08:30",
     "libelle": "Évaluation d'entrée",
     "aide": "Heure de déclenchement proposée, le premier jour de formation."},
    {"cle": "heure_fin", "section": "automatismes", "type": "heure", "defaut": "16:00",
     "libelle": "Évaluation de sortie",
     "aide": "Heure de déclenchement proposée, le dernier jour de formation."},
    {"cle": "heure_satisfaction", "section": "automatismes", "type": "heure", "defaut": "16:15",
     "libelle": "Questionnaire de satisfaction",
     "aide": "Juste après l'évaluation de sortie, pendant que les participants sont encore présents."},
    {"cle": "envois_auto_autorises", "section": "automatismes", "type": "booleen", "defaut": True,
     "libelle": "Autoriser les envois sans validation",
     "aide": "Si vous décochez, DFM demandera toujours confirmation avant d'envoyer un mail programmé."},
    {"cle": "periode_defaut", "section": "affichage", "type": "choix", "defaut": "tout",
     "libelle": "Période affichée à l'ouverture",
     "options": [("tout", "Tout l'historique"), ("avenir", "Sessions à venir"),
                 ("annee", "Année en cours"), ("m3", "3 derniers mois"),
                 ("m6", "6 derniers mois"), ("m12", "12 derniers mois")],
     "aide": "S'applique aux écrans Règlements, Conventions et Questionnaires. "
             "Attention : les périodes « N derniers mois » s'arrêtent à aujourd'hui "
             "et masquent donc les sessions à venir. « Tout l'historique » ne cache rien."},
    {"cle": "lignes_tableau", "section": "affichage", "type": "nombre", "defaut": 50,
     "libelle": "Lignes par tableau", "unite": "lignes",
     "aide": "Au-delà, les écrans deviennent lourds à charger."},
    {"cle": "mode_sombre", "section": "affichage", "type": "booleen", "defaut": False,
     "libelle": "Mode sombre par défaut",
     "aide": "Votre choix dans la barre de gauche reste prioritaire sur cet appareil."},
    {"cle": "fuseau", "section": "general", "type": "choix", "defaut": "Europe/Paris",
     "libelle": "Fuseau horaire",
     "options": [("Europe/Paris", "Paris, Bruxelles, Genève"), ("Europe/London", "Londres"),
                 ("America/Montreal", "Montréal"), ("Indian/Reunion", "La Réunion"),
                 ("America/Guadeloupe", "Antilles")],
     "aide": "Détermine l'heure des envois programmés. Important si DFM tourne un jour sur un serveur distant."},
    {"cle": "format_date", "section": "general", "type": "choix", "defaut": "jj/mm/aaaa",
     "libelle": "Format des dates",
     "options": [("jj/mm/aaaa", "31/12/2026"), ("aaaa-mm-jj", "2026-12-31")],
     "aide": "Affichage dans les écrans et les documents."},
    {"cle": "devise", "section": "general", "type": "choix", "defaut": "EUR",
     "libelle": "Devise",
     "options": [("EUR", "Euro (€)"), ("CHF", "Franc suisse"), ("CAD", "Dollar canadien")],
     "aide": "Symbole affiché sur les montants et les factures."},
    {"cle": "conservation_journal", "section": "conservation", "type": "nombre", "defaut": 36,
     "libelle": "Journal d'activités", "unite": "mois (durée déclarée)",
     "aide": "Durée que vous vous engagez à conserver. Rien n'est supprimé automatiquement : "
             "les évènements restent tant que vous ne les retirez pas vous-même. "
             "Trois ans couvrent un cycle d'audit complet."},
    {"cle": "conservation_reponses", "section": "conservation", "type": "nombre", "defaut": 36,
     "libelle": "Réponses aux questionnaires", "unite": "mois (durée déclarée)",
     "aide": "Elles contiennent le nom et l'adresse des participants : ce sont des données "
             "personnelles, et cette durée est celle que vous déclarez les concernant. "
             "DFM ne les efface pas de lui-même."},
    {"cle": "conservation_sessions", "section": "conservation", "type": "nombre", "defaut": 60,
     "libelle": "Sessions archivées", "unite": "mois (durée déclarée)",
     "aide": "Cinq ans correspondent à la durée attendue pour les pièces de formation. "
             "Aucune session n'est supprimée automatiquement : vos archives restent "
             "disponibles au-delà si vous ne faites rien."},
    {"cle": "sheet_suivi", "section": "technique", "type": "drive", "defaut": "",
     "libelle": "Identifiant du Sheet de suivi",
     "aide": "Collez l'adresse complète (https://…/d/XXXX/edit) ou l'identifiant seul : DFM en extrait l'identifiant. La longue chaîne dans l'adresse du tableur, entre /d/ et /edit."},
    {"cle": "url_signature", "section": "technique", "type": "texte", "defaut": "",
     "libelle": "Adresse du site de signature",
     "aide": "Le site Netlify qui héberge les pages de signature et de questionnaires."},
    {"cle": "logo_id", "section": "technique", "type": "drive", "defaut": "",
     "libelle": "Identifiant du logo dans Drive",
     "aide": "Collez l'adresse complète (https://…/d/XXXX/edit) ou l'identifiant seul : DFM en extrait l'identifiant. Utilisé dans tous les mails et documents."},
    {"cle": "dossier_conventions", "section": "technique", "type": "drive", "defaut": "",
     "libelle": "Dossier des conventions", "aide": "Collez l'adresse complète (https://…/d/XXXX/edit) ou l'identifiant seul : DFM en extrait l'identifiant. Identifiant du dossier Drive."},
    {"cle": "dossier_signees", "section": "technique", "type": "drive", "defaut": "",
     "libelle": "Dossier des conventions signées", "aide": "Collez l'adresse complète (https://…/d/XXXX/edit) ou l'identifiant seul : DFM en extrait l'identifiant. Identifiant du dossier Drive."},
    {"cle": "rib_id", "section": "technique", "type": "drive", "defaut": "",
     "libelle": "RIB en pièce jointe", "aide": "Collez l'adresse complète (https://…/d/XXXX/edit) ou l'identifiant seul : DFM en extrait l'identifiant. Identifiant du PDF joint aux mails de règlement."},
]
def _index():
    return {p["cle"]: p for p in SCHEMA}
def charger():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}
def enregistrer(tout):
    import fichiers
    fichiers.ecrire(_FICHIER, tout)
def valeur(cle, defaut=None):
    stocke = charger()
    if cle in stocke and stocke[cle] not in ("", None):
        return stocke[cle]
    try:
        from sessions import COMMUN
        if cle in COMMUN and COMMUN[cle] not in ("", None):
            return COMMUN[cle]
    except Exception:
        pass
    fiche = _index().get(cle)
    if fiche is not None:
        return fiche["defaut"]
    return defaut
def toutes():
    stocke = charger()
    sortie = {}
    for p in SCHEMA:
        cle = p["cle"]
        sortie[cle] = {"valeur": valeur(cle), "defaut": p["defaut"],
                       "modifie": (cle in stocke and stocke[cle] != p["defaut"])}
    return sortie
def normaliser(cle, brut):
    fiche = _index().get(cle)
    if not fiche:
        return None
    t = fiche["type"]
    if t == "booleen":
        return bool(brut) if not isinstance(brut, str) else brut.lower() in ("1", "true", "oui", "on")
    if t == "nombre":
        try:
            return int(str(brut).strip() or fiche["defaut"])
        except Exception:
            return fiche["defaut"]
    if t == "choix":
        valides = [o[0] for o in (fiche.get("options") or [])]
        v = str(brut).strip()
        return v if v in valides else fiche["defaut"]
    if t == "heure":
        v = str(brut).strip()
        if len(v) == 5 and v[2] == ":":
            return v
        return fiche["defaut"]
    return str(brut).strip()
def sauver(donnees):
    """Rend (modifies, refuses). Un champ 'drive' recoit un lien complet ou un
    identifiant nu ; une valeur inexploitable est REFUSEE avec un message,
    jamais enregistree telle quelle — elle echouerait silencieusement des
    semaines plus tard, a la premiere generation de document."""
    stocke = charger()
    modifies, refuses = [], []
    for cle, brut in (donnees or {}).items():
        fiche = _index().get(cle)
        if not fiche:
            continue
        if fiche["type"] == "drive":
            texte = str(brut or "").strip()
            if not texte:
                v = ""
            else:
                from sessions import extraire_id
                v = extraire_id(texte)
                if not v:
                    refuses.append({"cle": cle, "libelle": fiche["libelle"],
                                    "message": "« " + texte[:60] + " » n'est ni un lien Drive "
                                    "reconnaissable, ni un identifiant. Valeur non enregistrée."})
                    continue
        else:
            v = normaliser(cle, brut)
            if v is None:
                continue
        if stocke.get(cle) != v:
            modifies.append(cle)
        stocke[cle] = v
    enregistrer(stocke)
    return modifies, refuses
def reinitialiser(cle=None):
    if cle is None:
        enregistrer({})
        return len(SCHEMA)
    stocke = charger()
    if cle in stocke:
        del stocke[cle]
        enregistrer(stocke)
        return 1
    return 0
