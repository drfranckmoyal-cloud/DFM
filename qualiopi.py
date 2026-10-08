"""Le referentiel national qualite, lu pour CET organisme.

SOURCE. Guide de lecture V9 du 8 janvier 2024, seule version en vigueur au
05/08/2026. Les enonces, niveaux attendus et caracterisations de non-conformite
sont repris du guide ; le reste — applicabilite, correspondance avec DFM — est
une lecture, pas une citation, et l'ecran le dit.

CE MODULE NE FLATTE PAS. Un assistant qui annoncerait couvert ce qui ne l'est
pas serait pire qu'inutile le jour de l'audit : il ferait manquer la seule
occasion de corriger. Chaque indicateur porte donc un etat de socle etabli en
lisant le code de DFM, pas ses intentions.

TROIS ETATS, ET UN QUATRIEME.
  couvert  DFM produit la piece, elle suffit.
  partiel  DFM produit une partie ; ce qui manque est nomme.
  absent   DFM n'y repond pas. La preuve est ailleurs, et l'ecran dit ou.
  na       Ne s'applique pas a cette situation, avec la raison.

LA CONSIGNATION FAIT MONTER D'UN CRAN. Quatre indicateurs — les trois veilles
et le developpement des competences — ne demandent aucun developpement : ils
demandent qu'une pratique existante soit datee et exploitee. Consigner une
lecture de congres dans DFM la transforme en preuve. C'est le meilleur rapport
entre l'effort et le resultat de tout ce referentiel.
"""
import json
import os
from datetime import date, datetime

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_FICHIER = os.path.join(_DOSSIER, "qualiopi_consignations.json")

VERSION = "V9 du 8 janvier 2024"
VERIFIE_LE = "05/08/2026"

CRITERES = [
    (1, "Les conditions d'information du public sur les prestations proposées, "
        "les délais pour y accéder et les résultats obtenus", "ti-speakerphone"),
    (2, "L'identification précise des objectifs des prestations proposées et "
        "l'adaptation de ces prestations aux publics bénéficiaires lors de la conception",
        "ti-target"),
    (3, "L'adaptation aux publics bénéficiaires des prestations et des modalités "
        "d'accueil, d'accompagnement, de suivi et d'évaluation", "ti-users"),
    (4, "L'adéquation des moyens pédagogiques, techniques et d'encadrement aux "
        "prestations mises en œuvre", "ti-tools"),
    (5, "La qualification et le développement des connaissances et compétences "
        "des personnels chargés de mettre en œuvre les prestations", "ti-certificate-2"),
    (6, "L'inscription et l'investissement du prestataire dans son environnement "
        "professionnel", "ti-world"),
    (7, "Le recueil et la prise en compte des appréciations et des réclamations "
        "formulées par les parties prenantes", "ti-message-report"),
]

# Indicateurs pouvant donner lieu a une non-conformite MINEURE. Tous les autres
# ne connaissent que la majeure : le non-respect meme partiel suffit.
GRADUES = {1, 2, 3, 8, 9, 12, 13, 17, 18, 19, 23, 24, 25, 28, 30}

# Indicateurs a modalites adaptees pour les nouveaux entrants : formalisation
# verifiee a l'audit initial, mise en oeuvre effective a la surveillance.
ALLEGES = {2, 3, 11, 13, 14, 19, 22, 24, 25, 26, 32}


def _i(n, critere, enonce, attendu, nc, socle, dfm=None, charge=None,
       na="", registre="", note=""):
    return {"n": n, "critere": critere, "enonce": enonce, "attendu": attendu,
            "nc": nc, "socle": socle, "dfm": dfm or [], "charge": charge or [],
            "na": na, "registre": registre, "note": note,
            "gravite": "graduée" if n in GRADUES else "majeure",
            "allege": n in ALLEGES}


_NA_CERTIF = ("Formations non certifiantes : cet indicateur ne concerne que les "
              "prestations conduisant à une certification professionnelle inscrite "
              "au RNCP ou au RS.")
_NA_CFA = ("Indicateur spécifique aux CFA et à l'alternance. Aucune action "
           "d'apprentissage n'est dispensée.")
_NA_ST = ("Aucune sous-traitance ni portage salarial : les formations sont "
          "conçues et animées en propre.")
_NA_AFEST = ("Les formations se déroulent intégralement en centre. Aucune période "
             "de formation en situation de travail n'est prévue.")


