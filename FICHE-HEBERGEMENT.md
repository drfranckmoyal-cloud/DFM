# DFM — Mettre en ligne

*Écrite le 19/08/2026. Objectif : allumer n'importe quel ordinateur, taper une
adresse, travailler sur DFM — sans que le Mac personnel soit allumé.*

---

## Ce qu'il faut, et rien de plus

| | |
|---|---|
| **Une machine** | VPS Linux, 1 processeur, 1 Go de RAM, 10 Go de disque. 5 à 10 €/mois. |
| **Un domaine** | déjà acheté chez Hostinger. |
| **Chromium** | le moteur PDF de DFM. Une ligne d'installation. |
| **Python 3.11+** | 3.13 sur le Mac ; 3.11 suffit. |

**Un hébergement web classique ne convient pas** — PHP, pas de processus permanent.
Il faut un **VPS** (accès SSH, root, Ubuntu ou Debian).

**Choisir un hébergeur en France ou en Europe.** DFM détient les données
personnelles de professionnels de santé en formation. Rien ne l'impose
strictement, mais un OPCO ne vous interrogera jamais sur un hébergement français.

---

## 1. Préparer le serveur

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip chromium-browser rsync
sudo adduser --disabled-password --gecos "" dfm
```

*Chromium peut s'appeler `chromium` selon la distribution. `pdf.py` cherche
`chromium`, `chromium-browser` puis `google-chrome` dans le PATH : l'un des trois
suffit.*

## 2. Transporter DFM

Depuis le Mac, dans le dossier DFM :

```bash
rsync -av --exclude venv --exclude __pycache__ --exclude .sauvegardes \
      ./ dfm@VOTRE_SERVEUR:/home/dfm/DFM/
```

**60 Mo au total.** Les exclusions sont volontaires : l'environnement virtuel se
recrée sur place, et les sauvegardes n'ont pas à voyager.

**Les quatre secrets voyagent séparément**, jamais dans la même archive que le
reste : `credentials.json`, `token.json`, `config.py`, `smtp.json`.
Et **`scellement.json`** — la clé qui signe le journal : sans elle la piste
d'audit reste lisible mais devient invérifiable.

## 3. Installer

```bash
cd /home/dfm/DFM
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 4. Poser le mot de passe — obligatoire

```bash
venv/bin/python mot_de_passe.py
```

**DFM refuse de démarrer sur une adresse publique sans mot de passe.** Ce n'est
pas un avertissement qu'on ignore : il s'arrête, et il dit pourquoi. Sans cela,
une variable d'environnement suffirait à publier vos contacts, vos conventions
signées et vos factures.

## 5. Démarrer

```bash
DFM_HOTE=0.0.0.0 DFM_PORT=5001 venv/bin/python servir.py
```

C'est **le même fichier que sur le Mac** — `DFM.command` l'appelle aussi. Ce qui
marche chez vous marchera là-bas.

Pour qu'il redémarre tout seul après un redémarrage du serveur, un service
systemd dans `/etc/systemd/system/dfm.service` :

```ini
[Unit]
Description=DFM
After=network.target

[Service]
User=dfm
WorkingDirectory=/home/dfm/DFM
Environment=DFM_HOTE=127.0.0.1
Environment=DFM_PORT=5001
ExecStart=/home/dfm/DFM/venv/bin/python servir.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now dfm
sudo journalctl -u dfm -f     # le journal, en direct
```

*`DFM_HOTE=127.0.0.1` avec systemd : DFM n'écoute que la machine, et c'est le
reverse proxy ci-dessous qui l'expose. Une seule porte sur l'extérieur.*

## 6. HTTPS et le domaine

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

`/etc/nginx/sites-available/dfm` :

```nginx
server {
    server_name dfm.votredomaine.fr;
    client_max_body_size 25M;          # les dépôts de documents vont jusqu'à 20 Mo
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;       # la fabrication d'un PDF peut prendre du temps
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dfm /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d dfm.votredomaine.fr
```

**Chez Hostinger**, dans la zone DNS du domaine : un enregistrement `A`,
nom `dfm`, valeur l'adresse IP du serveur.

---

## Ce qui change une fois en ligne

**Les vignettes des CV disparaissent.** Elles utilisent `qlmanage`, propre à
macOS. L'écran Profils formateurs affiche l'icône du format à la place. Rien
d'autre ne change, et rien ne casse.

