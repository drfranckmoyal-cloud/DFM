"""Remplace la cle secrete Supabase dans config.py, sans editer le fichier.

    python3 changer_cle_supabase.py

POURQUOI CE SCRIPT. Modifier config.py a la main expose a trois accidents
classiques : un editeur de texte qui remplace les guillemets droits par des
guillemets typographiques, un enregistrement au format RTF, ou un espace de
trop. Chacun rend DFM muet. Ici, la cle est collee dans le Terminal, verifiee
contre Supabase AVANT d'etre ecrite, et l'ancienne est sauvegardee.

LA CLE N'EST JAMAIS AFFICHEE en clair, ni echangee autrement qu'entre votre
Terminal et votre fichier.
"""
import os
import re
import shutil
import sys
import json
import urllib.request
import urllib.error
import reseau
from datetime import datetime

DOSSIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(DOSSIER, "config.py")


def masquee(cle):
    return cle[:13] + "…" + cle[-4:] if len(cle) > 20 else "…"


def essayer(url, cle):
    """La cle repond-elle sur une table connue ? On lit un seul identifiant :
    aucune donnee n'est rapatriee, et l'echec est parlant."""
    requete = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/Contacts?select=id&limit=1",
        headers={"apikey": cle, "Authorization": "Bearer " + cle}, method="GET")
    try:
        with urllib.request.urlopen(requete, timeout=20, context=reseau.contexte()) as r:
            r.read()
        return True, ""
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode()).get("message") or ""
        except Exception:
            pass
        return False, "%s %s" % (e.code, detail[:90])
    except Exception as e:
        return False, str(e)[:90]


print("=" * 70)
print("  REMPLACEMENT DE LA CLE SECRETE SUPABASE")
print("=" * 70)

if not os.path.exists(CONFIG):
    print("config.py introuvable. Rien n'a ete fait.")
    raise SystemExit(1)

source = open(CONFIG, encoding="utf-8").read()
m_url = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', source)
m_cle = re.search(r'SUPABASE_KEY\s*=\s*"([^"]+)"', source)
if not m_url or not m_cle:
    print("config.py n'a pas la forme attendue. Rien n'a ete fait.")
    raise SystemExit(1)

url, ancienne = m_url.group(1), m_cle.group(1)
print("\n  Projet        : " + url)
print("  Cle actuelle  : " + masquee(ancienne))

ok, pourquoi = essayer(url, ancienne)
print("  Elle repond   : " + ("oui" if ok else "NON — " + pourquoi))

print("\n  Collez la NOUVELLE cle secrete (elle commence par sb_secret_),")
print("  puis Entree. Pour renoncer, tapez Entree sans rien coller.")
try:
    nouvelle = input("\n  > ").strip().strip('"').strip("'")
except (EOFError, KeyboardInterrupt):
    nouvelle = ""

if not nouvelle:
    print("\n  Abandon. config.py n'a pas ete touche.")
    raise SystemExit(0)
if nouvelle == ancienne:
    print("\n  C'est la cle deja en place. Rien a faire.")
    raise SystemExit(0)
if not nouvelle.startswith("sb_secret_"):
    print("\n  REFUS : une cle secrete commence par « sb_secret_ ».")
    print("  Celle-ci commence par « " + nouvelle[:12] + " ».")
    print("  Une cle « sb_publishable_ » n'aurait pas les droits necessaires.")
    print("  config.py n'a pas ete touche.")
    raise SystemExit(1)

print("\n  Verification aupres de Supabase...")
ok, pourquoi = essayer(url, nouvelle)
if not ok:
    print("  REFUS : cette cle ne fonctionne pas (" + pourquoi + ").")
    print("  config.py n'a pas ete touche. Verifiez la copie et recommencez.")
    raise SystemExit(1)
print("  Elle fonctionne.")

sauvegarde = CONFIG + ".avant-" + datetime.now().strftime("%Y%m%d-%H%M")
shutil.copy2(CONFIG, sauvegarde)
provisoire = CONFIG + ".en-cours"
with open(provisoire, "w", encoding="utf-8") as f:
    f.write(source.replace('"' + ancienne + '"', '"' + nouvelle + '"'))
os.replace(provisoire, CONFIG)

relu = re.search(r'SUPABASE_KEY\s*=\s*"([^"]+)"', open(CONFIG, encoding="utf-8").read())
if not relu or relu.group(1) != nouvelle:
    shutil.copy2(sauvegarde, CONFIG)
    print("  ECHEC de l'ecriture. L'ancienne configuration a ete remise en place.")
    raise SystemExit(1)

print("\n  Ecrit et relu : config.py porte bien la nouvelle cle.")
print("  Ancienne configuration conservee dans :")
print("     " + os.path.basename(sauvegarde))
print("\n  IL RESTE DEUX CHOSES A FAIRE, dans cet ordre :")
print("    1. Poser la meme cle dans Netlify, puis redeployer le site.")
print("    2. Supprimer l'ANCIENNE cle dans Supabase — seulement apres avoir")
print("       verifie qu'une signature de convention fonctionne encore.")
print("=" * 70)
