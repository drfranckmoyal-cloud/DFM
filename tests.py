# -*- coding: utf-8 -*-
"""Les tests de DFM. A lancer avant tout deploiement.

    venv/bin/python tests.py

POURQUOI CE FICHIER EXISTE, ET CE QU'IL AURAIT EVITE. Le 17/10/2026, une
modification de l'import des demandes a laisse un deballage de tuple a quatre
elements la ou il en fallait cinq. Le fichier COMPILAIT parfaitement, donc
deployer.sh l'a envoye sans rien dire. Resultat : l'import echouait pour tout
le monde, et Talia GUEZ, inscrite le 18/10 a 11h56, est restee un jour sans
fiche. Franck ne l'a su qu'en lisant un bandeau d'alerte.

UN TEST QUI FAIT TOURNER L'IMPORT POUR DE VRAI aurait echoue en trois
secondes, sur le Mac, avant l'envoi. C'est tout l'objet de ce fichier : la
syntaxe ne prouve rien, seul le passage prouve.

CE QUE CES TESTS NE TOUCHENT PAS : ni la base de Franck, ni Google, ni
Supabase, ni un seul mail. Base temporaire, portes reseau bouchees. Un test
qui ecrirait dans les vraies donnees serait pire que pas de test.
"""
import io
import os
import sys
import tempfile

DOSSIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOSSIER)
os.chdir(DOSSIER)

_ECHECS = []
_FAITS = [0]


def verifier(nom, condition, vu=""):
    _FAITS[0] += 1
    if condition:
        print("    ok   %s" % nom)
    else:
        print("    RATE %s%s" % (nom, ("  -> " + str(vu)) if vu != "" else ""))
        _ECHECS.append(nom)


def _corps_html(message):
    """Le texte HTML d'un mail, quel que soit son emboitement.

    Les mails de DFM sont des multipart « related » qui contiennent un
    multipart « alternative » qui contient le HTML. Demander le contenu du
    premier niveau rend None — erreur commise deux fois en ecrivant ces tests.
    """
    for part in message.walk():
        if part.get_content_type() == "text/html":
            charge = part.get_payload(decode=True)
            if charge:
                return charge.decode("utf-8", "replace")
    return ""


def _isoler():
    """Base temporaire et portes reseau bouchees. Rien ne sort de ce test."""
    import connexion
    connexion.service_sheets = lambda *a, **k: None
    connexion.service_drive = lambda *a, **k: None
    import base
    base.CHEMIN = os.path.join(tempfile.mkdtemp(prefix="dfm-test-"), "essai.db")
    base._SCHEMA_POSE.clear()
    if hasattr(base._LOCAL, "conn"):
        del base._LOCAL.conn
    import suivi, journal, miroir
    suivi.service_sheets = lambda *a, **k: None
    journal.service_sheets = lambda *a, **k: None
    miroir.deposer = lambda *a, **k: 0        # le classeur ne nous interesse pas ici
    journal.ecrire = lambda *a, **k: None
    return base


FICHE = {
    "code": "essai-test26", "nom_formation": "Essai", "titre_complet": "Essai",
    "organisme": "mon-organisme", "onglet_suivi": "Essai", "sheet_suivi": "FEUILLE-ESSAI",
    "places_max": 3, "tarif": "975", "date_texte": "1 et 2 mars 2027",
    "date_debut": "2027-03-01", "date_fin": "2027-03-02",
}


def _demande(nom, prenom, mail, demande="Je confirme ma demande d'inscription", ident=None):
    return {"id": ident if ident is not None else abs(hash(mail)) % 100000,
            "nom": nom, "prenom": prenom, "mail": mail, "telephone": "06 00 00 00 00",
            "ville": "Paris", "fonction": "Chirurgien-dentiste", "demande": demande,
            "connu_par": "", "dejeuner": "Oui", "restrictions": "", "image": "", "pmr": "Non",
            "code_session": FICHE["code"], "organisme": "mon-organisme",
            "horodateur": "2026-10-18T09:56:44.131591+00:00"}


