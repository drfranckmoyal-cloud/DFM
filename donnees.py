import sessions as _sessions
from sessions import nombre as _nombre
from sessions import session, formation, SESSIONS, FORMATIONS, sessions_de, SESSION_ACTIVE
from connexion import service_sheets
from datetime import datetime, date
import suivi
import journal
def _fiche_sessions_sheet():
    """L'etat de vie de chaque session. Le nom reste : les appelants le connaissent.

    NE LIT PLUS L'ONGLET GOOGLE. Cette fonction est appelee deux fois par le
    tableau de bord, et chaque appel telechargeait deux cents lignes.
    """
    try:
        import sessions as _sess
        etats = _sess.etats()
    except Exception:
        return {}
    return {code: {"statut": e.get("statut_session") or "ouverte",
                   "cloture_le": e.get("cloture_le", ""),
                   "emargement_genere_le": e.get("emargement_genere_le", ""),
                   "lien_emargement": e.get("lien_emargement", ""),
                   "emargement_signe_le": e.get("emargement_signe_le", ""),
                   "lien_emargement_signe": e.get("lien_emargement_signe", "")}
            for code, e in etats.items()}
def _qui(ligne, session_resume):
    """Nom, session et adresse — de quoi retrouver la personne en un clic."""
    return {"nom": ((ligne.get("prenom") or "") + " " + (ligne.get("nom") or "")).strip() or "Sans nom",
            "mail": (ligne.get("mail") or "").strip(),
            "code": session_resume.get("code") or "",
            "formation": (session_resume.get("session") or {}).get("nom_formation") or ""}


def _fin_formation(S):
    """Le jour ou la formation se termine, en francais — vide si elle est passee.

    POURQUOI CETTE FONCTION EXISTE. Constate le 20/08/2026 : le parcours
    annoncait « Attestations remises — a faire maintenant » pour une formation
    qui avait lieu DANS 106 JOURS, et offrait un bouton « Faire avancer ce
    dossier » qui ne pouvait rien avancer. generer_attestations.py refusait
    correctement — « trop tot » — mais l'ecran, lui, promettait le contraire et
    concluait « Dossier avance ». On demandait a l'utilisateur de faire une
    chose impossible, puis on lui disait qu'elle etait faite.

    ON LIT LA LISTE DES JOURNEES, pas un champ date_fin : une formation aux
    journees dispersees se termine le dernier jour travaille. C'est la meme
    source que generer_attestations.py — deux regles distinctes finiraient par
    se contredire, et l'ecran mentirait de nouveau.
    """
    try:
        import jours as _j
        fin = (_j.resume(S) or {}).get("date_fin") or ""
        if not fin:
            return ""
        d = datetime.strptime(fin, "%Y-%m-%d").date()
        if (d - date.today()).days <= 0:
            return ""          # la formation a eu lieu : l'etape est ouverte
        return d.strftime("%d/%m/%Y")
    except Exception:
        return ""              # dans le doute, on n'invente pas de blocage


