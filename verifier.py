"""Verifie que tous les fichiers Python du dossier compilent.

Ne modifie rien, n'envoie aucun mail, ne touche ni a Google Sheets ni a Drive :
il se contente de relire le code et de signaler les erreurs de syntaxe.

Usage : python3 verifier.py [fichier.py ...]
Sans argument, tous les fichiers .py du dossier sont verifies
(les copies de sauvegarde .avant-* et .reprise-* sont ignorees).
"""

import os
import sys


def a_verifier(nom):
    if not nom.endswith(".py"):
        return False
    return ".avant-" not in nom and ".reprise-" not in nom


def main():
    dossier = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1:
        fichiers = sys.argv[1:]
    else:
        fichiers = sorted(f for f in os.listdir(dossier) if a_verifier(f))

    erreurs = []
    for fichier in fichiers:
        chemin = fichier if os.path.isabs(fichier) else os.path.join(dossier, fichier)
        try:
            with open(chemin, "r", encoding="utf-8") as f:
                compile(f.read(), chemin, "exec")
        except SyntaxError as e:
            erreurs.append((fichier, f"ligne {e.lineno} : {e.msg}"))
        except (OSError, UnicodeDecodeError) as e:
            erreurs.append((fichier, str(e)))

    print(f"{len(fichiers)} fichier(s) verifie(s)")
    if not erreurs:
        print("Aucune erreur de syntaxe.")
        return 0

    print(f"{len(erreurs)} fichier(s) en erreur :\n")
    for fichier, message in erreurs:
        print(f"  {fichier}")
        for ligne in message.splitlines():
            print(f"      {ligne}")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