INDICATEURS = [
    # ---------------------------------------------------------------- CRITERE 1
    _i(1, 1,
       "Le prestataire diffuse une information accessible au public, détaillée et "
       "vérifiable sur les prestations proposées : prérequis, objectifs, durée, "
       "modalités et délais d'accès, tarifs, contacts, méthodes mobilisées et "
       "modalités d'évaluation, accessibilité aux personnes handicapées.",
       "Donner une information accessible, exhaustive sur la prestation, c'est-à-dire "
       "sur son contenu et sur l'intégralité des items mentionnés. Cette information "
       "doit être à jour.",
       "Mineure : information partiellement accessible, ou absence ponctuelle et non "
       "répétitive de certains items. Majeure si l'attendu n'est pas du tout respecté.",
       "absent",
       dfm=[{"quoi": "Objectifs, durée, tarif, public et lieu de chaque formation",
             "lien": "/formations", "etat": "ok"},
            {"quoi": "Programme détaillé, envoyé avec la convention",
             "lien": "/formations", "etat": "ok"}],
       charge=["Publier l'information — DFM détient la matière mais ne diffuse rien.",
               "Trois items manquent dans DFM : les PRÉREQUIS, les DÉLAIS D'ACCÈS "
               "et la MENTION D'ACCESSIBILITÉ aux personnes handicapées.",
               "Vérifier que l'information est à jour et antérieure à la "
               "contractualisation."],
       registre="diffusion",
       note="Le guide admet tout moyen dès lors que l'information précède la "
            "contractualisation : site internet, proposition commerciale, plaquette. "
            "Sans site public, la proposition commerciale adressée au client doit "
            "porter l'intégralité des items."),

    _i(2, 1,
       "Le prestataire diffuse des indicateurs de résultats adaptés à la nature des "
       "prestations mises en œuvre et des publics accueillis.",
       "Donner une information chiffrée permettant de suivre les résultats de la "
       "prestation au regard des objectifs.",
       "Mineure : information insuffisamment détaillée. Majeure si absente.",
       "partiel",
       dfm=[{"quoi": "Bilan : taux de satisfaction, progression moyenne, taux "
                     "d'atteinte des objectifs, nombre de participants",
             "lien": "/questionnaires/bilan", "etat": "ok"}],
       charge=["Diffuser ces chiffres publiquement — le bilan les calcule, rien ne "
               "les publie."],
       registre="diffusion"),

    _i(3, 1,
       "Lorsque le prestataire met en œuvre des prestations conduisant à une "
       "certification professionnelle, il informe sur les taux d'obtention, les blocs "
       "de compétences, les équivalences, passerelles, suites de parcours et débouchés.",
       "", "", "na", na=_NA_CERTIF),

    # ---------------------------------------------------------------- CRITERE 2
    _i(4, 2,
       "Le prestataire analyse le besoin du bénéficiaire en lien avec l'entreprise "
       "et/ou le financeur concerné(s).",
       "Démontrer comment le besoin du bénéficiaire est analysé en fonction de la "
       "finalité de la prestation.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "absent",
       dfm=[{"quoi": "Le formulaire d'inscription recueille la demande et la fonction "
                     "de l'apprenant", "lien": "/contacts", "etat": "partiel"}],
       charge=["Formaliser l'analyse : recueillir une demande n'est pas l'analyser. "
               "Une grille, un compte rendu d'entretien, un diagnostic préalable.",
               "Pour les sessions clients : ce que la structure attend pour ses "
               "praticiens, et pourquoi cette formation y répond."],
       registre="analyse_besoin"),

    _i(5, 2,
       "Le prestataire définit les objectifs opérationnels et évaluables de la prestation.",
       "Démontrer que les objectifs spécifiques à la prestation ont été définis et "
       "peuvent faire l'objet d'une évaluation.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "couvert",
       dfm=[{"quoi": "Objectifs déclarés sur chaque fiche formation",
             "lien": "/formations", "etat": "ok"},
            {"quoi": "Les mêmes objectifs, découpés en A/B/C et mesurés question par "
                     "question dans les questionnaires",
             "lien": "/templates", "etat": "ok"},
            {"quoi": "Résultat par objectif pour chaque participant",
             "lien": "/questionnaires", "etat": "ok"}]),

    _i(6, 2,
       "Le prestataire établit les contenus et les modalités de mise en œuvre de la "
       "prestation, adaptés aux objectifs définis et aux publics bénéficiaires.",
       "Démontrer que les contenus et modalités de mise en œuvre des prestations sont "
       "adaptés aux objectifs définis en fonction des bénéficiaires.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "partiel",
       dfm=[{"quoi": "Programme détaillé rattaché à chaque formation",
             "lien": "/formations", "etat": "ok"},
            {"quoi": "Durée, horaires, public visé, effectif maximum",
             "lien": "/formations", "etat": "ok"}],
       charge=["Écrire les MODALITÉS PÉDAGOGIQUES : déroulé, séquences, alternance "
               "théorie/pratique, méthodes mobilisées. Le programme dit le quoi, "
               "l'auditeur demande aussi le comment.",
               "Dire comment les contenus sont adaptés aux personnes en situation "
               "de handicap."]),

    _i(7, 2,
       "Lorsque le prestataire met en œuvre des prestations conduisant à une "
       "certification professionnelle, il s'assure de l'adéquation des contenus aux "
       "exigences de la certification visée.",
       "", "", "na", na=_NA_CERTIF),

    _i(8, 2,
       "Le prestataire détermine les procédures de positionnement et d'évaluation des "
       "acquis à l'entrée de la prestation.",
       "Démontrer l'existence de procédures de positionnement et d'évaluation des "
       "acquis à l'entrée de la prestation, adaptée aux publics et modalités de formations.",
       "Mineure : dispositif existant mais incomplet. Majeure si absent.",
       "couvert",
       dfm=[{"quoi": "Évaluation d'entrée envoyée avant chaque session, score par objectif",
             "lien": "/questionnaires", "etat": "ok"},
            {"quoi": "Modèle figé à la préparation : le questionnaire restitué est "
                     "celui qui a réellement servi", "lien": "/templates", "etat": "ok"}]),

    # ---------------------------------------------------------------- CRITERE 3
    _i(9, 3,
       "Le prestataire informe les publics bénéficiaires des conditions de déroulement "
       "de la prestation.",
       "Les modalités d'accueil et les conditions de déroulement de la prestation sont "
       "formalisées et diffusées.",
       "Mineure : information incomplète. Majeure si absente.",
       "couvert",
       dfm=[{"quoi": "Convocation J-20 : adresse, heure d'accueil, horaires, déjeuner",
             "lien": "/templates", "etat": "ok"},
            {"quoi": "Règlement intérieur, joint automatiquement à la convocation",
             "lien": "/profil", "etat": "ok"},
            {"quoi": "Modalités d'accès, dont l'accès PMR, jointes également",
             "lien": "/formations", "etat": "ok"},
            {"quoi": "Trace d'envoi par personne, datée",
             "lien": "/journal", "etat": "ok"}]),

    _i(10, 3,
       "Le prestataire met en œuvre et adapte la prestation, l'accompagnement et le "
       "suivi aux publics bénéficiaires.",
       "La prestation est adaptée aux situations et profils des bénéficiaires, lorsque "
       "l'analyse du besoin en établit la nécessité : contenus, accompagnement, suivi.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "partiel",
       dfm=[{"quoi": "Feuille d'émargement générée et récupérée signée",
             "lien": "/sessions", "etat": "ok"},
            {"quoi": "Besoins d'adaptation déclarés à l'inscription, affichés sur la session",
             "lien": "/sessions", "etat": "ok"}],
       charge=["Consigner ce qui a été ADAPTÉ, et pour qui. DFM montre qui a déclaré "
               "un besoin ; rien ne dit ce que vous en avez fait.",
               "Deux participants ont déclaré un besoin d'accès PMR sur Usures : c'est "
               "exactement le cas que l'auditeur suivra."],
       registre="adaptation"),

    _i(11, 3,
       "Le prestataire évalue l'atteinte par les publics bénéficiaires des objectifs "
       "de la prestation.",
       "Démontrer qu'un processus d'évaluation existe, est formalisé et mis en œuvre. "
       "Il permet d'apprécier l'atteinte des objectifs.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "couvert",
       dfm=[{"quoi": "Évaluation d'entrée et de sortie, résultat par objectif, seuil déclaré",
             "lien": "/questionnaires", "etat": "ok"},
            {"quoi": "Récapitulatif pédagogique remis à l'apprenant",
             "lien": "/sessions", "etat": "ok"},
            {"quoi": "Dossier de preuves par apprenant, imprimable",
             "lien": "/sessions", "etat": "ok"},
            {"quoi": "Évaluation à froid à trois mois", "lien": "/questionnaires", "etat": "ok"}]),

    _i(12, 3,
       "Le prestataire décrit et met en œuvre les mesures pour favoriser l'engagement "
       "des bénéficiaires et prévenir les ruptures de parcours.",
       "Démontrer que des mesures formalisées existent et sont mises en œuvre.",
       "Mineure : mise en œuvre partielle des mesures définies. Majeure si absentes.",
       "partiel",
       dfm=[{"quoi": "Relances automatiques : signature, règlement",
             "lien": "/journal", "etat": "ok"},
            {"quoi": "File d'attente et promotion, annulations tracées",
             "lien": "/sessions", "etat": "ok"}],
       charge=["DÉCRIRE les mesures : le guide demande d'abord une description "
               "formalisée. DFM les exécute sans qu'elles soient écrites nulle part.",
               "Ne s'applique qu'aux formations de plus de 2 jours."],
       registre="engagement",
       note="Applicable aux seules formations d'une durée supérieure à 2 jours. "
            "Usures et Masterclass, sur 2 jours, y échappent."),

    _i(13, 3, "Pour les formations en alternance, le prestataire anticipe avec "
       "l'apprenant les missions confiées et assure la coordination avec l'entreprise.",
       "", "", "na", na=_NA_CFA),
    _i(14, 3, "Le prestataire met en œuvre un accompagnement socio-professionnel, "
       "éducatif et relatif à l'exercice de la citoyenneté.", "", "", "na", na=_NA_CFA),
    _i(15, 3, "Le prestataire informe les apprentis de leurs droits et devoirs ainsi "
       "que des règles de santé et sécurité au travail.", "", "", "na", na=_NA_CFA),
    _i(16, 3, "Lorsque le prestataire met en œuvre des formations certifiantes, il "
       "s'assure du respect des exigences de l'autorité de certification.",
       "", "", "na", na=_NA_CERTIF),

    # ---------------------------------------------------------------- CRITERE 4
    _i(17, 4,
       "Le prestataire met à disposition ou s'assure de la mise à disposition des "
       "moyens humains et techniques adaptés et d'un environnement approprié "
       "(conditions, locaux, équipements, plateaux techniques…).",
       "Démontrer que les locaux, les équipements, les moyens humains sont en "
       "adéquation avec les objectifs de la ou des prestation(s).",
       "Mineure : défaut ponctuel et non répétitif dans les moyens. Majeure si "
       "l'attendu n'est pas respecté.",
       "absent",
       dfm=[{"quoi": "Adresse du lieu de formation, effectif maximum par session",
             "lien": "/formations", "etat": "partiel"}],
       charge=["Bail ou contrat de location de la salle.",
               "Registre public d'accessibilité du lieu.",
               "Inventaire du matériel pédagogique et technique.",
               "Document unique d'évaluation des risques professionnels."],
       registre="moyens"),

    _i(18, 4,
       "Le prestataire mobilise et coordonne les différents intervenants internes "
       "et/ou externes (pédagogiques, administratifs, logistiques, commerciaux…).",
       "Le prestataire identifie, selon les fonctions nécessaires aux prestations, "
       "les intervenants dont il assure la coordination.",
       "Mineure : défaut ponctuel de coordination. Majeure si l'attendu n'est pas respecté.",
       "partiel",
       dfm=[{"quoi": "Registre des formateurs, un par organisme",
             "lien": "/profil", "etat": "ok"},
            {"quoi": "Formateur désigné pour chaque formation de la bibliothèque",
             "lien": "/formations", "etat": "ok"}],
       charge=["Écrire quelles FONCTIONS sont assurées et par qui : pédagogique, "
               "administrative, logistique, commerciale."],
       note="Le guide précise : « Un prestataire indépendant peut assurer seul les "
            "différentes fonctions. » Il faut le dire, pas s'en excuser."),

    _i(19, 4,
       "Le prestataire met à disposition du bénéficiaire des ressources pédagogiques "
       "et permet à celui-ci de se les approprier.",
       "Démontrer que les ressources pédagogiques sont cohérentes avec les objectifs "
       "des prestations, sont disponibles et que des dispositions sont mises en place "
       "afin de permettre aux bénéficiaires de se les approprier.",
       "Mineure : défaut ponctuel et non répétitif dans les ressources et moyens mis "
       "à disposition. Majeure si l'attendu n'est pas respecté.",
       "partiel",
       dfm=[{"quoi": "Articles et documents joints à la convocation, avec trace d'envoi",
             "lien": "/formations", "etat": "ok"},
            {"quoi": "Programme remis avec la convention", "lien": "/formations", "etat": "ok"}],
       charge=["Décrire ce qui permet l'APPROPRIATION : envoyer n'est pas s'approprier. "
               "Lecture préalable demandée, temps prévu en séance, échange après coup.",
               "Lister les ressources remises pendant la formation, pas seulement avant."]),

    _i(20, 4, "Le prestataire dispose d'un personnel dédié à l'appui à la mobilité, "
       "d'un référent handicap et d'un conseil de perfectionnement.",
       "", "", "na", na=_NA_CFA + " Le référent handicap reste exigé au titre de "
       "l'indicateur 26, où il est traité."),

    # ---------------------------------------------------------------- CRITERE 5
    _i(21, 5,
       "Le prestataire détermine, mobilise et évalue les compétences des différents "
       "intervenants internes et/ou externes, adaptées aux prestations.",
       "Démontrer que les compétences requises pour réaliser les prestations ont été "
       "définies en amont et sont adaptées aux prestations. La maîtrise de ces "
       "compétences par les intervenants est vérifiée par le prestataire.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "partiel",
       dfm=[{"quoi": "Dossier formateur : CV, diplôme, pièces complémentaires",
             "lien": "/profil", "etat": "ok"},
            {"quoi": "Fonction déclarée et formations pour lesquelles il est désigné",
             "lien": "/profil", "etat": "ok"}],
       charge=["Déposer effectivement le CV et le diplôme — les emplacements existent, "
               "ils sont vides dans les deux organismes.",
               "Écrire quelles compétences sont REQUISES pour animer chaque formation. "
               "L'indicateur demande de les définir en amont, pas seulement de "
               "produire un CV."]),

    _i(22, 5,
       "Le prestataire entretient et développe les compétences de ses salariés, "
       "adaptées aux prestations qu'il délivre.",
       "Démontrer la mobilisation des différents leviers de formation et de "
       "professionnalisation pour l'ensemble de son personnel.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "absent",
       charge=["Sans salarié, le guide demande de démontrer VOTRE démarche de "
               "formation continue : congrès, DPC, formations suivies, publications.",
               "Chaque ligne consignée ici est une preuve. C'est le seul effort demandé."],
       registre="formation_continue",
       note="Le guide précise : « Les prestataires indépendants démontrent leur "
            "démarche de formation continue. »"),

    # ---------------------------------------------------------------- CRITERE 6
    _i(23, 6,
       "Le prestataire réalise une veille légale et réglementaire sur le champ de la "
       "formation professionnelle et en exploite les enseignements.",
       "Démontrer la mise en place d'une veille légale et réglementaire, sa prise en "
       "compte par le prestataire et sa communication en interne.",
       "Mineure : absence d'exploitation de la veille mise en place. Majeure si "
       "aucune veille n'existe.",
       "absent",
       charge=["Consigner ce que vous suivez : travail-emploi.gouv.fr, Centre Inffo, "
               "newsletters, webinaires de l'organisme certificateur.",
               "Et surtout ce que vous en avez FAIT : c'est l'exploitation qui est "
               "vérifiée, pas l'abonnement."],
       registre="veille_legale"),

    _i(24, 6,
       "Le prestataire réalise une veille sur les évolutions des compétences, des "
       "métiers et des emplois dans ses secteurs d'intervention et en exploite les "
       "enseignements.",
       "Démontrer la mise en place d'une veille sur les thèmes de l'indicateur et son "
       "impact éventuel sur les prestations.",
       "Mineure : absence d'exploitation de la veille mise en place. Majeure si "
       "aucune veille n'existe.",
       "absent",
       charge=["Congrès et sociétés savantes, revues professionnelles, syndicats, "
               "évolutions de la pratique dentaire.",
               "Noter l'impact sur vos formations quand il y en a un."],
       registre="veille_metiers"),

    _i(25, 6,
       "Le prestataire réalise une veille sur les innovations pédagogiques et "
       "technologiques permettant une évolution de ses prestations et en exploite "
       "les enseignements.",
       "Démontrer la mise en place d'une veille sur les thèmes de l'indicateur et son "
       "impact éventuel sur les prestations.",
       "Mineure : absence d'exploitation de la veille mise en place. Majeure si "
       "aucune veille n'existe.",
       "absent",
       charge=["Outils et méthodes pédagogiques, matériel et techniques nouvelles, "
               "formats de formation.",
               "Le guide cite explicitement la veille pédagogique pour les publics en "
               "situation de handicap."],
       registre="veille_pedago"),

    _i(26, 6,
       "Le prestataire mobilise les expertises, outils et réseaux nécessaires pour "
       "accueillir, accompagner/former ou orienter les publics en situation de handicap.",
       "Démontrer l'identification d'un réseau de partenaires/experts/acteurs du champ "
       "du handicap, mobilisable par les personnels. Dans le cas d'accueil de personnes "
       "en situation de handicap, préciser les modalités de recours à ce réseau et les "
       "mesures spécifiques d'accompagnement ou d'orientation mises en œuvre.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "partiel",
       dfm=[{"quoi": "Référent handicap nommé et joignable, repris sur les documents",
             "lien": "/profil", "etat": "ok"},
            {"quoi": "Besoins d'adaptation collectés à l'inscription et affichés",
             "lien": "/sessions", "etat": "ok"},
            {"quoi": "Question dédiée dans le questionnaire de satisfaction, restituée "
                     "dans le dossier de preuves", "lien": "/questionnaires", "etat": "ok"}],
       charge=["Constituer le RÉSEAU : Agefiph, Cap emploi, MDPH, Ressource Handicap "
               "Formation de votre région. C'est le cœur du niveau attendu, et DFM n'y "
               "répond pas.",
               "Consigner les prises de contact : un réseau se prouve par des échanges, "
               "pas par une liste de noms."],
       registre="reseau_handicap"),

    _i(27, 6, "Lorsque le prestataire fait appel à la sous-traitance ou au portage "
       "salarial, il s'assure du respect de la conformité au présent référentiel.",
       "", "", "na", na=_NA_ST),
    _i(28, 6, "Lorsque les prestations comprennent des périodes de formation en "
       "situation de travail, le prestataire mobilise son réseau de partenaires "
       "socio-économiques.", "", "", "na", na=_NA_AFEST),
    _i(29, 6, "Le prestataire développe des actions qui concourent à l'insertion "
       "professionnelle ou la poursuite d'étude par la voie de l'apprentissage.",
       "", "", "na", na=_NA_CFA),

    # ---------------------------------------------------------------- CRITERE 7
    _i(30, 7,
       "Le prestataire recueille les appréciations des parties prenantes : "
       "bénéficiaires, financeurs, équipes pédagogiques et entreprises concernées.",
       "Démontrer la sollicitation des appréciations à une fréquence pertinente, "
       "incluant des dispositifs de relance et permettant une libre expression.",
       "Mineure : absence de sollicitation des appréciations d'une partie prenante. "
       "Majeure si aucun recueil n'existe.",
       "partiel",
       dfm=[{"quoi": "Questionnaire de satisfaction, avec relance automatique",
             "lien": "/questionnaires", "etat": "ok"},
            {"quoi": "Évaluation à froid à trois mois", "lien": "/questionnaires", "etat": "ok"},
            {"quoi": "Verbatims conservés et restitués individuellement",
             "lien": "/sessions", "etat": "ok"}],
       charge=["Solliciter les STRUCTURES CLIENTES qui achètent des sessions : leur "
               "appréciation n'est recueillie nulle part.",
               "Solliciter les FINANCEURS au moins une fois par an — ou participer à "
               "leurs webinaires, que le guide accepte en remplacement."],
       registre="appreciations",
       note="Le guide est explicite : « Les évaluations des acquis ne sont pas un "
            "élément de preuve probant pour cet indicateur. » Vos scores ne comptent "
            "pas ici, seule la satisfaction compte."),

    _i(31, 7,
       "Le prestataire met en œuvre des modalités de traitement des difficultés "
       "rencontrées par les parties prenantes, des réclamations exprimées par ces "
       "dernières, des aléas survenus en cours de prestation.",
       "Démontrer la mise en place de modalités de traitement des aléas, difficultés "
       "et réclamations.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "couvert",
       dfm=[{"quoi": "Formulaire public de réclamation, lien envoyé avec l'attestation",
             "lien": "/reclamations", "etat": "ok"},
            {"quoi": "Registre numéroté : réception, accusé, traitement, clôture, délai",
             "lien": "/reclamations", "etat": "ok"},
            {"quoi": "Registre imprimable à présenter en contrôle",
             "lien": "/reclamations/registre", "etat": "ok"}],
       charge=["Les ALÉAS en cours de prestation ne sont pas couverts par le registre : "
               "salle indisponible, formateur empêché, matériel défaillant. Consignez-les "
               "quand ils surviennent."],
       registre="aleas"),

    _i(32, 7,
       "Le prestataire met en œuvre des mesures d'amélioration à partir de l'analyse "
       "des appréciations et des réclamations.",
       "Démontrer la mise en place d'une démarche d'amélioration continue.",
       "Majeure : le non-respect même partiel entraîne une non-conformité majeure.",
       "partiel",
       dfm=[{"quoi": "Plan d'amélioration du bilan, adossé aux notions fragiles",
             "lien": "/questionnaires/bilan", "etat": "ok"},
            {"quoi": "Champ « ce que cela change pour la suite » sur chaque réclamation",
             "lien": "/reclamations", "etat": "ok"}],
       charge=["Tenir un registre CONSOLIDÉ des actions d'amélioration : ce qui a été "
               "décidé, quand, à partir de quoi, et ce que ça a donné.",
               "L'indicateur porte sur la mise en œuvre, pas sur l'intention."],
       registre="amelioration"),
]


