"""Le dossier d'un apprenant, tel qu'on le presente en controle.

CE QUE DFM SAVAIT DEJA FAIRE. La route /session/<code>/recap/<mail> restitue
question par question l'evaluation des acquis : l'enonce, ce que la personne a
repondu a l'entree et en sortie, la bonne reponse, l'explication. C'est une
piece solide, et ce module ne la refait pas — il y renvoie.

CE QUI MANQUAIT VRAIMENT, et que ce module ajoute :

1. La SATISFACTION et l'evaluation A FROID n'etaient lisibles qu'en moyennes.
   Les notes d'une personne, ses commentaires libres, et surtout sa reponse a
   « Aviez-vous un besoin particulier d'adaptation ? » n'apparaissaient nulle
   part. Cette derniere est l'indicateur 26 : collecter la demande sans jamais
   pouvoir montrer la reponse, c'est le pire des deux mondes.

2. Le recap exige une evaluation de SORTIE : sans elle il rend 404. Quelqu'un
   qui n'a repondu qu'a l'entree n'avait aucune restitution.

3. Rien ne rassemblait le parcours : convention, reglement, evaluations,
   attestation. En controle on demande le dossier d'une personne, pas un ecran
   par piece.

4. Rien ne disait CE QUI MANQUE. Un dossier incomplet doit se voir avant le
   controle, pas pendant.

CE MODULE NE FABRIQUE RIEN ET N'ECRIT RIEN. Il assemble des pieces existantes :
le modele REELLEMENT utilise pour la session — l'instantane fige, pas celui
d'aujourd'hui —, les reponses telles qu'elles sont arrivees, les liens vers les
documents deja produits.
"""


def _cle(mail):
    return (mail or "").strip().lower()


def _reponses_supabase(code_session, mail):
    """Les questionnaires remplis par cette personne pour cette session.

    Deux colonnes designent la session dans cette table : « session_code »,
    d'origine et renseignee, et « session », ajoutee ensuite et restee vide. On
    accepte les deux. Un enregistrement sans aucune des deux est retenu : il
    date d'avant le rattachement et vaut mieux qu'un trou dans le dossier.
    """
    import config
    from supabase import create_client
    try:
        sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        r = sb.table("Questionnaires").select("*").eq("mail", _cle(mail)).execute()
        recus = r.data or []
    except Exception:
        return []
    sortie = []
    for x in recus:
        sien = (x.get("session_code") or x.get("session") or "").strip()
        if sien and sien != code_session:
            continue
        sortie.append(x)
    return sorted(sortie, key=lambda x: str(x.get("created_at") or ""))


_INTITULES = {
    "init": ("Évaluation des acquis — à l'entrée", "evaluation"),
    "fin": ("Évaluation des acquis — en sortie", "evaluation"),
    "satisfaction": ("Questionnaire de satisfaction", "satisfaction"),
    "froid": ("Évaluation à froid — trois mois après", "froid"),
}


def _texte_choix(propositions, donnee):
    """Le libelle derriere un indice. Les reponses arrivent parfois en « 0 »."""
    try:
        return (propositions or [])[int(donnee)]
    except (TypeError, ValueError, IndexError):
        return "" if donnee in (None, "") else str(donnee)


def _piece_appreciation(modele, reponses, quoi):
    """Satisfaction et evaluation a froid : notes, recommandation, texte libre.

    Ces modeles n'ont pas de « bonne reponse » — rien a corriger, tout a
    restituer. C'est precisement ce qui n'existait pas.
    """
    axes = modele.get("axes") or {}
    notes = []
    for n in modele.get("notes") or []:
        v = reponses.get(n["id"])
        notes.append({"libelle": n.get("libelle") or "",
                      "axe": axes.get(n.get("axe"), n.get("axe") or ""),
                      "note": v if isinstance(v, (int, float)) else None,
                      "sans_reponse": v in (None, "")})
    reco = None
    r = modele.get("recommandation")
    if r:
        v = reponses.get(r["id"])
        reco = {"libelle": r.get("libelle") or "",
                "note": v if isinstance(v, (int, float)) else None,
                "sans_reponse": v in (None, "")}
    adaptation = None
    a = modele.get("adaptation")
    if a:
        v = reponses.get(a["id"])
        adaptation = {"libelle": a.get("libelle") or "",
                      "repondu": _texte_choix(a.get("propositions"), v),
                      "sans_reponse": v in (None, "")}
    ouvertes = []
    for o in modele.get("ouvertes") or []:
        v = reponses.get(o["id"])
        ouvertes.append({"libelle": o.get("libelle") or "",
                         "repondu": str(v or "").strip(),
                         "sans_reponse": not str(v or "").strip()})
    moyennes = [n["note"] for n in notes if n["note"] is not None]
    return {"notes": notes, "recommandation": reco, "adaptation": adaptation,
            "ouvertes": ouvertes,
            "moyenne": round(sum(moyennes) / len(moyennes), 1) if moyennes else None,
            "sur": 5}


