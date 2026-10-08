from connexion import service_sheets
SHEET_ID = "1ohUbh_mYqPBTJ5Sa32eXzV7flDsY7sp97ykyKwbk9h8"
sheets = service_sheets()
resultat = sheets.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range="A1:Z100"
).execute()
lignes = resultat.get("values", [])
if not lignes:
    print("Aucune donnee dans le Sheet.")
    exit()
entetes = lignes[0]
inscriptions = lignes[1:]
def trouver_colonne(mot):
    for i, titre in enumerate(entetes):
        if mot.lower() in titre.lower():
            return i
    return -1
col_nom = trouver_colonne("NOM")
col_prenom = trouver_colonne("Prénom")
col_demande = trouver_colonne("Votre demande")
a_traiter = []
a_recontacter = []
for ligne in inscriptions:
    nom = ligne[col_nom] if col_nom < len(ligne) else "?"
    prenom = ligne[col_prenom] if col_prenom < len(ligne) else "?"
    demande = ligne[col_demande] if col_demande < len(ligne) else ""
    personne = f"{prenom} {nom}"
    if "confirme" in demande.lower():
        a_traiter.append(personne)
    elif "recontact" in demande.lower():
        a_recontacter.append(personne)
print("=" * 45)
print(f"  {len(inscriptions)} inscription(s) au total")
print("=" * 45)
print(f"DEMANDES A TRAITER ({len(a_traiter)})")
print("-" * 30)
if a_traiter:
    for p in a_traiter:
        print(f"   . {p}")
else:
    print("   (aucune)")
print(f"A RECONTACTER ({len(a_recontacter)})")
print("-" * 30)
if a_recontacter:
    for p in a_recontacter:
        print(f"   . {p}")
else:
    print("   (aucune)")
print("=" * 45)
