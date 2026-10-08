#!/bin/bash
# Pose le certificat HTTPS de DFM sur le serveur Scaleway.
# Franck accepte lui-meme les conditions de Let's Encrypt : c'est un
# engagement, il ne peut pas etre signe a sa place.
cd "$(dirname "$0")"
clear
cat <<'TXT'

  ─────────────────────────────────────────────────────────────────
   POSER LE HTTPS DE DFM
  ─────────────────────────────────────────────────────────────────

  Cette fenetre va demander a Let's Encrypt un certificat pour
  l'adresse :

      163-172-8-49.nip.io

  C'est ce certificat qui met le cadenas dans le navigateur et qui
  chiffre votre mot de passe et vos donnees. Il est gratuit et se
  renouvellera tout seul.

  ON VOUS POSERA TROIS QUESTIONS, dans cet ordre :

   1. « Enter email address »
      Tapez votre adresse mail, puis Entree.
      Elle sert uniquement a vous prevenir si le certificat expire.

   2. « (A)gree/(C)ancel »
      Ce sont les conditions d'utilisation de Let's Encrypt.
      Tapez  A  puis Entree pour accepter.

   3. « (Y)es/(N)o » — partager votre mail avec l'EFF ?
      C'est une lettre d'information, sans rapport avec le
      certificat. Tapez  N  puis Entree. Ca ne change rien.

  Vous pouvez fermer cette fenetre maintenant si vous preferez
  attendre : rien n'aura ete engage.

  ─────────────────────────────────────────────────────────────────

TXT
read -p "  Appuyez sur Entree pour commencer : " _
echo
ssh -t root@163.172.8.49 "certbot certonly --webroot -w /var/www/acme -d 163-172-8-49.nip.io"
echo
echo "  ─────────────────────────────────────────────────────────────────"
echo "  Termine. Revenez me le dire dans la discussion :"
echo "  je branche DFM derriere le certificat et je vous donne l'adresse."
echo "  ─────────────────────────────────────────────────────────────────"
echo
read -p "  Appuyez sur Entree pour fermer : " _
