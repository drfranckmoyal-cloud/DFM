"""Ce qu'une attestation de fin de formation doit porter, pour une personne.

POURQUOI CE MODULE EXISTE. Les attestations etaient des presentations Slides,
UNE PAR FORMATION, dont le titre etait ecrit en dur dans la diapositive : c'est
la seule raison pour laquelle il y en avait plusieurs. Elles portaient quatre
informations — nom, titre, dates, formateur.

L'ARTICLE L.6353-1 EN EXIGE QUATRE AUTRES : les objectifs, la nature de
l'action, sa duree, et les resultats de l'evaluation des acquis. Trois
manquaient. Une attestation incomplete est une non-conformite sur l'indicateur
11, et c'est la piece que le beneficiaire garde le plus longtemps.

LA GRILLE D'EVALUATION VIENT DU MODELE OFFICIEL des DEETS : pour chaque
objectif, les connaissances sont acquises, en cours d'acquisition, ou a
acquerir. DFM calcule deja un score PAR OBJECTIF ; la correspondance est
directe, et c'est ce qui rend cette attestation remplissable sans saisie.
"""
import os
from datetime import date, datetime

_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attestations.json")

# Les six categories de l'article L.6313-1, dans l'ordre du modele officiel.
CATEGORIES = [
    ("adaptation", "Adaptation et développement des compétences"),
    ("promotion", "Promotion"),
    ("prevention", "Prévention"),
    ("conversion", "Conversion"),
    ("connaissances", "Acquisition, entretien ou perfectionnement des connaissances"),
    ("qualification", "Qualification"),
]
# La formation dentaire continue releve de l'entretien et du perfectionnement
# des connaissances. Modifiable par formation le jour ou une autre categorie
# s'imposera ; ecrit ici pour n'avoir a le decider qu'une fois.
NATURE_DEFAUT = "connaissances"


def _organisme(code_session):
    """L'organisme PROPRIETAIRE de la session, jamais le profil actif.

    Meme defaut que celui corrige le 04/08/2026 sur les conventions et les
    factures : une attestation DSF editee pendant que Smileclub est actif
    porterait l'en-tete DSF — `balises_identite` lit la fiche — mais un numero
    pris dans le registre de Smileclub. Deux organismes Qualiopi partageraient
    une numerotation, et chacun aurait un registre a trous.

    Une session orpheline n'est PAS rattachee au profil actif par defaut : elle
    va dans « ? », visible comme telle, plutot que de polluer un vrai registre.
    """
    try:
        import sessions as _S
        return _S.organisme_de(code_session) or "?"
    except Exception:
        return "?"


def _qui(ligne):
    """Le nom sous lequel une inscription est reconnue au registre."""
    return "%s %s" % ((ligne.get("prenom") or "").strip(),
                      (ligne.get("nom") or "").strip().upper())


