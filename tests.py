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

    # 5 bis. UN PROMU N'EST PLUS EN FILE D'ATTENTE. Fiona CHETOUANE a recu
    #        « vous etes en file d'attente » une minute avant sa convention,
    #        parce que la selection ignorait la promotion.
    lignes_fa = suivi.lire_lignes_de(FICHE["code"])
    paul = next(l for l in lignes_fa if l["nom"] == "TARD")
    suivi.ecrire(paul["_numero"], "promu_le", "21/10/2026 09:00", FICHE["code"])
    relu = next(l for l in suivi.lire_lignes_de(FICHE["code"]) if l["nom"] == "TARD")
    a_prevenir = [l for l in suivi.lire_lignes_de(FICHE["code"])
                  if l["file_attente_le"] and not l["mail_attente_le"]
                  and not l["promu_le"] and not l["annule_le"]]
    verifier("la promotion est enregistree", bool(relu["promu_le"]), relu["promu_le"])
    verifier("et un promu n'est plus prevenu qu'il attend",
             all(l["nom"] != "TARD" for l in a_prevenir),
             [l["nom"] for l in a_prevenir])

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


def tests_formation_modules():
    """UNE FORMATION QUI PORTE DES MODULES — 23/10/2026, décision D23 de Franck.

    Esthétique360 est un cycle de cinq rendez-vous. La FORMATION en porte la
    structure, la SESSION portera les dates. Et surtout : les formations
    existantes ne doivent rien voir changer."""
    print("\n  LA FORMATION QUI PORTE DES MODULES")
    _isoler()
    import sessions as _s

    print("    lire la liste des modules")
    m, souci = _s.lire_modules("Essentiels | 3\nComposites | 3\nCéramique | 2")
    verifier("trois modules se lisent", len(m) == 3 and not souci, m)
    if len(m) == 3:
        verifier("l'intitulé est repris", m[0]["titre"] == "Essentiels", m[0])
        verifier("le nombre de journées aussi", m[2]["jours"] == 2, m[2])
        verifier("l'ordre est conservé", [x["titre"] for x in m][1] == "Composites")
    verifier("un intitulé à barre verticale ne casse rien",
             _s.lire_modules("Avant | après | 3")[0] == [{"titre": "Avant | après", "jours": 3}],
             _s.lire_modules("Avant | après | 3")[0])

    print("    on refuse plutôt que de deviner")
    for texte, ce_qui_manque in (("Essentiels", "le nombre de journées"),
                                 ("Essentiels | zéro", "un nombre"),
                                 ("Essentiels | 0", "zéro journée"),
                                 ("  |  3", "l'intitulé")):
        modules, souci = _s.lire_modules(texte)
        verifier("« %s » est refusé (%s)" % (texte.strip()[:18], ce_qui_manque),
                 modules is None and bool(souci), souci[:50])

    print("    une formation ordinaire n'en a pas")
    verifier("pas de module : liste vide, aucun refus",
             _s.lire_modules("") == ([], "") and _s.lire_modules(None) == ([], ""))

    print("    LES FORMATIONS EXISTANTES NE CHANGENT PAS")
    # L'écran enregistre désormais moyens, prérequis et nature ; vides, les
    # valeurs par défaut gravées dans le code doivent continuer de s'appliquer,
    # exactement comme quand ces champs n'existaient pas du tout.
    import attestation as _att
    import convention
    convention._images = lambda code_session=None: ("data:image/png;base64,AA",
                                                    "data:image/png;base64,BB", [])
    base_fiche = dict(FICHE, code="essai-test26", marque="Smileclub Formations",
                      tarif="975", date_debut="2027-03-01", date_fin="2027-03-02",
                      objectifs=["Objectif"], jours=[])
    ligne = {"nom": "DUPONT", "prenom": "Jean", "fonction": "Chirurgien-dentiste"}
    _s.session = lambda c=None: dict(_s.SESSIONS.get(c) or {})
    for nom, fiche in (("avant (champs absents)", base_fiche),
                       ("après (champs vides)",
                        dict(base_fiche, moyens=[], prerequis="", nature_action="",
                             modules=[]))):
        _s.SESSIONS["essai-test26"] = fiche
        d, souci = convention.pour("essai-test26", ligne=ligne)
        if not d:
            verifier("%s : la convention se calcule" % nom, False, souci)
            continue
        verifier("%s : moyens par défaut" % nom,
                 d["moyens"] == convention.MOYENS_DEFAUT, d["moyens"][:1])
        verifier("%s : prérequis par défaut" % nom,
                 d["prerequis"] == convention.PREREQUIS_DEFAUT)
        verifier("%s : catégorie par défaut" % nom,
                 d["categorie"] == dict(_att.CATEGORIES)[_att.NATURE_DEFAUT],
                 d["categorie"][:40])

    print("    et une formation qui les remplit en tient compte")
    _s.SESSIONS["essai-test26"] = dict(base_fiche, moyens=["Un microscope"],
                                       prerequis="Être praticien", nature_action="qualification")
    d, _souci = convention.pour("essai-test26", ligne=ligne)
    if d:
        verifier("les moyens saisis s'impriment", d["moyens"] == ["Un microscope"], d["moyens"])
        verifier("le prérequis saisi aussi", d["prerequis"] == "Être praticien")
        verifier("et la catégorie choisie", d["categorie"] == dict(_att.CATEGORIES)["qualification"],
                 d["categorie"][:30])


def tests_reparation_base():
    """Recoller une entree de journal depuis le classeur, SANS LA CROIRE SUR PAROLE.

    C'est la piece delicate de la reparation du 23/10/2026. Google convertit
    « 2026-10-22 08:34:56 » en nombre de jours : pour remettre l'entree dans la
    base, il faut refaire la conversion a l'envers, au caractere pres. Une
    seconde d'ecart et le scelle ne tombe plus — ce qui est precisement la
    garantie cherchee, mais encore faut-il que le cas juste passe.
    """
    import reparer_base as _r
    print()
    print("  LA REPARATION DE LA BASE")
    print("    une date de Google se reconvertit a la seconde")
    # 46317.35759259259 est le nombre qu'a rendu le classeur pour l'entree 952.
    d = _r._depuis_serie(46317.35759259259)
    verifier("le jour est retrouve", d is not None and d.strftime("%Y-%m-%d") == "2026-10-22",
             d and d.strftime("%Y-%m-%d"))
    verifier("l'heure a la seconde aussi", d is not None and d.strftime("%H:%M:%S") == "08:34:56",
             d and d.strftime("%H:%M:%S"))
    verifier("un nombre arrondi par le bas remonte", 
             _r._depuis_serie(46317.0).strftime("%H:%M:%S") == "00:00:00")
    verifier("ce qui n'est pas un nombre ne casse rien", _r._depuis_serie("") is None)
    verifier("ni une case vide", _r._depuis_serie(None) is None)

    print("    les ecritures possibles d'une ligne sont toutes essayees")
    brut = [46317.35759259259, 46317.0, 0.3576, "Convention signée", "Sandy BAER-LAYANI",
            "usures-nov26", "signe le 2026-10-21 a 14:00", "", ""]
    formate = ["22/10/2026 08:34:56", "22/10/2026", "08:34", "Convention signée",
               "Sandy BAER-LAYANI", "usures-nov26", "signe le 2026-10-21 a 14:00", "", ""]
    cands = _r._candidats(brut, formate)
    verifier("plusieurs ecritures sont proposees", len(cands) >= 3, "%d" % len(cands))
    verifier("toutes font neuf colonnes", all(len(c) == 9 for c in cands))
    attendu = ["2026-10-22 08:34:56", "22/10/2026", "08:34"]
    verifier("celle que DFM ecrit en fait partie",
             any(c[:3] == attendu for c in cands),
             " | ".join(cands[-1][:3]))

    print("    et le recollage ne passe QUE si le scelle se recalcule")
    import scellement
    ligne = attendu + ["Convention signée", "Sandy BAER-LAYANI", "usures-nov26",
                       "signe le 2026-10-21 a 14:00", "", ""]
    precedent = "f00ad6e9a21a3e7e71b0"
    vrai = scellement.empreinte(952, ligne, precedent, "")
    verifier("la bonne ligne reproduit son scelle",
             any(scellement.empreinte(952, c, precedent, "") == vrai for c in cands))
    faux = list(ligne)
    faux[4] = "Sandy BAER-LAYANl"          # un l minuscule au lieu d'un i
    verifier("un nom altere d'un caractere ne le reproduit pas",
             scellement.empreinte(952, faux, precedent, "") != vrai)
    verifier("un rang different non plus",
             scellement.empreinte(953, ligne, precedent, "") != vrai)
    verifier("un ancetre different non plus",
             scellement.empreinte(952, ligne, "0" * 20, "") != vrai)


