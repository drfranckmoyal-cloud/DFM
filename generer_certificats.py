"""Fabrique les certificats de fin de formation d'une session.

    python3 generer_certificats.py <code_session>            les certificats qui manquent
    python3 generer_certificats.py <code_session> --refaire  tous, refaits en place
    python3 generer_certificats.py <code_session> --avance   meme avant la fin de la formation

« --AVANCE » EST LE BOUTON « Generer les certificats » de la fiche de session —
08/11/2026, demande de Franck : les faire imprimer avant la formation, et y
revenir pour une inscription tardive. Il ne fabrique que ceux qui manquent.

UNE ETAPE DU TRAITEMENT QUOTIDIEN, juste apres les attestations : un certificat
nait le meme jour que l'attestation de la personne, une fois la formation
finie. Il ne part pas d'ici : il part AVEC l'attestation, par la fenetre
d'envoi de la fiche de session, la ou l'on decoche les absents. Voir
certificat.py et envoyer_attestation.py.

UN CERTIFICAT NE SE REFAIT PAS TOUT SEUL. Contrairement a l'attestation, il ne
porte aucun resultat qui arriverait plus tard : le nom, les dates et la
formation sont connus des le dernier jour. Si un nom est corrige ensuite,
« --refaire » le refabrique, au meme endroit et sous le meme nom.
"""
import sys
from datetime import date, datetime

import certificat
import journal
import jours as _jours
import pdf as _pdf
import suivi
from sessions import session

CODE = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
REFAIRE = "--refaire" in sys.argv[1:]
AVANCE = "--avance" in sys.argv[1:]
S = session(CODE)
print(f"-> Session : {S['nom_formation']} ({S['code']})")

if not certificat.fond(S["code"]):
    print("-> Pas de modele de certificat pour cette formation et cet organisme.")
    exit()

_j = _jours.resume(S)
fin = datetime.strptime(_j["date_fin"], "%Y-%m-%d").date() if _j["date_fin"] else date.today()
if fin > date.today() and not AVANCE:
    print(f"-> La formation se termine le {fin.strftime('%d/%m/%Y')}. Trop tot.")
    exit()

try:
    _pdf.navigateur()
except _pdf.Indisponible as e:
    print("-> " + str(e))
    exit()

# LES MEMES PERSONNES QUE POUR L'ATTESTATION, et par la meme regle : tous les
# inscrits actifs. Les absents se retirent a l'envoi, pas ici.
lignes = certificat.beneficiaires(S["code"])
a_faire = lignes if REFAIRE else [l for l in lignes if not certificat.present(S["code"], l)]
if not a_faire:
    print("-> Aucun certificat a generer.")
    exit()
print(f"-> {len(a_faire)} certificat(s) a generer.")

import documents
compte = 0
for ligne in a_faire:
    qui = f"{ligne['prenom']} {ligne['nom']}".strip()
    print(f"-> {qui}...")
    try:
        octets = certificat.fabriquer(S["code"], ligne)
    except Exception as e:
        print(f"   ECHEC : {e}")
        continue
    ref, lien, souci = documents.ranger(S["code"], "certificat", certificat.nom_fichier(ligne), octets)
    if not ref:
        print("   ECHEC : " + souci)
        continue
    try:
        journal.ecrire("Certificat généré", ((ligne["prenom"] or "").strip() + " "
                                             + (ligne["nom"] or "").strip().upper()).strip(),
                       lien or ref, "", S["code"])
    except Exception:
        pass
    print("   certificat range." + ("" if lien else " (copie Drive non partie)"))
    compte += 1
print(f"-> Termine : {compte} certificat(s) genere(s).")
