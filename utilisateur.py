"""Gerer les comptes de DFM depuis le serveur.

    venv/bin/python utilisateur.py                 # la liste
    venv/bin/python utilisateur.py --creer
    venv/bin/python utilisateur.py --mot-de-passe <identifiant>

POURQUOI UN OUTIL EN LIGNE DE COMMANDE ALORS QUE L'ECRAN EXISTE. Parce que
l'ecran est derriere la connexion. Le jour ou le dernier gerant perd son mot de
passe, ou ou l'on cree le tout premier compte, il n'y a personne pour ouvrir la
porte de l'interieur. C'est la porte de service, et elle demande un acces au
serveur — ce qui est exactement la bonne barriere.

LE MOT DE PASSE NE S'ECRIT PAS DANS LA COMMANDE. Il se tape quand l'outil le
demande, sans s'afficher : une commande reste dans l'historique du terminal, un
mot de passe n'a rien a y faire.
"""
import getpass
import sys

import acces


def _liste():
    comptes = acces.utilisateurs()
    if not comptes:
        print("  Aucun compte.")
        print()
        print("  DFM demande donc seulement le mot de passe d'installation,")
        print("  comme avant. Creer un compte bascule DFM sur les comptes :")
        print("    venv/bin/python utilisateur.py --creer")
        return 0
    print("  %d compte(s) :" % len(comptes))
    print()
    print("    %-16s %-24s %-11s %-7s %s"
          % ("identifiant", "nom", "role", "actif", "derniere connexion"))
    for u in comptes:
        print("    %-16s %-24s %-11s %-7s %s"
              % (u.get("identifiant", ""), (u.get("nom") or "")[:24],
                 acces.ROLES.get(u.get("role"), u.get("role") or ""),
                 "oui" if u.get("actif", True) else "NON",
                 u.get("derniere_connexion") or "jamais"))
    return 0


def _demander_mot_de_passe():
    m = getpass.getpass("  Mot de passe (10 caracteres minimum) : ")
    if m != getpass.getpass("  A nouveau, pour verifier               : "):
        print("  Les deux saisies different. Rien n'a ete enregistre.")
        return None
    return m


def _creer():
    premier = not acces.utilisateurs()
    if premier:
        print("  C'est le PREMIER compte. Des qu'il existera, DFM demandera")
        print("  un identifiant et un mot de passe au lieu du seul mot de")
        print("  passe d'installation. Ce premier compte sera gerant.")
        print()
    identifiant = input("  Identifiant (sans espace, ex. franck) : ").strip()
    nom = input("  Nom affiche (ex. Franck Moyal)        : ").strip()
    if premier:
        role = "gerant"
    else:
        print("  Role : 1 = gerant (tout), 2 = assistante (le quotidien)")
        role = "gerant" if input("  Votre choix [2] : ").strip() == "1" else "assistante"
    m = _demander_mot_de_passe()
    if m is None:
        return 1
    ok, message = acces.creer_utilisateur(identifiant, nom, m, role)
    print("  " + message)
    if ok and premier:
        print()
        print("  DFM demande desormais un identifiant. Notez-le bien :")
        print("    identifiant : %s" % acces._nettoyer_identifiant(identifiant))
    return 0 if ok else 1


def _changer(identifiant):
    if not acces.utilisateur(identifiant):
        print("  Compte inconnu : %s" % identifiant)
        return 1
    m = _demander_mot_de_passe()
    if m is None:
        return 1
    ok, message = acces.modifier_utilisateur(identifiant, mot_de_passe=m)
    print("  " + message)
    return 0 if ok else 1


if __name__ == "__main__":
    print()
    print("  LES COMPTES DE DFM")
    print("  " + "-" * 52)
    if "--creer" in sys.argv:
        code = _creer()
    elif "--mot-de-passe" in sys.argv:
        reste = [a for a in sys.argv[1:] if not a.startswith("--")]
        if not reste:
            print("  Il manque l'identifiant :")
            print("    venv/bin/python utilisateur.py --mot-de-passe franck")
            code = 1
        else:
            code = _changer(reste[0])
    else:
        code = _liste()
    print()
    sys.exit(code)
