"""Ranger un document produit par DFM, et le retrouver.

POURQUOI CE MODULE EXISTE. Chaque script disait la meme chose a sa facon :
« depose ce PDF dans tel dossier du Drive, puis va me le rechercher dans le
Drive pour le joindre a un mail ». Trente endroits, la meme logique recopiee,
et un aller-retour reseau pour un fichier qu'on venait de fabriquer.

CE MODULE EST UNE PORTE, PAS UN DOSSIER. L'appelant dit « range ceci » et
« rends-le-moi » ; il n'apprend jamais ou c'est. C'est deliberé : DFM doit
devenir un logiciel en ligne, et le jour ou les documents vivront sur un
serveur, SEUL CE FICHIER changera. Les scripts, eux, ne bougeront pas.

L'IMPLEMENTATION D'AUJOURD'HUI ecrit sur le disque de la machine et pousse une
copie dans le Drive. Le local est la reference — c'est lui qu'on relit ; le
Drive reste l'archive consultable depuis un telephone. Le jour du passage en
ligne, on remplace _ranger_local par un stockage objet et on garde le reste.

CE QUI N'EST PAS MIGRE. Les documents deja produits restent dans le Drive, avec
leurs liens valides : on n'ecrit le nouveau ailleurs qu'a partir de maintenant.
"""
import os

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.join(_DOSSIER, "documents")

# L'index relie une reference locale a son adresse dans le Drive. Il vit A COTE
# des fichiers, comme celui des justificatifs de veille : une copie peut etre
# poussee LONGTEMPS apres le rangement — le jour ou Google redevient joignable —
# et figer l'adresse dans la fiche obligerait a la rouvrir pour la corriger.
_INDEX = os.path.join(RACINE, "_index.json")

# Les categories, et le dossier Drive de chacune. C'est la seule table qui
# connait les deux mondes ; les scripts ne nomment plus que la categorie.
# Le troisieme element est le SUFFIXE du sous-dossier de session dans le Drive.
# Les conventions signees vivent depuis toujours sous « <session>-PDF » ; le
# perdre aurait deplace vos documents sans prevenir.
CATEGORIES = {
    "convention": ("dossier_conventions", "Conventions", ""),
    "convention_signee": ("dossier_signees", "Conventions signees", "-PDF"),
    "facture": ("dossier_factures", "Factures", ""),
    "attestation": ("dossier_attestations", "Attestations", ""),
    "emargement": ("dossier_emargement", "Emargement", ""),
}


def _sain(t):
    return "".join(c for c in str(t or "") if c.isalnum() or c in "-_. ").strip() or "x"


def _index_lire():
    import fichiers
    d = fichiers.lire(_INDEX, {})
    return d if isinstance(d, dict) else {}


def reference(code_session, categorie, nom):
    """L'adresse d'un document dans DFM, independante de son stockage.

    « dsf/usures-apdpcnov26/facture/Facture F2026-011.pdf ». C'est cette chaine
    que l'on garde et que l'on repasse a lire() — jamais un chemin de disque,
    jamais une URL.
    """
    import sessions as _s
    org = _s.organisme_de(code_session) or "sans-organisme"
    return "/".join((_sain(org), _sain(code_session), _sain(categorie), _sain(nom)))


def chemin(ref):
    """Le chemin sur disque, ou None. Refuse toute reference qui sort de RACINE.

    Le controle n'est pas theorique : une reference vient d'un fichier JSON,
    donc d'une valeur qu'un editeur de texte a pu modifier.
    """
    if not ref:
        return None
    plein = os.path.abspath(os.path.join(RACINE, str(ref)))
    racine = os.path.abspath(RACINE)
    if not plein.startswith(racine + os.sep):
        return None
    return plein if os.path.exists(plein) else None


def ranger(code_session, categorie, nom, octets, pousser=True):
    """Range un document. Rend (reference, lien, souci).

    `lien` est l'adresse dans le Drive quand la copie a pu partir, "" sinon.
    LE RANGEMENT NE DEPEND PAS DU RESEAU : le fichier est ecrit en local
    d'abord. Perdre un document parce que Google ne repond pas serait le pire
    des comportements — c'est la lecon des justificatifs de veille.
    """
    if categorie not in CATEGORIES:
        return None, "", "Catégorie de document inconnue : %s" % categorie
    if not octets:
        return None, "", "Document vide."

    ref = reference(code_session, categorie, nom)
    plein = os.path.abspath(os.path.join(RACINE, ref))
    os.makedirs(os.path.dirname(plein), exist_ok=True)
    import fichiers
    fichiers.ecrire_octets(plein, octets)

    lien, souci = ("", "")
    if pousser:
        lien, souci = pousser_copie(ref, code_session, categorie, nom, octets)
    return ref, lien, souci


