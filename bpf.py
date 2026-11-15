# -*- coding: utf-8 -*-
"""Le bilan pedagogique et financier (BPF) : quand, pour quel exercice, avec
quels chiffres, et les rappels jusqu'au depot.

POURQUOI CE MODULE EXISTE. Tout organisme declare doit deposer chaque annee, sur
Mon Activite Formation, le bilan de son DERNIER EXERCICE COMPTABLE CLOS. Un
bilan oublie, ou qui ne montre aucune formation, rend le numero de declaration
caduc : il faut alors tout redeclarer (art. L. 6351-6 du code du travail).
Franck pilote deux organismes, donc deux bilans, deux echeances. Demande du
15/11/2026, le soir ou LBS FORMATION a envoye sa declaration : « une partie
bilan pedagogique avec rappel par organisme, avec indicateur du temps qu'il
reste ».

L'ECHEANCE. La date reglementaire est le 30 avril (art. R. 6352-23). Le
ministere a prolonge la campagne au 31 mai ces dernieres annees, mais il ne
l'annonce qu'au printemps : tant que la campagne de l'annee n'est pas saisie
ici, DFM compte jusqu'au 30 avril. Mieux vaut un rappel un mois trop tot
qu'un numero perdu.

L'EXERCICE. Il se deduit de deux reglages du profil : la date de cloture
(« 31/12 ») et, si le premier exercice est irregulier, ses bornes. Celui de
LBS court du 30/06/2025 au 31/12/2026, soit dix-huit mois.

LES CHIFFRES SONT UNE AIDE, PAS LE BILAN. DFM ne connait que les sessions
saisies dans DFM, et le chiffre d'affaires comptable reste celui de
l'expert-comptable. La page le dit, et montre ce qu'elle a compte pour qu'on
puisse le verifier ligne a ligne.

LES RAPPELS NE PARTENT QUE DU SERVEUR. Le Mac fait tourner le meme
planificateur : sans cette garde, chaque rappel partirait deux fois. Ils vont a
l'adresse de contact de l'organisme, jamais chez un praticien.
"""
import datetime as dt
import io
import json
import os
import re

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER = os.path.join(DOSSIER, "bpf.json")

# La date reglementaire et l'ouverture habituelle de la campagne, en (mois, jour).
LIMITE_REGLEMENTAIRE = (4, 30)
OUVERTURE_HABITUELLE = (4, 1)

# LE SUIVI COMMENCE LE JOUR DE LA MISE EN SERVICE. Un bilan dont l'echeance est
# anterieure n'est ni compte en retard ni rappele : DFM ignore s'il a ete
# depose, et un « en retard » invente ferait plus de mal que de bien.
SUIVI_DEPUIS = dt.date(2026, 11, 15)

# Les rappels, en jours avant l'echeance. Le premier laisse le temps de
# demander les comptes a l'expert-comptable.
PALIERS = (90, 60, 30, 15, 7, 1)
# Apres l'echeance : trois relances, a une semaine d'intervalle.
RETARDS = (1, 8, 15)

MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

SPECIALITE_DEFAUT = "331 — Santé"