def tests_garde_fous_de_la_base():
    """Les deux protections posees apres la corruption du 22-23/10/2026.

    Ce ne sont pas des protections theoriques : chacune repare un silence qui a
    coute, cette fois-la, un jour et demi.
    """
    import base as _b
    import sauvegarde as _sv
    print()
    print("  LES GARDE-FOUS DE LA BASE")
    print("    une connexion morte se reconnait a tous ses messages")
    for m in ("database disk image is malformed", "disk I/O error",
              "DISK I/O ERROR", "file is not a database",
              "attempt to write a readonly database: disk image"):
        verifier("« %s » fait rouvrir" % m[:34], _b._connexion_perimee(m), m[:40])
    for m in ("no such table: suivi", "database is locked",
              "UNIQUE constraint failed: journal.rang"):
        verifier("« %s » ne fait PAS rouvrir" % m[:30], not _b._connexion_perimee(m))

    print("    la sauvegarde controle l'integrite de sa copie")
    import sqlite3 as _s3
    coin = tempfile.mkdtemp(prefix="dfm-integrite-")
    sain = os.path.join(coin, "sain.db")
    c = _s3.connect(sain)
    c.execute("CREATE TABLE t (a INTEGER PRIMARY KEY, b TEXT)")
    c.executemany("INSERT INTO t VALUES (?,?)", [(i, "x%d" % i) for i in range(50)])
    c.commit()
    c.close()
    verifier("une base saine rend « ok »", _sv._integrite(sain) == "ok",
             _sv._integrite(sain)[:40])

    pas_une_base = os.path.join(coin, "pas-une-base.db")
    with open(pas_une_base, "wb") as f:
        f.write(b"ceci n'est pas une base de donnees" * 40)
    etat = _sv._integrite(pas_une_base)
    verifier("un fichier qui n'est pas une base est signale",
             etat != "ok" and etat, etat[:50])

    absent = os.path.join(coin, "nulle-part.db")
    etat = _sv._integrite(absent)
    verifier("un fichier absent ne fait pas tomber la sauvegarde",
             isinstance(etat, str) and etat != "ok", etat[:50])


def tests_session_cycle():
    """Un cycle : cinq modules de trois jours sur l'annee, depuis cinq dates.

    LE DEFAUT CORRIGE LE 24/10/2026. Une session ne savait dire ses dates que
    d'une seule facon : les enumerer. Quinze journees reparties sur douze mois
    donnaient une phrase illisible, et l'ecran de saisie proposait une case a
    cocher par jour entre la premiere et la derniere — trois cent trente cases.
    """
    import jours as _j
    print()
    print("  LA SESSION « CYCLE »")

    print("    les journees se regroupent en venues")
    verifier("deux jours qui se suivent font une venue",
             len(_j.blocs(["2027-02-04", "2027-02-05"])) == 1)
    verifier("un samedi et un lundi aussi (le dimanche ne coupe pas)",
             len(_j.blocs(["2027-02-06", "2027-02-08"])) == 1,
             "%d" % len(_j.blocs(["2027-02-06", "2027-02-08"])))
    verifier("deux mois d'ecart font deux venues",
             len(_j.blocs(["2027-01-06", "2027-03-10"])) == 2)
    verifier("aucune journee, aucune venue", _j.blocs([]) == [])

    print("    cinq dates suffisent a decrire le cycle")
    modules = [{"titre": "Essentiels", "jours": 3},
               {"titre": "Composites", "jours": 3},
               {"titre": "Restaurations antérieures en céramique", "jours": 3},
               {"titre": "Techniques avancées", "jours": 3},
               {"titre": "Érosions et usures", "jours": 3}]
    departs = ["2027-01-06", "2027-03-10", "2027-05-19", "2027-09-22", "2027-12-01"]
    r = _j.depuis_modules(modules, departs)
    verifier("quinze journees", len(r["jours"]) == 15, "%d" % len(r["jours"]))
    verifier("105 heures, la duree du contrat", _j.duree(r["jours"]) == 105,
             "%s" % _j.duree(r["jours"]))
    verifier("cinq modules resolus", len(r["modules"]) == 5)
    verifier("aucun module sans date", r["manquants"] == 0)
    verifier("les bornes vont de janvier a decembre",
             _j.bornes(r["jours"]) == ("2027-01-06", "2027-12-03"),
             str(_j.bornes(r["jours"])))
    verifier("le module 1 nomme ses trois journees",
             r["modules"][0]["texte"] == "mercredi 6, jeudi 7 et vendredi 8 janvier 2027",
             r["modules"][0]["texte"])
    verifier("et le premier decembre s'ecrit « 1er »",
             r["modules"][4]["texte"] == "mercredi 1er, jeudi 2 et vendredi 3 décembre 2027",
             r["modules"][4]["texte"])

    print("    le dimanche n'est jamais compte dans un module")
    r2 = _j.depuis_modules([{"titre": "Trois jours", "jours": 3}], ["2027-01-09"])
    verifier("samedi, lundi, mardi — pas le dimanche",
             r2["jours"] == ["2027-01-09", "2027-01-11", "2027-01-12"],
             str(r2["jours"]))

    print("    une session en cours de saisie ne casse pas")
    r3 = _j.depuis_modules(modules, ["2027-01-06", "", "", "", ""])
    verifier("un seul module date : trois journees", len(r3["jours"]) == 3)
    verifier("et quatre modules annonces sans date", r3["manquants"] == 4)
    verifier("le module sans date le dit",
             "dates à venir" in _j.texte_modules(r3["modules"]),
             _j.texte_modules(r3["modules"]).splitlines()[1])

    print("    la balise des modules, telle qu'elle partira")
    t = _j.texte_modules(r["modules"])
    verifier("cinq lignes", len(t.splitlines()) == 5)
    verifier("chacune numerotee et datee",
             t.splitlines()[1]
             == "2 · Composites — mercredi 10, jeudi 11 et vendredi 12 mars 2027",
             t.splitlines()[1])

    print("    la phrase des dates reste lisible")
    verifier("chaque journee est nommee, les venues separees par une virgule",
             _j.texte(r["jours"]).startswith(
                 "mercredi 6, jeudi 7 et vendredi 8 janvier, mercredi 10,"),
             _j.texte(r["jours"])[:60])
    verifier("et l'annee n'est ecrite qu'une fois",
             _j.texte(r["jours"]).count("2027") == 1,
             "%d fois" % _j.texte(r["jours"]).count("2027"))

    print("    LES SESSIONS EN SERVICE NE BOUGENT PAS D'UN CARACTERE")
    for liste, attendu in (
            (["2027-02-25", "2027-02-26"], "jeudi 25 et vendredi 26 février 2027"),
            (["2026-10-28", "2026-10-29"], "mercredi 28 et jeudi 29 octobre 2026"),
            (["2026-12-03", "2026-12-04"], "jeudi 3 et vendredi 4 décembre 2026"),
            (["2027-02-04", "2027-02-05"], "jeudi 4 et vendredi 5 février 2027"),
            (["2026-11-04", "2026-11-05"], "mercredi 4 et jeudi 5 novembre 2026"),
            ([], "")):
        verifier("« %s »" % (attendu or "aucune journee"),
                 _j.texte(liste) == attendu, _j.texte(liste))
    verifier("un jour seul ne change pas",
             _j.texte(["2026-08-15"]) == "samedi 15 août 2026", _j.texte(["2026-08-15"]))
    verifier("trois jours contigus se nomment un par un",
             _j.texte(["2026-08-10", "2026-08-11", "2026-08-12"])
             == "lundi 10, mardi 11 et mercredi 12 août 2026",
             _j.texte(["2026-08-10", "2026-08-11", "2026-08-12"]))
    verifier("deux journees isolees gardent leur « et »",
             _j.texte(["2026-08-15", "2026-08-22"])
             == "samedi 15 et samedi 22 août 2026",
             _j.texte(["2026-08-15", "2026-08-22"]))
    verifier("deux jours disperses non plus",
             _j.texte(["2026-08-15", "2026-08-22"])
             == "samedi 15 et samedi 22 août 2026",
             _j.texte(["2026-08-15", "2026-08-22"]))

    print("    une session ancienne, sans modules ranges, s'apparie quand meme")
    a = _j.modules_depuis_jours(r["jours"], modules)
    verifier("cinq venues appariees", len(a["modules"]) == 5)
    verifier("aux bons intitules", a["modules"][2]["titre"]
             == "Restaurations antérieures en céramique", a["modules"][2]["titre"])
    verifier("et rien a signaler", a["souci"] == "", a["souci"])
    b = _j.modules_depuis_jours(["2027-01-06", "2027-01-07"], modules)
    verifier("un desaccord de comptes est DIT, pas devine",
             "1 venue(s)" in b["souci"] and "5 module(s)" in b["souci"], b["souci"])

    print("    le resume d'une fiche porte les modules ranges")
    fiche = {"jours": r["jours"], "modules": r["modules"]}
    res = _j.resume(fiche)
    verifier("quinze journees, 105 heures", res["nb"] == 15 and res["duree"] == 105)
    verifier("cinq venues", len(res["blocs"]) == 5)
    verifier("et la balise toute prete", res["modules_texte"].count("\n") == 4)
    ancienne = _j.resume({"jours": ["2027-02-04", "2027-02-05"]})
    verifier("une fiche sans modules n'en invente pas",
             ancienne["modules"] == [] and ancienne["modules_texte"] == "")