def pousser_copie(ref, code_session, categorie, nom, octets=None):
    """Envoie la copie d'archive dans le Drive. Rend (lien, souci).

    L'IDENTIFIANT DU FICHIER NE CHANGE PAS d'une regeneration a l'autre : on
    remplace le contenu d'un fichier de meme nom plutot que d'en creer un
    second. Un lien deja transmis reste donc valide.

    PLUS AUCUN PARTAGE PUBLIC : verifie le 17/08/2026, aucun modele de mail
    n'envoie ces adresses. Les documents restent lisibles par le compte de
    l'organisme, et par personne d'autre.
    """
    if octets is None:
        p = chemin(ref)
        if not p:
            return "", "Document introuvable en local."
        with open(p, "rb") as f:
            octets = f.read()
    try:
        import dossiers
        import fichiers
        import sessions as _s
        from connexion import service_drive
        from googleapiclient.http import MediaInMemoryUpload

        S = _s.session(code_session)
        cle, nom_hist, suffixe = CATEGORIES[categorie]
        drive = service_drive()
        parent = dossiers.trouver(drive, S, cle, nom_hist)
        if not parent:
            return "", "Dossier « %s » introuvable dans le Drive." % nom_hist
        dossier = dossiers.sous_dossier(drive, parent, S["dossier_session"] + suffixe)

        media = MediaInMemoryUpload(octets, mimetype="application/pdf")
        anciens = drive.files().list(
            q="name='%s' and '%s' in parents and trashed=false"
              % (nom.replace("'", "\\'"), dossier),
            fields="files(id)").execute().get("files", [])
        if anciens:
            f = drive.files().update(fileId=anciens[0]["id"], media_body=media,
                                     fields="id").execute()
            # LES EXEMPLAIRES EN DOUBLE SONT SIGNALES, JAMAIS SUPPRIMES. Une
            # attestation ou une convention est une piece remise a quelqu'un :
            # l'arbitrage revient a l'utilisateur, pas au programme. Ce module
            # ecrit donc a l'ecran, contrairement a l'usage — c'est le seul
            # endroit qui SAIT qu'il y a doublon.
            if len(anciens) > 1:
                print("   ATTENTION : %d autre(s) exemplaire(s) de « %s » dans le "
                      "Drive, laisses en place. A verifier a la main."
                      % (len(anciens) - 1, nom))
        else:
            f = drive.files().create(body={"name": nom, "parents": [dossier]},
                                     media_body=media, fields="id").execute()
        lien = "https://drive.google.com/file/d/%s/view" % f["id"]
        with fichiers.modifier(_INDEX, {}) as idx:
            idx[ref] = {"id": f["id"], "lien": lien}
        return lien, ""
    except Exception as e:
        return "", str(e)[:200]


def lire(ref):
    """Les octets d'un document. None s'il est introuvable.

    Le local d'abord. Le repli sur le Drive existe pour les documents ecrits
    AVANT ce module — ils n'ont pas de copie locale, et leurs liens circulent
    deja dans le suivi.
    """
    p = chemin(ref)
    if p:
        with open(p, "rb") as f:
            return f.read()
    ident = (_index_lire().get(ref) or {}).get("id")
    if not ident:
        return None
    try:
        from connexion import service_drive
        return service_drive().files().get_media(fileId=ident).execute()
    except Exception:
        return None


def lien(ref):
    """L'adresse dans le Drive, ou "" si la copie n'est pas partie."""
    return (_index_lire().get(ref) or {}).get("lien") or ""


