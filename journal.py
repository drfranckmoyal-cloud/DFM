from connexion import service_sheets
from sessions import session
from datetime import datetime
# MEME TOLERANCE QUE DANS suivi.py. « session() » sans code retombe sur
# SESSION_ACTIVE : vide, elle levait « Session inconnue » et faisait tomber toute
# l'application au chargement (502 du 01/10/2026). S ne sert ici que de REPLI
# pour l'identifiant du classeur Google, chemin deja facultatif depuis que le
# journal vit dans dfm.db. Le scellement n'est pas concerne.
try:
    S = session()
except Exception:
    S = {}
ONGLET = "Journal"
ACTIONS = {
    "mail1_envoye_le": ("Mail de signature envoyé", "ti-mail"),
    "signe_le": ("Convention signée", "ti-signature"),
    "convention_pdf_le": ("Convention PDF générée", "ti-file-check"),
    "mail2_envoye_le": ("Mail de confirmation envoyé", "ti-mail-check"),
    "rappel_le": ("Rappel J-20 envoyé", "ti-bell"),
    "paiement_recu_le": ("Règlement enregistré", "ti-coin"),
    "facture_le": ("Facture générée", "ti-receipt"),
    "facture_envoyee_le": ("Facture envoyée", "ti-send"),
    "attestation_le": ("Attestation générée", "ti-certificate"),
    "attestation_envoyee_le": ("Attestation envoyée", "ti-send"),
    "relance_signature_le": ("Relance signature", "ti-repeat"),
    "relance_reglement_le": ("Relance reglement", "ti-repeat"),
    "annulation_demandee_le": ("Annulation demandée", "ti-alert-triangle"),
    "annule_le": ("Annulation validée", "ti-x"),
    "file_attente_le": ("Place en file d'attente", "ti-hourglass"),
    "mail_attente_le": ("Mail file d'attente envoyé", "ti-mail"),
    "promu_le": ("Promotion depuis la file d'attente", "ti-arrow-up"),
    "present": ("Présence pointée", "ti-user-check"),
}
def libelle(champ):
    return ACTIONS.get(champ, (champ, "ti-point"))[0]
def icone(champ):
    return ACTIONS.get(champ, (champ, "ti-point"))[1]
# Actions qui ne se rattachent a aucune session : reglages de l'application,
# identite de l'organisme, bibliotheque de modeles, fiches formation (une
# formation vit au-dessus de ses sessions), et synchronisations qui couvrent
# plusieurs sessions a la fois. Sert a corriger l'AFFICHAGE des entrees deja
# ecrites avec l'ancien repli, sans toucher au Sheet.
SANS_SESSION = {
    "Formation créée", "Formation modifiée", "Formation supprimée",
    "Paramètres modifiés", "Paramètres réinitialisés",
    "Profil de l'organisme modifié", "Changement d'organisme",
    "Organisme créé", "Organisme supprimé",
    "Modèle dupliqué", "Modèle de mail enregistré",
    "Modèle de questionnaire enregistré", "Objectifs du questionnaire réalignés",
    "Questionnaire dupliqué pour une formation", "Fiches apprenant fusionnées",
    "Synchronisation réussie", "Synchronisation interrompue",
    "Synchronisation automatique activée", "Synchronisation automatique désactivée",
    "Envoi automatique en échec", "Rapprochement écarté",
    "Contacts synchronisés", "Contacts importés", "Import annulé", "Contacts fusionnés", "Miroir des contacts mis à jour",
    "Client créé", "Client modifié", "Client supprimé",
    "Journal scellé", "Correction du registre", "Consignation Qualiopi",
    "Réclamation reçue", "Réclamation close",
    "Pièce formateur déposée", "Pièce formateur retirée",
    "Formateur ajouté", "Formateur modifié", "Formateur retiré",
}
def session_ouvrable(code):
    """Une fleche ne doit mener quelque part que si la cible existe encore."""
    if not code:
        return False
    try:
        from sessions import SESSIONS
        return code in SESSIONS
    except Exception:
        return False
def _classeur(code_session=""):
    """Le classeur ou ECRIRE, resolu depuis la session concernee.

    DEFAUT CORRIGE LE 04/08/2026. Ce module figeait « S = session() » a
    l'import : le journal visait le classeur du profil actif au demarrage, et
    n'en bougeait plus. Consequence constatee : les evenements d'une session
    DSF — reglement enregistre, reglement retire — s'inscrivaient dans le
    journal de Smileclub.

    C'est la meme famille que le stockage, l'expediteur et l'identite des
    documents, corriges le meme jour. Mais ici il s'agit de la PISTE D'AUDIT :
    precisement ce qu'un auditeur Qualiopi vient examiner, et le seul endroit
    ou l'on ne peut pas plaider l'erreur d'affichage.

    Sans code de session — reglages, profils, modeles — l'evenement n'appartient
    a aucun organisme en particulier : il va dans le journal de l'organisme
    ACTIF, ce qui est le comportement voulu.
    """
    code = (code_session or "").strip()
    if code:
        try:
            from sessions import session as _s
            feuille = (_s(code) or {}).get("sheet_suivi")
            if feuille:
                return feuille
        except Exception:
            pass
    # On lit le PROFIL ACTIF, pas COMMUN. Meme precedence — le profil l'emporte
    # sur les parametres — mais sans dependre de quiconque ait pense a rappeler
    # sessions.appliquer_identite().
    #
    # DEFAUT CORRIGE LE 05/08/2026, decouvert en testant le scellement.
    # appliquer_identite() n'etait appele que par /profil/basculer. La creation
    # d'un organisme et la suppression de l'organisme actif basculent aussi,
    # sans le rappeler : COMMUN restait pointe sur le classeur precedent — celui
    # d'un profil parfois supprime — pour toute la duree du processus Flask.
    try:
        import profil
        f = ((profil.charger() or {}).get("sheet_suivi") or "").strip()
        if f:
            return f
    except Exception:
        pass
    try:
        from sessions import COMMUN
        return COMMUN.get("sheet_suivi") or (S.get("sheet_suivi") or "")
    except Exception:
        return (S.get("sheet_suivi") or "")