def _parcours_client(S, actifs):
    """Les etapes du dossier d'une session client, dans l'ordre reel.

    POURQUOI CETTE FONCTION EXISTE. L'ecran affichait quatre cartes dont l'etat
    se deduisait des colonnes du SUIVI — « signe_le », « paiement_recu_le ».
    Ce sont les colonnes du parcours INDIVIDUEL : dans une session client
    personne ne signe ligne par ligne, et elles restent vides pour toujours.
    L'ecran annoncait donc « convention a etablir » sur un dossier signe,
    contresigne et facture. Il lisait la mauvaise source.

    Les traces d'une session client vivent sur la FICHE DE SESSION, posees par
    les scripts de la chaine client. C'est ce qu'on lit ici.

    Chaque etape rend : son intitule, son etat, sa date quand elle est
    franchie, et un detail. Une etape franchie porte TOUJOURS une date quand
    elle en a une — c'est le signal qui ne depend ni de la couleur ni de la
    forme, donc le seul qui survive au mode sombre et au daltonisme.
    """
    def v(cle):
        return str(S.get(cle) or "").strip()

    # Les attestations sont individuelles meme en session client : elles sont
    # remises quand chaque participant a la sienne.
    avec_attest = [l for l in actifs if (l.get("attestation_le") or "").strip()]
    attest_faite = bool(actifs) and len(avec_attest) == len(actifs)
    premiere_inscription = min(
        [(l.get("inscrit_le") or "").strip() for l in actifs if (l.get("inscrit_le") or "").strip()],
        default="")

    nb = len(actifs)
    etapes = [
        {"cle": "participants", "titre": "Participants saisis",
         "fait": nb > 0, "date": premiere_inscription,
         "detail": ("%d participant%s" % (nb, "s" if nb > 1 else "")) if nb else
                   "aucun participant — la convention ne peut pas être éditée"},
        {"cle": "convention", "titre": "Convention établie",
         "fait": bool(v("convention_client_envoyee_le")), "date": "",
         "detail": v("convention_client_empreinte")},
        {"cle": "envoi", "titre": "Convention envoyée au client",
         "fait": bool(v("convention_client_envoyee_le")),
         "date": v("convention_client_envoyee_le"), "detail": ""},
        {"cle": "signature", "titre": "Signature du représentant",
         "fait": bool(v("convention_client_signee_le")),
         "date": v("convention_client_signee_le"),
         "detail": v("convention_client_signataire")},
        # LA FACTURE VIENT AVANT LA CONTRESIGNATURE — ordre corrige le
        # 19/08/2026. L'ecran les affichait dans l'autre sens, et annoncait donc
        # « a faire maintenant : convention contresignee » alors que le pipeline
        # commence par emettre la facture — laquelle voyage EN PIECE JOINTE du
        # mail de contresignature. On demandait une etape impossible avant son
        # prealable, et l'utilisateur se croyait bloque.
        {"cle": "facture", "titre": "Facture émise",
         "fait": bool(v("facture_client_numero")), "date": v("facture_client_le"),
         "detail": v("facture_client_numero"), "lien": v("facture_client_lien")},
        {"cle": "contresignee", "titre": "Convention contresignée et facture envoyées",
         "fait": bool(v("convention_client_signee_envoyee_le")),
         "date": v("convention_client_signee_envoyee_le"), "detail": "",
         "lien": v("convention_client_signee_lien")},
        {"cle": "reglement", "titre": "Règlement reçu",
         "fait": bool(v("reglement_client_le")), "date": v("reglement_client_le"),
         "detail": v("reglement_client_reference"), "saisissable": True},
        {"cle": "attestations", "titre": "Attestations remises",
         "fait": attest_faite, "date": "",
         "detail": ("%d sur %d" % (len(avec_attest), nb)) if nb else "après la formation",
         "pas_avant": _fin_formation(S)},
    ]
    # « Convention etablie » n'a pas de trace propre : elle est editee juste
    # avant l'envoi, par le meme passage du pipeline. On lui prete donc la date
    # de l'envoi plutot que d'afficher une etape franchie sans date.
    etapes[1]["date"] = etapes[2]["date"]

    # L'etape EN COURS est la premiere non franchie. C'est elle qui repond a la
    # question « qu'est-ce qui bloque ? », et elle est la seule mise en avant.
    encours = next((e for e in etapes if not e["fait"]), None)
    for e in etapes:
        e["etat"] = "fait" if e["fait"] else ("encours" if e is encours else "attente")
    return etapes


# Sessions dont la derniere lecture du classeur a echoue, et pourquoi.
# INDISPENSABLE : sans cela, une lecture ratee et une session sans inscrit
# produisent le meme ecran vide. Le 05/08/2026, deux processus DFM tournaient
# en parallele avec des identites d'organisme divergentes ; les lectures
# echouaient et DFM annoncait « Aucune inscription validee » sur des sessions
# qui comptaient six inscrits. Rien n'etait perdu, mais rien ne le disait.
_LECTURES_RATEES = {}


