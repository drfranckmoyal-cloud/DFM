"""Installe le mot de passe d'envoi d'un organisme, et verifie qu'il marche.

    python3 installer_smtp.py

CE SCRIPT NE MONTRE JAMAIS LE MOT DE PASSE. La saisie est masquee, la valeur va
directement dans « smtp.json », et le fichier est referme en lecture pour vous
seul. Personne d'autre — pas meme ce qui a ecrit ce script — ne le voit passer.

POURQUOI UN MOT DE PASSE D'APPLICATION, et pas celui du compte. Gmail refuse le
mot de passe du compte pour un envoi SMTP. Celui qu'on installe ici est un mot
de passe DEDIE : il ne donne acces qu'a l'envoi, et se revoque d'un clic sans
toucher au compte ni aux autres appareils.

TANT QU'IL N'EST PAS INSTALLE, RIEN NE CHANGE : DFM continue d'envoyer par
l'API Google, exactement comme avant. La bascule se fait organisme par
organisme, et se defait en retirant le mot de passe.
"""
import getpass
import json
import os
import sys

import courrier
import profil

FICHIER = courrier.FICHIER_SECRETS


def _lire():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    with open(FICHIER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    # LISIBLE PAR VOUS SEUL. Sans cela le fichier heriterait des droits par
    # defaut du dossier, et un mot de passe d'envoi n'a pas a etre lisible par
    # les autres comptes de la machine.
    try:
        os.chmod(FICHIER, 0o600)
    except Exception:
        pass


def main():
    print()
    print("  INSTALLATION DE L'ENVOI DE COURRIER")
    print("  " + "-" * 52)
    print()
    print("  Etat actuel :")
    for e in courrier.etat():
        print("    %-24s %-32s %s" % (e["marque"], e["adresse"], e["par"]))
    print()

    organismes = [p["id"] if isinstance(p, dict) else p for p in profil.lister()]
    if not organismes:
        print("  Aucun organisme declare. Rien a installer.")
        return
    print("  Pour quel organisme ?")
    for i, o in enumerate(organismes, 1):
        p = profil.charger(o) or {}
        print("    %d. %s  (%s)" % (i, p.get("marque") or o, p.get("mail_contact") or "sans adresse"))
    print()
    choix = input("  Numero (ou Entree pour abandonner) : ").strip()
    if not choix:
        print("  Abandonne. Rien n'a ete ecrit.")
        return
    try:
        org = organismes[int(choix) - 1]
    except Exception:
        print("  Choix invalide. Rien n'a ete ecrit.")
        return

    p = profil.charger(org) or {}
    adresse = (p.get("mail_contact") or "").strip()
    print()
    print("  Organisme : %s" % (p.get("marque") or org))
    print("  Adresse   : %s" % (adresse or "AUCUNE — completez la fiche d'abord"))
    if not adresse or "@" not in adresse:
        print()
        print("  Sans adresse de contact, l'envoi ne peut pas etre configure.")
        print("  Renseignez-la dans DFM, ecran Profil, puis relancez.")
        return

    print()
    print("  Il vous faut un MOT DE PASSE D'APPLICATION Google pour ce compte.")
    print("  Si vous n'en avez pas encore :")
    print("    1. Connectez-vous a ce compte Google")
    print("    2. Ouvrez  myaccount.google.com/apppasswords")
    print("    3. Creez-en un, nommez-le « DFM »")
    print("    4. Google affiche 16 lettres — c'est ce qu'on colle ci-dessous")
    print()
    print("  (la validation en deux etapes doit etre active sur le compte,")
    print("   sinon Google ne propose pas cette page)")
    print()
    mot = getpass.getpass("  Collez le mot de passe (rien ne s'affiche) : ").strip()
    # Google l'affiche par groupes de quatre ; les espaces ne font pas partie
    # du mot de passe et le collage les emporte souvent.
    mot = mot.replace(" ", "")
    if not mot:
        print("  Rien saisi. Rien n'a ete ecrit.")
        return

    d = _lire()
    d[org] = {"adresse": adresse, "mot_de_passe": mot,
              "serveur": courrier.DEFAUTS["serveur"],
              "port": courrier.DEFAUTS["port"], "tls": True}
    _ecrire(d)
    print()
    print("  Enregistre dans %s (lisible par vous seul)." % os.path.basename(FICHIER))
    print()

    dest = input("  Adresse ou envoyer l'essai [%s] : " % adresse).strip() or adresse
    print("  Envoi en cours...")
    ok, msg = courrier.essai(org, dest)
    print()
    print("  " + ("REUSSI — " if ok else "ECHEC — ") + msg)
    if ok:
        print()
        print("  A partir de maintenant, les mails de cet organisme partent par SMTP.")
        print("  Pour revenir en arriere : retirez son entree de smtp.json.")
    else:
        print()
        print("  Le mot de passe reste enregistre mais l'envoi ne fonctionne pas.")
        print("  DFM continue d'envoyer par l'API Google en attendant.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Interrompu. Rien n'a ete ecrit.\n")
        sys.exit(0)