def tests_import():
    """L'IMPORT DES DEMANDES. Le coeur du metier : une personne qui s'inscrit
    doit avoir une fiche, et une demande sans fiche ne doit JAMAIS etre
    marquee comme reprise."""
    print("\n  L'IMPORT DES DEMANDES")
    _isoler()
    import importer_demandes as imp
    import inscription as I
    import invitations as inv
    import sessions as _s
    import suivi

    _s.SESSIONS[FICHE["code"]] = dict(FICHE)
    _s.session = lambda c=None: dict(FICHE)
    _s.etat = lambda c=None: {"statut_session": "ouverte"}
    suivi.session = lambda c=None: dict(FICHE)
    suivi.rafraichir_statuts = lambda *a, **k: None
    marquees = []
    I.marquer_importee = lambda ident: marquees.append(ident)
    inv.FICHIER = os.path.join(tempfile.mkdtemp(prefix="dfm-inv-"), "invitations.json")

    # 1. LE CAS ORDINAIRE — c'est celui qui etait casse le 18/10.
    cree = imp.traiter(FICHE["code"], [_demande("GUEZ", "Talia", "talia@essai.test", ident=22)])
    lignes = suivi.lire_lignes_de(FICHE["code"])
    verifier("une demande donne une fiche", cree == 1 and len(lignes) == 1, (cree, len(lignes)))
    if lignes:
        l = lignes[0]
        verifier("le nom est repris", l["nom"] == "GUEZ", l["nom"])
        verifier("le mail est repris", l["mail"] == "talia@essai.test", l["mail"])
        verifier("la fonction est reprise", l["fonction"] == "Chirurgien-dentiste")
        verifier("le montant du est celui de la session", l["montant_du"] == "975", l["montant_du"])
        verifier("elle n'est pas invitee", not l["invite_le"])
        verifier("elle n'est pas en file d'attente", not l["file_attente_le"])
    verifier("la demande est marquee reprise", marquees == [22], marquees)

    # 2. PAS DEUX FOIS LA MEME PERSONNE
    del marquees[:]
    cree = imp.traiter(FICHE["code"], [_demande("GUEZ", "Talia", "talia@essai.test", ident=22)])
    verifier("une demande deja reprise ne cree pas de doublon",
             cree == 0 and len(suivi.lire_lignes_de(FICHE["code"])) == 1)
    verifier("et elle est remarquee, pour ne pas revenir sans fin", marquees == [22], marquees)

    # 3. UNE DEMANDE DE RAPPEL N'EST PAS UNE INSCRIPTION
    del marquees[:]
    imp.traiter(FICHE["code"], [_demande("DURAND", "Jean", "jean@essai.test",
                                         demande="Je souhaite un recontact", ident=23)])
    jean = next((l for l in suivi.lire_lignes_de(FICHE["code"]) if l["nom"] == "DURAND"), None)
    verifier("une demande de rappel donne quand meme une fiche", jean is not None)
    if jean:
        verifier("et elle n'est pas mise en file d'attente", not jean["file_attente_le"])

    # 4. UN INVITE NAIT INVITE, SANS SOMME A PAYER
    del marquees[:]
    inv.poser(FICHE["code"], "Cadeau@Essai.Test", par="Franck")
    imp.traiter(FICHE["code"], [_demande("CADEAU", "Alice", "cadeau@essai.test", ident=24)])
    alice = next((l for l in suivi.lire_lignes_de(FICHE["code"]) if l["nom"] == "CADEAU"), None)
    verifier("l'invitee a une fiche", alice is not None)
    if alice:
        verifier("elle est marquee invitee", bool(alice["invite_le"]), alice["invite_le"])
        verifier("elle ne doit rien", alice["montant_du"] == "0", alice["montant_du"])
    verifier("l'invitation est consommee", inv.pour(FICHE["code"], "cadeau@essai.test") is None)

    # 5. SESSION PLEINE : FILE D'ATTENTE, mais la fiche existe
    #    Trois places. Talia et Alice comptent ; Jean, qui demande un rappel, ne
    #    compte pas. Il faut donc une troisieme inscrite avant que Paul deborde.
    del marquees[:]
    imp.traiter(FICHE["code"], [_demande("PLEIN", "Sophie", "sophie@essai.test", ident=30)])
    sophie = next((l for l in suivi.lire_lignes_de(FICHE["code"]) if l["nom"] == "PLEIN"), None)
    verifier("la 3e inscrite entre encore", sophie is not None and not sophie["file_attente_le"])
    imp.traiter(FICHE["code"], [_demande("TARD", "Paul", "paul@essai.test", ident=25)])
    paul = next((l for l in suivi.lire_lignes_de(FICHE["code"]) if l["nom"] == "TARD"), None)
    verifier("la 4e, elle, a quand meme une fiche", paul is not None)
    if paul:
        verifier("et elle est en file d'attente", bool(paul["file_attente_le"]),
                 paul["file_attente_le"])

    # 6. LE PLUS IMPORTANT : SI L'ECRITURE RATE, RIEN N'EST MARQUE.
    #    C'est ce qui a sauve Talia GUEZ : sa demande revenait a chaque passage.
    del marquees[:]
    del imp.ECHECS[:]
    vrai = suivi.ajouter_plusieurs
    suivi.ajouter_plusieurs = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("panne simulee"))
    cree = imp.traiter(FICHE["code"], [_demande("PERDU", "Marie", "marie@essai.test", ident=26)])
    suivi.ajouter_plusieurs = vrai
    verifier("une ecriture ratee ne cree rien", cree == 0, cree)
    verifier("et NE MARQUE PAS la demande : elle reviendra", marquees == [], marquees)
    verifier("et l'echec est declare au traitement", len(imp.ECHECS) == 1, imp.ECHECS)