def _lire_onglet(S):
    """Les inscrits d'une session, enrichis pour le tableau de bord.

    NE LIT PLUS LE CLASSEUR. C'etait la DERNIERE lecture d'un onglet de suivi
    restee en dehors de suivi.py, et elle tenait le tableau de bord : la page
    d'accueil tombait en erreur des que Google ne repondait pas — decouvert le
    17/08/2026 en coupant le reseau pour de bon plutot qu'en le supposant.

    Le message de « lecture ratee » est conserve : il ne servira presque plus,
    mais une base illisible reste possible, et il dit la bonne chose — c'est la
    lecture qui a echoue, pas le contenu.
    """
    try:
        brutes = suivi.lire_lignes_de(S["code"])
        _LECTURES_RATEES.pop(S["code"], None)
    except Exception as e:
        _LECTURES_RATEES[S["code"]] = (
            "Les inscrits de « %s » n'ont pas pu être lus. "
            "Aucune donnée n'est perdue : c'est la lecture qui a échoué, "
            "pas le contenu. Détail : %s" % (S.get("onglet_suivi") or "?", str(e)[:200]))
        print("   (lecture impossible de %s : %s)" % (S.get("code"), e))
        return []
    lignes = []
    for l in brutes:
        l["_session"] = S["code"]
        l["statut_calcule"] = suivi.calculer_statut(l, l.get("_mode") or "individuel")
        # Porte par la ligne plutot que recalcule dans le gabarit : la reponse
        # au formulaire a plusieurs formes (« Oui », « OUI, fauteuil roulant »),
        # et une condition ecrite en Jinja finirait par en manquer une.
        try:
            import accessibilite as _acc
            l["besoin_adaptation"] = _acc.declare(l)
        except Exception:
            l["besoin_adaptation"] = False
        lignes.append(l)
    return lignes
def _accessibilite(actifs):
    """Qui a declare un besoin d'adaptation, et qui est le referent.

    Le referent est rendu meme quand personne n'a rien declare : c'est son
    ABSENCE qui doit se voir, et elle ne se verrait jamais si on n'affichait le
    bloc que le jour ou quelqu'un declare un besoin.
    """
    try:
        import accessibilite as _a
        gens = _a.concernes(actifs)
        return {"gens": gens, "nombre": len(gens), "referent": _a.referent()}
    except Exception:
        return {"gens": [], "nombre": 0, "referent": {"nom": "", "contact": "", "nomme": False}}


