#!/bin/bash
cd "$(dirname "$0")"
clear
./deployer.sh
echo
read -p "  Appuyez sur Entree pour fermer : " _