# --------------------------------------------------------------------------
# Lecture et ecriture du registre
# --------------------------------------------------------------------------
def _lire():
    try:
        d = json.load(io.open(FICHIER, encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _modifier():
    import fichiers
    return fichiers.modifier(FICHIER, {})


def _date(valeur):
    """Une date depuis « 30/06/2025 », « 2025-06-30 » ou une date. None sinon."""
    if isinstance(valeur, dt.datetime):
        return valeur.date()
    if isinstance(valeur, dt.date):
        return valeur
    t = str(valeur or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    return None


def texte(d):
    """« 30 avril 2027 », « 1er avril 2027 »."""
    if not d:
        return ""
    return "%s %s %d" % ("1er" if d.day == 1 else d.day, MOIS[d.month], d.year)


def _profil(organisme):
    try:
        import profil
        return profil.charger(organisme) or {}
    except Exception:
        return {}


def serveur():
    """Vrai sur le serveur en ligne : c'est la que tourne le service avec
    DFM_PROXY=1. Les scripts lances a la main l'en retirent (env -u)."""
    return (os.environ.get("DFM_PROXY") or "").strip().lower() in ("1", "oui", "true")


# --------------------------------------------------------------------------
# Les exercices et l'echeance
# --------------------------------------------------------------------------
def _cloture(fiche):
    """(jour, mois) de cloture, et vrai si c'est une supposition."""
    m = re.match(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})", str(fiche.get("exercice_cloture") or ""))
    if m:
        j, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= j <= 31:
            return (j, mo), False
    return (31, 12), True


def _fin_dans(annee, cloture):
    j, mo = cloture
    while True:
        try:
            return dt.date(annee, mo, j)
        except ValueError:
            j -= 1


def exercices(fiche, jusqua=None):
    """Les exercices de l'organisme, du plus ancien au plus recent, jusqu'a
    celui qui contient « jusqua » (aujourd'hui par defaut) et le suivant.

    Rend des couples (debut, fin). Sans premier exercice renseigne, on part
    de 2024 : assez loin pour la page, sans rien inventer d'utile au-dela.
    """
    jusqua = jusqua or dt.date.today()
    cloture, _ = _cloture(fiche)
    p_debut = _date(fiche.get("premier_exercice_debut"))
    p_fin = _date(fiche.get("premier_exercice_fin"))
    liste = []
    if p_debut and p_fin and p_fin > p_debut:
        liste.append((p_debut, p_fin))
        fin = p_fin
    else:
        fin = _fin_dans(2023, cloture)
    borne = jusqua + dt.timedelta(days=400)
    while fin < borne:
        debut = fin + dt.timedelta(days=1)
        nouvelle = _fin_dans(debut.year, cloture)
        if nouvelle < debut:
            nouvelle = _fin_dans(debut.year + 1, cloture)
        liste.append((debut, nouvelle))
        fin = nouvelle
    return liste


def cle(exercice):
    return "%s_%s" % (exercice[0].isoformat(), exercice[1].isoformat())


def depuis_cle(c):
    try:
        a, b = str(c).split("_")
        return (_date(a), _date(b))
    except Exception:
        return None


def libelle(exercice):
    d, f = exercice
    if d.month == 1 and d.day == 1 and f.month == 12 and f.day == 31 and d.year == f.year:
        return "Exercice %d" % d.year
    return "Exercice du %s au %s" % (d.strftime("%d/%m/%Y"), f.strftime("%d/%m/%Y"))


def campagne(annee, registre=None):
    """(ouverture, limite, connue) de la campagne de l'annee donnee."""
    r = (registre if registre is not None else _lire()).get("campagnes", {}).get(str(annee)) or {}
    ouv = _date(r.get("ouverture"))
    lim = _date(r.get("limite"))
    connue = bool(lim)
    return (ouv or dt.date(annee, *OUVERTURE_HABITUELLE),
            lim or dt.date(annee, *LIMITE_REGLEMENTAIRE), connue)


def annee_du_depot(exercice):
    """L'annee ou se depose le bilan : le premier 30 avril qui suit la cloture."""
    fin = exercice[1]
    return fin.year if fin < dt.date(fin.year, *LIMITE_REGLEMENTAIRE) else fin.year + 1


def echeance(exercice, registre=None):
    return campagne(annee_du_depot(exercice), registre)[1]


def cible(fiche, organisme, aujourdhui=None, registre=None):
    """L'exercice dont le bilan est a suivre maintenant : le plus ancien dont
    l'echeance tombe apres la mise en service et qui n'est pas encore depose.
    Si tous sont deposes, le prochain."""
    aujourdhui = aujourdhui or dt.date.today()
    registre = registre if registre is not None else _lire()
    deposes = (registre.get("depots") or {}).get(organisme) or {}
    for ex in exercices(fiche, aujourdhui):
        if echeance(ex, registre) < SUIVI_DEPUIS:
            continue
        if cle(ex) in deposes:
            continue
        return ex
    return None


# --------------------------------------------------------------------------
# L'etat d'un bilan, et ses rappels
# --------------------------------------------------------------------------
def etat(organisme, aujourdhui=None, exercice=None, registre=None):
    """Tout ce que la page, le menu et le tableau de bord affichent."""
    aujourdhui = aujourdhui or dt.date.today()
    registre = registre if registre is not None else _lire()
    fiche = _profil(organisme)
    _, suppose = _cloture(fiche)
    ex = exercice or cible(fiche, organisme, aujourdhui, registre)
    if not ex:
        return None
    ouv, lim, connue = campagne(annee_du_depot(ex), registre)
    depot = ((registre.get("depots") or {}).get(organisme) or {}).get(cle(ex))
    jours = (lim - aujourdhui).days
    if depot:
        e = "depose"
    elif echeance(ex, registre) < SUIVI_DEPUIS:
        e = "historique"
    elif jours < 0:
        e = "retard"
    elif aujourdhui >= ouv:
        e = "ouverte"
    elif ex[1] >= aujourdhui:
        e = "exercice_en_cours"
    else:
        e = "a_preparer"
    return {"organisme": organisme, "exercice": ex, "cle": cle(ex),
            "libelle": libelle(ex), "ouverture": ouv, "limite": lim,
            "campagne_connue": connue, "jours": jours, "etat": e,
            "depot": depot, "cloture_supposee": suppose,
            "limite_texte": texte(lim), "ouverture_texte": texte(ouv),
            "rappels": _plan_rappels(organisme, ex, ouv, lim, aujourdhui, registre)}


def _plan_rappels(organisme, ex, ouv, lim, aujourdhui, registre):
    faits = (((registre.get("rappels") or {}).get(organisme) or {}).get(cle(ex))) or {}
    plan = []
    for n in PALIERS:
        plan.append({"palier": "J-%d" % n, "date": lim - dt.timedelta(days=n)})
    plan.append({"palier": "ouverture", "date": ouv})
    for n in RETARDS:
        plan.append({"palier": "retard+%d" % n, "date": lim + dt.timedelta(days=n)})
    plan.sort(key=lambda p: p["date"])
    for p in plan:
        f = faits.get(p["palier"])
        p["date_texte"] = texte(p["date"])
        if f:
            p["etat"] = "saute" if f.startswith("saute") else "envoye"
            p["le"] = f
        else:
            p["etat"] = "passe" if p["date"] <= aujourdhui else "a_venir"
    return plan


def pastille(organisme, aujourdhui=None):
    """Le petit compteur du menu : « J-166 », sa couleur, et une infobulle."""
    try:
        e = etat(organisme, aujourdhui)
    except Exception:
        return None
    if not e:
        return None
    j = e["jours"]
    if e["etat"] == "depose":
        return {"texte": "✓", "classe": "bj-ok", "titre": "Bilan %s déposé" % e["libelle"].lower()}
    if j < 0:
        return {"texte": "J+%d" % -j, "classe": "bj-ko",
                "titre": "Bilan en retard depuis le %s" % e["limite_texte"]}
    classe = "bj-ko" if j <= 15 else ("bj-att" if j <= 90 else "bj-calme")
    return {"texte": "J-%d" % j, "classe": classe,
            "titre": "Bilan pédagogique et financier à déposer avant le %s" % e["limite_texte"]}


def marquer_depose(organisme, cle_exercice, le=None, note=""):
    le = _date(le) or dt.date.today()
    with _modifier() as r:
        r.setdefault("depots", {}).setdefault(organisme, {})[cle_exercice] = {
            "le": le.isoformat(), "note": (note or "").strip()[:300],
            "saisi_le": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    return le


def annuler_depot(organisme, cle_exercice):
    with _modifier() as r:
        ((r.get("depots") or {}).get(organisme) or {}).pop(cle_exercice, None)


def fixer_campagne(annee, ouverture=None, limite=None):
    o, l = _date(ouverture), _date(limite)
    with _modifier() as r:
        c = r.setdefault("campagnes", {}).setdefault(str(int(annee)), {})
        if o:
            c["ouverture"] = o.isoformat()
        if l:
            c["limite"] = l.isoformat()
    return o, l


def rappels_dus(organisme, aujourdhui=None, registre=None):
    """Le rappel a envoyer aujourd'hui, ou None. UN SEUL : si DFM a ete
    eteint, ou si le suivi commence tard, on n'envoie pas trois mails d'un
    coup — le plus recent dit tout, les precedents sont notes « sautes »."""
    aujourdhui = aujourdhui or dt.date.today()
    e = etat(organisme, aujourdhui, registre=registre)
    if not e or e["etat"] in ("depose", "historique"):
        return None, [], e
    passes = [p for p in e["rappels"] if p["etat"] == "passe"]
    if not passes:
        return None, [], e
    return passes[-1], passes[:-1], e


def _message(e, palier, fiche):
    marque = fiche.get("marque") or fiche.get("organisme") or e["organisme"]
    j = e["jours"]
    if j < 0:
        objet = "Bilan pédagogique et financier — %s : en retard" % marque
        paras = ["Le bilan pédagogique et financier de <b>%s</b> devait être déposé "
                 "avant le <b>%s</b>, et il n'est pas marqué comme déposé dans DFM."
                 % (marque, e["limite_texte"]),
                 "Sans dépôt, le numéro de déclaration d'activité devient caduc : il "
                 "faudrait alors refaire toute la déclaration."]
    elif palier["palier"] == "ouverture":
        objet = "Bilan pédagogique et financier — %s : la campagne est ouverte" % marque
        paras = ["La campagne de dépôt des bilans est ouverte sur Mon Activité Formation.",
                 "Le bilan de <b>%s</b> (%s) est à déposer avant le <b>%s</b>, "
                 "dans %d jours." % (marque, e["libelle"].lower(), e["limite_texte"], j)]
    else:
        objet = "Bilan pédagogique et financier — %s : J-%d" % (marque, j)
        paras = ["Le bilan pédagogique et financier de <b>%s</b> (%s) est à déposer "
                 "sur Mon Activité Formation avant le <b>%s</b> : il reste <b>%d jours</b>."
                 % (marque, e["libelle"].lower(), e["limite_texte"], j)]
        if j >= 60:
            paras.append("C'est le moment de demander à l'expert-comptable les chiffres "
                         "de l'exercice : le bilan doit concorder avec les comptes.")
    if not e["campagne_connue"] and j >= 0:
        paras.append("La date retenue est la date réglementaire du 30 avril. Si le "
                     "ministère prolonge la campagne, elle se change dans DFM.")
    quoi = ("Ouvrir DFM, rubrique « Bilan pédagogique » : les chiffres de l'exercice "
            "y sont prêts à recopier. Une fois le bilan déposé, cliquer « Marquer comme "
            "déposé » arrête les rappels.")
    return objet, paras, quoi


def envoyer_rappels(aujourdhui=None, envoyer=None, forcer=False):
    """Le passage quotidien. Rend la liste de ce qui est parti.

    `envoyer` remplace l'envoi reel (essais). Sans lui, rien ne part ailleurs
    que sur le serveur, sauf `forcer`."""
    if envoyer is None and not (forcer or serveur()):
        return []
    aujourdhui = aujourdhui or dt.date.today()
    try:
        import profil
        organismes = [o["id"] for o in profil.lister()]
    except Exception:
        organismes = []
    partis = []
    for org in organismes:
        try:
            palier, sautes, e = rappels_dus(org, aujourdhui)
        except Exception:
            continue
        if not palier:
            continue
        fiche = _profil(org)
        objet, paras, quoi = _message(e, palier, fiche)
        if envoyer is not None:
            vers = envoyer(org, objet, paras, quoi)
        else:
            import alerte
            vers = alerte.prevenir(
                "bpf-%s-%s-%s" % (org, e["cle"], palier["palier"]), objet, paras,
                organisme=org, heures=24 * 400, quoi_faire=quoi,
                signature="%s|%s" % (e["cle"], palier["palier"]),
                pied="Rappel automatique de DFM : il revient jusqu'au dépôt du bilan, "
                     "puis s'arrête.")
        if not vers:
            continue
        maintenant = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        with _modifier() as r:
            faits = r.setdefault("rappels", {}).setdefault(org, {}).setdefault(e["cle"], {})
            faits[palier["palier"]] = maintenant
            for s in sautes:
                faits.setdefault(s["palier"], "saute le " + maintenant)
        try:
            import journal
            journal.ecrire("Rappel bilan pédagogique envoyé", "",
                           "%s — %s, échéance le %s (%s)" % (
                               fiche.get("marque") or org, e["libelle"],
                               e["limite_texte"], palier["palier"]))
        except Exception:
            pass
        partis.append({"organisme": org, "palier": palier["palier"], "vers": vers})
    return partis


# --------------------------------------------------------------------------
# Les chiffres que DFM connait
# --------------------------------------------------------------------------
def _heures(valeur):
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(valeur or ""))
    return float(m.group(1).replace(",", ".")) if m else 0.0


def _vrai(v):
    return str(v or "").strip().lower() in ("oui", "1", "true", "x", "present", "présent")


def _formateur_cle(nom):
    t = re.sub(r"\b(dr|docteur|pr)\b\.?", " ", str(nom or "").lower())
    mots = sorted(w for w in re.split(r"[^a-zà-ÿ-]+", t) if w)
    return " ".join(mots)


def chiffres(organisme, exercice, aujourdhui=None):
    """Ce que DFM sait de l'exercice : sessions, stagiaires, heures, factures.

    UN STAGIAIRE EST COMPTE quand sa presence est notee ou que son attestation
    lui a ete envoyee. Une session passee dont personne n'est confirme est
    signalee, pas devinee : le bilan doit compter ceux qui ont ete formes,
    pas ceux qui etaient inscrits.
    """
    aujourdhui = aujourdhui or dt.date.today()
    debut, fin = exercice
    import jours as _J
    import sessions as _S
    import suivi as _SV
    lignes_s, alertes = [], []
    formateurs = {}
    par_mode = {"individuel": {"stagiaires": 0, "heures": 0.0},
                "client": {"stagiaires": 0, "heures": 0.0}}
    fonctions = {}
    for code in sorted(_S.SESSIONS):
        if _S.organisme_de(code) != organisme:
            continue
        # La fiche complete d'abord ; la brute si elle ne se compose pas (une
        # formation retiree de la bibliotheque ne doit pas effacer ses heures).
        try:
            S = _S.session(code) or {}
        except Exception:
            S = dict(_S.SESSIONS.get(code) or {})
        try:
            r = _J.resume(S)
        except Exception:
            continue
        tous = [_J._d(j) for j in r.get("jours") or []]
        tous = [j for j in tous if j]
        dedans = [j for j in tous if debut <= j <= fin]
        if not dedans:
            continue
        total_h = _heures(S.get("duree_heures")) or float(r.get("duree") or 0)
        h = total_h * len(dedans) / max(len(tous), 1)
        passee = max(tous) < aujourdhui
        mode = "client" if (S.get("mode") or "") == "client" else "individuel"
        conf = a_conf = prevus = 0
        try:
            lignes = _SV.lire_lignes_de(code)
        except Exception:
            lignes = []
        for l in lignes:
            if (l.get("annule_le") or "").strip():
                continue
            # PRESENT : pointe, ou attestation ENVOYEE. Pas seulement generee :
            # DFM fabrique l'attestation de chaque inscrit, absents compris, et
            # n'envoie qu'aux presents (voir suivi.cocher_present_atteste).
            present = _vrai(l.get("present")) or bool((l.get("attestation_envoyee_le") or "").strip())
            if present:
                conf += 1
                f = (l.get("fonction") or "Non précisée").strip() or "Non précisée"
                fonctions[f] = fonctions.get(f, 0) + 1
            elif passee and ((l.get("signe_le") or "").strip() or mode == "client"):
                a_conf += 1
            elif not passee:
                prevus += 1
        par_mode[mode]["stagiaires"] += conf
        par_mode[mode]["heures"] += conf * h
        nom_f = (S.get("formateur") or "").strip()
        if nom_f:
            k = _formateur_cle(nom_f)
            fo = formateurs.setdefault(k, {"nom": nom_f, "heures": 0.0, "sessions": 0})
            fo["heures"] += h
            fo["sessions"] += 1
        if passee and a_conf:
            alertes.append("%s : %d inscrit%s sans présence notée ni attestation — à vérifier "
                           "avant de reporter les chiffres." % (S.get("titre_complet") or code,
                                                                 a_conf, "s" if a_conf > 1 else ""))
        lignes_s.append({
            "code": code, "titre": S.get("titre_complet") or S.get("nom_formation") or code,
            "dates": r.get("texte") or "", "jours": len(dedans), "jours_total": len(tous),
            "heures": round(h, 1), "mode": mode, "formateur": nom_f,
            "confirmes": conf, "a_confirmer": a_conf, "prevus": prevus,
            "heures_stagiaires": round(conf * h, 1), "passee": passee})
    # LES FACTURES, une fois chacune : le registre garde parfois un numero sous
    # deux cles (« F2026-012 » et « mon-organisme/F2026-012 »).
    vues, factures = set(), []
    try:
        import factures as _F
        for e in _F.tout().values():
            if not isinstance(e, dict) or e.get("organisme") != organisme:
                continue
            d = _date(e.get("date"))
            if not d or not (debut <= d <= fin):
                continue
            k = (e.get("numero") or "", e.get("organisme"))
            if k in vues:
                continue
            vues.add(k)
            try:
                tot = float(e.get("total") or 0)
            except (TypeError, ValueError):
                tot = 0.0
            factures.append({"numero": e.get("numero") or "", "date": d,
                             "client": e.get("client") or "", "session": e.get("session") or "",
                             "type": "client" if e.get("type") == "client" else "individuel",
                             "total": tot})
    except Exception:
        pass
    # LES SESSIONS D'AVANT DFM (15/11/2026, voir pre_dfm.py) : le premier
    # exercice de LBS commence en juin 2025, cinq sessions ont eu lieu hors de
    # DFM. Leurs presents (attestation archivee), leurs heures et leurs factures
    # comptent dans le bilan ; ce qui n'est pas prouve reste en alerte.
    try:
        import pre_dfm as _P
        l2, f2, a2, h2 = _P.pour_bilan(organisme, debut, fin)
    except Exception:
        l2, f2, a2, h2 = [], [], [], 0.0
    for s in l2:
        lignes_s.append(s)
        par_mode["individuel"]["stagiaires"] += s["confirmes"]
        par_mode["individuel"]["heures"] += s["heures_stagiaires"]
    if h2:
        k = _formateur_cle("Dr Franck Moyal")
        fo = formateurs.setdefault(k, {"nom": "Dr Franck Moyal", "heures": 0.0, "sessions": 0})
        fo["heures"] += h2
        fo["sessions"] += len(l2)
    alertes += a2
    factures += f2
    factures.sort(key=lambda x: (x["date"], x["numero"]))
    produits = {"individuel": sum(f["total"] for f in factures if f["type"] == "individuel"),
                "client": sum(f["total"] for f in factures if f["type"] == "client")}
    # LA SOUS-TRAITANCE : un autre organisme de formation qui confie une action
    # a celui-ci (UP CARE pour LBS). Ligne a part du formulaire, et ses
    # stagiaires vont au cadre F-2 : DFM n'en connait pas le nombre.
    try:
        import pre_dfm as _P2
        st = _P2.sous_traitance(organisme, debut, fin)
    except Exception:
        st = []
    produits["sous_traitance"] = round(sum(x["montant"] for x in st), 2)
    if st:
        alertes.append("Sous-traitance : %d prestation%s pour %s (%s €) — le formulaire demande aussi le nombre de "
                       "stagiaires et d'heures de ces actions (cadre F-2), que DFM ne connaît pas."
                       % (len(st), "s" if len(st) > 1 else "", ", ".join(sorted({x["payeur"] for x in st})),
                          ("%.0f" % produits["sous_traitance"])))
    produits["total"] = produits["individuel"] + produits["client"] + produits["sous_traitance"]
    stag = sum(v["stagiaires"] for v in par_mode.values())
    heures_st = sum(v["heures"] for v in par_mode.values())
    fo = sorted(formateurs.values(), key=lambda x: -x["heures"])
    for x in fo:
        x["heures"] = round(x["heures"], 1)
    for v in par_mode.values():
        v["heures"] = round(v["heures"], 1)
    fiche = _profil(organisme)
    return {
        "sessions": lignes_s, "factures": factures, "produits": produits,
        "par_mode": par_mode, "stagiaires": stag, "heures_stagiaires": round(heures_st, 1),
        "formateurs": fo, "heures_formateurs": round(sum(x["heures"] for x in fo), 1),
        "fonctions": sorted(fonctions.items(), key=lambda x: -x[1]),
        "specialite": (fiche.get("specialite_nsf") or "").strip() or SPECIALITE_DEFAUT,
        "alertes": alertes,
    }


def csv_lignes(organisme, exercice, aujourdhui=None):
    """Les chiffres a plat, pour l'expert-comptable ou pour soi."""
    c = chiffres(organisme, exercice, aujourdhui)
    out = [["Rubrique", "Libellé", "Valeur"]]
    e = lambda x: ("%.2f" % x).replace(".", ",")
    out += [["C", "Produits — contrats individuels (praticiens à leurs frais)", e(c["produits"]["individuel"])],
            ["C", "Produits — entreprises (conventions client)", e(c["produits"]["client"])],
            ["C", "Produits — autres organismes de formation (sous-traitance)", e(c["produits"].get("sous_traitance", 0))],
            ["C", "Total des produits connus de DFM sur l'exercice", e(c["produits"]["total"])],
            ["E", "Personnes ayant dispensé des heures de formation", str(len(c["formateurs"]))],
            ["E", "Heures de formation dispensées", e(c["heures_formateurs"])],
            ["F-1", "Stagiaires — inscription individuelle", str(c["par_mode"]["individuel"]["stagiaires"])],
            ["F-1", "Heures-stagiaires — inscription individuelle", e(c["par_mode"]["individuel"]["heures"])],
            ["F-1", "Stagiaires — envoyés par une entreprise", str(c["par_mode"]["client"]["stagiaires"])],
            ["F-1", "Heures-stagiaires — envoyés par une entreprise", e(c["par_mode"]["client"]["heures"])],
            ["F-3", "Autres formations professionnelles — stagiaires", str(c["stagiaires"])],
            ["F-3", "Autres formations professionnelles — heures-stagiaires", e(c["heures_stagiaires"])],
            ["F-4", "Spécialité %s — stagiaires" % c["specialite"], str(c["stagiaires"])],
            ["F-4", "Spécialité %s — heures-stagiaires" % c["specialite"], e(c["heures_stagiaires"])]]
    out.append([])
    out.append(["Session", "Dates", "Heures dans l'exercice", "Stagiaires confirmés",
                "À confirmer", "Heures-stagiaires", "Formateur", "Mode"])
    for s in c["sessions"]:
        out.append([s["titre"], s["dates"], e(s["heures"]), str(s["confirmes"]),
                    str(s["a_confirmer"]), e(s["heures_stagiaires"]), s["formateur"], s["mode"]])
    out.append([])
    out.append(["Facture", "Date", "Client", "Session", "Type", "Montant"])
    for f in c["factures"]:
        out.append([f["numero"], f["date"].strftime("%d/%m/%Y"), f["client"], f["session"],
                    f["type"], e(f["total"])])
    return out
