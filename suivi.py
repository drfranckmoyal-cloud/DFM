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
    # LE JALON DE VALIDATION — 24/10/2026, pour Esthetique 360. Deux colonnes,
    # AJOUTEES A LA FIN comme la 50e : les precedentes gardent leur position.
    #
    # « a_valider_le » est posee A L'IMPORT, et seulement si la formation exige
    # une validation une par une. C'est elle, et non un reglage lu ailleurs, qui
    # fait qu'une ligne est une DEMANDE et non une inscription : une ligne
    # ecrite avant le 24/10/2026 ne la porte pas, donc rien de ce qui existe ne
    # change de statut. Le reglage ne vaut que pour les lignes a venir.
    #
    # « valide_le » est posee quand le responsable valide la demande. C'est a ce
    # moment, et seulement a ce moment, que le prix de la personne est arrete.
    "a_valider_le": 50, "valide_le": 51,
    # LES VERSEMENTS — 25/10/2026. Voir « versements() » plus bas : une ligne
    # par virement, dans une seule cellule. Au bout de la rangee, comme les
    # deux precedentes : une colonne inseree ailleurs decalerait tout le
    # classeur.
    "versements": 52,
}

# CE QUI N'OCCUPE PAS ENCORE UNE PLACE. Une file d'attente et une demande non
# validee ont le meme effet sur l'effectif : la personne ne compte pas, n'entre
# pas dans la capacite, ne recoit ni convention ni attestation. Un seul nom pour
# les deux, plutot qu'une comparaison a « File d'attente » recopiee a quatorze
# endroits — c'est ainsi qu'un quinzieme finit par etre oublie.
PAS_ENCORE_INSCRIT = ("File d'attente", "Demande à valider")
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
    # LA DEMANDE PAS ENCORE VALIDEE. Elle se lit sur la ligne elle-meme et non
    # sur un reglage de formation : une ligne qui ne porte pas « a_valider_le »
    # ne peut pas basculer dans ce statut, et aucune session en service ne la
    # porte. Le jalon s'ajoute donc sans toucher a ce qui tourne.
    if ligne.get("a_valider_le") and not ligne.get("valide_le"):
        return "Demande à valider"
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
        # UN ACOMPTE N'EST PAS UNE ATTENTE — 25/10/2026. « paiement_recu_le »
        # garde son sens : la date ou le compte est SOLDE. Tant qu'il reste
        # quelque chose a payer, la case est vide — et une ligne qui porte
        # deja des versements ne doit plus etre annoncee comme n'ayant rien
        # regle. Une ligne qui n'en porte aucun retombe mot pour mot sur le
        # comportement d'avant : c'est ce qui laisse les formations courtes
        # intactes.
        if (ligne.get("versements") or "").strip():
            return "Reglement partiel"
        return "En attente reglement"
    return "Reglee"
def euros(brut):
    """Un montant saisi, lu comme un nombre. Zero si l'on n'y comprend rien.

    « 1 234,50 € », « 6 000 », « 975 » : la saisie varie, le nombre non. La
    regle vivait dans « montant_attendu » ; elle en sort le 25/10/2026 parce
    que les versements en ont besoin eux aussi, et qu'une regle recopiee est
    une regle qu'on corrige a un endroit sur deux.
    """
    import re as _re
    # On garde les chiffres, le separateur et le signe ; on jette le reste
    # (l'euro, les espaces fines).
    propre = _re.sub(r"[^0-9.,-]", "", str(brut or "")).replace(",", ".")
    try:
        return float(propre) if propre not in ("", "-", ".", "-.") else 0.0
    except ValueError:
        return 0.0


def montant_attendu(ligne, tarif_session=None):
    """Ce que cette personne doit, en euros. Zero pour un invite.

    UNE SEULE REGLE, UN SEUL ENDROIT — 18/10/2026. Elle etait recopiee dans
    cinq : l'ecran des reglements, le tableau de bord d'une session, l'espace
    du praticien, la balise {{tarif}} des mails et la convocation. Quatre de
    ces cinq copies comptaient 975 euros a un invite — et le mail 2 lui a
    reellement demande de regler. Une regle recopiee est une regle qu'on
    corrige a quatre endroits sur cinq.

    DEUX CHOSES A SAVOIR, ET LES DEUX SE SONT PAYEES :

    - UN INVITE NE DOIT RIEN. C'est la regle de DFM partout ailleurs : son
      statut est « Invitee », sa facture « sans objet », sa convention porte
      zero euro. Les ecrans financiers etaient les derniers a l'ignorer.

    - UN MONTANT VIDE N'EST PAS UN ZERO. « montant_du » n'est ecrit qu'a
      l'enregistrement d'un reglement, et l'ancien formulaire Google ne le
      posait jamais. Un inscrit qui n'a pas encore paye a donc le champ VIDE,
      et il doit le tarif de la session. Seul un zero ECRIT est un zero —
      l'inverse a ete suppose le 17/10, et quatre inscrits d'Usures novembre
      ont failli cesser d'etre relances.

    Le tarif de la session se passe en argument : « suivi » ne sait pas lire
    une session, et n'a pas a l'apprendre pour une division.
    """
    if str(ligne.get("invite_le") or "").strip():
        return 0.0
    brut = str(ligne.get("montant_du") or "").strip()
    if not brut:
        brut = str(tarif_session or "").strip()
    return euros(brut)


