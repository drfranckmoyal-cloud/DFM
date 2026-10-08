"""Fabrique les attestations de fin de formation d'une session.

LE MODELE EST UNIQUE, et il est dans DFM : templates/attestation.html.
Avant le 06/08/2026, chaque formation avait SA presentation Slides dans le
Drive — uniquement parce que le titre de la formation y etait ecrit en dur.
Ces modeles portaient quatre informations ; l'article L.6353-1 en exige huit.
La duree, la nature de l'action et les resultats de l'evaluation manquaient.

L'en-tete s'ajuste a l'organisme actif : meme document pour DSF et Smileclub,
avec leur logo, leur SIRET et leur numero de declaration respectifs.

CE QUI N'A PAS CHANGE : le PDF est toujours depose dans le dossier Drive
« Attestations » de l'organisme, et un PDF existant est mis a jour EN PLACE —
son identifiant Drive ne bouge pas, donc le lien deja transmis reste valide.
"""
from connexion import service_drive
from googleapiclient.http import MediaInMemoryUpload
from datetime import date, datetime
import sys
import attestation
import jours as _jours
import journal
import pdf as _pdf
import suivi
from sessions import session

CODE = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
S = session(CODE)
# Forcage reserve aux TESTS, en ligne de commande uniquement :
#   python3 generer_attestations.py --forcer
# Aucune route ni aucun ecran ne lance ce script — dfm.py l'appelle sans
# argument — il ne peut donc pas etre declenche depuis l'interface.
FORCER = "--forcer" in sys.argv[1:]

# La date de fin vient de la LISTE DES JOURNEES, pas du champ date_fin : une
# formation aux journees dispersees se termine le dernier jour travaille, et
# c'est lui qui decide si l'attestation peut partir.
_j = _jours.resume(S)
fin = datetime.strptime(_j["date_fin"], "%Y-%m-%d").date() if _j["date_fin"] else date.today()
reste = (fin - date.today()).days
print(f"-> Session : {S['nom_formation']} ({S['code']})")
if reste > 0 and not FORCER:
    print(f"-> La formation se termine dans {reste} jour(s). Trop tot.")
    print("   (test uniquement : python3 generer_attestations.py --forcer)")
    exit()
if reste > 0:
    print(f"-> FORCAGE : la formation se termine dans {reste} jour(s).")
    print("   Attestations generees a des fins de test.")

# Sans navigateur, aucun PDF n'est fabricable : on le dit ICI, une fois, plutot
# que d'echouer inscrit par inscrit avec une trace incomprehensible.
try:
    _pdf.navigateur()
except _pdf.Indisponible as e:
    print("-> " + str(e))
    exit()

lignes = suivi.lire_lignes_de(CODE)
# Tous les inscrits actifs, sans condition de presence : le tri des absents
# se fait au moment de l'ENVOI, dans la fenetre de validation de l'interface.
a_generer = [l for l in lignes
             if not l["attestation_le"]
             and not l["annule_le"]
             and "recontact" not in l["demande"].lower()
             and suivi.calculer_statut(l) != "File d'attente"]
if not a_generer:
    print("-> Aucune attestation a generer.")
    exit()
print(f"-> {len(a_generer)} attestation(s) a generer.")

# Par IDENTIFIANT : une attestation est une preuve Qualiopi, elle appartient a
# l'organisme qui a dispense la formation et a lui seul.
# LE DOSSIER DRIVE A ETE RETIRE LE 18/08/2026. Ces lignes ouvraient une
# connexion Google, cherchaient un dossier « Attestations », creaient un
# sous-dossier de session — et le resultat n'etait JAMAIS RELU : le rangement
# passe par documents.ranger() depuis le branchement de la couche « documents ».
# Il ne restait qu'un preambule capable d'arreter tout le script, pour un
# dossier dont plus personne n'avait besoin.

# Le logo se telecharge UNE FOIS pour toute la session : il est identique sur
# chaque attestation, et un appel Drive par inscrit serait du gaspillage.
logo = ""
try:
    logo = _pdf.image_en_ligne(
        __import__("profil").logo(__import__("sessions").organisme_de(S["code"])), "image/png")
