from sessions import session
import journal
import sys
S = session()
args = [a for a in sys.argv[1:]]
filtre_type = None
filtre_praticien = None
limite = 100
for a in args:
    if a.isdigit():
        limite = int(a)
    elif a.startswith("type:"):
        filtre_type = a[5:].lower()
    else:
        filtre_praticien = a.lower()
lignes = journal.lire(2000)
if filtre_type:
    lignes = [l for l in lignes if filtre_type in l["type_action"].lower()]
if filtre_praticien:
    lignes = [l for l in lignes if filtre_praticien in l["praticien"].lower()]
lignes = lignes[:limite]
if not lignes:
    print("-> Aucune entree dans le journal.")
    exit()
titre = f"JOURNAL D'ACTIVITE  ({len(lignes)} entree(s))"
if filtre_type:
    titre += f"  -  type: {filtre_type}"
if filtre_praticien:
    titre += f"  -  praticien: {filtre_praticien}"
print("\n" + "=" * 68)
print("  " + titre)
print("=" * 68)
jour_courant = None
for l in lignes:
    if l["date"] != jour_courant:
        jour_courant = l["date"]
        print(f"\n  {jour_courant}")
        print("  " + "-" * 64)
    detail = f"  ({l['detail']})" if l["detail"] else ""
    montant = f"  {l['montant']} EUR" if l["montant"] else ""
    praticien = f"  {l['praticien']}" if l["praticien"] else ""
    print(f"   {l['heure']}   {l['type_action']:<32}{praticien}{montant}{detail}")
print("\n" + "=" * 68)
print("  Filtres : python3 voir_journal.py [nombre] [nom] [type:mot]")
print("  Exemple : python3 voir_journal.py wayne")
print("            python3 voir_journal.py type:relance 20")