def _organisme(code_session=""):
    """L'organisme dont c'est le journal. EXACTEMENT la regle de _classeur.

    LES DEUX DOIVENT DESIGNER LA MEME ENTITE, toujours. Le journal local et son
    miroir Google sont deux vues d'une seule piste d'audit : si l'une des deux
    resolutions divergeait, on reproduirait le defaut du 04/08/2026 — des
    evenements DSF inscrits dans le journal de Smileclub — en pire, puisque les
    deux vues se contrediraient.

    Sans code de session, l'evenement va a l'organisme ACTIF, comme le classeur.
    """
    code = (code_session or "").strip()
    if code:
        try:
            import sessions as _s
            o = (_s.organisme_de(code) or "").strip()
            if o:
                return o
        except Exception:
            pass
    try:
        import profil
        return profil.actif() or "mon-organisme"
    except Exception:
        return "mon-organisme"


# QUI AGIT, pour la duree d'une requete. Pose par DFM a chaque requete web
# depuis le compte connecte ; laisse vide par les scripts du traitement, qui
# n'ont pas d'utilisateur — et une entree sans auteur se lit alors « DFM »,
# ce qui est la verite plutot qu'un nom emprunte.
AUTEUR = ""


def poser_auteur(nom):
    """Dit au journal au nom de qui les prochaines entrees seront ecrites."""
    global AUTEUR
    AUTEUR = str(nom or "").strip()


def ecrire(type_action, praticien="", detail="", montant="", code_session="", details=""):
    maintenant = datetime.now()
    auteur = (AUTEUR or "").strip()
    ligne = [
        maintenant.strftime("%Y-%m-%d %H:%M:%S"),
        maintenant.strftime("%d/%m/%Y"),
        maintenant.strftime("%H:%M"),
        type_action,
        praticien,
        # Plus de repli sur la session active : un evenement global — reglages,
        # profils, modeles, formations — n'appartient a AUCUNE session. Le repli
        # estampillait 45 entrees sur 182 avec « usures-nov26 », d'ou une
        # etiquette trompeuse et une fleche menant a une session sans rapport.
        code_session,
        detail,
        str(montant) if montant else "",
        # Colonne I : detail long, consultable en depliant la ligne. Il ne doit
        # jamais etre necessaire a la lecture — la phrase courte se suffit.
        str(details or ""),
    ]
    # LE JOURNAL S'ECRIT D'ABORD CHEZ VOUS. Il partait dans le classeur Google,
    # et une panne de reseau faisait disparaitre l'evenement : la piste d'audit
    # etait le seul endroit de DFM ou une indisponibilite se traduisait par un
    # TROU DE PREUVE. C'est desormais l'inverse — Google ne recoit qu'une copie,
    # et son echec ne coute qu'un miroir en retard.
    import base
    import scellement
    org = _organisme(code_session)
    try:
        rang = base.journal_ajouter(org, ligne, auteur=auteur)
    except Exception as e:
        print(f"   (journal non ecrit : {e})")
        return

    # LE SCELLE SE CALCULE SUR LA BASE, plus sur ce que Google renvoie. Meme
    # regle qu'avant : l'ancetre est le scelle du rang precedent, VIDE COMPRIS.
    # A partir d'ici, un scelle manquant est un defaut de preuve, jamais une
    # perte d'information — on ne remonte donc pas l'erreur.
    scelle = ""
    try:
        if rang == 2:
            precedent = scellement._RACINE
        else:
            avant = base.journal_ligne(org, rang - 1) or {}
            precedent = avant.get("scelle") or ""
        scelle = scellement.empreinte(rang, ligne, precedent, auteur)
        base.journal_sceller(org, rang, scelle)
    except Exception as e:
        print(f"   (journal ecrit mais non scelle : {e})")

    # LE MIROIR, ecrit AU RANG DECIDE PAR LA BASE et non par un append. Laisser
    # Google choisir la ligne les ferait diverger au premier decalage, et le
    # scelle — qui porte sur le rang — ne vaudrait plus que pour l'un des deux.
    feuille = _classeur(code_session)
    try:
        service_sheets().spreadsheets().values().update(
            spreadsheetId=feuille, range=f"'{ONGLET}'!A{rang}:J{rang}",
            valueInputOption="USER_ENTERED",
            body={"values": [ligne + [scelle]]},
        ).execute()
    except Exception as e:
        print(f"   (miroir Google en retard, entree bien enregistree : {str(e)[:90]})")


# Rang et empreinte de la derniere ligne scellee par CE processus, par feuille.
# Evite un appel de lecture quand les ecritures se suivent, ce qui est le cas
# courant : un envoi groupe journalise une entree par personne.
_DERNIER = {}