def _resume(S, lignes, fiche_sheet):
    attente = [l for l in lignes if l["statut_calcule"] == "File d'attente"]
    annules = [l for l in lignes if l["statut_calcule"] == "Annulee"]
    demandes = [l for l in lignes if l["statut_calcule"] == "Annulation demandee"]
    recontacter = [l for l in lignes if l["statut_calcule"] == "A recontacter"]
    actifs = [l for l in lignes if l["statut_calcule"] not in
              ("File d'attente", "Annulee", "Annulation demandee", "A recontacter")]
    encaisse = 0.0
    for l in actifs:
        if l["paiement_recu_le"]:
            try:
                encaisse += float(str(l["montant_recu"]).replace(",", ".").replace(" ", "") or 0)
            except ValueError:
                pass
    # Tolerant : une fiche ancienne peut contenir "975 €" ou "1 200" (B6).
    tarif = _nombre(S["tarif"])
    maxi = S["places_max"]
    debut = datetime.strptime(S["date_debut"], "%Y-%m-%d").date()
    fin = datetime.strptime(S["date_fin"], "%Y-%m-%d").date()
    # Les invites occupent une place et suivent toute la chaine, mais aucune
    # somme ne leur est demandee : ils sortent du chiffre d'affaires attendu et
    # du restant du. Les compter fabriquerait un impaye qui n'existe pas.
    invites = [l for l in actifs if l.get("invite_le")]
    payants = [l for l in actifs if not l.get("invite_le")]
    attendu = len(payants) * tarif
    # Le mode est porte jusqu'aux ecrans, mais ne change RIEN au calcul :
    # palier 2, il se declare et s'affiche, il n'agit pas encore.
    _mode = _sessions.mode(S["code"])
    _client_nom = ""
    if _mode == "client":
        try:
            import clients as _CL
            _client_nom = (_CL.client(_sessions.client_de(S["code"])) or {}).get("raison_sociale") or ""
        except Exception:
            _client_nom = ""
    return {
        "mode": _mode, "client_nom": _client_nom,
        "parcours_client": _parcours_client(S, actifs) if _mode == "client" else [],
        "code": S["code"], "session": S, "sheet": fiche_sheet,
        # Vide parce qu'il n'y a personne, ou vide parce qu'on n'a pas su lire ?
        # Les deux ne se disent pas de la meme facon a quelqu'un qui cherche ses
        # inscrits.
        "lecture_ratee": _LECTURES_RATEES.get(S["code"], ""),
        # Les besoins d'adaptation declares a l'inscription. Collectes depuis
        # toujours, affiches nulle part jusqu'au 05/08/2026.
        "accessibilite": _accessibilite(actifs),
        "lignes": lignes, "actifs": actifs, "attente": attente,
        "annules": annules, "demandes_annulation": demandes, "a_recontacter": recontacter,
        "invites": invites, "payants": payants,
        "places_max": maxi, "places_occupees": len(actifs),
        "complet": len(actifs) >= maxi,
        "remplissage": round(100 * len(actifs) / maxi) if maxi else 0,
        "signees": len([l for l in actifs if l["signe_le"]]),
        "regles": len([l for l in payants if l["paiement_recu_le"]]),
        "encaisse": encaisse, "attendu": attendu,
        "reste_du": attendu - encaisse,
        "debut": debut, "fin": fin,
        "jours_avant": (debut - date.today()).days,
        "passee": fin < date.today(),
    }
def toutes_sessions():
    """Les sessions montrees a l'ecran : celles de l'organisme actif seulement.

    C'est LE point de passage de toute l'interface — tableau de bord, liste des
    sessions, conventions, reglements, indicateurs. Filtrer ici plutot que dans
    chaque ecran : un oubli sur un seul ecran ne serait pas un chiffre faux,
    ce serait une certification indefendable."""
    fiches = _fiche_sessions_sheet()
    resultat = []
    for code in _sessions.visibles():
        S = session(code)
        lignes = _lire_onglet(S)
        resultat.append(_resume(S, lignes, fiches.get(code, {"statut": "ouverte"})))
    resultat.sort(key=lambda r: r["debut"])
    return resultat
def une_session(code=None):
    S = session(code)
    fiches = _fiche_sessions_sheet()
    return _resume(S, _lire_onglet(S), fiches.get(S["code"], {"statut": "ouverte"}))
def inscrits_par_mois(sessions=None, mois=12):
    sessions = sessions if sessions is not None else toutes_sessions()
    aujourdhui = date.today()
    seau = {}
    for i in range(mois):
        m = aujourdhui.month - (mois - 1 - i)
        a = aujourdhui.year
        while m <= 0:
            m += 12
            a -= 1
        seau[(a, m)] = 0
    for s in sessions:
        for l in s["lignes"]:
            h = l["horodateur"]
            try:
                d = datetime.strptime(h[:10], "%d/%m/%Y").date()
            except Exception:
                continue
            cle = (d.year, d.month)
            if cle in seau:
                seau[cle] += 1
    ordre = sorted(seau)
    return [{"annee": a, "mois": m, "valeur": seau[(a, m)]} for a, m in ordre]