def depuis_lien(url):
    """Les octets d'un document designe par une adresse Drive.

    Les scripts decoupaient cette URL pour en extraire l'identifiant, chacun a
    sa facon. Le decoupage vit ici desormais, et nulle part ailleurs.

    L'INDEX SE LIT AUSSI A L'ENVERS, et c'est le point important. Le suivi ne
    garde qu'une URL — vos ecrans s'en servent, les liens deja transmis doivent
    rester valides, il n'etait pas question de la remplacer. Mais un appelant
    qui n'a que cette URL obtient malgre tout LA COPIE LOCALE : on retrouve la
    reference par l'identifiant. Sans reseau, et sans qu'aucun ecran change.
    """
    url = str(url or "")
    if "/d/" not in url:
        return None
    ident = url.split("/d/")[1].split("/")[0]

    for ref, v in _index_lire().items():
        if (v or {}).get("id") == ident:
            p = chemin(ref)
            if p:
                with open(p, "rb") as f:
                    return f.read()
            break  # connu de l'index mais absent du disque : le Drive tranchera
    try:
        from connexion import service_drive
        return service_drive().files().get_media(fileId=ident).execute()
    except Exception:
        return None


# --------------------------------------------------------------------------
# LES PIECES DE REFERENCE
#
# Ce ne sont pas des documents produits par DFM : le programme, le RIB, le plan
# d'acces et le reglement interieur sont DEPOSES par l'utilisateur, et joints
# aux mails. Ils changent rarement et pesent lourd — 6,17 Mo au total le
# 17/08/2026, dont 5,44 pour le seul programme, retelecharges a chaque envoi.
#
# ILS PASSENT PAR CETTE PORTE, et pas par un module a part. C'etait tentant
# d'en ouvrir un second : ces pieces ne sont pas rangees par session, elles
# n'ont pas de categorie, l'appelant ne les cree pas. Mais un second module de
# stockage romprait la promesse de celui-ci — le jour du passage en ligne, UN
# SEUL FICHIER doit changer.
# --------------------------------------------------------------------------

# La cle publique, et le champ de la fiche de session qui porte l'identifiant.
PIECES = {
    "programme": "programme_id",           # par formation
    "rib": "rib_id",                       # par organisme
    "acces": "acces_id",                   # commun (le lieu)
    "reglement": "reglement_interieur_id",  # par organisme
}
_PIECES = os.path.join(RACINE, "_pieces")
_INDEX_PIECES = os.path.join(_PIECES, "_index.json")


def _ident_piece(cle, code_session=None):
    champ = PIECES.get(cle)
    if not champ:
        return ""
    try:
        import sessions as _s
        return str((_s.session(code_session) or {}).get(champ) or "").strip()
    except Exception:
        return ""


def piece(cle, code_session=None):
    """Les octets d'une piece de reference. None si introuvable.

    LA COPIE LOCALE FAIT FOI TANT QU'ELLE EST A JOUR. Pour le savoir, on
    demande au Drive la seule DATE DE MODIFICATION du fichier : environ un Ko
    de reseau, la ou le programme en pese 5 440. C'est le bon echange —
    telecharger a chaque fois coutait cher, ne jamais verifier ferait partir
    un programme perime chez un client.

    SI GOOGLE NE REPOND PAS, la copie locale part quand meme. Un mail sans son
    programme serait pire qu'un programme peut-etre plus tout a fait a jour.

    Le fichier local est nomme d'apres l'IDENTIFIANT Drive, pas d'apres la
    cle : deux formations qui partagent un programme partagent son fichier, et
    reaffecter la piece dans les reglages ne laisse pas l'ancienne repondre.
    """
    ident = _ident_piece(cle, code_session)
    if not ident:
        return None
    return piece_par_ident(ident, cle)