**La sauvegarde de DFM devient votre seul filet.** Plus de Time Machine. Elle
tourne à 19h30, garde trente jours, et pèse 4,7 Mo. **Sortez-la du serveur** —
une sauvegarde qui vit sur la machine qu'elle protège ne protège de rien :

```bash
0 21 * * * rsync -a /home/dfm/DFM/.sauvegardes/ ailleurs:/sauvegardes/dfm/
```

**Le planificateur remplace les agents launchd.** Il vit dans DFM : guet des
signatures toutes les 10 minutes, passage complet à 8h30 et 13h30, sauvegarde à
19h30. **N'emportez pas les deux `.plist`** — ils ne servent plus.

---

## Vérifier que tout est arrivé

```bash
# 1. tout compile
venv/bin/python -c "import py_compile,glob; [py_compile.compile(f,doraise=True) for f in glob.glob('*.py')]"

# 2. le planificateur tourne
curl -s http://127.0.0.1:5001/planificateur/etat

# 3. les pistes d'audit sont intactes — le chiffre doit être celui du Mac
venv/bin/python -c "import journal; print(journal.verifier('dsf'))"

# 4. les documents ont suivi
venv/bin/python -c "import bibliotheque as B; print(B.resume(B.inventaire('dsf')))"

# 5. un PDF se fabrique — c'est le test de Chromium
venv/bin/python -c "import pdf; print(len(pdf.depuis_html('<h1>essai</h1>')), 'octets')"
```

Si ces cinq commandes passent, le déménagement est réussi.

---

## Modifier le code une fois en ligne

**Le serveur détient la vérité des données.** Sessions, inscriptions, factures,
journal scellé n'existent plus que là-bas. La copie du Mac est figée au
20/08/2026 et ne doit **jamais** repartir vers le serveur.

```bash
./deployer.sh              # ou double-cliquer « 3 — Envoyer les modifications... »
```

**Ce qui part, et rien d'autre** : `*.py`, `templates/`, `static/`,
`requirements.txt`. C'est une **liste blanche**, pas une liste d'exclusions —
une liste d'exclusions finirait par oublier un fichier de données nouveau, et
cet oubli écraserait du travail vivant sans un message. `config.py` en est
exclu : il porte les clés Supabase et voyage à la main.

**Les cinq étapes, dans l'ordre :**

1. **Tout compile-t-il sur le Mac ?** Sinon rien ne part.
2. **Ce qui va changer** est affiché, et l'envoi demande confirmation.
3. **Un point de retour** est pris sur le serveur (`~/deploiements/`, dix gardés).
4. **Tout compile-t-il sur le serveur ?** Sinon retour arrière immédiat, sans
   même interrompre DFM.
5. **DFM répond-il par son adresse publique ?** Sinon retour arrière automatique.

### Pourquoi deux contrôles de compilation et pas un contrôle « DFM répond »

Éprouvé le 20/08/2026, et c'est la raison d'être du mécanisme. Un `pdf.py`
cassé a été envoyé : le service est resté **« actif »**, l'adresse a répondu
**200** — et la fabrication des PDF était morte. La plupart des modules de DFM
ne sont chargés qu'au moment de servir : **demander à DFM s'il répond ne dit
rien de ce qu'il sait encore faire.** Seule la compilation le dit.

Les deux chemins de panne ont été éprouvés pour de vrai :

| Panne | Ce qui l'attrape | Résultat mesuré |
|---|---|---|
| Erreur de syntaxe | contrôle sur le Mac | rien n'est parti |
| Import impossible (compile mais plante au démarrage) | contrôle par l'adresse publique | 502, retour arrière, DFM répond de nouveau |

---

## Le Mac, après

Gardez-le tel quel quelques semaines, sans y travailler. Le jour où vous êtes sûr
du serveur, il devient votre archive de secours — et vous pourrez arrêter ses
deux agents :

```bash
launchctl unload ~/Library/LaunchAgents/com.dfm.pipeline-quotidien.plist
launchctl unload ~/Library/LaunchAgents/com.dfm.reveil-supabase.plist
```

**Ne faites pas tourner les deux en même temps plus que nécessaire.** Les étapes
sont idempotentes — rien ne partirait deux fois — mais deux DFM qui écrivent dans
deux journaux séparés créeraient deux vérités, et il faudrait choisir.
