from connexion import service_drive

print("→ Connexion à Google (token existant)...")

service = service_drive()

print("\n✅ Connexion réussie !")
print("→ On teste l'accès à ton Google Drive...\n")

resultats = service.files().list(pageSize=5, fields="files(name)").execute()
fichiers = resultats.get("files", [])

if not fichiers:
    print("Aucun fichier trouvé (mais la connexion marche).")
else:
    print("Voici 5 fichiers de ton Drive :")
    for f in fichiers:
        print("  -", f["name"])

print("\n🎉 Tout fonctionne. DFM peut parler à Google.")