def _villes(sessions, limite=5):
    compte = {}
    for s in sessions:
        for l in s["actifs"]:
            v = (l["ville"] or "").strip().title()
            if v:
                compte[v] = compte.get(v, 0) + 1
    return sorted(compte.items(), key=lambda x: -x[1])[:limite]
def global_kpi():
    sessions = toutes_sessions()
    annee = date.today().year
    encaisse = sum(s["encaisse"] for s in sessions if s["debut"].year == annee)
    attendu = sum(s["attendu"] for s in sessions if s["debut"].year == annee)
    places = sum(s["places_max"] for s in sessions if not s["passee"])
    occupees = sum(s["places_occupees"] for s in sessions if not s["passee"])
    courbe = inscrits_par_mois(sessions)
    return {
        "sessions": sessions,
        "en_cours": [s for s in sessions if not s["passee"]],
        "passees": [s for s in sessions if s["passee"]],
        "formations": FORMATIONS,
        "ca_annee": encaisse, "ca_attendu": attendu, "annee": annee,
        "remplissage": round(100 * occupees / places) if places else 0,
        "reste_du": sum(s["reste_du"] for s in sessions if not s["passee"]),
        "praticiens_formes": sum(len(s["actifs"]) for s in sessions),
        "villes": _villes(sessions),
        "ca_total": sum(s["encaisse"] for s in sessions),
        "sessions_organisees": len(sessions),
        "sessions_en_cours": len([s for s in sessions if not s["passee"]]),
        "conv_attente": sum(1 for s in sessions for l in s["actifs"]
                            if l["mail1_envoye_le"] and not l["signe_le"]),
        "prix_moyen": (sum(s["encaisse"] for s in sessions) /
                       sum(len([l for l in s["payants"] if l["paiement_recu_le"]]) for s in sessions))
                      if sum(len([l for l in s["payants"] if l["paiement_recu_le"]]) for s in sessions) else 0,
        "formations_realisees": len([s for s in sessions if s["passee"]]),
        "satisfaction": None,
        "courbe": courbe,
        "total_courbe": sum(p["valeur"] for p in courbe),
        # LE BANDEAU D'ALERTE annonce des NOMBRES. Un nombre sans nom ne se
        # traite pas : « 1 reglement en attente » laissait chercher dans trois
        # ecrans sans savoir qui. On rend donc aussi QUI, et sur quelle session,
        # pour que l'alerte mene quelque part.
        "alertes": {
            "annulations": sum(len(s["demandes_annulation"]) for s in sessions),
            "attente": sum(len(s["attente"]) for s in sessions),
            "impayes": sum(1 for s in sessions for l in s["actifs"]
                           if l["mail2_envoye_le"] and not l["paiement_recu_le"]
                           and not l.get("invite_le")),
            "qui_impayes": [_qui(l, s) for s in sessions for l in s["actifs"]
                            if l["mail2_envoye_le"] and not l["paiement_recu_le"]
                            and not l.get("invite_le")][:6],
            "qui_annulations": [_qui(l, s) for s in sessions
                                for l in s["demandes_annulation"]][:6],
            "qui_attente": [_qui(l, s) for s in sessions for l in s["attente"]][:6],
        },
        # LE JOURNAL NE DOIT PAS EMPORTER L'ECRAN. Il est en bas a droite du
        # tableau de bord ; sa lecture faisait pourtant tomber TOUTES les pages
        # qui appellent global_kpi(). Constate le 16/08/2026 : le classeur de
        # DSF n'etant pas partage avec le compte Google connecte, chaque onglet
        # repondait « Internal Server Error » — sans dire lequel des cinquante
        # appels avait echoue.
        #
        # ON NE REND PAS UNE LISTE VIDE EN SILENCE : l'ecran afficherait
        # « Aucune activite », ce qui est faux et envoie chercher au mauvais
        # endroit. Le souci est nomme et remonte jusqu'a l'affichage.
        **_journal_ou_souci(),
    }


