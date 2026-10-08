from connexion import service_sheets
from sessions import session
from datetime import datetime
# DFM DOIT DEMARRER MEME SANS SESSION ACTIVE. Cette ligne reclamait la session
# active des le chargement du module : avec SESSION_ACTIVE vide elle levait
# « Session inconnue », et toute l'application tombait — 502 constate le
# 01/10/2026 en retirant les deux sessions d'essai. C'est le meme mur que
# remise_a_zero.py aurait rencontre le jour de la vraie remise a zero.
# Les deux constantes qui suivent ne sont lues nulle part ailleurs (verifie le
# 01/10/2026) : un repli vide ne cache rien.
try:
    S = session()
except Exception:
    S = {}
SHEET_SUIVI = S.get("sheet_suivi") or ""
ONGLET = S.get("onglet_suivi") or ""
COL = {
    "horodateur": 0, "nom": 1, "prenom": 2, "mail": 3, "telephone": 4,
    "ville": 5, "date_formation": 6, "demande": 7, "connu_par": 8,
    "dejeuner": 9, "restrictions": 10, "image": 11, "pmr": 12,
    "statut": 13, "mail1_envoye_le": 14, "signe_le": 15,
    "convention_pdf_le": 16, "lien_pdf": 17, "mail2_envoye_le": 18,
    "rappel_le": 19, "montant_du": 20, "paiement_recu_le": 21,
    "montant_recu": 22, "mode_paiement": 23, "reference_paiement": 24,
    "facture_le": 25, "lien_facture": 26, "attestation_le": 27,
    "facture_envoyee_le": 28, "relance_signature_le": 29, "relance_reglement_le": 30,
    "annulation_demandee_le": 31, "annule_le": 32, "motif_annulation": 33,
    "lien_attestation": 34, "present": 35, "file_attente_le": 36, "mail_attente_le": 37,
    "promu_le": 38, "attestation_envoyee_le": 39,
    "eval_init_le": 40, "score_init": 41, "eval_fin_le": 42, "score_fin": 43,
    "satisfaction_le": 44, "note_satisfaction": 45, "froid_le": 46, "note_froid": 47,
    # Apprenant invite : date a laquelle l'invitation a ete posee. Vider la
    # cellule remet l'apprenant dans le circuit financier normal.
    "invite_le": 48,
    # 50e colonne, ajoutee le 03/08/2026. AJOUTEE A LA FIN, jamais inseree :
    # les 49 premieres gardent leur position, donc rien ne se decale.
    # Chirurgien-dentiste ou assistante dentaire. Necessaire a la convention
    # d'une session client, qui liste les participants AVEC leur fonction ;
    # utile ensuite partout — fiche apprenant, ciblage des envois.
    "fonction": 49,
}
def lettre_colonne(index):
    lettre = ""
    n = index + 1
    while n > 0:
        n, reste = divmod(n - 1, 26)
        lettre = chr(65 + reste) + lettre
    return lettre
def aujourdhui():
    return datetime.now().strftime("%d/%m/%Y %H:%M")
def _organisme(code=None):
    """L'organisme proprietaire d'une session. Sans code : celui de l'active.

    LE CLOISONNEMENT PASSE PAR LA. Deux entites, deux jeux d'inscrits ; se
    tromper d'organisme ici, c'est lire ou ecrire dans le suivi de l'autre.
    """
    import sessions as _sessions
    return _sessions.organisme_de(code or _sessions.SESSION_ACTIVE) or ""


def lire_lignes_de(code=None):
    """Les inscrits d'une session. Sans argument : la session active.

    LA LECTURE VIENT DE LA BASE LOCALE depuis le 17/08/2026. Elle telechargeait
    mille lignes de tableur a chaque affichage d'ecran, a chaque envoi, a chaque
    verification — et DFM s'arretait des que Google ne repondait pas.

    LA FORME RENDUE N'A PAS BOUGE : un dictionnaire par inscrit, tous les champs
    de COL presents, plus « _numero » et « _mode ». C'etait la condition pour
    que la bascule ne se voie nulle part ailleurs.
    """
    import sessions as _sessions
    import base
    code = code or _sessions.SESSION_ACTIVE
    # Le mode voyage AVEC la ligne : les appelants n'ont pas a le rechercher,
    # et une ligne ne peut pas se retrouver jugee selon le mode d'une autre
    # session.
    _mode = _sessions.mode(code)
    lignes = []
    for numero, d in base.suivi_lire(_organisme(code), code):
        if not (d.get("horodateur") or "").strip():
            continue
        ligne = {cle: (d.get(cle) or "") for cle in COL}
        ligne["_numero"] = numero
        ligne["_mode"] = _mode
        lignes.append(ligne)
    return lignes
