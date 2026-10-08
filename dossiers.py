"""Retrouver un dossier Drive par IDENTIFIANT, avec secours par nom.

POURQUOI CE MODULE EXISTE
-------------------------
Historiquement, DFM cherchait ses dossiers de travail (Factures, Attestations,
Emargement, Templates) par leur NOM, sur l'ensemble du Drive, et prenait le
PREMIER resultat. Tant qu'il n'y avait qu'un organisme, cela marchait.

Depuis le cloisonnement, il existe DEUX dossiers de chaque nom — un par
organisme — et la recherche prenait le premier venu. Une facture DSF pouvait
donc etre rangee chez Smileclub, et un emargement Smileclub chez DSF, sans le
moindre message. Ce sont des pieces comptables et des preuves Qualiopi qui
franchissaient la frontiere entre deux entites juridiques distinctes.

Chaque organisme porte desormais l'IDENTIFIANT de ses dossiers dans sa fiche.
Un identifiant ne change jamais : le proprietaire peut renommer le dossier,
le deplacer, le ranger ailleurs — DFM continue de le trouver.

CE QUI GARANTIT QU'ON NE CASSE RIEN
-----------------------------------
Trois filets, dans cet ordre :

1. L'identifiant de la fiche, s'il est present ET si le dossier existe encore.
   On VERIFIE qu'il repond : un dossier mis a la corbeille pendant un menage
   ne doit pas faire echouer une generation.
2. A defaut, l'ancienne recherche par nom — le comportement d'avant, a
   l'identique. Une fiche incomplete ne bloque donc jamais rien.
3. Si ce secours trouve PLUSIEURS dossiers du meme nom, il le DIT. Avant, il
   choisissait en silence ; c'est precisement ce qui a permis au defaut de
   passer inapercu.

Le secours est un filet, pas un mode de fonctionnement : quand il se declenche,
le message invite a completer la fiche de l'organisme.
"""

_TYPE_DOSSIER = "application/vnd.google-apps.folder"


def _vivant(drive, fid):
    """Le dossier repond-il encore ? Un identifiant mort ne doit pas etre suivi."""
    try:
        f = drive.files().get(fileId=fid, fields="id,trashed").execute()
        return not f.get("trashed")
    except Exception:
        return False


def trouver(drive, fiche, cle, nom, creer_dans=None, dire=print):
    """Identifiant du dossier <nom> pour l'organisme decrit par <fiche>.

    fiche      la session ou le profil : tout objet repondant a .get()
    cle        le champ qui porte l'identifiant, p. ex. "dossier_factures"
    nom        le nom historique, pour le secours, p. ex. "Factures"
    creer_dans identifiant du parent ou creer le dossier s'il n'existe nulle
               part. Sans cela, on renvoie "" plutot que de creer au hasard.

    Renvoie "" si rien n'a ete trouve : l'appelant reste maitre de la suite.
    """
    fid = ""
    try:
        fid = (fiche.get(cle) or "").strip()
    except AttributeError:
        fid = ""
    if fid and _vivant(drive, fid):
        return fid
    if fid:
        dire("   (le dossier note dans la fiche n'existe plus ; recherche par nom)")

    try:
        trouves = drive.files().list(
            q="name='%s' and mimeType='%s' and trashed=false" % (nom.replace("'", "\\'"), _TYPE_DOSSIER),
            fields="files(id,name,parents)").execute().get("files", [])
    except Exception as e:
        dire("   (recherche du dossier '%s' impossible : %s)" % (nom, str(e)[:60]))
        return ""

    if len(trouves) > 1:
        # Le defaut historique, rendu visible au lieu d'etre subi.
        dire("   ATTENTION : %d dossiers '%s' existent dans le Drive." % (len(trouves), nom))
        dire("   DFM en choisit un au hasard. Renseignez '%s' dans la fiche" % cle)
        dire("   de l'organisme (Reglages) pour lever l'ambiguite.")
    if trouves:
        return trouves[0]["id"]

    if creer_dans:
        cree = drive.files().create(
            body={"name": nom, "mimeType": _TYPE_DOSSIER, "parents": [creer_dans]},
            fields="id").execute()["id"]
        dire("   Dossier '%s' cree." % nom)
        return cree
    return ""


def racine(drive, fiche):
    """Le dossier racine de l'organisme proprietaire, deduit d'un identifiant.

    POURQUOI DEDUIRE PLUTOT QUE STOCKER. « Documents d'envoi » est le seul
    dossier de travail qui n'a jamais eu d'identifiant dans les fiches : il ne
    pouvait donc etre trouve que par son nom, et il en existe deux — un par
    organisme. Plutot que d'ajouter une valeur a saisir dans chaque profil, on
    remonte au parent d'un dossier dont l'identifiant est deja connu. Cela
    marche sans rien completer, et cela reste juste si un dossier est renomme.
    """
    for cle in ("dossier_factures", "dossier_attestations", "dossier_emargement",
                "dossier_templates", "dossier_conventions", "dossier_signees"):
        try:
            fid = (fiche.get(cle) or "").strip()
        except AttributeError:
            return ""
        if not fid:
            continue
        try:
            parents = drive.files().get(fileId=fid, fields="parents").execute().get("parents") or []
        except Exception:
            continue
        if parents:
            return parents[0]
    return ""


def sous_dossier(drive, parent, nom, creer=True, dire=print):
    """Le sous-dossier <nom> sous <parent>, cree au besoin.

    Ici la recherche par nom est LEGITIME et le restera : elle est bornee a un
    parent connu, donc sans ambiguite possible entre les deux organismes.
    """
    trouves = drive.files().list(
        q="name='%s' and '%s' in parents and mimeType='%s' and trashed=false"
          % (nom.replace("'", "\\'"), parent, _TYPE_DOSSIER),
        fields="files(id)").execute().get("files", [])
    if trouves:
        return trouves[0]["id"]
    if not creer:
        return ""
    return drive.files().create(
        body={"name": nom, "mimeType": _TYPE_DOSSIER, "parents": [parent]},
        fields="id").execute()["id"]
