"""Met a l'abri ce que DFM garde en local, et lui seul.

POURQUOI CE SCRIPT EXISTE. Tant que l'essentiel vivait chez Google, le Drive
faisait office de filet : un disque perdu ne perdait rien. Depuis le chantier
d'independance, l'identite des organismes — logo, signature, tampon — et les
registres Qualiopi vivent sur ce Mac, et NULLE PART AILLEURS.

CE QUE macOS PROTEGE DEJA, et ce qu'il ne protege pas. Verifie le 17/08/2026 :
des instantanes APFS locaux sont pris toutes les heures, et ils rattrapent une
suppression accidentelle. Mais ils vivent SUR LE MEME DISQUE. Time Machine est
bien configure sur « My Passport » et inclut DFM — encore faut-il que le disque
soit branche, ce qu'il n'etait pas ce jour-la.

CE SCRIPT NE REMPLACE PAS TIME MACHINE. Il produit une archive datee, minuscule
— 412 Ko le jour de son ecriture —, qu'on peut poser n'importe ou : le Drive,
une cle, un mail. C'est le filet du filet.

LES SECRETS NE SONT PAS INCLUS PAR DEFAUT. « credentials.json » et
« token.json » ouvrent votre compte Google ; les mettre dans une archive qu'on
depose sans y penser serait leur faire quitter cette machine. L'option existe,
elle se demande : --avec-secrets.

    python3 sauvegarde_locale.py [--avec-secrets] [--vers <dossier>]
"""
import os
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from urllib.parse import quote

DOSSIER = os.path.dirname(os.path.abspath(__file__))

# Ce qui ne se reconstitue pas. Volontairement nomme un par un : une sauvegarde
# « tout le dossier » embarquerait le venv, les PDF et les copies .avant-XX,
# et deviendrait trop lourde pour etre faite souvent — donc ne serait pas faite.
CONTENU = [
    "identite",                      # logo, signature, tampon de chaque organisme
    "justificatifs",                 # pieces jointes des veilles
    "profils",                       # les fiches d'organisme
    "profil.json", "sessions.json", "formations.json", "clients.json",
    "reclamations.json",             # le registre numerote
    "qualiopi_consignations.json",   # les registres du referentiel
    "veille_sources.json",           # les sources declarees
    "factures.json",                 # la numerotation, qui ne se rejoue pas
    "questionnaires_etat.json", "parametres.json", "mails.json",
    # AJOUTES LE 19/08/2026. Ils manquaient, et deux d'entre eux sont le coeur
    # de DFM depuis les chantiers de la semaine :
    "dfm.db",                        # journal scelle, suivi, etat des sessions
    "formateurs.json",               # le registre partage des intervenants
    "attestations.json",             # la numerotation AT2026-xxx, qui ne se rejoue pas
    "bibliotheque.json", "communications.json", "campagnes.json",
    "marqueurs.json", "auto.json", "questionnaires_figes",
    # LES DOCUMENTS PRODUITS ET DEPOSES. Conventions, factures, attestations,
    # emargements, CV et diplomes des formateurs, programmes et RIB.
    # 4,7 Mo — les caches en sont exclus, voir CACHES ci-dessous.
    "documents",
]

# CE QU'ON N'EMPORTE PAS, ET POURQUOI. Ce sont des COPIES : le cache des pieces
# reflete des originaux qui vivent ailleurs, les vignettes se refabriquent en
# une seconde, la corbeille contient ce qu'on a deja ecarte. Les inclure ferait
# passer l'archive de 5 Mo a 60 Mo pour ne rien proteger de plus.
CACHES = ("documents/_pieces", "documents/_vignettes", "documents/_corbeille")

# « smtp.json » porte les mots de passe d'envoi. Il rejoint les secrets pour la
# meme raison que les autres : une archive qu'on depose sans y penser ne doit
# pas emporter de quoi ecrire du courrier au nom de vos organismes.
SECRETS = ["credentials.json", "token.json", "config.py", "smtp.json",
           # LA CLE DES SCELLES. Sans elle, le journal reste lisible mais
           # INVERIFIABLE : plus rien ne prouve qu'aucune ligne n'a bouge, et
           # c'est precisement ce qu'un audit regarde. Elle est classee dans les
           # secrets — elle signe au nom de l'organisme — mais une sauvegarde
           # sans elle laisse la piste d'audit orpheline. A conserver A PART,
           # et pas dans la meme archive que le journal qu'elle scelle.
           "scellement.json"]


