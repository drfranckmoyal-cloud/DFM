"""Le planificateur de DFM : ce qui doit se faire tout seul, et quand.

POURQUOI CE MODULE EXISTE. La planification vivait dans deux agents launchd,
c'est-a-dire dans macOS. Le jour ou DFM demenage sur un serveur, ces agents ne
suivent pas. Ce module fait la meme chose DANS DFM, avec la bibliotheque
standard : il tourne partout ou Python tourne.

CE QU'IL FAIT
    - toutes les 10 minutes : le GUETTEUR. Il regarde les sessions client dont
      le dossier attend une signature, interroge Supabase, et si le representant
      a signe, il enchaine facture puis contresignature. Un centre qui signe
      attend dix minutes au lieu de vingt et une heures.
    - deux fois par jour : le PASSAGE COMPLET, celui de dfm.py.

POURQUOI PAS TOUTES LES HEURES. Le passage complet compte 71 etapes et
regenere des documents. Douze fois par jour noieraient le journal. Le guetteur
couvre l'urgent ; le reste peut attendre le prochain passage.

CE QU'IL NE FAIT PAS. Il ne remplace pas l'agent launchd : celui-ci reste comme
FILET, pour reveiller le traitement si DFM est eteint a l'heure dite. Les deux
sont idempotents — chaque etape refuse ce qui est deja fait — donc se marcher
dessus est sans consequence.

UN SEUL FIL, ET IL EST DEMON. Si DFM s'arrete, le fil meurt avec lui : aucun
processus orphelin ne survit au serveur.
"""
import datetime
import os
import subprocess
import sys
import threading

DOSSIER = os.path.dirname(os.path.abspath(__file__))

# Toutes les dix minutes. Assez court pour qu'un client ne s'impatiente pas,
# assez long pour ne pas marteler Supabase.
GUETTEUR_SECONDES = 600

# Les heures du passage complet. Deux fois : le matin avant la journee, et en
# debut d'apres-midi pour ce qui est arrive dans la matinee.
PASSAGE_HEURES = ((8, 30), (13, 30))

# LA SAUVEGARDE, UNE FOIS PAR JOUR. Constate le 19/08/2026 : ni dfm.db — 623
# entrees de journal scelle — ni les documents produits n'etaient sauvegardes.
# Un disque perdu, et la piste d'audit disparaissait avec lui. L'archive pese
# 4,6 Mo, caches exclus : la faire tous les jours ne coute rien.
SAUVEGARDE_HEURE = (19, 30)
SAUVEGARDES_GARDEES = 30

# La chaine client, dans son ordre reel : la facture precede la contresignature
# parce qu'elle voyage en piece jointe de son mail.
CHAINE_CLIENT = ("relever_signature_client.py", "generer_facture_client.py",
                 "generer_convention_client_signee.py")

_journal = []
_dernier_passage = None
_derniere_sauvegarde = None
_arret = threading.Event()


def _noter(texte):
    """Garde une trace en memoire, consultable par l'ecran. Bornee a 200 lignes :
    un journal qui grossit sans fin finit par manger la memoire du serveur."""
    _journal.append({"quand": datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
                     "texte": str(texte)[:300]})
    del _journal[:-200]


def journal():
    return list(reversed(_journal))


def _lancer(script, code=None, delai=300):
    """Un script, isole. Rend (ok, dernieres lignes)."""
    cmd = [sys.executable, script] + ([code] if code else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=DOSSIER, timeout=delai)
    except subprocess.TimeoutExpired:
        return False, ["%s n'a pas rendu la main en %d s." % (script, delai)]
    return r.returncode == 0, [l.rstrip() for l in r.stdout.splitlines() if l.strip()]


def _sessions_en_attente_de_signature():
    """Les sessions client dont le dossier bute sur la signature du representant.

    On lit la FICHE DE SESSION, pas le suivi : dans une session client personne
    ne signe ligne par ligne. Une session dont la convention est partie mais
    dont la signature manque est exactement celle qu'il faut guetter.
    """
    try:
        import sessions as _S
        brutes = _S._charger_json(_S._FICHIER_S) or {}
    except Exception:
        return []
    sortie = []
    for code, f in brutes.items():
        if (f or {}).get("mode") != "client":
            continue
        envoyee = str((f or {}).get("convention_client_envoyee_le") or "").strip()
        signee = str((f or {}).get("convention_client_signee_le") or "").strip()
        renvoyee = str((f or {}).get("convention_client_signee_envoyee_le") or "").strip()
        # Envoyee mais pas encore renvoyee contresignee : il reste du chemin.
        if envoyee and not renvoyee:
            sortie.append((code, bool(signee)))
    return sortie


def _guetter():
    """Un tour de guet. Rend le nombre de dossiers qui ont avance."""
    avances = 0
    for code, deja_signee in _sessions_en_attente_de_signature():
        ok, lignes = _lancer("relever_signature_client.py", code)
        signee_maintenant = any("Signee le" in l or "deja signee" in l.lower() for l in lignes)
        if not signee_maintenant:
            continue
        if not deja_signee:
            _noter("%s : signature relevee." % code)
        # La suite : facture, puis contresignature avec la facture jointe.
        for script in CHAINE_CLIENT[1:]:
            ok, lignes = _lancer(script, code)
            if lignes:
                _noter("%s · %s — %s" % (code, script.replace(".py", ""), lignes[-1][:150]))
        avances += 1
    _guetter_sante()
    avances += _guetter_inscriptions()
    return avances


