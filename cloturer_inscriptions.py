from sessions import session
from datetime import datetime
import subprocess
import sys
import sessions as _sess
import suivi
S = session()
# L'ETAT VIENT DE LA BASE LOCALE. Il n'y a plus de numero de ligne a retrouver
# dans un onglet, donc plus de « session absente de l'onglet Sessions » : une
# session qui n'a rien vecu a simplement un etat vide.
fiche = _sess.etat(S["code"])
print(f"-> Session : {S['nom_formation']} ({S['code']})")
print(f"-> Statut actuel : {fiche['statut_session'] or 'ouverte'}")
if fiche["statut_session"] == "cloturee":
    print(f"\n-> Deja cloturee le {fiche['cloture_le']}.")
    if fiche["lien_emargement"]:
        print(f"   Feuille d'emargement : {fiche['lien_emargement']}")
    if input("\nRegenerer la feuille d'emargement ? (o/n) : ").strip().lower() not in ("o", "oui", "y"):
        exit()
else:
    lignes = suivi.lire_lignes()
    actifs = [l for l in lignes if "recontact" not in l["demande"].lower()
              and not l["annule_le"] and not l["annulation_demandee_le"]]
    non_signes = [l for l in actifs if not l["signe_le"]]
    non_regles = [l for l in actifs if not l["paiement_recu_le"]]
    print(f"\n  {len(actifs)} participant(s) sur {S['places_max']} place(s)")
    if non_signes:
        print(f"\n  ATTENTION : {len(non_signes)} convention(s) non signee(s)")
        for l in non_signes:
            print(f"    . {l['prenom']} {l['nom']}")
    if non_regles:
        print(f"\n  ATTENTION : {len(non_regles)} reglement(s) en attente")
        for l in non_regles:
            print(f"    . {l['prenom']} {l['nom']}")
    print("\n  La cloture fige la liste des participants.")
    print("  Les inscriptions suivantes ne seront plus importees automatiquement.")
    if input("\nCloturer les inscriptions ? (o/n) : ").strip().lower() not in ("o", "oui", "y"):
        print("-> Annule.")
        exit()
    maintenant = datetime.now().strftime("%d/%m/%Y %H:%M")
    # LES DEUX CHAMPS EN UNE SEULE ECRITURE : une session ne doit jamais etre
    # vue « cloturee » sans sa date, meme le temps de deux instructions.
    _sess.poser_etats(S["code"], {"statut_session": "cloturee",
                                  "cloture_le": maintenant})
    print(f"\n-> Inscriptions cloturees le {maintenant}.")
    import journal
    journal.ecrire("Inscriptions clôturées", "", f"{len(actifs)} participant(s)", "", S["code"])
print("\n-> Generation de la feuille d'emargement...")
resultat = subprocess.run([sys.executable, "generer_emargement.py"], capture_output=True, text=True)
for l in resultat.stdout.splitlines():
    if l.strip():
        print("   " + l)
if resultat.returncode != 0:
    print("   ERREUR lors de la generation.")
    for l in resultat.stderr.splitlines()[-6:]:
        print("   " + l)
    exit()
# DEFAUT CORRIGE LE 17/08/2026. On ne cherchait que « docs.google.com », l'adresse
# d'un Google Doc. Depuis que la feuille d'emargement est un PDF, elle est servie
# par « drive.google.com » : le lien n'etait plus jamais reconnu, donc jamais
# enregistre, et l'ecran affichait une session sans feuille alors qu'elle existait.
# Meme defaut que celui deja corrige dans deux routes de l'application.
lien = ""
for l in resultat.stdout.splitlines():
    if "drive.google.com" in l or "docs.google.com" in l:
        for mot in l.split():
            if mot.startswith("http"):
                lien = mot.strip()
if lien:
    _sess.poser_etats(S["code"], {
        "emargement_genere_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "lien_emargement": lien})
    print(f"\n-> Feuille enregistree.")
    print(f"   {lien}")