def tests_montant_attendu():
    """CE QU'UNE PERSONNE DOIT. Deux erreurs en une journee le 17/10 :
    reclamer 975 euros a une invitee, puis cesser de reclamer a qui devait."""
    print("\n  LE MONTANT DU PAR UNE PERSONNE")
    _isoler()
    import suivi
    cas = [("un invite ne doit rien", {"invite_le": "17/10/2026"}, "975", 0.0),
           ("un montant vide vaut le tarif", {"montant_du": ""}, "975", 975.0),
           ("un montant ecrit est respecte", {"montant_du": "500"}, "975", 500.0),
           ("un zero ecrit est un zero", {"montant_du": "0"}, "975", 0.0),
           ("le format francais se lit", {"montant_du": "1 234,50 €"}, "975", 1234.5)]
    for nom, ligne, tarif, attendu in cas:
        vu = suivi.montant_attendu(ligne, tarif)
        verifier(nom, abs(vu - attendu) < 0.001, vu)


def tests_file_du_classeur():
    """LA FILE DES COPIES VERS LE CLASSEUR : l'ordre, et la survie."""
    print("\n  LA FILE DES COPIES VERS LE CLASSEUR")
    base = _isoler()
    import miroir
    import importlib
    importlib.reload(miroir)            # on veut le vrai deposer, pas le bouchon
    # AUCUN FIL DE FOND PENDANT UN TEST. Sinon il vide la file en meme temps
    # qu'on la mesure, et le test devient une loterie : c'est exactement ce
    # qui l'a fait echouer a sa premiere ecriture. Ici, on vide a la main.
    miroir.demarrer = lambda: None
    passages, casse = [], {"actif": False}
    miroir._executer = lambda f, d: (_ for _ in ()).throw(RuntimeError("Google absent")) \
        if casse["actif"] else passages.append((f, d))
    for i in range(4):
        miroir.deposer("mon-organisme", "F", [{"range": "A%d" % i, "values": [[i]]}])
    faites, restantes, _souci = miroir.rattraper()
    verifier("les copies partent", faites == 4 and restantes == 0, (faites, restantes))
    verifier("dans l'ordre du depot",
             [p[1][0]["range"] for p in passages] == ["A0", "A1", "A2", "A3"])
    casse["actif"] = True
    miroir.deposer("mon-organisme", "F", [{"range": "B1", "values": [["x"]]}])
    faites, restantes, souci = miroir.rattraper()
    verifier("une copie qui echoue reste en file", restantes == 1, restantes)
    verifier("et le souci est connu", bool(souci), souci)
    casse["actif"] = False
    base.fermer()
    base._SCHEMA_POSE.clear()
    if hasattr(base._LOCAL, "conn"):
        del base._LOCAL.conn
    verifier("elle survit a un redemarrage", base.miroir_etat()["attente"] == 1)
    faites, restantes, _ = miroir.rattraper()
    verifier("et elle part ensuite", faites == 1 and restantes == 0, (faites, restantes))


