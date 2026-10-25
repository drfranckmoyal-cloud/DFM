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
# LA FACTURE PEUT PRECEDER LE REGLEMENT — 25/10/2026, reglage de la formation.
#
# DFM n'a jamais emis de facture avant d'avoir encaisse : « paiement_recu_le et
# pas encore facture ». Pour une formation de deux jours payee en une fois,
# c'est juste, et la facture part acquittee. Pour un cycle d'un an regle en
# quatre virements, cela voudrait dire pas de facture avant le dernier — alors
# que le praticien en a besoin des le depart pour la faire prendre en charge.
#
# COCHEE SUR LA FICHE, la facture part des que la CONVENTION EST SIGNEE, pour
# la somme entiere, A REGLER. Chaque virement recoit ensuite son recu.
# DECOCHEE, rien ne change : c'est le cas des quatre formations en service.
_FICHE_F = (__import__("sessions").FORMATIONS.get(S.get("formation") or "") or {})
AVANT_REGLEMENT = bool(_FICHE_F.get("facture_a_l_inscription"))
if AVANT_REGLEMENT:
    print("-> Facture emise des l'inscription (reglage de la formation).")
    # ELLE ATTEND LE MAIL DE CONFIRMATION — 25/10/2026, apres l'essai de Franck.
    #
    # « signe_le » seul ne suffisait pas. Le mail de confirmation, lui, a besoin
    # de la convention signee et des pieces de la session : quand l'une manque,
    # il ne part pas — et la facture, qui n'a besoin de rien, partait a sa
    # place. Franck a signe sa convention d'essai et a recu SA FACTURE au lieu
    # de sa convention signee.
    #
    # L'ORDRE EST UNE REGLE, PAS UN HASARD D'ORDONNANCEMENT : « ton inscription
    # est confirmee » precede « voici ta facture ». On l'ecrit donc dans la
    # condition, et non dans la place de l'etape au sein de dfm.py.
    a_facturer = [l for l in lignes
                  if l["signe_le"] and l["mail2_envoye_le"] and not l["facture_le"]
                  and not l.get("invite_le")
                  and suivi.calculer_statut(l) not in
                      suivi.PAS_ENCORE_INSCRIT + ("Annulee", "Annulation demandee")]
else:
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
    # LA SOMME ENTIERE QUAND LA FACTURE PRECEDE : « montant_recu » ne vaut
    # alors rien, ou un acompte. C'est le prix convenu avec la personne qu'il
    # faut, celui-la meme que porte sa convention.
    if AVANT_REGLEMENT:
        montant = suivi.montant_attendu(ligne, S.get("tarif"))
    else:
        montant = ligne["montant_recu"] or S["tarif"]
    # LE DOCUMENT EST FABRIQUE EN LOCAL. Les valeurs reproduisent exactement
    # l'ancien texte : civilite « Docteur », un seul participant, et la facture
    # ACQUITTEE — elle n'est emise qu'apres paiement. Afficher un IBAN sur une
    # facture acquittee inviterait a payer deux fois.
    import facture as _fac
    if AVANT_REGLEMENT:
        # Pas de bloc « acquittee » : la facture porte l'IBAN, comme celle
        # d'un client. Afficher un paiement qui n'a pas eu lieu serait faux ;
        # afficher les deux inviterait a payer deux fois.
        pdf_bytes = _fac.fabriquer(
            S, numero, nom_prenom, float(str(montant).replace(",", ".") or 0), 1,
            civilite="Docteur ",
            mention_reglement="À régler avant le début du dernier module",
            ligne_reglement="Par virement sur le compte ci-dessous. "
                            "Le règlement peut être échelonné ; chaque versement "
                            "donne lieu à un reçu.")
    else:
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