def tests_balises_du_cycle():
    """{{modules}} et {{nb_journees}} : remplies pour un cycle, vides sinon.

    Le meme modele de courriel doit servir une session de deux jours et un
    cycle de quinze : c'est la fiche de session qui change, pas le texte.
    """
    import jours as _j
    import mails as _m
    print()
    print("  LES BALISES DU CYCLE")

    print("    un nombre de journees s'ecrit en lettres, au feminin")
    for n, attendu in ((1, "une"), (2, "deux"), (15, "quinze"), (20, "vingt"),
                       (21, "vingt et une"), (23, "vingt-trois"), (30, "trente")):
        verifier("%d → %s" % (n, attendu), _j.en_lettres(n) == attendu, _j.en_lettres(n))
    verifier("au-dela de trente, le chiffre", _j.en_lettres(45) == "45", _j.en_lettres(45))
    verifier("et rien d'illisible", _j.en_lettres("x") == "", "[%s]" % _j.en_lettres("x"))

    modules = [{"titre": "Essentiels", "jours": 3}, {"titre": "Composites", "jours": 3}]
    r = _j.depuis_modules(modules, ["2027-01-06", "2027-03-10"])

    print("    une session de cycle remplit les deux balises")
    S = {"jours": r["jours"], "modules": r["modules"], "nom_formation": "Esthetique 360",
         "titre_complet": "Esthétique 360", "date_texte": _j.texte(r["jours"]),
         "adresse": "61 rue Balard, 75015 Paris", "tarif": "6000",
         "organisme": "mon-organisme", "marque": "Smileclub Formations"}
    d = _m._jours_de(S)
    verifier("nb_journees en lettres", d.get("nb_journees") == "six", d.get("nb_journees"))
    verifier("deux modules, un par ligne",
             d.get("modules", "").count("<br>") == 1, d.get("modules", "")[:60])
    verifier("l'intitule est en gras",
             "<b>1 · Essentiels</b>" in d.get("modules", ""), d.get("modules", "")[:40])
    verifier("et sa date suit",
             "mercredi 6, jeudi 7 et vendredi 8 janvier 2027" in d.get("modules", ""))

    print("    une session ordinaire les laisse vides, sans rien casser")
    d2 = _m._jours_de({"jours": ["2027-02-04", "2027-02-05"]})
    verifier("aucun module", d2.get("modules") == "", "[%s]" % d2.get("modules"))
    verifier("mais le reste est la", d2.get("nb_jours") == "2", d2.get("nb_jours"))
    verifier("et le nombre en lettres aussi", d2.get("nb_journees") == "deux",
             d2.get("nb_journees"))
    verifier("une fiche sans journees ne leve pas", _m._jours_de({}) == {})

    print("    le lieu en abrege, pour les phrases")
    # mails.contexte() est la fonction meme qu'un vrai envoi appelle.
    c = _m.contexte({"adresse": "61 rue Balard - 75015 Paris",
                     "lieu_court": "Paris 15e (61 rue Balard)"})
    verifier("{{lieu}} garde l'adresse complete",
             c.get("lieu") == "61 rue Balard - 75015 Paris", c.get("lieu"))
    verifier("{{lieu_court}} porte la forme courte",
             c.get("lieu_court") == "Paris 15e (61 rue Balard)", c.get("lieu_court"))
    c2 = _m.contexte({"adresse": "12 rue des Lilas, 75011 Paris"})
    verifier("sans forme courte, l'adresse complete est reprise",
             c2.get("lieu_court") == "12 rue des Lilas, 75011 Paris", c2.get("lieu_court"))
    verifier("et une fiche sans lieu du tout ne leve pas",
             _m.contexte({}).get("lieu_court") == "",
             "[%s]" % _m.contexte({}).get("lieu_court"))

    print("    les balises sont proposees dans l'editeur de modeles")
    plates = [c for _groupe, items in _m.BALISES for c, _l, _e in items]
    verifier("{{modules}} est offerte", "modules" in plates)
    verifier("{{nb_journees}} aussi", "nb_journees" in plates)
    verifier("{{lieu_court}} aussi", "lieu_court" in plates)