def tests_alerte_inscriptions():
    """L'ALERTE QUI VIENT CHERCHER FRANCK. Le 19/10/2026 : « si je n'avais pas
    lu la banderole d'erreur je n'aurais jamais su qu'elle etait inscrite »."""
    print("\n  L'ALERTE PAR MAIL DU CONTROLE DES INSCRIPTIONS")
    _isoler()
    import courrier
    import profil
    import verifier_inscriptions as v

    envoyes = []
    courrier.envoyer = lambda message, organisme: envoyes.append(
        {"a": message["To"], "objet": message["Subject"],
         "corps": _corps_html(message), "of": organisme})
    profil.charger = lambda i: {"mail_contact": "contact-%s@essai.test" % i,
                                "marque": "Marque " + i}
    v.MEMOIRE = os.path.join(tempfile.mkdtemp(prefix="dfm-alerte-"), "etat.json")

    soucis = ["Talia GUEZ <t@essai.test> a demandé usures-fev27 — pas encore reprise"]
    partis = v._prevenir(soucis, {"mon-organisme": soucis})
    verifier("l'alerte part", len(envoyes) == 1, len(envoyes))
    if envoyes:
        m = envoyes[0]
        verifier("a l'adresse de contact de l'organisme",
                 m["a"] == "contact-mon-organisme@essai.test", m["a"])
        verifier("l'objet dit ce qui se passe", "sans fiche" in m["objet"], m["objet"])
        verifier("le nom de la personne y est", "Talia GUEZ" in m["corps"])
        verifier("elle dit qu'aucun courrier ne partira",
                 "aucun courrier ne leur partira" in m["corps"])
        verifier("sous l'identite du bon organisme", m["of"] == "mon-organisme", m["of"])

    # PAS DEUX FOIS LA MEME ALERTE : le controle passe toutes les dix minutes.
    signature = "|".join(sorted(soucis))
    v._noter_alerte(signature)
    verifier("la meme alerte ne repart pas dans les six heures",
             v._deja_alerte(signature) is True)
    verifier("mais une liste differente, si",
             v._deja_alerte(signature + "|un autre") is False)
    v._oublier_alerte()
    verifier("et quand l'ecart est resorbe, la memoire est effacee",
             v._deja_alerte(signature) is False)

    # DEUX ORGANISMES, DEUX DESTINATAIRES : le cloisonnement vaut aussi pour
    # les alertes.
    del envoyes[:]
    v._prevenir(soucis * 2, {"mon-organisme": soucis, "dsf": soucis})
    verifier("chaque organisme recoit la sienne", len(envoyes) == 2, len(envoyes))
    verifier("et jamais celle du voisin",
             sorted(m["a"] for m in envoyes)
             == ["contact-dsf@essai.test", "contact-mon-organisme@essai.test"],
             [m["a"] for m in envoyes])


