from connexion import service_sheets
from sessions import session
S = session()
NOUVELLES = ["attestation_envoyee_le"]
sheets = service_sheets()
onglet = S["onglet_suivi"]
meta = sheets.spreadsheets().get(spreadsheetId=S["sheet_suivi"]).execute()
feuille = None
for f in meta["sheets"]:
    if f["properties"]["title"] == onglet:
        feuille = f["properties"]
        break
if not feuille:
    print(f"Onglet '{onglet}' introuvable.")
    exit()
largeur = feuille["gridProperties"]["columnCount"]
print(f"-> Onglet {onglet} : {largeur} colonne(s) physique(s).")
entetes = sheets.spreadsheets().values().get(
    spreadsheetId=S["sheet_suivi"], range=f"'{onglet}'!1:1"
).execute().get("values", [[]])
entetes = [e for e in (entetes[0] if entetes else []) if e.strip()]
print(f"-> {len(entetes)} colonne(s) nommee(s).")
manquantes = [c for c in NOUVELLES if c not in entetes]
if not manquantes:
    print("-> Toutes les colonnes existent deja.")
    exit()
besoin = len(entetes) + len(manquantes)
if besoin > largeur:
    a_ajouter = besoin - largeur
    print(f"-> Agrandissement de la grille : +{a_ajouter} colonne(s).")
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=S["sheet_suivi"],
        body={"requests": [{"appendDimension": {
            "sheetId": feuille["sheetId"], "dimension": "COLUMNS", "length": a_ajouter}}]},
    ).execute()
def lettre(i):
    l = ""
    n = i + 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        l = chr(65 + r) + l
    return l
depart = len(entetes)
sheets.spreadsheets().values().update(
    spreadsheetId=S["sheet_suivi"],
    range=f"'{onglet}'!{lettre(depart)}1",
    valueInputOption="USER_ENTERED",
    body={"values": [manquantes]},
).execute()
print(f"-> {len(manquantes)} colonne(s) ajoutee(s) a partir de {lettre(depart)}1 :")
for c in manquantes:
    print(f"   . {c}")