def _journal_ou_souci(limite=12):
    try:
        return {"journal": journal.lire(limite), "journal_souci": ""}
    except Exception as e:
        souci = str(e)
        if "does not have permission" in souci or "403" in souci:
            souci = ("Le classeur de suivi de cet organisme n'est pas accessible "
                     "au compte Google connecté à DFM.")
        else:
            souci = "Le journal n'a pas pu être lu : " + souci[:150]
        return {"journal": [], "journal_souci": souci}

def _trouver_dossier(drive, nom, parent=None):
    propre = nom.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name='{propre}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent:
        q += f" and '{parent}' in parents"
    r = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    return r[0]["id"] if r else None
# Les six dossiers d'une session, dans l'ordre d'affichage. Leur description ne
# depend d'aucun reseau : seule leur ADRESSE en depend. Les separer permet de
# rendre l'ecran sans toucher au Drive quand les adresses sont deja connues.
_DOSSIERS_SESSION = [
    ("conv_gen",     "Conventions générées",      "ti-file-text",       "Avant signature"),
    ("conv_sig",     "Conventions signées",       "ti-file-check",      "Signées des deux parties"),
    ("factures",     "Factures",                  "ti-receipt",         "Émises après règlement"),
    ("emargement",   "Feuilles d'émargement",     "ti-clipboard-check", "Vierge et scan signé"),
    ("attestations", "Attestations de formation", "ti-certificate",     "Après la formation"),
    ("envoi",        "Documents d'envoi",         "ti-paperclip",       "Programme, RIB, plan d'accès"),
]


def _fichier_cache_dossiers():
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_dossiers.json")


def _rendre_dossiers(liens, alertes):
    return [{"cle": c, "titre": t, "icone": i, "detail": d,
             "alerte": alertes.get(c, ""), "lien": liens.get(c) or None}
            for c, t, i, d in _DOSSIERS_SESSION]


def _dossiers_memorises(cle_cache):
    try:
        import fichiers
        return (fichiers.lire(_fichier_cache_dossiers(), {}) or {}).get(cle_cache) or {}
    except Exception:
        return {}


def _memoriser_dossiers(cle_cache, liens):
    """ON NE MEMORISE QUE CE QU'ON A TROUVE. Un dossier absent aujourd'hui sera
    cree demain, a la premiere facture ou a la premiere attestation : le retenir
    comme « absent » le rendrait invisible pour toujours. Une adresse trouvee,
    elle, ne change jamais — un identifiant Drive est definitif."""
    try:
        import fichiers
        with fichiers.modifier(_fichier_cache_dossiers(), {}) as d:
            garde = dict(d.get(cle_cache) or {})
            garde.update({k: v for k, v in (liens or {}).items() if v})
            d[cle_cache] = garde
    except Exception:
        pass


