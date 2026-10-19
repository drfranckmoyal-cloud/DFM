#!/bin/bash
# Lance les tests de DFM, puis le controle des inscriptions sur le serveur.
#
# POURQUOI CE LANCEUR EXISTE. Le 18/10/2026, une inscrite est restee un jour
# sans fiche parce qu'une modification avait casse l'import. Rien ne le disait
# a l'ecran ; l'etape s'affichait meme en vert. Ces deux controles repondent a
# la seule question qui compte : « tout le monde a-t-il sa fiche ? »
cd "$(dirname "$0")"
clear
echo
echo "  ┌──────────────────────────────────────────────────────────────┐"
echo "  │  DFM VA-T-IL BIEN ?                                          │"
echo "  └──────────────────────────────────────────────────────────────┘"
echo
echo "  1. LES TESTS DU CODE, sur ce Mac."
echo "     Ils font tourner l'import pour de vrai, sur une base d'essai."
echo "     Rien n'est ecrit dans vos donnees, aucun mail ne part."
echo
venv/bin/python tests.py
echo
echo "  2. LES INSCRIPTIONS, sur le serveur."
echo "     Il compare ce que le formulaire a recu et ce que DFM contient."
echo
ssh -o ConnectTimeout=20 dfm@163.172.8.49 'cd /home/dfm/DFM && venv/bin/python verifier_inscriptions.py --sans-mail'
echo
echo "  ──────────────────────────────────────────────────────────────"
echo "  Si tout est au vert, chaque personne inscrite a bien sa fiche."
echo "  Sinon, les noms manquants sont ecrits ci-dessus."
echo
echo "  Vous pouvez fermer cette fenetre."
echo