class LectureRatee(Exception):
    """Le suivi n'a pas pu etre lu — reseau, quota, jeton.

    POURQUOI CETTE EXCEPTION EXISTE. L'echec de lecture etait avale : `lignes`
    tombait a vide, personne n'y etait trouve, et l'ecran annoncait « cette
    personne n'est pas inscrite sur cette session ». Constate le 06/08/2026, un
    appel sur deux. Un faux diagnostic coute plus cher qu'une erreur affichee :
    on cherche la personne dans le Sheet au lieu de reessayer.
    """


def _lignes(code_session):
    import suivi as _su
    try:
        return _su.lire_lignes_de(code_session)
    except Exception as e:
        raise LectureRatee(str(e))


def formulaire(code_session, mail, type_):
    """UN questionnaire, tel qu'une personne l'a rempli. Question par question.

    POURQUOI CETTE FONCTION EXISTE. Le dossier de preuves montrait le SCORE de
    l'evaluation, pas les reponses. Le detail n'existait que sur le recapitulatif
    pedagogique, qui melange l'entree et la sortie et refuse de s'afficher tant
    que l'evaluation de sortie manque. Devant un auditeur qui demande a voir le
    questionnaire d'un apprenant, il n'y avait rien a ouvrir.

    Rend None si la personne n'a pas rempli ce questionnaire : on ne fabrique
    pas une page vide qui laisserait croire a une piece existante.
    """
    import sessions as _s
    import questionnaires as _q

    try:
        S = _s.session(code_session) or {}
    except Exception:
        return None
    if not S:
        return None
    ligne = next((l for l in _lignes(code_session)
                  if _cle(l.get("mail")) == _cle(mail)), None)
    if ligne is None:
        return None

    enr = next((e for e in _reponses_supabase(code_session, mail)
                if (e.get("type") or "").strip() == type_), None)
    if enr is None:
        return None

    reponses = enr.get("reponses") or {}
    if isinstance(reponses, str):
        import json as _j
        try:
            reponses = _j.loads(reponses)
        except Exception:
            reponses = {}

    libelle, quoi = _INTITULES.get(type_, (type_ or "Questionnaire", "evaluation"))
    try:
        modele = _q.modele_session(code_session, S.get("formation") or "", quoi)
    except Exception:
        modele = None

    base = {"session": S, "code": code_session, "type": type_, "quoi": quoi,
            "libelle": libelle, "modele_titre": (modele or {}).get("titre") or "",
            "nom": ((ligne.get("prenom") or "") + " " + (ligne.get("nom") or "")).strip()
                   or ligne.get("mail") or "Sans nom",
            "mail": ligne.get("mail") or mail,
            "fonction": ligne.get("fonction") or "",
            "quand": _s.date_fr(enr.get("created_at") or ""),
            "fige": bool(_q.fige(code_session)),
            "questions": [], "appreciation": None, "brut": None,
            "score": None, "obtenu": None, "total": None, "seuil": None}

    if not modele:
        # Sans modele on ignore ce qui a ete demande. On restitue les reponses
        # telles quelles : illisible vaut mieux qu'absent pour une preuve.
        base["brut"] = reponses
        return base

    if quoi != "evaluation":
        base["appreciation"] = _piece_appreciation(modele, reponses, quoi)
        return base

    resultat = None
    try:
        resultat = _q.corriger_avec(modele, reponses)
    except Exception:
        resultat = None
    juste_par_id = {d.get("id"): d.get("juste")
                    for d in ((resultat or {}).get("detail") or [])}
    base["seuil"] = modele.get("seuil")
    if resultat:
        base.update({"score": resultat.get("score"), "obtenu": resultat.get("obtenu"),
                     "total": resultat.get("total"),
                     "par_objectif": resultat.get("par_objectif") or {},
                     "objectifs": modele.get("objectifs") or {}})

    for rang, q in enumerate(modele.get("questions") or [], 1):
        donnee = reponses.get(q["id"])
        try:
            choisi = int(donnee)
        except (TypeError, ValueError):
            choisi = None
        attendu = q.get("reponse")
        props = q.get("propositions") or []
        base["questions"].append({
            "rang": rang, "id": q["id"], "objectif": q.get("objectif") or "",
            "enonce": q.get("enonce") or "", "poids": q.get("poids", 1),
            "explication": q.get("explication") or "",
            "juste": juste_par_id.get(q["id"]),
            "sans_reponse": choisi is None,
            "propositions": [
                {"texte": t, "cochee": (i == choisi), "attendue": (i == attendu)}
                for i, t in enumerate(props)],
        })
    return base


