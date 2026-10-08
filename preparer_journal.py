from connexion import service_sheets
from sessions import session
S = session()
ONGLET = "Journal"
COLONNES = ["horodatage", "date", "heure", "type_action", "praticien",
            "session", "detail", "montant"]
sheets = service_sheets()
meta = sheets.spreadsheets().get(spreadsheetId=S["sheet_suivi"]).execute()
existants = [f["properties"]["title"] for f in meta["sheets"]]
if ONGLET not in existants:
    print(f"-> Creation de l'onglet {ONGLET}...")
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=S["sheet_suivi"],
        body={"requests": [{"addSheet": {"properties": {
            "title": ONGLET,
            "gridProperties": {"rowCount": 5000, "columnCount": len(COLONNES), "frozenRowCount": 1}}}}]},
    ).execute()
else:
    print(f"-> Onglet {ONGLET} deja present.")
actuelles = sheets.spreadsheets().values().get(
    spreadsheetId=S["sheet_suivi"], range=f"'{ONGLET}'!1:1"
).execute().get("values", [[]])
actuelles = [c for c in (actuelles[0] if actuelles else []) if c.strip()]
if not actuelles:
    sheets.spreadsheets().values().update(
        spreadsheetId=S["sheet_suivi"], range=f"'{ONGLET}'!A1",
        valueInputOption="USER_ENTERED", body={"values": [COLONNES]},
    ).execute()
    print(f"-> {len(COLONNES)} colonne(s) ecrite(s).")
else:
    print(f"-> {len(actuelles)} colonne(s) deja en place.")
