"""Convention a signer, en PDF, produite AVANT l'envoi du lien de signature.

Le praticien doit pouvoir lire ce qu'il signe. Jusqu'ici la convention n'existait
qu'APRES la signature (generer_convention_signee.py, etape 6) : au moment du
clic, il n'y avait rien a lui montrer.

Ce script produit exactement le meme document que la version signee. La seule
difference tient a l'emplacement de la signature : la version signee y insere
l'image, celle-ci laisse le cadre vide, avec sa mention discrete. Le contenu contractuel
est identique — c'est convention.py qui l'etablit, une fois pour les deux.

PLUS DE GOOGLE DOCS : le PDF est rendu localement par Chrome (convention.py et
pdf.py). Ce qui disparait par praticien : la copie du modele, le remplacement
des balises et l'export PDF par le Drive.

LE PDF N'EST PLUS PARTAGE PUBLIQUEMENT : verifie le 17/08/2026, aucun modele de
mail n'envoie son adresse. Il est range par la couche « documents », qui l'ecrit
en local et en pousse une copie d'archive.

NON BLOQUANT : un echec ici ne doit jamais empecher le mail de signature de
partir. Un praticien sans lien est un probleme plus grave qu'une convention
qu'il ne peut pas relire.

    python3 generer_convention_apercu.py [code_session]
"""
from sessions import session
import convention
import pdf as _pdf
from datetime import datetime
import sys
import suivi

CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "la convention est unique et etablie au nom du client.")
print(f"-> Session : {S['nom_formation']} ({S['code']})")

def nom_pdf(nom_prenom):
    return f"Convention a signer - {nom_prenom}.pdf"



print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
# Ceux qui vont recevoir le lien : le mail 1 n'est pas encore parti.
a_faire = [l for l in lignes
           if not l["mail1_envoye_le"]
           and not l["annule_le"]
           and not l["annulation_demandee_le"]
           and "recontact" not in l["demande"].lower()
           and not (l["file_attente_le"] and not l["promu_le"])]
if not a_faire:
    print("-> Aucune convention a preparer.")
    raise SystemExit(0)

# Dossier de session, sous « Conventions generees »
import documents

date_jour = datetime.now().strftime("%d/%m/%Y")
compte, echecs = 0, 0
for ligne in a_faire:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    cible = nom_pdf(nom_prenom)
    # Deja prepare ? On ne refait pas : le lien deja envoye doit rester valide.
    # DEJA PREPARE ? On interroge la couche, pas le Drive : le document
    # existe des qu'il est range, meme si sa copie d'archive n'est pas partie.
    if documents.chemin(documents.reference(CODE, "convention", cible)):
        print(f"   . {nom_prenom} : deja prepare.")
        continue
    print(f"-> {nom_prenom}...")
    try:
        contenu, souci = convention.fabriquer(CODE, ligne=ligne)
        if not contenu:
            print("   " + souci)
            echecs += 1
            continue
        ref, lien, _souci = documents.ranger(CODE, "convention", cible, contenu)
        if not ref:
            print("   " + _souci)
            echecs += 1
            continue
        # PLUS DE PARTAGE PUBLIC. Le praticien ne recoit plus un lien vers le
        # Drive : la convention part en PIECE JOINTE du mail de signature. Ce
        # message annoncait « partage » alors que le code ne partageait plus —
        # il disait le contraire de ce qui se passait.
        print("   PDF pret, range en local%s." % (" et copie dans le Drive" if lien else ""))
        compte += 1
    except Exception as e:
        echecs += 1
        print(f"   ECHEC pour {nom_prenom} : {str(e)[:120]}", file=sys.stderr)

if compte:
    try:
        import journal
        journal.ecrire("Conventions preparees", "", f"{compte} document(s) a signer",
                       "", S["code"])
    except Exception:
        pass
print(f"-> Termine : {compte} convention(s) preparee(s)"
      + (f", {echecs} en echec." if echecs else "."))
# Sortie 0 meme en cas d'echec partiel : l'etape est non bloquante et le mail
# de signature doit partir quoi qu'il arrive.
raise SystemExit(0)
