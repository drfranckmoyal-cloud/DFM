import os
import sys
import threading
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

DOSSIER = os.path.dirname(os.path.abspath(__file__))

# UN SEUL ECRAN DE CONNEXION A LA FOIS. Flask sert chaque requete dans son
# propre fil : le 14/08/2026, le jeton etant revoque, CHAQUE appel Google a
# ouvert sa propre page de consentement. Une fenetre toutes les deux secondes,
# machine inutilisable. Le verrou serialise ; le premier fil qui reussit ecrit
# le jeton, et les suivants le trouvent valide sans rien rouvrir.
_VERROU = threading.Lock()


class SansAutorisation(Exception):
    """Le jeton est mort et personne ne peut repondre a la demande.

    Vaut mieux qu'une page de connexion ouverte dans le vide : DFM lance des
    sous-processus (emargement, attestations, synchronisation) qui n'ont pas de
    terminal, et un serveur demarre en arriere-plan n'en a pas non plus.
    """

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]

def _interactif():
    """Y a-t-il quelqu'un devant un terminal pour terminer la connexion ?

    `run_local_server` ouvre une page et ATTEND le retour. Sans personne pour
    choisir un compte, elle ne rend jamais la main — et chaque nouvel appel en
    ouvre une de plus. On refuse de la lancer dans ce cas.
    """
    if os.environ.get("DFM_CONNEXION_AUTO") == "1":
        return True     # echappatoire volontaire, si un jour c'est necessaire
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except Exception:
        return False


def connexion():
    chemin_token = os.path.join(DOSSIER, "token.json")
    chemin_creds = os.path.join(DOSSIER, "credentials.json")
    creds = _charger(chemin_token)
    if creds and creds.valid:
        return creds
    with _VERROU:
        # Un autre fil a pu rendre le jeton valide pendant l'attente : on
        # relit avant de deranger qui que ce soit.
        creds = _charger(chemin_token)
        if creds and creds.valid:
            return creds
        return _obtenir(creds, chemin_token, chemin_creds)


def _charger(chemin_token):
    if not os.path.exists(chemin_token):
        return None
    try:
        return Credentials.from_authorized_user_file(chemin_token, SCOPES)
    except Exception:
        return None


def _obtenir(creds, chemin_token, chemin_creds):
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            # Une autorisation Google peut etre revoquee, ou expirer pour de
            # bon : tant que l'application reste en mode « Test » dans la
            # console Google, elle ne dure que SEPT JOURS. Jusqu'ici DFM
            # s'arretait net sur cette erreur, et la seule issue etait de
            # supprimer token.json a la main — un fichier que l'on n'ose pas
            # toucher, et pour cause. On redemande simplement l'autorisation,
            # exactement comme au tout premier lancement.
            print("-> Autorisation Google expiree ou revoquee.")
            print("   (" + str(e)[:90] + ")")
            creds = None
    if not creds or not creds.valid:
        if not _interactif():
            raise SansAutorisation(
                "L'autorisation Google a expiré ou a été révoquée, et DFM ne "
                "tourne pas dans un terminal : il ne peut pas vous demander de "
                "vous reconnecter.\n"
                "   Arrêtez DFM, puis relancez-le en double-cliquant DFM.command : "
                "une page de connexion Google s'ouvrira une seule fois.\n"
                "   (En mode « Test » dans la console Google, l'autorisation ne "
                "dure que sept jours.)")
        print("-> Une page de connexion Google va s'ouvrir dans le navigateur.")
        print("   Choisissez le compte habituel et acceptez : DFM repart ensuite seul.")
        flow = InstalledAppFlow.from_client_secrets_file(chemin_creds, SCOPES)
        creds = flow.run_local_server(port=0)
    # ECRITURE ATOMIQUE, et ce n'est pas un luxe. Ce fichier est reecrit a
    # CHAQUE rafraichissement du jeton, depuis Flask comme depuis chacun des
    # sous-processus du pipeline. Un `open(..., "w")` le vide d'abord : une
    # coupure a cet instant laisse un token.json vide, et plus rien ne
    # fonctionne — ni les Sheets, ni le Drive, ni les mails. On ecrit a cote,
    # puis on renomme : le fichier est soit l'ancien, soit le nouveau.
    import fichiers
    fichiers.ecrire_texte(chemin_token, creds.to_json())
    return creds

def service_sheets():
    return build("sheets", "v4", credentials=connexion())

def service_drive():
    return build("drive", "v3", credentials=connexion())

def service_gmail():
    return build("gmail", "v1", credentials=connexion())