def _guetter_sante():
    """DFM lit-il encore ses donnees ? — 20/10/2026.

    L'INCIDENT QUI A IMPOSE CE GUET. De 17h00 a 23h40, la base a repondu
    « database disk image is malformed » a chaque lecture : plus un inscrit,
    plus une session a l'ecran. Le fichier etait sain — c'etait la connexion du
    processus qui etait morte — et une relance a tout remis. Mais rien ne l'a
    dit pendant six heures, et c'est Franck qui l'a decouvert en voulant
    travailler.

    Depuis, base.py rouvre une connexion perimee toute seule. Ce guet est la
    pour le cas ou cela ne suffit pas : il LIT, vraiment, toutes les dix
    minutes, et si la lecture echoue il ecrit a Franck.

    IL NE JOURNALISE PAS SON ECHEC : le journal est dans la base. Quand c'est
    la base qui ne repond plus, le mail est le seul chemin qui reste.
    """
    import alerte
    try:
        import base
        inscrits = base.suivi_compte()
        entrees = base.journal_compte()
    except Exception as e:
        _noter("LA BASE NE REPOND PLUS : %s" % str(e)[:120])
        alerte.prevenir(
            "base-illisible",
            "DFM — la base de données ne répond plus",
            ["<b>DFM n'arrive plus à lire ses données.</b> Les inscrits et les "
             "sessions n'apparaissent donc plus à l'écran.",
             "Message de la base&nbsp;: <code>%s</code>" % str(e)[:160],
             "Rien n'est perdu pour autant&nbsp;: les sauvegardes de nuit sont "
             "intactes, et dans la plupart des cas le fichier lui-même est sain — "
             "c'est la connexion du programme qui est à remplacer."],
            quoi_faire="Double-cliquez «&nbsp;7 — Verifier que DFM va bien&nbsp;». "
                       "Si le souci persiste, une relance de DFM suffit presque "
                       "toujours&nbsp;: dites-le-moi.")
        return
    # TOUT VA BIEN : on efface la memoire de l'alerte, pour qu'une rechute
    # reparte tout de suite au lieu d'attendre six heures.
    alerte.oublier("base-illisible")
    # ET ON SURVEILLE LES RECYCLAGES. Un remplacement de connexion de temps en
    # temps est normal apres un deploiement ; une serie dit qu'autre chose
    # abime la base, et cela doit se savoir avant la panne franche.
    try:
        import base
        n = base._RECYCLAGES[0]
    except Exception:
        n = 0
    if n >= 20:
        alerte.prevenir(
            "connexions-recyclees",
            "DFM — la base se coupe et se rouvre souvent",
            ["DFM a du rouvrir sa connexion a la base <b>%d fois</b> depuis son "
             "demarrage. Il s'en remet seul a chaque fois, et rien n'est perdu, "
             "mais cette repetition n'est pas normale." % n,
             "Pour information&nbsp;: %d inscrits et %d entrees de journal se "
             "lisent correctement en ce moment." % (inscrits, entrees)],
            quoi_faire="Rien d'urgent. A me signaler pour que je cherche la cause.",
            heures=24, signature="recyclages")


def _guetter_inscriptions():
    """Les inscriptions du formulaire, toutes les dix minutes — 19/10/2026.

    POURQUOI CE GUET EXISTE. L'import ne tournait qu'aux deux passages
    complets, 8h30 et 13h30. Quelqu'un qui s'inscrivait a 11h56 n'avait donc
    pas de fiche avant 13h30 — et si l'import echouait, il n'y avait pas de
    fiche du tout, pendant des heures, sans que personne le sache. C'est
    arrive : Talia GUEZ, inscrite le 18/10 a 11h56, est restee un jour.

    Une inscription a maintenant AU PIRE DIX MINUTES de retard. Et quand la
    reprise echoue, le controle qui suit previent Franck par mail au lieu
    d'attendre qu'il lise un bandeau.

    ON NE FAIT RIEN S'IL N'Y A RIEN. Un appel a la boite aux lettres, et on
    s'arrete : ni import, ni controle, ni journal. Aucun mail de formation ne
    part d'ici — l'import ne cree que des fiches, les courriers sont d'autres
    etapes, aux passages complets.
    """
    try:
        import inscription as I
        attente = I.en_attente()
    except Exception:
        return 0                      # Supabase injoignable : le passage complet reessaiera
    if not attente:
        return 0
    qui = ", ".join(sorted({((e.get("prenom") or "") + " " + (e.get("nom") or "")).strip()
                            for e in attente})[:4])
    _noter("%d demande(s) d'inscription a reprendre : %s" % (len(attente), qui))
    # D'ABORD DIRE A LA PERSONNE QUE SA DEMANDE EST ARRIVEE. Cet envoi ne
    # depend ni du suivi ni du classeur : il part meme si tout le reste est
    # casse. C'est le seul courrier dont on soit sur.
    ok_ar, lignes_ar = _lancer("accuser_reception.py")
    for l in lignes_ar[-2:]:
        _noter("   %s" % l[:150])
    ok, lignes = _lancer("importer_demandes.py")
    for l in lignes[-3:]:
        _noter("   %s" % l[:150])
    # LE CONTROLE JUSTE APRES, TOUJOURS : c'est lui qui compare ce que le
    # formulaire a recu et ce que le suivi contient, et qui alerte par mail.
    ok_ctrl, lignes_ctrl = _lancer("verifier_inscriptions.py")
    if not ok_ctrl:
        for l in lignes_ctrl[-4:]:
            _noter("   CONTROLE : %s" % l[:150])
    return 1