PAR_NUMERO = {i["n"]: i for i in INDICATEURS}

# Les registres de consignation, avec ce qu'on y note.
REGISTRES = {
    "veille_legale": ("Veille légale et réglementaire",
                      "Ce que vous avez lu ou suivi sur le droit de la formation, et ce que vous en avez tiré."),
    "veille_metiers": ("Veille métiers et compétences",
                       "Congrès, revues, évolutions de la pratique dentaire."),
    "veille_pedago": ("Veille pédagogique et technologique",
                      "Méthodes, outils, formats, matériel."),
    "formation_continue": ("Votre formation continue",
                           "Formations suivies, DPC, congrès, publications."),
    "reseau_handicap": ("Réseau handicap",
                        "Contacts pris et ressources mobilisables : Agefiph, Cap emploi, MDPH."),
    "moyens": ("Moyens matériels et locaux",
               "Bail, accessibilité, matériel, document unique."),
    "analyse_besoin": ("Analyse des besoins",
                       "Entretiens, diagnostics, attentes exprimées par les structures clientes."),
    "adaptation": ("Adaptations mises en œuvre",
                   "Ce qui a été aménagé, pour qui, et le résultat."),
    "engagement": ("Prévention des ruptures de parcours",
                   "Mesures décrites et cas traités."),
    "diffusion": ("Diffusion de l'information",
                  "Où et quand l'information et les résultats ont été publiés."),
    "appreciations": ("Appréciations des clients et financeurs",
                      "Retours des structures clientes et des financeurs."),
    "aleas": ("Aléas survenus", "Incidents en cours de prestation et solutions apportées."),
    "amelioration": ("Actions d'amélioration",
                     "Décidées à partir de quoi, mises en œuvre quand, avec quel effet."),
}