def piece_par_ident(ident, cle=""):
    """La meme chose, pour une piece designee par son SEUL identifiant Drive.

    Les quatre pieces de reference passent par piece(), qui sait les nommer.
    Mais les pieces jointes libres d'une session — « pieces_rappel » — ne sont
    qu'une liste d'identifiants : elles n'avaient donc aucun cache et se
    retelchargeaient a chaque envoi. Le jour ou l'autorisation Google est
    tombee, elles ont cesse de partir, et les convocations avec elles.
    """
    ident = str(ident or "").strip()
    if not ident:
        return None

    # UNE REFERENCE LOCALE PASSE PAR ICI SANS DETOUR. Depuis le 19/08/2026 les
    # champs « programme_id », « rib_id » et les autres peuvent porter soit un
    # identifiant Drive — l'ancien monde — soit une reference locale. Les deux
    # doivent se lire par la meme porte, sinon chaque appelant devrait savoir
    # dans quel monde il se trouve, et l'un d'eux l'oublierait.
    if est_reference(ident):
        chem = chemin(ident)
        if not chem:
            return None
        with open(chem, "rb") as f:
            return f.read()

    local = os.path.join(_PIECES, _sain(ident))

    distant = None
    try:
        from connexion import service_drive
        distant = service_drive().files().get(
            fileId=ident, fields="modifiedTime,size,name").execute()
    except Exception:
        distant = None

    import fichiers
    if os.path.exists(local):
        connu = (fichiers.lire(_INDEX_PIECES, {}) or {}).get(ident) or {}
        if distant is None or connu.get("modifie") == distant.get("modifiedTime"):
            with open(local, "rb") as f:
                return f.read()

    if distant is None:
        return None
    try:
        from connexion import service_drive
        octets = service_drive().files().get_media(fileId=ident).execute()
    except Exception:
        return None
    if not octets:
        return None
    os.makedirs(_PIECES, exist_ok=True)
    fichiers.ecrire_octets(local, octets)
    with fichiers.modifier(_INDEX_PIECES, {}) as x:
        x[ident] = {"cle": cle, "nom": distant.get("name") or "",
                    "modifie": distant.get("modifiedTime") or "",
                    "taille": len(octets)}
    return octets


def fiche_formateur(ref):
    """Ancien nom de fiche_piece(). Conserve : formateurs.py l'appelle."""
    return fiche_piece(ref)


def ecarter_formateur(ref):
    """Ancien nom de ecarter()."""
    return ecarter(ref)


# --------------------------------------------------- les pieces que VOUS posez
#
# Programme, plan d'acces, RIB, reglement interieur, pieces jointes aux
# convocations. Elles partaient jusqu'au 19/08/2026 DIRECTEMENT DANS LE DRIVE,
# par la route /deposer-document — c'est pourquoi neuf d'entre elles n'avaient
# aucune copie ici le jour ou l'autorisation Google est tombee.
#
# DEUX PORTEURS, PARCE QU'IL Y A DEUX PORTEES. Le programme d'une formation vaut
# pour les deux organismes qui la dispensent — la bibliotheque de formations est
# commune. Le RIB, lui, est celui d'UNE entite juridique : les melanger enverrait
# un client payer sur le mauvais compte.

DEPOSES_FORMATION = "_formations"
DEPOSES_ORGANISME = "_organisme"

# Ce qu'on accepte, et ou. La table est fermee : un type inconnu est refuse
# plutot que range n'importe ou.
TYPES_DEPOSES = {
    "programme":   ("formation", "Programme de la formation"),
    "acces":       ("formation", "Plan d'accès et modalités"),
    "convocation": ("formation", "Pièce jointe à la convocation"),
    "rib":         ("organisme", "RIB"),
    "reglement":   ("organisme", "Règlement intérieur"),
}


def reference_depose(type_piece, porteur, nom):
    """« _formations/usures/programme/Programme USURES.pdf »."""
    portee = (TYPES_DEPOSES.get(type_piece) or ("", ""))[0]
    if not portee:
        return None
    if portee == "formation":
        return "/".join((DEPOSES_FORMATION, _sain(porteur), _sain(type_piece), _sain(nom)))
    return "/".join((_sain(porteur), DEPOSES_ORGANISME, _sain(type_piece), _sain(nom)))


def ranger_depose(type_piece, porteur, nom, octets):
    """Ecrit une piece deposee. Rend (reference, souci). Aucun reseau."""
    if type_piece not in TYPES_DEPOSES:
        return None, "Type de document inconnu : %s" % type_piece
    if not str(porteur or "").strip():
        return None, "Document sans propriétaire : on ne saurait pas où le ranger."
    if not octets:
        return None, "Document vide."
    ref = reference_depose(type_piece, porteur, nom)
    plein = os.path.abspath(os.path.join(RACINE, ref))
    if not plein.startswith(os.path.abspath(RACINE) + os.sep):
        return None, "Référence de document invalide."
    os.makedirs(os.path.dirname(plein), exist_ok=True)
    import fichiers
    fichiers.ecrire_octets(plein, octets)
    return ref, ""