def _rang_ecrit(reponse):
    """« Journal!A186:I186 » -> 186. Google seul sait ou la ligne a atterri."""
    plage = ((reponse or {}).get("updates") or {}).get("updatedRange") or ""
    chiffres = ""
    for c in reversed(plage):
        if c.isdigit():
            chiffres = c + chiffres
        elif chiffres:
            break
    return int(chiffres) if chiffres else 0


def _sceller(feuille, reponse):
    import scellement
    sh = service_sheets()
    rang = _rang_ecrit(reponse)
    if rang < 2:
        return
    valeurs = (((reponse or {}).get("updates") or {}).get("updatedData") or {}).get("values")
    if not valeurs:
        valeurs = sh.spreadsheets().values().get(
            spreadsheetId=feuille, range=f"'{ONGLET}'!A{rang}:I{rang}"
        ).execute().get("values", [[]])
    ligne = (valeurs or [[]])[0]

    cache = _DERNIER.get(feuille)
    if cache and cache[0] == rang - 1:
        precedent = cache[1]
    elif rang == 2:
        precedent = scellement._RACINE
    else:
        # Une autre ecriture s'est intercalee, ou c'est la premiere de ce
        # processus : on va relire l'ancetre plutot que de supposer.
        lu = sh.spreadsheets().values().get(
            spreadsheetId=feuille,
            range=f"'{ONGLET}'!{scellement.COLONNE}{rang - 1}"
        ).execute().get("values", [[]])
        precedent = (lu or [[]]) and (lu[0][0] if lu and lu[0] else "") or ""

    scelle = scellement.empreinte(rang, ligne, precedent)
    sh.spreadsheets().values().update(
        spreadsheetId=feuille,
        range=f"'{ONGLET}'!{scellement.COLONNE}{rang}",
        valueInputOption="RAW", body={"values": [[scelle]]},
    ).execute()
    _DERNIER[feuille] = (rang, scelle)
def depuis_champ(champ, ligne_praticien, detail="", montant="", code_session=""):
    if champ not in ACTIONS:
        return
    prenom = (ligne_praticien.get("prenom") or "").strip()
    nom = (ligne_praticien.get("nom") or "").strip().upper()
    qui = (prenom + " " + nom).strip()
    ecrire(libelle(champ), qui, detail, montant, code_session)
def lire(limite=200):
    """Les entrees de l'organisme actif, la plus recente d'abord.

    LA LECTURE NE PASSE PLUS PAR GOOGLE. Afficher le journal telechargeait
    jusqu'a cinq mille lignes a chaque ouverture de l'ecran ; c'est desormais
    une requete locale, et l'ecran s'ouvre meme reseau coupe.
    """
    import base
    org = _organisme()
    # On demande large : le tri se fait ensuite sur l'horodatage, comme avant,
    # parce que le rang suit l'ordre d'ECRITURE et pas toujours celui du temps.
    brutes = base.journal_lire(org, limite=max(int(limite), 1) * 5)
    champs = ["horodatage", "date", "heure", "type_action", "praticien", "session",
              "detail", "montant", "details"]
    _DE_LA_BASE = ["horodateur", "date", "heure", "type_action", "praticien",
                   "code_session", "detail", "montant", "details"]
    lignes = []
    for b in brutes:
        e = {c: (b.get(k) or "") for c, k in zip(champs, _DE_LA_BASE)}
        # Entrees anterieures : le repli leur a colle la session active. On la
        # retire a l'affichage — ni etiquette, ni fleche — plutot que de
        # reecrire 45 lignes du Sheet.
        if e["type_action"] in SANS_SESSION:
            e["session"] = ""
        e["ouvrable"] = session_ouvrable(e["session"])
        e["phrase"] = phrase(e)
        lignes.append(e)
    lignes.sort(key=lambda l: l["horodatage"], reverse=True)
    return lignes[:limite]

def _feuilles():
    """Les classeurs de journal des deux organismes, sans tenir compte du profil.

    Verifier la seule feuille active reviendrait a ne verifier qu'une piste
    d'audit sur deux, ce qui est exactement le defaut corrige le 04/08/2026.
    """
    sortie = []
    try:
        import profil
        for p in profil.lister():
            ident = p["id"] if isinstance(p, dict) else p
            fiche = profil.charger(ident) or {}
            f = fiche.get("sheet_suivi")
            if f and f not in [x[1] for x in sortie]:
                sortie.append((fiche.get("marque") or ident, f))
    except Exception:
        pass
    if not sortie:
        sortie = [("", _classeur())]
    return sortie


def _cibles_verif(feuille=None):
    """Les organismes a verifier : (marque, organisme, classeur miroir).

    Verifier le seul organisme actif reviendrait a ne controler qu'une piste
    d'audit sur deux — le defaut du 04/08/2026.
    """
    sortie = []
    vus = False
    try:
        import profil
        for p in profil.lister():
            ident = p["id"] if isinstance(p, dict) else p
            fiche = profil.charger(ident) or {}
            f = fiche.get("sheet_suivi") or ""
            vus = True
            # DESIGNE PAR SON IDENTIFIANT OU PAR SON CLASSEUR.
            #
            # DEFAUT CORRIGE LE 18/08/2026. Le filtre ne comparait qu'au
            # classeur miroir. Depuis que la base fait autorite, on appelle
            # naturellement verifier("dsf") — qui ne correspondait a aucun
            # classeur : la liste restait vide, la ligne de secours plus bas
            # prenait alors l'organisme ACTIF, et le resultat repartait
            # ETIQUETE AU NOM DEMANDE. Un verificateur de piste d'audit qui
            # repond sur un autre organisme que celui qu'on lui nomme est pire
            # qu'un verificateur absent : on le croit.
            if feuille and feuille not in (f, ident):
                continue
            sortie.append((fiche.get("marque") or ident, ident, f))
    except Exception:
        pass
    if not sortie and not (vus and feuille):
        # Aucun profil lisible : on retombe sur l'organisme actif. Mais si des
        # profils EXISTENT et qu'aucun ne porte le nom demande, on ne rend rien
        # — se taire vaut mieux que repondre sur quelqu'un d'autre.
        sortie = [("", _organisme(), feuille or _classeur())]
    return sortie