def _ajouter_base(z, chemin, base):
    """LA BASE S'ARCHIVE PAR UNE PHOTO, JAMAIS PAR LE FICHIER — 31/10/2026.

    Cette archive se fabrique DANS le processus de DFM, celui qui tient la base
    ouverte. Or, sous Linux, ouvrir puis refermer un fichier a la main annule
    tous les verrous que ce processus avait sur lui. SQLite ne le sait pas : le
    script suivant se croit seul, et en partant il SUPPRIME le journal de la
    base (dfm.db-wal) sous les pieds de DFM. Celui-ci continue d'ecrire dans un
    fichier disparu, et repond « database disk image is malformed » alors que
    la base est saine, jusqu'a la prochaine relance.

    Reproduit le 31/10/2026 dans un dossier jetable. Les dates collent : la
    sauvegarde de 19h30, puis la panne au passage de 8h30 le lendemain.

    Et la photo est juste : le fichier seul laissait de cote ce qui etait encore
    dans le journal de la base.
    """
    with tempfile.TemporaryDirectory(prefix="dfm-photo-") as dossier:
        photo = os.path.join(dossier, "photo.db")
        source = sqlite3.connect("file:%s?mode=ro" % quote(chemin), uri=True)
        copie = sqlite3.connect(photo)
        source.backup(copie)
        copie.close()
        source.close()
        z.write(photo, os.path.relpath(chemin, base))
    return 1


def _ajouter(z, chemin, base):
    if chemin.endswith(".db"):
        return _ajouter_base(z, chemin, base)
    if os.path.isfile(chemin):
        z.write(chemin, os.path.relpath(chemin, base))
        return 1
    n = 0
    for racine, dossiers, fichiers in os.walk(chemin):
        # LES CACHES NE SONT PAS EMPORTES. On coupe la descente ici plutot que
        # de filtrer fichier par fichier : os.walk ne visite alors meme pas
        # 52 Mo de pieces dont l'original vit ailleurs.
        rel = os.path.relpath(racine, base)
        if any(rel == c or rel.startswith(c + os.sep) for c in CACHES):
            dossiers[:] = []
            continue
        dossiers[:] = [d for d in dossiers
                       if not any(os.path.join(rel, d) == c for c in CACHES)]
        for f in fichiers:
            if f.startswith(".") or f.endswith(".verrou"):
                continue
            p = os.path.join(racine, f)
            z.write(p, os.path.relpath(p, base))
            n += 1
    return n


def fabriquer(vers=None, avec_secrets=False):
    """Rend (chemin de l'archive, nombre de fichiers)."""
    vers = vers or os.path.join(DOSSIER, ".sauvegardes")
    os.makedirs(vers, exist_ok=True)
    nom = "DFM-local-%s.zip" % datetime.now().strftime("%Y-%m-%d-%H%M")
    cible = os.path.join(vers, nom)
    liste = CONTENU + (SECRETS if avec_secrets else [])
    n = 0
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for x in liste:
            p = os.path.join(DOSSIER, x)
            if os.path.exists(p):
                n += _ajouter(z, p, DOSSIER)
        # Un lisez-moi DANS l'archive : dans deux ans, celui qui l'ouvre doit
        # savoir ce qu'il tient et ou le remettre.
        z.writestr("LISEZ-MOI.txt",
                   "Sauvegarde des données locales de DFM\n"
                   "Faite le %s\n\n"
                   "Ce que contient cette archive : l'identité de vos organismes\n"
                   "(logo, signature, tampon), vos registres Qualiopi, vos fiches\n"
                   "clients, sessions et formations, et la numérotation des factures.\n"
                   "Ce sont les données qui n'existent QUE sur le Mac.\n\n"
                   "Ne s'y trouvent PAS : vos documents (Drive), votre suivi\n"
                   "d'inscriptions (Sheets), vos questionnaires et signatures\n"
                   "(Supabase). Ceux-là vivent en ligne.\n\n"
                   "Pour restaurer : décompresser à la racine du dossier DFM.\n"
                   "%s\n"
                   % (datetime.now().strftime("%d/%m/%Y à %H:%M"),
                      "Les identifiants Google sont inclus dans cette archive."
                      if avec_secrets else
                      "Les identifiants Google NE SONT PAS inclus."))
    return cible, n


if __name__ == "__main__":
    avec = "--avec-secrets" in sys.argv
    vers = None
    if "--vers" in sys.argv:
        i = sys.argv.index("--vers")
        vers = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
    chemin, n = fabriquer(vers, avec)
    print("-> Sauvegarde faite : %s" % chemin)
    print("   %d fichier(s), %d Ko%s"
          % (n, os.path.getsize(chemin) // 1024,
             " — identifiants Google INCLUS" if avec else ""))
    if not avec:
        print("   (identifiants Google non inclus : --avec-secrets pour les ajouter)")
