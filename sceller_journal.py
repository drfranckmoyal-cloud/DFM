"""Poser le scelle sur les journaux existants, et proteger l'onglet.

    python3 sceller_journal.py            # montre ce qui serait fait
    python3 sceller_journal.py --ecrire   # le fait

A LANCER UNE FOIS. Les entrees ecrites ensuite sont scellees a la volee par
journal.ecrire().

CE QUE CE SCELLE RETROACTIF ATTESTE : l'etat des entrees LE JOUR OU IL EST
POSE. Rien avant. La date de pose est enregistree et reste affichee sur l'ecran
de verification — sans elle, la chaine laisserait croire a une continuite
depuis l'origine, ce qui serait faux.

NE TOUCHE A AUCUNE DONNEE EXISTANTE : ce script n'ecrit que dans la colonne J,
vide jusqu'ici, et pose une protection avec avertissement sur l'onglet.
"""
import json
import sys
from datetime import datetime

import journal
import scellement
from connexion import service_sheets

ECRIRE = "--ecrire" in sys.argv
sh = service_sheets()
aujourdhui = datetime.now().strftime("%d/%m/%Y")

print()
print("  SCELLEMENT DES JOURNAUX")
print("  " + "-" * 62)
if not ECRIRE:
    print("  Simulation. Relancez avec --ecrire pour appliquer.")
    print()

for marque, feuille in journal._feuilles():
    valeurs = sh.spreadsheets().values().get(
        spreadsheetId=feuille, range="'Journal'!A2:J10000").execute().get("values", [])
    deja = len([b for b in valeurs if len(b) > 9 and str(b[9]).strip()])
    utiles = [(i + 2, b) for i, b in enumerate(valeurs)
              if b and str(b[0]).strip()]
    print("  %s" % marque)
    print("     %d entrees, %d deja scellees" % (len(utiles), deja))
    if not utiles:
        print("     rien a faire")
        continue

    # Sauvegarde avant toute ecriture : le journal est la piece qu'on ne peut
    # pas reconstituer.
    if ECRIRE:
        import os
        coffre = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sauvegardes")
        os.makedirs(coffre, exist_ok=True)
        chemin = os.path.join(coffre, "journal-%s-%s.json" % (
            "".join(c for c in marque if c.isalnum()) or "of",
            datetime.now().strftime("%Y%m%d-%H%M%S")))
        import fichiers
        fichiers.ecrire(chemin, valeurs)
        print("     sauvegarde -> %s" % chemin)

    precedent = scellement._RACINE
    colonne = []
    dernier_rang = 0
    for rang, brute in utiles:
        while len(colonne) < rang - 2:
            colonne.append([""])          # lignes vides intercalees
        pose = scellement.empreinte(rang, brute[:9], precedent)
        colonne.append([pose])
        precedent = pose
        dernier_rang = rang

    if not ECRIRE:
        print("     poserait %d scelles, jusqu'a la ligne %d" % (len(utiles), dernier_rang))
        continue

    # L'onglet peut n'avoir que les neuf colonnes d'origine : Google refuse
    # alors d'ecrire en J, meme vide. On l'elargit avant, jamais apres.
    meta = sh.spreadsheets().get(spreadsheetId=feuille).execute()
    props = next((x["properties"] for x in meta["sheets"]
                  if x["properties"]["title"] == "Journal"), None)
    largeur = ((props or {}).get("gridProperties") or {}).get("columnCount") or 0
    if props and largeur < 10:
        sh.spreadsheets().batchUpdate(spreadsheetId=feuille, body={"requests": [{
            "appendDimension": {"sheetId": props["sheetId"], "dimension": "COLUMNS",
                                "length": 10 - largeur}}]}).execute()
        print("     onglet elargi de %d a 10 colonnes" % largeur)

    sh.spreadsheets().values().update(
        spreadsheetId=feuille, range="'Journal'!J1",
        valueInputOption="RAW", body={"values": [["scelle"]]}).execute()
    sh.spreadsheets().values().update(
        spreadsheetId=feuille, range="'Journal'!J2:J%d" % (len(colonne) + 1),
        valueInputOption="RAW", body={"values": colonne}).execute()
    scellement.noter_demarrage(feuille, dernier_rang, aujourdhui)
    print("     %d scelles poses jusqu'a la ligne %d" % (len(utiles), dernier_rang))

    # Protection de l'onglet : un avertissement s'affiche a toute edition
    # manuelle. Ce n'est pas un verrou — le proprietaire du classeur reste
    # maitre chez lui — mais un geste distrait ne passe plus inapercu.
    try:
        meta = sh.spreadsheets().get(spreadsheetId=feuille).execute()
        onglet = next((x["properties"]["sheetId"] for x in meta["sheets"]
                       if x["properties"]["title"] == "Journal"), None)
        deja_protege = any(
            p.get("range", {}).get("sheetId") == onglet
            for x in meta["sheets"] for p in (x.get("protectedRanges") or []))
        if onglet is not None and not deja_protege:
            sh.spreadsheets().batchUpdate(spreadsheetId=feuille, body={"requests": [{
                "addProtectedRange": {"protectedRange": {
                    "range": {"sheetId": onglet},
                    "description": "Piste d'audit DFM — toute modification rompt le scelle",
                    "warningOnly": True}}}]}).execute()
            print("     onglet protege (avertissement a l'edition)")
        elif deja_protege:
            print("     onglet deja protege")
    except Exception as e:
        print("     protection non posee : %s" % e)

print()
if ECRIRE:
    print("  Termine. Verifiez sur /journal.")
print()