def tests_jalon_validation():
    """LE JALON DE VALIDATION — 24/10/2026, pour Esthetique 360.

    Une demande d'inscription n'est pas une inscription : elle attend d'etre
    validee a la main, et c'est a ce moment que le prix de la personne est
    arrete. Ce qui doit tenir : une demande apparait mais n'occupe pas de
    place, ne recoit ni convention ni convocation ni attestation, et une ligne
    ecrite avant ce jour ne peut pas basculer dans ce statut.
    """
    import suivi as _sv
    print()
    print("  LE JALON DE VALIDATION")
    vide = {c: "" for c in _sv.COL}

    print("    le statut se lit sur la ligne, pas sur un reglage")
    verifier("une ligne ordinaire reste « A contacter »",
             _sv.calculer_statut(dict(vide)) == "A contacter",
             _sv.calculer_statut(dict(vide)))
    d = dict(vide, a_valider_le="24/10/2026 08:00")
    verifier("marquee a valider, elle l'est",
             _sv.calculer_statut(d) == "Demande à valider", _sv.calculer_statut(d))
    v = dict(d, valide_le="24/10/2026 09:00")
    verifier("validee, elle reprend le circuit normal",
             _sv.calculer_statut(v) == "A contacter", _sv.calculer_statut(v))
    verifier("une annulation passe devant",
             _sv.calculer_statut(dict(d, annule_le="x")) == "Annulee")
    verifier("la file d'attente aussi",
             _sv.calculer_statut(dict(d, file_attente_le="x")) == "File d'attente")

    print("    une demande n'occupe pas de place")
    verifier("elle est dans PAS_ENCORE_INSCRIT",
             "Demande à valider" in _sv.PAS_ENCORE_INSCRIT, str(_sv.PAS_ENCORE_INSCRIT))
    verifier("la file d'attente y est toujours",
             "File d'attente" in _sv.PAS_ENCORE_INSCRIT)

    print("    ni convention, ni convocation, ni attestation")
    for fichier, ce_que_c_est in (("generer_convention_apercu.py", "la convention"),
                                  ("envoyer_rappel.py", "la convocation J-20"),
                                  ("generer_attestations.py", "l'attestation")):
        texte = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), fichier), encoding="utf-8").read()
        verifier("%s ecarte les demandes" % ce_que_c_est,
                 "PAS_ENCORE_INSCRIT" in texte, fichier)
    texte = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "envoyer_mail_signature.py"), encoding="utf-8").read()
    verifier("le mail 1 ne part qu'aux « A contacter »",
             'calculer_statut(l) == "A contacter"' in texte)

    print("    l'import ne marque que si la formation l'exige")
    _isoler()
    import importer_demandes as imp
    import inscription as I
    import invitations as inv
    import sessions as _s
    import suivi

    fiche = dict(FICHE)
    _s.SESSIONS[fiche["code"]] = dict(fiche)
    _s.session = lambda c=None: dict(fiche)
    _s.etat = lambda c=None: {"statut_session": "ouverte"}
    suivi.session = lambda c=None: dict(fiche)
    suivi.rafraichir_statuts = lambda *a, **k: None
    I.marquer_importee = lambda ident: None
    inv.FICHIER = os.path.join(tempfile.mkdtemp(prefix="dfm-inv-"), "invitations.json")

    # Formation SANS validation : rien ne change, c'est le cas de toutes
    # celles qui existaient avant le 24/10/2026.
    _s.FORMATIONS["essai"] = {"nom_formation": "Essai", "tarif": "975"}
    fiche["formation"] = "essai"
    imp.traiter(fiche["code"], [_demande("SANS", "Paul", "paul@essai.test", ident=1)])
    l = [x for x in suivi.lire_lignes_de(fiche["code"]) if x["nom"] == "SANS"]
    verifier("sans le reglage, la ligne n'est pas marquee",
             l and not l[0]["a_valider_le"], l[0]["a_valider_le"] if l else "pas de ligne")
    verifier("et son statut est celui d'avant",
             l and suivi.calculer_statut(l[0]) == "A contacter",
             suivi.calculer_statut(l[0]) if l else "")

    # Formation AVEC validation.
    _s.FORMATIONS["essai"]["validation_manuelle"] = True
    imp.traiter(fiche["code"], [_demande("AVEC", "Lea", "lea@essai.test", ident=2)])
    l2 = [x for x in suivi.lire_lignes_de(fiche["code"]) if x["nom"] == "AVEC"]
    verifier("avec le reglage, la ligne est marquee",
             l2 and l2[0]["a_valider_le"], l2[0]["a_valider_le"] if l2 else "pas de ligne")
    verifier("et son statut est « Demande à valider »",
             l2 and suivi.calculer_statut(l2[0]) == "Demande à valider",
             suivi.calculer_statut(l2[0]) if l2 else "")
    verifier("le montant propose reste le tarif de la session",
             l2 and l2[0]["montant_du"] == "975", l2[0]["montant_du"] if l2 else "")
    verifier("la ligne precedente n'a pas bouge",
             not [x for x in suivi.lire_lignes_de(fiche["code"])
                  if x["nom"] == "SANS" and x["a_valider_le"]])

    print("    une demande se voit des la page d'accueil")
    for fichier, ce_qu_on_cherche, pourquoi in (
            ("donnees.py", '"a_valider": sum(', "le compte est agrege"),
            ("donnees.py", '"qui_a_valider"', "et les noms avec, pour que l'alerte mene quelque part"),
            ("templates/dashboard.html", "g.alertes.a_valider", "le bandeau l'affiche")):
        texte = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), fichier),
                     encoding="utf-8").read()
        verifier(pourquoi, ce_qu_on_cherche in texte, fichier)

    print("    le prix d'un invite est zero, celui d'un autre est ce qu'on a dit")
    verifier("un invite ne doit rien",
             _sv.montant_attendu(dict(vide, invite_le="x", montant_du="6000"), "6000") == 0.0)
    verifier("un prix arrete est respecte",
             _sv.montant_attendu(dict(vide, montant_du="4500"), "6000") == 4500.0)
    verifier("sans prix arrete, le tarif de la session fait foi",
             _sv.montant_attendu(dict(vide), "6000") == 6000.0)


def tests_fonction_par_defaut():
    """Une fonction manquante vaut « Chirurgien-dentiste » — regle du 24/10/2026.

    ELLE REVIENT SUR CELLE DU 22/08/2026, qui faisait refuser la convention.
    Le motif du revirement et le risque qu'il laisse sont ecrits dans
    contacts.fonction_ou_defaut ; ici on verifie seulement que la regle
    s'applique PARTOUT de la meme facon, et qu'elle n'ecrase jamais une
    fonction renseignee.
    """
    import contacts as _C
    print()
    print("  LA FONCTION PAR DEFAUT")

    print("    la regle, en un seul endroit")
    for brut, attendu, quoi in (("", "Chirurgien-dentiste", "une case vide"),
                                (None, "Chirurgien-dentiste", "une case absente"),
                                ("   ", "Chirurgien-dentiste", "des espaces"),
                                ("\n\t", "Chirurgien-dentiste", "un retour a la ligne")):
        verifier("%s vaut chirurgien-dentiste" % quoi,
                 _C.fonction_ou_defaut(brut) == attendu, _C.fonction_ou_defaut(brut))
    print("    et elle n'ecrase JAMAIS une reponse donnee")
    for brut in ("Assistant-e dentaire", "Assistant(e) dentaire",
                 "Étudiant-e en chirurgie dentaire", "Employé cadre"):
        verifier("« %s » est conservee" % brut[:28],
                 _C.fonction_ou_defaut(brut) == brut, _C.fonction_ou_defaut(brut))
    verifier("les espaces autour sont retires",
             _C.fonction_ou_defaut("  Assistant-e dentaire  ") == "Assistant-e dentaire")

    print("    la convention ne refuse plus, elle applique le defaut")
    ici = os.path.dirname(os.path.abspath(__file__))
    conv = open(os.path.join(ici, "convention.py"), encoding="utf-8").read()
    verifier("le refus cote individuel a disparu",
             "La fonction de %s n'est pas renseignée" not in conv)
    verifier("le refus cote session client aussi",
             "La fonction n'est pas renseignée pour" not in conv)
    verifier("les deux chemins passent par la regle commune",
             conv.count("fonction_ou_defaut") >= 2,
             "%d appel(s)" % conv.count("fonction_ou_defaut"))

    print("    et elle se pose A L'ENTREE, pour se voir et se corriger a l'ecran")
    for fichier in ("importer_demandes.py", "importer_inscriptions.py"):
        texte = open(os.path.join(ici, fichier), encoding="utf-8").read()
        verifier("%s l'ecrit sur la ligne" % fichier,
                 "fonction_ou_defaut" in texte, fichier)

    print("    la CSP deduite reste muette sur une fonction inconnue")
    verifier("un chirurgien-dentiste est cadre",
             _C.csp("Chirurgien-dentiste") == "Cadre", _C.csp("Chirurgien-dentiste"))
    verifier("une fonction vide ne donne AUCUNE csp",
             _C.csp("") == "", "[%s]" % _C.csp(""))