def tests_accuse_reception():
    """L'ACCUSE DE RECEPTION. Le seul courrier qui ne depende de rien : ni du
    suivi, ni du classeur. Il aurait fonctionne le 18/10 avec le code casse."""
    print("\n  L'ACCUSE DE RECEPTION A L'INSCRITE")
    _isoler()
    import accuser_reception as ar
    import courrier
    import inscription as I
    import journal
    import mails as _mails
    import profil
    import sessions as _s

    _s.SESSIONS[FICHE["code"]] = dict(FICHE)
    _s.session = lambda c=None: dict(FICHE)
    _s.organisme_de = lambda c=None: "mon-organisme"
    profil.logo = lambda o=None: None
    journal.ecrire = lambda *a, **k: None
    envoyes = []
    casse = {"actif": False}

    def faux_envoi(message, organisme):
        if casse["actif"]:
            raise RuntimeError("Gmail indisponible (essai)")
        envoyes.append({"a": message["To"], "objet": message["Subject"],
                        "corps": _corps_html(message)})
    courrier.envoyer = faux_envoi
    ar.REGISTRE = os.path.join(tempfile.mkdtemp(prefix="dfm-ar-"), "registre.json")
    ar.SIMULATION = False       # il envoie par defaut ; on l'explicite ici

    anciennes = [_demande("ANCIEN", "Paul", "paul@essai.test", ident=1)]
    I._sb = lambda chemin: list(anciennes)

    # 1. PREMIER PASSAGE : on prend date, on n'ecrit a personne.
    ar.main()
    verifier("au premier passage, aucun mail", envoyes == [], envoyes)
    verifier("mais les demandes connues sont enregistrees",
             ar._registre() == {"1"}, ar._registre())

    # 2. UNE NOUVELLE DEMANDE EST ACCUSEE
    anciennes.append(_demande("GUEZ", "Talia", "talia@essai.test", ident=2))
    ar.main()
    verifier("la nouvelle demande recoit un accuse", len(envoyes) == 1, len(envoyes))
    if envoyes:
        m = envoyes[0]
        verifier("adresse a la bonne personne", m["a"] == "talia@essai.test", m["a"])
        verifier("l'objet dit que c'est arrive", "bien arriv" in m["objet"], m["objet"])
        verifier("son prenom y est", "Talia" in m["corps"])
        verifier("le titre de la formation y est", "Essai" in m["corps"])
        verifier("et LA PHRASE QUI SAUVE : relancer si rien n'arrive",
                 "d'ici une semaine" in m["corps"])
        verifier("aucune balise oubliee", "{{" not in m["corps"])

    # 3. PAS DEUX FOIS
    del envoyes[:]
    ar.main()
    verifier("un accuse ne part jamais deux fois", envoyes == [], envoyes)

    # 4. UNE DEMANDE TROP VIEILLE N'EST PAS ACCUSEE SIX MOIS APRES
    vieille = _demande("VIEUX", "Jean", "jean@essai.test", ident=3)
    vieille["horodateur"] = "2026-01-05T10:00:00+00:00"
    anciennes.append(vieille)
    ar.main()
    verifier("une demande de plus de sept jours n'est pas accusee", envoyes == [], envoyes)
    verifier("mais elle est enregistree, pour ne plus etre reexaminee",
             "3" in ar._registre())

    # 5. UNE SESSION INCONNUE N'EMPECHE PAS D'ACCUSER : la personne n'y est pour rien
    del envoyes[:]
    orpheline = _demande("ORPHELIN", "Lea", "lea@essai.test", ident=4)
    orpheline["code_session"] = "session-disparue"
    anciennes.append(orpheline)
    ar.main()
    verifier("une demande sur session inconnue est accusee quand meme",
             len(envoyes) == 1, len(envoyes))

    # 6. LE PLUS IMPORTANT : UN ENVOI RATE N'EST PAS ENREGISTRE.
    del envoyes[:]
    casse["actif"] = True
    anciennes.append(_demande("RATE", "Marie", "marie@essai.test", ident=5))
    ar.main()
    casse["actif"] = False
    verifier("un envoi rate ne compte pas comme accuse", "5" not in ar._registre(),
             ar._registre())
    ar.main()
    verifier("et il repart au passage suivant", len(envoyes) == 1, len(envoyes))


def tests_connexion_perimee():
    """LA BASE QUI SE CASSE SOUS LES PIEDS DU PROCESSUS.

    Incident du 20/10/2026 : six heures de « database disk image is malformed »
    a chaque lecture, plus aucun inscrit a l'ecran, alors que le FICHIER etait
    sain — c'etait la connexion du processus qui etait morte. Une relance a
    tout remis, mais personne n'etait la pour relancer."""
    print("\n  UNE CONNEXION PERIMEE SE REMPLACE TOUTE SEULE")
    import sqlite3
    base = _isoler()
    base.suivi_ajouter("mon-organisme", "essai", {"nom": "DURAND"})
    verifier("la lecture marche au depart",
             len(base.suivi_lire("mon-organisme", "essai")) == 1)

    class ConnexionMorte:
        """Se plaint comme SQLite quand le fichier a change sous elle."""
        def execute(self, *a, **k):
            raise sqlite3.DatabaseError("database disk image is malformed")
        def commit(self):
            raise sqlite3.DatabaseError("database disk image is malformed")
        def close(self):
            pass

    depart = base._RECYCLAGES[0]
    base._LOCAL.conn = ConnexionMorte()
    lignes = base.suivi_lire("mon-organisme", "essai")
    verifier("malgre une connexion morte, la lecture aboutit", len(lignes) == 1, lignes)
    verifier("et la connexion a bien ete remplacee",
             base._RECYCLAGES[0] == depart + 1, base._RECYCLAGES[0] - depart)

    # suivi_poser MET A JOUR la ligne, il n'en cree pas une seconde : on
    # verifie donc que le champ a bien change, pas qu'une ligne s'est ajoutee.
    # suivi_lire rend [(numero, {champs}), ...]
    numero = base.suivi_lire("mon-organisme", "essai")[0][0]
    base._LOCAL.conn = ConnexionMorte()
    base.suivi_poser("mon-organisme", "essai", numero, {"nom": "MARTIN"})
    champs = dict(base.suivi_lire("mon-organisme", "essai"))[numero]
    verifier("une ECRITURE aussi se rejoue", champs.get("nom") == "MARTIN", champs)

    # UNE VRAIE ERREUR NE DOIT PAS ETRE AVALEE : on ne rejoue que la connexion
    # perimee, pas un defaut de code.
    class ConnexionBancale:
        def execute(self, *a, **k):
            raise sqlite3.DatabaseError("no such table: inexistante")
        def commit(self):
            pass
        def close(self):
            pass
    base._LOCAL.conn = ConnexionBancale()
    remontee = False
    try:
        base.suivi_lire("mon-organisme", "essai")
    except sqlite3.DatabaseError:
        remontee = True
    base._jeter()
    verifier("une autre erreur de base remonte, elle n'est pas cachee", remontee)
    verifier("la lecture remarche apres",
             len(base.suivi_lire("mon-organisme", "essai")) == 1)


