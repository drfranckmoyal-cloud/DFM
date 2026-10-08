#!/bin/bash
# Publie le site public de DFM sur Netlify.
#
# ON PUBLIE DEPUIS UNE COPIE FILTREE, jamais depuis le dossier de travail.
# Celui-ci contient des sauvegardes datees — « index.html.avant-marque » — qui
# etaient servies publiquement jusqu'au 18/08/2026. Une regle de redirection ne
# peut pas les bloquer : Netlify n'accepte l'etoile qu'en fin de motif.
#
# LES ORIGINAUX NE BOUGENT PAS. On copie ce qui doit partir, on laisse le reste.
set -e
SITE="4fab9020-646f-41cf-bc97-affb3c94e531"
SOURCE="$(cd "$(dirname "$0")" && pwd)"
COPIE="$(mktemp -d)"
trap 'rm -rf "$COPIE"' EXIT

rsync -a \
  --exclude='*.avant-*' --exclude='*.safe.*' \
  --exclude='node_modules' --exclude='.netlify' --exclude='.git*' \
  --exclude='publier_site.sh' \
  "$SOURCE/" "$COPIE/"

# LES DEPENDANCES SONT PRETEES, PAS COPIEES. L'assembleur de Netlify a besoin
# de « @supabase/supabase-js » pour empaqueter les fonctions ; sans lui la
# publication echoue sur « Cannot find module ». Un lien evite de recopier des
# dizaines de megaoctets a chaque publication.
ln -s "$SOURCE/node_modules" "$COPIE/node_modules"

echo "-> Ce qui part :"
find "$COPIE" -type f | sed "s|$COPIE/|   |" | sort
echo
cd "$COPIE"
netlify deploy --prod --dir=. --site="$SITE"