def tests_convention_du_cycle():
    """La convention d'un cycle : un seul gabarit, des blocs qui s'allument.

    LA CONDITION POSEE AU CADRAGE DU 23/10/2026 : pas de second modele. Deux
    textes seraient deux clauses a tenir d'accord, et le jour ou l'on corrige
    une phrase on n'en corrigerait qu'une. Ce qui doit tenir : « cycle » est
    vrai quand la SESSION porte ses modules, faux partout ailleurs — donc
    jamais pour une session ecrite avant ce jour.
    """
    import convention as _cv
    import jours as _j
    print()
    print("  LA CONVENTION DU CYCLE")

    print("    un montant s'ecrit comme sur un acte")
    for v, attendu in ((0, "0"), (975, "975"), (999, "999"),
                       (6000, "6\u202f000"), (12500, "12\u202f500"),
                       (1234.5, "1\u202f234,50")):
        verifier("%s → %s" % (v, attendu.replace("\u202f", " ")),
                 _cv._euros(v) == attendu, repr(_cv._euros(v)))
    verifier("et sous mille euros, rien ne change",
             all(_cv._euros(v) == "%d" % v for v in (0, 1, 540, 975, 999)))
    verifier("un montant illisible ne fait pas tomber la convention",
             _cv._euros("abc") == "abc", _cv._euros("abc"))

    print("    « cycle » se lit sur la session, et sur elle seule")
    modules = [{"titre": "Essentiels", "jours": 3}, {"titre": "Composites", "jours": 3}]
    r = _j.depuis_modules(modules, ["2027-01-06", "2027-03-10"])
    cyc = _cv._commun({"jours": r["jours"], "modules": r["modules"],
                       "titre_complet": "Cycle", "horaires": "9h-17h"})
    verifier("une session a modules est un cycle", cyc["cycle"] is True)
    verifier("deux modules comptes", cyc["nb_modules"] == 2, cyc["nb_modules"])
    verifier("trois journees par module", cyc["jours_par_module"] == 3,
             cyc["jours_par_module"])
    verifier("six journees, en lettres", cyc["nb_journees_lettres"] == "six",
             cyc["nb_journees_lettres"])
    ord_ = _cv._commun({"jours": ["2027-02-04", "2027-02-05"], "titre_complet": "Usures"})
    verifier("UNE SESSION ORDINAIRE N'EST PAS UN CYCLE", ord_["cycle"] is False)
    verifier("et ne porte aucun module", ord_["modules"] == [], str(ord_["modules"]))
    verifier("une session sans journees non plus",
             _cv._commun({"titre_complet": "x"})["cycle"] is False)
    print("    des modules de durees differentes ne mentent pas sur le compte")
    r2 = _j.depuis_modules([{"titre": "A", "jours": 3}, {"titre": "B", "jours": 2}],
                           ["2027-01-06", "2027-03-10"])
    c2 = _cv._commun({"jours": r2["jours"], "modules": r2["modules"]})
    verifier("« de N journees » est tu quand elles diffèrent",
             c2["jours_par_module"] == 0, c2["jours_par_module"])

    print("    le prix est celui de la PERSONNE, pas de la session")
    ici = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(ici, "convention.py"), encoding="utf-8").read()
    verifier("la convention passe par suivi.montant_attendu",
             "montant_attendu(ligne" in src)
    # LA SESSION CLIENT, ELLE, GARDE LE TARIF DE LA SESSION : une structure
    # achete la formation au prix unitaire fois le nombre de participants. Ce
    # n'est pas le meme acte, et les deux sessions client en service ne doivent
    # pas changer d'un caractere.
    verifier("la session client garde le prix unitaire de la session",
             'unitaire = _nombre(S.get("tarif"))' in src)
    verifier("et son total n'est pas reformate",
             '"tarif": "%.0f" % unitaire' in src or '"%.0f" % total' in src,
             "le total client garde son format")

    print("    le gabarit garde UN SEUL texte pour les deux cas")
    tpl = open(os.path.join(ici, "templates", "convention.html"), encoding="utf-8").read()
    verifier("les clauses du cycle sont conditionnelles",
             tpl.count("c.cycle") >= 8, "%d mentions" % tpl.count("c.cycle"))
    for phrase, ou in (("l'employeur", "article 4 des autres formations"),
                       ("Pour le Client", "le cartouche des autres formations"),
                       ("au plus tard 20 jours", "article 7 des autres formations"),
                       ("Une première partie théorique", "article 5 des autres formations")):
        verifier("%s est conservee" % ou, phrase in tpl, phrase)
    for phrase, ou in (("cycle annuel composé de", "article 1"),
                       ("les deux tiers du temps", "article 2"),
                       ("sans entrer dans ce décompte", "article 2"),
                       ("trente jours à l'avance", "article 2"),
                       ("Conditions matérielles", "article 3"),
                       ("déjeuners\n      et dîners", "article 4"),
                       ("à solder avant le début du dernier module", "article 4"),
                       ("ses propres cas cliniques", "article 5"),
                       ("attestation de présence", "article 6"),
                       ("lien de paiement sécurisé", "article 7"),
                       ("plus de vingt jours francs", "article 8"),
                       ("force majeure", "article 8"),
                       ("Le Stagiaire", "le cartouche")):
        verifier("le texte du cycle est la (%s)" % ou, phrase in tpl, phrase[:34])


