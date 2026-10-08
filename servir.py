"""Demarre DFM. Le meme fichier sur votre Mac et sur un serveur.

    python3 servir.py                    # local, comme avant
    DFM_HOTE=0.0.0.0 python3 servir.py   # ouvert au reseau, pour un serveur

POURQUOI CE FICHIER EXISTE. « python3 app.py » lance le serveur de developpement
de Flask, qui l'annonce lui-meme a chaque demarrage : « development server, do
not use in a production deployment ». Il traite une requete a la fois, ne survit
pas a une erreur imprevue, et n'a jamais ete ecrit pour etre expose. Tant que
DFM vivait sur 127.0.0.1, cela n'avait aucune importance. Des qu'il ecoute une
adresse publique, cela en a.

Ici, DFM est servi par waitress : du Python pur, rien a compiler, le meme
comportement sur macOS, Linux et Windows.

LA REGLE QUI NE SE CONTOURNE PAS. Si DFM ecoute ailleurs que sur cette machine
et qu'aucun mot de passe n'est pose, il REFUSE de demarrer. Ce n'est pas un
avertissement : sans cela, une seule variable d'environnement suffirait a
publier deux cents fiches de contacts, des conventions signees et des factures
sur l'internet ouvert, sans que personne s'en apercoive avant longtemps.
"""
import os
import sys

# LA SORTIE N'EST PAS TAMPONNEE. Python retient ce qu'il ecrit quand la sortie
# n'est pas un terminal — c'est-a-dire toujours, sur un serveur. Le journal
# restait vide jusqu'a l'arret du processus : au moment ou l'on cherche
# pourquoi DFM ne repond pas, c'est precisement ce qu'il ne faut pas.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

DOSSIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOSSIER)

HOTE = os.environ.get("DFM_HOTE") or "127.0.0.1"
PORT = int(os.environ.get("DFM_PORT") or 5001)
FILS = int(os.environ.get("DFM_FILS") or 6)

# Ce qui compte n'est pas le nom de l'hote mais s'il est ATTEIGNABLE D'AILLEURS.
# « localhost » et « ::1 » designent la meme machine que « 127.0.0.1 » ; tout le
# reste, y compris « 0.0.0.0 », expose DFM au reseau.
_LOCAL = ("127.0.0.1", "localhost", "::1")

# DERRIERE UN MANDATAIRE, DFM EST PUBLIC MEME SUR 127.0.0.1. C'est exactement
# l'hebergement recommande : nginx tient le domaine et le HTTPS, DFM n'ecoute
# que la machine. Sans cette variable le garde-fou ci-dessous verrait une
# installation personnelle et laisserait DFM s'ouvrir sans mot de passe au
# monde entier — la regle qui ne se contourne pas, contournee par
# l'architecture qu'on preconise. Le service systemd pose la variable ; app.py
# verifie EN PLUS a chaque requete, pour le jour ou quelqu'un l'oublie.
PROXY = (os.environ.get("DFM_PROXY") or "").strip().lower() in ("1", "oui", "true")
EXPOSE = HOTE not in _LOCAL or PROXY


def _refuser(lignes):
    print()
    print("  " + "─" * 62)
    for l in lignes:
        print("  " + l)
    print("  " + "─" * 62)
    print()
    raise SystemExit(1)


def main():
    import acces

    if EXPOSE and not acces.protege():
        # DEUX RAISONS DIFFERENTES D'ETRE JOIGNABLE, DEUX PHRASES DIFFERENTES.
        # Dire « vous ecoutez 127.0.0.1 donc vous etes joignable d'ailleurs »
        # serait faux et ferait chercher au mauvais endroit.
        pourquoi = (["Un mandataire (nginx) est annonce devant DFM : c'est lui qui",
                     "publie l'adresse, et DFM est donc joignable depuis internet",
                     "— alors qu'aucun mot de passe n'est pose."]
                    if PROXY else
                    ["Vous lui demandez d'ecouter « %s » — donc d'etre joignable" % HOTE,
                     "depuis un autre ordinateur — alors qu'aucun mot de passe n'est pose."])
        _refuser([
            "DFM REFUSE DE DEMARRER.",
            "",
        ] + pourquoi + [
            "",
            "En l'etat, quiconque trouve l'adresse lirait vos contacts, vos",
            "conventions signees et vos factures.",
            "",
            "Posez un mot de passe, puis relancez :",
            "",
            "    python3 mot_de_passe.py",
        ])

    from app import app

    print()
    print("  DFM — %s" % ("SERVEUR, joignable depuis le reseau" if EXPOSE else "local"))
    print("  http://%s:%d" % ("127.0.0.1" if not EXPOSE else HOTE, PORT))
    if EXPOSE:
        print("  Mot de passe : actif.")
    elif not acces.protege():
        print("  Aucun mot de passe — sans risque tant que DFM reste sur cette machine.")

    # LE PLANIFICATEUR DEMARRE ICI AUSSI. app.py ne le lance que sous
    # « __main__ », qui n'est pas atteint quand on passe par waitress : sans
    # cette ligne, le guet des signatures et la sauvegarde quotidienne
    # s'arreteraient le jour meme du demenagement, sans un message.
    try:
        import planificateur as plan
        if plan.demarrer():
            print("  Planificateur actif : guet toutes les %d min, passage a %s,"
                  % (plan.GUETTEUR_SECONDES // 60,
                     " et ".join("%dh%02d" % h for h in plan.PASSAGE_HEURES)))
            print("  sauvegarde a %dh%02d." % plan.SAUVEGARDE_HEURE)
    except Exception as e:
        print("  Planificateur non demarre : %s" % str(e)[:110])

    try:
        from waitress import serve
    except ImportError:
        _refuser(["waitress n'est pas installe.",
                  "", "    pip install waitress"])

    # LE MANDATAIRE EST SUR LA MEME MACHINE, ON LE DECLARE DE CONFIANCE.
    # Sans cela waitress efface les X-Forwarded-* qu'il pose, et DFM croit que
    # toutes ses requetes viennent de 127.0.0.1, en clair : l'adresse du
    # visiteur est perdue et le HTTPS invisible.
    reglages = {}
    if PROXY:
        reglages = dict(trusted_proxy="127.0.0.1", trusted_proxy_count=1,
                        trusted_proxy_headers={"x-forwarded-for",
                                               "x-forwarded-proto",
                                               "x-forwarded-host"})

    print("  Ctrl+C pour arreter")
    print()
    serve(app, host=HOTE, port=PORT, threads=FILS,
          # Le nom annonce dans les en-tetes. Sans lui, waitress publie sa
          # version, ce qui renseigne gratuitement sur ce qui tourne.
          ident="DFM", **reglages)


if __name__ == "__main__":
    main()