def lire_lignes():
    """Comportement historique, inchange : la session active."""
    return lire_lignes_de()
def _mode_de(ligne, code=None):
    """Le mode de la session d'une ligne. La ligne le porte si elle vient de
    lire_lignes_de ; sinon on le demande a la session."""
    m = (ligne or {}).get("_mode")
    if m:
        return m
    try:
        import sessions as _sessions
        return _sessions.mode(code)
    except Exception:
        return "individuel"


def calculer_statut(ligne, mode="individuel"):
    """Le statut d'un inscrit.

    EN MODE CLIENT, deux statuts suffisent. La convention, la signature et le
    reglement y sont COLLECTIFS : les afficher ligne par ligne repeterait N
    fois un fait unique, et chaque participant paraitrait « a contacter »
    pour l'eternite puisque aucune de ces cases ne sera jamais remplie.
    L'etat collectif s'affiche une seule fois, sur la fiche de session.

    LE DEFAUT EST « individuel », VOLONTAIREMENT. Les appelants qui ne passent
    rien obtiennent donc exactement le resultat d'avant, par construction —
    c'est ce qui garantit qu'aucune session existante ne bouge. Une detection
    interne, a partir de la ligne, aurait ete implicite et fragile : toutes
    les lignes ne portent pas leur session."""
    if mode == "client":
        if ligne["annule_le"]:
            return "Annulee"
        return "Inscrit"
    if ligne["annule_le"]:
        return "Annulee"
    if ligne["annulation_demandee_le"]:
        return "Annulation demandee"
    if ligne["file_attente_le"] and not ligne["promu_le"]:
        return "File d'attente"
    if "recontact" in ligne["demande"].lower():
        return "A recontacter"
    if not ligne["mail1_envoye_le"]:
        return "A contacter"
    if not ligne["signe_le"]:
        return "En attente signature"
    if not ligne["convention_pdf_le"]:
        return "Convention a generer"
    if not ligne["mail2_envoye_le"]:
        return "Mail 2 a envoyer"
    # Un invite ne passe jamais par « En attente reglement » : aucune somme ne
    # lui est demandee. Statut distinct de « Reglee » pour rester visible.
    if ligne.get("invite_le"):
        return "Invitee"
    if not ligne["paiement_recu_le"]:
        return "En attente reglement"
    return "Reglee"
def ecrire(numero_ligne, champ, valeur, code=None):
    """Ecrit une cellule du suivi. Sans code : la session active, comportement
    historique. Avec code : l'onglet de CETTE session — indispensable des que
    plusieurs sessions coexistent, sinon un numero de ligne venu d'un onglet
    serait applique a un autre (melange croise, point A1)."""
    return ecrire_plusieurs(numero_ligne, {champ: valeur}, code)


def ecrire_plusieurs(numero_ligne, valeurs, code=None):
    """Ecrit plusieurs champs d'UNE ligne, en un seul aller-retour.

    POURQUOI CETTE FONCTION EXISTE. Une vingtaine d'endroits d'app.py
    composaient eux-memes leurs plages — « 'onglet'!" + _lettre(COL[champ]) +
    str(numero) » — et appelaient l'API a la place de ce module. Chacun devait
    donc savoir qu'un suivi est une feuille de calcul, ou vit son onglet, et
    comment se nomme une colonne. C'est exactement ce qu'il faut ignorer pour
    que le magasin puisse changer.

    LE CHAMP EST VERIFIE AVANT D'ECRIRE. Une faute de frappe visait auparavant
    une colonne voisine, sans rien dire : « facture_le » ecrit « facture_les »
    partait dans la colonne d'a cote. Ici elle leve.
    """
    return ecrire_lignes([(numero_ligne, valeurs)], code)


def ecrire_lignes(maj, code=None):
    """Ecrit PLUSIEURS lignes en un seul aller-retour.

    `maj` est une liste de (numero_ligne, {champ: valeur}). Les envois groupes
    — passage en file d'attente, pointage des presences, relevee des
    questionnaires — touchent des dizaines de lignes : les ecrire une par une
    ferait autant d'appels reseau.
    """
    maj = [(n, v) for n, v in (maj or []) if v]
    if not maj:
        return
    inconnus = sorted({c for _, v in maj for c in v if c not in COL})
    if inconnus:
        raise KeyError("Champ(s) de suivi inconnu(s) : %s" % ", ".join(inconnus))

    # L'ECRITURE LOCALE D'ABORD, ET ELLE SEULE PEUT ECHOUER. Un reglement
    # enregistre pendant une panne de Google etait purement perdu ; il est
    # desormais acquis, et c'est le classeur qui attend.
    import sessions as _sessions
    import base
    code = code or _sessions.SESSION_ACTIVE
    org = _organisme(code)
    for numero, valeurs in maj:
        base.suivi_poser(org, code, numero, valeurs)

    _miroir(code, maj)