# ---------------------------------------------------------------------------
# LES VERSEMENTS D'UN INSCRIT
# ---------------------------------------------------------------------------
# POURQUOI UNE LISTE, ET PAS QUATRE CASES — 25/10/2026, pour Esthetique 360.
#
# DFM ne savait enregistrer QU'UN SEUL reglement par personne : quatre cases,
# une date, un montant, un mode, une reference. Le second etait refuse. Pour
# une formation de deux jours a 975 euros, cela suffisait. Pour un cycle d'un
# an a 6 000 euros, ou chacun verse quand il peut, cela ne suffit plus.
#
# LA FORME : une ligne par versement, dans UNE seule cellule.
#
#     12/01/2027 | 2000 | Virement | VIR-0042 | https://.../recu.pdf
#     15/03/2027 | 2000 | Virement | VIR-0109 |
#
# C'est l'idiome de DFM — les relances empilent deja leurs dates separees par
# « | » dans une case. Et c'est LISIBLE DANS LE CLASSEUR, ce qu'un bloc JSON
# n'aurait pas ete : Franck relit le classeur.
#
# LES QUATRE CASES D'ORIGINE NE DISPARAISSENT PAS. « montant_recu » porte
# desormais le TOTAL verse, et c'est ce que tous les ecrans existants lisaient
# deja. « paiement_recu_le » garde son sens exact : la date ou le compte est
# solde — donc vide tant qu'il reste quelque chose. Aucun ecran n'a eu a
# changer de lecture.
#
# ET LES 58 INSCRITS D'AVANT ? Leur cellule est vide, mais leurs quatre cases
# sont remplies : « versements() » leur reconstitue un versement unique. Pour
# eux, la liste existe sans avoir jamais ete ecrite.
SEPARATEUR_VERSEMENT = "\n"
SEPARATEUR_CHAMP = " | "
CHAMPS_VERSEMENT = ("le", "montant", "mode", "reference", "recu")


def _propre(valeur):
    """Une valeur de versement, debarrassee de ce qui couperait la ligne.

    Une reference de virement ne contient legitimement ni « | » ni retour a la
    ligne. Si elle en porte un, c'est une coquille de saisie — et la laisser
    passer casserait la relecture de TOUS les versements de la personne.
    """
    return str(valeur or "").replace("|", "/").replace("\n", " ").replace("\r", " ").strip()


def versements(ligne):
    """Les versements de cette personne, du plus ancien au plus recent.

    Chaque versement est un dictionnaire : le, montant, mode, reference, recu.
    « montant » reste du texte — c'est ce qui a ete saisi ; « total_verse »
    s'occupe de le compter.
    """
    brut = (ligne.get("versements") or "").strip()
    if not brut:
        # UNE LIGNE D'AVANT LE 25/10/2026 : son reglement unique vit encore
        # dans les quatre cases. On le rend sous la meme forme que les autres,
        # pour que l'appelant n'ait jamais deux cas a traiter.
        if not (ligne.get("paiement_recu_le") or "").strip():
            return []
        return [{"le": (ligne.get("paiement_recu_le") or "").strip(),
                 "montant": str(ligne.get("montant_recu") or "").strip(),
                 "mode": (ligne.get("mode_paiement") or "").strip(),
                 "reference": (ligne.get("reference_paiement") or "").strip(),
                 "recu": ""}]
    liste = []
    for rangee in brut.split(SEPARATEUR_VERSEMENT):
        if not rangee.strip():
            continue
        morceaux = [m.strip() for m in rangee.split("|")]
        morceaux += [""] * (len(CHAMPS_VERSEMENT) - len(morceaux))
        liste.append(dict(zip(CHAMPS_VERSEMENT, morceaux)))
    return liste


def versements_texte(liste):
    """La cellule a ecrire, depuis une liste de versements."""
    return SEPARATEUR_VERSEMENT.join(
        SEPARATEUR_CHAMP.join(_propre((v or {}).get(c, "")) for c in CHAMPS_VERSEMENT)
        for v in (liste or []))


def total_verse(ligne):
    """Ce qui a ete encaisse de cette personne, tous versements confondus."""
    return sum(euros(v.get("montant")) for v in versements(ligne))


def solde(ligne, tarif_session=None):
    """Ce qu'il reste a payer. Jamais negatif : un trop-percu n'est pas une
    dette a rebours, et l'afficher en negatif ferait croire a une erreur de
    saisie la ou il n'y a qu'un arrondi."""
    return max(0.0, montant_attendu(ligne, tarif_session) - total_verse(ligne))


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
        # LA COPIE PART EN FILE, PAS VERS GOOGLE — 18/10/2026. Attendre Google
        # ici coutait de trois a sept dixiemes de seconde a chaque clic qui
        # enregistre, pour une copie dont l'echec ne perd rien. Voir miroir.py.
        import miroir
        miroir.deposer(_organisme(code), fiche["sheet_suivi"], donnees,
                       "suivi de %s" % code)
    except Exception as e:
        print("   (copie du suivi non mise en file, donnee bien enregistree : %s)"
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
        import miroir
        miroir.deposer(org, fiche["sheet_suivi"], donnees,
                       "%d inscrit(s) de %s" % (len(donnees), code))
    except Exception as e:
        print("   (copie du suivi non mise en file, inscrits bien enregistres : %s)"
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