def dossiers_session(code=None):
    """Les dossiers Drive de cette session, PAR IDENTIFIANT.

    CE QUE CET ECRAN MONTRAIT AVANT. Il cherchait « Factures »,
    « Attestations », « Emargement » et « Documents d'envoi » par leur NOM, sur
    tout le Drive, et prenait le premier resultat. Il en existe DEUX de chaque
    depuis le cloisonnement. Mesure le 06/08/2026 sur la fiche Smileclub de
    usures-nov26 : « Feuilles d'emargement » et « Documents d'envoi » ouvraient
    les dossiers DE DSF, et « Attestations » affichait « pas encore cree » alors
    que cinq attestations venaient d'y etre deposees — dans le dossier de
    Smileclub, que cette recherche ne regardait pas.

    C'est le meme defaut que celui corrige le 04/08 dans les scripts de
    generation ; cet ecran, qui ne genere rien, avait ete oublie.

    LES SOUS-DOSSIERS DE SESSION, eux, etaient deja justes : ils sont cherches
    sous un parent connu, donc sans ambiguite. Ils ne le devenaient que parce
    que le parent, lui, etait faux.
    """
    S = session(code)
    nom = S["dossier_session"]
    cle_cache = (_sessions.organisme_de(S["code"]) or "") + "/" + S["code"]
    memorise = _dossiers_memorises(cle_cache)
    # LE RESEAU N'EST PLUS TOUCHE QUAND TOUT EST DEJA CONNU. Cette recherche
    # lancait ONZE requetes au Drive — a chaque ouverture, sur chaque session —
    # soit 2,3 des 2,6 secondes que mettait la fiche a s'afficher (mesure du
    # 08/10/2026). Elle ne servait qu'a retrouver six adresses qui ne bougent
    # jamais.
    if all(memorise.get(c) for c, _t, _i, _d in _DOSSIERS_SESSION):
        return _rendre_dossiers(memorise, {})

    from connexion import service_drive
    import dossiers as _d
    drive = service_drive()

    def lien(i):
        return f"https://drive.google.com/drive/folders/{i}" if i else None

    # Les avertissements de `dossiers.trouver` partaient sur la sortie standard,
    # invisible depuis un navigateur. On les RECUPERE pour les afficher a cote
    # du lien concerne : une ambiguite doit se voir la ou elle se produit.
    alertes = []
    def noter(m):
        m = (m or "").strip()
        if m:
            alertes.append(m)

    def racine_de(cle, nom_hist):
        del alertes[:]
        fid = _d.trouver(drive, S, cle, nom_hist, dire=noter)
        return fid, " ".join(alertes)

    fac, a_fac = racine_de("dossier_factures", "Factures")
    att, a_att = racine_de("dossier_attestations", "Attestations")
    emarg, a_emarg = racine_de("dossier_emargement", "Emargement")

    # « Documents d'envoi » n'a jamais eu d'identifiant dans les fiches. On le
    # cherche SOUS la racine de l'organisme plutot que dans tout le Drive :
    # borne a un parent connu, le nom redevient sans ambiguite.
    racine_of = _d.racine(drive, S)
    env = _d.sous_dossier(drive, racine_of, "Documents d'envoi", creer=False) if racine_of else ""
    a_env = "" if racine_of else "Racine de l'organisme introuvable."

    def sous(parent, nom_dossier):
        return _d.sous_dossier(drive, parent, nom_dossier, creer=False) if parent else ""

    liens = {
        "conv_gen":     lien(sous(S.get("dossier_conventions"), nom)),
        "conv_sig":     lien(sous(S.get("dossier_signees"), nom + "-PDF")),
        "factures":     lien(sous(fac, nom)),
        "emargement":   lien(emarg),
        "attestations": lien(sous(att, nom)),
        "envoi":        lien(env),
    }
    _memoriser_dossiers(cle_cache, liens)
    return _rendre_dossiers(liens, {"factures": a_fac, "emargement": a_emarg,
                                    "attestations": a_att, "envoi": a_env})

