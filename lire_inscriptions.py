from connexion import service_sheets
SHEET_ID = "1ohUbh_mYqPBTJ5Sa32eXzV7flDsY7sp97ykyKwbk9h8"
print("-> Lecture des inscriptions...")
sheets = service_sheets()
resultat = sheets.spreadsheets().values().get(
    spreadsheetId=SHEET_ID,
    range="A1:Z100"
).execute()
lignes = resultat.get("values", [])
if not lignes:
    print("Aucune donnee trouvee dans le Sheet.")
else:
    entetes = lignes[0]
    inscriptions = lignes[1:]
    print(f"{len(inscriptions)} inscription(s) trouvee(s).")
    print("=" * 50)
    for i, ligne in enumerate(inscriptions, 1):
        print(f"INSCRIPTION #{i}")
        print("-" * 30)
        for j, valeur in enumerate(ligne):
            titre = entetes[j] if j < len(entetes) else f"Colonne {j+1}"
            print(f"  {titre} : {valeur}")
    print("=" * 50)