def dossier(code_session, mail):
    """Tout ce qui prouve le parcours d'une personne sur une session.

    Rend None si la personne n'est pas inscrite sur cette session : on ne
    fabrique pas de dossier pour quelqu'un qui n'y figure pas.
    """
    import sessions as _s
    import questionnaires as _q

    try:
        S = _s.session(code_session) or {}
    except Exception:
        return None
    if not S:
        return None
    ligne = next((l for l in _lignes(code_session)
                  if _cle(l.get("mail")) == _cle(mail)), None)
    if ligne is None:
        return None

    formation = S.get("formation") or ""
    pieces = []
    for enr in _reponses_supabase(code_session, mail):
        type_ = (enr.get("type") or "").strip()
        libelle, quoi = _INTITULES.get(type_, (type_ or "Questionnaire", "evaluation"))
        reponses = enr.get("reponses") or {}
        if isinstance(reponses, str):
            import json as _j
            try:
                reponses = _j.loads(reponses)
            except Exception:
                reponses = {}
        try:
            modele = _q.modele_session(code_session, formation, quoi)
        except Exception:
            modele = None

        piece = {"type": type_, "libelle": libelle, "quoi": quoi,
                 # LE QUESTIONNAIRE REMPLI, consultable tel quel. Un auditeur
                 # qui demande a voir les reponses d'un apprenant doit avoir un
                 # lien a ouvrir, pas un score a croire.
                 "lien": "/session/%s/questionnaire/%s/%s" % (
                     code_session, ligne.get("mail") or mail, type_),
                 # Supabase horodate en ISO. Partout ailleurs DFM affiche des
                 # dates francaises ; un dossier presente en controle ne peut
                 # pas etre le seul ecran a parler une autre langue.
                 "quand": _s.date_fr(enr.get("created_at") or ""),
                 "modele_titre": (modele or {}).get("titre") or "",
                 "score": enr.get("score"), "detail": None,
                 # Sans modele on ne sait pas ce qui a ete demande. On garde les
                 # reponses brutes plutot que de les taire : illisible vaut
                 # mieux qu'absent quand il s'agit d'une preuve.
                 "brut": None}
        if not modele:
            piece["brut"] = reponses
        elif quoi == "evaluation":
            # L'evaluation des acquis a deja son ecran detaille, concu pour etre
            # remis au praticien. On n'en refait pas une seconde version : on
            # resume et on renvoie dessus.
            resultat = None
            try:
                resultat = _q.corriger_avec(modele, reponses)
            except Exception:
                resultat = None
            if resultat:
                piece["score"] = resultat.get("score")
                piece["detail"] = {
                    "obtenu": resultat.get("obtenu"), "total": resultat.get("total"),
                    "par_objectif": resultat.get("par_objectif") or {},
                    "objectifs": modele.get("objectifs") or {},
                    "questions": len(modele.get("questions") or []),
                    "justes": len([d for d in (resultat.get("detail") or []) if d.get("juste")]),
                }
            else:
                piece["brut"] = reponses
        else:
            piece["detail"] = _piece_appreciation(modele, reponses, quoi)
        pieces.append(piece)

    a = {t: any(p["type"] == t for p in pieces) for t in ("init", "fin", "satisfaction", "froid")}

    documents = []
    for cle_lien, cle_date, quoi in (
            ("lien_pdf", "signe_le", "Convention signée"),
            ("lien_facture", "facture_le", "Facture"),
            ("lien_attestation", "attestation_le", "Attestation de formation")):
        if (ligne.get(cle_lien) or "").strip():
            documents.append({"quoi": quoi, "quand": (ligne.get(cle_date) or "")[:10],
                              "lien": ligne[cle_lien]})

    manques = []
    if not (ligne.get("lien_pdf") or "").strip():
        manques.append("Convention signée")
    if not a["init"]:
        manques.append("Évaluation d'entrée")
    if not a["fin"]:
        manques.append("Évaluation de sortie")
    if not a["satisfaction"]:
        manques.append("Questionnaire de satisfaction")
    if not (ligne.get("lien_attestation") or "").strip():
        manques.append("Attestation")

    nom = ((ligne.get("prenom") or "") + " " + (ligne.get("nom") or "")).strip()
    return {
        "session": S, "code": code_session, "ligne": ligne,
        "nom": nom or ligne.get("mail") or "Sans nom",
        "mail": ligne.get("mail") or mail,
        "fonction": ligne.get("fonction") or "",
        "pieces": pieces, "documents": documents, "manques": manques,
        # Le recap detaille n'existe qu'avec une evaluation de sortie : y
        # renvoyer sans elle menerait a une page 404.
        "recap": ("/session/%s/recap/%s" % (code_session, ligne.get("mail") or mail))
                 if a["fin"] else "",
        "fige": bool(_q.fige(code_session)),
    }