def est_reference(x):
    """Une reference locale porte des barres obliques ; un identifiant Drive, non."""
    return "/" in str(x or "")


# ------------------------------------------------ les pieces des formateurs
#
# Elles ne dependent d'AUCUNE SESSION : un CV appartient a une personne, pas a
# une date. Elles ne peuvent donc pas passer par reference(), qui compose son
# adresse a partir du code de session.
#
# ECRIT LE 18/08/2026, le jour ou l'autorisation Google a ete revoquee et ou le
# depot d'un CV est devenu impossible : formateurs.py etait le dernier module
# dont le Drive etait la SEULE voie, pas un miroir.

DOSSIER_FORMATEURS = "_formateurs"


def reference_formateur(ident, nom):
    """« _formateurs/franck-moyal/CV Franck Moyal.pdf ».

    PLUS D'ORGANISME DANS LE CHEMIN depuis le 19/08/2026 : le dossier d'une
    personne est partage entre les organismes pour lesquels elle intervient.
    Un CV ne change pas selon l'entite qui vous emploie.
    """
    return "/".join((DOSSIER_FORMATEURS, _sain(ident), _sain(nom)))


def ranger_formateur(ident, nom, octets):
    """Ecrit une piece de formateur. Rend (reference, souci).

    Aucun reseau, aucun repli : le disque est la seule voie. C'est justement ce
    qui manquait — un CV ne doit pas dependre d'un jeton d'autorisation.
    """
    if not octets:
        return None, "Document vide."
    ref = reference_formateur(ident, nom)
    plein = os.path.abspath(os.path.join(RACINE, ref))
    if not plein.startswith(os.path.abspath(RACINE) + os.sep):
        return None, "Référence de document invalide."
    os.makedirs(os.path.dirname(plein), exist_ok=True)
    import fichiers
    fichiers.ecrire_octets(plein, octets)
    return ref, ""


def ecarter(ref):
    """Deplace une piece dans « _corbeille ». Rend (ok, message).

    ON NE DETRUIT PAS. Le module l'a toujours promis du temps du Drive, ou
    « retirer » voulait dire « mettre a la corbeille, recuperable trente
    jours ». En local, la corbeille est un dossier — et elle n'expire pas.
    """
    p = chemin(ref)
    if not p:
        return False, "Pièce introuvable."
    cible = os.path.abspath(os.path.join(RACINE, "_corbeille", str(ref)))
    os.makedirs(os.path.dirname(cible), exist_ok=True)
    base, ext = os.path.splitext(cible)
    n = 2
    while os.path.exists(cible):          # deux retraits du meme nom
        cible = "%s-%d%s" % (base, n, ext)
        n += 1
    os.replace(p, cible)
    return True, os.path.basename(p)