def _miroir(code, maj):
    """Recopie des cellules dans le classeur. Ne leve jamais.

    LE MIROIR N'EST PAS UNE ECRITURE, c'est une copie. Son echec laisse une
    trace a l'ecran et rien de plus : la donnee est deja enregistree. Lever
    ici ferait croire a l'appelant que son enregistrement a rate.
    """
    try:
        fiche = session(code)
        onglet = fiche["onglet_suivi"]
        donnees = [{"range": "'%s'!%s%s" % (onglet, lettre_colonne(COL[c]), numero),
                    "values": [[v]]}
                   for numero, valeurs in maj for c, v in valeurs.items()]
        if not donnees:
            return
        service_sheets().spreadsheets().values().batchUpdate(
            spreadsheetId=fiche["sheet_suivi"],
            body={"valueInputOption": "USER_ENTERED", "data": donnees}).execute()
    except Exception as e:
        print("   (miroir du suivi en retard, donnee bien enregistree : %s)"
              % str(e)[:80])


def ajouter(valeurs, code=None):
    """Ajoute une ligne au suivi et rend son numero."""
    n = ajouter_plusieurs([valeurs], code)
    return n[0] if n else 0


def ajouter_plusieurs(lignes, code=None):
    """Ajoute plusieurs lignes et rend leurs numeros.

    Chaque entree est un dictionnaire {champ: valeur} ; les champs absents
    restent vides. L'appelant n'a plus a construire une liste de cinquante
    cases dans le bon ordre — c'etait une source de decalage silencieux a
    chaque colonne ajoutee.

    LA PLAGE VA JUSQU'A LA DERNIERE COLONNE DE COL, calculee. Un appelant
    ecrivait « A:AW » en dur, ce qui s'arretait a la 49e colonne alors que la
    ligne en compte cinquante depuis l'ajout de « fonction » le 03/08/2026.
    Une plage ecrite a la main vieillit mal ; celle-ci suit COL.
    """
    lignes = [l for l in (lignes or []) if l]
    if not lignes:
        return []
    inconnus = sorted({c for l in lignes for c in l if c not in COL})
    if inconnus:
        raise KeyError("Champ(s) de suivi inconnu(s) : %s" % ", ".join(inconnus))

    # C'EST LA BASE QUI ATTRIBUE LES NUMEROS, plus le classeur. Laisser Google
    # choisir la ligne les ferait diverger au premier decalage, et « _numero »
    # circule dans tout DFM — un numero venu d'un magasin et applique a l'autre
    # ecrirait sur la mauvaise personne. Meme regle que pour le journal.
    import sessions as _sessions
    import base
    code = code or _sessions.SESSION_ACTIVE
    org = _organisme(code)
    numeros = [base.suivi_ajouter(org, code, v) for v in lignes]

    # Le miroir ecrit AUX RANGS DECIDES, ligne complete.
    try:
        fiche = session(code)
        derniere = lettre_colonne(len(COL) - 1)
        donnees = []
        for numero, valeurs in zip(numeros, lignes):
            r = [""] * len(COL)
            for c, v in valeurs.items():
                r[COL[c]] = "" if v is None else v
            donnees.append({"range": "'%s'!A%d:%s%d"
                                     % (fiche["onglet_suivi"], numero, derniere, numero),
                            "values": [r]})
        service_sheets().spreadsheets().values().batchUpdate(
            spreadsheetId=fiche["sheet_suivi"],
            body={"valueInputOption": "USER_ENTERED", "data": donnees}).execute()
    except Exception as e:
        print("   (miroir du suivi en retard, inscrits bien enregistres : %s)"
              % str(e)[:80])
    return numeros
def marquer(ligne, champ, valeur=None, code=None, detail=""):
    """detail : texte joint a l'entree de journal — destinataire d'un mail,
    lien d'un document. Sans lui, le journal dit qu'un document est parti sans
    dire a qui ni lequel, ce qui ne prouve rien en audit."""
    valeur = valeur if valeur is not None else aujourdhui()
    ecrire(ligne["_numero"], champ, valeur, code)
    ligne[champ] = valeur
    ecrire(ligne["_numero"], "statut", calculer_statut(ligne, _mode_de(ligne, code)), code)
    try:
        import journal
        journal.depuis_champ(champ, ligne, detail=detail, code_session=code or "")
    except Exception:
        pass
def rafraichir_statuts(code=None):
    lignes = lire_lignes_de(code)
    for ligne in lignes:
        nouveau = calculer_statut(ligne, _mode_de(ligne, code))
        if ligne["statut"] != nouveau:
            ecrire(ligne["_numero"], "statut", nouveau, code)
    return len(lignes)