def tests_versements():
    """PLUSIEURS VERSEMENTS SUR UNE MEME LIGNE — 25/10/2026, pour Esthetique 360.

    DFM n'acceptait QU'UN reglement par personne : quatre cases, et un refus
    pour le second. Un cycle d'un an a 6 000 euros se regle en plusieurs
    virements.

    CE QUI DOIT TENIR, ET C'EST TOUT L'ENJEU : les inscrits des formations
    courtes ne doivent rien voir changer. Leur cellule de versements est vide,
    mais leurs quatre cases sont remplies — DFM doit leur reconstituer un
    versement unique sans qu'on ait rien reecrit chez eux.
    """
    import suivi as _sv
    print()
    print("  LES VERSEMENTS")
    vide = {c: "" for c in _sv.COL}
    # une ligne arrivee jusqu'a l'etape du reglement
    pret = dict(vide, mail1_envoye_le="x", signe_le="x", convention_pdf_le="x",
                mail2_envoye_le="x")

    print("    un montant saisi se lit comme un nombre")
    for brut, attendu in (("975", 975.0), ("6 000", 6000.0), ("2 000,00 €", 2000.0),
                          ("1234.5", 1234.5), ("", 0.0), ("beaucoup", 0.0)):
        verifier("« %s » vaut %g" % (brut, attendu),
                 _sv.euros(brut) == attendu, _sv.euros(brut))

    print("    une ligne d'AVANT retrouve son versement unique")
    ancien = dict(pret, montant_du="975", montant_recu="975",
                  paiement_recu_le="12/10/2026", mode_paiement="Virement",
                  reference_paiement="USURES-NOV26-DUPONT")
    v = _sv.versements(ancien)
    verifier("un seul versement", len(v) == 1, len(v))
    verifier("avec son montant", v[0]["montant"] == "975", v[0])
    verifier("sa date", v[0]["le"] == "12/10/2026", v[0])
    verifier("et son mode", v[0]["mode"] == "Virement", v[0])
    verifier("sans cellule de versements", not ancien["versements"])
    verifier("le total est le sien", _sv.total_verse(ancien) == 975.0)
    verifier("elle ne doit plus rien", _sv.solde(ancien) == 0.0)
    verifier("et son statut n'a pas bouge",
             _sv.calculer_statut(ancien) == "Reglee", _sv.calculer_statut(ancien))

    print("    une ligne qui n'a rien paye n'invente pas de versement")
    verifier("aucun versement", _sv.versements(dict(pret)) == [])
    verifier("le statut est celui d'avant",
             _sv.calculer_statut(dict(pret, montant_du="975")) == "En attente reglement",
             _sv.calculer_statut(dict(pret, montant_du="975")))

    print("    trois virements s'ecrivent et se relisent")
    trois = [{"le": "12/01/2027", "montant": "2000", "mode": "Virement",
              "reference": "VIR-0042", "recu": "https://essai.test/r1.pdf"},
             {"le": "15/03/2027", "montant": "2 000,00 €", "mode": "Virement",
              "reference": "VIR-0109", "recu": ""},
             {"le": "02/06/2027", "montant": "1500", "mode": "Carte",
              "reference": "", "recu": ""}]
    cellule = _sv.versements_texte(trois)
    verifier("une ligne par virement", cellule.count("\n") == 2, repr(cellule))
    cycle = dict(pret, montant_du="6000", versements=cellule)
    relu = _sv.versements(cycle)
    verifier("les trois reviennent", len(relu) == 3, len(relu))
    verifier("dans l'ordre", [x["le"] for x in relu] == [x["le"] for x in trois], relu)
    verifier("le recu du premier est garde",
             relu[0]["recu"] == "https://essai.test/r1.pdf", relu[0])
    verifier("5 500 encaisses", _sv.total_verse(cycle) == 5500.0, _sv.total_verse(cycle))
    verifier("il reste 500", _sv.solde(cycle) == 500.0, _sv.solde(cycle))
    verifier("le statut dit « Reglement partiel »",
             _sv.calculer_statut(cycle) == "Reglement partiel",
             _sv.calculer_statut(cycle))

    print("    une reference ne peut pas couper la ligne")
    sale = _sv.versements_texte([{"le": "01/01/2027", "montant": "100",
                                  "mode": "Virement",
                                  "reference": "A | B\nC", "recu": ""}])
    verifier("le « | » de trop est neutralise", sale.count("|") == 4, repr(sale))
    verifier("et le retour a la ligne aussi", "\n" not in sale, repr(sale))
    verifier("le versement se relit entier",
             len(_sv.versements(dict(pret, versements=sale))) == 1, repr(sale))

    print("    le dernier virement solde, et le statut suit")
    solde_ = dict(cycle, paiement_recu_le="20/09/2027",
                  versements=_sv.versements_texte(
                      trois + [{"le": "20/09/2027", "montant": "500",
                                "mode": "Virement", "reference": "VIR-0311",
                                "recu": ""}]))
    verifier("6 000 encaisses", _sv.total_verse(solde_) == 6000.0)
    verifier("plus rien a payer", _sv.solde(solde_) == 0.0)
    verifier("« Reglee »", _sv.calculer_statut(solde_) == "Reglee",
             _sv.calculer_statut(solde_))

    print("    un invite ne doit rien, meme si un versement est saisi")
    inv = dict(cycle, invite_le="24/10/2026")
    verifier("son solde est nul", _sv.solde(inv) == 0.0, _sv.solde(inv))
    verifier("et son statut reste « Invitee »",
             _sv.calculer_statut(inv) == "Invitee", _sv.calculer_statut(inv))

    print("    un trop-percu ne fabrique pas une dette a rebours")
    trop = dict(pret, montant_du="975",
                versements=_sv.versements_texte([{"le": "01/01/2027", "montant": "1000",
                                                  "mode": "Virement", "reference": "",
                                                  "recu": ""}]))
    verifier("le solde ne passe pas sous zero", _sv.solde(trop) == 0.0, _sv.solde(trop))

    print("    les ecrans comptent les acomptes, et les prix de chacun")
    ici = os.path.dirname(os.path.abspath(__file__))
    source = open(os.path.join(ici, "donnees.py"), encoding="utf-8").read()
    resume = source[source.index("def _resume("):]
    resume = resume[:resume.index("\ndef ")]
    verifier("l'encaisse passe par total_verse", "total_verse(l)" in resume)
    verifier("elle ne se limite plus aux lignes soldees",
             'if l["paiement_recu_le"]:' not in resume)
    verifier("la fiche d'un praticien compte ses acomptes aussi",
             'p["total_paye"] += __import__("suivi").total_verse(l)' in source)
    verifier("l'attendu est la somme des montants dus",
             "montant_attendu" in source and "len(payants) * tarif" not in source)

    print("    la saisie accepte un versement de plus, et en retire un seul")
    app_ = open(os.path.join(ici, "app.py"), encoding="utf-8").read()
    bloc = app_[app_.index("def enregistrer_reglement("):]
    bloc = bloc[:bloc.index("@app.route", 10)]
    # On cherche le REFUS, pas la phrase : le commentaire de la route cite
    # encore l'ancien message pour dire ce qui a change, et c'est voulu.
    verifier("le refus du second reglement a disparu",
             'message": "Un reglement est deja enregistre' not in bloc)
    verifier("elle ajoute a la liste", "liste.append(" in bloc)
    verifier("montant_recu porte le total", '"%g" % verse' in bloc)
    verifier("paiement_recu_le n'est pose qu'au solde",
             "if solde <= 0:" in bloc and 'cible["paiement_recu_le"] = quand' in bloc)
    corr = app_[app_.index("def corriger_reglement("):]
    corr = corr[:corr.index("def _grilles_suivi(")]
    verifier("la correction designe un rang", '"rang"' in corr)
    verifier("et ne vide plus les quatre cases d'un coup",
             'vides = ["montant_recu"' not in corr)

    print("    le recu d'un versement")
    import recu as _recu
    S = {"tarif": "6000", "adresse": "61 rue Balard - 75015 Paris",
         "jours": ["2027-01-06", "2027-01-07"], "nom_formation": "Essai",
         "titre_complet": "Essai", "organisme": "mon-organisme",
         "mail_contact": "contact@essai.test"}
    d = _recu.pour(S, "R-ESS-DURAND-2", "Camille DURAND",
                   {"le": "15/03/2027", "montant": "2000", "mode": "Virement",
                    "reference": "VIR-0109"}, 4000.0, 6000.0, civilite="Docteur ")
    verifier("il porte le montant de CE versement",
             d["unitaire"] == "2 000", repr(d["unitaire"]))
    verifier("ce qui est verse en tout", d["verse"] == "4 000", repr(d["verse"]))
    verifier("et ce qu'il reste", d["reste"] == "2 000", repr(d["reste"]))
    fini = _recu.pour(S, "R-ESS-DURAND-3", "Camille DURAND",
                      {"le": "20/09/2027", "montant": "2000", "mode": "Virement",
                       "reference": ""}, 6000.0, 6000.0)
    verifier("un compte solde ne porte PAS de reste", fini["reste"] == "",
             repr(fini["reste"]))
    import documents as _doc
    verifier("le recu a une categorie de rangement", "recu" in _doc.CATEGORIES)

    print("    la facture peut preceder le reglement, sur reglage seulement")
    gen = open(os.path.join(ici, "generer_factures.py"), encoding="utf-8").read()
    verifier("le reglage existe", "facture_a_l_inscription" in gen)
    verifier("sans lui, la selection d'avant est intacte",
             'l["paiement_recu_le"] and not l["facture_le"]' in gen)
    verifier("avec lui, elle part a la convention signee",
             'l["signe_le"] and not l["facture_le"]' in gen)
    verifier("et porte la somme entiere", "montant_attendu" in gen)
    verifier("sans bloc « acquittee »", "À régler avant le début" in gen)
    verifier("un invite n'est jamais facture", 'not l.get("invite_le")' in gen)
    verifier("le reglage est sur la fiche",
             '"facture_a_l_inscription": bool(' in app_)
    ecran = open(os.path.join(ici, "templates", "formation_creer.html"),
                 encoding="utf-8").read()
    verifier("et a l'ecran", 'name="facture_a_l_inscription"' in ecran)