def fiche_piece(ref):
    """Ce qu'il faut pour afficher une piece : nom, poids, date. None si absente."""
    p = chemin(ref)
    if not p:
        return None
    import datetime
    st = os.stat(p)
    o = float(st.st_size)
    for unite in ("o", "Ko", "Mo"):
        if o < 1024 or unite == "Mo":
            poids = ("%d %s" if unite == "o" else "%.1f %s") % (o, unite)
            break
        o /= 1024
    return {"ref": ref, "nom": os.path.basename(p), "poids": poids,
            "octets": st.st_size,
            "quand": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")}


def vignette(ref, taille=520):
    """Une image PNG de la premiere page d'un document. None si impossible.

    POURQUOI PAS L'APERCU DU NAVIGATEUR. Un <object> PDF dans un cadre de
    120 px n'affiche que le fond sombre de la visionneuse : on voit un rectangle
    noir, pas un CV. Une vraie vignette se regarde a n'importe quelle taille.

    L'OUTIL EST CELUI DE macOS — « qlmanage », le meme qui montre un apercu
    quand on presse Espace dans le Finder. Il n'est donc pas installe partout :
    rendre None est un cas NORMAL, et l'ecran retombe alors sur l'icone du
    format. Une vignette absente ne doit jamais empecher de lire la piece.

    LA VIGNETTE EST MISE EN CACHE a cote des documents, et refaite des que le
    fichier source est plus recent qu'elle.
    """
    p = chemin(ref)
    if not p:
        # UN IDENTIFIANT DRIVE DEJA EN CACHE A LUI AUSSI UN FICHIER SUR LE
        # DISQUE — sous « _pieces », nomme d'apres l'identifiant. Sans cette
        # ligne, l'ecran Documents annoncait « sur cet ordinateur » et proposait
        # un apercu qui rendait 404 : le pire des deux mondes.
        candidat = os.path.join(_PIECES, _sain(str(ref or "")))
        p = candidat if os.path.exists(candidat) else None
    if not p:
        return None
    if os.path.splitext(p)[1].lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        with open(p, "rb") as f:          # une image est deja sa propre vignette
            return f.read()

    cache = os.path.abspath(os.path.join(RACINE, "_vignettes", str(ref) + ".png"))
    if not cache.startswith(os.path.abspath(RACINE) + os.sep):
        return None
    try:
        if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(p):
            with open(cache, "rb") as f:
                return f.read()
    except Exception:
        pass

    import shutil, subprocess, tempfile
    if not shutil.which("qlmanage"):
        return None
    sortie = tempfile.mkdtemp(prefix="dfm-vignette-")
    source = p
    lien = ""
    try:
        # L'EXTENSION EST INDISPENSABLE. Quick Look identifie un fichier par son
        # extension, pas par son contenu : sans elle il ne rend pas la main —
        # constate le 19/08/2026, un qlmanage laisse tourner plus de six minutes
        # sur une piece du cache, qui est nommee d'apres son identifiant Drive.
        # Le delai ci-dessous protegeait DFM, mais aucune vignette ne sortait.
        if not os.path.splitext(p)[1]:
            import fichiers
            connu = (fichiers.lire(_INDEX_PIECES, {}) or {}).get(os.path.basename(p)) or {}
            ext = os.path.splitext(connu.get("nom") or "")[1] or ".pdf"
            lien = os.path.join(sortie, "source" + ext)
            shutil.copyfile(p, lien)
            source = lien
        subprocess.run(["qlmanage", "-t", "-s", str(int(taille)), "-o", sortie, source],
                       capture_output=True, timeout=25)
        # qlmanage nomme sa sortie « <nom du fichier>.png ».
        faits = [os.path.join(sortie, x) for x in os.listdir(sortie)
                 if x.endswith(".png") and os.path.join(sortie, x) != lien]
        if not faits:
            return None
        with open(faits[0], "rb") as f:
            octets = f.read()
    except Exception:
        return None
    finally:
        shutil.rmtree(sortie, ignore_errors=True)
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        import fichiers
        fichiers.ecrire_octets(cache, octets)
    except Exception:
        pass                              # le cache est un confort, pas une condition
    return octets


def nom_piece(ident):
    """Le nom d'origine d'une piece mise en cache, ou "" si on ne l'a pas.

    Les envois nommaient leur piece jointe d'apres le Drive. Le nom est deja
    dans l'index local : le redemander au reseau pour une chaine de caracteres
    faisait dependre une convocation entiere de la disponibilite de Google.
    """
    ident = str(ident or "").strip()
    if est_reference(ident):
        return os.path.basename(ident)
    import fichiers
    return ((fichiers.lire(_INDEX_PIECES, {}) or {}).get(ident) or {}).get("nom") or ""


def pieces_en_cache():
    """Ce qui est deja en local, pour l'inventaire et les sauvegardes."""
    import fichiers
    return fichiers.lire(_INDEX_PIECES, {}) or {}


def en_attente():
    """Les documents ranges en local dont la copie n'est pas partie.

    « _pieces » est ECARTE : ce sont des copies DESCENDANTES du Drive, pas des
    documents produits ici. Sans cette exclusion, chaque piece de reference
    figurerait dans la liste des copies a pousser — et on aurait renvoye au
    Drive ce qui en venait.
    """
    idx = _index_lire()
    manque = []
    for racine, dossiers_, fichiers_ in os.walk(RACINE):
        dossiers_[:] = [d for d in dossiers_ if not d.startswith("_")]
        for n in fichiers_:
            if n.startswith("_") or n.endswith(".verrou"):
                continue
            ref = os.path.relpath(os.path.join(racine, n), RACINE).replace(os.sep, "/")
            if not (idx.get(ref) or {}).get("lien"):
                manque.append(ref)
    return sorted(manque)