def _valeurs_base(organisme):
    """Le journal d'un organisme, en lignes de dix colonnes, rangs conserves.

    On rend la MEME FORME que ce que renvoyait le classeur — une liste de
    listes indexee par le rang — pour que la verification en dessous reste mot
    pour mot celle qui a ete eprouvee. Changer le magasin ET la regle dans le
    meme mouvement, c'est se priver du moyen de savoir lequel des deux a fauté.
    """
    import base
    lignes = base.journal_toutes(organisme)
    if not lignes:
        return []
    dernier = lignes[-1]["rang"]
    par_rang = {l["rang"]: l for l in lignes}
    sortie = []
    for rang in range(2, dernier + 1):
        l = par_rang.get(rang)
        if not l:
            sortie.append([])          # trou : une ligne vide, comme dans la feuille
            continue
        # L'auteur voyage EN ONZIEME position, apres le scelle : les dix
        # premieres gardent leur index, donc la verification en dessous — et
        # tout ce qui lit le journal — ne bouge pas d'une ligne.
        try:
            a = l["auteur"] or ""
        except Exception:
            a = ""
        sortie.append([l[c] for c in base.CHAMPS_JOURNAL] + [a])
    return sortie


def verifier(feuille=None):
    """Recalculer la chaine et dire ou elle se rompt, s'il y a lieu.

    Rend une fiche par organisme. « intacte » signifie : aucune ligne modifiee,
    ajoutee ni supprimee depuis son ecriture par DFM — dans la limite de ce que
    prouve un scelle dont la cle est sur cette machine, ce que l'ecran dit.

    ON VERIFIE LA BASE, PLUS LE CLASSEUR. L'autorite a change de main : le
    classeur n'est qu'un miroir, et controler un miroir ne prouve rien sur
    l'original. Une verification qui porterait sur la copie donnerait le pire
    des resultats — rassurante, et vide de sens.

    L'argument `feuille` est conserve : les appelants le passent, et il sert
    encore a designer UN organisme. On le traduit en organisme.
    """
    import scellement
    cibles = _cibles_verif(feuille)
    fiches = []
    for marque, org, f in cibles:
        try:
            valeurs = _valeurs_base(org)
        except Exception as e:
            fiches.append({"marque": marque, "feuille": f, "lisible": False,
                           "souci": str(e), "entrees": 0})
            continue
        # « Precedent » = le scelle de la ligne PHYSIQUEMENT au-dessus, vide
        # compris. C'est ce que _sceller lit au moment de l'ecriture ; toute
        # autre definition ferait diverger la verification de la pose.
        #
        # DEFAUT CORRIGE LE 05/08/2026. La version precedente sautait les lignes
        # non scellees en conservant l'ancetre d'avant : une seule entree ecrite
        # par un processus depourvu de scellement — cas reel : le serveur reste
        # en cours depuis plusieurs jours — et TOUTES les entrees suivantes
        # etaient declarees rompues. Une piste d'audit qui crie a la fraude sur
        # un incident d'exploitation ne sera plus jamais regardee.
        total = 0
        scellees = 0
        rupture = None
        for i, brute in enumerate(valeurs):
            rang = i + 2
            if not brute or not str(brute[0] if brute else "").strip():
                continue
            total += 1
            complete = list(brute) + [""] * (11 - len(brute))
            pose = (complete[9] or "").strip()
            if not pose:
                # Non scellee : n'atteste rien, ne rompt rien. Elle est comptee
                # a part, et c'est ce compte qui doit alerter.
                continue
            if rang == 2:
                precedent = scellement._RACINE
            else:
                avant = valeurs[i - 1] if i >= 1 else []
                precedent = (list(avant) + [""] * 11)[9].strip()
            attendu = scellement.empreinte(rang, complete[:9], precedent,
                                           complete[10])
            if pose != attendu and rupture is None:
                rupture = {"rang": rang,
                           "quand": complete[1] or complete[0],
                           "quoi": complete[3], "qui": complete[4]}
            scellees += 1
        d = scellement.demarrage(f)
        fiches.append({
            "marque": marque, "feuille": f, "lisible": True, "souci": "",
            "entrees": total, "scellees": scellees,
            "non_scellees": total - scellees,
            "intacte": rupture is None and scellees > 0,
            "rupture": rupture,
            "pose_le": d.get("pose_le") or "",
            "retroactif_jusqu_a": d.get("retroactif_jusqu_a") or 0,
            "lien": "https://docs.google.com/spreadsheets/d/%s" % f,
        })
    return fiches