def numero(code_session, ligne, attribuer=True):
    """« AT2026-001 ». Un numero par attestation, PAR ORGANISME.

    IL NE CHANGE JAMAIS. Regenerer une attestation — parce qu'un score a ete
    corrige, parce qu'un nom etait mal orthographie — remplace le contenu du
    PDF sans changer son identifiant Drive : le lien deja transmis reste
    valide. Le numero doit se comporter pareil, sinon deux exemplaires du meme
    document circulent sous deux numeros, et le registre ne prouve plus rien.

    LA CLE EST LA LIGNE DU SUIVI, PAS LE MAIL. Deux inscrits peuvent partager
    une adresse : un praticien qui inscrit son assistante depuis la boite du
    cabinet, par exemple. Constate le 06/08/2026 sur usures-nov26, ou deux
    personnes ont recu le meme numero. Aucun code de DFM ne supprime de ligne
    dans un onglet de suivi : le rang y est donc un identifiant stable.

    LE NOM SERT DE GARDE-FOU. Si quelqu'un supprime une ligne A LA MAIN dans le
    Sheet, les rangs suivants remontent, et le rang d'une personne designerait
    alors quelqu'un d'autre. On verifie que le nom enregistre est bien celui
    attendu ; s'il ne l'est pas, on attribue un numero neuf plutot que de
    reutiliser celui d'un tiers.

    L'attribution passe par `fichiers.modifier`, qui pose un verrou : deux
    generations lancees en meme temps ne peuvent pas prendre le meme numero.

    `attribuer=False` pour lire sans consommer un numero — un apercu ne doit
    pas creer d'entree au registre.
    """
    import fichiers
    ident = _organisme(code_session)
    cle = "%s|%s" % ((code_session or "").strip().lower(), ligne.get("_numero"))
    qui = _qui(ligne)
    annee = date.today().year
    prefixe = "AT%d-" % annee

    if not attribuer:
        fiche = ((fichiers.lire(_FICHIER, {}) or {}).get(ident) or {}).get(cle) or {}
        return fiche.get("numero", "") if fiche.get("qui") == qui else ""

    with fichiers.modifier(_FICHIER, {}) as registre:
        fiches = registre.setdefault(ident, {})
        connue = fiches.get(cle) or {}
        if connue.get("numero") and connue.get("qui") == qui:
            return connue["numero"]
        suite = 0
        for f in fiches.values():
            n = str((f or {}).get("numero") or "")
            if n.startswith(prefixe):
                try:
                    suite = max(suite, int(n.split("-")[-1]))
                except ValueError:
                    pass
        if connue.get("numero"):
            # Le rang a change d'occupant. L'ancienne entree est DEPLACEE, pas
            # ecrasee : le numero qu'elle porte figure sur un document deja
            # emis, et un registre qui perd un numero ne prouve plus rien. La
            # cle d'archive contient un « # », que la cle de recherche ne peut
            # pas contenir : elle ne sera plus jamais retrouvee ni reutilisee.
            fiches["%s#%s" % (cle, connue["numero"])] = dict(connue, rang_repris=True)
        attribue = "%s%03d" % (prefixe, suite + 1)
        fiches[cle] = {"numero": attribue, "session": code_session, "qui": qui,
                       "mail": (ligne.get("mail") or "").strip(),
                       "emis_le": date.today().isoformat()}
        return attribue


def registre(ident=None):
    """Le registre d'un organisme, du plus recent au plus ancien.

    Sans argument : celui du profil actif — c'est un ECRAN qui appelle, et un
    ecran montre ce que l'utilisateur consulte. L'attribution, elle, ne s'y fie
    jamais : elle suit le proprietaire de la session.
    """
    import fichiers
    if not ident:
        try:
            import profil
            ident = profil.actif()
        except Exception:
            ident = ""
    d = fichiers.lire(_FICHIER, {}) or {}
    fiches = list((d.get(ident) or {}).values())
    return sorted(fiches, key=lambda f: f.get("numero") or "", reverse=True)


def _etat(score, seuil):
    """acquis / en_cours / a_acquerir, depuis un score par objectif.

    Le seuil est celui du questionnaire, pas une valeur inventee ici. En
    dessous de la moitie du seuil, on ne peut pas parler d'acquisition en
    cours : ce serait flatter un resultat sur un document contractuel.
    """
    if score is None:
        return ""
    if score >= seuil:
        return "acquis"
    return "en_cours" if score >= seuil / 2.0 else "a_acquerir"


def _logo(S):
    """Le logo, en dernier recours — celui de l'organisme DE LA SESSION.

    generer_attestations telecharge le logo UNE FOIS pour toute la session et
    le passe a pour() ; ce chemin ne sert donc qu'a un appel direct sans logo.
    Il lit malgre tout profil.logo() et non le « logo_id » du Sheet : ce champ
    ne connait pas les organismes, et une attestation Smileclub portant le logo
    DSF serait un faux document.
    """
    try:
        import pdf as _pdf
        import profil
        import sessions as _s
        octets = profil.logo(_s.organisme_de(S.get("code")))
        return _pdf.image_en_ligne(octets, "image/png") if octets else ""
    except Exception:
        return ""


