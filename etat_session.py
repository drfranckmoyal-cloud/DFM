from sessions import session
from datetime import datetime, date
import suivi
S = session()
ORDRE = ["Annulation demandee", "File d'attente", "A recontacter", "A contacter",
         "En attente signature", "Convention a generer", "Mail 2 a envoyer",
         "En attente reglement", "Reglee", "Annulee"]
lignes = suivi.lire_lignes()
debut = datetime.strptime(S["date_debut"], "%Y-%m-%d").date()
reste = (debut - date.today()).days
groupes = {}
for l in lignes:
    groupes.setdefault(suivi.calculer_statut(l), []).append(l)
attente = groupes.get("File d'attente", [])
if attente:
    print()
    print("~" * 62)
    print(f"  {len(attente)} PERSONNE(S) EN FILE D'ATTENTE")
    print("~" * 62)
    for l in sorted(attente, key=lambda x: x["file_attente_le"]):
        prevenu = "prevenu" if l["mail_attente_le"] else "PAS ENCORE PREVENU"
        print(f"    {l['prenom']} {l['nom']:<18} depuis le {l['file_attente_le'][:10]}  ({prevenu})")
    print("~" * 62)
demandes = groupes.get("Annulation demandee", [])
if demandes:
    print()
    print("!" * 62)
    print(f"  {len(demandes)} DEMANDE(S) D'ANNULATION EN ATTENTE DE VALIDATION")
    print("!" * 62)
    for l in demandes:
        print(f"    {l['prenom']} {l['nom']}")
        print(f"      demande le {l['annulation_demandee_le'][:16]}")
        print(f"      motif : {l['motif_annulation'] or 'non precise'}")
        if l["paiement_recu_le"]:
            print(f"      DEJA REGLE {l['montant_recu']} EUR le {l['paiement_recu_le'][:10]} - remboursement a prevoir")
    print("!" * 62)
print()
print("=" * 62)
print(f"  {S['nom_formation'].upper()} - {S['date_texte']}")
print(f"  Dans {reste} jour(s)  |  {S['tarif']} EUR par participant")
print("=" * 62)
if not lignes:
    print("  Aucune inscription.")
    exit()
actifs = [l for l in lignes if "recontact" not in l["demande"].lower()
          and not l["annule_le"] and not l["annulation_demandee_le"]
          and suivi.calculer_statut(l) != "File d'attente"]
regles = [l for l in actifs if l["paiement_recu_le"]]
encaisse = 0
for l in regles:
    try:
        encaisse += float(str(l["montant_recu"]).replace(",", ".") or 0)
    except ValueError:
        pass
attendu = len(actifs) * float(S["tarif"])
annules = len(groupes.get("Annulee", []))
occupation = f"{len(actifs)}/{S['places_max']}"
if len(actifs) >= S["places_max"]:
    occupation += " COMPLET"
print(f"  {occupation} place(s)  |  {len(regles)} regle(s)  |  {annules} annule(s)  |  {len(attente)} en attente")
print(f"  Encaisse : {encaisse:.0f} EUR sur {attendu:.0f} EUR attendus")
print("-" * 62)
for statut in ORDRE:
    gens = groupes.get(statut)
    if not gens:
        continue
    print(f"\n  {statut.upper()}  ({len(gens)})")
    for l in gens:
        detail = ""
        if statut == "En attente reglement" and l["mail2_envoye_le"]:
            detail = f"  - mail 2 le {l['mail2_envoye_le'][:10]}"
        elif statut == "Reglee":
            detail = f"  - {l['montant_recu']} EUR par {l['mode_paiement']}"
            if l["facture_le"]:
                detail += " - facturee"
        elif statut == "En attente signature" and l["mail1_envoye_le"]:
            detail = f"  - mail du {l['mail1_envoye_le'][:10]}"
        elif statut == "Annulee":
            detail = f"  - {l['motif_annulation'] or 'motif non precise'}"
        elif statut == "Annulation demandee":
            detail = "  - A VALIDER"
        elif statut == "File d'attente":
            detail = f"  - depuis le {l['file_attente_le'][:10]}"
            if not l["mail_attente_le"]:
                detail += " - PAS PREVENU"
        print(f"    . {l['prenom']} {l['nom']:<18}{detail}")
print("\n" + "=" * 62)