_CACHE_FORMATIONS = {}
def nom_formation(code_session):
    if not code_session:
        return ""
    if code_session in _CACHE_FORMATIONS:
        return _CACHE_FORMATIONS[code_session]
    nom = code_session
    try:
        from sessions import session as _s
        f = _s(code_session)
        nom = f.get("nom_formation") or code_session
    except Exception:
        pass
    _CACHE_FORMATIONS[code_session] = nom
    return nom
PHRASES = {
    "Rapprochement écarté": "Un rapprochement de doublons a été écarté — {d}",
    "Contacts synchronisés": "Les inscrits du classeur ont été repris dans la base de contacts — {d}",
    "Contacts importés": "Une liste a été importée dans la base de contacts — {p} : {d}",
    "Import annulé": "Un import de contacts a été annulé — {d}",
    "Contacts fusionnés": "Deux fiches de contact ont été fusionnées — {p} : {d}",
    "Miroir des contacts mis à jour": "La copie lisible des contacts a été rafraîchie — {d}",
    "Convention client envoyée": "La convention a été envoyée au client pour signature — {p} : {d}",
    "Convention client éditée": "La convention unique d'une session client a été éditée — {p} : {d}",
    "Participants saisis": "Les participants d'une session client ont été saisis — {d}",
    "Client créé": "Un client a été ajouté à la base — {p} ({d})",
    "Client modifié": "La fiche d'un client a été modifiée — {p}",
    "Client supprimé": "Un client a été retiré de la base — {p} ; {d}",
    "Règlement corrigé": "Le règlement de {p} a été retiré sur {f} — {d}",
    "Apprenant invité": "{p} est invité·e par l'organisme sur {f} — aucun règlement demandé",
    "Invitation retirée": "L'invitation de {p} a été retirée sur {f} — retour au circuit normal",
    "Convention PDF générée": "La convention signée de {p} a été générée · {f}",
    "Mail de confirmation envoyé": "Confirmation d'inscription envoyée à {p} · {f}",
    "Mail file d'attente envoyé": "Mail de file d'attente envoyé à {p} · {f}",
    "Facture générée": "Facture de {p} générée · {f}",
    "Facture envoyée": "Facture envoyée à {p} · {f}",
    "Attestation envoyée": "Attestation envoyée à {p} · {f}",
    "Présence pointée": "Présence de {p} pointée sur {f}",
    "Nouvelle inscription": "{p} s'est inscrit sur la session {f}",
    "Session terminée et archivée": "Administrateur a déclaré la session {f} terminée — {d}",
    "Session déverrouillée": "Administrateur a déverrouillé la session {f} — {d}",
    "Clôture reportée": "Clôture de {f} reportée — {d}",
    "Demande sur session clôturée": "{p} a demandé à s'inscrire sur {f}, déjà clôturée",
    "Fiches apprenant fusionnées": "Fiches de {p} fusionnées — {d}",
    "Réinscription": "{p} s'est réinscrit — il a déjà {d}",
    "Demande de rappel reçue": "{p} a demandé à être recontacté au sujet de {f}",
    "Inscriptions importées": "Administrateur a importé les inscriptions de la session {f} — {d}",
    "Place en file d'attente": "{p} a été placé en file d'attente sur {f}",
    "Passage en file d'attente": "{p} a été placé en file d'attente sur {f}",
    "Promotion depuis la file d'attente": "{p} a été promu depuis la file d'attente sur {f}",
    "Promu depuis la file d'attente": "{p} a été promu depuis la file d'attente sur {f}",
    "Reintegration": "{p} a été réintégré sur {f} — {d}",
    "Mail de signature envoyé": "Convention envoyée à {p} pour signature · {f}",
    "Convention signée": "{p} a signé sa convention · {f}",
    "Rappel J-20 envoyé": "Rappel avant formation envoyé à {p} · {f}",
    "Relance signature": "Relance de signature envoyée à {p} — {d}",
    "Relance reglement": "Relance de règlement envoyée à {p} — {d}",
    "Règlement reçu": "Règlement reçu de {p} · {f} — {d}",
    "Règlement enregistré": "Règlement de {p} enregistré — {d}",
    "Attestation générée": "Attestation de {p} générée · {f}",
    "Annulation demandée": "{p} a demandé l'annulation de son inscription sur {f}",
    "Annulation validée": "Annulation de {p} validée sur {f} — {d}",
    "Annulation refusée": "Demande d'annulation de {p} refusée sur {f}",
    "Évaluation d'entrée complétée": "{p} a répondu à l'évaluation d'entrée · {f} — {d}",
    "Évaluation de sortie complétée": "{p} a répondu à l'évaluation de sortie · {f} — {d}",
    "Questionnaire de satisfaction complété": "{p} a répondu au questionnaire de satisfaction · {f} — {d}",
    "Évaluation à froid complétée": "{p} a répondu à l'évaluation à froid · {f} — {d}",
    "Questionnaires préparés": "Administrateur a préparé les questionnaires de la session {f} — {d}",
    "Questionnaires publiés": "Administrateur a préparé les questionnaires de la session {f} — {d}",
    "Réponses relevées": "Résultats des questionnaires récupérés · {f} — {d}",
    "Réponses relevées automatiquement": "Résultats récupérés automatiquement · {f} — {d}",
    "Récapitulatif pédagogique envoyé": "Récapitulatif pédagogique envoyé à {p} — {d}",
    "Journal scellé": "Le journal a été scellé — {d}",
    "Consignation Qualiopi": "Une preuve Qualiopi a été consignée — {d}",
    "Correction du registre": "Correction apportée à un registre — {d}",
    "Réclamation reçue": "Une réclamation a été enregistrée — {p} : {d}",
    "Réclamation close": "Une réclamation a été close — {p} : {d}",
    "Formateur ajouté": "{p} a été ajouté au registre des formateurs",
    "Formateur modifié": "La fiche du formateur {p} a été modifiée",
    "Formateur retiré": "{p} a été retiré du registre des formateurs — {d}",
    "Pièce formateur déposée": "Une pièce a été ajoutée au dossier formateur — {d}",
    "Pièce formateur retirée": "Une pièce du dossier formateur a été retirée — {d}",
    "Formation créée": "Administrateur a créé la formation « {d} »",
    "Formation modifiée": "Administrateur a modifié la formation « {d} »",
    "Formation supprimée": "Administrateur a supprimé la formation « {d} »",
    "Session créée": "Administrateur a créé une session — {d}",
    "Session supprimée": "Administrateur a supprimé une session — {d}",
    "Inscriptions clôturées": "Administrateur a clôturé les inscriptions de la session {f} — {d}",
    "Inscriptions rouvertes": "Administrateur a rouvert les inscriptions de la session {f}",
    "Feuille d'émargement générée": "Feuille d'émargement générée · {f} — {d}",
    "Émargement signé reçu": "Émargement signé reçu · {f} — {d}",
    "Émargement signé délié": "Administrateur a délié l'émargement signé de la session {f}",
    "Modèle de questionnaire enregistré": "Administrateur a enregistré le modèle « {d} »",
    "Objectifs du questionnaire réalignés": "Objectifs du modèle « {d} » réalignés sur la formation",
    "Questionnaire dupliqué pour une formation": "Modèle de questionnaire dupliqué pour {d}",
}
def phrase(entree):
    type_action = (entree.get("type_action") or "").strip()
    p = (entree.get("praticien") or "").strip()
    d = (entree.get("detail") or "").strip()
    f = (entree.get("session") or "").strip()
    modele = PHRASES.get(type_action)
    if not modele:
        for cle, m in PHRASES.items():
            if type_action.startswith(cle):
                modele = m
                break
    if not modele:
        bout = type_action
        if p:
            bout += " — " + p
        if d:
            bout += " (" + d + ")"
        return bout
    nomf = f or "la session"
    texte = modele.replace("{p}", p or "un praticien").replace("{f}", nomf).replace("{d}", d)
    texte = texte.replace(" — )", ")").replace("( )", "")
    if texte.endswith(" — "):
        texte = texte[:-3]
    if texte.endswith("—"):
        texte = texte[:-1].rstrip()
    return texte.strip()
