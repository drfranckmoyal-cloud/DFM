# -*- coding: utf-8 -*-
"""Sauvegarde de DFM : un instantane par nuit, restaurable et verifie.

    venv/bin/python sauvegarde.py            # un instantane maintenant
    venv/bin/python sauvegarde.py --liste    # ce qui existe deja

CE QUE CA PROTEGE, ET CE QUE CA NE PROTEGE PAS. Les instantanes vivent sur LE
MEME DISQUE que DFM. Ils protegent contre la fausse manoeuvre, la suppression,
la corruption d'un fichier, une mise a jour qui tourne mal — c'est-a-dire la
quasi-totalite de ce qui arrive. Ils ne protegent PAS contre la perte du
serveur : pour cela il faut une copie ailleurs, et c'est `rapatrier.sh` qui la
descend sur le Mac. Les deux sont necessaires ; aucun des deux ne remplace
l'autre, et ce fichier ne pretend pas le contraire.

LES LIENS DURS SONT CE QUI REND LA CHOSE POSSIBLE ICI. `documents/` pese 75 Mo
et le disque n'a que 1,6 Go de libre (mesure du 08/10/2026) : sept copies
completes ne tiendraient pas. Avec `--link-dest`, un fichier qui n'a pas change
n'est pas recopie — il est partage avec l'instantane precedent. Sept
instantanes coutent donc 75 Mo, plus ce qui a bouge. Chacun reste pourtant une
arborescence COMPLETE : restaurer, c'est recopier un dossier, il n'y a rien a
rejouer et rien a reconstruire.

LA BASE SE COPIE PAR sqlite3.backup(), JAMAIS AU rsync. Copier `dfm.db` pendant
que DFM ecrit donne un fichier a moitie ecrit — qui s'ouvre, qui se lit, et dont
on ne decouvre le trou que le jour ou on en a besoin. C'est la meme precaution
que prend `rapatrier.sh` depuis le 20/08/2026.

CHAQUE INSTANTANE EST VERIFIE EN TANT QU'INSTANTANE. On n'inspecte pas la base
vivante : on ouvre CELLE DE LA COPIE et on lui fait recalculer la chaine du
journal. Une sauvegarde dont on n'a jamais verifie qu'elle se relit n'est pas
une sauvegarde, c'est une esperance.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

RACINE = os.path.dirname(os.path.abspath(__file__))
DESTINATION = os.path.join(os.path.dirname(RACINE), "sauvegardes")
# Ce qui ne se sauvegarde pas : reconstructible, volumineux, ou deja ailleurs.
EXCLUS = ["venv/", "__pycache__/", "node_modules/", ".git/", ".miroirs/",
          "*.pyc", ".DS_Store"]
# Marge exigee AVANT de commencer. Un disque plein pendant une sauvegarde
# laisse un instantane tronque ET une application qui ne peut plus ecrire :
# mieux vaut ne pas commencer et le dire.
LIBRE_MINIMUM_MO = 400
GARDE_QUOTIDIENS = 7
GARDE_HEBDOMADAIRES = 4


def _mo(octets):
    return octets / (1024.0 * 1024.0)


def _libre_mo(chemin):
    s = os.statvfs(chemin)
    return _mo(s.f_bavail * s.f_frsize)


def instantanes():
    """Les instantanes existants, du plus ancien au plus recent."""
    if not os.path.isdir(DESTINATION):
        return []
    noms = [n for n in os.listdir(DESTINATION)
            if os.path.isdir(os.path.join(DESTINATION, n)) and n[:2].isdigit()]
    return sorted(noms)


def _taille(chemin):
    """Rend (contenu, cout_propre), en octets.

    LES DEUX CHIFFRES NE DISENT PAS LA MEME CHOSE, et confondre les deux fait
    croire qu'un instantane quotidien coute 300 Mo. « contenu », c'est ce qu'on
    retrouve en restaurant : l'arborescence entiere. « cout propre », c'est ce
    que cet instantane occupe VRAIMENT en plus des autres — les fichiers qui ne
    sont partages avec personne. Mesure du 08/10/2026 : 307 Mo de contenu, et
    1 Mo de cout propre pour le deuxieme instantane de la journee.
    """
    contenu, propre = 0, 0
    for dossier, _sous, fichiers in os.walk(chemin):
        for f in fichiers:
            try:
                st = os.lstat(os.path.join(dossier, f))
            except OSError:
                continue
            contenu += st.st_size
            if st.st_nlink <= 1:
                propre += st.st_size
    return contenu, propre


def _photo_base(vers):
    """Une copie coherente de la base, prise pendant que DFM ecrit."""
    source = os.path.join(RACINE, "dfm.db")
    if not os.path.exists(source):
        return False, "dfm.db est introuvable."
    try:
        s = sqlite3.connect(source)
        d = sqlite3.connect(vers)
        s.backup(d)
        d.close()
        s.close()
        return True, ""
    except Exception as e:
        return False, "photo de la base impossible : %s" % str(e)[:120]


def _verifier(dossier):
    """Faire relire la chaine du journal PAR LA COPIE elle-meme.

    On lance un python dans l'instantane : il a son propre code, sa propre
    base, sa propre cle de scellement. S'il repond, la copie est utilisable —
    et c'est la seule question qui compte.
    """
    python = os.path.join(RACINE, "venv", "bin", "python")
    if not os.path.exists(python):
        python = sys.executable
    code = ("import journal, json;"
            "print(json.dumps([{'marque': f['marque'], 'entrees': f['entrees'],"
            "'intacte': bool(f['intacte'])} for f in journal.verifier()]))")
    try:
        r = subprocess.run([python, "-c", code], cwd=dossier, timeout=120,
                           capture_output=True, text=True)
    except Exception as e:
        return None, "verification impossible : %s" % str(e)[:120]
    if r.returncode != 0:
        return None, (r.stderr or "").strip().splitlines()[-1:] and \
            (r.stderr or "").strip().splitlines()[-1][:160] or "echec"
    import json as _json
    try:
        return _json.loads(r.stdout.strip().splitlines()[-1]), ""
    except Exception:
        return None, "reponse illisible de la verification"


def _rotation():
    """Garder sept quotidiens, puis un par semaine pendant un mois.

    Les liens durs rendent la conservation presque gratuite ; ce qui coute,
    c'est ce qui a change. On garde donc large, mais pas sans fin : un disque
    a 82 % ne pardonne pas l'accumulation.
    """
    tous = instantanes()
    garder = set(tous[-GARDE_QUOTIDIENS:])
    par_semaine = {}
    for n in tous[:-GARDE_QUOTIDIENS] if len(tous) > GARDE_QUOTIDIENS else []:
        try:
            quand = datetime.strptime(n[:8], "%Y%m%d")
        except ValueError:
            garder.add(n)      # nom inattendu : on n'y touche pas
            continue
        par_semaine[quand.strftime("%G-S%V")] = n
    for semaine in sorted(par_semaine)[-GARDE_HEBDOMADAIRES:]:
        garder.add(par_semaine[semaine])
    retires = []
    for n in tous:
        if n in garder:
            continue
        try:
            shutil.rmtree(os.path.join(DESTINATION, n))
            retires.append(n)
        except OSError:
            pass
    return retires


def sauvegarder():
    os.makedirs(DESTINATION, exist_ok=True)
    libre = _libre_mo(DESTINATION)
    if libre < LIBRE_MINIMUM_MO:
        print("  REFUS : il reste %d Mo sur le disque, il en faut %d."
              % (libre, LIBRE_MINIMUM_MO))
        print("  Aucune sauvegarde n'a ete prise. Faire de la place d'abord.")
        return 1

    anciens = instantanes()
    marque = datetime.now().strftime("%Y%m%d-%H%M")
    cible = os.path.join(DESTINATION, marque)
    if os.path.exists(cible):
        cible += "-b"
        marque += "-b"

    commande = ["rsync", "-a", "--delete"]
    for motif in EXCLUS:
        commande += ["--exclude", motif]
    if anciens:
        commande += ["--link-dest", os.path.join(DESTINATION, anciens[-1])]
    commande += [RACINE.rstrip("/") + "/", cible + "/"]

    print("  Instantane %s..." % marque)
    r = subprocess.run(commande, capture_output=True, text=True)
    if r.returncode != 0:
        print("  ECHEC de la copie : " + (r.stderr or "")[:200])
        shutil.rmtree(cible, ignore_errors=True)
        return 1

    ok, souci = _photo_base(os.path.join(cible, "dfm.db"))
    if not ok:
        print("  ECHEC : " + souci)
        shutil.rmtree(cible, ignore_errors=True)
        return 1

    fiches, souci = _verifier(cible)
    contenu, propre = _taille(cible)

    lignes = ["Instantane DFM", "=" * 46,
              "pris le          : " + datetime.now().strftime("%d/%m/%Y a %H:%M"),
              "source           : " + RACINE,
              "appuye sur       : " + (anciens[-1] if anciens else "(aucun, copie complete)"),
              "contenu          : %.1f Mo" % _mo(contenu),
              "cout propre      : %.1f Mo (le reste est partage)" % _mo(propre),
              ""]
    if fiches is None:
        lignes.append("VERIFICATION : ECHEC — " + souci)
        print("  ATTENTION : l'instantane est pris, mais il ne se relit pas.")
        print("              " + souci)
    else:
        lignes.append("verification du journal, FAITE SUR CETTE COPIE :")
        for f in fiches:
            lignes.append("  %-16s %5d entrees   %s"
                          % (f["marque"], f["entrees"],
                             "chaine intacte" if f["intacte"] else "CHAINE ROMPUE"))
        rompu = [f for f in fiches if not f["intacte"]]
        if rompu:
            print("  ATTENTION : la chaine du journal est rompue dans la copie.")
    lignes += ["", "Pour restaurer : venv/bin/python restaurer.py " + marque]
    with open(os.path.join(cible, "MANIFESTE.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")

    retires = _rotation()
    print("  %.0f Mo de contenu, dont %.1f Mo propres a cet instantane"
          % (_mo(contenu), _mo(propre)))
    print("  %d instantane(s) conserve(s)%s"
          % (len(instantanes()),
             (", %d retire(s)" % len(retires)) if retires else ""))
    if fiches is not None:
        for f in fiches:
            print("  %-16s %5d entrees   %s"
                  % (f["marque"], f["entrees"],
                     "chaine intacte" if f["intacte"] else "CHAINE ROMPUE"))
    print("  Il reste %d Mo sur le disque." % _libre_mo(DESTINATION))
    return 0


def lister():
    tous = instantanes()
    if not tous:
        print("  Aucun instantane.")
        return 0
    print("  %d instantane(s) dans %s :" % (len(tous), DESTINATION))
    for n in tous:
        chemin = os.path.join(DESTINATION, n)
        etat = "?"
        manifeste = os.path.join(chemin, "MANIFESTE.txt")
        if os.path.exists(manifeste):
            texte = open(manifeste, encoding="utf-8").read()
            etat = "verifie" if "chaine intacte" in texte else "A REGARDER"
        contenu, propre = _taille(chemin)
        print("    %-18s %6.0f Mo de contenu, %6.1f Mo propres   %s"
              % (n, _mo(contenu), _mo(propre), etat))
    print("  Il reste %d Mo sur le disque." % _libre_mo(DESTINATION))
    return 0


if __name__ == "__main__":
    print()
    print("  SAUVEGARDE DE DFM")
    print("  " + "-" * 52)
    sys.exit(lister() if "--liste" in sys.argv else sauvegarder())
