from connexion import service_sheets
from sessions import session, SESSIONS
S = session()
ONGLET = "Sessions"
COLONNES = ["code_session", "nom_formation", "date_debut", "date_fin", "statut_session",
            "cloture_le", "emargement_genere_le", "lien_emargement",
            "emargement_signe_le", "lien_emargement_signe", "places_max", "terminee_le", "report_le", "alerte_cloture_le"]
sheets = service_sheets()
meta = sheets.spreadsheets().get(spreadsheetId=S["sheet_suivi"]).execute()
existants = [f["properties"]["title"] for f in meta["sheets"]]
if ONGLET not in existants:
    print(f"-> Creation de l'onglet {ONGLET}...")
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=S["sheet_suivi"],
        body={"requests": [{"addSheet": {"properties": {"title": ONGLET,
              "gridProperties": {"rowCount": 200, "columnCount": len(COLONNES)}}}}]},
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
codes = sheets.spreadsheets().values().get(
    spreadsheetId=S["sheet_suivi"], range=f"'{ONGLET}'!A2:A200"
).execute().get("values", [])
connus = [c[0] for c in codes if c]
a_ajouter = []
for code, fiche in SESSIONS.items():
    if code in connus:
        continue
    a_ajouter.append([code, fiche["nom_formation"], fiche["date_debut"], fiche["date_fin"],
                      "ouverte", "", "", "", "", "", ""])
if a_ajouter:
    sheets.spreadsheets().values().append(
        spreadsheetId=S["sheet_suivi"], range=f"'{ONGLET}'!A:K",
        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
        body={"values": a_ajouter},
    ).execute()
    print(f"-> {len(a_ajouter)} session(s) ajoutee(s) :")
    for l in a_ajouter:
        print(f"   . {l[0]} ({l[4]})")
else:
    print("-> Toutes les sessions sont deja listees.")