def _creneau(maintenant, heure, minute):
    """L'etiquette du creneau courant si l'on y est, sinon None.

    ON RAISONNE PAR FENETRE, PAS PAR MINUTE EXACTE. Premiere version : on
    comparait (heure, minute) a 8h30 pile. Or le guetteur se reveille toutes les
    dix minutes — il tombe sur 8h28 ou 8h34, jamais sur 8h30. Le passage complet
    ne serait donc quasiment jamais parti, et personne ne l'aurait vu : un
    rendez-vous manque ne laisse aucune trace.

    La fenetre dure un tour de guet complet, et l'etiquette du jour empeche de
    repasser deux fois dans la meme.
    """
    debut = maintenant.replace(hour=heure, minute=minute, second=0, microsecond=0)
    ecart = (maintenant - debut).total_seconds()
    if 0 <= ecart < GUETTEUR_SECONDES:
        return "%s %02d:%02d" % (maintenant.strftime("%Y-%m-%d"), heure, minute)
    return None


def _sauvegarder():
    """L'archive du jour, et le menage des anciennes."""
    import sauvegarde_locale as _sl
    cible, n = _sl.fabriquer()
    _noter("Sauvegarde : %s (%d fichiers)." % (os.path.basename(cible), n))
    # ON GARDE TRENTE JOURS. Sans menage, une archive quotidienne de 4,6 Mo
    # remplit un disque en quelques annees — et personne ne s'en apercoit avant
    # que l'ecriture echoue, c'est-a-dire le jour ou la sauvegarde compte.
    import glob
    vieilles = sorted(glob.glob(os.path.join(DOSSIER, ".sauvegardes", "DFM-local-*.zip")))
    for v in vieilles[:-SAUVEGARDES_GARDEES]:
        try:
            os.remove(v)
            _noter("Ancienne sauvegarde retiree : %s" % os.path.basename(v))
        except Exception:
            pass


def _boucle():
    global _dernier_passage, _derniere_sauvegarde
    _noter("Planificateur demarre : guet toutes les %d min, passage complet a %s, "
           "sauvegarde a %dh%02d."
           % (GUETTEUR_SECONDES // 60,
              " et ".join("%dh%02d" % h for h in PASSAGE_HEURES),
              SAUVEGARDE_HEURE[0], SAUVEGARDE_HEURE[1]))
    while not _arret.is_set():
        try:
            n = _guetter()
            if n:
                _noter("%d dossier(s) client avance(s)." % n)
        except Exception as e:
            _noter("Guetteur en echec : %s" % str(e)[:180])

        # LE PASSAGE COMPLET, une seule fois par creneau. Sans cette marque, un
        # reveil toutes les dix minutes le relancerait six fois dans l'heure.
        try:
            m = datetime.datetime.now()
            creneau = next((c for c in (_creneau(m, h, mi) for h, mi in PASSAGE_HEURES) if c), None)
            if creneau and creneau != _dernier_passage:
                _dernier_passage = creneau
                _noter("Passage complet lance.")
                ok, lignes = _lancer("dfm.py", delai=1800)
                _noter("Passage complet termine : %s" % (lignes[-1][:150] if lignes else "sans sortie"))
        except Exception as e:
            _noter("Passage complet en echec : %s" % str(e)[:180])

        try:
            m = datetime.datetime.now()
            creneau_s = _creneau(m, SAUVEGARDE_HEURE[0], SAUVEGARDE_HEURE[1])
            if creneau_s and creneau_s != _derniere_sauvegarde:
                _derniere_sauvegarde = creneau_s
                _sauvegarder()
        except Exception as e:
            _noter("Sauvegarde en echec : %s" % str(e)[:180])

        _arret.wait(GUETTEUR_SECONDES)


_fil = None


def demarrer():
    """Lance le fil, une seule fois. Sans effet s'il tourne deja.

    LE RELOADER DE FLASK LANCE LE PROCESSUS DEUX FOIS : sans la garde ci-dessous,
    deux planificateurs tourneraient en parallele et doubleraient chaque envoi.
    """
    global _fil
    if _fil and _fil.is_alive():
        return False
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return False
    _fil = threading.Thread(target=_boucle, name="dfm-planificateur", daemon=True)
    _fil.start()
    return True


def actif():
    return bool(_fil and _fil.is_alive())