def tests_guet_de_sante():
    """DFM CRIE-T-IL QUAND IL NE LIT PLUS SES DONNEES ?

    Le 20/10/2026, il est reste muet six heures. Ce guet est la pour que ca ne
    se reproduise pas."""
    print("\n  LE GUET DE SANTE DE LA BASE")
    base = _isoler()
    import alerte
    import planificateur as plan

    appels = []
    alerte.prevenir = lambda cle, objet, paras, **k: appels.append(
        {"cle": cle, "objet": objet, "paras": paras, "quoi": k.get("quoi_faire", "")}) or "contact@essai.test"
    oublis = []
    alerte.oublier = lambda cle: oublis.append(cle)

    # 1. TOUT VA BIEN : pas d'alerte, et la memoire est effacee.
    plan._guetter_sante()
    verifier("base lisible : aucune alerte", appels == [], appels)
    verifier("et la memoire de l'alerte est effacee", "base-illisible" in oublis, oublis)

    # 2. LA BASE NE REPOND PLUS : on ecrit a Franck.
    import sqlite3
    vrai = base.suivi_compte
    base.suivi_compte = lambda *a, **k: (_ for _ in ()).throw(
        sqlite3.DatabaseError("database disk image is malformed"))
    del appels[:]
    plan._guetter_sante()
    base.suivi_compte = vrai
    verifier("base illisible : une alerte part", len(appels) == 1, len(appels))
    if appels:
        a = appels[0]
        verifier("sous la bonne cle", a["cle"] == "base-illisible", a["cle"])
        verifier("l'objet est explicite", "ne répond plus" in a["objet"], a["objet"])
        verifier("elle dit que les inscrits n'apparaissent plus",
                 any("inscrits" in p for p in a["paras"]))
        verifier("elle rassure sur les donnees",
                 any("Rien n'est perdu" in p for p in a["paras"]))
        verifier("et elle dit quoi faire", "Verifier que DFM va bien" in a["quoi"], a["quoi"])

    # 3. LES RECYCLAGES EN SERIE SE SIGNALENT AUSSI
    del appels[:]
    base._RECYCLAGES[0] = 25
    plan._guetter_sante()
    base._RECYCLAGES[0] = 0
    verifier("une serie de reouvertures se signale",
             any(x["cle"] == "connexions-recyclees" for x in appels), [x["cle"] for x in appels])


