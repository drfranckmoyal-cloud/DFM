#!/bin/bash
cd "$(dirname "$0")"
clear
cat <<'TXT'

  ─────────────────────────────────────────────────────────────────
   RAPATRIER LES DONNEES DU SERVEUR VERS CE MAC
  ─────────────────────────────────────────────────────────────────

  Copie sur ce Mac tout ce que le serveur contient : sessions,
  inscriptions, factures, documents, journal scelle et les
  sauvegardes du soir.

  Le sens est unique : du serveur vers le Mac, JAMAIS l'inverse.
  Rien de ce que vous avez en ligne ne risque quoi que ce soit.

  DFM ne doit pas tourner sur ce Mac. Si c'est le cas, le script
  s'arretera et vous le dira — il ne forcera rien.

  ─────────────────────────────────────────────────────────────────

TXT
./rapatrier.sh
echo
read -p "  Appuyez sur Entree pour fermer : " _