# ------------------------------------------------------------ les consignations

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


# LES QUATRE REGISTRES DU CRITERE 6 SONT COMMUNS AUX DEUX ORGANISMES.
#
# Tout le reste de DFM est cloisonne, et pour de bonnes raisons : une session,
# une convention, une reclamation appartiennent a UN organisme. Ces quatre-la
# non. La veille legale sur le droit de la formation vaut pour DSF comme pour
# Smileclub ; l'evolution de la pratique dentaire aussi ; et la formation
# continue de l'indicateur 22 est celle d'une seule et meme personne. Les
# saisir deux fois serait un double travail pour un contenu identique, et la
# premiere divergence entre les deux copies serait un ecart releve en audit.
#
# LE PARTAGE SE FAIT PAR UN SEUL EMPLACEMENT, pas par recopie. Dupliquer a
# l'ecriture obligerait a re-synchroniser a chaque modification et a chaque
# suppression ; un rangement unique n'a rien a synchroniser.
PARTAGES = {"veille_legale", "veille_metiers", "veille_pedago", "formation_continue"}

# Une cle qui ne peut pas etre un identifiant d'organisme : ceux-ci ne
# commencent jamais par un tiret bas.
COMMUN = "_commun"


def bucket(registre, organisme=None):
    """Sous quelle clé ranger ce registre : l'organisme, ou le fonds commun."""
    return COMMUN if registre in PARTAGES else _organisme(organisme)