def tests_entete_des_mails():
    """L'EN-TETE DES MAILS — « option A », choisie par Franck le 21/10/2026.

    Ce qui est verifie ici n'est pas le gout, c'est ce qui casse en vrai :
    les dimensions qu'Outlook exige, le repli du degrade, et le fait que le
    filet suive l'organisme au lieu d'etre ecrit en dur."""
    print("\n  L'EN-TETE DES MAILS")
    _isoler()
    import mails as _mails
    import profil
    import sessions as _s

    profils = {"mon-organisme": {"marque": "Smileclub Formations",
                                 "couleur": "#d4890a", "couleur_mail": "#4B6BCD",
                                 "degrade_mail": "linear-gradient(90deg, #264BC6 0%, #3559C4 100%)"},
               "dsf": {"marque": "DSF", "couleur": "#4f7ef8"}}
    profil.charger = lambda i=None: dict(profils.get(i) or {})
    _s.organisme_de = lambda c=None: "dsf" if c == "chez-dsf" else "mon-organisme"
    # La vraie fiche de session porte la marque de l'organisme ; celle des
    # autres essais ne l'a pas, on la pose ici.
    S = dict(FICHE, code="essai-test26", formation="", marque="Smileclub Formations")

    # UNE IMAGE DE LOGO MINUSCULE MAIS VALIDE : 40 x 20, donc large.
    import base64
    logo = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAACgAAAAUCAYAAADIpHLKAAAAHklEQVRIx2NgGAWjYBSMglEw"
        "CkbBKBgFo2AUjAIaAwAHBgABm1bBpwAAAABJRU5ErkJggg==")

    modele = _mails.pour_formation("", "accuse-reception")
    html = _mails.poser_logo(
        _mails.rendre(modele, _mails.contexte(S, {"prenom": "Camille"}))["html"], logo)

    print("    le logo")
    verifier("il est dans le mail", "cid:logo" in html)
    verifier("avec ses dimensions en ATTRIBUTS, qu'Outlook exige",
             'width="' in html and 'height="' in html)
    verifier("et aussi en style, pour les autres",
             "width:" in html and "height:" in html)
    verifier("il est centre", "margin:0 auto" in html)
    verifier("il porte le nom de l'organisme en texte de remplacement",
             'alt="Smileclub Formations"' in html, html[html.find("alt="):][:40])

    print("    le filet")
    verifier("la couleur unie est la, pour Outlook",
             "background:#4B6BCD" in html, html[html.find("background:"):][:40])
    verifier("le degrade est la, pour les autres",
             "background-image:linear-gradient" in html)
    verifier("l'ancien trait gris a disparu", "background:#e6e9f2" not in html)
    verifier("il ne grossit pas d'une ligne de texte",
             "font-size:0" in html and "line-height:0" in html)

    print("    chaque organisme a ses couleurs")
    html_dsf = _mails.rendre(
        _mails.pour_formation("", "accuse-reception"),
        _mails.contexte(dict(S, code="chez-dsf"), {"prenom": "Camille"}))["html"]
    verifier("DSF a la sienne", "background:#4f7ef8" in html_dsf)
    verifier("et PAS celle de Smileclub", "#4B6BCD" not in html_dsf)
    verifier("sans degrade declare, aucun n'est impose",
             "background-image:none" in html_dsf)

    print("    le corps n'a pas bouge")
    verifier("le texte du mail est intact", "bien reçu votre demande" in html)
    verifier("et la phrase qui sert de filet de securite aussi",
             "d'ici une semaine" in html)
    verifier("aucune balise oubliee", "{{" not in html and "}}" not in html)

    print("    tous les modeles passent l'enveloppe")
    for usage in sorted(_mails.USAGES):
        m = _mails.pour_formation("", usage)
        h = _mails.rendre(m, _mails.contexte(S, {"prenom": "Camille"}))["html"]
        verifier("%-24s rendu sans balise oubliee" % usage,
                 "{{" not in h and "}}" not in h and "cid:logo" in h)


def main():
    print()
    print("  LES TESTS DE DFM")
    print("  " + "-" * 56)
    for essai in (tests_import, tests_montant_attendu, tests_file_du_classeur,
                  tests_alerte_inscriptions, tests_accuse_reception,
                  tests_connexion_perimee, tests_guet_de_sante,
                  tests_entete_des_mails):
        try:
            essai()
        except Exception as e:
            import traceback
            print("    RATE %s a leve : %s" % (essai.__name__, e))
            traceback.print_exc()
            _ECHECS.append(essai.__name__)
    print()
    print("  " + "-" * 56)
    if _ECHECS:
        print("  %d CONTROLE(S) EN ECHEC sur %d :" % (len(_ECHECS), _FAITS[0]))
        for x in _ECHECS:
            print("     . %s" % x)
        print()
        print("  NE PAS DEPLOYER.")
        return 1
    print("  %d controles, tous au vert." % _FAITS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