def tests_relances_en_modeles():
    """LES DEUX RELANCES SONT DEVENUES DES MODELES — 25/10/2026.

    Elles etaient les seuls courriers de DFM ecrits en dur : quatre-vingt-dix
    lignes de HTML dans app.py. Trois consequences, et c'est chacune d'elles
    que ce test garde :

      — ON NE POUVAIT PAS LES MODIFIER a l'ecran, alors que les neuf autres
        mails se modifient ;
      — ELLES PORTAIENT L'ANCIEN EN-TETE, celui d'avant le filet irise ;
      — ELLES ANNONCAIENT LE TARIF DE LA SESSION et non le prix convenu avec
        la personne. Pour un cycle ou chacun paie son prix, c'est faux.

    ET LE PIEGE QUI RESTE : la relance de reglement ne doit JAMAIS partir a
    quelqu'un qu'on invite. « _rel_type » l'ecarte, et c'est la seule chose qui
    l'en empeche — un invite force dans ce mail s'y verrait reclamer 0 euro.
    """
    import mails as _m
    print()
    print("  LES DEUX RELANCES, DEVENUES DES MODELES")

    print("    elles existent comme usages, avec un texte fourni")
    for usage, nom in (("relance_signature", "Relance de signature"),
                       ("relance_reglement", "Relance de règlement")):
        verifier("l'usage « %s » existe" % usage, usage in _m.USAGES)
        verifier("il s'appelle « %s »" % nom,
                 (_m.USAGES.get(usage) or {}).get("nom") == nom)
        verifier("et DFM en fournit un texte", bool(_m.defaut(usage)))

    print("    la relance se construit depuis un modele, et plus a la main")
    source = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"),
                  encoding="utf-8").read()
    bloc = source[source.index("def _mail_relance("):]
    bloc = bloc[:bloc.index("\n@app.route")]
    verifier("elle passe par pour_formation", "pour_formation(" in bloc)
    verifier("et par l'enveloppe commune", "mails.rendre(" in bloc)
    verifier("plus aucun <table> ecrit a la main", "<table" not in bloc, bloc[:0])

    print("    le montant annonce est celui de LA PERSONNE")
    S = {"tarif": "6000", "adresse": "61 rue Balard - 75015 Paris",
         "jours": ["2027-01-06", "2027-01-07"], "nom_formation": "Essai",
         "mail_contact": "contact@essai.test"}
    c_pers = _m.contexte(S, {"prenom": "Camille", "montant_du": "5500"})
    c_sans = _m.contexte(S, {"prenom": "Camille", "montant_du": ""})
    c_inv = _m.contexte(S, {"prenom": "Camille", "invite_le": "24/10/2026"})
    verifier("un prix convenu passe devant le tarif",
             c_pers["tarif"] == "5\u202f500", repr(c_pers["tarif"]))
    verifier("un montant vide retombe sur le tarif de la session",
             c_sans["tarif"] == "6\u202f000", repr(c_sans["tarif"]))
    verifier("un invite ne doit rien", c_inv["tarif"] == "0", repr(c_inv["tarif"]))

    print("    les deux textes fournis partent sans balise oubliee")
    for usage in ("relance_signature", "relance_reglement"):
        r = _m.rendre(_m.pour_formation("", usage),
                      _m.contexte(S, {"prenom": "Camille", "montant_du": "5500"},
                                  {"lien_signature": "https://essai.test/s",
                                   "lien_annulation": "https://essai.test/a"}))
        verifier("%-18s aucune balise oubliee" % usage,
                 "{{" not in r["html"] and "}}" not in r["html"])
        verifier("%-18s son objet est accentue" % usage,
                 "a signer" not in r["objet"] and "Reglement" not in r["objet"],
                 r["objet"])

    print("    l'IBAN est un vrai cadre, et non une ligne de texte")
    blocs = _m.pour_formation("", "relance_reglement")["blocs"]
    cadres = [b for b in blocs if b.get("type") == "encadre" and "IBAN" in str(b.get("contenu"))]
    verifier("un bloc « encadre » porte l'IBAN", len(cadres) == 1, str(len(cadres)))
    verifier("au ton bleu, celui des cadres informatifs",
             (cadres[0].get("ton") if cadres else "") == "bleu")
    verifier("avec le BIC et le motif",
             all(x in cadres[0].get("contenu", "") for x in ("{{bic}}", "Motif")))

    print("    un invite n'est jamais relance pour un reglement")
    bloc_t = source[source.index("def _rel_type("):]
    bloc_t = bloc_t[:bloc_t.index("def _mail_relance(")]
    verifier("seuls deux statuts ouvrent une relance",
             bloc_t.count("if st ==") == 2, bloc_t)
    verifier("tout le reste n'en ouvre aucune", 'return ""' in bloc_t)
    verifier("« En attente reglement » en est un",
             "En attente reglement" in bloc_t)
    import suivi as _sv
    inv = dict({c: "" for c in _sv.COL}, invite_le="24/10/2026",
               convention_signee_le="20/10/2026")
    verifier("le statut d'un invite n'est aucun des deux",
             _sv.calculer_statut(inv) not in ("En attente signature",
                                              "En attente reglement"),
             _sv.calculer_statut(inv))

    print("    la relance du questionnaire est un usage a part entiere")
    verifier("l'usage existe", "relance-inscription" in _m.USAGES)
    verifier("DFM en fournit un texte", bool(_m.defaut("relance-inscription")))
    r = _m.rendre(_m.pour_formation("", "relance-inscription"),
                  _m.contexte({"nom_formation": "Essai", "adresse": "x",
                               "date_limite": "2026-11-07", "jours": ["2027-01-06"],
                               "code": "essai", "site": ""},
                              {"prenom": "Camille"}))
    verifier("il part sans balise oubliee",
             "{{" not in r["html"] and "}}" not in r["html"])
    verifier("et il vouvoie, comme les autres textes fournis",
             "votre" in r["html"].lower() and "ton questionnaire" not in r["html"].lower())
    envoi = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "envoyer_validation_cycle.py"), encoding="utf-8").read()
    verifier("le script sait l'envoyer", '"--relance"' in envoi)
    verifier("et ecarte ceux qui ont deja repondu", "_deja_inscrits(" in envoi)
    verifier("un suivi illisible arrete la relance",
             "aucune relance envoyee" in envoi)

    print("    une balise vide emporte sa phrase")
    S2 = {"adresse": "x", "nom_formation": "Essai", "date_limite": "2026-11-07",
          "jours": ["2027-01-06"]}
    avec = _m.rendre({"objet": "o", "blocs": [
        {"type": "texte", "si": "date_limite",
         "contenu": "Réponse attendue avant le {{date_limite}}."}]},
        _m.contexte(S2, {"prenom": "Camille"}))["html"]
    sans = _m.rendre({"objet": "o", "blocs": [
        {"type": "texte", "si": "date_limite",
         "contenu": "Réponse attendue avant le {{date_limite}}."}]},
        _m.contexte(dict(S2, date_limite=""), {"prenom": "Camille"}))["html"]
    verifier("la phrase part quand la session porte la date",
             "Réponse attendue" in avec)
    verifier("elle disparait entierement quand la session n'en porte pas",
             "Réponse attendue" not in sans)
    verifier("et jamais « avant le . »", "avant le ." not in sans)
    inconnu = _m.rendre({"objet": "o", "blocs": [
        {"type": "texte", "si": "coquille", "contenu": "Un paragraphe."}]},
        _m.contexte(S2, {"prenom": "Camille"}))["html"]
    verifier("un « si » qui ne nomme rien garde le bloc", "Un paragraphe." in inconnu)

    print("    l'intitule des courriels peut porter ses accents")
    verifier("sans nom_court, c'est l'intitule court",
             _m.contexte({"nom_formation": "Esthetique 360", "adresse": "x"})["formation"]
             == "Esthetique 360")
    verifier("avec nom_court, c'est lui",
             _m.contexte({"nom_formation": "Esthetique 360", "adresse": "x",
                          "nom_court": "Esthétique 360"})["formation"]
             == "Esthétique 360")
    verifier("et l'intitule court n'a pas bouge",
             '"nom_formation": nom,' in open(os.path.join(
                 os.path.dirname(os.path.abspath(__file__)), "app.py"),
                 encoding="utf-8").read())

    print("    la fiche d'une formation peut porter ses propres relances")
    verifier("le champ est journalise",
             "modele_mail_relance_signature" in source
             and "modele_mail_relance_reglement" in source)
    ecran = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "templates", "formation_creer.html"),
                 encoding="utf-8").read()
    verifier("l'ecran liste les onze mails, et non deux en dur",
             "usages_mail" in ecran and "modele_mail_signature" not in ecran)
    verifier("un champ absent du formulaire n'efface plus rien",
             'if _cle in d:' in source)


