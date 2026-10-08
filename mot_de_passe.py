"""Definir le mot de passe d'acces a DFM.

    python3 mot_de_passe.py

A LANCER AVANT TOUTE PUBLICATION. Tant qu'aucun mot de passe n'est defini, DFM
s'ouvre sans rien demander — ce qui convient sur une machine personnelle et
serait une porte ouverte des que l'adresse devient joignable.
"""
import getpass
import sys

import acces

print()
print("  MOT DE PASSE D'ACCES A DFM")
print("  " + "-" * 52)
if acces.protege():
    print("  Un mot de passe est deja defini. Le remplacer fermera toutes")
    print("  les sessions ouvertes.")
else:
    print("  Aucun mot de passe : DFM s'ouvre actuellement sans rien demander.")
print()
print("  Il protege 181 contacts, vos conventions, vos factures et le")
print("  journal d'activite. Dix caracteres au minimum.")
print()

try:
    un = getpass.getpass("  Nouveau mot de passe : ")
    deux = getpass.getpass("  Confirmer            : ")
except (EOFError, KeyboardInterrupt):
    print("\n  Interrompu. Rien n'a change.")
    sys.exit(1)

if un != deux:
    print("\n  Les deux saisies different. Rien n'a change.")
    sys.exit(1)

ok, message = acces.definir(un)
print()
print("  " + message)
if ok:
    print("  Relancez DFM : une page de connexion s'affichera.")
sys.exit(0 if ok else 1)
