# -*- coding: utf-8 -*-
"""Refabrique les polices de DFM : static/polices.css et les .woff2.

    python3 fabriquer_polices.py

A LANCER SUR LE MAC, APRES AVOIR AJOUTE UNE ICONE QUELQUE PART. Ce qu'il
produit est versionne dans /static : le serveur n'a besoin ni de cet outil, ni
d'un acces a Internet.

CE QU'IL FAIT. Il recense tous les noms « ti-quelquechose » ecrits dans les
gabarits, dans le JavaScript et dans le Python ; il va chercher la police
d'icones complete et Inter ; il taille la police d'icones aux SEULES icones
employees ; il ecrit la feuille de style qui les declare.

POURQUOI CE N'EST PAS AUTOMATIQUE. Une icone employee mais absente de la
police n'affiche RIEN, et c'est silencieux : deux noms inexistants ont vecu
des mois dans DFM (« ti-building-plus » et « ti-building-off », corriges le
18/10/2026). L'outil les nomme a la fin de son passage — c'est la seule facon
de les voir.

IL LUI FAUT fontTools, qui n'est PAS une dependance de DFM :

    venv/bin/pip install fonttools brotli

CHIFFRES DU 18/10/2026 : 5 268 icones et 790 Ko dans la police d'origine, 204
icones et 37 Ko dans la notre. La feuille de style passe de 218 Ko a 11 Ko.
"""
import glob
import io
import os
import re
import subprocess
import sys
import tempfile

DOSSIER = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(DOSSIER, "static")
TABLER = "3.1.0"
BASE_TABLER = "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@" + TABLER + "/dist/"
INTER_CSS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600"
             "&display=swap")
# Les sous-ensembles qu'on garde. Le francais tient dans « latin » ; on prend
# « latin-ext » pour les noms polonais, tcheques ou turcs. Les autres
# (cyrillique, grec, vietnamien) n'ont jamais servi et le navigateur ne les
# telecharge de toute facon que s'il en a besoin.
SOUS_ENSEMBLES = ("latin", "latin-ext")
# NAVIGATEUR DECLARE : sans cela, Google renvoie du .ttf au lieu du .woff2.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def _prendre(url, cible, ua=False):
    """Telecharge par curl : le Python du Mac n'a pas les certificats."""
    cmd = ["curl", "-sfL", "-o", cible]
    if ua:
        cmd += ["-H", "User-Agent: " + UA]
    cmd.append(url)
    if subprocess.run(cmd).returncode != 0 or not os.path.getsize(cible):
        raise SystemExit("  Telechargement impossible : %s" % url)
    return cible


def icones_employees():
    """Tous les noms d'icones ecrits dans DFM, ou qu'ils soient."""
    noms = set()
    for motif in ("templates/*.html", "static/*.js", "static/*.css", "*.py"):
        for f in sorted(glob.glob(os.path.join(DOSSIER, motif))):
            # CET OUTIL S'EXCLUT LUI-MEME : ses propres commentaires citent des
            # noms d'icones en exemple, et il les signalait comme manquants.
            if os.path.basename(f) == os.path.basename(__file__):
                continue
            try:
                t = io.open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            noms |= set(re.findall(r"\bti-([a-z0-9]+(?:-[a-z0-9]+)*)\b", t))
    noms.discard("")
    return sorted(noms)


