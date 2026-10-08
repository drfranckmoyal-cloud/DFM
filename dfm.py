import subprocess
import sys
import json
import os
from datetime import datetime
DOSSIER = os.path.dirname(os.path.abspath(__file__))
RAPPORT = os.path.join(DOSSIER, "derniere_synchro.json")

# --------------------------------------------------------------------------
# UN SEUL PIPELINE A LA FOIS
#
# DEFAUT CORRIGE LE 04/08/2026. Trois endroits d'app.py lancent ce script, et
# rien n'empechait deux executions de se chevaucher. Les garde-fous des etapes
# client ecrivent leur trace APRES l'action : deux passages simultanes lisent
# tous deux « rien n'a encore ete fait » et agissent tous deux. Resultat reel :
# DEUX factures numerotees pour la meme session — 008 et 009 — et deux mails au
# client a la meme minute.
#
# Une trace ecrite AVANT l'action aurait ferme la porte a la reprise : un echec
# reseau laisserait une facture reputee emise qui n'existe pas. Le verrou traite
# la cause, pas le symptome, et protege TOUTES les etapes d'un coup.
VERROU = os.path.join(DOSSIER, "dfm.verrou")
_PERIME = 20 * 60          # au-dela, on considere le precedent comme mort


def _vivant(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _prendre_le_verrou():
    if os.path.exists(VERROU):
        try:
            with open(VERROU, encoding="utf-8") as f:
                d = json.load(f)
            age = (datetime.now() - datetime.strptime(d["quand"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        except Exception:
            d, age = {}, _PERIME + 1
        if age < _PERIME and _vivant(int(d.get("pid") or 0)):
            print("=" * 55)
            print("  Un traitement est deja en cours (depuis " + str(int(age)) + " s).")
            print("  Celui-ci s'arrete pour ne rien faire en double.")
            print("=" * 55)
            sys.exit(0)
        # Verrou perime ou processus disparu : on le reprend, en le disant.
        if os.path.exists(VERROU):
            print("-> Verrou abandonne trouve (traitement interrompu ?). Repris.")
    import fichiers
    fichiers.ecrire(VERROU, {"pid": os.getpid(),
                             "quand": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


def _rendre_le_verrou():
    # Ne retirer QUE le sien : un traitement qui a repris un verrou perime ne
    # doit pas effacer celui d'un autre au passage.
    try:
        with open(VERROU, encoding="utf-8") as f:
            if int(json.load(f).get("pid") or 0) != os.getpid():
                return
        os.remove(VERROU)
    except Exception:
        pass


_prendre_le_verrou()
import atexit
atexit.register(_rendre_le_verrou)
# Troisieme colonne : l'echec de cette etape doit-il interrompre la suite ?
# Le critere n'est pas l'importance de l'etape, mais ce que la SUIVANTE ferait
# de travers si celle-ci echouait.
#   - Import : le controle d'en-tetes refuse quand le formulaire a change ;
#     poursuivre travaillerait sur des donnees partielles.
#   - Releve des annulations : sans elle, une personne ayant demande
#     l'annulation reste "active" et recevra confirmation, facture et rappels.
# Les neuf autres n'echouent que localement : l'etape suivante trouve
# simplement moins de choses a faire, et rien de faux ne part.
ETAPES = [
    # NON BLOQUANTE DEPUIS LE 18/08/2026. Elle lit le formulaire Google, et
    # l'autorisation Google meurt tous les sept jours tant que l'application
    # reste en mode « Test » dans la console. Bloquante, cette etape emportait
    # avec elle les SEIZE suivantes de chaque session : conventions, relances,
    # factures, attestations. Un passage du 18/08 l'a montre — masterclass-oct26
    # a perdu ses seize etapes sur une erreur 503 passagere.
    #
    # Meme raison que pour son jumeau juste en dessous : une panne de la source
    # d'inscriptions ne doit pas arreter le travail de la journee. Ce qu'on perd
    # est borne et rattrapable — une inscription arrivee par l'ancien formulaire
    # attend le passage suivant. Ce qu'on gagnait a bloquer n'existait pas.
    ("Import des inscriptions", "importer_inscriptions.py", False),
    # LE FORMULAIRE MAISON, juste apres celui de Google. Les deux coexistent :
    # une session alimentee par l'ancien formulaire continue de l'etre, une
    # session publiee sur la nouvelle page passe par ici. Rien n'oblige a tout
    # basculer le meme jour.
    #
    # NON BLOQUANTE : une panne de Supabase ne doit pas arreter les conventions,
    # les factures et les attestations de la journee.
    ("Demandes du formulaire", "importer_demandes.py", False),
    ("Releve des annulations", "relever_annulations.py", True),
    ("Mails de file d'attente", "envoyer_mail_attente.py", False),
    # Avant l'envoi : le lien de signature doit pouvoir pointer sur le document.
    # Non bloquante — un praticien sans lien serait pire qu'une convention
    # qu'il ne peut pas relire.
    # Sessions CLIENT : ces etapes remplacent toute la chaine individuelle de
    # convention. Elles s'abstiennent d'elles-memes sur une session
    # individuelle, exactement comme les autres s'abstiennent en mode client.
    #
    # La relevee de signature vient JUSTE APRES l'envoi : c'est elle qui, au
    # passage suivant, constatera que le representant a signe. C'est le
    # declencheur de la facturation client (choix du 03/08/2026 : facturer a la
    # validation de la convention signee).
    ("Convention client", "generer_convention_client.py", False),
    ("Envoi de la convention au client", "envoyer_mail_signature_client.py", False),
    ("Releve de la signature du client", "relever_signature_client.py", False),
    # La FACTURE avant l'envoi : la convention contresignee et la facture
    # partent dans le MEME mail, et l'envoi s'abstient si l'une des deux
    # manque. Deux pieces qui vont ensemble dans le dossier du centre.
    ("Facture client", "generer_facture_client.py", False),
    ("Convention client signee + facture", "generer_convention_client_signee.py", False),
    ("Preparation des conventions a signer", "generer_convention_apercu.py", False),
    ("Envoi des mails de signature", "envoyer_mail_signature.py", False),
    ("Releve des signatures", "relever_signatures.py", False),
    ("Generation des conventions signees", "generer_convention_signee.py", False),
    ("Envoi des mails de confirmation", "envoyer_mail_confirmation.py", False),
    ("Envoi des rappels J-20", "envoyer_rappel.py", False),
    ("Generation des factures", "generer_factures.py", False),
    ("Envoi des factures", "envoyer_facture.py", False),
    ("Generation des attestations", "generer_attestations.py", False),
    # L'envoi des attestations n'est plus automatique : il passe par la fenetre
    # de validation de la fiche de session, ou l'on decoche les absents.
    # Voir /session/<code>/attestations/envoyer dans app.py.
]
def ecrire_rapport(rapport):
    try:
        import fichiers
        fichiers.ecrire(RAPPORT, rapport)
    except Exception:
        pass
def resumer(sortie):
    utiles = []
    for l in (sortie or "").splitlines():
        t = l.strip()
        if not t or t.startswith("=") or t.startswith("-"):
            continue
        if t.startswith("->") or t.startswith("."):
            utiles.append(t.lstrip("-> ").strip())
    return utiles[-3:]
print("=" * 55)
print("  DFM - traitement complet")
print("=" * 55)
def _sessions_a_traiter():
    """Sessions a traiter, en ordre chronologique. Les sessions archivees
    (terminee_le renseigne dans l'onglet Sessions) sont sautees ; en cas de
    doute (lecture impossible), on traite tout plutot que d'oublier."""
    from sessions import SESSIONS
    codes = sorted(SESSIONS, key=lambda c: SESSIONS[c].get("date_debut") or "")
    terminees = set()
    # LES DEUX ORGANISMES, pas seulement celui du profil actif. Ce script traite
    # toutes les sessions des deux entites ; il lisait pourtant l'onglet
    # « Sessions » d'un seul. Une session DSF archivee aurait ete retraitee des
    # lors que le pipeline tournait sous Smileclub — relances, documents et
    # mails compris.
    #
    # La base rend les etats de TOUS les organismes en une requete locale : le
    # defaut ci-dessus ne peut plus se reproduire par distraction.
    try:
        import sessions as _sess
        for _code, _e in _sess.etats().items():
            if (_e.get("terminee_le") or "").strip():
                terminees.add(_code)
    except Exception:
        pass
    return [c for c in codes if c not in terminees], sorted(terminees & set(codes))

codes_sessions, archivees = _sessions_a_traiter()
rapport = {"quand": datetime.now().strftime("%d/%m/%Y %H:%M"),
           "ok": True, "etapes": [], "echec": None, "echecs": [],
           "sessions": codes_sessions, "archivees": archivees}
if archivees:
    print("  Session(s) archivee(s), non traitee(s) : " + ", ".join(archivees))
for code in codes_sessions:
    print("=" * 55)
    print("  SESSION " + code)
    print("=" * 55)
    arrete_a = None
    for numero, (titre, script, bloquant) in enumerate(ETAPES, 1):
        print("[" + code + " " + str(numero) + "/" + str(len(ETAPES)) + "] " + titre)
        print("-" * 55)
        # Le code de session est TOUJOURS transmis : c'est lui qui garantit
        # que lectures et ecritures visent le meme onglet (point A1).
        resultat = subprocess.run([sys.executable, script, code],
                                  capture_output=True, text=True, cwd=DOSSIER)
        for ligne in resultat.stdout.splitlines():
            if ligne.strip():
                print("   " + ligne)
        fiche = {"numero": numero, "titre": titre, "script": script,
                 "session": code, "executee": True, "bloquant": bloquant,
                 "ok": resultat.returncode == 0, "resume": resumer(resultat.stdout)}
        if resultat.returncode != 0:
            erreurs = [l.strip() for l in resultat.stderr.splitlines() if l.strip()]
            cause = ""
            for l in reversed(erreurs):
                if "Error" in l or "error" in l:
                    cause = l
                    break
            if not cause and erreurs:
                cause = erreurs[-1]
            fiche["cause"] = cause[:220]
            fiche["details"] = erreurs[-6:]
            rapport["ok"] = False
            rapport["echecs"].append(fiche)
            if rapport["echec"] is None or (bloquant and not rapport["echec"].get("bloquant")):
                rapport["echec"] = fiche
            rapport["etapes"].append(fiche)
            print("   ERREUR : cette etape a echoue.")
            for ligne in erreurs[-8:]:
                print("   " + ligne)
            if bloquant:
                arrete_a = numero
                print("-" * 55)
                print("  [" + code + "] etape bloquante : la suite de CETTE session")
                print("  est abandonnee. Les autres sessions seront traitees.")
                break
            print("   Etape non bloquante : le traitement continue.")
            print()
            continue
        rapport["etapes"].append(fiche)
        print()
    if arrete_a is not None:
        # Non tentee n'est pas reussie : les etapes sautees figurent au rapport.
        for numero, (titre, script, bloquant) in enumerate(ETAPES, 1):
            if numero <= arrete_a:
                continue
            rapport["etapes"].append({"numero": numero, "titre": titre,
                                      "script": script, "session": code,
                                      "executee": False, "bloquant": bloquant,
                                      "ok": None, "resume": []})
        print("  [" + code + "] etapes non executees : "
              + ", ".join(str(n) for n in range(arrete_a + 1, len(ETAPES) + 1)) + ".")

# --- Etapes qui ne dependent d'AUCUNE session -------------------------------
# Les reclamations arrivent d'une page publique ouverte a tous : un ancien
# stagiaire, une structure cliente, un formateur. Elles n'appartiennent a
# aucune session en particulier, et surtout elles arrivent meme quand aucune
# session n'est en cours. Les relever DANS la boucle par session les aurait
# manquees les semaines creuses, et relevees N fois les semaines chargees.
print("=" * 55)
print("  RECLAMATIONS")
print("=" * 55)
try:
    import reclamations as _rec
    _nouvelles, _souci = _rec.relever()
    if _souci:
        print("   " + _souci)
        rapport["etapes"].append({"numero": 0, "titre": "Releve des reclamations",
                                  "script": "reclamations.py", "session": "",
                                  "executee": True, "bloquant": False,
                                  "ok": False, "resume": [_souci]})
    else:
        _mot = ("%d nouvelle(s) reclamation(s) versee(s) au registre" % _nouvelles
                if _nouvelles else "Aucune nouvelle reclamation.")
        print("   " + _mot)
        if _nouvelles:
            try:
                import journal as _j
                _j.ecrire("Réclamations relevées",
                          detail="%d depuis la page publique, à la synchronisation"
                                 % _nouvelles)
            except Exception:
                pass
        rapport["etapes"].append({"numero": 0, "titre": "Releve des reclamations",
                                  "script": "reclamations.py", "session": "",
                                  "executee": True, "bloquant": False,
                                  "ok": True, "resume": [_mot]})
except Exception as _e:
    # Une reclamation non relevee se rattrape au passage suivant ou d'un clic.
    # Elle ne doit jamais faire echouer la synchronisation des sessions.
    print("   (releve des reclamations impossible : %s)" % _e)

reussies = len([e for e in rapport["etapes"] if e.get("ok") is True])
non_exec = len([e for e in rapport["etapes"] if e.get("executee") is False])
print("-" * 55)
print("  " + str(len(codes_sessions)) + " session(s) · "
      + str(reussies) + " etape(s) reussie(s) · "
      + str(len(rapport["echecs"])) + " en echec"
      + (" · " + str(non_exec) + " non executee(s)" if non_exec else ""))
ecrire_rapport(rapport)
if not rapport["ok"]:
    sys.exit(1)
print("  Traitement termine.")
print("=" * 55)
