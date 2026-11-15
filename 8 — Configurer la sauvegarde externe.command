#!/bin/bash
# 8 — Configurer la sauvegarde externe de DFM (15/11/2026)
#
# Recoit les cles de l'espace de stockage Scaleway, fabrique la phrase de
# chiffrement, la range dans le trousseau du Mac, depose le tout sur le serveur
# (lisible du seul compte dfm), puis fait un essai complet : envoi d'une copie
# chiffree, rapatriement, dechiffrement, verification.
#
# LES CLES NE PASSENT PAR PERSONNE : ni par Claude, ni par l'ecran (la cle
# secrete se colle sans s'afficher), ni par un fichier du Mac.

SERVEUR="dfm@163.172.8.49"
cd "$(dirname "$0")" || exit 1

clear
echo "=============================================================="
echo "  Sauvegarde externe de DFM — mise en place"
echo "=============================================================="
echo
echo "  Il vous faut les trois informations notées dans la console"
echo "  Scaleway : le nom de l'espace de stockage (bucket), la clé"
echo "  d'accès (elle commence par SCW) et la clé secrète."
echo
read -r -p "  Nom du bucket : " BUCKET
read -r -p "  Clé d'accès   : " CLE
echo "  Clé secrète   : (collez-la puis Entrée — rien ne s'affiche, c'est normal)"
read -r -s SECRET
echo
if [ -z "$BUCKET" ] || [ -z "$CLE" ] || [ -z "$SECRET" ]; then
  echo "  Il manque une des trois valeurs : rien n'a été modifié."
  read -r -p "  Entrée pour fermer." _
  exit 1
fi

# LA PHRASE DE CHIFFREMENT. Sans elle, une copie est illisible — y compris pour
# nous. Elle part au serveur ET dans le trousseau du Mac.
PHRASE="$(openssl rand -base64 33 | tr -d '\n')"
if security add-generic-password -U -s "DFM sauvegarde externe" -a "phrase de chiffrement" -w "$PHRASE" 2>/dev/null; then
  echo "  Phrase de chiffrement rangée dans le trousseau du Mac"
  echo "  (Trousseaux d'accès › « DFM sauvegarde externe »)."
else
  echo "  ATTENTION : le trousseau a refusé la phrase. Notez-la ci-dessous."
fi

echo
echo "  Envoi de la configuration au serveur…"
export BUCKET CLE SECRET PHRASE
python3 - <<'PY' | ssh -o ConnectTimeout=20 "$SERVEUR" 'umask 077; cat > /home/dfm/DFM/stockage_externe.json && chmod 600 /home/dfm/DFM/stockage_externe.json'
import json, os
print(json.dumps({"bucket": os.environ["BUCKET"].strip(),
                  "cle_acces": os.environ["CLE"].strip(),
                  "cle_secrete": os.environ["SECRET"].strip(),
                  "phrase": os.environ["PHRASE"],
                  "region": "fr-par", "garder_jours": 30}, ensure_ascii=False))
PY
if [ $? -ne 0 ]; then
  echo "  Le serveur n'a pas pu être joint : rien n'a été déposé."
  read -r -p "  Entrée pour fermer." _
  exit 1
fi
unset SECRET

echo "  Essai complet (envoi, rapatriement, déchiffrement)…"
echo
ssh -o ConnectTimeout=20 "$SERVEUR" 'cd /home/dfm/DFM && env -u DFM_PROXY -u DFM_AUTO venv/bin/python sauvegarde_externe.py --essai'
RESULTAT=$?
echo
if [ $RESULTAT -eq 0 ]; then
  echo "  C'EST EN PLACE. Chaque soir, la sauvegarde partira chiffrée"
  echo "  vers ce stockage ; trente jours de copies y seront gardés,"
  echo "  et une restauration d'essai sera faite chaque dimanche."
else
  echo "  L'ESSAI A ÉCHOUÉ. Montrez ce message à Claude : la configuration"
  echo "  est déposée, il suffira de corriger ce qui est indiqué."
fi
echo
echo "  À garder aussi dans votre gestionnaire de mots de passe,"
echo "  sous le nom « DFM sauvegarde externe » :"
echo
echo "      $PHRASE"
echo
unset PHRASE
read -r -p "  Entrée pour fermer cette fenêtre." _