def main():
    try:
        from fontTools import subset
    except ImportError:
        raise SystemExit("  Il manque fontTools :\n"
                         "    venv/bin/pip install fonttools brotli")
    tmp = tempfile.mkdtemp(prefix="polices-")
    print("  Telechargement des sources...")
    css_src = io.open(_prendre(BASE_TABLER + "tabler-icons.min.css",
                               os.path.join(tmp, "tabler.css")),
                      encoding="utf-8").read()
    woff_src = _prendre(BASE_TABLER + "fonts/tabler-icons.woff2",
                        os.path.join(tmp, "tabler.woff2"))
    inter_css = io.open(_prendre(INTER_CSS, os.path.join(tmp, "inter.css"), ua=True),
                        encoding="utf-8").read()

    table = {m.group(1): int(m.group(2), 16) for m in re.finditer(
        r"\.ti-([a-z0-9-]+):before\{content:\"\\([0-9a-f]+)\"\}", css_src)}
    voulus = icones_employees()
    retenus = [n for n in voulus if n in table]
    absents = [n for n in voulus if n not in table]
    print("  %d icone(s) employee(s), %d trouvee(s) dans la police"
          % (len(voulus), len(retenus)))

    options = subset.Options()
    options.flavor = "woff2"
    options.desubroutinize = True
    options.layout_features = []
    options.name_IDs = ["*"]
    police = subset.load_font(woff_src, options)
    sous = subset.Subsetter(options=options)
    sous.populate(unicodes=sorted({table[n] for n in retenus}))
    sous.subset(police)
    cible = os.path.join(STATIC, "icones.woff2")
    subset.save_font(police, cible, options)
    police.close()
    print("  Police d'icones : %d Ko -> %d Ko"
          % (os.path.getsize(woff_src) // 1024, os.path.getsize(cible) // 1024))

    faces = ""
    blocs = re.split(r"/\* ([a-z-]+) \*/", inter_css)
    for i in range(1, len(blocs), 2):
        nom_sous, corps = blocs[i], blocs[i + 1]
        if nom_sous not in SOUS_ENSEMBLES:
            continue
        poids = re.search(r"font-weight:\s*(\d+)", corps)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", corps)
        plage = re.search(r"unicode-range:\s*([^;]+);", corps)
        if not (poids and url and plage):
            continue
        fichier = "inter-%s.woff2" % nom_sous
        chemin = os.path.join(STATIC, fichier)
        if not os.path.exists(chemin):
            _prendre(url.group(1), chemin, ua=True)
            print("  Inter %-10s %d Ko" % (nom_sous, os.path.getsize(chemin) // 1024))
        faces += ('@font-face{font-family:"Inter";font-style:normal;font-weight:%s;'
                  'font-display:swap;\n  src:url("%s") format("woff2");\n'
                  '  unicode-range:%s}\n' % (poids.group(1), fichier, plage.group(1).strip()))

    regles = "".join('.ti-%s:before{content:"\\%04x"}\n' % (n, table[n]) for n in retenus)
    io.open(os.path.join(STATIC, "polices.css"), "w", encoding="utf-8").write(
        """/* LES POLICES DE DFM, chez nous. FICHIER FABRIQUE — ne pas modifier a la main.
 *
 * Refabriquer : python3 fabriquer_polices.py  (voir POLICES.md)
 *
 * Inter, licence SIL Open Font 1.1, (c) 2016 The Inter Project Authors
 * https://github.com/rsms/inter
 * Tabler Icons %s, licence MIT, (c) 2020-2024 Pawel Kuna
 * https://tabler.io — https://github.com/tabler/tabler-icons/blob/master/LICENSE
 * Les deux licences autorisent cet hebergement.
 *
 * POURQUOI. DFM prenait ses polices chez deux hebergeurs exterieurs, par des
 * feuilles de style QUI BLOQUENT l'affichage : celle des icones pesait 218 Ko
 * et amenait une police de 809 Ko pour %d icones sur les %d qu'elle contient,
 * et celle d'Inter etait revalidee chez Google tous les jours. Tout est servi
 * par DFM, les icones reduites aux seules employees, et plus aucun tiers n'est
 * sur le chemin d'une page.
 */
%s@font-face{font-family:"tabler-icons";font-style:normal;font-weight:400;
  src:url("icones.woff2") format("woff2");font-display:block}
.ti{font-family:"tabler-icons" !important;speak:none;font-style:normal;font-weight:normal;
  font-variant:normal;text-transform:none;line-height:1;-webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale}
%s""" % (TABLER, len(retenus), len(table), faces, regles))
    print("  Feuille de style : %d Ko"
          % (os.path.getsize(os.path.join(STATIC, "polices.css")) // 1024))

    if absents:
        print()
        print("  ATTENTION : %d nom(s) d'icone n'existe(nt) pas dans Tabler %s."
              % (len(absents), TABLER))
        print("  Ces icones n'affichent RIEN, et personne ne le voit :")
        for n in absents:
            print("     ti-%s" % n)
        return 1
    print("  Aucune icone manquante.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
