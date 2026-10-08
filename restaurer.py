# -*- coding: utf-8 -*-
"""Restaurer DFM depuis un instantane.

    venv/bin/python restaurer.py --liste
    venv/bin/python restaurer.py 20261008-0330              # a cote, pour voir
    venv/bin/python restaurer.py 20261008-0330 --sur-place --je-confirme

PAR DEFAUT, ON NE TOUCHE PAS A L'INSTALLATION EN SERVICE. La restauration se
fait DANS UN DOSSIER NEUF, a cote, et le script la verifie. C'est ce qui permet
de repondre a la seule question qui vaille — « est-ce que cette sauvegarde se
relit ? » — sans rien risquer, et donc de se poser la question souvent plutot
qu'une fois dans l'urgence.

SUR PLACE, RIEN N'EST SUPPRIME. L'installation actuelle est DEPLACEE de cote,
sous un nom date, avant d'etre remplacee. Si la restauration deçoit, le retour
arriere est un simple renommage. Une restauration qui efface ce qu'elle
remplace transforme une mauvaise journee en journee irreparable.
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime

RACINE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(RACINE)
DESTINATION = os.path.join(PARENT, "sauvegardes")


def instantanes():
    if not os.path.isdir(DESTINATION):
        return []
    return sorted(n for n in os.listdir(DESTINATION)
                  if os.path.isdir(os.path.join(DESTINATION, n)) and n[:2].isdigit())


def _verifier(dossier):
    python = os.path.join(dossier, "venv", "bin", "python")
    if not os.path.exists(python):
        python = os.path.join(RACINE, "venv", "bin", "python")
    if not os.path.exists(python):
        python = sys.executable
    code = ("import journal, json;"
            "print(json.dumps([{'marque': f['marque'], 'entrees': f['entrees'],"
            "'intacte': bool(f['intacte'])} for f in journal.verifier()]))")
    try:
        r = subprocess.run([python, "-c", code], cwd=dossier, timeout=180,
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None, (r.stderr or "").strip()[-160:]
        import json as _json
        return _json.loads(r.stdout.strip().splitlines()[-1]), ""
    except Exception as e:
        return None, str(e)[:160]


def _copier(source, cible):
    r = subprocess.run(["rsync", "-a", source.rstrip("/") + "/", cible + "/"],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "")[:200]


def restaurer(marque, sur_place=False, confirme=False):
    source = os.path.join(DESTINATION, marque)
    if not os.path.isdir(source):
        print("  Instantane inconnu : %s" % marque)
        print("  Les instantanes disponibles : venv/bin/python restaurer.py --liste")
        return 1

    manifeste = os.path.join(source, "MANIFESTE.txt")
    if os.path.exists(manifeste):
        print("  " + "-" * 52)
        for ligne in open(manifeste, encoding="utf-8").read().splitlines():
            print("  " + ligne)
        print("  " + "-" * 52)

    if not sur_place:
        cible = os.path.join(PARENT, "DFM-restaure-" + datetime.now().strftime("%Y%m%d-%H%M"))
        print("  Restauration a cote, dans %s..." % cible)
        ok, souci = _copier(source, cible)
        if not ok:
            print("  ECHEC de la copie : " + souci)
            return 1
        fiches, souci = _verifier(cible)
        if fiches is None:
            print("  LA COPIE RESTAUREE NE SE RELIT PAS : " + souci)
            return 1
        for f in fiches:
            print("  %-16s %5d entrees   %s"
                  % (f["marque"], f["entrees"],
                     "chaine intacte" if f["intacte"] else "CHAINE ROMPUE"))
        print("  Restauration verifiee. L'installation en service n'a pas bouge.")
        print("  Ce dossier peut etre efface quand vous voudrez : " + cible)
        return 0

    if not confirme:
        print("  REFUS : --sur-place remplace l'installation en service.")
        print("  Relancer avec --je-confirme si c'est bien ce que vous voulez.")
        return 1

    print("  Arret de DFM...")
    subprocess.run(["sudo", "systemctl", "stop", "dfm"], capture_output=True)
    ecarte = RACINE + ".avant-restauration-" + datetime.now().strftime("%Y%m%d-%H%M")
    print("  L'installation actuelle est mise de cote dans %s" % ecarte)
    try:
        os.rename(RACINE, ecarte)
    except OSError as e:
        print("  ECHEC : impossible de mettre de cote l'installation (%s)" % str(e)[:100])
        subprocess.run(["sudo", "systemctl", "start", "dfm"], capture_output=True)
        return 1
    ok, souci = _copier(source, RACINE)
    if not ok:
        print("  ECHEC de la copie : " + souci)
        print("  RETOUR ARRIERE : on remet l'installation precedente.")
        shutil.rmtree(RACINE, ignore_errors=True)
        os.rename(ecarte, RACINE)
        subprocess.run(["sudo", "systemctl", "start", "dfm"], capture_output=True)
        return 1
    fiches, souci = _verifier(RACINE)
    subprocess.run(["sudo", "systemctl", "start", "dfm"], capture_output=True)
    if fiches is None:
        print("  ATTENTION : DFM est redemarre, mais la chaine ne se verifie pas.")
        print("  " + souci)
        print("  L'installation precedente est intacte dans %s" % ecarte)
        return 1
    for f in fiches:
        print("  %-16s %5d entrees   %s"
              % (f["marque"], f["entrees"],
                 "chaine intacte" if f["intacte"] else "CHAINE ROMPUE"))
    print("  DFM a ete restaure et redemarre.")
    print("  L'installation precedente reste dans %s — a effacer vous-meme" % ecarte)
    print("  quand vous serez sur de vous.")
    return 0


if __name__ == "__main__":
    print()
    print("  RESTAURATION DE DFM")
    print("  " + "-" * 52)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--liste" in sys.argv or not args:
        tous = instantanes()
        if not tous:
            print("  Aucun instantane. Lancer sauvegarde.py d'abord.")
            sys.exit(1)
        print("  Instantanes disponibles :")
        for n in tous:
            print("    " + n)
        print()
        print("  venv/bin/python restaurer.py <instantane>")
        sys.exit(0)
    sys.exit(restaurer(args[0], "--sur-place" in sys.argv, "--je-confirme" in sys.argv))
