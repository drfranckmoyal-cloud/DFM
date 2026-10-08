"""Fabriquer un PDF a partir de HTML, sans Google et sans rien installer.

POURQUOI CE MODULE EXISTE. Les documents de DFM passaient tous par Google :
un Docs ou un Slides copie, ses balises remplacees, puis exporte en PDF par le
Drive. Trois appels reseau, un jeton OAuth qui expire, et un modele qui vit
ailleurs que le code qui le remplit.

CE MODULE UTILISE CHROME, deja installe sur la machine, en mode sans interface.
C'est le MEME moteur que celui qui affiche DFM : ce qu'on voit a l'ecran est ce
qui sort en PDF, aux memes pixels. Mesure le 06/08/2026 : A4 paysage exact,
degrades et polices respectes, accents corrects, texte selectionnable — pas une
image — en 2,2 secondes, sans aucune dependance ajoutee.

LES ALTERNATIVES ONT ETE ECARTEES, verifiees sur cette machine :
  WeasyPrint  exigerait « brew install pango », que l'utilisateur ne peut pas
              lancer seul.
  reportlab   la mise en page se construit en code, point par point : illisible
              a relire et impossible a ajuster sans developpeur.
  Slides      c'est precisement ce qu'on remplace.

CE QUE CELA COUTE. Le modele n'est plus modifiable en glissant des cadres : il
s'edite comme une page web. C'est un choix assume, pas un oubli.
"""
import os
import shutil
import subprocess
import tempfile

_DOSSIER = os.path.dirname(os.path.abspath(__file__))

# LE FICHIER DE TRAVAIL NE VA PAS DANS /tmp — corrige le 19/08/2026, sur le
# serveur. Ubuntu livre Chromium sous forme de SNAP, et un snap est confine : il
# possede son PROPRE /tmp et ne voit pas celui du systeme. Le HTML ecrit dans
# /tmp lui etait donc invisible, et l'impression echouait — sans message utile,
# puisque Chrome se contente de ne rien produire.
#
# Verifie sur le serveur : meme document, /tmp echoue, /root reussit.
#
# On ecrit donc a cote de DFM. Cela vaut aussi sur macOS, ou rien ne l'interdit :
# un seul chemin pour les deux mondes, c'est un comportement de moins a tenir.
_TRAVAIL = os.path.join(_DOSSIER, ".travail")

# Chemins des navigateurs a base de Chromium, du plus probable au moins.
# Chrome d'abord : c'est celui qui est installe.
_CANDIDATS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


class Indisponible(Exception):
    """Aucun navigateur trouve. L'appelant doit pouvoir le DIRE plutot que
    d'echouer avec une trace incomprehensible au milieu d'un envoi."""


_choisi = None


def _repond(chemin):
    """Ce binaire est-il vraiment un navigateur ?

    ON NE SE CONTENTE PLUS DE SON EXISTENCE. Ubuntu laisse derriere lui un
    /usr/bin/chromium-browser qui n'est qu'un message d'erreur deguise en
    navigateur : il existe, il est executable, et tout ce qu'il sait faire est
    reclamer l'installation d'un snap. DFM l'aurait choisi — il vient avant
    google-chrome dans la liste — et chaque convention, chaque facture, chaque
    attestation aurait echoue. Constate sur le serveur le 19/08/2026.

    Une question a --version coute un dixieme de seconde, et la reponse est
    retenue pour toute la duree du processus.
    """
    try:
        r = subprocess.run([chemin, "--version"], capture_output=True,
                           text=True, timeout=20)
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except Exception:
        return False


def navigateur():
    global _choisi
    if _choisi:
        return _choisi
    for c in _CANDIDATS:
        if os.path.exists(c) and os.access(c, os.X_OK) and _repond(c):
            _choisi = c
            return c
    for nom in ("google-chrome", "chromium", "chromium-browser"):
        trouve = shutil.which(nom)
        if trouve and _repond(trouve):
            _choisi = trouve
            return trouve
    raise Indisponible(
        "Aucun navigateur Chrome ou Chromium trouve sur cette machine. "
        "Les documents PDF ne peuvent pas etre fabriques. "
        "Installez Google Chrome, ou signalez-le.")