def consignations(registre="", organisme=None):
    """Les entrées consignées, la plus récente d'abord.

    Sans registre precise, on rend celles de l'organisme ET celles du fonds
    commun : c'est ce que voit un auditeur venu pour cet organisme.
    """
    tout = _tout()
    if registre:
        lignes = list((tout.get(bucket(registre, organisme)) or {}).get(registre) or [])
    else:
        propre = tout.get(_organisme(organisme)) or {}
        commun = tout.get(COMMUN) or {}
        lignes = [x for v in list(propre.values()) + list(commun.values()) for x in v]
    lignes.sort(key=lambda x: str(x.get("quand") or ""), reverse=True)
    return lignes


def _rang_libre(liste, registre):
    """Le premier numero non utilise dans ce registre."""
    pris = set()
    for x in liste:
        bout = str(x.get("id") or "").rsplit("-", 1)[-1]
        if bout.isdigit():
            pris.add(int(bout))
    n = 1
    while n in pris:
        n += 1
    return n


def consigner(registre, valeurs, organisme=None):
    if registre not in REGISTRES:
        return None, "Registre inconnu."
    quoi = str(valeurs.get("quoi") or "").strip()
    if not quoi:
        return None, "Dites ce que vous avez fait ou lu."
    import fichiers
    o = bucket(registre, organisme)
    with fichiers.modifier(_FICHIER, {}) as tout:
        liste = tout.setdefault(o, {}).setdefault(registre, [])
        entree = {
        # Le rang plutot que la longueur : apres une suppression, deux entrees
        # auraient porte le meme identifiant, et retirer l'une aurait retire
        # l'autre. Le defaut existait avant le partage ; il devient probable
        # avec un registre commun, plus fourni.
        "id": "%s-%d" % (registre, _rang_libre(liste, registre)),
        "quand": str(valeurs.get("quand") or "").strip() or date.today().strftime("%Y-%m-%d"),
        "quoi": quoi,
        "source": str(valeurs.get("source") or "").strip(),
        # L'EXPLOITATION est ce que l'auditeur verifie. Une veille sans
        # exploitation est une non-conformite mineure ; c'est ecrit noir sur
        # blanc pour les indicateurs 23, 24 et 25.
        "exploitation": str(valeurs.get("exploitation") or "").strip(),
        "lien": str(valeurs.get("lien") or "").strip(),
        # Un justificatif depose : chemin RELATIF au dossier justificatifs/, et
        # le nom lisible. La preuve la plus solide du critere 6 est souvent un
        # fichier — une attestation de DPC, le programme d'un congres — et non
        # une adresse qui peut disparaitre.
        "fichier": str(valeurs.get("fichier") or "").strip(),
        "fichier_nom": str(valeurs.get("fichier_nom") or "").strip(),
        }
        liste.append(entree)
    return entree, ""