def pour(code_session, ligne, logo=None, attribuer=True):
    """Le dossier complet d'une attestation, prêt pour le gabarit.

    `ligne` est la ligne de suivi de la personne. `logo` se passe d'un appel a
    l'autre pour ne pas retelecharger l'image a chaque attestation.
    `attribuer=False` pour un apercu : aucun numero n'est consomme.
    """
    import jours as _J
    import questionnaires as _Q
    import sessions as _S

    S = _S.session(code_session)
    ident = _S.balises_identite(S)

    def b(cle):
        return (ident.get("{{%s}}" % cle) or "").strip()

    j = _J.resume(S)
    nom = ((ligne.get("prenom") or "") + " " + (ligne.get("nom") or "").upper()).strip()

    # La civilite suit la FONCTION declaree : « Dr » devant une assistante
    # dentaire ou un comptable serait faux, et l'ancien modele l'ecrivait en dur.
    fonction = (ligne.get("fonction") or "").strip()
    # UNE FONCTION VIDE NE DONNE PLUS « Dr ». Le vide etait traite comme un
    # chirurgien-dentiste : un etudiant ou une assistante dont la fonction
    # manquait recevait une attestation au nom du « Dr Untel ». Corrige le
    # 22/08/2026 — dans le doute, pas de titre.
    civilite = "Dr" if fonction == "Chirurgien-dentiste" else ""

    modele = None
    try:
        modele = _Q.modele_session(code_session, S.get("formation") or "", "evaluation")
    except Exception:
        modele = None
    seuil = (modele or {}).get("seuil") or _Q.seuil_defaut()

    resultats, score_fin, score_init = {}, None, None
    try:
        import preuve as _preuve
        for enr in _preuve._reponses_supabase(code_session, ligne.get("mail") or ""):
            if not modele:
                break
            r = _Q.corriger_avec(modele, enr.get("reponses") or {})
            if enr.get("type") == "fin":
                resultats, score_fin = r.get("par_objectif") or {}, r.get("score")
            elif enr.get("type") == "init":
                score_init = r.get("score")
    except Exception:
        pass

    libelles = (modele or {}).get("objectifs") or {}
    objectifs = []
    if libelles:
        for cle in sorted(libelles):
            s = resultats.get(cle)
            objectifs.append({"cle": cle, "libelle": libelles[cle], "score": s,
                              "etat": _etat(s, seuil)})
    else:
        # Formation sans modele de questionnaire : on reprend les objectifs
        # declares sur la fiche, sans etat — mieux vaut les mentionner sans
        # resultat que de taire l'exigence legale.
        for o in (S.get("objectifs") or []):
            objectifs.append({"cle": "", "libelle": o, "score": None, "etat": ""})

    return {
        "nom_prenom": nom, "civilite": civilite, "fonction": fonction,
        "numero": numero(code_session, ligne, attribuer),
        "marque": b("marque") or b("organisme"),
        "organisme": b("organisme"), "adresse_organisme": b("adresse_organisme"),
        "siret": b("siret"), "numero_declaration": b("numero_declaration"),
        "mail_contact": b("mail_contact"), "telephone": b("telephone"),
        "formateur": b("formateur"),
        "qualite_signataire": "Responsable pédagogique",
        "ville_of": (S.get("ville") or "").strip() or _ville(b("adresse_organisme")),
        "logo": logo if logo is not None else _logo(S),
        "signature": "",
        "titre_formation": S.get("titre_complet") or S.get("nom_formation") or "",
        "public": (S.get("public") or "").strip(),
        "lieu": (S.get("adresse") or "").strip(),
        "dates": j["texte"], "jours": j["detail"], "nb_jours": j["nb"],
        "date_debut": _fr(j["date_debut"]), "date_fin": _fr(j["date_fin"]),
        "duree": "%s heures" % j["duree"],
        "categories": CATEGORIES,
        "nature": (S.get("nature_action") or NATURE_DEFAUT).strip(),
        "objectifs": objectifs, "seuil": seuil,
        "score_fin": score_fin, "score_init": score_init,
        "progression": (score_fin - score_init)
                       if (score_fin is not None and score_init is not None) else None,
        "date_du_jour": datetime.now().strftime("%d/%m/%Y"),
    }


def _fr(iso):
    import jours as _J
    d = _J._d(iso)
    return d.strftime("%d/%m/%Y") if d else ""


def _ville(adresse):
    """« 12 rue des Lilas, 75011 Paris » -> « Paris ». Le lieu de signature
    d'un acte est une ville, pas une adresse complete."""
    bout = (adresse or "").split(",")[-1].strip()
    morceaux = [m for m in bout.split() if not m.isdigit()]
    return " ".join(morceaux) or bout


def html(donnees):
    """Le document, rendu par le gabarit de DFM."""
    from flask import render_template
    import app as _app
    with _app.app.app_context():
        return render_template("attestation.html", a=donnees)


def fabriquer(code_session, ligne, logo=None, attribuer=True):
    """Les octets du PDF, prets a etre deposes ou envoyes."""
    import pdf as _pdf
    return _pdf.depuis_html(html(pour(code_session, ligne, logo, attribuer)))