STYLES = {
    "Nouvelle inscription": ("ti-user-plus", "#4f7ef8", "#eef3fe", "inscriptions"),
    "Session terminée et archivée": ("ti-archive", "#6b7280", "#f1f2f6", "administration"),
    "Session déverrouillée": ("ti-lock-open", "#d4890a", "#fdf0dc", "administration"),
    "Clôture reportée": ("ti-clock-pause", "#6b7280", "#f1f2f6", "administration"),
    "Demande sur session clôturée": ("ti-user-exclamation", "#d4890a", "#fdf0dc", "inscriptions"),
    "Fiches apprenant fusionnées": ("ti-git-merge", "#6b7280", "#f1f2f6", "administration"),
    "Réinscription": ("ti-user-check", "#0f9e6a", "#eafaf3", "inscriptions"),
    "Demande de rappel reçue": ("ti-phone", "#d4890a", "#fdf0dc", "inscriptions"),
    "Passage en file d'attente": ("ti-hourglass", "#d4890a", "#fdf0dc", "inscriptions"),
    "Reintegration": ("ti-arrow-back-up", "#4f7ef8", "#eef3fe", "inscriptions"),
    "Annulation refusée": ("ti-hand-stop", "#d4890a", "#fdf0dc", "annulations"),
    "Règlement enregistré": ("ti-building-bank", "#0f9e6a", "#eafaf3", "reglements"),
    "Évaluation d'entrée complétée": ("ti-school", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Évaluation de sortie complétée": ("ti-school", "#0f9e6a", "#eafaf3", "questionnaires"),
    "Questionnaire de satisfaction complété": ("ti-star", "#d4890a", "#fdf0dc", "questionnaires"),
    "Évaluation à froid complétée": ("ti-clock-hour-9", "#d4890a", "#fdf0dc", "questionnaires"),
    "Questionnaires préparés": ("ti-clipboard-check", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Questionnaires publiés": ("ti-clipboard-check", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Réponses relevées": ("ti-download", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Réponses relevées automatiquement": ("ti-download", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Récapitulatif pédagogique envoyé": ("ti-send", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Envoi automatique en échec": ("ti-alert-triangle", "#d03b3b", "#fdeaea", "questionnaires"),
    "Modèle de questionnaire enregistré": ("ti-file-pencil", "#6b7280", "#f1f2f6", "administration"),
    "Objectifs du questionnaire réalignés": ("ti-target", "#6b7280", "#f1f2f6", "administration"),
    "Questionnaire dupliqué pour une formation": ("ti-copy", "#6b7280", "#f1f2f6", "administration"),
    "Formation créée": ("ti-folder-plus", "#6b7280", "#f1f2f6", "administration"),
    "Formation modifiée": ("ti-folder-cog", "#6b7280", "#f1f2f6", "administration"),
    "Formation supprimée": ("ti-folder-x", "#d03b3b", "#fdeaea", "administration"),
    "Session créée": ("ti-calendar-plus", "#6b7280", "#f1f2f6", "administration"),
    "Session supprimée": ("ti-calendar-x", "#d03b3b", "#fdeaea", "administration"),
    "Émargement signé délié": ("ti-unlink", "#d4890a", "#fdf0dc", "formation"),
    "Mail de signature envoyé": ("ti-mail", "#4f7ef8", "#eef3fe", "mails"),
    "Convention signée": ("ti-writing-sign", "#0f9e6a", "#eafaf3", "signatures"),
    "Convention PDF générée": ("ti-file-check", "#0f9e6a", "#eafaf3", "signatures"),
    "Mail de confirmation envoyé": ("ti-mail-check", "#4f7ef8", "#eef3fe", "mails"),
    "Rappel J-20 envoyé": ("ti-bell", "#d4890a", "#fdf0dc", "mails"),
    "Règlement reçu": ("ti-building-bank", "#0f9e6a", "#eafaf3", "reglements"),
    "Facture générée": ("ti-file-invoice", "#0f9e6a", "#eafaf3", "reglements"),
    "Facture envoyée": ("ti-send", "#4f7ef8", "#eef3fe", "reglements"),
    "Attestation générée": ("ti-certificate", "#7c5bf7", "#f0eefe", "formation"),
    "Attestation envoyée": ("ti-send", "#7c5bf7", "#f0eefe", "formation"),
    "Relance signature": ("ti-mail-forward", "#d4890a", "#fdf0dc", "mails"),
    "Relance reglement": ("ti-mail-forward", "#d4890a", "#fdf0dc", "mails"),
    "Annulation demandée": ("ti-alert-triangle", "#d03b3b", "#fdeaea", "annulations"),
    "Annulation validée": ("ti-user-x", "#d03b3b", "#fdeaea", "annulations"),
    "Place en file d'attente": ("ti-hourglass", "#d4890a", "#fdf0dc", "inscriptions"),
    "Mail file d'attente envoyé": ("ti-mail", "#4f7ef8", "#eef3fe", "mails"),
    "Promu depuis la file d'attente": ("ti-arrow-up", "#4f7ef8", "#eef3fe", "inscriptions"),
    # Libelle reellement ecrit par la route de promotion : sans cette entree,
    # l'evenement s'affichait avec le style par defaut, sans icone ni couleur.
    "Promotion depuis la file d'attente": ("ti-arrow-up", "#4f7ef8", "#eef3fe", "inscriptions"),
    # --- Libelles produits par l'application mais jamais declares ici ---
    # Sans style, une entree tombe sur le point gris « autre » : indistinguable
    # a l'oeil, et surtout inclassable, la categorie servant au filtrage.
    # 22 % des entrees etaient dans ce cas au 02/08/2026.
    "Synchronisation réussie":              ("ti-refresh", "#0f9e6a", "#eafaf3", "administration"),
    "Synchronisation interrompue":          ("ti-refresh-alert", "#d03b3b", "#fdeaea", "administration"),
    "Synchronisation automatique activée":  ("ti-player-play", "#0f9e6a", "#eafaf3", "administration"),
    "Synchronisation automatique désactivée": ("ti-player-pause", "#6b7280", "#f1f2f6", "administration"),
    "Envoi automatique en échec":           ("ti-alert-triangle", "#d03b3b", "#fdeaea", "administration"),
    "Paramètres modifiés":                  ("ti-settings", "#6b7280", "#f1f2f6", "administration"),
    "Paramètres réinitialisés":             ("ti-rotate", "#d4890a", "#fdf3e3", "administration"),
    "Profil de l'organisme modifié":        ("ti-building", "#4f7ef8", "#eef3fe", "administration"),
    "Changement d'organisme":               ("ti-switch-horizontal", "#7c5bf7", "#f0eefe", "administration"),
    "Organisme créé":                       ("ti-building-plus", "#0f9e6a", "#eafaf3", "administration"),
    "Organisme supprimé":                   ("ti-building-off", "#d03b3b", "#fdeaea", "administration"),
    "Modèle de mail enregistré":            ("ti-mail-cog", "#4f7ef8", "#eef3fe", "administration"),
    "Modèle de questionnaire enregistré":   ("ti-clipboard-text", "#4f7ef8", "#eef3fe", "administration"),
    "Modèle dupliqué":                      ("ti-copy", "#6b7280", "#f1f2f6", "administration"),
    "Objectifs du questionnaire réalignés": ("ti-target", "#d4890a", "#fdf3e3", "questionnaires"),
    "Questionnaire dupliqué pour une formation": ("ti-copy", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Fiches apprenant fusionnées":          ("ti-users", "#7c5bf7", "#f0eefe", "administration"),
    "Renvoi groupe convention":             ("ti-send", "#4f7ef8", "#eef3fe", "mails"),
    "Renvoi groupe facture":                ("ti-send", "#0f9e6a", "#eafaf3", "mails"),
    "Renvoi groupe attestation":            ("ti-send", "#7c5bf7", "#f0eefe", "mails"),
    "Renvoi groupe programme":              ("ti-send", "#d4890a", "#fdf3e3", "mails"),
    "Relance règlement":                    ("ti-bell-dollar", "#d4890a", "#fdf3e3", "reglements"),
    "Évaluation d'entrée envoyé":           ("ti-clipboard-check", "#4f7ef8", "#eef3fe", "questionnaires"),
    "Évaluation de sortie envoyé":          ("ti-clipboard-check", "#4f7ef8", "#eef3fe", "questionnaires"),
    "Questionnaire de satisfaction envoyé": ("ti-star", "#d4890a", "#fdf3e3", "questionnaires"),
    "Évaluation à froid, 3 mois après envoyé": ("ti-clock-hour-9", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Récapitulatif pédagogique envoyé":     ("ti-file-text", "#4f7ef8", "#eef3fe", "questionnaires"),
    "Règlement corrigé":                    ("ti-eraser", "#d03b3b", "#fdeaea", "reglements"),
    "Rapprochement écarté":                 ("ti-user-off", "#6b7280", "#f1f2f6", "administration"),
    "Contacts synchronisés":                ("ti-refresh", "#4f7ef8", "#eef3ff", "administration"),
    "Contacts importés":                    ("ti-file-import", "#0f9e6a", "#eafaf3", "administration"),
    "Import annulé":                        ("ti-arrow-back-up", "#d4890a", "#fdf3e3", "administration"),
    "Contacts fusionnés":                   ("ti-arrows-join", "#635BFF", "#f0eeff", "administration"),
    "Miroir des contacts mis à jour":       ("ti-table-share", "#4f7ef8", "#eef3ff", "administration"),
    "Participants saisis":                  ("ti-user-plus", "#0f9e6a", "#eafaf3", "inscriptions"),
    "Convention client éditée":             ("ti-file-certificate", "#4f7ef8", "#eef3ff", "documents"),
    "Convention client envoyée":            ("ti-send", "#0f9e6a", "#eafaf3", "documents"),
    "Client créé":                          ("ti-building-plus", "#0f9e6a", "#eafaf3", "administration"),
    "Client modifié":                       ("ti-building", "#4f7ef8", "#eef3ff", "administration"),
    "Client supprimé":                      ("ti-building-off", "#d4890a", "#fdf3e3", "administration"),
    "Apprenant invité":                     ("ti-gift", "#d4890a", "#fdf3e3", "reglements"),
    "Invitation retirée":                   ("ti-gift-off", "#6b7280", "#f1f2f6", "reglements"),
    "Évaluation d'entrée envoyé automatiquement": ("ti-clipboard-check", "#4f7ef8", "#eef3fe", "questionnaires"),
    "Évaluation de sortie envoyé automatiquement": ("ti-clipboard-check", "#4f7ef8", "#eef3fe", "questionnaires"),
    "Questionnaire de satisfaction envoyé automatiquement": ("ti-star", "#d4890a", "#fdf3e3", "questionnaires"),
    "Évaluation à froid, 3 mois après envoyé automatiquement": ("ti-clock-hour-9", "#7c5bf7", "#f0eefe", "questionnaires"),
    "Promotion depuis file d'attente": ("ti-arrow-up", "#4f7ef8", "#eef3fe", "inscriptions"),
    "Présence pointée": ("ti-user-check", "#0f9e6a", "#eafaf3", "formation"),
    "Journal scellé": ("ti-shield-check", "#0f9e6a", "#eafaf3", "administration"),
    "Consignation Qualiopi": ("ti-checkup-list", "#7c5bf7", "#f0eefe", "administration"),
    "Correction du registre": ("ti-eraser", "#d4890a", "#fdf3e3", "administration"),
    "Réclamation reçue": ("ti-message-report", "#d4890a", "#fdf3e3", "administration"),
    "Réclamation close": ("ti-message-check", "#0f9e6a", "#eafaf3", "administration"),
    "Formateur ajouté": ("ti-user-plus", "#0f9e6a", "#eafaf3", "administration"),
    "Formateur modifié": ("ti-user-edit", "#4f7ef8", "#eef3fe", "administration"),
    "Formateur retiré": ("ti-user-minus", "#d4890a", "#fdf3e3", "administration"),
    "Pièce formateur déposée": ("ti-certificate-2", "#0f9e6a", "#eafaf3", "administration"),
    "Pièce formateur retirée": ("ti-trash", "#d4890a", "#fdf3e3", "administration"),
    "Inscriptions importées": ("ti-user-plus", "#4f7ef8", "#eef3fe", "inscriptions"),
    "Inscriptions clôturées": ("ti-lock", "#6b7280", "#f1f2f6", "formation"),
    "Inscriptions rouvertes": ("ti-lock-open", "#6b7280", "#f1f2f6", "formation"),
    "Feuille d'émargement générée": ("ti-clipboard-list", "#4f7ef8", "#eef3fe", "formation"),
    "Émargement signé reçu": ("ti-clipboard-check", "#0f9e6a", "#eafaf3", "formation"),
}
CATEGORIES = [
    ("tout", "Tout", "ti-list"),
    ("inscriptions", "Inscriptions", "ti-user-plus"),
    ("signatures", "Signatures", "ti-writing-sign"),
    ("reglements", "Règlements", "ti-coin"),
    ("mails", "Mails", "ti-mail"),
    ("formation", "Formation", "ti-school"),
    ("annulations", "Annulations", "ti-user-x"),
    ("questionnaires", "Questionnaires", "ti-clipboard-list"),
    ("administration", "Administration", "ti-settings"),
]
def style(type_action):
    i, c, f, cat = STYLES.get(type_action, ("ti-point", "#6b7280", "#f1f2f6", "autre"))
    return {"icone": i, "couleur": c, "fond": f, "categorie": cat}