def retirer_consignation(registre, ident, organisme=None):
    import fichiers
    o = bucket(registre, organisme)
    with fichiers.modifier(_FICHIER, {}) as tout:
        liste = (tout.get(o) or {}).get(registre) or []
        reste = [x for x in liste if x.get("id") != ident]
        if len(reste) == len(liste):
            return False
        tout[o][registre] = reste
    return True


# --------------------------------------------------------------- l'appréciation

_ORDRE = {"couvert": 3, "partiel": 2, "absent": 1, "na": 0}


def _etat(ind, consignes):
    """L'état réel : le socle, relevé d'un cran si vous avez consigné.

    Consigner ne rend pas conforme — c'est l'auditeur qui juge. Mais une veille
    datée et exploitée fait passer l'indicateur 23 de « rien à montrer » à
    « quelque chose à montrer », et c'est toute la différence.
    """
    if ind["socle"] == "na":
        return "na"
    if not ind.get("registre") or not consignes:
        return ind["socle"]
    if ind["socle"] == "absent":
        return "partiel"
    if ind["socle"] == "partiel":
        return "couvert"
    return ind["socle"]


def etat(organisme=None):
    """Le référentiel entier, apprécié pour cet organisme."""
    import profil
    o = _organisme(organisme)
    fiche = profil.charger(o) or {}
    nouvel = bool(fiche.get("nouvel_entrant"))
    site = (fiche.get("site_web") or "").strip()
    tout = _tout()
    par_registre = (tout.get(o) or {})
    # Les registres partages ne sont pas ranges sous l'organisme : sans cette
    # seconde lecture, l'ecran d'audit compterait zero consignation sur les
    # indicateurs 22 a 25 alors que le registre commun est rempli.
    commun = (tout.get(COMMUN) or {})

    sortie = []
    for ind in INDICATEURS:
        d = dict(ind)
        reg = ind.get("registre") or ""
        source = commun if reg in PARTAGES else par_registre
        notes = list(source.get(reg, []))
        d["consignes"] = len(notes)
        d["derniere"] = max((x.get("quand") or "" for x in notes), default="")
        d["etat"] = _etat(ind, notes)
        d["allege_actif"] = nouvel and ind["allege"] and ind["socle"] != "na"
        # Sans site public, la preuve des indicateurs 1 et 2 change de nature :
        # elle passe par la proposition commerciale adressee au client.
        if ind["n"] in (1, 2):
            d["sans_site"] = not site
            d["site"] = site
        sortie.append(d)
    return {"organisme": o, "marque": fiche.get("marque") or o,
            "nouvel_entrant": nouvel, "site": site,
            "version": VERSION, "verifie_le": VERIFIE_LE,
            "indicateurs": sortie, "criteres": CRITERES,
            "bilan": bilan(sortie)}


def bilan(indicateurs):
    c = {"couvert": 0, "partiel": 0, "absent": 0, "na": 0}
    for i in indicateurs:
        c[i["etat"]] = c.get(i["etat"], 0) + 1
    applicables = c["couvert"] + c["partiel"] + c["absent"]
    c["applicables"] = applicables
    c["total"] = len(indicateurs)
    c["pct"] = int(round(100.0 * c["couvert"] / applicables)) if applicables else 0
    # Ce qui coute le plus cher : un indicateur absent qui ne connait que la
    # non-conformite majeure.
    c["majeurs_absents"] = len([i for i in indicateurs
                                if i["etat"] == "absent" and i["gravite"] == "majeure"])
    return c


def par_critere(donnees):
    """Regroupe pour l'affichage : un bloc par critère, non applicables à part."""
    blocs = []
    for num, titre, icone in CRITERES:
        siens = [i for i in donnees["indicateurs"] if i["critere"] == num]
        actifs = [i for i in siens if i["etat"] != "na"]
        blocs.append({
            "num": num, "titre": titre, "icone": icone,
            "indicateurs": actifs,
            "non_applicables": [i for i in siens if i["etat"] == "na"],
            "bilan": bilan(siens),
        })
    return blocs
