# Les journees de la session, mises en forme une fois pour tout le document.
def _resume_jours(S):
    try:
        import jours as _J
        r = _J.resume(S or {})
        if not r["jours"]:
            return {}
        return {"date_debut": _J._d(r["date_debut"]).strftime("%d/%m/%Y"),
                "date_fin": _J._d(r["date_fin"]).strftime("%d/%m/%Y"),
                "jours_formation": "\n".join(r["detail"]),
                "nb_jours": str(r["nb"]),
                "duree_texte": "%s heures" % r["duree"]}
    except Exception:
        return {}


"""Facture UNIQUE d'une session client, au nom de la structure.

    python3 generer_facture_client.py <code_session>

UNE SEULE FACTURE, pas une par praticien : c'est le centre qui achete, et c'est
lui qui reglera. Le montant est le tarif MULTIPLIE par le nombre de
participants — l'erreur la plus couteuse de tout ce chantier serait d'y laisser
le prix unitaire.

CE QUI DECLENCHE : la signature du representant, relevee sur la fiche de
session. Une facture emise avant la signature engagerait la comptabilite sur un
engagement que personne n'a pris.

CE SCRIPT N'ENVOIE RIEN. Il fabrique la piece et l'inscrit au registre ;
generer_convention_client_signee.py l'attache au meme mail que la convention
contresignee, pour que le centre recoive les deux ensemble.

FACTURE NON ACQUITTEE : contrairement au parcours individuel, ou la facture
n'est editee qu'apres reception du paiement, celle-ci part AVANT. Elle porte
donc « A regler a reception », jamais « Facture acquittee ».

NON BLOQUANT : un echec ici ne doit pas arreter le pipeline.
"""
import sys
from datetime import datetime

from googleapiclient.http import MediaInMemoryUpload

from connexion import service_drive
from sessions import session, balises_identite, est_client, client_de
import suivi
import dossiers
import factures as reg

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CODE = ARGS[0] if ARGS else None
FORCER = "--forcer" in sys.argv
S = session(CODE)
print(f"-> Session : {S['nom_formation']} ({S['code']})")

if not est_client(CODE):
    print("-> Session individuelle : la facturation suit les paiements, un par un.")
    raise SystemExit(0)

import sessions as _S
_BRUTES = _S._charger_json(_S._FICHIER_S)
_fiche_brute = dict(_BRUTES.get(CODE) or {})

if not str(_fiche_brute.get("convention_client_signee_le") or "").strip():
    print("-> Convention non signee. Aucune facture n'est emise.")
    raise SystemExit(0)

deja = str(_fiche_brute.get("facture_client_numero") or "").strip()
if deja and not FORCER:
    print(f"-> Facture {deja} deja emise pour cette session. Rien n'est refait.")
    print("   Un numero de facture ne se reattribue pas. Pour un cas particulier : --forcer")
    raise SystemExit(0)

import clients as CL
identifiant_client = client_de(CODE)
fiche_client = CL.client(identifiant_client) or {}
raison = (fiche_client.get("raison_sociale") or "").strip()
if not raison:
    print("-> Client introuvable ou sans raison sociale. Rien a facturer.")
    raise SystemExit(0)
manques = CL.complet(fiche_client)
if manques:
    print("-> Fiche client incomplete : " + ", ".join(manques))
    print("   Une facture incomplete n'est pas une piece comptable valable.")
    raise SystemExit(0)

lignes = [l for l in suivi.lire_lignes_de(CODE) if not l["annule_le"]]
if not lignes:
    print("-> Aucun participant. Rien a facturer.")
    raise SystemExit(0)

try:
    unitaire = float(str(S.get("tarif") or 0).replace(",", ".").replace(" ", ""))
except ValueError:
    unitaire = 0.0
nb = len(lignes)
total = unitaire * nb
print(f"-> {unitaire:.0f} EUR x {nb} participant(s) = {total:.0f} EUR")