def tous_praticiens():
    sessions = toutes_sessions()
    par_mail = {}
    for s in sessions:
        for l in s["lignes"]:
            mail = (l["mail"] or "").strip().lower()
            if not mail:
                continue
            p = par_mail.get(mail)
            if not p:
                p = {
                    "mail": mail, "nom": l["nom"], "prenom": l["prenom"],
                    "ville": l["ville"], "telephone": l["telephone"],
                    "image": l["image"], "pmr": l["pmr"], "connu_par": l["connu_par"],
                    "sessions": [], "participations": 0, "regle": 0,
                    "total_paye": 0.0, "derniere": "",
                }
                par_mail[mail] = p
            if l["ville"] and not p["ville"]:
                p["ville"] = l["ville"]
            if l["telephone"] and not p["telephone"]:
                p["telephone"] = l["telephone"]
            statut = l["statut_calcule"]
            p["sessions"].append({
                "code": s["code"], "formation": s["session"]["nom_formation"],
                "date": s["debut"], "statut": statut, "passee": s["passee"],
            })
            if statut not in ("A recontacter", "Annulee", "Annulation demandee", "File d'attente"):
                p["participations"] += 1
            if l["paiement_recu_le"]:
                p["regle"] += 1
                try:
                    p["total_paye"] += float(str(l["montant_recu"]).replace(",", ".").replace(" ", "") or 0)
                except ValueError:
                    pass
            if l["horodateur"] > p["derniere"]:
                p["derniere"] = l["horodateur"]
    for p in par_mail.values():
        p["complet"] = all([p["nom"], p["prenom"], p["mail"], p["telephone"], p["ville"]])
        p["fidele"] = p["participations"] > 1
        p["initiales"] = ((p["nom"][:1] or "") + (p["prenom"][:1] or "")).upper()
        p["sessions"].sort(key=lambda x: x["date"])
    liste = sorted(par_mail.values(), key=lambda p: (p["nom"] or "").upper())
    return {
        "praticiens": liste,
        "total": len(liste),
        "participants": len([p for p in liste if p["participations"]]),
        "fideles": len([p for p in liste if p["fidele"]]),
        "incomplets": len([p for p in liste if not p["complet"]]),
        "ca_cumule": sum(p["total_paye"] for p in liste),
    }

PALETTE_F = ["#4f7ef8", "#7c5bf7", "#0f9e6a", "#d4890a", "#d03b3b", "#0891b2"]
def courbes_formations(sessions=None, mois=12):
    from datetime import date as _d
    sessions = sessions if sessions is not None else toutes_sessions()
    aujourdhui = _d.today()
    cles = []
    for i in range(mois):
        m = aujourdhui.month - (mois - 1 - i)
        a = aujourdhui.year
        while m <= 0:
            m += 12
            a -= 1
        cles.append((a, m))
    index = {c: i for i, c in enumerate(cles)}
    total = [0] * mois
    par_formation = {}
    for s in sessions:
        nom = s["session"]["nom_formation"]
        if nom not in par_formation:
            par_formation[nom] = [0] * mois
        for l in s["lignes"]:
            try:
                d = datetime.strptime(l["horodateur"][:10], "%d/%m/%Y").date()
            except Exception:
                continue
            i = index.get((d.year, d.month))
            if i is not None:
                total[i] += 1
                par_formation[nom][i] += 1
    maxi = max([1] + total)
    L, H, MG, MB = 300.0, 96.0, 10.0, 12.0
    def chemin(valeurs):
        pts = []
        for i, v in enumerate(valeurs):
            x = MG + (L - 2 * MG) * (i / max(1, mois - 1))
            y = (H - MB) - (H - MB - 6) * (v / maxi)
            pts.append(f"{x:.1f} {y:.1f}")
        return "M" + " L".join(pts), pts
    d_total, pts_total = chemin(total)
    aire = d_total + f" L{MG + (L - 2 * MG):.1f} {H - MB:.1f} L{MG:.1f} {H - MB:.1f} Z"
    courbes = []
    for i, (nom, vals) in enumerate(sorted(par_formation.items())):
        d, _ = chemin(vals)
        courbes.append({"nom": nom, "couleur": PALETTE_F[i % len(PALETTE_F)],
                        "chemin": d, "total": sum(vals), "valeurs": vals})
    return {
        "mois": [{"annee": a, "mois": m} for a, m in cles],
        "total": total, "total_somme": sum(total), "maxi": maxi,
        "chemin_total": d_total, "aire_total": aire,
        "dernier_x": MG + (L - 2 * MG), "dernier_y": (H - MB) - (H - MB - 6) * (total[-1] / maxi),
        "courbes": courbes, "largeur": L, "hauteur": H,
    }
