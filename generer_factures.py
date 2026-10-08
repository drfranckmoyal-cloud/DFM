from connexion import service_drive
from sessions import session, balises_identite
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime
import html
import re
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "la facture est unique et etablie au nom du client.")
# LE DRIVE EST FACULTATIF DEPUIS LE 18/08/2026. Il ne sert plus qu'a une chose
# ici — verifier la numerotation contre les factures deja posees — et cette
# verification a desormais deux sources locales qui suffisent. Ouvrir la
# connexion au chargement faisait mourir le script avant meme qu'il sache s'il
# avait une facture a produire.
drive = None
try:
    drive = service_drive()
except Exception as _e:
    print("-> Drive injoignable : la numerotation se lit en local. (%s)" % str(_e)[:70])
annee = datetime.now().year
print(f"-> Session : {S['nom_formation']} ({S['code']})")
print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
a_facturer = [l for l in lignes if l["paiement_recu_le"] and not l["facture_le"]]
if not a_facturer:
    print("-> Aucune facture a generer.")
    exit()
print(f"-> {len(a_facturer)} facture(s) a generer.")
# Par IDENTIFIANT, pris sur la fiche de l'organisme proprietaire de la session.
# Une facture est une piece comptable : elle ne doit jamais tomber dans les
# comptes de l'autre entite, ce que la recherche par nom permettait.
#
# SON ABSENCE N'ARRETE PLUS RIEN. Ce dossier ne sert qu'a la verification de
# numerotation ; le rangement, lui, passe par « documents » et vit sur le
# disque. On s'arretait ici faute d'un dossier dont on n'avait plus besoin.
dossier_factures = None
if drive:
    print("-> Recherche du dossier Factures...")
    import dossiers
    dossier_factures = dossiers.trouver(drive, S, "dossier_factures", "Factures")
    if not dossier_factures:
        print("   Dossier 'Factures' introuvable dans le Drive. Numerotation locale.")
# Le sous-dossier de session est desormais cree par la couche « documents » :
# ce script n'a plus a l'annoncer, il ne le cree plus. Les deux lignes qui le
# faisaient survivaient au branchement et parlaient de variables disparues —
# le script plantait des qu'une facture etait reellement a produire.
print("-> Recherche du dernier numero de facture...")
# SERIE PROPRE A L'ORGANISME. L'ancienne recherche balayait tout le Drive sans
# distinction : la facture F2026-008 de DSF a ainsi pris un numero dans la
# serie de Smileclub. Deux entites juridiques, deux comptabilites, deux suites
# continues et separees — c'est une obligation, pas un confort.
import factures as _reg
ORG = (S.get("organisme_code") or "").strip()
if not ORG:
    print("   ATTENTION : session sans organisme. Numerotation impossible a cloisonner.")
numero_complet = _reg.prochain_numero(ORG, drive=drive, dossier=dossier_factures, annee=annee)
prefixe = _reg.prefixe(annee)
prochain = int(numero_complet[len(prefixe):])
print(f"   Serie de {ORG or '(inconnu)'}. Prochain numero : {numero_complet}")
titre_propre = html.unescape(S["titre_complet"])
duree = S.get("duree", "14 heures")
date_jour = datetime.now().strftime("%d/%m/%Y")
compte = 0
for ligne in a_facturer:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    numero = f"{prefixe}{prochain:03d}"
    print(f"-> {numero} pour {nom_prenom}...")
    montant = ligne["montant_recu"] or S["tarif"]
    # LE DOCUMENT EST FABRIQUE EN LOCAL. Les valeurs reproduisent exactement
    # l'ancien texte : civilite « Docteur », un seul participant, et la facture
    # ACQUITTEE — elle n'est emise qu'apres paiement. Afficher un IBAN sur une
    # facture acquittee inviterait a payer deux fois.
    import facture as _fac
    pdf_bytes = _fac.fabriquer(
        S, numero, nom_prenom, float(str(montant).replace(",", ".") or 0), 1,
        civilite="Docteur ",
        paiement={"le": ligne["paiement_recu_le"],
                  "mode": ligne["mode_paiement"] or "virement",
                  "reference": ligne["reference_paiement"] or "-"})
    import documents
    nom_pdf = f"Facture {numero} - {nom_prenom}.pdf"
    ref, lien, _souci = documents.ranger(CODE, "facture", nom_pdf, pdf_bytes)
    if not ref:
        print("   ECHEC : " + _souci)
        continue
    suivi.ecrire(ligne["_numero"], "lien_facture", lien, CODE)
    suivi.marquer(ligne, "facture_le", code=CODE, detail=lien)
    # Au REGISTRE : la piece comptable survit a la suppression de la session.
    try:
        _montant = float(str(montant).replace(",", ".").replace(" ", "").replace("€", ""))
    except ValueError:
        _montant = 0.0
    _reg.enregistrer(numero, ORG, "", nom_prenom, CODE, titre_propre, _montant,
                     participants=1, unitaire=_montant, lien=lien,
                     type_facture="individuel")
    print("   PDF genere, inscrit au suivi et au registre.")
    prochain += 1
    compte += 1
print(f"-> Termine : {compte} facture(s) generee(s).")