except Exception as e:
    print(f"   ATTENTION : logo indisponible ({e}). Attestations sans logo.")

compte = 0
for ligne in a_generer:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    print(f"-> {nom_prenom}...")
    try:
        donnees = attestation.pour(CODE, ligne, logo)
        octets = _pdf.depuis_html(attestation.html(donnees))
    except Exception as e:
        # Un echec sur une personne ne doit pas priver les autres de leur
        # attestation : on signale et on continue.
        print(f"   ECHEC : {e}")
        continue
    # SANS RESULTAT, L'ATTESTATION NE SE FIGE PAS. L'evaluation de sortie est
    # relevee A LA MAIN depuis l'interface, et rien ne garantit qu'elle l'ait
    # ete avant cette synchronisation. Tant que le score manque, on N'INSCRIT
    # PAS `attestation_le` : la generation suivante refera le document, en
    # place, avec le meme identifiant Drive et le meme numero. Elle se complete
    # donc toute seule des que la relevee a lieu.
    #
    # Le document est quand meme depose : une attestation est DUE a chaque
    # participant, y compris a celui qui n'a jamais repondu au questionnaire.
    # Elle porte alors l'encadre qui dit ce qui manque.
    complet = donnees["score_fin"] is not None
    # Passe ce delai, on fige : au-dela, l'absence de reponse n'est plus un
    # retard de saisie, c'est un fait. Sans cette borne, une session close
    # referait ses attestations a chaque synchronisation, indefiniment.
    depuis = (date.today() - fin).days
    if not complet and depuis > 30:
        complet = True
        print("   Aucun resultat d'evaluation, et la formation est finie depuis "
              f"{depuis} jours : attestation figee en l'etat.")
    elif not complet:
        print("   SANS RESULTAT d'evaluation : le document le mentionne. "
              "Il sera refait automatiquement des la relevee des questionnaires.")
    nom_pdf = f"Attestation - {nom_prenom}.pdf"
    # LE RANGEMENT PASSE PAR LA COUCHE « documents » : plus de dossier Drive
    # nomme ici. L'avertissement sur les exemplaires en double y a suivi.
    import documents
    ref, lien, _souci = documents.ranger(CODE, "attestation", nom_pdf, octets)
    if not ref:
        print("   ECHEC : " + _souci)
        continue
    if not lien:
        print("   Attestation rangee en local ; copie Drive non partie.")
    suivi.ecrire(ligne["_numero"], "lien_attestation", lien, CODE)
    if complet:
        # L'ATTESTATION DEJA PARTIE INCOMPLETE EST RENVOYEE. Sans cela, le
        # document se corrigeait partout — en local, dans le Drive, dans le
        # dossier de preuve — SAUF dans la boite de l'apprenant, qui gardait a
        # jamais l'exemplaire portant « evaluation de sortie non enregistree ».
        #
        # La condition est stricte : on ne rouvre que si l'envoi precedent a eu
        # lieu SANS resultat (`attestation_le` vide avant ce passage). Une
        # attestation deja envoyee complete ne repart jamais — sinon chaque
        # regeneration relancerait un mail.
        if ligne["attestation_envoyee_le"] and not ligne["attestation_le"]:
            suivi.ecrire(ligne["_numero"], "attestation_envoyee_le", "", CODE)
            print("   Resultat desormais connu : cette attestation avait ete "
                  "envoyee incomplete,")
            print("   elle sera RENVOYEE corrigee au prochain envoi.")
        suivi.ecrire(ligne["_numero"], "attestation_le", suivi.aujourdhui(), CODE)
    try:
        qui = (ligne["prenom"] or "").strip() + " " + (ligne["nom"] or "").strip().upper()
        journal.ecrire("Attestation générée", qui.strip(),
                       donnees["numero"] + " · " + lien, "", S["code"])
    except Exception:
        pass
    print(f"   {donnees['numero']} genere.")
    compte += 1
print(f"-> Termine : {compte} attestation(s) generee(s).")