# LE DRIVE EST FACULTATIF DEPUIS LE 18/08/2026 : il ne sert plus qu'a verifier
# la numerotation contre les factures deja posees, et cette verification a deux
# sources locales qui suffisent. Le rangement, lui, passe par « documents ».
drive = None
dossier_factures = None
try:
    drive = service_drive()
    dossier_factures = dossiers.trouver(drive, S, "dossier_factures", "Factures")
    if not dossier_factures:
        print("-> Dossier 'Factures' introuvable dans le Drive. Numerotation locale.")
except Exception as _e:
    print("-> Drive injoignable : la numerotation se lit en local. (%s)" % str(_e)[:70])
ORG = (S.get("organisme_code") or "").strip()

numero = reg.prochain_numero(ORG, drive=drive, dossier=dossier_factures)
print(f"-> Serie de {ORG or '(inconnu)'} : {numero}")

import html as htmlmod
titre = htmlmod.unescape(S.get("titre_complet") or S.get("nom_formation") or "")
date_jour = datetime.now().strftime("%d/%m/%Y")
try:
    # La mise en forme du RIB est desormais dans facture.py — une ligne vide
    # plutot qu'un « IBAN :   —   BIC : » sans valeur. Le SCRIPT garde
    # l'avertissement : c'est lui qu'on lit dans le rapport de synchronisation.
    if not (balises_identite(S).get("{{iban}}") or "").strip():
        print("   ATTENTION : aucun IBAN dans la fiche de l'organisme.")
        print("   La facture partira sans coordonnees de virement.")
    # LE DOCUMENT EST FABRIQUE EN LOCAL. Ce qui disparait ici : la copie du
    # modele, le remplacement des balises et l'export PDF par le Drive.
    import facture as _fac
    pdf = _fac.fabriquer(
        S, numero, raison, unitaire, nb,
        mention_reglement="À régler à réception",
        ligne_reglement="Par virement sur le compte ci-dessous.")


    nom_pdf = f"Facture {numero} - {raison}.pdf"
    # LE RANGEMENT PASSE PAR LA COUCHE « documents » : ce script ne nomme plus
    # ni dossier Drive ni chemin de disque.
    import documents
    ref, lien, _souci = documents.ranger(CODE, "facture", nom_pdf, pdf)
    if not ref:
        print("   ECHEC : " + _souci, file=sys.stderr)
        raise SystemExit(0)
    if not lien:
        print("   Facture rangee en local ; copie Drive non partie : " + _souci)
    print("-> Facture prete : " + lien)

    # AU REGISTRE, avant la fiche de session : c'est lui la piece durable.
    reg.enregistrer(numero, ORG, identifiant_client, raison, CODE, titre, total,
                    participants=nb, unitaire=unitaire, lien=lien,
                    type_facture="client")

    if _fiche_brute:
        _fiche_brute["facture_client_numero"] = numero
        _fiche_brute["facture_client_lien"] = lien
        _fiche_brute["facture_client_le"] = date_jour
        _S.enregistrer_session(CODE, _fiche_brute)

    # Le plafond OPCO se juge sur l'annee de FACTURE, pas de session.
    plafond = CL.plafond(fiche_client)
    if plafond:
        cumul = reg.cumul_client(identifiant_client)
        reste = plafond - cumul
        print("-> Plafond OPCO : %.0f EUR | facture cette annee : %.0f | reste %.0f"
              % (plafond, cumul, reste))
        if reste < 0:
            print("   ATTENTION : le plafond annuel est DEPASSE de %.0f EUR." % -reste)

    try:
        import journal
        journal.ecrire("Facture client éditée", raison,
                       f"{numero} — {nb} participant(s), {total:.0f} EUR", "", S["code"])
    except Exception:
        pass
except Exception as e:
    print(f"   ECHEC : {str(e)[:160]}", file=sys.stderr)
raise SystemExit(0)