def depuis_html(html, delai=60):
    """Rend les octets d'un PDF. Le format se declare dans le CSS du document.

    Le HTML passe par un FICHIER, jamais par une adresse data: — Chrome refuse
    d'imprimer ces dernieres, et le message d'erreur n'en dit rien.
    """
    exe = navigateur()
    try:
        os.makedirs(_TRAVAIL, exist_ok=True)
        dossier = tempfile.mkdtemp(prefix="dfm-pdf-", dir=_TRAVAIL)
    except Exception:
        # Si le dossier de DFM n'est pas inscriptible, on retombe sur /tmp :
        # mieux vaut un PDF qui echoue sur un snap qu'un PDF impossible partout.
        dossier = tempfile.mkdtemp(prefix="dfm-pdf-")
    source = os.path.join(dossier, "doc.html")
    cible = os.path.join(dossier, "doc.pdf")
    try:
        with open(source, "w", encoding="utf-8") as f:
            f.write(html)
        # PAS DE --user-data-dir. On l'avait ajoute par precaution, en pensant
        # que Chrome refuserait de demarrer avec une fenetre deja ouverte :
        # c'est faux, le mode sans interface s'isole tout seul. Mesure le
        # 06/08/2026, Chrome ouvert a cote : 2 secondes sans l'option, 26 avec
        # — un profil neuf declenche toute l'initialisation de premier lancement.
        # PAS DE --no-sandbox non plus : inutile ici, et cela desactive un
        # cloisonnement qui protege la machine du contenu rendu.
        # CHROME A BESOIN D'UN CHEZ-LUI INSCRIPTIBLE. Sur le serveur, le
        # service interdit l'ecriture dans /home (ProtectHome=read-only) :
        # Chrome ne peut plus creer son dossier de profil et refuse de
        # demarrer — « Failed to create headless user data directory
        # container ». Constate le 19/08/2026.
        #
        # On lui en donne un A COTE DE DFM, et surtout PERSISTANT : c'est le
        # mot qui compte. Un profil neuf a chaque document rejouerait toute
        # l'initialisation de premier lancement, mesuree a 24 secondes le
        # 06/08/2026. Ici elle est payee une seule fois, au premier PDF de la
        # machine. On le place a cote du dossier de travail, quel qu'il soit :
        # si DFM a du se replier sur /tmp, la maison de Chrome l'y suit.
        # ON NE DEPLACE LE CHEZ-LUI DE CHROME QUE S'IL N'EN A PLUS.
        #
        # Premiere version : on le deplacait toujours. Sur le Mac, Chrome a
        # aussitot cherche le trousseau a ce nouvel endroit, ne l'a pas trouve,
        # et a ouvert une FENETRE — « Impossible de trouver un trousseau pour
        # stocker Chrome ». Une fenetre, en mode sans interface : plus rien ne
        # sortait, et l'impression expirait au bout de soixante secondes.
        # Constate le 19/08/2026, sur cette machine.
        #
        # La regle est donc : on ne touche a rien tant que le chez-lui existe
        # et s'ecrit. C'est le cas sur le Mac (1,9 s par document, mesure). Sur
        # le serveur, le service interdit d'ecrire dans /home et Chrome ne peut
        # plus creer son profil — la, et la seulement, on lui en donne un a
        # cote de DFM.
        env = dict(os.environ)
        try:
            chez_lui = os.path.expanduser("~")
            if not (os.path.isdir(chez_lui) and os.access(chez_lui, os.W_OK)):
                maison = os.path.join(os.path.dirname(dossier), "chrome-maison")
                os.makedirs(maison, exist_ok=True)
                env["HOME"] = maison
        except Exception:
            pass
        r = subprocess.run(
            [exe, "--headless", "--disable-gpu",
             # Sans cela, Chrome ajoute l'URL du fichier et un numero de page
             # en haut et en bas : illisible sur un document contractuel.
             "--no-pdf-header-footer",
             # CHROME NE VA PAS CHERCHER DE TROUSSEAU. Il n'a aucun mot de
             # passe a retenir pour imprimer une page, et cette quete est
             # exactement ce qui a ouvert une fenetre bloquante sur le Mac.
             # Sous Linux elle reveille gnome-keyring, absent d'un serveur.
             "--password-store=basic",
             "--print-to-pdf=" + cible, "file://" + source],
            capture_output=True, timeout=delai, env=env)
        if not os.path.exists(cible):
            detail = (r.stderr or b"").decode("utf-8", "replace")[-300:]
            raise Indisponible("Chrome n'a produit aucun PDF. " + detail)
        with open(cible, "rb") as f:
            return f.read()
    except subprocess.TimeoutExpired:
        raise Indisponible("Chrome n'a pas rendu la main en %d secondes." % delai)
    finally:
        shutil.rmtree(dossier, ignore_errors=True)


def image_en_ligne(octets, type_mime="image/png"):
    """Une image utilisable dans le HTML sans fichier a cote.

    Le PDF doit etre fabricable sans reseau : un logo reference par une adresse
    serait absent le jour ou le Drive ne repond pas.
    """
    import base64
    if not octets:
        return ""
    return "data:%s;base64,%s" % (type_mime, base64.b64encode(octets).decode())