def tests_courriel_de_validation():
    """Les balises du courriel 01, et le modele qui s'en sert.

    CE QUI DOIT TENIR : le texte ne porte AUCUNE valeur du cycle 2027. Tout ce
    qui change d'une session a l'autre — dates, lieu, tarif, nombre de modules,
    date limite — passe par une balise remplie depuis la fiche. C'est la regle
    posee par Franck le 23/10/2026 : Esthetique 360 est une formation, pas une
    session, et ce texte doit resservir en 2028.
    """
    import jours as _j
    import mails as _m
    print()
    print("  LE COURRIEL DE VALIDATION")

    modules = [{"titre": "Essentiels", "jours": 3}, {"titre": "Composites", "jours": 3},
               {"titre": "Usures", "jours": 3}]
    r = _j.depuis_modules(modules, ["2027-01-06", "2027-03-10", "2027-05-19"])
    S = {"jours": r["jours"], "modules": r["modules"], "tarif": "6000",
         "adresse": "61 rue Balard - 75015 Paris",
         "lieu_court": "Paris 15e (61 rue Balard)",
         "date_limite": "2026-11-07", "nom_formation": "Esthetique 360",
         "mail_contact": "contact@essai.test",
         "url_signature": "https://essai.test", "code": "essai-cycle27"}
    c = _m.contexte(S, {"prenom": "Camille", "nom": "DURAND"})

    print("    la date limite s'ecrit en lettres, depuis la session")
    verifier("samedi 7 novembre 2026", c["date_limite"] == "samedi 7 novembre 2026",
             c["date_limite"])
    verifier("une session sans date limite rend du vide",
             _m.contexte({"adresse": "x"})["date_limite"] == "",
             "[%s]" % _m.contexte({"adresse": "x"})["date_limite"])

    print("    le nombre de modules aussi, et leur duree")
    verifier("trois modules", c["nb_modules"] == "trois", c["nb_modules"])
    verifier("de trois jours", c["jours_par_module"] == "trois", c["jours_par_module"])
    verifier("neuf journees", c["nb_journees"] == "neuf", c["nb_journees"])
    ord_ = _m.contexte({"jours": ["2027-02-04", "2027-02-05"], "adresse": "x"})
    verifier("une session ordinaire n'annonce aucun module",
             ord_["nb_modules"] == "" and ord_["jours_par_module"] == "",
             "[%s] [%s]" % (ord_["nb_modules"], ord_["jours_par_module"]))

    print("    le tarif porte son separateur de milliers")
    verifier("6 000 et non 6000", c["tarif"] == "6\u202f000", repr(c["tarif"]))
    verifier("975 ne change pas",
             _m.contexte({"tarif": "975", "adresse": "x"})["tarif"] == "975")

    print("    le lien du questionnaire est celui de CETTE session")
    verifier("il mene au formulaire de la session",
             c["lien_inscription"]
             == "https://essai.test/inscription.html?of=mon-organisme&s=essai-cycle27",
             c["lien_inscription"])
    verifier("sans adresse de site, rien plutot qu'un lien mort",
             _m.contexte({"code": "x", "adresse": "y"})["lien_inscription"] == "")

    print("    le renoncement ouvre un message tout pret, nominatif")
    ren = c["lien_renoncer"]
    verifier("c'est un mailto vers l'organisme",
             ren.startswith("mailto:contact@essai.test?"), ren[:40])
    verifier("le nom est dans l'objet, encode",
             "Camille%20DURAND" in ren, ren[:120])
    verifier("et la formation aussi", "Esthetique%20360" in ren)
    verifier("sans adresse de contact, pas de lien mort",
             _m.contexte({"adresse": "x"})["lien_renoncer"] == "")

    print("    le modele existe, et aucune de ses balises n'est inconnue")
    # LE MODELE EST UNE DONNEE, PAS DU CODE. Il vit dans mails.json, que
    # deployer.sh n'envoie pas et qu'une copie fraiche du depot n'a pas. On ne
    # fait donc pas echouer la suite s'il manque : on le dit, et on controle son
    # contenu des qu'il est la — c'est ce controle-la qui a de la valeur.
    m = _m.modele("invitation-inscription-esthetique360-validation")
    if not m:
        print("    (modele absent de cette installation : contrôles de contenu passés)")
    else:
        verifier("le modele est pose dans DFM", True)
        verifier("usage « invitation-inscription »",
                 m.get("usage") == "invitation-inscription", m.get("usage"))
        connues = {x for _g, items in _m.BALISES for x, _l, _e in items}
        texte = " ".join(str(b.get("contenu", "")) + " " + str(b.get("lien", ""))
                         for b in (m.get("blocs") or []))
        import re as _re
        inconnues = sorted(set(_re.findall(r"\{\{([a-z_]+)\}\}", texte)) - connues)
        verifier("toutes ses balises existent dans DFM", not inconnues,
                 ", ".join(inconnues))
        print("    et AUCUNE valeur du cycle 2027 n'est ecrite en dur")
        for interdit in ("2027", "6000", "6 000", "janvier", "Balard",
                         "7 novembre", "cinq modules", "quinze"):
            verifier("« %s » n'est pas dans le texte" % interdit,
                     interdit not in texte, interdit)

    print("    la piece « materiel et prerequis » est un type connu")
    import documents as _d
    verifier("le type existe", "prerequis" in _d.TYPES_DEPOSES)
    verifier("il appartient a la formation",
             _d.TYPES_DEPOSES["prerequis"][0] == "formation")
    verifier("et son champ est nomme", _d.PIECES.get("prerequis") == "prerequis_id")


def main():
    print()
    print("  LES TESTS DE DFM")
    print("  " + "-" * 56)
    for essai in (tests_import, tests_montant_attendu, tests_file_du_classeur,
                  tests_alerte_inscriptions, tests_accuse_reception,
                  tests_connexion_perimee, tests_guet_de_sante,
                  tests_entete_des_mails, tests_formation_modules,
                  tests_reparation_base, tests_garde_fous_de_la_base,
                  tests_session_cycle, tests_balises_du_cycle,
                  tests_jalon_validation, tests_fonction_par_defaut,
                  tests_convention_du_cycle, tests_courriel_de_validation,
                  tests_relances_en_modeles, tests_versements):
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
