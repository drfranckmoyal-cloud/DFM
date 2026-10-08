from flask import Flask, render_template, redirect, url_for, request, jsonify, session as _session
from sessions import FORMATIONS, SESSIONS, SESSION_ACTIVE, COMMUN as COMMUN_TPL, session as fiche_session, sessions_de
from datetime import date
import subprocess
import sys
import os
import donnees
import journal
app = Flask(__name__)

# LES GABARITS SE RELISENT A CHAQUE AFFICHAGE.
#
# Sans cela, Flask les charge une fois au demarrage et n'y revient jamais :
# DFM tournant en permanence, une correction d'ecran restait invisible pendant
# des jours. Constate deux fois de suite les 14 et 16/08/2026 — un serveur
# lance le vendredi servait encore, le dimanche, des pages d'avant les
# modifications, et rien a l'ecran ne le laissait deviner.
#
# CE QUE CELA COUTE : une verification de date de fichier par affichage. Sur
# une application locale a un seul utilisateur, c'est indetectable.
#
# CE QUE CELA NE FAIT PAS : recharger le code Python. Une modification de .py
# demande toujours un redemarrage.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

DOSSIER = os.path.dirname(os.path.abspath(__file__))
MOIS_COURT = ["", "jan", "fév", "mar", "avr", "mai", "juin",
              "juil", "août", "sep", "oct", "nov", "déc"]
_SYMBOLES = {"EUR": "€", "CHF": "CHF", "CAD": "$"}
@app.template_filter("euros")
def f_euros(v):
    """Le symbole suit le reglage Devise (C4 : il n'etait lu par personne)."""
    try:
        import parametres as _P
        symbole = _SYMBOLES.get(str(_P.valeur("devise") or "EUR"), "€")
    except Exception:
        symbole = "€"
    try:
        return f"{float(v):,.0f}".replace(",", " ") + " " + symbole
    except (TypeError, ValueError):
        return "—"
@app.template_filter("jour")
def f_jour(d):
    try:
        return f"{d.day} {MOIS_COURT[d.month]} {d.year}"
    except Exception:
        return str(d)
@app.context_processor
def commun():
    try:
        import parametres as _P
        sombre_defaut = bool(_P.valeur("mode_sombre"))
    except Exception:
        sombre_defaut = False
    return {
        # Le compteur de la barre suit le CLOISONNEMENT, comme les ecrans :
        # il annoncait le total des deux organismes, donc 3 sous DSF qui n'en
        # a qu'une. Un chiffre qu'on ne retrouve nulle part en cliquant.
        "nb_sessions": len(__import__("sessions").visibles()),
        "nb_formations": len(FORMATIONS),
        "aujourdhui": date.today(),
        "mois_court": MOIS_COURT,
        # Defaut du reglage ; le choix fait sur CET appareil reste prioritaire.
        "sombre_defaut": sombre_defaut,
        # Les quatre veilles du critere 6, en sous-menu. La pastille porte le
        # numero de l'indicateur et sa couleur dit s'il tient debout : c'est le
        # seul endroit de DFM ou l'on voit ces quatre-la sans les chercher.
        "nav_veilles": _nav_veilles(),
    }
def _nav_veilles():
    """Le sous-menu des veilles. Ne doit JAMAIS faire echouer un rendu : il
    s'affiche sur toutes les pages, y compris celles qui n'ont rien a voir."""
    try:
        import veille as _v
        sortie = []
        for e in _v.tableau():
            a = e["axe"]
            sortie.append({"cle": a["cle"], "indicateur": a["indicateur"],
                           "icone": a["icone"], "solide": e["solide"],
                           "court": a["court"]})
        return sortie
    except Exception:
        return []
from sessions import Inconnue as _Inconnue
# L'ETAT DE VIE DES SESSIONS passe par le module, pas par l'onglet Google :
# sessions.etat(code) et sessions.poser_etat(s). Une vingtaine de routes
# lisaient deux cents lignes de l'onglet pour retrouver une ligne par son code.
import sessions as SESSIONS_MOD
import courrier
@app.errorhandler(_Inconnue)
def _erreur_inconnue(e):
    """Une fiche disparue ne doit pas couper l'ecran entier (B5)."""
    return render_template("erreur.html", message=str(e)), 404
@app.route("/")
def tableau_de_bord():
    g = donnees.global_kpi()
    prochaine = None
    for s in g["en_cours"]:
        if prochaine is None or s["jours_avant"] < prochaine["jours_avant"]:
            prochaine = s
    # Les seules valeurs NUMERIQUES : le dictionnaire porte aussi les listes de
    # noms depuis le 05/08/2026, et les additionner leve une erreur.
    total_alertes = sum(v for v in g["alertes"].values() if isinstance(v, int))
    fiches = []
    for code, f in FORMATIONS.items():
        sess = [s for s in g["sessions"] if s["session"]["code_formation"] == code]
        fiches.append({"code": code, "formation": f, "sessions": sess,
                       "nb_sessions": len(sess),
                       "total_inscrits": sum(len(s["actifs"]) for s in sess)})
    recents = []
    for s in g["sessions"]:
        for l in s["lignes"]:
            l["_formation"] = s["session"]["nom_formation"]
            l["_dates"] = s["debut"].strftime("%d/%m/%Y")
            recents.append(l)
    recents.sort(key=lambda l: l["horodateur"], reverse=True)
    courbes = donnees.courbes_formations(g["sessions"])
    return render_template("dashboard.html", g=g, prochaine=prochaine,
                           total_alertes=total_alertes, fiches=fiches,
                           recents=recents[:8], courbes=courbes,
                           activite=[dict(e, style=journal.style(e["type_action"])) for e in g["journal"][:7]],
                           journal_souci=g.get("journal_souci") or "")
@app.route("/formations")
def liste_formations():
    g = donnees.global_kpi()
    fiches = []
    for code, f in FORMATIONS.items():
        sess = [s for s in g["sessions"] if s["session"]["code_formation"] == code]
        docs = {
            "programme": f.get("programme_id"),
            "acces": f.get("acces_id"),
        }
        # Qui est designe pour la delivrer, dans l'organisme ACTIF. Une
        # formation sans formateur est un trou dans l'indicateur 21 : rien ne
        # prouve la competence de quiconque pour l'animer.
        try:
            import formateurs as _fo
            designes = [x["nom_complet"] for x in _fo.pour_formation(code)]
        except Exception:
            designes = []
        fiches.append({
            "formateurs": designes,
            "code": code, "f": f, "sessions": sess,
            "nb_sessions": len(sess),
            "en_cours": len([s for s in sess if not s["passee"]]),
            "total_inscrits": sum(len(s["actifs"]) for s in sess),
            "ca": sum(s["encaisse"] for s in sess),
            "signees": sum(s["signees"] for s in sess),
            "docs": docs,
            "docs_ok": len([v for v in docs.values() if v]),
            "docs_total": len(docs),
        })
    return render_template("formations.html", fiches=fiches)
@app.route("/documents")
def page_documents():
    """Tout ce que DFM detient, en un seul endroit.

    Les depots contextuels RESTENT — on pose le programme d'une formation depuis
    sa fiche, c'est le geste naturel. Cet ecran est celui ou l'on REGARDE : ce
    qui manque, ce qui est perime, ce qui n'est pas encore descendu du Drive.
    """
    import bibliotheque as _b
    inv = _b.inventaire()
    return render_template("documents.html", inv=inv, resume=_b.resume(inv))


def _ref_permise(ref):
    """Un document lisible depuis cet ecran : le sien, ou celui d'une formation.

    Les formations sont communes aux organismes ; le reste ne l'est pas. Sans ce
    controle, une reference etant un chemin, l'adresse d'un document servirait a
    lire ceux de l'autre entite — la meme famille de defaut que le cloisonnement
    corrige le 04/08/2026.
    """
    import documents as _doc
    import profil as _pr
    ref = str(ref or "").strip()
    if not ref or ".." in ref:
        return None
    # Un identifiant Drive deja descendu dans le cache : il n'a pas de chemin
    # « organisme/... », mais son fichier est bien la, et il est reclame par une
    # fiche de cet organisme ou d'une formation commune.
    if not _doc.est_reference(ref):
        cache = os.path.join(_doc._PIECES, _doc._sain(ref))
        return cache if os.path.exists(cache) else None
    org = _doc._sain(_pr.actif() or "")
    if not (ref.startswith(_doc.DEPOSES_FORMATION + "/") or ref.startswith(org + "/")):
        return None
    return _doc.chemin(ref)


@app.route("/document")
def servir_document():
    """Sert un document range dans DFM, pour l'apercu comme pour l'ouverture."""
    from flask import Response, abort
    import mimetypes
    chem = _ref_permise(request.args.get("ref"))
    if not chem:
        abort(404)
    import documents as _doc
    ref = request.args.get("ref")
    with open(chem, "rb") as f:
        octets = f.read()
    # Le fichier de cache porte l'IDENTIFIANT pour nom ; le vrai nom est dans
    # l'index. Sans cela le navigateur proposerait « 120tVmiFg1uEg… » a
    # l'enregistrement, et le type serait devine sur une extension absente.
    nom = _doc.nom_piece(ref) or os.path.basename(chem)
    return Response(octets, mimetype=mimetypes.guess_type(nom)[0]
                            or mimetypes.guess_type(chem)[0] or "application/octet-stream",
                    headers={"Content-Disposition": "inline; filename*=UTF-8''%s" % _quote_nom(nom),
                             "Cache-Control": "private, max-age=300"})


@app.route("/document/vignette")
def vignette_document():
    """L'image d'apercu d'un document. 404 quand il n'y en a pas."""
    from flask import Response, abort
    import documents as _doc
    ref = request.args.get("ref")
    if not _ref_permise(ref):
        abort(404)
    octets = _doc.vignette(ref)
    if not octets:
        abort(404)
    return Response(octets, mimetype="image/png",
                    headers={"Cache-Control": "private, max-age=600"})


@app.route("/documents/deposer", methods=["POST"])
def documents_deposer():
    """Depose ou remplace une piece depuis l'ecran Documents."""
    import documents as _doc
    fichier = request.files.get("doc")
    if not fichier or not fichier.filename:
        return jsonify({"ok": False, "message": "Aucun fichier reçu."})
    cle = (request.form.get("cle") or "").strip()
    porteur = (request.form.get("porteur") or "").strip()
    type_piece = _CHAMP_VERS_TYPE.get(cle) or (cle if cle in _doc.TYPES_DEPOSES else "")
    if not type_piece:
        return jsonify({"ok": False, "message": "Type de document inconnu : %s." % (cle or "(vide)")})
    if type_piece in ("programme", "acces", "convocation") \
            and not fichier.filename.lower().endswith(".pdf"):
        return jsonify({"ok": False, "message":
                        "Format refusé : seul le PDF est accepté pour ce document."})
    contenu = fichier.read()
    if len(contenu) > 20 * 1024 * 1024:
        return jsonify({"ok": False, "message": "Fichier trop volumineux (20 Mo maximum)."})
    ref, souci = _doc.ranger_depose(type_piece, porteur, fichier.filename, contenu)
    if not ref:
        return jsonify({"ok": False, "message": souci})

    ok, souci, remplace = _documents_inscrire(type_piece, porteur, cle, ref)
    if not ok:
        return jsonify({"ok": False, "message": souci})
    try:
        # CE QUI A ETE REMPLACE EST ECRIT NOIR SUR BLANC. Sans cela, deposer un
        # document par-dessus un autre effacait sa reference en silence — et
        # quand cette reference etait un identifiant Drive, elle etait le SEUL
        # moyen de retrouver le fichier. Constate le 19/08/2026, sur le
        # reglement interieur de DSF.
        journal.ecrire("Document déposé", "",
                       detail="%s — %s" % (_doc.TYPES_DEPOSES[type_piece][1], fichier.filename),
                       details=("Remplace : %s" % remplace) if remplace else
                               "Aucun document ne se trouvait à cette place.")
    except Exception:
        pass
    return jsonify({"ok": True, "ref": ref, "nom": fichier.filename, "remplace": remplace})


def _documents_inscrire(type_piece, porteur, cle, ref):
    """Inscrit la reference sur la fiche qui porte le document. Rend (ok, souci).

    SOUS VERROU, par fichiers.modifier : l'ecran Formation peut enregistrer la
    meme fiche au meme moment, et la derniere ecriture gagnerait sans le dire.
    """
    import fichiers
    import sessions as _S
    portee = _doc_portee(type_piece)
    remplace = ""
    if portee == "organisme":
        import profil as _pr
        champ = {"rib": "rib_id", "reglement": "reglement_interieur_id"}[type_piece]
        try:
            with fichiers.modifier(_pr._chemin(porteur), {}) as d:
                remplace = str(d.get(champ) or "").strip()
                d[champ] = ref
        except Exception as e:
            return False, str(e)[:160], ""
        try:
            _S.appliquer_identite()
        except Exception:
            pass
        return True, "", remplace

    # portee « formation »
    if porteur not in _S.FORMATIONS:
        return False, "Formation inconnue : %s." % porteur, ""
    champ = {"programme": "programme_id", "acces": "acces_id"}.get(type_piece)
    try:
        with fichiers.modifier(_S._FICHIER_F, {}) as d:
            f = d.setdefault(porteur, {})
            if type_piece == "convocation":
                # LES PIECES DE CONVOCATION S'AJOUTENT, elles ne se remplacent
                # pas : elles sont une liste, et deposer la deuxieme ne doit pas
                # effacer la premiere.
                liste = list(f.get("pieces_rappel") or [])
                if ref not in liste:
                    liste.append(ref)
                f["pieces_rappel"] = liste
            else:
                remplace = str(f.get(champ) or "").strip()
                f[champ] = ref
            neuve = dict(f)
    except Exception as e:
        return False, str(e)[:160], ""
    # LA MEMOIRE SUIT LE DISQUE. sessions.FORMATIONS est charge au demarrage :
    # sans cette ligne, le document serait bien ecrit mais l'ecran continuerait
    # a le dire absent jusqu'au prochain redemarrage de DFM.
    _S.FORMATIONS[porteur] = neuve
    return True, "", remplace


def _doc_portee(type_piece):
    import documents as _doc
    return (_doc.TYPES_DEPOSES.get(type_piece) or ("", ""))[0]


@app.route("/documents/retirer", methods=["POST"])
def documents_retirer():
    """Detache une piece de sa fiche et la met de cote. Rien n'est detruit."""
    import documents as _doc
    import fichiers
    import sessions as _S
    cle = (request.form.get("cle") or "").strip()
    porteur = (request.form.get("porteur") or "").strip()
    ref = (request.form.get("ref") or "").strip()
    type_piece = _CHAMP_VERS_TYPE.get(cle) or (cle if cle in _doc.TYPES_DEPOSES else "")
    if not type_piece:
        return jsonify({"ok": False, "message": "Type de document inconnu."})
    portee = _doc_portee(type_piece)
    try:
        if portee == "organisme":
            import profil as _pr
            champ = {"rib": "rib_id", "reglement": "reglement_interieur_id"}[type_piece]
            with fichiers.modifier(_pr._chemin(porteur), {}) as d:
                d[champ] = ""
            _S.appliquer_identite()
        else:
            with fichiers.modifier(_S._FICHIER_F, {}) as d:
                f = d.setdefault(porteur, {})
                if type_piece == "convocation":
                    f["pieces_rappel"] = [x for x in (f.get("pieces_rappel") or []) if x != ref]
                else:
                    f[{"programme": "programme_id", "acces": "acces_id"}[type_piece]] = ""
                neuve = dict(f)
            _S.FORMATIONS[porteur] = neuve
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:160]})
    # Le fichier ne part a la corbeille que s'il est LOCAL : un identifiant
    # Drive ne nous appartient pas, on se contente de le detacher.
    if _doc.est_reference(ref):
        try:
            _doc.ecarter(ref)
        except Exception:
            pass
    try:
        journal.ecrire("Document retiré", "", detail="%s — %s" % (cle, ref[:60]),
                       details=("Référence détachée : %s. " % ref)
                               + ("Le fichier est dans documents/_corbeille."
                                  if _doc.est_reference(ref)
                                  else "Identifiant Drive : le fichier n'a pas été touché."))
    except Exception:
        pass
    return jsonify({"ok": True})


# Le champ du formulaire -> le type de piece de la couche « documents ».
_CHAMP_VERS_TYPE = {"programme_id": "programme", "acces_id": "acces",
                    "pieces_rappel": "convocation",
                    "rib_id": "rib", "reglement_interieur_id": "reglement"}


def _porteur_de(champ, demande, defaut_organisme=True):
    """Qui possede cette piece : une formation, ou un organisme.

    Le programme appartient a la FORMATION — la bibliotheque est commune aux
    deux organismes, et recopier le programme par organisme creerait deux
    verites a tenir d'accord. Le RIB appartient a l'ORGANISME : c'est celui
    d'une entite juridique, et les melanger enverrait un client payer sur le
    mauvais compte.
    """
    import re as _re
    demande = (demande or "").strip()
    if _CHAMP_VERS_TYPE.get(champ) in ("rib", "reglement"):
        import profil as _pr
        return demande or (_pr.actif() or "")
    if demande:
        return _re.sub(r"[^a-z0-9]+", "-", demande.lower()).strip("-")
    return ""


@app.route("/deposer-document", methods=["POST"])
def deposer_document():
    """Depose une piece SUR LE DISQUE.

    CHANGE LE 19/08/2026. Cette route televersait dans le Drive, et c'est elle
    qui a laisse neuf pieces sans aucune copie locale le jour ou l'autorisation
    Google est tombee — dont le reglement interieur de DSF, que l'indicateur 1
    veut remis avant l'entree en formation.
    """
    fichier = request.files.get("doc")
    if not fichier or not fichier.filename:
        return jsonify({"ok": False, "message": "Aucun fichier reçu."})
    champ = (request.form.get("champ") or "").strip()
    type_piece = _CHAMP_VERS_TYPE.get(champ)
    if not type_piece:
        return jsonify({"ok": False, "message":
                        "Ce champ n'attend pas un fichier : %s." % (champ or "(sans nom)")})
    if type_piece in ("programme", "acces", "convocation") \
            and not fichier.filename.lower().endswith(".pdf"):
        return jsonify({"ok": False, "message":
                        "Format refusé : seul le PDF est accepté pour ce document."})
    contenu = fichier.read()
    if len(contenu) > 20 * 1024 * 1024:
        return jsonify({"ok": False, "message": "Fichier trop volumineux (20 Mo maximum)."})

    porteur = _porteur_de(champ, request.form.get("porteur"))
    if not porteur:
        return jsonify({"ok": False, "message":
                        "Nommez d'abord la formation : c'est elle qui portera ce document."})
    import documents as _doc
    ref, souci = _doc.ranger_depose(type_piece, porteur, fichier.filename, contenu)
    if not ref:
        return jsonify({"ok": False, "message": souci})
    ext = (fichier.filename.rsplit(".", 1)[-1] or "").upper()
    return jsonify({"ok": True, "id": ref, "reference": ref, "nom": fichier.filename,
                    "type": ext or "fichier", "local": True, "depose": True})
def _c19_modeles_partages(code_courant, valeurs):
    """Modeles de documents Drive deja utilises par une AUTRE formation.
    Avertissement seulement : deux formations peuvent legitimement partager une
    convention. Mais un partage involontaire ne se voit pas autrement — la fiche
    declare elle-meme le mauvais modele, et la chaine l'applique fidelement (C19)."""
    from sessions import FORMATIONS
    # Les deux « template_* » ont quitte cette table le 19/08/2026 : plus aucun
    # generateur ne les lisait. L'avertissement reste utile pour le programme et
    # le plan d'acces, qui, eux, partent reellement avec les convocations.
    LIB = {"programme_id": "Programme", "acces_id": "Informations d'accès"}
    sortie = []
    for champ, libelle in LIB.items():
        ident = (valeurs.get(champ) or "").strip()
        if not ident:
            continue
        autres = [_tp_nom_formation(c) for c, fi in FORMATIONS.items()
                  if c != code_courant and (fi or {}).get(champ) == ident]
        if autres:
            sortie.append({"champ": champ, "libelle": libelle, "formations": autres})
    return sortie
def _c19_nom_incoherent(nom_fichier, nom_formation):
    """Le nom du fichier evoque-t-il une AUTRE formation que celle editee ?
    C'est ce controle qui aurait attrape le certificat Usures rattache a la
    Masterclass : le fichier portait « CERTIFICAT USURES » en toutes lettres."""
    from sessions import FORMATIONS
    import unicodedata

    def plat(s):
        # Tout separateur non alphanumerique devient une espace : sans cela,
        # "Programme MASTERCLASS.pdf" ne livrerait pas le mot "masterclass",
        # le point collant au mot et cassant la frontiere.
        s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
        s = "".join(c if c.isalnum() else " " for c in s.lower())
        return " " + " ".join(s.split()) + " "
    fich = plat(nom_fichier)
    mienne = plat(nom_formation).strip()
    for fi in FORMATIONS.values():
        autre = plat((fi or {}).get("nom_formation") or "").strip()
        if not autre or len(autre) < 4 or autre == mienne:
            continue
        if (" " + autre + " ") in fich and (not mienne or (" " + mienne + " ") not in fich):
            return ("Ce fichier porte le nom de la formation « "
                    + ((fi or {}).get("nom_formation") or "") + " ». Vérifiez que c'est bien "
                    "le document voulu ici.")
    return ""
@app.route("/verifier-document", methods=["POST"])
def verifier_document():
    """Verifie un lien ou un identifiant Drive : extrait l'identifiant puis
    demande a Drive le nom et le type REELS du fichier. Voir le nom du document
    est la seule preuve qu'on a colle le bon fichier, pas juste une chaine."""
    from sessions import extraire_id
    valeur = (request.form.get("valeur") or "").strip()
    champ = (request.form.get("champ") or "").strip()
    if not valeur:
        return jsonify({"ok": False, "message": "Valeur vide."})
    ident = extraire_id(valeur)
    if not ident:
        return jsonify({"ok": False, "message": "Ni un lien Drive reconnaissable, ni un identifiant."})
    from connexion import service_drive
    try:
        m = service_drive().files().get(fileId=ident, fields="name,mimeType,trashed").execute()
    except Exception as e:
        return jsonify({"ok": False, "message": "Introuvable dans votre Drive : " + str(e)[:90]})
    TYPES = {"application/pdf": "PDF",
             "application/vnd.google-apps.document": "Google Docs",
             "application/vnd.google-apps.presentation": "Google Slides",
             "application/vnd.google-apps.spreadsheet": "Google Sheets",
             "application/vnd.google-apps.folder": "Dossier"}
    genre = TYPES.get(m.get("mimeType"), "fichier")
    alerte = ""
    if m.get("trashed"):
        alerte = "Ce fichier est dans la corbeille du Drive."
    ATTENDUS = {"programme_id": ("PDF",), "acces_id": ("PDF",), "pieces_rappel": ("PDF",),
                "sheet_reponses": ("Google Sheets",), "sheet_suivi": ("Google Sheets",),
                "dossier_conventions": ("Dossier",), "dossier_signees": ("Dossier",)}
    att = ATTENDUS.get(champ)
    if not alerte and att and genre not in att:
        alerte = "Type inattendu : " + genre + " (attendu : " + " ou ".join(att) + ")."
    if not alerte:
        alerte = _c19_nom_incoherent(m.get("name") or "",
                                     request.form.get("formation") or "")
    return jsonify({"ok": True, "id": ident, "nom": m.get("name") or "",
                    "type": genre, "lien": ident != valeur, "alerte": alerte})
@app.route("/formations/nouvelle")
def creer_formation():
    return render_template("formation_creer.html", commun=COMMUN_TPL,
                           heures_par_jour=__import__("jours").heures_par_jour())
@app.route("/formations/<code>/modifier")
def modifier_formation(code):
    if code not in FORMATIONS:
        return redirect("/formations")
    return render_template("formation_creer.html", commun=COMMUN_TPL,
                           heures_par_jour=__import__("jours").heures_par_jour(),
                           fiche_edit=FORMATIONS[code], code_edition=code)
def _resume_synchro(rapport):
    """Ce que la synchronisation a REELLEMENT produit, et pas seulement combien
    d'etapes ont tourne. « 22 etapes » ne distingue pas 22 etapes qui n'ont rien
    fait de 22 etapes qui ont tout fait."""
    etapes = rapport.get("etapes") or []
    sessions = sorted({e.get("session") for e in etapes if e.get("session")})
    faits, sans_effet = [], 0
    for e in etapes:
        if e.get("executee") is False or not e.get("ok"):
            continue
        lignes = [l.strip(" .") for l in (e.get("resume") or []) if l.strip(" .")]
        # Les scripts impriment aussi des lignes d'etat sans effet (« pas encore
        # signe », « deja envoye »). Les compter comme des actions ferait dire au
        # journal qu'il s'est passe quelque chose alors que non.
        SANS_EFFET = ("pas encore", "deja ", "déjà ", "rien", "aucun", "personne",
                      "trop tot", "trop tôt", "non concerne")
        utiles = [l for l in lignes
                  if not any(m in l.lower() for m in SANS_EFFET)]
        if utiles:
            faits.append({"etape": e.get("titre", ""), "session": e.get("session", ""),
                          "quoi": utiles})
        else:
            sans_effet += 1
    echecs = [{"etape": e.get("titre", ""), "session": e.get("session", ""),
               "cause": (e.get("cause") or "")[:140], "bloquant": bool(e.get("bloquant"))}
              for e in (rapport.get("echecs") or [])]
    non_exec = len([e for e in etapes if e.get("executee") is False])
    return {"sessions": sessions, "faits": faits, "sans_effet": sans_effet,
            "echecs": echecs, "non_executees": non_exec}
def _journaliser_synchro(rapport):
    """Une synchronisation « reussie » peut contenir des etapes non bloquantes
    en echec (comportement voulu, point B1). Le journal doit le dire."""
    import journal
    r = _resume_synchro(rapport)
    bouts = []
    for f in r["faits"][:4]:
        bouts.append(f["etape"].lower() + " : " + "; ".join(f["quoi"][:2])
                     + (" …" if len(f["quoi"]) > 2 else ""))
    corps = str(len(r["sessions"])) + " session(s)"
    if bouts:
        corps += " · " + " · ".join(bouts)
    else:
        corps += " · aucun effet"
    if r["sans_effet"]:
        corps += " · " + str(r["sans_effet"]) + " étape(s) sans effet"
    if rapport.get("ok") and r["echecs"]:
        titre = "Synchronisation réussie avec réserves"
        corps += " · " + str(len(r["echecs"])) + " étape(s) en échec : " \
               + ", ".join(e["etape"] + " (" + e["session"] + ")" for e in r["echecs"][:2])
    elif rapport.get("ok"):
        titre = "Synchronisation réussie"
    else:
        titre = "Synchronisation interrompue"
        e = (r["echecs"] or [{}])[0]
        corps = (e.get("etape") or "?") + " (" + (e.get("session") or "?") + ") — " + (e.get("cause") or "")
        if r["non_executees"]:
            corps += " · " + str(r["non_executees"]) + " étape(s) non exécutée(s)"
    journal.ecrire(titre, "", corps[:400])
def _lien_produit(sortie):
    """L'adresse Drive imprimee par un script de generation, ou "".

    DEUX HOTES, PAS UN. Cette lecture ne cherchait que « docs.google.com ».
    Le 06/08/2026, la feuille d'emargement est passee du Google Docs au PDF :
    son adresse est devenue « drive.google.com », plus aucune ligne ne
    correspondait, et l'interface repondait « la feuille n'a pas ete produite »
    alors que le PDF venait d'etre depose. Le lien enregistre restait celui de
    l'ancien document.
    """
    for l in (sortie or "").splitlines():
        if "docs.google.com" in l or "drive.google.com" in l:
            return l.strip()
    return ""


# Champs dont la modification merite d'apparaitre au journal : ceux qui ont un
# effet contractuel ou operationnel. Les autres (description, objectifs, couleur)
# changent souvent et noieraient l'essentiel.
_CHAMPS_FORMATION = [
    # LE TYPE EN TETE : c'est le changement le plus lourd de consequences, celui
    # qu'on doit lire en premier dans le journal quand une formation bascule.
    ("type_formation", "type"),
    ("nom_formation", "intitulé"), ("titre_complet", "titre"), ("tarif", "tarif"),
    ("places_max", "places"), ("duree_heures", "durée"), ("horaires", "horaires"),
    ("adresse", "lieu"), ("public", "public"),
    # Le texte d'accueil du formulaire public. Il appartient a la FORMATION
    # et non a la session : deux sessions d'une meme formation presentent le
    # meme contenu, et le recopier serait deux verites a tenir d'accord.
    ("descriptif_inscription", "descriptif du formulaire"),
    ("programme_id", "programme"), ("acces_id", "informations d'accès"),
    ("pieces_rappel", "pièces du rappel"),
    ("modele_evaluation", "questionnaire d'évaluation"),
    ("modele_satisfaction", "questionnaire de satisfaction"),
    ("modele_froid", "questionnaire à froid"),
    ("modele_mail_signature", "mail de signature"),
    ("modele_mail_confirmation", "mail de confirmation"),
    ("modele_mail_attente", "mail de file d'attente"),
    ("modele_mail_rappel", "mail de rappel"),
    ("modele_mail_facture", "mail de facture"),
    ("modele_mail_attestation", "mail d'attestation"),
]
def _diff_fiche(avant, apres, champs):
    """Liste des champs reellement modifies, avec ancienne et nouvelle valeur.
    Ne compare que les champs presents dans `apres` : un champ absent du
    formulaire n'est pas un effacement."""
    def lisible(v):
        if isinstance(v, (list, tuple)):
            return str(len(v)) + " élément(s)" if v else "aucun"
        s = str(v if v is not None else "").strip()
        return s if s else "(vide)"
    sortie = []
    for cle, libelle in champs:
        if cle not in apres:
            continue
        a, b = avant.get(cle), apres.get(cle)
        if lisible(a) == lisible(b):
            continue
        sortie.append({"champ": libelle, "avant": lisible(a), "apres": lisible(b)})
    return sortie
def _resume_diff(changements, maxi=3):
    """Phrase courte pour la ligne du journal. Le detail complet ira dans la
    colonne « details », consultable sans encombrer la liste."""
    if not changements:
        return ""
    def court(v, n=22):
        v = str(v)
        return v if len(v) <= n else v[:n - 1] + "…"
    bouts = [c["champ"] + " " + court(c["avant"]) + " → " + court(c["apres"])
             for c in changements[:maxi]]
    reste = len(changements) - maxi
    return ", ".join(bouts) + (" (+ " + str(reste) + " autre" + ("s" if reste > 1 else "") + ")" if reste > 0 else "")
@app.route("/formations/nouvelle", methods=["POST"])
def enregistrer_nouvelle_formation():
    import re as _re
    from sessions import enregistrer_formation
    d = request.form
    nom = (d.get("nom_formation") or "").strip()
    if not nom:
        return jsonify({"ok": False, "message": "L'intitule court est obligatoire"})
    edition = (d.get("code_edition") or "").strip()
    if edition:
        if edition not in FORMATIONS:
            return jsonify({"ok": False, "message": "Formation inconnue"})
        code = edition
    else:
        code = _re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")
        if code in FORMATIONS:
            return jsonify({"ok": False, "message": f"Une formation '{code}' existe deja"})
    # Refus explicite plutot que vidage silencieux : une valeur ni lien ni
    # identifiant echouerait des semaines plus tard, sans message (C17).
    for _cle, _lib in (("programme_id", "Programme (PDF)"),
                       ("acces_id", "Informations d'accès (PDF)")):
        _brut = (d.get(_cle) or "").strip()
        if _brut and not _extraire_id(_brut):
            return jsonify({"ok": False, "message": "Le champ « " + _lib + " » ne contient ni un lien Drive reconnaissable, ni un identifiant. Rien n'a été enregistré."})
    # Le gabarit envoie CINQ champs "pieces_rappel" : getlist les recupere tous.
    # d.get() n'en lisait que le premier — les lignes 2 a 5 etaient jetees a
    # chaque enregistrement (C18). Le split conserve la compatibilite avec un
    # eventuel envoi multiligne (brouillon).
    _pieces_brutes = []
    for _bloc in d.getlist("pieces_rappel"):
        _pieces_brutes.extend((_bloc or "").split("\n"))
    for _x in _pieces_brutes:
        if _x.strip() and not _extraire_id(_x):
            return jsonify({"ok": False, "message": "Une pièce du rappel J-20 (« " + _x.strip()[:40] + " ») n'est ni un lien Drive reconnaissable, ni un identifiant. Rien n'a été enregistré."})
    from sessions import nombre as _nb
    _tarif_brut = (d.get("tarif") or "").strip()
    if _tarif_brut and _nb(_tarif_brut, None) is None:
        return jsonify({"ok": False, "message": "Le tarif « " + _tarif_brut[:30]
                        + " » n'est pas un montant lisible. Rien n'a été enregistré."})
    # Stocke normalise : "975 €" ou "1 200" deviennent "975" et "1200".
    _v = _nb(_tarif_brut, 0.0)
    _tarif_propre = str(int(_v)) if float(_v).is_integer() else str(_v)
    objectifs = [o.strip() for o in (d.get("objectifs") or "").split("\n") if o.strip()]
    fiche = {
        "nom_formation": nom,
        "titre_complet": (d.get("titre_complet") or nom).strip(),
        "description": (d.get("description") or "").strip(),
        "public": (d.get("public") or "").strip(),
        # Le texte d'accueil du formulaire public. Les sauts de ligne sont
        # conserves tels quels : c'est ainsi qu'on ecrit un descriptif, et la
        # page les rend en paragraphes.
        "descriptif_inscription": (d.get("descriptif_inscription") or "").strip(),
        "objectifs": objectifs,
        "duree_heures": (d.get("duree_heures") or "14 heures").strip(),
        "tarif": _tarif_propre,
        "places_max": int(d.get("places_max") or 14),
        "adresse": (d.get("adresse") or "").strip(),
        "horaires": (d.get("horaires") or "9h00 - 17h00").strip(),
        "couleur": d.get("couleur") or "#4f7ef8",
        # _extraire_id : accepte un lien Drive complet OU un identifiant nu.
        # Sans cela, une URL collee telle quelle casserait get_media/copy en aval.
        "programme_id": _extraire_id(d.get("programme_id")),
        "acces_id": _extraire_id(d.get("acces_id")),
        "pieces_rappel": [_extraire_id(x) for x in _pieces_brutes if _extraire_id(x)],
        "modele_evaluation": (d.get("modele_evaluation") or "").strip(),
        "modele_satisfaction": (d.get("modele_satisfaction") or "").strip(),
        "modele_froid": (d.get("modele_froid") or "").strip(),
        "modele_mail_signature": (d.get("modele_mail_signature") or "").strip(),
        "modele_mail_confirmation": (d.get("modele_mail_confirmation") or "").strip(),
        "modele_mail_attente": (d.get("modele_mail_attente") or "").strip(),
        "modele_mail_rappel": (d.get("modele_mail_rappel") or "").strip(),
        "modele_mail_facture": (d.get("modele_mail_facture") or "").strip(),
        "modele_mail_attestation": (d.get("modele_mail_attestation") or "").strip(),
        "modele_mail_invitation": (d.get("modele_mail_invitation") or "").strip(),
        # LE TYPE DE FORMATION. Pose le 23/08/2026 : les deux pipelines ne
        # partagent qu'UNE etape sur dix-huit, et l'ecran de creation s'y adapte.
        # Ce qu'il vaut ici : le mode PROPOSE PAR DEFAUT a la creation d'une
        # session. Il ne contraint pas — une formation client peut encore servir
        # en individuel si l'on change le mode sur la session, et c'est
        # volontaire tant que Franck n'a pas tranche l'inverse.
        "type_formation": ("client" if (d.get("type_formation") or "").strip() == "client"
                           else "individuel"),
    }
    changements = []
    if edition:
        ancienne = dict(FORMATIONS.get(code) or {})
        changements = _diff_fiche(ancienne, fiche, _CHAMPS_FORMATION)
        ancienne.update(fiche)
        fiche = ancienne
    try:
        avertissements = _c19_modeles_partages(code, fiche)
        enregistrer_formation(code, fiche)
        journal.ecrire("Formation modifiée" if edition else "Formation créée", "",
                       nom + (" — " + _resume_diff(changements) if changements else ""))
        return jsonify({"ok": True, "code": code, "avertissements": avertissements})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
# En-tetes des 13 premieres colonnes d'un onglet de suivi : ce sont les intitules
# des questions du Google Form d'inscription.
# A MAINTENIR ALIGNE SUR DEUX CHOSES, dans le meme ordre :
#   - les questions du Google Form d'inscription ;
#   - les indices 0 a 12 de suivi.COL (horodateur, nom, prenom, mail, telephone,
#     ville, date_formation, demande, connu_par, dejeuner, restrictions, image, pmr).
# Attention : importer_inscriptions.py recopie les reponses du Form par position
# dans les colonnes A:M. Un ecart d'ordre ici, ou dans le Form, fait atterrir les
# donnees dans les mauvaises colonnes sans declencher la moindre erreur.
ENTETES_FORM = [
    "Horodateur",
    "NOM (en majuscules)",
    "Prénom",
    "Adresse mail",
    "Numéro de téléphone",
    "Lieu d'exercice (ville)",
    "Date de la formation choisie",
    "Votre demande",
    "Comment avez-vous connu cette formation ?",
    "Je souhaite déjeuner avec le groupe",
    "Si restrictions alimentaires, précisez",
    "Autorisation image (réseaux sociaux)",
    "Je suis porteur(euse) d'un handicap ou nécessite un accès PMR",
]
def _extraire_id(valeur):
    from sessions import extraire_id
    return extraire_id(valeur)
def _texte_dates(debut, fin, liste=None):
    """La phrase des dates. Une seule regle, dans jours.py.

    Reliait autrefois debut et fin par « et », ce qui annoncait deux journees
    quelle que soit la duree reelle : « lundi 10 et mardi 25 aout » pour une
    formation de cinq jours. Sans liste, on retombe sur l'ancienne lecture —
    deux journees — pour ne pas changer le sens des sessions deja creees.
    """
    import jours as _J
    j = _J.normaliser(liste or []) or _J.depuis_bornes(debut, fin)
    return _J.texte(j)
@app.route("/sessions/nouvelle")
def creer_session():
    from datetime import datetime as dt
    fiches = []
    for code, f in FORMATIONS.items():
        fiches.append({"code": code, "nom": f["nom_formation"],
                       "titre": f.get("titre_complet", f["nom_formation"]),
                       "tarif": f.get("tarif", ""), "places": f.get("places_max", 14),
                       "adresse": f.get("adresse", ""), "duree": f.get("duree_heures", "")})
    import clients as _CL
    import sessions as _S
    # Ce que chaque formation transmettra reellement a sa session.
    import questionnaires as _Q
    quest = {}
    for code in FORMATIONS:
        titres = []
        for genre in ("evaluation", "satisfaction", "froid"):
            try:
                m = _Q.pour_formation(code, genre) if genre != "evaluation" else _Q.pour_formation(code)
            except TypeError:
                m = _Q.pour_formation(code) if genre == "evaluation" else None
            except Exception:
                m = None
            if m and (m.get("titre") or m.get("id")):
                titres.append(m.get("titre") or m.get("id"))
        quest[code] = titres
    return render_template("session_creer.html", formations=fiches,
                           modes=_S.MODES, clients=_CL.liste(),
                           questionnaires=quest,
                           fonctions=__import__("contacts").FONCTIONS,
                           heures_par_jour=__import__("jours").heures_par_jour(),
                           manques={c["id"]: _CL.complet(c) for c in _CL.liste()})
@app.route("/sessions/nouvelle", methods=["POST"])
def enregistrer_nouvelle_session():
    import re as _re
    from datetime import datetime as dt
    from connexion import service_sheets
    from sessions import enregistrer_session, COMMUN
    import suivi as _suivi
    d = request.form
    formation = d.get("formation") or ""
    if formation not in FORMATIONS:
        return jsonify({"ok": False, "message": "Formation inconnue"})
    code_session = _re.sub(r"[^a-z0-9]+", "", (d.get("code_session") or "").lower())
    if not code_session:
        return jsonify({"ok": False, "message": "Le code de session est obligatoire"})
    code = f"{formation}-{code_session}"
    if code in SESSIONS:
        return jsonify({"ok": False, "message": f"La session '{code}' existe deja"})
    # LES JOURNEES FONT FOI, les bornes en decoulent. Un champ de date libre a
    # cote d'une liste de journees finit toujours par la contredire, et c'est
    # precisement l'ecart qu'un financeur releve sur une convention.
    import jours as _J
    _liste = _J.normaliser(d.getlist("jours") if hasattr(d, "getlist")
                           else (d.get("jours") or []))
    if not _liste:
        _liste = _J.depuis_bornes(d.get("date_debut") or "", d.get("date_fin") or "")
    debut, fin = _J.bornes(_liste)
    if not debut:
        return jsonify({"ok": False, "message": "Aucune journée de formation n'est retenue."})
    # Le mode se choisit ICI et nulle part ailleurs : il commande les documents
    # que la session produira. Le refus est prononce AVANT toute creation, pour
    # qu'une session client sans client ne puisse pas exister.
    import sessions as _S
    import clients as _CL
    _mode_demande = (d.get("mode") or "individuel").strip()
    if _mode_demande not in _S.MODES:
        return jsonify({"ok": False, "message": "Mode de session inconnu."})
    # L'organisme proprietaire est celui du profil ACTIF, ecrit explicitement.
    # Une session sans organisme est refusee : elle apparaitrait dans l'audit
    # des deux entites, ou d'aucune.
    try:
        import profil as _PR
        _organisme = (_PR.actif() or "").strip()
    except Exception:
        _organisme = ""
    if not _organisme:
        return jsonify({"ok": False, "message":
                        "Aucun profil d'organisme actif : impossible de dire à qui appartiendrait "
                        "cette session. Rien n'a été créé."})
    _client_demande = (d.get("client") or "").strip()
    if _mode_demande == "client":
        if not _client_demande:
            return jsonify({"ok": False, "message": "Une session client doit désigner son client. Rien n'a été créé."})
        if not _CL.client(_client_demande):
            return jsonify({"ok": False, "message": "Ce client n'existe pas dans la base clients. Rien n'a été créé."})
    _brut_rep = (d.get("sheet_reponses") or "").strip()
    if _brut_rep and not _extraire_id(_brut_rep):
        return jsonify({"ok": False, "message": "Le Sheet de réponses ne contient ni un lien Drive reconnaissable, ni un identifiant. Rien n'a été créé."})
    nom_formation = FORMATIONS[formation]["nom_formation"]
    onglet = f"{nom_formation}-{code_session}"
    fiche = {
        "formation": formation,
        "code_session": code_session,
        "onglet_suivi": onglet,
        "date_debut": debut,
        "date_fin": fin,
        "jours": _liste,
        "date_texte": d.get("date_texte") or _texte_dates(debut, fin, _liste),
        "sheet_reponses": _extraire_id(d.get("sheet_reponses")),
        "stripe_lien": (d.get("stripe_lien") or "").strip(),
        "mode": _mode_demande,
        "organisme": _organisme,
    }
    if _mode_demande == "client":
        fiche["client"] = _client_demande
    for cle in ("tarif", "places_max", "adresse", "heure_debut", "heure_fin", "salle", "note"):
        v = (d.get(cle) or "").strip()
        if v:
            fiche[cle] = int(v) if cle == "places_max" else v
    _h1 = (d.get("heure_debut") or "").strip()
    _h2 = (d.get("heure_fin") or "").strip()
    if _h1 and _h2:
        fiche["horaires"] = _h1 + " - " + _h2
    etapes = []
    sheets = service_sheets()
    feuille = COMMUN["sheet_suivi"]
    try:
        meta = sheets.spreadsheets().get(spreadsheetId=feuille).execute()
        existants = [x["properties"]["title"] for x in meta["sheets"]]
        if onglet in existants:
            etapes.append({"ok": True, "texte": f"Onglet « {onglet} » deja present"})
        else:
            sheets.spreadsheets().batchUpdate(
                spreadsheetId=feuille,
                body={"requests": [{"addSheet": {"properties": {
                    "title": onglet,
                    "gridProperties": {"rowCount": 1002, "columnCount": 52, "frozenRowCount": 1}}}}]},
            ).execute()
            etapes.append({"ok": True, "texte": f"Onglet « {onglet} » cree"})
        entetes = [None] * len(_suivi.COL)
        for cle, idx in _suivi.COL.items():
            entetes[idx] = cle
        entetes[:len(ENTETES_FORM)] = ENTETES_FORM
        sheets.spreadsheets().values().update(
            spreadsheetId=feuille, range=f"'{onglet}'!A1",
            valueInputOption="USER_ENTERED", body={"values": [entetes]},
        ).execute()
        etapes.append({"ok": True, "texte": "40 colonnes de suivi ecrites"})
    except Exception as e:
        etapes.append({"ok": False, "texte": f"Onglet de suivi : {e}"})
    try:
        enregistrer_session(code, fiche)
        # L'ETAT SE POSE APRES L'ENREGISTREMENT, jamais avant : le miroir
        # recompose la ligne du classeur depuis sessions.json, et une session
        # pas encore enregistree y arriverait sans nom ni dates.
        SESSIONS_MOD.poser_etat(code, "statut_session", "ouverte")
        journal.ecrire("Session créée", "", f"{nom_formation} — {fiche['date_texte']}", "", code)
        etapes.append({"ok": True, "texte": "Fiche de session enregistree"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e), "etapes": etapes})
    manquants = []
    # Une session client n'a ni formulaire ni lien de paiement : le centre
    # fournit sa liste et regle sur facture. Les reclamer laisserait croire
    # qu'il manque quelque chose alors que tout est complet.
    if _mode_demande == "client":
        return jsonify({"ok": True, "code": code, "etapes": etapes, "manquants": []})
    if not fiche["sheet_reponses"]:
        manquants.append("le Sheet de reponses du formulaire")
    if not fiche["stripe_lien"]:
        manquants.append("le lien de paiement Stripe")
    return jsonify({"ok": True, "code": code, "etapes": etapes, "manquants": manquants})
@app.route("/apercu-dates", methods=["POST"])
def apercu_dates():
    """La phrase des dates, calculee a la volee pendant la saisie.

    Recoit la liste des journees retenues ; sans elle — un appel ancien —
    retombe sur les deux bornes.
    """
    import jours as _J
    try:
        liste = _J.normaliser(request.form.getlist("jours"))
        if not liste:
            liste = _J.depuis_bornes(request.form.get("debut"), request.form.get("fin"))
        return jsonify({"texte": _J.texte(liste), "nb": len(liste),
                        "duree": _J.duree(liste), "detail": _J.detail(liste)})
    except Exception:
        return jsonify({"texte": ""})
@app.route("/sessions")
def liste_sessions():
    g = donnees.global_kpi()
    try:
        etats = _et_lire()
    except Exception:
        etats = {}
    ORDRE = {"active": 0, "cloturee": 1, "archivee": 2}
    for x in (g.get("sessions") or []):
        d = etats.get(x.get("code")) or {}
        if d.get("terminee_le"):
            groupe = "archivee"
        elif (d.get("statut") or "") == "cloturee":
            groupe = "cloturee"
        else:
            groupe = "active"
        x["etat"] = {"groupe": groupe, "terminee_le": d.get("terminee_le", ""),
                     "cloture_le": d.get("cloture_le", "")}
    try:
        g["sessions"] = sorted(g.get("sessions") or [],
                               key=lambda x: ORDRE.get(x["etat"]["groupe"], 0))
    except Exception:
        pass
    return render_template("sessions.html", g=g)
@app.route("/session/<code>")
def detail_session(code):
    if code not in SESSIONS:
        return redirect(url_for("liste_sessions"))
    s = donnees.une_session(code)
    try:
        dossiers = donnees.dossiers_session(code)
    except Exception:
        dossiers = []
    # LE LIEN D'INSCRIPTION SE CALCULE, il ne se stocke pas. Il n'a donc rien a
    # creer a la naissance d'une session, rien a reparer si une adresse change,
    # et le onzieme organisme aura le sien sans qu'on y pense. Les sessions
    # client n'en ont pas : leurs participants sont saisis par le centre.
    lien_inscription = ""
    try:
        _S = fiche_session(code)
        if not SESSIONS_MOD.est_client(code):
            _base = (_S.get("url_signature") or "").rstrip("/")
            _org = SESSIONS_MOD.organisme_de(code) or ""
            if _base and _org:
                lien_inscription = "%s/inscription.html?of=%s&s=%s" % (_base, _org, code)
    except Exception:
        lien_inscription = ""
    # LE VOCABULAIRE DES FONCTIONS descend dans l'ecran : la saisie des
    # participants doit PROPOSER une liste, pas laisser deviner. Une fonction
    # tapee a la main finit toujours par exister en trois orthographes.
    import contacts as _Cf
    # L'ETAT DE PUBLICATION SE LIT A L'AFFICHAGE. Une session peut exister dans DFM
    # sans etre proposee au public : c'est l'etat normal au depart, et l'ecran doit
    # le DIRE plutot que de laisser deviner — le lien d'inscription s'affichait sans
    # que rien n'indique qu'il ne menait a rien.
    # La lecture passe par le reseau : son echec rend None, et l'ecran l'avoue,
    # plutot que d'afficher « ferme » sur une session peut-etre ouverte.
    etat_inscription = None
    if lien_inscription:
        try:
            import inscription as _insc
            etat_inscription = _insc.etat(code)
        except Exception:
            etat_inscription = None
    # LA CARTE DES ACTIONS NE VAUT QUE POUR UNE SESSION INDIVIDUELLE. En mode
    # client, les colonnes du parcours individuel restent vides par construction :
    # la carte n'afficherait qu'une colonne de tirets, ce qui ferait croire a un
    # oubli au lieu de dire une difference de nature.
    actions_faites, jalons = [], []
    if not SESSIONS_MOD.est_client(code):
        try:
            actions_faites = _actions_faites(s.get("lignes") if isinstance(s, dict) else None,
                                             s.get("places_max") if isinstance(s, dict) else 0)
        except Exception:
            actions_faites = []
        try:
            jalons = _jalons_session(code, s)
        except Exception:
            jalons = []
    return render_template("session.html", s=s, dossiers=dossiers,
                           fonctions=_Cf.FONCTIONS,
                           lien_inscription=lien_inscription,
                           etat_inscription=etat_inscription,
                           actions_faites=actions_faites, jalons=jalons)
# LES ACTIONS DEJA FAITES SUR UNE SESSION, en une liste lisible.
#
# POURQUOI CETTE LISTE EXISTE. Les cinq compteurs du haut de l'ecran disent OU ON
# EN EST — inscrits, conventions envoyees, signees, reglements, chiffre d'affaires.
# Ils ne disent pas CE QUI A ETE FAIT : les questionnaires partis, les rappels, les
# relances, les attestations. Ces evenements etaient lisibles un par un dans le
# tableau des inscrits, colonne par colonne, et nulle part en resume.
#
# ON COMPTE SUR TOUTES LES LIGNES, pas seulement les inscrits actifs : un mail
# parti a quelqu'un qui a annule EST parti. C'est un releve d'actions, pas un etat
# des lieux — les deux ne se confondent pas, et le titre de la carte le dit.
_ACTIONS_SESSION = [
    ("horodateur",             "Inscriptions reçues",       "ti-user-plus"),
    ("mail1_envoye_le",        "Conventions envoyées",      "ti-mail"),
    ("signe_le",               "Conventions signées",       "ti-signature"),
    ("convention_pdf_le",      "Conventions contresignées", "ti-file-check"),
    ("mail2_envoye_le",        "Confirmations envoyées",    "ti-mail-check"),
    ("relance_signature_le",   "Relances de signature",     "ti-repeat"),
    ("rappel_le",              "Rappels J-20",              "ti-bell"),
    ("facture_le",             "Factures générées",         "ti-receipt"),
    ("facture_envoyee_le",     "Factures envoyées",         "ti-send"),
    ("paiement_recu_le",       "Règlements enregistrés",    "ti-coin"),
    ("relance_reglement_le",   "Relances de règlement",     "ti-repeat"),
    ("eval_init_le",           "Évaluations de départ",     "ti-school"),
    ("eval_fin_le",            "Évaluations finales",       "ti-school"),
    ("satisfaction_le",        "Questionnaires satisfaction", "ti-star"),
    ("froid_le",               "Évaluations à froid",       "ti-clock-hour-9"),
    ("attestation_le",         "Attestations générées",     "ti-certificate"),
    ("attestation_envoyee_le", "Attestations envoyées",     "ti-send"),
]

# LE VOLET FINANCIER NE CONCERNE PAS LES INVITES. Rien ne leur est demande, aucune
# facture ne leur est due : les compter au denominateur affichait « 9 / 12 » sur une
# session entierement a jour, et ces trois unites manquantes passaient pour un retard.
_ACTIONS_FINANCIERES = {"facture_le", "facture_envoyee_le",
                        "paiement_recu_le", "relance_reglement_le"}


def _quand(v):
    """Rend une date francaise comparable. None si elle ne se lit pas.

    LES DATES DU SUIVI SONT DU TEXTE, « 04/10/2026 09:15 » ou « 04/10/2026 ». Les
    comparer comme des chaines mettrait le 09/01 apres le 10/12 : il faut les lire.
    Une date illisible ne casse rien, elle ne compte pas pour la plus recente.
    """
    from datetime import datetime as _dt
    t = str(v or "").strip()
    for forme in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return _dt.strptime(t, forme)
        except ValueError:
            continue
    return None


def _actions_faites(lignes, places=0):
    """Un releve par action : combien, sur combien, et quand pour la derniere fois.

    UN NOMBRE SEUL NE DIT RIEN. « Conventions signees : 4 » laisse chercher le
    total ailleurs sur l'ecran ; « 4 / 14 » se lit d'un coup. Le denominateur est
    le nombre d'inscrits, sauf pour les inscriptions elles-memes, qui se comparent
    aux places ouvertes.

    LES REGLEMENTS PORTENT LEUR MONTANT. Huit reglements de 975 euros ou huit
    reglements partiels ne demandent pas la meme action : la somme encaissee est
    la seule precision qui tranche.
    """
    lignes = lignes or []
    total = len(lignes)
    payants = len([l for l in lignes if not str(l.get("invite_le") or "").strip()])
    sortie = []
    for cle, libelle, icone in _ACTIONS_SESSION:
        dates = [str(l.get(cle) or "").strip() for l in lignes]
        dates = [d for d in dates if d]
        dernier = ""
        if dates:
            lus = [(_quand(d), d) for d in dates if _quand(d)]
            if lus:
                dernier = max(lus)[1]
        detail = ""
        if cle == "paiement_recu_le":
            somme = 0.0
            for l in lignes:
                if not str(l.get(cle) or "").strip():
                    continue
                brut = str(l.get("montant_recu") or "").replace(",", ".")
                brut = "".join(c for c in brut if c.isdigit() or c == ".")
                try:
                    somme += float(brut or 0)
                except ValueError:
                    pass
            if somme:
                detail = ("%d" % somme if somme == int(somme) else "%.2f" % somme) + " €"
        sortie.append({"cle": cle, "libelle": libelle, "icone": icone,
                       "nb": len(dates),
                       "sur": (places or total) if cle == "horodateur"
                              else (payants if cle in _ACTIONS_FINANCIERES else total),
                       "dernier": dernier, "detail": detail})
    return sortie


def _jalons_session(code, s):
    """Les jalons de la session, pour la barre d'etat.

    TROIS ETATS ET NON DEUX : fait, pas encore, et INCONNU. L'etat des
    questionnaires se lit sur le reseau ; si la lecture echoue, cocher ou decocher
    serait affirmer quelque chose qu'on ne sait pas. Un jalon inconnu le dit.

    CHAQUE JALON NOMME SA SOURCE dans « sur », et c'est volontaire : « formation
    cloturee » peut vouloir dire deux choses dans DFM — les inscriptions fermees,
    ou la session archivee — et seule la seconde cloture la formation.
    """
    lignes = (s.get("lignes") or []) if isinstance(s, dict) else []
    actifs = (s.get("actifs") or []) if isinstance(s, dict) else []
    feuille = (s.get("sheet") or {}) if isinstance(s, dict) else {}

    def compte(cle, base=None):
        base = actifs if base is None else base
        return len([1 for l in base if str(l.get(cle) or "").strip()])

    def date_max(cle, base=None):
        base = actifs if base is None else base
        lus = [(_quand(l.get(cle)), str(l.get(cle) or "").strip()) for l in base]
        lus = [x for x in lus if x[0]]
        return max(lus)[1] if lus else ""

    # L'etat des trois questionnaires vit dans la table publique, pas dans DFM.
    publie, ouvert, inconnu = False, {}, False
    try:
        r = _sb("Sessions_publiques?session_code=eq." + code + "&select=questions,ouvert,maj")
        if r:
            publie = bool(r[0].get("questions"))
            ouvert = r[0].get("ouvert") or {}
    except Exception:
        inconnu = True

    def reseau(fait):
        return "inconnu" if inconnu else ("fait" if fait else "attente")

    etat_sess = {}
    try:
        import sessions as _S
        etat_sess = _S.etat(code) or {}
    except Exception:
        etat_sess = {}

    n = len(actifs)
    att = compte("attestation_envoyee_le")
    jalons = [
        {"libelle": "Questionnaire publié", "court": "Quest. publié", "icone": "ti-upload",
         "etat": reseau(publie), "sur": "la page publique des questionnaires"},
        {"libelle": "Rappel J-20 envoyé", "court": "Rappel J-20", "icone": "ti-bell",
         "etat": "fait" if compte("rappel_le") else "attente",
         "date": date_max("rappel_le"),
         "sur": "%d inscrit(s) sur %d" % (compte("rappel_le"), n) if n else ""},
        {"libelle": "Évaluation initiale ouverte", "court": "Éval. initiale", "icone": "ti-school",
         "etat": reseau(bool(ouvert.get("init"))), "sur": "interrupteur « init »"},
        {"libelle": "Évaluation finale ouverte", "court": "Éval. finale", "icone": "ti-school",
         "etat": reseau(bool(ouvert.get("fin"))), "sur": "interrupteur « fin »"},
        {"libelle": "Satisfaction ouverte", "court": "Satisfaction", "icone": "ti-star",
         "etat": reseau(bool(ouvert.get("satisfaction"))), "sur": "interrupteur « satisfaction »"},
        {"libelle": "Émargement signé reçu", "court": "Émargement", "icone": "ti-clipboard-check",
         "etat": "fait" if feuille.get("lien_emargement_signe") else "attente",
         "date": feuille.get("emargement_signe_le") or "", "sur": "scan déposé dans DFM"},
        {"libelle": "Attestations envoyées", "court": "Attestations", "icone": "ti-certificate",
         "etat": "fait" if (n and att >= n) else "attente",
         "date": date_max("attestation_envoyee_le"),
         "sur": "%d sur %d inscrit(s)" % (att, n) if n else ""},
        {"libelle": "Formation clôturée", "court": "Clôturée", "icone": "ti-archive",
         "etat": "fait" if etat_sess.get("terminee_le") else "attente",
         "date": etat_sess.get("terminee_le") or "", "sur": "session archivée"},
    ]
    for j in jalons:
        j.setdefault("date", "")
    return jalons


@app.route("/session/<code>/liens", methods=["POST"])
def session_liens(code):
    """Renseigne apres coup le lien de paiement et le classeur de reponses.

    POURQUOI CETTE ROUTE EXISTE. L'ecran de creation porte un encadre « Liens a
    coller » qui promet : « Tu peux aussi les ajouter plus tard. » C'etait faux —
    AUCUN ECRAN NE PERMETTAIT DE MODIFIER UNE SESSION une fois creee. Une session
    nee sans lien de paiement le restait, et le rappel J-20 partait avec un bouton
    « Regler ma formation » qui ne menait nulle part. Constate le 04/10/2026.

    ON N'ECRIT QUE CES DEUX CHAMPS. La fiche est relue puis reecrite entiere par
    enregistrer_session : fusionner plutot que remplacer est ici une obligation,
    sans quoi dates, tarif et mode disparaitraient d'un coup.
    """
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue."})
    import sessions as _S
    import journal
    fiche = dict(_S._charger_json(_S._FICHIER_S).get(code) or {})
    if not fiche:
        return jsonify({"ok": False, "message":
                        "Cette session est definie dans le code, pas dans les donnees : "
                        "elle ne peut pas etre modifiee ici."})
    change = []
    if "stripe_lien" in request.form:
        lien = (request.form.get("stripe_lien") or "").strip()
        # UN LIEN QUI N'EN EST PAS UN EST REFUSE. Un champ rempli de travers vaut
        # moins qu'un champ vide : vide, le mail masque le bouton ; faux, il offre
        # un bouton mort a quelqu'un qui veut payer.
        if lien and not lien.lower().startswith(("http://", "https://")):
            return jsonify({"ok": False, "message":
                            "Le lien de paiement doit commencer par https://. Rien n'a été enregistré."})
        if lien != (fiche.get("stripe_lien") or ""):
            fiche["stripe_lien"] = lien
            change.append("lien de paiement " + ("renseigné" if lien else "retiré"))
    if "sheet_reponses" in request.form:
        brut = (request.form.get("sheet_reponses") or "").strip()
        ident = _extraire_id(brut) if brut else ""
        if brut and not ident:
            return jsonify({"ok": False, "message":
                            "Ce lien ne contient ni adresse Drive reconnaissable ni identifiant. "
                            "Rien n'a été enregistré."})
        if ident != (fiche.get("sheet_reponses") or ""):
            fiche["sheet_reponses"] = ident
            change.append("classeur de réponses " + ("renseigné" if ident else "retiré"))
    if not change:
        return jsonify({"ok": True, "message": "Rien n'a changé."})
    _S.enregistrer_session(code, fiche)
    try:
        journal.ecrire("Session modifiée", "", code + " — " + ", ".join(change), "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "message": ", ".join(change).capitalize() + ".",
                    "stripe_lien": fiche.get("stripe_lien") or "",
                    "sheet_reponses": fiche.get("sheet_reponses") or ""})


@app.route("/session/<code>/formulaire", methods=["POST"])
def session_formulaire(code):
    """Ouvre ou ferme le formulaire public d'inscription de CETTE session.

    POURQUOI CETTE ROUTE EXISTE. La fonction qui publie une session vit dans
    inscription.py depuis le 06/08/2026, propre et eprouvee — mais AUCUN ECRAN NE
    L'APPELAIT. Ouvrir les inscriptions demandait donc une commande, et une session
    creee dans DFM restait invisible du public sans que rien ne le dise. Constate le
    04/10/2026 sur la session de fevrier 2027.

    NE PAS CONFONDRE AVEC « CLOTURER LES INSCRIPTIONS ». Celle-la agit a l'interieur
    de DFM et renvoie les demandes suivantes en file d'attente ; celle-ci decide si
    la session est PROPOSEE sur la page publique. On peut vouloir l'une sans
    l'autre : une session complete reste publiee pour que le praticien voie qu'elle
    existe, et cloturee pour qu'il entre en file d'attente.

    LE REFUS DES SESSIONS CLIENT EST PRONONCE PAR inscription.publier, qui connait
    la regle : leurs participants sont saisis par le centre, elles n'ont pas de
    formulaire. On ne la redit pas ici — une regle ecrite deux fois finit par
    differer.
    """
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue."})
    import inscription as _insc
    ouverte = (request.form.get("ouverte") or "").strip() in ("1", "oui", "true")
    ok, message = _insc.publier(code, ouverte=True) if ouverte else _insc.fermer(code)
    if ok:
        # LA PISTE D'AUDIT RETIENT L'OUVERTURE. A partir de quand une formation a ete
        # proposee au public, et jusqu'a quand : c'est exactement ce qu'un controle
        # demande en examinant le recrutement des stagiaires.
        try:
            import journal
            journal.ecrire("Formulaire public " + ("ouvert" if ouverte else "ferme"), "",
                           "%s — inscriptions %s sur la page publique"
                           % (code, "ouvertes" if ouverte else "fermees"), "", code)
        except Exception:
            pass
    etat = None
    try:
        etat = _insc.etat(code)
    except Exception:
        etat = None
    return jsonify({"ok": ok, "message": message, "etat": etat})


@app.route("/inscrits")
def liste_inscrits():
    """L'ancienne « Base apprenants » mene desormais a l'ecran unifie, filtre
    sur les apprenants : une seule liste ou chercher une personne. L'adresse
    est conservee pour que rien de ce qui pointait vers elle ne se casse."""
    from flask import redirect
    return redirect("/contacts?qualite=apprenant")
@app.route("/formateurs")
def page_formateurs():
    """Les profils formateurs de l'organisme actif, en fiches.

    L'ecran a longtemps vecu au bas de la fiche de l'organisme, en une liste
    d'une ligne par personne. L'indicateur 21 se joue sur des PIECES : il faut
    les voir, pas seulement lire qu'elles manquent.
    """
    import formateurs as _f
    from sessions import FORMATIONS
    gens = []
    for f in _f.lister():
        pieces = _f.pieces(f["id"])
        gens.append(dict(f, pieces=pieces, formations_nommees=[
            (FORMATIONS.get(c) or {}).get("nom_formation") or c
            for c in (f.get("formations") or [])]))
    return render_template("formateurs.html", gens=gens,
                           alertes=_f.alertes(), orphelines=_f.orphelines())


@app.route("/formateurs/liste")
def liste_formateurs():
    import formateurs as _f
    try:
        return jsonify({"ok": True, "formateurs": _f.lister(),
                        "alertes": _f.alertes(),
                        "orphelines": _f.orphelines()})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:200]})


@app.route("/formateur/<ident>/piece")
def formateur_piece(ident):
    """Sert une piece du dossier, pour l'apercu comme pour le telechargement.

    Le controle d'appartenance vit dans formateurs.octets_piece : une reference
    etant un chemin, sans lui l'adresse d'une piece servirait a lire n'importe
    quel document de DFM.
    """
    from flask import Response, abort
    import formateurs as _f
    octets, type_, nom = _f.octets_piece(ident, request.args.get("ref") or "")
    if not octets:
        abort(404)
    # « inline » : le navigateur affiche le PDF au lieu de le telecharger.
    return Response(octets, mimetype=type_, headers={
        "Content-Disposition": "inline; filename*=UTF-8''%s" % _quote_nom(nom),
        "Cache-Control": "private, max-age=300"})


@app.route("/formateur/<ident>/vignette")
def formateur_vignette(ident):
    """L'image d'apercu d'une piece. 404 quand il n'y en a pas — l'ecran
    affiche alors l'icone du format, ce qui est une reponse, pas une panne."""
    from flask import Response, abort
    import formateurs as _f
    octets = _f.octets_vignette(ident, request.args.get("ref") or "")
    if not octets:
        abort(404)
    return Response(octets, mimetype="image/png",
                    headers={"Cache-Control": "private, max-age=600"})


def _quote_nom(nom):
    import urllib.parse
    return urllib.parse.quote(nom or "piece", safe="")
@app.route("/formateur/ajouter", methods=["POST"])
def formateur_ajouter():
    import formateurs as _f
    fiche, souci = _f.ajouter(request.form.get("nom") or "",
                              request.form.get("prenom") or "",
                              request.form.get("civilite") or "",
                              request.form.get("fonction") or "")
    if not fiche:
        return jsonify({"ok": False, "message": souci})
    try:
        journal.ecrire("Formateur ajouté", fiche["nom_complet"])
    except Exception:
        pass
    return jsonify({"ok": True, "formateur": fiche})
@app.route("/formateurs/disponibles")
def formateurs_disponibles():
    """Les personnes deja connues que cet organisme n'a PAS encore declarees.

    Sans cet ecran, on recreerait la personne — et son dossier repartirait
    vide, ce qui est exactement le defaut corrige le 19/08/2026.
    """
    import formateurs as _f
    try:
        gens = [g for g in _f.tous() if not g.get("rattache")]
        return jsonify({"ok": True, "formateurs": gens})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:200]})


@app.route("/formateur/<ident>/rattacher", methods=["POST"])
def formateur_rattacher(ident):
    """Declare qu'une personne deja enregistree intervient pour cet organisme."""
    import formateurs as _f
    fiche, souci = _f.rattacher(ident)
    if not fiche:
        return jsonify({"ok": False, "message": souci})
    try:
        journal.ecrire("Formateur rattaché", fiche["nom_complet"],
                       details="Dossier partagé : CV, diplôme et pièces sont ceux "
                               "déjà déposés pour cette personne.")
    except Exception:
        pass
    return jsonify({"ok": True, "formateur": fiche})


@app.route("/formateur/<ident>")
def fiche_formateur(ident):
    """La fiche d'un formateur : son identite, ses formations, ses pieces."""
    import formateurs as _f
    from sessions import FORMATIONS
    f = _f.un(ident)
    if not f:
        return redirect("/profil")
    catalogue = sorted(
        ({"code": c, "nom": (FORMATIONS[c].get("nom_formation") or c),
          "titre": FORMATIONS[c].get("titre_complet") or ""} for c in FORMATIONS),
        key=lambda x: x["nom"].lower())
    # LE RETOUR MENE D'OU L'ON VIENT. La fiche a deux portes d'entree depuis le
    # 18/08/2026 — la fiche de l'organisme et l'ecran Profils formateurs — et le
    # bouton ne connaissait que la premiere : entre par la seconde, on en
    # ressortait ailleurs.
    #
    # LE POINT DE DEPART VOYAGE DANS L'ADRESSE, pas dans le referent HTTP : la
    # fiche se RECHARGE apres chaque depot de piece, et un referent ne survit
    # pas toujours a un rechargement. Une chaine de requete, si.
    retours = {"profil": ("/profil", "Fiche de l'organisme"),
               "formateurs": ("/formateurs", "Profils formateurs")}
    retour = retours.get(request.args.get("de") or "", retours["formateurs"])
    # POUR QUI CETTE PERSONNE INTERVIENT. Le dossier est partage entre
    # organismes depuis le 19/08/2026 : sans cette ligne, on modifie une fiche
    # sans savoir qu'on touche aussi celle que voit l'autre entite.
    import profil as _pr
    noms = {}
    for p in _pr.lister():
        i = p["id"] if isinstance(p, dict) else p
        noms[i] = (_pr.charger(i) or {}).get("marque") or i
    lies = [{"id": o, "nom": noms.get(o, o), "actif": o == (_pr.actif() or "")}
            for o in (f.get("organismes_lies") or [])]
    return render_template("formateur.html", f=f, pieces=_f.pieces(ident),
                           catalogue=catalogue,
                           obligatoires=_f.OBLIGATOIRES, organismes_lies=lies,
                           retour_lien=retour[0], retour_nom=retour[1])
@app.route("/formateur/<ident>/photo")
def formateur_photo(ident):
    """Relaie la photo depuis le Drive.

    Comme pour le logo : un fichier du Drive n'est pas affichable dans une
    balise <img> sans le rendre public, et la photo d'un formateur n'a aucune
    raison d'etre lisible du monde entier.
    """
    from flask import Response, abort
    import formateurs as _f
    octets, type_ = _f.octets_photo(ident)
    if not octets:
        abort(404)
    return Response(octets, mimetype=type_,
                    headers={"Cache-Control": "private, max-age=300"})
@app.route("/formateur/<ident>/enregistrer", methods=["POST"])
def formateur_enregistrer(ident):
    import formateurs as _f
    donnees = request.get_json(silent=True) or {}
    fiche, souci = _f.enregistrer(ident, donnees)
    if not fiche:
        return jsonify({"ok": False, "message": souci})
    try:
        journal.ecrire("Formateur modifié", fiche["nom_complet"])
    except Exception:
        pass
    return jsonify({"ok": True, "formateur": fiche})
@app.route("/formateur/<ident>/deposer", methods=["POST"])
def formateur_deposer(ident):
    """Depose une piece justifiant la qualite du formateur — indicateur 21."""
    import formateurs as _f
    fichier = request.files.get("piece")
    if not fichier or not fichier.filename:
        return jsonify({"ok": False, "message": "Aucun fichier recu."})
    role = (request.form.get("role") or "autre").strip()
    piece, souci = _f.deposer(ident, role, fichier.filename, fichier.read(),
                              fichier.mimetype or "")
    if not piece:
        return jsonify({"ok": False, "message": souci})
    try:
        journal.ecrire("Pièce formateur déposée", (_f.un(ident) or {}).get("nom_complet", ""),
                       detail="%s : %s" % (role, fichier.filename))
    except Exception:
        pass
    return jsonify({"ok": True, "piece": piece, "formateur": _f.un(ident)})
@app.route("/formateur/<ident>/retirer", methods=["POST"])
def formateur_retirer(ident):
    """Met une piece a la corbeille du Drive — jamais de suppression definitive."""
    import formateurs as _f
    ok, message = _f.retirer(ident, (request.form.get("id") or "").strip())
    if not ok:
        return jsonify({"ok": False, "message": message})
    try:
        journal.ecrire("Pièce formateur retirée", (_f.un(ident) or {}).get("nom_complet", ""),
                       detail=message,
                       details="Mise à la corbeille du Drive, récupérable 30 jours.")
    except Exception:
        pass
    return jsonify({"ok": True, "formateur": _f.un(ident)})
@app.route("/formateur/<ident>/supprimer", methods=["POST"])
def formateur_supprimer(ident):
    """Retire le formateur du registre. Ses pieces RESTENT dans le Drive."""
    import formateurs as _f
    ok, message, formations = _f.supprimer(ident)
    if not ok:
        return jsonify({"ok": False, "message": message})
    try:
        journal.ecrire("Formateur détaché", message,
                       detail=("Formations qui lui étaient rattachées ici : %s"
                               % ", ".join(formations)) if formations else "",
                       details="Détaché de cet organisme seulement. La personne et son "
                               "dossier restent connus des autres organismes : ne plus "
                               "intervenir ici n'efface pas ce qu'elle a animé ailleurs. "
                               "Le rattacher de nouveau ne ramènera PAS ses formations : "
                               "elles sont inscrites ci-dessus.")
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/reclamations")
def page_reclamations():
    """Le registre des reclamations — indicateur 31.

    Ce que l'auditeur demande n'est pas l'absence de reclamation, mais la
    trace de leur traitement : reception, accuse, reponse, cloture, delai.
    """
    import reclamations as _r
    try:
        lien_public = _r.lien()
    except Exception:
        lien_public = ""
    return render_template("reclamations.html",
                           liste=_r.lister(), bilan=_r.bilan(), lien_public=lien_public,
                           origines=_r.ORIGINES, issues=_r.ISSUES,
                           sessions=sorted(SESSIONS.keys()))
@app.route("/audit")
def page_audit():
    """L'assistant d'audit : le referentiel lu pour l'organisme actif."""
    import qualiopi as _q
    d = _q.etat()
    return render_template("audit.html", d=d, blocs=_q.par_critere(d),
                           registres=_q.REGISTRES,
                           consignations={r: _q.consignations(r) for r in _q.REGISTRES})
@app.route("/audit/consigner", methods=["POST"])
def audit_consigner():
    """Ajoute une entree a un registre — veille, formation continue, aleas…

    C'est le seul endroit ou l'assistant ECRIT. Consigner ne rend pas conforme :
    cela donne quelque chose a montrer la ou il n'y avait rien.
    """
    import qualiopi as _q
    registre = (request.form.get("registre") or "").strip()
    entree, souci = _q.consigner(registre, request.form.to_dict())
    if not entree:
        return jsonify({"ok": False, "message": souci})
    try:
        journal.ecrire("Consignation Qualiopi",
                       detail="%s — %s" % (_q.REGISTRES[registre][0], entree["quoi"]))
    except Exception:
        pass
    return jsonify({"ok": True, "entree": entree})
@app.route("/audit/consignation/retirer", methods=["POST"])
def audit_retirer_consignation():
    """Retire une ligne d'un registre. `qualiopi.retirer_consignation` existait
    depuis le debut sans qu'aucun ecran ne l'appelle : une ligne saisie de
    travers ne pouvait pas se corriger."""
    import qualiopi as _q
    registre = (request.form.get("registre") or "").strip()
    ident = (request.form.get("id") or "").strip()
    if not _q.retirer_consignation(registre, ident):
        return jsonify({"ok": False, "message": "Ligne introuvable."})
    try:
        journal.ecrire("Consignation retirée",
                       detail="%s — %s" % (_q.REGISTRES.get(registre, (registre,))[0], ident))
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/veilles")
def page_veilles():
    """Les quatre axes du critere 6, d'un coup d'oeil."""
    import veille as _v
    return render_template("veilles.html", axes=_v.tableau(), resume=_v.resume())
@app.route("/veille/<cle>")
def page_veille(cle):
    import veille as _v
    e = _v.etat(cle)
    if not e:
        return redirect(url_for("page_veilles"))
    return render_template("veille.html", e=e)
@app.route("/veille/source/ajouter", methods=["POST"])
def veille_ajouter_source():
    import veille as _v
    cle = (request.form.get("cle") or "").strip()
    s, souci = _v.ajouter_source(cle, request.form.to_dict())
    if not s:
        return jsonify({"ok": False, "message": souci})
    return jsonify({"ok": True, "source": s})
@app.route("/veille/justificatif", methods=["POST"])
def veille_deposer_justificatif():
    """Depose une piece jointe pour une consignation de veille."""
    import veille as _v
    f = request.files.get("fichier")
    if not f or not f.filename:
        return jsonify({"ok": False, "message": "Aucun fichier reçu."})
    d, souci = _v.deposer_justificatif((request.form.get("cle") or "").strip(),
                                       f.filename, f.read())
    if not d:
        return jsonify({"ok": False, "message": souci})
    return jsonify({"ok": True, **d})
@app.route("/veille/justificatifs/remonter", methods=["POST"])
def veille_remonter():
    """Rattrape les justificatifs que le Drive n'avait pas pu recevoir."""
    import veille as _v
    montes, soucis = _v.remonter_en_attente()
    if soucis and not montes:
        return jsonify({"ok": False, "message":
                        "Aucun fichier remonté. " + soucis[0].split(" : ", 1)[-1][:160]})
    return jsonify({"ok": True, "montes": len(montes), "soucis": len(soucis)})
@app.route("/justificatif/<path:rel>")
def voir_justificatif(rel):
    """Ouvre un justificatif deja depose."""
    import veille as _v
    from flask import send_file
    plein = _v.chemin_justificatif(rel)
    if not plein:
        return "Justificatif introuvable", 404
    return send_file(plein)
@app.route("/veille/source/retirer", methods=["POST"])
def veille_retirer_source():
    import veille as _v
    cle = (request.form.get("cle") or "").strip()
    if not _v.retirer_source(cle, (request.form.get("id") or "").strip()):
        return jsonify({"ok": False, "message": "Source introuvable."})
    return jsonify({"ok": True})
@app.route("/audit/dossier")
def audit_dossier():
    """Tout le referentiel en un document imprimable, a poser sur la table."""
    import qualiopi as _q
    from datetime import datetime as dt
    d = _q.etat()
    return render_template("audit_dossier.html", d=d, blocs=_q.par_critere(d),
                           registres=_q.REGISTRES,
                           consignations={r: _q.consignations(r) for r in _q.REGISTRES},
                           edite=dt.now().strftime("%d/%m/%Y"))
@app.route("/reclamations/registre")
def reclamations_registre():
    """Le registre tel qu'on le presente en controle, imprimable.

    Distinct de l'ecran /reclamations, qui est un ecran de travail : ici, rien
    n'est modifiable, tout est date, et le document dit d'ou viennent les
    reclamations — un registre sans son canal de depot ne prouve qu'a moitie.
    """
    import reclamations as _r
    import profil as _pr
    from datetime import datetime as dt
    f = _pr.charger() or {}
    return render_template("reclamations_registre.html",
                           liste=_r.lister(), bilan=_r.bilan(),
                           marque=f.get("marque") or f.get("organisme") or "",
                           raison_sociale=f.get("organisme") or "",
                           siret=f.get("siret") or "",
                           contact=f.get("reclamations_contact") or "",
                           delai=_r._delai_annonce(),
                           edite=dt.now().strftime("%d/%m/%Y"))
@app.route("/reclamations/relever", methods=["POST"])
def reclamations_relever():
    """Rapatrie les reclamations deposees sur la page publique."""
    import reclamations as _r
    combien, souci = _r.relever()
    if souci:
        return jsonify({"ok": False, "message": souci})
    if combien:
        try:
            journal.ecrire("Réclamations relevées",
                           detail="%d nouvelle(s) depuis la page publique" % combien)
        except Exception:
            pass
    return jsonify({"ok": True, "nouvelles": combien})
@app.route("/reclamations/ajouter", methods=["POST"])
def reclamation_ajouter():
    import reclamations as _r
    fiche, souci = _r.ajouter(request.form.to_dict())
    if not fiche:
        return jsonify({"ok": False, "message": souci})
    try:
        journal.ecrire("Réclamation reçue", fiche.get("qui") or "",
                       detail="%s — %s" % (fiche["numero"], fiche["objet"]),
                       code_session=fiche.get("session") or "")
    except Exception:
        pass
    return jsonify({"ok": True, "reclamation": fiche})
@app.route("/reclamations/<ident>/enregistrer", methods=["POST"])
def reclamation_enregistrer(ident):
    import reclamations as _r
    avant = _r.une(ident)
    fiche, souci = _r.enregistrer(ident, request.get_json(silent=True) or {})
    if not fiche:
        return jsonify({"ok": False, "message": souci})
    try:
        # On ne journalise que la CLOTURE : enregistrer chaque frappe noierait
        # la piste d'audit sous des evenements sans portee.
        if fiche.get("close_le") and not (avant or {}).get("close_le"):
            journal.ecrire("Réclamation close", fiche.get("qui") or "",
                           detail="%s — %s" % (fiche["numero"], fiche["issue_libelle"]),
                           code_session=fiche.get("session") or "",
                           details=fiche.get("traitement") or "")
    except Exception:
        pass
    return jsonify({"ok": True, "reclamation": fiche})
@app.route("/conservation")
def politique_conservation():
    """La politique de conservation, telle qu'on la produit en controle.

    Les trois durees declarees dans les reglages n'etaient lues nulle part.
    Cet ecran les confronte aux donnees reellement detenues — sans rien
    supprimer : la decision de retirer des pieces de formation reste humaine.
    """
    import conservation as _cons
    from datetime import datetime as dt
    try:
        etat = _cons.etat()
    except Exception as e:
        etat = []
        print("   (etat de conservation indisponible : %s)" % e)
    return render_template("conservation.html", etat=etat,
                           edite=dt.now().strftime("%d/%m/%Y"))
@app.route("/journal/verifier")
def verifier_journal():
    """Recalcule la chaine de scelles des deux organismes.

    Route separee, et non calcul a l'affichage : la verification lit l'integralite
    des journaux, ce qui n'a pas a ralentir chaque consultation. C'est un geste
    que l'on pose devant un auditeur, pas un traitement de fond.
    """
    try:
        return jsonify({"ok": True, "feuilles": journal.verifier()})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})
@app.route("/journal")
def voir_journal():
    from datetime import datetime as dt
    PALETTE = [("#2a78d6", "#eaf1fc"), ("#7c5bf7", "#f0eefe"), ("#0f9e6a", "#eafaf3"),
               ("#d4890a", "#fdf0dc"), ("#d03b3b", "#fdeaea")]
    couleurs = {}
    for i, code in enumerate(SESSIONS):
        S = fiche_session(code)
        d = dt.strptime(S["date_debut"], "%Y-%m-%d")
        couleurs[code] = {
            "libelle": f"{S['nom_formation']} · {MOIS_COURT[d.month]}. {d.year}",
            "texte": PALETTE[i % len(PALETTE)][0],
            "fond": PALETTE[i % len(PALETTE)][1],
        }
    # Meme raison qu'au tableau de bord : un classeur inaccessible doit
    # produire une phrase, pas une page « Internal Server Error » qui ne dit
    # ni ce qui a echoue ni quoi faire.
    try:
        entrees = journal.lire(500)
    except Exception as e:
        souci = str(e)
        return render_template(
            "erreur.html", titre="Journal indisponible",
            sous_titre="Ce n'est pas une fiche manquante : la lecture a échoué",
            explication=("Le reste de l'application fonctionne normalement : seules "
                         "les pages qui affichent le journal sont concernées. "
                         "Une fois l'accès rétabli, rien d'autre n'est à faire."),
            second_lien="/profils", second_libelle="Profils organismes",
            message=(
                "Le classeur de suivi de cet organisme n'est pas accessible au "
                "compte Google connecté à DFM. Partagez-le avec ce compte, ou "
                "reconnectez DFM avec le compte qui en est propriétaire."
                if ("does not have permission" in souci or "403" in souci)
                else "Le journal n'a pas pu être lu : " + souci[:200])), 503
    for e in entrees:
        e["style"] = journal.style(e["type_action"])
        e["tag"] = couleurs.get(e["session"], {"libelle": e["session"] or "Systeme",
                                               "texte": "#6b7280", "fond": "#f1f2f6"})
        e["heure_fr"] = e["heure"].replace(":", "h")
    categorie = request.args.get("cat", "tout")
    recherche = (request.args.get("q") or "").lower()
    filtre_session = request.args.get("session", "")
    if categorie != "tout":
        entrees = [e for e in entrees if e["style"]["categorie"] == categorie]
    if filtre_session:
        entrees = [e for e in entrees if e["session"] == filtre_session]
    if recherche:
        entrees = [e for e in entrees
                   if recherche in (e["praticien"] + " " + e["type_action"] + " " + e["detail"]).lower()]
    aujourdhui = date.today().strftime("%d/%m/%Y")
    from datetime import timedelta
    hier = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    jours = []
    courant = None
    for e in entrees:
        if courant is None or courant["date"] != e["date"]:
            if e["date"] == aujourdhui:
                libelle = "Aujourd'hui — " + e["date"]
            elif e["date"] == hier:
                libelle = "Hier — " + e["date"]
            else:
                libelle = e["date"]
            courant = {"date": e["date"], "libelle": libelle, "entrees": []}
            jours.append(courant)
        courant["entrees"].append(e)
    return render_template("journal.html", jours=jours, total=len(entrees),
                           categories=journal.CATEGORIES, categorie=categorie,
                           recherche=request.args.get("q") or "",
                           sessions_dispo=couleurs, filtre_session=filtre_session)
@app.route("/session/<code>/emargement", methods=["POST"])
def deposer_emargement(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    fichier = request.files.get("scan")
    if not fichier or not fichier.filename:
        return jsonify({"ok": False, "message": "Aucun fichier recu"})
    from connexion import service_drive, service_sheets
    from googleapiclient.http import MediaInMemoryUpload
    from datetime import datetime as dt
    import journal
    S = fiche_session(code)
    drive = service_drive()
    sheets = service_sheets()
    try:
        # L'emargement signe rejoint le dossier de l'organisme de CETTE session,
        # designe par identifiant. Par nom, une feuille DSF partait chez
        # Smileclub, qui possedait le seul dossier de ce nom.
        import dossiers
        _em = dossiers.trouver(drive, S, "dossier_emargement", "Emargement")
        if not _em:
            return jsonify({"ok": False, "message": "Dossier Emargement introuvable dans le Drive"})
        r = [{"id": _em}]
        contenu = fichier.read()
        extension = fichier.filename.rsplit(".", 1)[-1].lower() if "." in fichier.filename else "pdf"
        nom = f"Emargement signe - {S['dossier_session']}.{extension}"
        media = MediaInMemoryUpload(contenu, mimetype=fichier.mimetype or "application/pdf")
        anciens = drive.files().list(
            q=f"name='{nom}' and '{r[0]['id']}' in parents and trashed=false", fields="files(id)",
        ).execute().get("files", [])
        for vieux in anciens:
            drive.files().delete(fileId=vieux["id"]).execute()
        cree = drive.files().create(
            body={"name": nom, "parents": [r[0]["id"]]}, media_body=media, fields="id",
        ).execute()
        lien = f"https://drive.google.com/file/d/{cree['id']}/view"
        SESSIONS_MOD.poser_etats(code, {
            "emargement_signe_le": dt.now().strftime("%d/%m/%Y %H:%M"),
            "lien_emargement_signe": lien})
        journal.ecrire("Émargement signé reçu", "", nom, "", code)
        return jsonify({"ok": True, "lien": lien})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})
@app.route("/session/<code>/cloturer", methods=["POST"])
def cloturer_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    from datetime import datetime as dt
    import journal
    S = fiche_session(code)
    try:
        maintenant = dt.now().strftime("%d/%m/%Y %H:%M")
        # LA CLOTURE EN UNE SEULE ECRITURE : une session ne doit jamais paraitre
        # cloturee sans sa date, meme le temps de deux appels.
        SESSIONS_MOD.poser_etats(code, {"statut_session": "cloturee",
                                        "cloture_le": maintenant})
        # Le code de session est indispensable : sans lui le script travaille sur
        # SESSION_ACTIVE et produit la feuille d'une AUTRE session (point A2).
        r = subprocess.run([sys.executable, "generer_emargement.py", code],
                           capture_output=True, text=True, cwd=DOSSIER, timeout=300)
        lien = _lien_produit(r.stdout)
        if lien:
            SESSIONS_MOD.poser_etats(code, {"emargement_genere_le": maintenant,
                                            "lien_emargement": lien})
        journal.ecrire("Inscriptions clôturées", "", S["nom_formation"], "", code)
        return jsonify({"ok": True, "emargement": bool(lien)})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})
@app.route("/session/<code>/impact")
def impact_suppression(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    from connexion import service_sheets
    from sessions import SESSION_ACTIVE
    S = fiche_session(code)
    inscrits = 0
    try:
        lignes = service_sheets().spreadsheets().values().get(
            spreadsheetId=S["sheet_suivi"], range="'" + S["onglet_suivi"] + "'!A2:A1000"
        ).execute().get("values", [])
        inscrits = len([l for l in lignes if l and str(l[0]).strip()])
    except Exception:
        inscrits = -1
    return jsonify({"ok": True, "code": code, "inscrits": inscrits,
                    "active": code == SESSION_ACTIVE,
                    "onglet": S["onglet_suivi"], "nom": S["nom_formation"]})
@app.route("/session/<code>/suppression/impact")
def impact_suppression_session(code):
    """Ce qu'une suppression de session emporte, ce qu'elle laisse, et ou.
    Ne modifie rien. Trois categories : nettoye d'office (aucune valeur
    probante), propose (conserve par defaut), jamais touche (pieces comptables
    et piste d'audit)."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    auto, propose, jamais = [], [], []
    try:
        lignes = _lignes_onglet(S)
    except Exception:
        lignes = []
    inscrits = len(lignes)
    if inscrits:
        jamais.append({"quoi": "L'onglet de suivi « " + S["onglet_suivi"] + " »",
                       "ou": "Google Sheets",
                       "note": str(inscrits) + " inscrit(s) — l'onglet est renommé ZZ-supprimee-…, jamais effacé"})
    else:
        auto.append({"quoi": "L'onglet de suivi « " + S["onglet_suivi"] + " »",
                     "ou": "Google Sheets", "note": "aucun inscrit"})
    auto.append({"quoi": "La ligne de la session", "ou": "onglet Sessions", "note": ""})
    try:
        import config
        from supabase import create_client
        sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        n_sig = len(sb.table("Signatures").select("praticien").eq("formation", S["nom_formation"]).execute().data or [])
        n_q = len(sb.table("Questionnaires").select("mail").eq("session_code", code).execute().data or [])
        if n_sig:
            auto.append({"quoi": str(n_sig) + " signature(s)", "ou": "Supabase",
                         "note": "la convention signée reste dans le Drive"})
        if n_q:
            auto.append({"quoi": str(n_q) + " réponse(s) de questionnaire", "ou": "Supabase", "note": ""})
    except Exception as e:
        auto.append({"quoi": "Lignes Supabase", "ou": "Supabase", "note": "inventaire indisponible : " + str(e)[:60]})
    try:
        from connexion import service_drive
        dr = service_drive()
        dossier_session = S["dossier_session"]
        # PAR IDENTIFIANT, comme supprimees.py qui fait le travail reel. Cet
        # apercu cherchait les dossiers PAR NOM, sur tout le Drive : il balayait
        # donc les deux organismes, et surtout il cherchait « Emargements » —
        # au pluriel — alors que le dossier s'appelle « Emargement ». Aucune
        # feuille d'emargement n'a jamais figure dans cet apercu. C'est le
        # document qu'on lit AVANT de supprimer une session.
        def _contenu(fid, genre):
            if not genre.endswith("folder"):
                return ""      # une piece isolee, pas un dossier a compter
            k = dr.files().list(q="'" + fid + "' in parents and trashed=false",
                                fields="files(id)", pageSize=200).execute().get("files", [])
            return str(len(k)) + " "

        def _entrees(cle):
            parent = (S.get(cle) or "").strip()
            if not parent:
                return []
            return [f for f in dr.files().list(
                        q="'" + parent + "' in parents and trashed=false",
                        fields="files(id,name,mimeType)", pageSize=100).execute().get("files", [])
                    if dossier_session in f["name"]]

        for cle, libelle, etiquette in (
                ("dossier_signees", "Conventions signées", "conventions signées"),
                ("dossier_attestations", "Attestations", "attestations"),
                ("dossier_emargement", "Émargement", "feuilles d'émargement")):
            for sd in _entrees(cle):
                propose.append({"quoi": libelle + "/" + sd["name"], "ou": "Drive",
                                "note": _contenu(sd["id"], sd["mimeType"]) + etiquette})
        for sd in _entrees("dossier_factures"):
            jamais.append({"quoi": "Factures/" + sd["name"], "ou": "Drive",
                           "note": _contenu(sd["id"], sd["mimeType"])
                                   + "facture(s) — pièces comptables, jamais supprimées automatiquement"})
    except Exception as e:
        propose.append({"quoi": "Dossiers Drive", "ou": "Drive", "note": "inventaire indisponible : " + str(e)[:60]})
    try:
        import journal
        n_j = len([e for e in journal.lire(5000) if e.get("session") == code])
    except Exception:
        n_j = 0
    if n_j:
        jamais.append({"quoi": str(n_j) + " entrée(s) de journal", "ou": "Google Sheets",
                       "note": "piste d'audit — elle doit survivre à ce qu'elle documente"})
    return jsonify({"ok": True, "code": code, "nom": S.get("nom_formation") or code,
                    "inscrits": inscrits, "auto": auto, "propose": propose, "jamais": jamais})
@app.route("/session/<code>/supprimer", methods=["POST"])
def supprimer_la_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _v = _et_verrou(code, "suppression")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from connexion import service_sheets
    from sessions import supprimer_session, SESSION_ACTIVE
    import journal
    if code == SESSION_ACTIVE:
        return jsonify({"ok": False, "message": "Cette session est la session active de DFM. Change la session active dans sessions.py avant de la supprimer."})
    if (request.form.get("confirmation") or "").strip() != code:
        return jsonify({"ok": False, "message": "Le code recopie ne correspond pas."})
    S = fiche_session(code)
    id_sessions = None
    onglet = S["onglet_suivi"]
    feuille = S["sheet_suivi"]
    sheets = service_sheets()
    etapes = []
    inscrits = 0
    try:
        lignes = sheets.spreadsheets().values().get(
            spreadsheetId=feuille, range="'" + onglet + "'!A2:A1000"
        ).execute().get("values", [])
        inscrits = len([l for l in lignes if l and str(l[0]).strip()])
    except Exception:
        inscrits = 0
    try:
        meta = sheets.spreadsheets().get(spreadsheetId=feuille).execute()
        id_onglet = None
        id_sessions = None
        for x in meta["sheets"]:
            t = x["properties"]["title"]
            if t == onglet:
                id_onglet = x["properties"]["sheetId"]
            if t == "Sessions":
                id_sessions = x["properties"]["sheetId"]
        if id_onglet is None:
            etapes.append({"ok": True, "texte": "Onglet de suivi deja absent"})
        elif inscrits == 0:
            sheets.spreadsheets().batchUpdate(
                spreadsheetId=feuille,
                body={"requests": [{"deleteSheet": {"sheetId": id_onglet}}]},
            ).execute()
            etapes.append({"ok": True, "texte": "Onglet de suivi supprime (aucun inscrit)"})
        else:
            nouveau = ("ZZ-supprimee-" + onglet)[:95]
            sheets.spreadsheets().batchUpdate(
                spreadsheetId=feuille,
                body={"requests": [{"updateSheetProperties": {
                    "properties": {"sheetId": id_onglet, "title": nouveau},
                    "fields": "title"}}]},
            ).execute()
            etapes.append({"ok": True, "texte": str(inscrits) + " inscrit(s) : onglet conserve sous le nom " + nouveau})
            # OU SONT PARTIES LES PIECES. Sans cette trace, un controle portant
            # sur cette formation obligerait a fouiller le Drive a l'aveugle.
            # Le journal doit dire ce qui a ete conserve et sous quel nom.
            try:
                journal.ecrire("Session supprimée", "",
                               "%s — %d inscrit(s) conservé(s) dans l'onglet « %s ». "
                               "Documents laissés sur le Drive. Écran : Sessions supprimées."
                               % (code, inscrits, nouveau), "", "")
            except Exception:
                pass
    except Exception as e:
        etapes.append({"ok": False, "texte": "Onglet de suivi : " + str(e)})
    try:
        # L'ETAT LOCAL PART AVEC LA SESSION. Sans cela, recreer plus tard une
        # session du meme code ressusciterait sa cloture et son emargement.
        import base as _b
        if _b.etat_supprimer(SESSIONS_MOD.organisme_de(code) or "", code):
            etapes.append({"ok": True, "texte": "Etat de session retire de la base"})
    except Exception as e:
        etapes.append({"ok": False, "texte": "Etat de session : " + str(e)})
    try:
        if id_sessions is not None:
            codes = sheets.spreadsheets().values().get(
                spreadsheetId=feuille, range="'Sessions'!A2:A200"
            ).execute().get("values", [])
            trouve = None
            for i, c in enumerate(codes):
                if c and c[0] == code:
                    trouve = i + 1
                    break
            if trouve is None:
                etapes.append({"ok": True, "texte": "Ligne deja absente de l'onglet Sessions"})
            else:
                sheets.spreadsheets().batchUpdate(
                    spreadsheetId=feuille,
                    body={"requests": [{"deleteDimension": {"range": {
                        "sheetId": id_sessions, "dimension": "ROWS",
                        "startIndex": trouve, "endIndex": trouve + 1}}}]},
                ).execute()
                etapes.append({"ok": True, "texte": "Ligne retiree de l'onglet Sessions"})
    except Exception as e:
        etapes.append({"ok": False, "texte": "Onglet Sessions : " + str(e)})
    try:
        supprimer_session(code)
        etapes.append({"ok": True, "texte": "Fiche de session supprimee"})
    except Exception as e:
        etapes.append({"ok": False, "texte": "Fiche : " + str(e)})
    # LES LIGNES PUBLIQUES PARTENT AVEC LA SESSION — ajoute le 04/10/2026. Elles
    # survivaient, indexees sur le code : une session recreee avec un code deja
    # utilise heritait de l'etat de la precedente, et la page publique des
    # questionnaires servait encore les participants de l'ancienne.
    try:
        import inscription as _insc
        _effacees = _insc.oublier(code)
        etapes.append({"ok": True, "texte": ("Lignes publiques retirees : " + ", ".join(_effacees))
                       if _effacees else "Aucune ligne publique a retirer"})
    except Exception as e:
        etapes.append({"ok": False, "texte": "Lignes publiques : " + str(e)[:90]})
    revient = code in SESSIONS
    try:
        journal.ecrire("Session supprimée", "", S["nom_formation"] + " — " + code, "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "etapes": etapes, "revient": revient})
@app.route("/formations/<code>/impact")
def impact_formation(code):
    if code not in FORMATIONS:
        return jsonify({"ok": False, "message": "Formation inconnue"})
    liees = [c for c, x in SESSIONS.items() if (x or {}).get("formation") == code]
    return jsonify({"ok": True, "code": code,
                    "nom": FORMATIONS[code].get("nom_formation", code),
                    "sessions": liees})
@app.route("/formations/<code>/supprimer", methods=["POST"])
def supprimer_la_formation(code):
    if code not in FORMATIONS:
        return jsonify({"ok": False, "message": "Formation inconnue"})
    from sessions import supprimer_formation
    import journal
    liees = [c for c, x in SESSIONS.items() if (x or {}).get("formation") == code]
    if liees:
        return jsonify({"ok": False, "message": "Cette formation porte encore " + str(len(liees)) + " session(s) : " + ", ".join(liees) + ". Supprime-les d'abord."})
    if (request.form.get("confirmation") or "").strip() != code:
        return jsonify({"ok": False, "message": "Le code recopie ne correspond pas."})
    nom = FORMATIONS[code].get("nom_formation", code)
    etapes = []
    try:
        supprimer_formation(code)
        etapes.append({"ok": True, "texte": "Fiche de formation supprimee"})
    except Exception as e:
        etapes.append({"ok": False, "texte": str(e)})
    revient = code in FORMATIONS
    try:
        journal.ecrire("Formation supprimée", "", nom)
    except Exception:
        pass
    return jsonify({"ok": True, "etapes": etapes, "revient": revient})
def _lettre(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s
@app.route("/session/<code>/reglement", methods=["POST"])
def enregistrer_reglement(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("reglement")
    if _g:
        return jsonify({"ok": False, "message": _g})
    from connexion import service_sheets
    from datetime import datetime as dt
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    mail = (request.form.get("mail") or "").strip().lower()
    montant = (request.form.get("montant") or "").strip()
    mode = (request.form.get("mode") or "Virement").strip()
    quand = (request.form.get("date") or "").strip() or dt.now().strftime("%d/%m/%Y")
    if not mail:
        return jsonify({"ok": False, "message": "Praticien non identifie"})
    if not montant:
        return jsonify({"ok": False, "message": "Le montant est obligatoire"})
    try:
        lignes = _suivi.lire_lignes_de(code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du suivi : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable dans cette session"})
    numero = cible["_numero"]

    def valeur(cle):
        return cible.get(cle) or ""
    if valeur("paiement_recu_le"):
        return jsonify({"ok": False, "message": "Un reglement est deja enregistre pour ce praticien."})
    nom = valeur("nom")
    reference = (S["nom_formation"] + "-" + S["code_session"] + "-" + nom).upper()
    ecritures = {
        "montant_recu": montant,
        "mode_paiement": mode,
        "reference_paiement": reference,
        "paiement_recu_le": quand,
    }
    if not valeur("montant_du"):
        ecritures["montant_du"] = S.get("tarif", "")
    try:
        _suivi.ecrire_plusieurs(numero, ecritures, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    try:
        journal.ecrire("Règlement enregistré", nom, mode + " " + str(montant) + " EUR", montant, code)
    except Exception:
        pass
    return jsonify({"ok": True, "reference": reference, "montant": montant,
                    "mode": mode, "date": quand, "nom": nom, "ligne": numero})
@app.route("/session/<code>/reglement/corriger", methods=["POST"])
def corriger_reglement(code):
    """Retire un reglement saisi par erreur : vide les quatre colonnes d'un
    coup, recalcule le statut, et journalise le montant retire.
    Un reglement efface sans trace serait pire que pas d'effacement — la piste
    d'audit doit montrer qu'il a existe puis qu'il a ete retire, et par quoi."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("reglement")
    if _g:
        return jsonify({"ok": False, "message": _g})
    from connexion import service_sheets
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    mail = (request.form.get("mail") or "").strip().lower()
    motif = (request.form.get("motif") or "").strip()
    if not mail:
        return jsonify({"ok": False, "message": "Praticien non identifie"})
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    if not cible.get("paiement_recu_le"):
        return jsonify({"ok": False, "message": "Aucun reglement enregistre pour ce praticien."})
    ancien = {"montant": cible.get("montant_recu") or "",
              "mode": cible.get("mode_paiement") or "",
              "reference": cible.get("reference_paiement") or "",
              "date": cible.get("paiement_recu_le") or ""}
    # Les quatre colonnes sont videes ensemble : en laisser une remplie
    # produirait une ligne incoherente, mi-payee mi-impayee.
    vides = ["montant_recu", "mode_paiement", "reference_paiement", "paiement_recu_le"]
    for c in vides:
        cible[c] = ""
    ecritures = {c: "" for c in vides}
    ecritures["statut"] = _suivi.calculer_statut(cible)
    try:
        _suivi.ecrire_plusieurs(cible["_numero"], ecritures, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    nom_prenom = ((cible.get("prenom") or "") + " " + (cible.get("nom") or "")).strip()
    detail = "retiré : " + str(ancien["montant"]) + " € " + (ancien["mode"] or "") \
             + " du " + (ancien["date"] or "")[:10]
    if motif:
        detail += " — " + motif
    long = ("montant : " + str(ancien["montant"]) + " € → (vide)\n"
            "mode : " + (ancien["mode"] or "(vide)") + " → (vide)\n"
            "référence : " + (ancien["reference"] or "(vide)") + " → (vide)\n"
            "date de règlement : " + (ancien["date"] or "(vide)") + " → (vide)\n"
            "nouveau statut : " + _suivi.calculer_statut(cible)
            + (("\nmotif : " + motif) if motif else ""))
    try:
        journal.ecrire("Règlement corrigé", nom_prenom, detail, "", code, long)
    except Exception:
        pass
    facture = bool(cible.get("facture_le"))
    return jsonify({"ok": True, "nom": nom_prenom, "ancien": ancien,
                    "statut": _suivi.calculer_statut(cible),
                    "facture": facture,
                    "lien_facture": cible.get("lien_facture") or ""})
def _grilles_suivi(codes):
    """Les lignes de plusieurs sessions, DANS LA FORME DU CLASSEUR.

    Rend {code: [ligne1, ligne2, ...]} ou ligne1 est l'en-tete et chaque ligne
    est une liste de cinquante cases — exactement ce que renvoyait batchGet.

    LA FORME EST CONSERVEE VOLONTAIREMENT. Cinq ecrans parcourent ces grilles
    avec leurs propres boucles et leur propre numerotation ; changer la source
    ET la forme d'un meme mouvement, ce serait ne plus savoir lequel des deux a
    fauté quand un chiffre bouge. La source devient locale, rien d'autre.

    LES TROUS DE NUMEROTATION SONT CONSERVES : « _numero » sert de cle
    d'ecriture, et le tasser ferait ecrire sur la mauvaise personne.
    """
    import suivi as _suivi
    entete = [""] * len(_suivi.COL)
    for cle, i in _suivi.COL.items():
        entete[i] = cle
    out = {}
    for code in codes:
        try:
            lignes = _suivi.lire_lignes_de(code)
        except Exception:
            out[code] = []
            continue
        haut = max([l["_numero"] for l in lignes] or [1])
        grille = [[] for _ in range(haut)]
        grille[0] = entete
        for l in lignes:
            r = [""] * len(_suivi.COL)
            for cle, i in _suivi.COL.items():
                r[i] = l.get(cle) or ""
            grille[l["_numero"] - 1] = r
        out[code] = grille
    return out


def _lignes_onglet(S):
    """Les inscrits d'une session, ceux qui ont une adresse mail.

    NE LIT PLUS LE CLASSEUR. Cette fonction refaisait, en moins bien, ce que
    fait suivi.lire_lignes_de : meme forme, meme mode attache a la ligne. Deux
    lectures d'une meme table finissent par diverger — celle-ci retenait les
    lignes ayant un mail, l'autre celles ayant un horodateur. Le filtre sur le
    mail est conserve, c'est le seul ecart qui avait un sens.
    """
    import suivi as _suivi
    return [l for l in _suivi.lire_lignes_de(S.get("code"))
            if (l.get("mail") or "").strip()]
def _capacite(S, lignes):
    import suivi as _suivi
    actifs = [l for l in lignes
              if "recontact" not in (l.get("demande") or "").lower()
              and not l.get("annule_le") and not l.get("annulation_demandee_le")
              and _suivi.calculer_statut(l) != "File d'attente"]
    maxi = int(S.get("places_max") or 0)
    return len(actifs), maxi, maxi - len(actifs)
@app.route("/session/<code>/promotion/impact")
def impact_promotion(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import suivi as _suivi
    S = fiche_session(code)
    mail = (request.args.get("mail") or "").strip().lower()
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    occupees, maxi, libres = _capacite(S, lignes)
    attente = [l for l in lignes if _suivi.calculer_statut(l) == "File d'attente"]
    attente.sort(key=lambda l: l.get("file_attente_le") or "")
    cible = None
    position = 0
    for i, l in enumerate(attente, 1):
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            position = i
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Ce praticien n'est plus en file d'attente."})
    devant = [(l.get("prenom") or "") + " " + (l.get("nom") or "") for l in attente[:position - 1]]
    return jsonify({"ok": True, "nom": (cible.get("prenom") or "") + " " + (cible.get("nom") or ""),
                    "depuis": (cible.get("file_attente_le") or "")[:10],
                    "prevenu": bool(cible.get("mail_attente_le")),
                    "occupees": occupees, "maxi": maxi, "libres": libres,
                    "position": position, "devant": devant})
@app.route("/session/<code>/promotion", methods=["POST"])
def promouvoir_depuis_attente(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("mail")
    if _g:
        return jsonify({"ok": False, "message": _g})
    _v = _et_verrou(code, "promotion")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from connexion import service_sheets
    from datetime import datetime as dt
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    mail = (request.form.get("mail") or "").strip().lower()
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable dans l'onglet"})
    if cible.get("promu_le"):
        return jsonify({"ok": False, "message": "Ce praticien a deja ete promu."})
    if not cible.get("file_attente_le"):
        return jsonify({"ok": False, "message": "Ce praticien n'est pas en file d'attente."})
    quand = dt.now().strftime("%d/%m/%Y %H:%M")
    try:
        _suivi.ecrire(cible["_numero"], "promu_le", quand, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    nom_prenom = (cible.get("prenom") or "") + " " + (cible.get("nom") or "")
    try:
        journal.ecrire("Promotion depuis la file d'attente", nom_prenom, "", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "nom": nom_prenom, "quand": quand})
import os as _os
import json as _json
import time as _time
import threading as _threading
_AUTO_FICHIER = _os.path.join(DOSSIER, "auto.json")
_AUTO_ETAT = {"actif": False, "minutes": 5, "dernier": "", "en_cours": False,
              "resultat": "", "prochain": 0}
_AUTO_VERROU = _threading.Lock()
def _auto_charger():
    try:
        with open(_AUTO_FICHIER, encoding="utf-8") as f:
            d = _json.load(f)
        _AUTO_ETAT["actif"] = bool(d.get("actif"))
        _AUTO_ETAT["minutes"] = int(d.get("minutes") or 5)
    except Exception:
        pass
def _auto_ecrire():
    try:
        import fichiers
        fichiers.ecrire(_AUTO_FICHIER,
                        {"actif": _AUTO_ETAT["actif"], "minutes": _AUTO_ETAT["minutes"]})
    except Exception:
        pass
def _auto_executer():
    from datetime import datetime as _dt
    # Reglage "Autoriser les envois sans validation" (C4 : lu par personne).
    # Decoche, la synchro automatique ne part plus seule : le bouton
    # "Relancer le traitement" reste disponible, et c'est lui la validation.
    try:
        import parametres as _P
        if not _P.valeur("envois_auto_autorises"):
            _AUTO_ETAT["resultat"] = "suspendu par reglage"
            _AUTO_ETAT["dernier"] = _dt.now().strftime("%d/%m/%Y %H:%M")
            return False
    except Exception:
        pass
    if not _AUTO_VERROU.acquire(False):
        return False
    try:
        _AUTO_ETAT["en_cours"] = True
        # Delai de garde : connexion.py peut ouvrir un navigateur et attendre
        # indefiniment quand le jeton Google n'est plus rafraichissable. Sans
        # timeout, le verrou _AUTO_VERROU ne serait jamais relache et la
        # synchro automatique resterait morte jusqu'au redemarrage.
        r = subprocess.run([sys.executable, "dfm.py"], capture_output=True,
                           text=True, cwd=DOSSIER, timeout=900)
        _AUTO_ETAT["resultat"] = "ok" if r.returncode == 0 else "erreur"
    except subprocess.TimeoutExpired:
        _AUTO_ETAT["resultat"] = "delai depasse"
        _auto_signaler("boucle de synchronisation",
                       Exception("dfm.py n'a pas rendu la main en 15 minutes"))
    except Exception as e:
        _AUTO_ETAT["resultat"] = "erreur"
        _auto_signaler("boucle de synchronisation", e)
    finally:
        _AUTO_ETAT["dernier"] = _dt.now().strftime("%d/%m/%Y %H:%M")
        _AUTO_ETAT["en_cours"] = False
        _AUTO_VERROU.release()
    return True
_AUTO_DERNIERE_ERREUR = {"texte": "", "quand": 0}
def _auto_signaler(contexte, e, code=""):
    """Inscrit un echec d'envoi automatique au journal, sans le saturer :
    une erreur identique n'est reinscrite qu'au bout d'une heure."""
    texte = contexte + " : " + str(e)[:150]
    maintenant = _time.time()
    if (texte == _AUTO_DERNIERE_ERREUR["texte"]
            and maintenant - _AUTO_DERNIERE_ERREUR["quand"] < 3600):
        return
    _AUTO_DERNIERE_ERREUR["texte"] = texte
    _AUTO_DERNIERE_ERREUR["quand"] = maintenant
    try:
        journal.ecrire("Envoi automatique en échec", "", texte, "", code)
    except Exception:
        pass
def _auto_boucle():
    while True:
        _time.sleep(20)
        if not _AUTO_ETAT["actif"]:
            _AUTO_ETAT["prochain"] = 0
            continue
        try:
            _q_auto()
        except Exception as e:
            _auto_signaler("boucle des questionnaires", e)
        maintenant = _time.time()
        if not _AUTO_ETAT["prochain"]:
            _AUTO_ETAT["prochain"] = maintenant + _AUTO_ETAT["minutes"] * 60
            continue
        if maintenant >= _AUTO_ETAT["prochain"]:
            _auto_executer()
            _AUTO_ETAT["prochain"] = _time.time() + _AUTO_ETAT["minutes"] * 60
_auto_charger()
if _os.environ.get("WERKZEUG_RUN_MAIN") == "true" or _os.environ.get("DFM_AUTO") == "1":
    _threading.Thread(target=_auto_boucle, daemon=True).start()
@app.route("/auto/etat")
def auto_etat():
    reste = 0
    if _AUTO_ETAT["actif"] and _AUTO_ETAT["prochain"]:
        reste = max(0, int(_AUTO_ETAT["prochain"] - _time.time()))
    return jsonify({"actif": _AUTO_ETAT["actif"], "minutes": _AUTO_ETAT["minutes"],
                    "dernier": _AUTO_ETAT["dernier"], "en_cours": _AUTO_ETAT["en_cours"],
                    "resultat": _AUTO_ETAT["resultat"], "reste": reste})
@app.route("/auto/basculer", methods=["POST"])
def auto_basculer():
    import journal
    _AUTO_ETAT["actif"] = (request.form.get("actif") == "1")
    m = request.form.get("minutes")
    if m and str(m).isdigit():
        _AUTO_ETAT["minutes"] = max(3, min(240, int(m)))
    _AUTO_ETAT["prochain"] = 0
    _auto_ecrire()
    try:
        journal.ecrire("Synchronisation automatique " + ("activée" if _AUTO_ETAT["actif"] else "désactivée"),
                       "", "toutes les " + str(_AUTO_ETAT["minutes"]) + " min")
    except Exception:
        pass
    return jsonify({"ok": True, "actif": _AUTO_ETAT["actif"], "minutes": _AUTO_ETAT["minutes"]})
def _mail_annulation(S, ligne):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import base64
    prenom = ligne.get("prenom") or ""
    # La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
    # ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
    # au demarrage du script, meme quand aucun mail n'etait a envoyer.
    logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    corps_html = """
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 560px; margin: 0 auto; color: #2b2f3a; line-height: 1.6;">
  <div style="padding: 20px 0 4px;">
    <img src="cid:logo" alt="LOGO_ALT" style="height: 60px;">
  </div>
  <div style="height:1px; background:#e6e9f2; margin: 8px 0 24px;"></div>
  <p><strong>Bonjour PRENOM,</strong></p>
  <p>Nous confirmons l'<strong>annulation de ton inscription</strong> &agrave; la formation
  <strong>&laquo; TITRE &raquo;</strong> pr&eacute;vue le DATES.</p>
  <p>Ta place a &eacute;t&eacute; lib&eacute;r&eacute;e et aucune somme ne te sera r&eacute;clam&eacute;e.</p>
  <p>Nous esp&eacute;rons avoir le plaisir de t'accueillir sur une prochaine session. N'h&eacute;site pas &agrave; nous &eacute;crire
  pour conna&icirc;tre les dates &agrave; venir.</p>
  <p>En cas de question, r&eacute;ponds simplement &agrave; ce mail.</p>
  <p style="margin-top: 24px;">Bien &agrave; toi,<br>
  <strong>SIGNATURE</strong></p>
</div>
"""
    organisme = S.get("marque") or S.get("nom_organisme") or S.get("organisme") or ""
    formateur = S.get("signature_mail") or S.get("formateur") or ""
    corps_html = corps_html.replace("PRENOM", prenom)
    corps_html = corps_html.replace("TITRE", S.get("titre_complet") or S.get("nom_formation") or "")
    corps_html = corps_html.replace("DATES", S.get("date_texte") or "")
    corps_html = corps_html.replace("LOGO_ALT", organisme)
    corps_html = corps_html.replace("SIGNATURE", formateur + ", " + organisme)
    import mails as _mails
    corps_html = _mails.poser_logo(corps_html, logo_bytes)
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    import mails as _m_exp
    _exp = _m_exp.expediteur(S if "S" in dir() else None)
    if _exp:
        message["From"] = _exp
    message["Subject"] = "Annulation confirmée · " + (S.get("titre_complet") or S.get("nom_formation") or "")
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(corps_html, "html"))
    message.attach(corps)
    logo = MIMEImage(logo_bytes)
    logo.add_header("Content-ID", "<logo>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    message.attach(logo)
    # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
    # decide d'ou part le mail — deux entites, deux adresses.
    courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
@app.route("/session/<code>/annulation/impact")
def impact_annulation(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    mail = (request.args.get("mail") or "").strip().lower()
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    if cible.get("annule_le"):
        return jsonify({"ok": False, "message": "Cette inscription est deja annulee."})
    if not cible.get("annulation_demandee_le"):
        return jsonify({"ok": False, "message": "Aucune demande d'annulation en attente pour ce praticien."})
    return jsonify({"ok": True,
                    "nom": (cible.get("prenom") or "") + " " + (cible.get("nom") or ""),
                    "demande_le": (cible.get("annulation_demandee_le") or "")[:16],
                    "motif": cible.get("motif_annulation") or "",
                    "montant": cible.get("montant_recu") or "",
                    "mode": cible.get("mode_paiement") or "",
                    "paye_le": (cible.get("paiement_recu_le") or "")[:10],
                    "facture": bool(cible.get("facture_le")),
                    "signe": bool(cible.get("signe_le"))})
def _suivi_statut(ligne):
    """Le mode voyage avec la ligne depuis lire_lignes_de. A defaut —
    une ligne construite a la main — on retombe sur « individuel », qui est
    le comportement d'avant."""
    import suivi as _s
    try:
        return _s.calculer_statut(ligne, ligne.get("_mode") or "individuel")
    except Exception:
        return ligne.get("statut") or ""
def _mail_invitation(S, ligne):
    """Envoie le mail d'invitation, depuis le modele de la bibliotheque.
    Aucun script du pipeline ne l'appelle : il ne part que sur votre geste."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import base64
    import mails as _mails
    from connexion import service_drive
    modele = _mails.pour_formation(S.get("formation", ""), "invitation")
    ctx = _mails.contexte(S, ligne)
    rendu = _mails.rendre(modele, ctx)
    # Le logo est telecharge AVANT l'assemblage du corps : ses dimensions
    # reelles conditionnent la balise <img>. Son absence reste sans gravite,
    # poser_logo rend alors le HTML inchange.
    logo_bytes = None
    try:
        logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    except Exception:
        pass
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    import mails as _m_exp
    _exp = _m_exp.expediteur(S if "S" in dir() else None)
    if _exp:
        message["From"] = _exp
    message["Subject"] = rendu["objet"]
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(_mails.poser_logo(rendu["html"], logo_bytes), "html"))
    message.attach(corps)
    if logo_bytes:
        logo = MIMEImage(logo_bytes)
        logo.add_header("Content-ID", "<logo>")
        logo.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(logo)
    # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
    # decide d'ou part le mail — deux entites, deux adresses.
    courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
@app.route("/session/<code>/invitation/impact", methods=["POST"])
def impact_invitation(code):
    """Consequences de la mise en invitation. Ne modifie rien."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    mails = [m.strip().lower() for m in (request.form.get("mails") or "").split(",") if m.strip()]
    retirer = (request.form.get("retirer") or "") == "1"
    if not mails:
        return jsonify({"ok": False, "message": "Aucun praticien selectionne."})
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    par_mail = {(l.get("mail") or "").strip().lower(): l for l in lignes}
    concernes, ignores = [], []
    for m in mails:
        l = par_mail.get(m)
        if l is None:
            ignores.append({"mail": m, "motif": "introuvable"}); continue
        if l.get("annule_le"):
            ignores.append({"mail": m, "motif": "inscription annulee"}); continue
        deja = bool(l.get("invite_le"))
        if retirer and not deja:
            ignores.append({"mail": m, "motif": "n'est pas invite"}); continue
        if not retirer and deja:
            ignores.append({"mail": m, "motif": "deja invite"}); continue
        concernes.append({
            "mail": m,
            "nom": ((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip(),
            "statut": _suivi_statut(l),
            "paye": bool(l.get("paiement_recu_le")),
            "montant": l.get("montant_recu") or "",
            "facture": bool(l.get("facture_le")),
            "mail2": bool(l.get("mail2_envoye_le")),
            "invite_le": l.get("invite_le") or "",
        })
    from sessions import nombre as _nb
    tarif = _nb(S.get("tarif"), 0.0)
    return jsonify({"ok": True, "concernes": concernes, "ignores": ignores,
                    "nb": len(concernes), "retirer": retirer,
                    "montant_unitaire": tarif,
                    "nb_payes": len([c for c in concernes if c["paye"]]),
                    "nb_factures": len([c for c in concernes if c["facture"]]),
                    "nb_mail2": len([c for c in concernes if c["mail2"]])})
@app.route("/session/<code>/invitation", methods=["POST"])
def marquer_invitation(code):
    """Pose ou retire l'invitation. Le mail d'invitation ne part QUE d'ici :
    jamais depuis le pipeline. Il peut etre renvoye a la demande."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _v = _et_verrou(code, "mail")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from connexion import service_sheets
    from datetime import datetime as dt
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    mail = (request.form.get("mail") or "").strip().lower()
    retirer = (request.form.get("retirer") or "") == "1"
    envoyer = (request.form.get("envoyer") or "1") == "1"
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    if cible.get("annule_le"):
        return jsonify({"ok": False, "message": "Cette inscription est annulee."})
    quand = "" if retirer else dt.now().strftime("%d/%m/%Y %H:%M")
    etapes = []
    try:
        cible["invite_le"] = quand
        _suivi.ecrire_plusieurs(cible["_numero"],
                                {"invite_le": quand,
                                 "statut": _suivi.calculer_statut(cible)}, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    nom_prenom = ((cible.get("prenom") or "") + " " + (cible.get("nom") or "")).strip()
    etapes.append({"ok": True, "texte": ("Invitation retirée — retour au circuit normal"
                                         if retirer else "Marqué comme invité")})
    if not retirer and envoyer:
        try:
            _mail_invitation(S, cible)
            etapes.append({"ok": True, "texte": "Mail d'invitation envoyé à " + cible["mail"]})
        except Exception as e:
            etapes.append({"ok": False, "texte": "Mail non envoyé : " + str(e)[:120]})
    try:
        journal.ecrire("Invitation retirée" if retirer else "Apprenant invité",
                       nom_prenom, cible["mail"], "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "etapes": etapes, "nom": nom_prenom})
@app.route("/session/<code>/annulation/impact-groupe", methods=["POST"])
def impact_annulation_groupe(code):
    """Consequences d'une annulation decidee depuis la liste des inscrits.
    Ne modifie RIEN : sert a montrer avant de valider. La route /impact
    existante reste dediee aux demandes recues des praticiens (origine
    « demande ») et n'est pas touchee."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    mails = [m.strip().lower() for m in (request.form.get("mails") or "").split(",") if m.strip()]
    if not mails:
        return jsonify({"ok": False, "message": "Aucun praticien selectionne."})
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    par_mail = {(l.get("mail") or "").strip().lower(): l for l in lignes}
    concernes, ignores = [], []
    for m in mails:
        l = par_mail.get(m)
        if l is None:
            ignores.append({"mail": m, "motif": "introuvable dans l'onglet"})
            continue
        if l.get("annule_le"):
            ignores.append({"mail": m, "motif": "deja annulee"})
            continue
        docs = []
        if l.get("signe_le"):
            docs.append("convention signee")
        if l.get("facture_le"):
            docs.append("facture emise")
        if l.get("attestation_le"):
            docs.append("attestation generee")
        concernes.append({
            "mail": m,
            "nom": ((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip(),
            "statut": _suivi_statut(l),
            "paye": bool(l.get("paiement_recu_le")),
            "montant": l.get("montant_recu") or "",
            "mode": l.get("mode_paiement") or "",
            "paye_le": (l.get("paiement_recu_le") or "")[:10],
            "documents": docs,
            "demande_par_lui": bool(l.get("annulation_demandee_le")),
        })
    payes = [c for c in concernes if c["paye"]]
    return jsonify({"ok": True, "concernes": concernes, "ignores": ignores,
                    "nb": len(concernes), "nb_payes": len(payes),
                    "places_liberees": len(concernes)})
@app.route("/session/<code>/annulation", methods=["POST"])
def trancher_annulation(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _v = _et_verrou(code, "mail")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from datetime import datetime as dt
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    mail = (request.form.get("mail") or "").strip().lower()
    action = (request.form.get("action") or "").strip()
    # origine « demande » : le praticien a demande l'annulation via le lien de
    # ses mails — comportement historique, mail de confirmation envoye.
    # origine « decision » : annulation decidee depuis la liste des inscrits —
    # aucune demande prealable requise, et AUCUN mail au praticien.
    origine = (request.form.get("origine") or "demande").strip()
    if origine not in ("demande", "decision"):
        return jsonify({"ok": False, "message": "Origine inconnue"})
    if action not in ("valider", "refuser"):
        return jsonify({"ok": False, "message": "Action inconnue"})
    if origine == "decision" and action != "valider":
        return jsonify({"ok": False, "message": "Une annulation decidee ne peut pas etre refusee."})
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    if cible.get("annule_le"):
        return jsonify({"ok": False, "message": "Cette inscription est deja annulee."})
    if origine == "demande" and not cible.get("annulation_demandee_le"):
        return jsonify({"ok": False, "message": "Aucune demande d'annulation en attente."})
    onglet = S["onglet_suivi"]
    numero = cible["_numero"]
    nom_prenom = (cible.get("prenom") or "") + " " + (cible.get("nom") or "")
    etapes = []
    def poser(cle, valeur):
        _suivi.ecrire(numero, cle, valeur, code)
    if action == "valider":
        quand = dt.now().strftime("%d/%m/%Y %H:%M")
        # Motif : meme colonne que ceux venant des praticiens (AH). Leur origine
        # reste distinguable sans colonne supplementaire — annulation_demandee_le
        # est renseignee quand c'est le praticien qui a demande.
        motif = (request.form.get("motif") or "").strip()
        try:
            if motif and origine == "decision":
                poser("motif_annulation", motif)
                cible["motif_annulation"] = motif
            poser("annule_le", quand)
            cible["annule_le"] = quand
            poser("statut", _suivi.calculer_statut(cible))
            etapes.append({"ok": True, "texte": "Inscription annulee, la place est liberee"})
        except Exception as e:
            return jsonify({"ok": False, "message": "Ecriture dans le Sheet : " + str(e)})
        if origine == "demande":
            try:
                _mail_annulation(S, cible)
                etapes.append({"ok": True, "texte": "Mail de confirmation envoye a " + cible["mail"]})
            except Exception as e:
                etapes.append({"ok": False, "texte": "Mail non envoye : " + str(e)})
        else:
            # Annulation decidee : la communication au praticien reste manuelle.
            etapes.append({"ok": True, "texte": "Aucun mail envoye — communication a votre main"})
        if cible.get("paiement_recu_le"):
            etapes.append({"ok": False, "texte": "A FAIRE : rembourser " + str(cible.get("montant_recu") or "") + " EUR regles par " + str(cible.get("mode_paiement") or "")})
        if cible.get("facture_le"):
            etapes.append({"ok": False, "texte": "A FAIRE : etablir un avoir, une facture a ete emise"})
        try:
            journal.ecrire("Annulation validée", nom_prenom, cible.get("motif_annulation") or "", "", code)
        except Exception:
            pass
        return jsonify({"ok": True, "action": "valider", "nom": nom_prenom, "etapes": etapes})
    try:
        cible["annulation_demandee_le"] = ""
        cible["motif_annulation"] = ""
        poser("annulation_demandee_le", "")
        poser("motif_annulation", "")
        poser("statut", _suivi.calculer_statut(cible))
        etapes.append({"ok": True, "texte": "Demande retiree, le praticien reintegre le circuit"})
        etapes.append({"ok": True, "texte": "Nouveau statut : " + _suivi.calculer_statut(cible)})
    except Exception as e:
        return jsonify({"ok": False, "message": "Ecriture dans le Sheet : " + str(e)})
    try:
        journal.ecrire("Annulation refusée", nom_prenom, "", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "action": "refuser", "nom": nom_prenom, "etapes": etapes})
def _rel_historique(valeur):
    return [p.strip() for p in (valeur or "").split("|") if p.strip()]
def _rel_jours(valeur):
    from datetime import datetime as dt, date as dd
    try:
        d = dt.strptime((valeur or "")[:10], "%d/%m/%Y").date()
        return (dd.today() - d).days
    except Exception:
        return None
def _rel_type(ligne):
    import suivi as _suivi
    st = _suivi.calculer_statut(ligne)
    if st == "En attente signature":
        return "signature"
    if st == "En attente reglement":
        return "reglement"
    return ""
def _mail_relance(S, ligne, type_relance):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import base64
    import urllib.parse
    prenom = ligne.get("prenom") or ""
    nom_prenom = (prenom + " " + (ligne.get("nom") or "")).strip()
    marque = S.get("marque") or S.get("organisme") or ""
    signature = S.get("signature_mail") or S.get("formateur") or ""
    titulaire = S.get("organisme") or ""
    # Volontairement vide plutot qu'un repli sur des coordonnees bancaires
    # ecrites en dur : mieux vaut une ligne absente qu'un virement adresse au
    # mauvais compte (meme regle que numero_declaration, point C6).
    iban = S.get("iban") or ""
    bic = S.get("bic") or ""
    # La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
    # ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
    # au demarrage du script, meme quand aucun mail n'etait a envoyer.
    logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    params_annul = urllib.parse.urlencode({"marque": S.get("marque") or "",
                                           "contact": S.get("mail_contact") or "", "tel": S.get("telephone_contact") or "",
                                           "praticien": nom_prenom, "session": S["code"],
                                           "formation": S.get("titre_complet") or S["nom_formation"],
                                           "debut": S["date_debut"]})
    lien_annulation = S["url_signature"] + "/annulation.html?" + params_annul
    entete = ("\n<div style=\"font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 560px;"
              " margin: 0 auto; color: #2b2f3a; line-height: 1.6;\">\n"
              "  <div style=\"padding: 20px 0 4px;\">\n"
              "    <img src=\"cid:logo\" alt=\"" + marque + "\" style=\"height: 60px;\">\n"
              "  </div>\n"
              "  <div style=\"height:1px; background:#e6e9f2; margin: 8px 0 24px;\"></div>\n"
              "  <p><strong>Bonjour " + prenom + ",</strong></p>")
    pied = ("\n  <p>En cas de question ou de changement de programme, r&eacute;ponds simplement &agrave; ce mail.</p>\n"
            "  <p style=\"margin-top: 24px;\">Bonne journ&eacute;e,<br>\n"
            "  <strong>" + signature + ", " + marque + "</strong></p>\n"
            "  <p style=\"text-align:center; margin:26px 0 0; font-size:12px;\">\n"
            "    <a href=\"" + lien_annulation + "\" style=\"color:#8a90a2; text-decoration:underline;\">"
            "Je souhaite annuler mon inscription</a>\n  </p>\n</div>")
    titre = S.get("titre_complet") or S.get("nom_formation") or ""
    dates = S.get("date_texte") or ""
    if type_relance == "signature":
        params = urllib.parse.urlencode({"marque": S.get("marque") or "", "accroche": S.get("accroche_of") or "", "contact": S.get("mail_contact") or "", "tel": S.get("telephone_contact") or "", "praticien": nom_prenom, "formation": S.get("titre_complet") or S["nom_formation"], "session": S["code"]})
        lien = S["url_signature"] + "/?" + params
        sujet = "Convention a signer · " + (S.get("titre_complet") or S.get("nom_formation") or "")
        milieu = ("\n  <p>Ta demande d'inscription &agrave; la formation <strong>&laquo; " + titre + " &raquo;</strong>\n"
                  "  (" + dates + ") est bien enregistr&eacute;e, mais nous n'avons pas encore re&ccedil;u ta convention sign&eacute;e.</p>\n"
                  "  <p>Pour <strong>valider d&eacute;finitivement ton inscription</strong>, il te suffit de la signer en ligne, en un clic :</p>\n"
                  "  <div style=\"text-align:center; margin: 28px 0;\">\n"
                  "    <a href=\"" + lien + "\" style=\"display:inline-block; background:#0f9e6a; color:#fff;"
                  " padding:14px 32px; text-decoration:none; border-radius:8px; font-weight:600; font-size:15px;\">"
                  "Signer ma convention</a>\n  </div>\n")
    else:
        sujet = "Reglement en attente · " + (S.get("titre_complet") or S.get("nom_formation") or "")
        milieu = ("\n  <p>Ton inscription &agrave; la formation <strong>&laquo; " + titre + " &raquo;</strong>\n"
                  "  (" + dates + ") est confirm&eacute;e, mais nous n'avons pas encore re&ccedil;u ton r&egrave;glement.</p>\n"
                  "  <p>Le montant est de <strong>" + str(S.get("tarif") or "") + " &euro;</strong>, d&eacute;jeuners inclus.</p>\n"
                  "  <div style=\"text-align:center; margin: 24px 0;\">\n"
                  "    <a href=\"" + (S.get("stripe_lien") or "#") + "\" style=\"display:inline-block; background:#635BFF;"
                  " color:#fff; padding:14px 32px; text-decoration:none; border-radius:8px; font-weight:600; font-size:15px;\">"
                  "R&eacute;gler ma formation</a>\n"
                  "    <div style=\"font-size:12px; color:#8a90a2; margin-top:6px;\">(paiement par carte bancaire)</div>\n  </div>\n"
                  "  <p style=\"margin-bottom:8px;\"><strong>Ou par virement :</strong><br>\n"
                  "  <span style=\"font-size:13px; color:#5b6172;\">Motif : " + S["nom_formation"] + " + Nom Pr&eacute;nom</span></p>\n"
                  "  <table style=\"width:100%; border-collapse:collapse; font-size:13px; margin: 8px 0 20px;\">\n"
                  "    <tr><td style=\"padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb; font-weight:600; width:120px;\">Titulaire</td>\n"
                  "        <td style=\"padding:8px 10px; border:1px solid #e0e8fb;\">" + titulaire + "</td></tr>\n"
                  "    <tr><td style=\"padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb; font-weight:600;\">IBAN</td>\n"
                  "        <td style=\"padding:8px 10px; border:1px solid #e0e8fb;\">" + iban + "</td></tr>\n"
                  "    <tr><td style=\"padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb; font-weight:600;\">BIC</td>\n"
                  "        <td style=\"padding:8px 10px; border:1px solid #e0e8fb;\">" + bic + "</td></tr>\n  </table>\n"
                  "  <p style=\"font-size:12px; color:#8a90a2; font-style:italic;\">Si ton r&egrave;glement vient d'&ecirc;tre"
                  " effectu&eacute;, merci d'ignorer ce message.</p>")
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    import mails as _m_exp
    _exp = _m_exp.expediteur(S if "S" in dir() else None)
    if _exp:
        message["From"] = _exp
    message["Subject"] = sujet
    corps = MIMEMultipart("alternative")
    import mails as _mails
    corps.attach(MIMEText(_mails.poser_logo(entete + milieu + pied, logo_bytes), "html"))
    message.attach(corps)
    logo = MIMEImage(logo_bytes)
    logo.add_header("Content-ID", "<logo>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    message.attach(logo)
    # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
    # decide d'ou part le mail — deux entites, deux adresses.
    courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
@app.route("/session/<code>/relance/impact")
def impact_relance(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    mail = (request.args.get("mail") or "").strip().lower()
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    t = _rel_type(cible)
    if not t:
        return jsonify({"ok": False, "message": "Aucune relance necessaire : ce praticien n'attend ni signature ni reglement."})
    champ = "relance_signature_le" if t == "signature" else "relance_reglement_le"
    origine = cible.get("mail1_envoye_le") if t == "signature" else cible.get("mail2_envoye_le")
    passees = _rel_historique(cible.get(champ))
    dernier_j = _rel_jours(passees[-1]) if passees else None
    return jsonify({"ok": True, "type": t,
                    "nom": (cible.get("prenom") or "") + " " + (cible.get("nom") or ""),
                    "mail": cible.get("mail") or "",
                    "depuis": _rel_jours(origine),
                    "nb": len(passees),
                    "dates": [p[:10] for p in passees],
                    "dernier_jours": dernier_j,
                    "recent": bool(dernier_j is not None and dernier_j < 7)})
@app.route("/session/<code>/relance", methods=["POST"])
def envoyer_relance(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("mail")
    if _g:
        return jsonify({"ok": False, "message": _g})
    _v = _et_verrou(code, "mail")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from connexion import service_sheets
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    mail = (request.form.get("mail") or "").strip().lower()
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    t = _rel_type(cible)
    if not t:
        return jsonify({"ok": False, "message": "Aucune relance necessaire pour ce praticien."})
    champ = "relance_signature_le" if t == "signature" else "relance_reglement_le"
    passees = _rel_historique(cible.get(champ))
    try:
        _mail_relance(S, cible, t)
    except Exception as e:
        return jsonify({"ok": False, "message": "Mail non envoye : " + str(e)})
    nouveau = " | ".join(passees + [_suivi.aujourdhui()])
    try:
        _suivi.ecrire(cible["_numero"], champ, nouveau, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Mail parti mais historique non ecrit : " + str(e)})
    nom_prenom = (cible.get("prenom") or "") + " " + (cible.get("nom") or "")
    try:
        journal.ecrire("Relance " + t, nom_prenom, "relance n" + str(len(passees) + 1), "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "type": t, "nom": nom_prenom, "numero": len(passees) + 1})
def _fa_cibles(S, mails):
    lignes = _lignes_onglet(S)
    voulus = [m.strip().lower() for m in (mails or "").split(",") if m.strip()]
    return [l for l in lignes if (l.get("mail") or "").strip().lower() in voulus]
@app.route("/session/<code>/file-attente/impact", methods=["POST"])
def impact_file_attente(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    try:
        cibles = _fa_cibles(S, request.form.get("mails"))
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun praticien reconnu dans la selection."})
    gens = []
    for l in cibles:
        deja = bool(l.get("file_attente_le")) and not l.get("promu_le")
        gens.append({"mail": l.get("mail") or "",
                     "nom": (l.get("prenom") or "") + " " + (l.get("nom") or ""),
                     "signe": bool(l.get("signe_le")),
                     "paye": bool(l.get("paiement_recu_le")),
                     "montant": l.get("montant_recu") or "",
                     "facture": bool(l.get("facture_le")),
                     "annule": bool(l.get("annule_le")),
                     "deja": deja})
    return jsonify({"ok": True, "gens": gens})
@app.route("/session/<code>/file-attente", methods=["POST"])
def basculer_file_attente(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _v = _et_verrou(code, "promotion")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from datetime import datetime as dt
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    try:
        cibles = _fa_cibles(S, request.form.get("mails"))
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun praticien reconnu."})
    onglet = S["onglet_suivi"]
    quand = dt.now().strftime("%d/%m/%Y %H:%M")
    etapes = []
    donnees_maj = []
    faits = 0
    for l in cibles:
        nom_prenom = (l.get("prenom") or "") + " " + (l.get("nom") or "")
        if l.get("annule_le"):
            etapes.append({"ok": False, "texte": nom_prenom + " : inscription annulee, ignore"})
            continue
        if l.get("file_attente_le") and not l.get("promu_le"):
            etapes.append({"ok": False, "texte": nom_prenom + " : deja en file d'attente"})
            continue
        copie = dict(l)
        copie["file_attente_le"] = quand
        copie["promu_le"] = ""
        copie["mail_attente_le"] = ""
        donnees_maj.append((l["_numero"], {
            "file_attente_le": quand, "promu_le": "", "mail_attente_le": "",
            "statut": _suivi.calculer_statut(copie)}))
        etapes.append({"ok": True, "texte": nom_prenom + " : passe en file d'attente"})
        faits += 1
        try:
            journal.ecrire("Passage en file d'attente", nom_prenom, "", "", code)
        except Exception:
            pass
    if not donnees_maj:
        return jsonify({"ok": True, "faits": 0, "etapes": etapes})
    try:
        _suivi.ecrire_lignes(donnees_maj, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    return jsonify({"ok": True, "faits": faits, "etapes": etapes})
def _ri_origine(l):
    if l.get("annule_le"):
        return "annule"
    if l.get("annulation_demandee_le"):
        return "demande_annulation"
    if "recontact" in (l.get("demande") or "").lower():
        return "recontacter"
    return ""
@app.route("/session/<code>/reintegrer/impact")
def impact_reintegration(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    mail = (request.args.get("mail") or "").strip().lower()
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    origine = _ri_origine(cible)
    if not origine:
        return jsonify({"ok": False, "message": "Ce praticien figure deja parmi les inscrits actifs."})
    occupees, maxi, libres = _capacite(S, lignes)
    return jsonify({"ok": True,
                    "nom": (cible.get("prenom") or "") + " " + (cible.get("nom") or ""),
                    "origine": origine,
                    "motif": cible.get("motif_annulation") or "",
                    "demande": cible.get("demande") or "",
                    "occupees": occupees, "maxi": maxi, "libres": libres,
                    "en_attente": libres <= 0,
                    "paye": bool(cible.get("paiement_recu_le")),
                    "facture": bool(cible.get("facture_le"))})
@app.route("/session/<code>/reintegrer", methods=["POST"])
def reintegrer_praticien(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _v = _et_verrou(code, "promotion")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from connexion import service_sheets
    from datetime import datetime as dt
    import suivi as _suivi
    import journal
    S = fiche_session(code)
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    mail = (request.form.get("mail") or "").strip().lower()
    cible = None
    for l in lignes:
        if (l.get("mail") or "").strip().lower() == mail:
            cible = l
            break
    if cible is None:
        return jsonify({"ok": False, "message": "Praticien introuvable"})
    origine = _ri_origine(cible)
    if not origine:
        return jsonify({"ok": False, "message": "Ce praticien figure deja parmi les inscrits actifs."})
    occupees, maxi, libres = _capacite(S, lignes)
    quand = dt.now().strftime("%d/%m/%Y %H:%M")
    copie = dict(cible)
    ecritures = {"annule_le": "", "annulation_demandee_le": "", "motif_annulation": ""}
    etapes = []
    if origine == "annule":
        etapes.append({"ok": True, "texte": "Annulation effacee"})
    elif origine == "demande_annulation":
        etapes.append({"ok": True, "texte": "Demande d'annulation retiree"})
    if "recontact" in (cible.get("demande") or "").lower():
        ecritures["demande"] = "Validee depuis DFM le " + quand[:10]
        etapes.append({"ok": True, "texte": "Demande de renseignements convertie en inscription"})
    if libres > 0:
        ecritures["file_attente_le"] = ""
        ecritures["promu_le"] = ""
        ecritures["mail_attente_le"] = ""
        etapes.append({"ok": True, "texte": "Place disponible : rejoint les inscrits (" + str(occupees + 1) + "/" + str(maxi) + ")"})
    else:
        ecritures["file_attente_le"] = quand
        ecritures["promu_le"] = ""
        etapes.append({"ok": False, "texte": "Capacite atteinte (" + str(occupees) + "/" + str(maxi) + ") : place en file d'attente"})
    copie.update(ecritures)
    try:
        _suivi.ecrire_plusieurs(
            cible["_numero"],
            dict(ecritures, statut=_suivi.calculer_statut(copie)), code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    nom_prenom = (cible.get("prenom") or "") + " " + (cible.get("nom") or "")
    statut = _suivi.calculer_statut(copie)
    etapes.append({"ok": True, "texte": "Nouveau statut : " + statut})
    try:
        journal.ecrire("Reintegration", nom_prenom, statut, "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "nom": nom_prenom, "statut": statut,
                    "en_attente": libres <= 0, "etapes": etapes})
def _rg_iso(valeur):
    v = (valeur or "")[:10]
    p = v.split("/")
    if len(p) == 3 and len(p[2]) == 4:
        return p[2] + "-" + p[1] + "-" + p[0]
    return ""
def _rg_numeros(liens):
    """Le numero de facture derriere chaque lien.

    L'INDEX LOCAL D'ABORD, le Drive seulement pour les factures d'avant la
    couche « documents ». Cet ecran demandait le NOM de chaque fichier au
    Drive, un appel par facture : la page tombait entierement des que Google
    ne repondait pas, alors que les numeros sont sur le disque.
    """
    import re as _r
    trouves = {}
    if not liens:
        return trouves
    try:
        import documents as _doc
        import fichiers as _f
        index = _f.lire(_doc._INDEX, {}) or {}
    except Exception:
        index = {}
    # L'index va de la reference vers le lien ; ici on a le lien.
    par_lien = {}
    for ref, v in index.items():
        if (v or {}).get("lien"):
            par_lien[v["lien"]] = ref.rsplit("/", 1)[-1]

    manquants = []
    for lien in liens:
        nom = par_lien.get(lien or "")
        if nom:
            num = _r.search(r"[A-Za-z]{0,5}[-_ ]?\d{4}[-_]\d{2,4}", nom)
            trouves[lien] = num.group(0).strip() if num else nom.rsplit(".", 1)[0][:30]
        else:
            manquants.append(lien)

    if not manquants:
        return trouves
    try:
        from connexion import service_drive
        drive = service_drive()
    except Exception:
        return trouves
    for lien in manquants:
        m = _r.search(r"/d/([a-zA-Z0-9_-]{20,})", lien or "")
        if not m:
            continue
        try:
            nom = drive.files().get(fileId=m.group(1), fields="name").execute().get("name", "")
        except Exception:
            continue
        num = _r.search(r"[A-Za-z]{0,5}[-_ ]?\d{4}[-_]\d{2,4}", nom)
        trouves[lien] = num.group(0).strip() if num else nom.rsplit(".", 1)[0][:30]
    return trouves
def _rg_age(valeur):
    from datetime import datetime as dt, date as dd
    try:
        return (dd.today() - dt.strptime((valeur or "")[:10], "%d/%m/%Y").date()).days
    except Exception:
        return None
@app.route("/reglements")
def page_reglements():
    import sessions as _sessions
    from connexion import service_sheets
    import suivi as _suivi
    from datetime import datetime as dt
    PALETTE = ["#4f7ef8", "#7c5bf7", "#0f9e6a", "#d4890a", "#d03b3b"]
    fiches = {code: fiche_session(code) for code in _sessions.visibles()}
    brut = _grilles_suivi(list(fiches))
    formations = {}
    lignes = []
    for i, code in enumerate(_sessions.visibles()):
        S = fiches[code]
        couleur = PALETTE[i % len(PALETTE)]
        nomf = S.get("nom_formation") or ""
        formations.setdefault(nomf, 0)
        grille = brut.get(code, [])
        try:
            debut = dt.strptime(S.get("date_debut") or "", "%Y-%m-%d")
        except Exception:
            debut = None
        for n, r in enumerate(grille[1:], 2):
            if not r or len(r) <= _suivi.COL["mail"]:
                continue
            d = {}
            for cle, idx in _suivi.COL.items():
                d[cle] = (r[idx] if len(r) > idx else "") or ""
            if not d.get("mail"):
                continue
            if d.get("annule_le"):
                continue
            if "recontact" in (d.get("demande") or "").lower():
                continue
            if d.get("file_attente_le") and not d.get("promu_le"):
                continue
            try:
                du = float(str(d.get("montant_du") or S.get("tarif") or 0).replace(",", ".") or 0)
            except Exception:
                du = 0
            try:
                recu = float(str(d.get("montant_recu") or 0).replace(",", ".") or 0)
            except Exception:
                recu = 0
            paye = bool(d.get("paiement_recu_le"))
            # Un invite ne doit apparaitre ni comme impaye, ni comme recette :
            # son du est nul et il n'est pas relancable.
            invite = bool(d.get("invite_le"))
            if invite:
                du = 0
            formations[nomf] = formations.get(nomf, 0) + 1
            lignes.append({
                "invite": invite,
                "nom": (d.get("nom") or "").upper() + " " + (d.get("prenom") or ""),
                "mail": d.get("mail") or "",
                "formation": nomf,
                "session": code,
                "session_texte": S.get("date_texte") or "",
                "couleur": couleur,
                "du": du,
                "recu": recu if paye else 0,
                "paye": paye,
                "mode": d.get("mode_paiement") or "",
                "reference": d.get("reference_paiement") or "",
                "date_paiement": (d.get("paiement_recu_le") or "")[:10],
                "paiement_iso": _rg_iso(d.get("paiement_recu_le")),
                "lien_facture": d.get("lien_facture") or "",
                "facture_le": (d.get("facture_le") or "")[:10],
                "jours": _rg_age(d.get("mail2_envoye_le") or d.get("mail1_envoye_le")),
                "relancable": bool(d.get("mail2_envoye_le")) and not paye and not invite,
                "annee": debut.year if debut else 0,
                "debut": S.get("date_debut") or "",
            })
    lignes.sort(key=lambda x: (x["debut"], x["nom"]), reverse=True)
    numeros = _rg_numeros([x["lien_facture"] for x in lignes if x["lien_facture"]])
    for x in lignes:
        x["numero_facture"] = numeros.get(x["lien_facture"], "")

    attendu = sum(x["du"] for x in lignes)
    encaisse = sum(x["recu"] for x in lignes)
    nb_payes = len([x for x in lignes if x["paye"]])
    nb_invites = len([x for x in lignes if x["invite"]])
    nb_factures = len([x for x in lignes if x["facture_le"]])
    annees = sorted({x["annee"] for x in lignes if x["annee"]}, reverse=True)
    return render_template("reglements.html", lignes=lignes, attendu=attendu,
                           encaisse=encaisse, restant=attendu - encaisse,
                           nb_total=len(lignes), nb_payes=nb_payes,
                           nb_attente=len(lignes) - nb_payes - nb_invites,
                           nb_invites=nb_invites, nb_factures=nb_factures,
                           formations=sorted(formations.items()), annees=annees,
                           annee_courante=dt.now().year, periode_defaut=_par_periode())
def _gr_mail(S, ligne, action, pdf_bytes, logo_bytes):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from email.mime.application import MIMEApplication
    import base64
    prenom = ligne.get("prenom") or ""
    nom_prenom = (prenom + " " + (ligne.get("nom") or "")).strip()
    marque = S.get("marque") or S.get("organisme") or ""
    signature = S.get("signature_mail") or S.get("formateur") or ""
    titre = S.get("titre_complet") or S.get("nom_formation") or ""
    dates = S.get("date_texte") or ""
    if action == "facture":
        sujet = "Votre facture · " + (S.get("titre_complet") or S.get("nom_formation") or "")
        fichier = "Facture - " + nom_prenom + ".pdf"
        milieu = ("  <p>Nous avons bien re&ccedil;u ton r&egrave;glement pour la formation\n"
                  "  <strong>&laquo; " + titre + " &raquo;</strong> &mdash; merci !</p>\n"
                  "  <p>Tu trouveras ci-joint ta <strong>facture acquitt&eacute;e</strong>.</p>\n"
                  "  <p>Nous te donnons rendez-vous le <strong>" + dates + "</strong>.</p>\n")
    else:
        sujet = "Votre convention signee · " + (S.get("titre_complet") or S.get("nom_formation") or "")
        fichier = "Convention - " + nom_prenom + ".pdf"
        milieu = ("  <p>Tu trouveras ci-joint ta <strong>convention de formation sign&eacute;e</strong> pour\n"
                  "  <strong>&laquo; " + titre + " &raquo;</strong>.</p>\n"
                  "  <p>Nous te donnons rendez-vous le <strong>" + dates + "</strong>.</p>\n")
    html = ("<div style=\"font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 560px;"
            " margin: 0 auto; color: #2b2f3a; line-height: 1.6;\">\n"
            "  <div style=\"padding: 20px 0 4px;\">\n"
            "    <img src=\"cid:logo\" alt=\"" + marque + "\" style=\"height: 60px;\">\n  </div>\n"
            "  <div style=\"height:1px; background:#e6e9f2; margin: 8px 0 24px;\"></div>\n"
            "  <p><strong>Bonjour " + prenom + ",</strong></p>\n" + milieu +
            "  <p>En cas de question, r&eacute;ponds simplement &agrave; ce mail.</p>\n"
            "  <p style=\"margin-top: 24px;\">Bien &agrave; toi,<br>\n"
            "  <strong>" + signature + ", " + marque + "</strong></p>\n</div>")
    import mails as _mails
    html = _mails.poser_logo(html, logo_bytes)
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    import mails as _m_exp
    _exp = _m_exp.expediteur(S if "S" in dir() else None)
    if _exp:
        message["From"] = _exp
    message["Subject"] = sujet
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(html, "html"))
    message.attach(corps)
    logo = MIMEImage(logo_bytes)
    logo.add_header("Content-ID", "<logo>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    message.attach(logo)
    pj = MIMEApplication(pdf_bytes, _subtype="pdf")
    pj.add_header("Content-Disposition", "attachment", filename=fichier)
    message.attach(pj)
    # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
    # decide d'ou part le mail — deux entites, deux adresses.
    courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
@app.route("/session/<code>/groupe/impact", methods=["POST"])
def impact_groupe(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    action = (request.form.get("action") or "").strip()
    if action not in ("facture", "convention"):
        return jsonify({"ok": False, "message": "Action inconnue"})
    try:
        cibles = _fa_cibles(S, request.form.get("mails"))
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun praticien reconnu."})
    champ = "lien_facture" if action == "facture" else "lien_pdf"
    prets, sans = [], []
    for l in cibles:
        nom = (l.get("prenom") or "") + " " + (l.get("nom") or "")
        if l.get(champ) and "/d/" in l.get(champ):
            prets.append({"nom": nom, "mail": l.get("mail") or ""})
        else:
            sans.append({"nom": nom, "mail": l.get("mail") or ""})
    return jsonify({"ok": True, "action": action, "prets": prets, "sans": sans})
@app.route("/session/<code>/groupe", methods=["POST"])
def executer_groupe(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("mail")
    if _g:
        return jsonify({"ok": False, "message": _g})
    _v = _et_verrou(code, "mail")
    if _v:
        return jsonify({"ok": False, "message": _v})
    import documents
    import journal
    S = fiche_session(code)
    action = (request.form.get("action") or "").strip()
    if action not in ("facture", "convention"):
        return jsonify({"ok": False, "message": "Action inconnue"})
    try:
        cibles = _fa_cibles(S, request.form.get("mails"))
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun praticien reconnu."})
    champ = "lien_facture" if action == "facture" else "lien_pdf"
    try:
        logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    except Exception as e:
        return jsonify({"ok": False, "message": "Logo introuvable : " + str(e)})
    etapes = []
    envoyes = 0
    for l in cibles:
        nom = ((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip()
        lien = l.get(champ) or ""
        if "/d/" not in lien:
            etapes.append({"ok": False, "texte": nom + " : aucun document disponible, ignore"})
            continue
        # LA COPIE LOCALE D'ABORD, le Drive ensuite : documents.depuis_lien()
        # retrouve la reference a partir de l'URL. Ce renvoi groupe repart donc
        # du disque, sans un appel reseau par praticien.
        pdf_bytes = documents.depuis_lien(lien)
        if not pdf_bytes:
            etapes.append({"ok": False, "texte": nom + " : document illisible"})
            continue
        try:
            _gr_mail(S, l, action, pdf_bytes, logo_bytes)
            etapes.append({"ok": True, "texte": nom + " : envoye a " + (l.get("mail") or "")})
            envoyes += 1
        except Exception as e:
            etapes.append({"ok": False, "texte": nom + " : echec (" + str(e)[:70] + ")"})
    try:
        journal.ecrire("Renvoi groupe " + action, "", str(envoyes) + " envoi(s)", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "envoyes": envoyes, "etapes": etapes})
def _sb(chemin, methode="GET", corps=None, prefer=None):
    import json as _json
    import urllib.request
    import reseau
    from config import SUPABASE_URL, SUPABASE_KEY
    url = SUPABASE_URL.rstrip("/") + "/rest/v1/" + chemin
    entetes = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY,
               "Content-Type": "application/json"}
    if prefer:
        entetes["Prefer"] = prefer
    donnees = _json.dumps(corps).encode("utf-8") if corps is not None else None
    requete = urllib.request.Request(url, data=donnees, headers=entetes, method=methode)
    with urllib.request.urlopen(requete, timeout=30, context=reseau.contexte()) as r:
        texte = r.read().decode("utf-8")
    return _json.loads(texte) if texte.strip() else []
def _q_actifs(S):
    sortie = []
    for l in _lignes_onglet(S):
        if l.get("annule_le"):
            continue
        if "recontact" in (l.get("demande") or "").lower():
            continue
        if l.get("file_attente_le") and not l.get("promu_le"):
            continue
        sortie.append(l)
    return sortie
def _q_public(fcode):
    import questionnaires as Q
    ev = Q.pour_formation(fcode)
    if not ev:
        return []
    return [{"id": q["id"], "type": q["type"], "enonce": q["enonce"],
             "propositions": q.get("propositions", [])} for q in ev["questions"]]
@app.route("/session/<code>/questionnaires/etat")
def etat_questionnaires(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import questionnaires as Q
    S = fiche_session(code)
    fcode = SESSIONS[code].get("formation") or ""
    ev = Q.pour_formation(fcode)
    publie = None
    try:
        r = _sb("Sessions_publiques?session_code=eq." + code + "&select=participants,questions,ouvert,maj")
        publie = r[0] if r else None
    except Exception as e:
        return jsonify({"ok": False, "message": "Supabase injoignable : " + str(e)})
    comptes = {"init": 0, "fin": 0, "satisfaction": 0, "froid": 0}
    try:
        for x in _sb("Questionnaires?session_code=eq." + code + "&select=type"):
            t = x.get("type")
            if t in comptes:
                comptes[t] += 1
    except Exception:
        pass
    return jsonify({"ok": True, "code": code,
                    "formation": S.get("nom_formation") or "",
                    "titre": S.get("titre_complet") or "",
                    "questionnaire_dispo": bool(ev),
                    "nb_questions": len(ev["questions"]) if ev else 0,
                    "seuil": (ev or {}).get("seuil", Q.seuil_defaut()),
                    "publie": bool(publie),
                    "maj": (publie or {}).get("maj", ""),
                    "nb_participants": len((publie or {}).get("participants") or []),
                    "nb_inscrits": len(_q_actifs(S)),
                    "ouvert": (publie or {}).get("ouvert") or {},
                    "reponses": comptes,
                    "lien": (S.get("url_signature") or "") + "/questionnaire.html?s=" + code})
@app.route("/session/<code>/questionnaires/publier", methods=["POST"])
def publier_questionnaires(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import questionnaires as Q
    import journal
    import random
    S = fiche_session(code)
    fcode = SESSIONS[code].get("formation") or ""
    questions = _q_public(fcode)
    if not questions:
        return jsonify({"ok": False, "message": "Aucun questionnaire d'evaluation defini pour la formation " + fcode})
    random.shuffle(questions)
    gens = []
    for l in _q_actifs(S):
        gens.append({"nom": ((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip(),
                     "mail": (l.get("mail") or "").strip().lower()})
    ouvert = {"init": False, "fin": False, "satisfaction": False}
    try:
        r = _sb("Sessions_publiques?session_code=eq." + code + "&select=ouvert")
        if r and r[0].get("ouvert"):
            ouvert = r[0]["ouvert"]
    except Exception:
        pass
    corps = {"session_code": code,
             "formation": S.get("nom_formation") or "",
             "titre": S.get("titre_complet") or "",
             "date_texte": S.get("date_texte") or "",
             "participants": gens,
             "questions": questions,
             "satisfaction": Q.satisfaction_pour(fcode),
             "froid": Q.froid_pour(fcode),
             "ouvert": ouvert}
    try:
        _sb("Sessions_publiques", "POST", [corps], "resolution=merge-duplicates")
    except Exception as e:
        return jsonify({"ok": False, "message": "Publication impossible : " + str(e)})
    # Instantane local des modeles complets, cle de correction comprise.
    # L'echec n'est deliberement PAS avale : sans instantane, la session ne
    # pourra plus etre corrigee avec le modele qui a reellement servi, et la
    # piste d'audit manque. L'utilisateur doit l'apprendre tout de suite.
    fige_ok, fige_erreur = True, ""
    try:
        Q.figer(code, fcode, [q["id"] for q in questions])
    except Exception as e:
        fige_ok, fige_erreur = False, str(e)[:160]
    try:
        journal.ecrire("Questionnaires préparés", "", str(len(gens)) + " participant(s), " + str(len(questions)) + " questions", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "participants": len(gens), "questions": len(questions),
                    "fige": fige_ok, "fige_erreur": fige_erreur})
@app.route("/session/<code>/questionnaires/ouvrir", methods=["POST"])
def ouvrir_questionnaire(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import journal
    quoi = (request.form.get("type") or "").strip()
    etat = (request.form.get("etat") or "") == "1"
    if quoi not in ("init", "fin", "satisfaction"):
        return jsonify({"ok": False, "message": "Type inconnu"})
    try:
        r = _sb("Sessions_publiques?session_code=eq." + code + "&select=ouvert")
        if not r:
            return jsonify({"ok": False, "message": "Publie d'abord les questionnaires de cette session."})
        ouvert = r[0].get("ouvert") or {}
        ouvert[quoi] = etat
        _sb("Sessions_publiques?session_code=eq." + code, "PATCH", {"ouvert": ouvert})
    except Exception as e:
        return jsonify({"ok": False, "message": "Supabase : " + str(e)})
    try:
        # `code` atterrissait en position "detail" : l'evenement s'affichait avec le
        # code de session en guise de texte, rattache a la session active (C2).
        journal.ecrire("Questionnaire " + quoi + (" ouvert" if etat else " fermé"), "", "", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "ouvert": ouvert})
@app.route("/session/<code>/questionnaires/relever", methods=["POST"])
def relever_questionnaires(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    from connexion import service_sheets
    from datetime import datetime as dt
    import suivi as _suivi
    import questionnaires as Q
    import journal
    S = fiche_session(code)
    fcode = SESSIONS[code].get("formation") or ""
    try:
        recues = _sb("Questionnaires?session_code=eq." + code + "&select=mail,nom,type,reponses,created_at")
    except Exception as e:
        return jsonify({"ok": False, "message": "Supabase injoignable : " + str(e)})
    if not recues:
        return jsonify({"ok": True, "traites": 0, "etapes": [{"ok": True, "texte": "Aucune reponse a relever"}]})
    lignes = _lignes_onglet(S)
    par_mail = {}
    for l in lignes:
        par_mail[(l.get("mail") or "").strip().lower()] = l
    CHAMPS = {"init": ("eval_init_le", "score_init"),
              "fin": ("eval_fin_le", "score_fin"),
              "satisfaction": ("satisfaction_le", "note_satisfaction"),
              "froid": ("froid_le", "note_froid")}
    donnees_maj = []
    etapes = []
    traites = 0
    for r in recues:
        mail = (r.get("mail") or "").strip().lower()
        quoi = r.get("type") or ""
        ligne = par_mail.get(mail)
        if quoi not in CHAMPS:
            continue
        if not ligne:
            etapes.append({"ok": False, "texte": mail + " : introuvable dans l'onglet, reponse ignoree"})
            continue
        champ_date, champ_score = CHAMPS[quoi]
        if ligne.get(champ_date):
            continue
        reponses = r.get("reponses") or {}
        quand = (r.get("created_at") or "")[:10]
        if quand and "-" in quand:
            p = quand.split("-")
            quand = p[2] + "/" + p[1] + "/" + p[0]
        else:
            quand = dt.now().strftime("%d/%m/%Y")
        if quoi in ("satisfaction", "froid"):
            notes = []
            modele = Q.modele_session(code, fcode, quoi)
            for n in modele["notes"]:
                v = reponses.get(n["id"])
                try:
                    notes.append(float(v))
                except Exception:
                    pass
            valeur = round(sum(notes) / len(notes), 2) if notes else ""
        else:
            res = Q.corriger_avec(Q.modele_session(code, fcode), reponses)
            valeur = res["score"] if res else ""
        donnees_maj.append((ligne["_numero"],
                            {champ_date: quand, champ_score: valeur}))
        etapes.append({"ok": True, "texte": (r.get("nom") or mail) + " \u2014 " + quoi + " : " + str(valeur)})
        traites += 1
        try:
            import journal as _j
            _LIB = {"init": "Évaluation d'entrée complétée",
                    "fin": "Évaluation de sortie complétée",
                    "satisfaction": "Questionnaire de satisfaction complété",
                    "froid": "Évaluation à froid complétée"}
            _det = (str(valeur) + " %") if quoi in ("init", "fin") else (str(valeur) + "/5")
            _j.ecrire(_LIB.get(quoi, quoi), r.get("nom") or mail, _det, "", code)
        except Exception:
            pass
    if donnees_maj:
        try:
            _suivi.ecrire_lignes(donnees_maj, code)
        except Exception as e:
            return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    if not traites:
        etapes.append({"ok": True, "texte": "Rien de nouveau : toutes les reponses etaient deja relevees"})
    try:
        journal.ecrire("Réponses relevées", "", str(traites) + " questionnaire(s)", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "traites": traites, "etapes": etapes})
# Releve automatique, toutes sessions. Appelee par base.html a l'ouverture des
# ecrans concernes (A6 : la route etait appelee mais n'existait pas, et le
# .catch() vide du gabarit avalait le 404 — la releve automatique n'a donc
# jamais fonctionne).
_RELEVE_TOUT = {"quand": 0.0}
@app.route("/questionnaires/relever-tout", methods=["POST"])
def relever_tout():
    import time as _t
    import parametres as _P
    try:
        heures = float(_P.valeur("releve_heures") or 6)
    except Exception:
        heures = 6.0
    # Sans limite de frequence, chaque ouverture d'ecran declencherait une
    # requete Supabase par session. Le bouton manuel d'une session, lui, n'est
    # jamais bride : il appelle directement /session/<code>/questionnaires/relever.
    if _t.time() - _RELEVE_TOUT["quand"] < heures * 3600:
        return jsonify({"ok": True, "traites": 0, "saute": True,
                        "message": "Releve deja faite il y a moins de "
                                   + str(int(heures)) + " h"})
    _RELEVE_TOUT["quand"] = _t.time()
    total, details, soucis = 0, [], []
    for _code in list(SESSIONS):
        try:
            rep = relever_questionnaires(_code).get_json() or {}
        except Exception as e:
            soucis.append({"session": _code, "message": str(e)[:120]})
            continue
        if not rep.get("ok"):
            soucis.append({"session": _code, "message": rep.get("message", "")[:120]})
            continue
        n = rep.get("traites") or 0
        total += n
        if n:
            details.append({"session": _code, "traites": n})
    return jsonify({"ok": True, "traites": total, "sessions": details,
                    "soucis": soucis})
_Q_FICHIER = _os.path.join(DOSSIER, "questionnaires_etat.json")
_Q_TYPES = ("init", "fin", "satisfaction", "froid")
_Q_NOMS = {"init": "Évaluation d'entrée", "fin": "Évaluation de sortie",
           "satisfaction": "Questionnaire de satisfaction",
           "froid": "Évaluation à froid, 3 mois après"}
def _q_lire():
    try:
        with open(_Q_FICHIER, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}
def _q_ecrire(tout):
    try:
        import fichiers
        fichiers.ecrire(_Q_FICHIER, tout)
    except Exception:
        pass
def _q_plus_tard(date_iso, jours):
    from datetime import datetime as dt, timedelta
    try:
        return (dt.strptime(date_iso, "%Y-%m-%d") + timedelta(days=jours)).strftime("%Y-%m-%d")
    except Exception:
        return date_iso or ""
def _q_reglages(code):
    S = fiche_session(code)
    fin = S.get("date_fin") or S.get("date_debut") or ""
    defauts = {"init": {"date": S.get("date_debut") or "", "heure": _par("heure_init", "08:30")},
               "fin": {"date": fin, "heure": _par("heure_fin", "16:00")},
               "satisfaction": {"date": fin, "heure": _par("heure_satisfaction", "16:15")},
               "froid": {"date": _q_plus_tard(fin, int(_par("delai_froid", 90))), "heure": "09:00"}}
    d = _q_lire().get(code, {})
    plan = d.get("planning") or {}
    for t in _Q_TYPES:
        if isinstance(plan.get(t), dict):
            defauts[t].update(plan[t])
    return defauts, (d.get("auto") or {}), (d.get("envois") or {})
def _q_enregistrer(code, planning=None, auto=None, envoi=None):
    tout = _q_lire()
    d = tout.get(code) or {}
    if planning is not None:
        d["planning"] = planning
    if auto is not None:
        d["auto"] = auto
    if envoi:
        envois = d.get("envois") or {}
        envois[envoi[0]] = envoi[1]
        d["envois"] = envois
    tout[code] = d
    _q_ecrire(tout)
def _q_moment(reglage):
    from datetime import datetime as dt
    try:
        return dt.strptime((reglage.get("date") or "") + " " + (reglage.get("heure") or "00:00"),
                           "%Y-%m-%d %H:%M")
    except Exception:
        return None
def _q_repondants(code):
    par_type = {"init": [], "fin": [], "satisfaction": [], "froid": []}
    try:
        for x in _sb("Questionnaires?session_code=eq." + code + "&select=mail,type"):
            t = x.get("type")
            if t in par_type:
                par_type[t].append((x.get("mail") or "").strip().lower())
    except Exception:
        pass
    return par_type
def _q_mail_lien(S, code, quoi, mail):
    import urllib.parse
    base = (S.get("url_signature") or "") + "/questionnaire.html?s=" + code + "&type=" + quoi
    return base + "&m=" + urllib.parse.quote(mail)
def _q_envoyer_mails(code, quoi, cibles):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import base64
    S = fiche_session(code)
    marque = S.get("marque") or S.get("organisme") or ""
    signature = S.get("signature_mail") or S.get("formateur") or ""
    # La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
    # ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
    # au demarrage du script, meme quand aucun mail n'etait a envoyer.
    logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    TEXTES = {
        "init": ("Evaluation d'entree",
                 "Avant d'entrer dans le vif du sujet, voici un court questionnaire de positionnement. "
                 "Il n'est pas not&eacute; et ne conditionne rien : il nous servira &agrave; mesurer votre progression &agrave; la fin de la journ&eacute;e.",
                 "R&eacute;pondre maintenant", "6 minutes environ"),
        "fin": ("Evaluation de fin de formation",
                "Voici les m&ecirc;mes questions qu'&agrave; votre arriv&eacute;e. En comparant les deux, vous verrez pr&eacute;cis&eacute;ment "
                "ce que la journ&eacute;e vous a apport&eacute;. Vous recevrez ensuite votre score et le corrig&eacute; comment&eacute;.",
                "R&eacute;pondre maintenant", "6 minutes environ"),
        "froid": ("Trois mois apres : et dans votre pratique ?",
                "Vous avez suivi cette formation il y a trois mois. Quelques questions rapides pour savoir ce qui, "
                "concr&egrave;tement, a chang&eacute; dans votre pratique. C'est ce retour qui nous permet de faire &eacute;voluer nos programmes.",
                "R&eacute;pondre en 2 minutes", "2 minutes environ"),
        "satisfaction": ("Votre avis sur la formation",
                "Votre retour nous aide &agrave; am&eacute;liorer nos formations. Les r&eacute;ponses ne sont exploit&eacute;es "
                "que de fa&ccedil;on globale, jamais nominativement.",
                "Donner mon avis", "3 minutes environ"),
    }
    sujet_base, corps_txt, bouton, duree = TEXTES.get(quoi, TEXTES["init"])
    resultats = []
    for personne in cibles:
        mail = (personne.get("mail") or "").strip()
        if not mail:
            continue
        prenom = (personne.get("nom") or "").split(" ")[0]
        lien = _q_mail_lien(S, code, quoi, mail)
        html = ("<div style=\"font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 560px;"
                " margin: 0 auto; color: #2b2f3a; line-height: 1.6;\">\n"
                "  <div style=\"padding: 20px 0 4px;\">"
                "<img src=\"cid:logo\" alt=\"" + marque + "\" style=\"height: 60px;\"></div>\n"
                "  <div style=\"height:1px; background:#e6e9f2; margin: 8px 0 24px;\"></div>\n"
                "  <p><strong>Bonjour " + prenom + ",</strong></p>\n"
                "  <p>" + corps_txt + "</p>\n"
                "  <div style=\"text-align:center; margin: 28px 0;\">"
                "<a href=\"" + lien + "\" style=\"display:inline-block; background:#4f7ef8; color:#fff;"
                " padding:14px 32px; text-decoration:none; border-radius:8px; font-weight:600; font-size:15px;\">"
                + bouton + "</a>"
                "<div style=\"font-size:12px; color:#8a90a2; margin-top:8px;\">" + duree + "</div></div>\n"
                "  <p style=\"font-size:13px; color:#5b6172;\">Ce lien vous est personnel, il vous identifie "
                "automatiquement.</p>\n"
                "  <p style=\"margin-top: 24px;\">Bien &agrave; vous,<br><strong>" + signature + ", " + marque
                + "</strong></p>\n</div>")
        try:
            import mails as _mails
            html = _mails.poser_logo(html, logo_bytes)
            message = MIMEMultipart("related")
            message["To"] = mail
            import mails as _m_exp
            _exp = _m_exp.expediteur(S if "S" in dir() else None)
            if _exp:
                message["From"] = _exp
            message["Subject"] = sujet_base + " · " + (S.get("titre_complet") or S.get("nom_formation") or "")
            corps = MIMEMultipart("alternative")
            corps.attach(MIMEText(html, "html"))
            message.attach(corps)
            logo = MIMEImage(logo_bytes)
            logo.add_header("Content-ID", "<logo>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            message.attach(logo)
            # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
            # decide d'ou part le mail — deux entites, deux adresses.
            courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
            resultats.append({"ok": True, "texte": (personne.get("nom") or mail) + " : envoye"})
        except Exception as e:
            resultats.append({"ok": False, "texte": (personne.get("nom") or mail) + " : echec (" + str(e)[:60] + ")"})
    return resultats
@app.route("/session/<code>/questionnaires/tableau")
def tableau_questionnaires(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    from datetime import datetime as dt
    import questionnaires as Q
    S = fiche_session(code)
    fcode = SESSIONS[code].get("formation") or ""
    ev = Q.pour_formation(fcode)
    publie = None
    try:
        r = _sb("Sessions_publiques?session_code=eq." + code + "&select=participants,questions,ouvert,maj")
        publie = r[0] if r else None
    except Exception as e:
        return jsonify({"ok": False, "message": "Supabase injoignable : " + str(e)})
    gens = (publie or {}).get("participants") or []
    repondants = _q_repondants(code) if publie else {"init": [], "fin": [], "satisfaction": []}
    planning, auto, envois = _q_reglages(code)
    ouvert = (publie or {}).get("ouvert") or {}
    maintenant = dt.now()
    etapes = []
    for quoi in _Q_TYPES:
        rep = set(repondants.get(quoi) or [])
        manquants = [p for p in gens if (p.get("mail") or "").strip().lower() not in rep]
        moment = _q_moment(planning[quoi])
        retard = 0
        if moment and maintenant > moment:
            retard = int((maintenant - moment).total_seconds() // 60)
        etapes.append({
            "type": quoi, "nom": _Q_NOMS[quoi],
            "planning": planning[quoi],
            "auto": bool(auto.get(quoi)),
            "envoye_le": envois.get(quoi, ""),
            "ouvert": bool(ouvert.get(quoi)),
            "repondu": len(rep),
            "total": len(gens),
            "manquants": [{"nom": p.get("nom") or "", "mail": p.get("mail") or ""} for p in manquants],
            "retard": retard,
            "a_faire": bool(retard > 0 and not envois.get(quoi) and not ouvert.get(quoi)),
            "lien": (S.get("url_signature") or "") + "/questionnaire.html?s=" + code + "&type=" + quoi,
        })
    a_relever = 0
    if publie:
        try:
            faits = {"init": 0, "fin": 0, "satisfaction": 0, "froid": 0}
            CH = {"init": "eval_init_le", "fin": "eval_fin_le", "satisfaction": "satisfaction_le",
                  "froid": "froid_le"}
            for l in _lignes_onglet(S):
                for quoi, champ in CH.items():
                    if l.get(champ):
                        faits[quoi] += 1
            for quoi in _Q_TYPES:
                a_relever += max(0, len(repondants.get(quoi) or []) - faits[quoi])
        except Exception:
            a_relever = 0
    return jsonify({"ok": True, "code": code,
                    "formation": S.get("nom_formation") or "",
                    "date_texte": S.get("date_texte") or "",
                    "dispo": bool(ev),
                    "nb_questions": len(ev["questions"]) if ev else 0,
                    "prepare": bool(publie),
                    "prepare_le": (publie or {}).get("maj", ""),
                    # Un instantane local des modeles existe-t-il pour cette
                    # session ? Sans lui, la correction retombe sur la
                    # bibliotheque et suivra ses futures modifications.
                    "fige": bool(Q.fige(code)),
                    "nb_participants": len(gens),
                    "nb_inscrits": len(_q_actifs(S)),
                    "etapes": etapes, "a_relever": a_relever})
@app.route("/session/<code>/questionnaires/planning", methods=["POST"])
def enregistrer_planning(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    planning, auto, envois = _q_reglages(code)
    quoi = (request.form.get("type") or "").strip()
    if quoi not in _Q_TYPES:
        return jsonify({"ok": False, "message": "Type inconnu"})
    date = (request.form.get("date") or "").strip()
    heure = (request.form.get("heure") or "").strip()
    if date:
        planning[quoi]["date"] = date
    if heure:
        planning[quoi]["heure"] = heure
    if request.form.get("auto") is not None:
        auto[quoi] = (request.form.get("auto") == "1")
    _q_enregistrer(code, planning=planning, auto=auto)
    return jsonify({"ok": True, "planning": planning[quoi], "auto": bool(auto.get(quoi))})
@app.route("/session/<code>/questionnaires/envoyer", methods=["POST"])
def envoyer_questionnaire(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("mail")
    if _g:
        return jsonify({"ok": False, "message": _g})
    _v = _et_verrou(code, "mail")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from datetime import datetime as dt
    import journal
    quoi = (request.form.get("type") or "").strip()
    cible = (request.form.get("cible") or "manquants").strip()
    if quoi not in _Q_TYPES:
        return jsonify({"ok": False, "message": "Type inconnu"})
    try:
        r = _sb("Sessions_publiques?session_code=eq." + code + "&select=participants,ouvert")
    except Exception as e:
        return jsonify({"ok": False, "message": "Supabase injoignable : " + str(e)})
    if not r:
        return jsonify({"ok": False, "message": "Prepare d'abord les questionnaires de cette session."})
    gens = r[0].get("participants") or []
    if cible == "manquants":
        rep = set(_q_repondants(code).get(quoi) or [])
        gens = [p for p in gens if (p.get("mail") or "").strip().lower() not in rep]
    if not gens:
        return jsonify({"ok": True, "envoyes": 0,
                        "etapes": [{"ok": True, "texte": "Tout le monde a deja repondu"}]})
    ouvert = r[0].get("ouvert") or {}
    if not ouvert.get(quoi):
        ouvert[quoi] = True
        try:
            _sb("Sessions_publiques?session_code=eq." + code, "PATCH", {"ouvert": ouvert})
        except Exception as e:
            return jsonify({"ok": False, "message": "Ouverture impossible : " + str(e)})
    etapes = _q_envoyer_mails(code, quoi, gens)
    envoyes = len([e for e in etapes if e["ok"]])
    if envoyes:
        _q_enregistrer(code, envoi=(quoi, dt.now().strftime("%d/%m/%Y %H:%M")))
    try:
        journal.ecrire(_Q_NOMS[quoi] + " envoyé", "", str(envoyes) + " destinataire(s)", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "envoyes": envoyes, "etapes": etapes})
@app.route("/taches")
def liste_taches():
    from datetime import datetime as dt, timedelta
    taches = []
    aujourdhui = dt.now()
    for code in SESSIONS:
        try:
            S = fiche_session(code)
            fin = S.get("date_fin") or S.get("date_debut") or ""
            if fin:
                d = dt.strptime(fin, "%Y-%m-%d")
                if d < aujourdhui - timedelta(days=45) or d > aujourdhui + timedelta(days=120):
                    continue
            planning, auto, envois = _q_reglages(code)
            try:
                r = _sb("Sessions_publiques?session_code=eq." + code + "&select=ouvert")
                ouvert = (r[0].get("ouvert") or {}) if r else {}
            except Exception:
                continue
            if not r:
                continue
            for quoi in _Q_TYPES:
                if envois.get(quoi) or ouvert.get(quoi):
                    continue
                moment = _q_moment(planning[quoi])
                if not moment or aujourdhui < moment:
                    continue
                retard = int((aujourdhui - moment).total_seconds() // 60)
                taches.append({"session": code, "type": quoi,
                               "titre": _Q_NOMS[quoi] + " — " + (S.get("nom_formation") or ""),
                               "detail": "Prévu le " + planning[quoi]["date"] + " à " + planning[quoi]["heure"],
                               "retard": retard,
                               "urgence": "haute" if retard > 60 else "moyenne",
                               "auto": bool(auto.get(quoi)),
                               "lien": "/session/" + code})
        except Exception:
            continue
    from datetime import datetime as dt2, timedelta as td2
    try:
        etats = _et_lire()
    except Exception:
        etats = {}
    for code in SESSIONS:
        d = etats.get(code) or {}
        if d.get("terminee_le"):
            continue
        try:
            S = fiche_session(code)
            fin = S.get("date_fin") or S.get("date_debut") or ""
            if not fin:
                continue
            limite = dt2.strptime(fin, "%Y-%m-%d") + td2(weeks=int(_par("relance_cloture", 10)))
            report = (d.get("report_le") or "").strip()
            if report:
                try:
                    p = report.split("/")
                    limite = dt2(int(p[2]), int(p[1]), int(p[0]))
                except Exception:
                    pass
            if dt2.now() < limite:
                continue
            jours = (dt2.now() - limite).days
            taches.append({"session": code, "type": "cloture",
                           "titre": "Session à clôturer — " + (S.get("nom_formation") or code),
                           "detail": "La formation s'est terminée il y a plus de 10 semaines",
                           "retard": jours * 1440,
                           "urgence": "moyenne", "auto": False,
                           "lien": "/session/" + code})
        except Exception:
            continue
    taches.sort(key=lambda t: -t["retard"])
    return jsonify({"ok": True, "taches": taches})
def _q_auto():
    from datetime import datetime as dt
    for code in list(SESSIONS):
        try:
            planning, auto, envois = _q_reglages(code)
            if not any(auto.get(t) for t in _Q_TYPES):
                continue
            r = _sb("Sessions_publiques?session_code=eq." + code + "&select=participants,ouvert")
            if not r:
                continue
            for quoi in _Q_TYPES:
                if not auto.get(quoi) or envois.get(quoi):
                    continue
                moment = _q_moment(planning[quoi])
                if not moment or dt.now() < moment:
                    continue
                gens = r[0].get("participants") or []
                rep = set(_q_repondants(code).get(quoi) or [])
                gens = [p for p in gens if (p.get("mail") or "").strip().lower() not in rep]
                if not gens:
                    continue
                ouvert = r[0].get("ouvert") or {}
                ouvert[quoi] = True
                _sb("Sessions_publiques?session_code=eq." + code, "PATCH", {"ouvert": ouvert})
                res = _q_envoyer_mails(code, quoi, gens)
                envoyes = len([e for e in res if e["ok"]])
                if envoyes:
                    _q_enregistrer(code, envoi=(quoi, dt.now().strftime("%d/%m/%Y %H:%M")))
                    try:
                        import journal
                        journal.ecrire(_Q_NOMS[quoi] + " envoyé automatiquement", "",
                                       str(envoyes) + " destinataire(s)", "", code)
                    except Exception:
                        pass
        except Exception as e:
            _auto_signaler("session " + code, e, code)
            continue
def _qd_nombre(v):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None
def _qd_moyenne(valeurs):
    v = [x for x in valeurs if x is not None]
    return round(sum(v) / len(v), 1) if v else None
def _qd_satisfaction_brute(filtre=""):
    """Les reponses de satisfaction, RESTREINTES aux sessions de l'organisme
    actif. Supabase les stocke toutes ensemble : sans ce filtre, les avis des
    apprenants d'un organisme alimenteraient les indicateurs de l'autre."""
    try:
        brut = _sb("Questionnaires?type=eq.satisfaction&select=session_code,mail,nom,reponses" + filtre)
    except Exception:
        return []
    try:
        import sessions as _sessions
        permis = set(_sessions.visibles())
    except Exception:
        return brut
    return [r for r in brut if (r.get("session_code") or "") in permis]
def _qd_axes(reponses_liste, code_session=None):
    """Analyse des reponses de satisfaction.
    Sans code_session : la trame de reference, comportement historique — c'est
    le cas des vues qui agregent plusieurs sessions, ou aucun modele unique
    n'existe. Avec code_session : le modele FIGE de cette session, seul fidele
    aux questions reellement posees (C5)."""
    import questionnaires as Q
    modele = Q.SATISFACTION
    if code_session:
        try:
            fcode = SESSIONS.get(code_session, {}).get("formation") or ""
            m = Q.modele_session(code_session, fcode, "satisfaction")
            if m and m.get("notes"):
                modele = m
        except Exception:
            pass
    axes = {}
    for n in modele["notes"]:
        axes.setdefault(n["axe"], {"libelle": modele["axes"].get(n["axe"], n["axe"]),
                                   "valeurs": [], "questions": []})
    detail = {}
    for n in modele["notes"]:
        detail[n["id"]] = {"libelle": n["libelle"], "axe": n["axe"], "valeurs": []}
    recos = []
    adaptation = {"total": 0, "concernes": 0, "pris": 0}
    verbatims = []
    for r in reponses_liste:
        rep = r.get("reponses") or {}
        for n in modele["notes"]:
            v = _qd_nombre(rep.get(n["id"]))
            if v is not None:
                axes[n["axe"]]["valeurs"].append(v)
                detail[n["id"]]["valeurs"].append(v)
        v = _qd_nombre(rep.get(modele["recommandation"]["id"]))
        if v is not None:
            recos.append(v)
        a = rep.get(modele["adaptation"]["id"])
        if a is not None and a != "":
            adaptation["total"] += 1
            try:
                i = int(a)
            except Exception:
                i = 0
            if i > 0:
                adaptation["concernes"] += 1
                if i == 1:
                    adaptation["pris"] += 1
        for o in modele["ouvertes"]:
            t = (rep.get(o["id"]) or "").strip() if isinstance(rep.get(o["id"]), str) else ""
            if t:
                verbatims.append({"question": o["libelle"], "texte": t})
    sortie_axes = []
    for cle, v in axes.items():
        sortie_axes.append({"axe": cle, "libelle": v["libelle"], "note": _qd_moyenne(v["valeurs"]),
                            "reponses": len(v["valeurs"])})
    sortie_detail = []
    for cle, v in detail.items():
        sortie_detail.append({"id": cle, "libelle": v["libelle"], "axe": v["axe"],
                              "note": _qd_moyenne(v["valeurs"])})
    promoteurs = len([x for x in recos if x >= 9])
    detracteurs = len([x for x in recos if x <= 6])
    nps = round(100.0 * (promoteurs - detracteurs) / len(recos)) if recos else None
    return {"axes": sortie_axes, "questions": sortie_detail,
            "note_globale": _qd_moyenne([x for a in axes.values() for x in a["valeurs"]]),
            "reco_moyenne": _qd_moyenne(recos), "nps": nps, "nb_reco": len(recos),
            "adaptation": adaptation, "verbatims": verbatims}
def _qd_sessions():
    """Les sessions dont l'ecran Questionnaires tire ses indicateurs.

    CLOISONNE PAR ORGANISME. Les statistiques pedagogiques ne se separent
    jamais par MODE de session — un praticien venu par son centre repond au
    meme questionnaire, et l'atteinte des objectifs Qualiopi se mesure sur
    tous les participants. Mais elles se separent par ORGANISME : deux
    certifications a defendre, et un auditeur ne doit voir que la sienne."""
    from connexion import service_sheets
    import suivi as _suivi
    import questionnaires as Q
    import sessions as _sessions
    fiches = {code: fiche_session(code) for code in _sessions.visibles()}
    brut = _grilles_suivi(list(fiches))
    sorties = []
    # Meme restriction que la boucle de lecture ci-dessus : sans cela, la
    # seconde boucle cherchait la fiche d'une session non chargee et l'ecran
    # tombait en erreur des qu'un organisme n'avait aucune session.
    for code in _sessions.visibles():
        S = fiches[code]
        fcode = SESSIONS[code].get("formation") or ""
        # Seuil fige a la preparation : relever le seuil aujourd'hui ne doit pas
        # faire basculer retroactivement des sessions passees en "non atteint".
        ev = Q.modele_session(code, fcode)
        seuil = (ev or {}).get("seuil", Q.seuil_defaut())
        gens = []
        for r in brut.get(code, [])[1:]:
            if not r or len(r) <= _suivi.COL["mail"]:
                continue
            d = {}
            for cle, idx in _suivi.COL.items():
                d[cle] = (r[idx] if len(r) > idx else "") or ""
            if not d.get("mail") or d.get("annule_le"):
                continue
            if "recontact" in (d.get("demande") or "").lower():
                continue
            if d.get("file_attente_le") and not d.get("promu_le"):
                continue
            gens.append({"nom": (d.get("nom") or "").upper() + " " + (d.get("prenom") or ""),
                         "mail": (d.get("mail") or "").strip().lower(),
                         "init": _qd_nombre(d.get("score_init")),
                         "fin": _qd_nombre(d.get("score_fin")),
                         "satisfaction": _qd_nombre(d.get("note_satisfaction")),
                         "ville": d.get("ville") or "",
                         "present": bool(d.get("present"))})
        inits = [g["init"] for g in gens if g["init"] is not None]
        fins = [g["fin"] for g in gens if g["fin"] is not None]
        paires = [(g["init"], g["fin"]) for g in gens if g["init"] is not None and g["fin"] is not None]
        satis = [g["satisfaction"] for g in gens if g["satisfaction"] is not None]
        atteints = len([f for f in fins if f >= seuil])
        try:
            annee = int((S.get("date_debut") or "0000")[:4])
        except Exception:
            annee = 0
        sorties.append({
            "code": code, "formation": S.get("nom_formation") or "",
            "formation_code": fcode,
            "titre": S.get("titre_complet") or "",
            "date_texte": S.get("date_texte") or "",
            "debut": S.get("date_debut") or "", "annee": annee,
            "seuil": seuil,
            "participants": len(gens), "gens": gens,
            "nb_init": len(inits), "nb_fin": len(fins), "nb_satis": len(satis),
            "moy_init": _qd_moyenne(inits), "moy_fin": _qd_moyenne(fins),
            "progression": _qd_moyenne([b - a for a, b in paires]) if paires else None,
            "atteints": atteints,
            "taux_atteinte": round(100.0 * atteints / len(fins)) if fins else None,
            "moy_satis": _qd_moyenne(satis),
        })
    sorties.sort(key=lambda x: x["debut"], reverse=True)
    return sorties
@app.route("/questionnaires")
def page_questionnaires():
    sessions = _qd_sessions()
    satisfactions = _qd_satisfaction_brute()
    global_sat = _qd_axes(satisfactions)
    formations = {}
    for s in sessions:
        f = formations.setdefault(s["formation"], {
            "formation": s["formation"], "sessions": 0, "participants": 0,
            "inits": [], "fins": [], "prog": [], "satis": [], "atteints": 0, "nb_fin": 0})
        f["sessions"] += 1
        f["participants"] += s["participants"]
        for g in s["gens"]:
            if g["init"] is not None:
                f["inits"].append(g["init"])
            if g["fin"] is not None:
                f["fins"].append(g["fin"])
                f["nb_fin"] += 1
                if g["fin"] >= s["seuil"]:
                    f["atteints"] += 1
            if g["init"] is not None and g["fin"] is not None:
                f["prog"].append(g["fin"] - g["init"])
            if g["satisfaction"] is not None:
                f["satis"].append(g["satisfaction"])
    liste_formations = []
    for nom, f in formations.items():
        liste_formations.append({
            "formation": nom, "sessions": f["sessions"], "participants": f["participants"],
            "moy_init": _qd_moyenne(f["inits"]), "moy_fin": _qd_moyenne(f["fins"]),
            "progression": _qd_moyenne(f["prog"]),
            "taux_atteinte": round(100.0 * f["atteints"] / f["nb_fin"]) if f["nb_fin"] else None,
            "moy_satis": _qd_moyenne(f["satis"])})
    liste_formations.sort(key=lambda x: x["formation"])
    tous_init, tous_fin, tous_prog, tous_satis = [], [], [], []
    total_part = 0
    total_atteints = 0
    total_fins = 0
    for s in sessions:
        total_part += s["participants"]
        for g in s["gens"]:
            if g["init"] is not None:
                tous_init.append(g["init"])
            if g["fin"] is not None:
                tous_fin.append(g["fin"])
                total_fins += 1
                if g["fin"] >= s["seuil"]:
                    total_atteints += 1
            if g["init"] is not None and g["fin"] is not None:
                tous_prog.append(g["fin"] - g["init"])
            if g["satisfaction"] is not None:
                tous_satis.append(g["satisfaction"])
    annees = sorted({s["annee"] for s in sessions if s["annee"]}, reverse=True)
    for s in sessions:
        s.pop("gens", None)
    return render_template("questionnaires.html",
        sessions=sessions, formations=liste_formations, annees=annees,
        g={"participants": total_part,
           "moy_init": _qd_moyenne(tous_init), "moy_fin": _qd_moyenne(tous_fin),
           "progression": _qd_moyenne(tous_prog),
           "taux_atteinte": round(100.0 * total_atteints / total_fins) if total_fins else None,
           "moy_satis": _qd_moyenne(tous_satis),
           "nb_init": len(tous_init), "nb_fin": len(tous_fin), "nb_satis": len(tous_satis),
           "nps": global_sat["nps"], "reco": global_sat["reco_moyenne"],
           "axes": global_sat["axes"]}, periode_defaut=_par_periode())
def _qd_objectifs(code):
    import questionnaires as Q
    fcode = SESSIONS.get(code, {}).get("formation") or ""
    # Modele fige a la preparation quand il existe : le bilan par objectif d'une
    # session passee ne doit pas bouger parce qu'on a retouche la bibliotheque.
    ev = Q.modele_session(code, fcode)
    if not ev:
        return None
    try:
        recues = _sb("Questionnaires?session_code=eq." + code + "&type=in.(init,fin)&select=mail,nom,type,reponses")
    except Exception:
        return None
    par_personne = {}
    for r in recues:
        m = (r.get("mail") or "").strip().lower()
        par_personne.setdefault(m, {"nom": r.get("nom") or m})
        par_personne[m][r.get("type")] = r.get("reponses") or {}
    objectifs = ev.get("objectifs") or {}
    cumul = {}
    for cle in objectifs:
        cumul[cle] = {"libelle": objectifs[cle], "init": [], "fin": []}
    questions = {}
    for q in ev["questions"]:
        questions[q["id"]] = {"enonce": q["enonce"], "objectif": q.get("objectif", "?"),
                              "init_justes": 0, "fin_justes": 0, "init_total": 0, "fin_total": 0}
    personnes = []
    for m, d in par_personne.items():
        ligne = {"nom": d.get("nom") or m, "mail": m, "init": None, "fin": None, "objectifs": {}}
        for quoi in ("init", "fin"):
            if quoi not in d:
                continue
            res = Q.corriger_avec(ev, d[quoi])
            if not res:
                continue
            ligne[quoi] = res["score"]
            for cle, val in res["par_objectif"].items():
                if cle in cumul:
                    cumul[cle][quoi].append(val)
                ligne["objectifs"].setdefault(cle, {})[quoi] = val
            for det in res["detail"]:
                q = questions.get(det["id"])
                if not q:
                    continue
                q[quoi + "_total"] += 1
                if det["juste"]:
                    q[quoi + "_justes"] += 1
        personnes.append(ligne)
    personnes.sort(key=lambda x: x["nom"])
    sortie_obj = []
    for cle, v in sorted(cumul.items()):
        mi = _qd_moyenne(v["init"])
        mf = _qd_moyenne(v["fin"])
        sortie_obj.append({"cle": cle, "libelle": v["libelle"], "init": mi, "fin": mf,
                           "progression": round(mf - mi, 1) if (mi is not None and mf is not None) else None})
    sortie_q = []
    for qid, v in questions.items():
        ti = round(100.0 * v["init_justes"] / v["init_total"]) if v["init_total"] else None
        tf = round(100.0 * v["fin_justes"] / v["fin_total"]) if v["fin_total"] else None
        sortie_q.append({"id": qid, "enonce": v["enonce"], "objectif": v["objectif"],
                         "init": ti, "fin": tf,
                         "progression": (tf - ti) if (ti is not None and tf is not None) else None})
    sortie_q.sort(key=lambda x: (x["fin"] if x["fin"] is not None else 999))
    return {"objectifs": sortie_obj, "questions": sortie_q, "personnes": personnes,
            "seuil": ev.get("seuil", Q.seuil_defaut())}
@app.route("/questionnaires/<code>/detail")
def detail_questionnaires(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    fiche = None
    for s in _qd_sessions():
        if s["code"] == code:
            fiche = s
    if not fiche:
        return jsonify({"ok": False, "message": "Session introuvable"})
    obj = _qd_objectifs(code)
    sat = _qd_axes(_qd_satisfaction_brute("&session_code=eq." + code), code)
    return jsonify({"ok": True, "session": fiche, "acquis": obj, "satisfaction": sat})
def _qd_donut(segments, centre="", centre_sous=""):
    total = 0
    for s in segments:
        total += s[1]
    if total <= 0:
        total = 1
    rayon = 60.0
    circo = 2 * 3.14159265 * rayon
    out = []
    curseur = 0.0
    for libelle, valeur, couleur in segments:
        pct = 100.0 * valeur / total
        longueur = circo * pct / 100.0
        out.append({"libelle": libelle, "valeur": valeur, "pct": int(round(pct)),
                    "couleur": couleur, "dash": round(longueur, 1),
                    "reste": round(circo - longueur, 1), "offset": round(-curseur, 1)})
        curseur += longueur
    return {"rayon": int(rayon), "circo": round(circo, 1), "segments": out,
            "centre": centre, "centre_sous": centre_sous, "total": total}
def _qd_colonnes(items, maxi=None):
    valeurs = [i[1] for i in items if i[1] is not None]
    haut = maxi if maxi else (max(valeurs) if valeurs else 1)
    if not haut:
        haut = 1
    out = []
    for libelle, valeur, couleur in items:
        h = 0 if valeur is None else int(round(100.0 * valeur / haut))
        out.append({"libelle": libelle, "valeur": valeur, "couleur": couleur,
                    "hauteur": max(2, min(100, h))})
    return out
def _qd_periode_bornes(periode):
    from datetime import datetime as dt, timedelta
    if periode == "m3":
        return (dt.now() - timedelta(days=92)).strftime("%Y-%m-%d"), "3 derniers mois"
    if periode == "m6":
        return (dt.now() - timedelta(days=183)).strftime("%Y-%m-%d"), "6 derniers mois"
    if periode in ("m12", "an1"):
        return (dt.now() - timedelta(days=365)).strftime("%Y-%m-%d"), "12 derniers mois"
    return "", "Depuis le début"
def _qd_agreger(liste):
    inits, fins, progs, satis = [], [], [], []
    atteints = 0
    nb_fin = 0
    participants = 0
    nb_init = 0
    nb_satis = 0
    for s in liste:
        participants += s["participants"]
        for g in s.get("gens") or []:
            if g["init"] is not None:
                inits.append(g["init"])
                nb_init += 1
            if g["fin"] is not None:
                fins.append(g["fin"])
                nb_fin += 1
                if g["fin"] >= s["seuil"]:
                    atteints += 1
            if g["init"] is not None and g["fin"] is not None:
                progs.append(g["fin"] - g["init"])
            if g["satisfaction"] is not None:
                satis.append(g["satisfaction"])
                nb_satis += 1
    return {"participants": participants, "nb_init": nb_init, "nb_fin": nb_fin, "nb_satis": nb_satis,
            "moy_init": _qd_moyenne(inits), "moy_fin": _qd_moyenne(fins),
            "progression": _qd_moyenne(progs), "atteints": atteints,
            "taux_atteinte": int(round(100.0 * atteints / nb_fin)) if nb_fin else None,
            "moy_satis": _qd_moyenne(satis), "sessions": len(liste)}
def _qd_stats(valeurs):
    v = sorted([x for x in valeurs if x is not None])
    if not v:
        return None
    n = len(v)
    moy = sum(v) / float(n)
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0
    var = sum((x - moy) ** 2 for x in v) / float(n)
    return {"n": n, "min": round(min(v), 1), "max": round(max(v), 1),
            "moy": round(moy, 1), "mediane": round(med, 1), "ecart": round(var ** 0.5, 1)}
def _qd_histo(valeurs, bandes, couleur="#4f7ef8"):
    items = []
    for lib, bas, haut in bandes:
        n = len([x for x in valeurs if x is not None and x >= bas and x < haut])
        items.append((lib, n, couleur))
    return _qd_colonnes(items)
def _qd_duo(items):
    plates = []
    for i in items:
        for x in (i[1], i[2]):
            if x is not None:
                plates.append(x)
    haut = max(plates) if plates else 1
    if not haut:
        haut = 1
    out = []
    for lib, a, b in items:
        out.append({"libelle": lib, "a": a, "b": b,
                    "ha": max(2, min(100, int(round(100.0 * a / haut)))) if a is not None else 0,
                    "hb": max(2, min(100, int(round(100.0 * b / haut)))) if b is not None else 0})
    return out
def _qd_questions_cumul(codes):
    cumul = {}
    for code in codes:
        o = _qd_objectifs(code)
        if not o:
            continue
        for q in o["questions"]:
            c = cumul.setdefault(q["id"], {"enonce": q["enonce"], "objectif": q["objectif"],
                                           "init": [], "fin": []})
            if q["init"] is not None:
                c["init"].append(q["init"])
            if q["fin"] is not None:
                c["fin"].append(q["fin"])
    sortie = []
    for qid, v in cumul.items():
        mi = _qd_moyenne(v["init"])
        mf = _qd_moyenne(v["fin"])
        sortie.append({"id": qid, "enonce": v["enonce"], "objectif": v["objectif"],
                       "init": mi, "fin": mf,
                       "progression": round(mf - mi, 1) if (mi is not None and mf is not None) else None})
    sortie.sort(key=lambda x: (x["fin"] if x["fin"] is not None else 999))
    return sortie
def _qd_operationnel(code):
    from connexion import service_sheets
    S = fiche_session(code)
    lignes = _lignes_onglet(S)
    def nb(v):
        try:
            return float(str(v).replace(",", ".").replace(" ", "") or 0)
        except Exception:
            return 0.0
    tarif = nb(S.get("tarif"))
    participants = []
    annulations = []
    attente = []
    for l in lignes:
        nom = ((l.get("nom") or "").upper() + " " + (l.get("prenom") or "")).strip()
        if not (l.get("mail") or "").strip():
            continue
        if "recontact" in (l.get("demande") or "").lower():
            continue
        if l.get("annule_le"):
            annulations.append({"nom": nom, "le": (l.get("annule_le") or "")[:10],
                                "motif": l.get("motif_annulation") or ""})
            continue
        if l.get("file_attente_le") and not l.get("promu_le"):
            attente.append({"nom": nom, "depuis": (l.get("file_attente_le") or "")[:10]})
            continue
        du = nb(l.get("montant_du")) or tarif
        recu = nb(l.get("montant_recu"))
        participants.append({
            "nom": nom, "mail": (l.get("mail") or "").strip(),
            "ville": l.get("ville") or "",
            "convention_le": (l.get("signe_le") or "")[:10],
            "convention_lien": l.get("lien_pdf") or "",
            "du": du, "recu": recu,
            "reglement_le": (l.get("paiement_recu_le") or "")[:10],
            "mode": l.get("mode_paiement") or "",
            "facture_lien": l.get("lien_facture") or "",
            "facture_le": (l.get("facture_envoyee_le") or "")[:10],
            "attestation_lien": l.get("lien_attestation") or "",
            "attestation_le": (l.get("attestation_le") or "")[:10],
            "present": bool(l.get("present")),
            "promu": bool(l.get("promu_le")),
        })
    # L'ETAT VIENT DE LA BASE. Cette fiche est construite a chaque ouverture de
    # session : c'etaient deux cents lignes d'onglet telechargees pour trois
    # cellules.
    try:
        _e = SESSIONS_MOD.etat(code)
        emargement = {"vierge": _e["lien_emargement"],
                      "signe_le": _e["emargement_signe_le"],
                      "lien": _e["lien_emargement_signe"]}
    except Exception:
        emargement = {"signe_le": "", "lien": "", "vierge": ""}
    ca_attendu = sum(p["du"] for p in participants)
    ca_encaisse = sum(p["recu"] for p in participants)
    return {
        "participants": participants,
        "annulations": annulations, "attente": attente,
        "ca_attendu": round(ca_attendu, 2), "ca_encaisse": round(ca_encaisse, 2),
        "reste": round(ca_attendu - ca_encaisse, 2),
        "nb": len(participants),
        "nb_conventions": len([p for p in participants if p["convention_le"]]),
        "nb_reglements": len([p for p in participants if p["recu"]]),
        "nb_factures": len([p for p in participants if p["facture_lien"]]),
        "nb_attestations": len([p for p in participants if p["attestation_lien"]]),
        "nb_presents": len([p for p in participants if p["present"]]),
        "emargement": emargement,
        "tarif": tarif,
        "adresse": S.get("adresse") or "", "horaires": S.get("horaires") or "",
        "formateur": S.get("formateur") or "", "duree": S.get("duree") or "",
    }
def _bilan_entete():
    """L'organisme qui figure en tete d'un bilan.

    Il est tire des SESSIONS QUI COMPOSENT LE BILAN, pas du profil actif. Un
    bilan est une piece que l'on peut presenter a un auditeur Qualiopi : son
    en-tete doit nommer l'organisme dont il rend compte, meme si l'on s'est
    trompe de profil en l'ouvrant. En-tete et donnees ne peuvent plus diverger."""
    from sessions import COMMUN
    import sessions as _s
    codes = _s.visibles()
    if codes:
        S = fiche_session(codes[0])
        return {"organisme": S.get("organisme") or "", "marque": S.get("marque") or "",
                "formateur": S.get("formateur") or ""}
    return {"organisme": COMMUN.get("organisme") or "", "marque": COMMUN.get("marque") or "",
            "formateur": COMMUN.get("formateur") or ""}


def _qd_bilan(portee, cible=None, periode=""):
    from datetime import datetime as dt
    toutes = _qd_sessions()
    borne, libelle_periode = _qd_periode_bornes(periode)
    if portee == "session":
        liste = [s for s in toutes if s["code"] == cible]
        titre = "Bilan de session"
        sous = (liste[0]["titre"] or liste[0]["formation"]) if liste else ""
        contexte = liste[0]["date_texte"] if liste else ""
        reference = cible
    elif portee == "formation":
        liste = [s for s in toutes if s["formation_code"] == cible or s["formation"] == cible]
        if borne:
            liste = [s for s in liste if s["debut"] >= borne]
        titre = "Bilan de formation"
        sous = (liste[0]["titre"] or liste[0]["formation"]) if liste else str(cible)
        contexte = str(len(liste)) + " session(s) · " + libelle_periode
        reference = str(cible)
    else:
        liste = toutes
        if borne:
            liste = [s for s in liste if s["debut"] >= borne]
        titre = "Bilan global d'activité"
        sous = "Toutes formations et toutes sessions confondues"
        contexte = str(len(liste)) + " session(s) · " + libelle_periode
        reference = "global"
    codes = [s["code"] for s in liste]
    synth = _qd_agreger(liste)
    tous_init, tous_fin, tous_prog, tous_satis = [], [], [], []
    mails = set()
    villes = {}
    progresses, stables, regresses = 0, 0, 0
    for s in liste:
        for g in s.get("gens") or []:
            if g.get("mail"):
                mails.add(g["mail"])
            v = (g.get("ville") or "").strip().title()
            if v:
                villes[v] = villes.get(v, 0) + 1
            if g["init"] is not None:
                tous_init.append(g["init"])
            if g["fin"] is not None:
                tous_fin.append(g["fin"])
            if g["satisfaction"] is not None:
                tous_satis.append(g["satisfaction"])
            if g["init"] is not None and g["fin"] is not None:
                e = g["fin"] - g["init"]
                tous_prog.append(e)
                if e > 0:
                    progresses += 1
                elif e == 0:
                    stables += 1
                else:
                    regresses += 1
    top_villes = sorted(villes.items(), key=lambda x: -x[1])[:8]
    filtre = "&session_code=in.(" + ",".join(codes) + ")" if codes else ""
    brutes = _qd_satisfaction_brute(filtre) if codes else []
    sat = _qd_axes(brutes)
    recos = []
    for r in brutes:
        # L'identifiant de la question de recommandation etait ecrit en dur
        # ("s09") : un modele personnalise le nommant autrement faisait tomber
        # la repartition promoteurs/passifs/detracteurs a zero, silencieusement,
        # pendant que le NPS affiche juste a cote restait juste (C7).
        import questionnaires as _Q
        _sc = r.get("session_code") or ""
        _idr = "s09"
        try:
            _fc = SESSIONS.get(_sc, {}).get("formation") or ""
            _m = _Q.modele_session(_sc, _fc, "satisfaction")
            _idr = ((_m or {}).get("recommandation") or {}).get("id") or _idr
        except Exception:
            pass
        v = _qd_nombre((r.get("reponses") or {}).get(_idr))
        if v is not None:
            recos.append(v)
    promoteurs = len([x for x in recos if x >= 9])
    passifs = len([x for x in recos if 7 <= x <= 8])
    detracteurs = len([x for x in recos if x <= 6])
    objectifs, personnes, questions = [], [], []
    seuil = 70
    if portee == "session" and codes:
        o = _qd_objectifs(codes[0])
        if o:
            objectifs, personnes, questions, seuil = o["objectifs"], o["personnes"], o["questions"], o["seuil"]
    elif portee == "formation" and codes:
        cumul = {}
        for code in codes:
            o = _qd_objectifs(code)
            if not o:
                continue
            seuil = o["seuil"]
            for x in o["objectifs"]:
                c = cumul.setdefault(x["cle"], {"libelle": x["libelle"], "init": [], "fin": []})
                if x["init"] is not None:
                    c["init"].append(x["init"])
                if x["fin"] is not None:
                    c["fin"].append(x["fin"])
        for cle, v in sorted(cumul.items()):
            mi, mf = _qd_moyenne(v["init"]), _qd_moyenne(v["fin"])
            objectifs.append({"cle": cle, "libelle": v["libelle"], "init": mi, "fin": mf,
                              "progression": round(mf - mi, 1) if (mi is not None and mf is not None) else None})
        questions = _qd_questions_cumul(codes)
    formations = {}
    for s in liste:
        formations.setdefault(s["formation"], []).append(s)
    tableau_formations = []
    for nom, ses in sorted(formations.items()):
        a = _qd_agreger(ses)
        a["formation"] = nom
        tableau_formations.append(a)
    donut_objectifs = _qd_donut(
        [("Objectifs atteints", synth["atteints"], "#0f9e6a"),
         ("Partiellement atteints", max(0, synth["nb_fin"] - synth["atteints"]), "#f0cf94")],
        (str(synth["taux_atteinte"]) + " %") if synth["taux_atteinte"] is not None else "—", "atteinte")
    donut_reponses = _qd_donut(
        [("Ont répondu", synth["nb_fin"], "#4f7ef8"),
         ("Sans réponse", max(0, synth["participants"] - synth["nb_fin"]), "#e5e8f0")],
        (str(int(round(100.0 * synth["nb_fin"] / synth["participants"]))) + " %") if synth["participants"] else "—",
        "participation")
    donut_progression = _qd_donut(
        [("Ont progressé", progresses, "#0f9e6a"), ("Score stable", stables, "#f0cf94"),
         ("En recul", regresses, "#d03b3b")],
        str(progresses + stables + regresses), "évalués")
    donut_reco = _qd_donut(
        [("Promoteurs, 9-10", promoteurs, "#0f9e6a"), ("Passifs, 7-8", passifs, "#f0cf94"),
         ("Détracteurs, 0-6", detracteurs, "#d03b3b")],
        (str(sat["nps"]) if sat["nps"] is not None else "—"), "indice net")
    histo_scores = _qd_histo(tous_fin, [("0-40", 0, 40), ("40-60", 40, 60), ("60-70", 60, 70),
                                        ("70-80", 70, 80), ("80-90", 80, 90), ("90-100", 90, 101)], "#0f9e6a")
    histo_prog = _qd_histo(tous_prog, [("recul", -200, 0), ("0-10", 0, 10), ("10-25", 10, 25),
                                       ("25-50", 25, 50), ("50 et +", 50, 500)], "#4f7ef8")
    if portee == "session":
        duo = [(p["nom"].split(" ")[0][:10], p["init"], p["fin"]) for p in personnes]
        titre_duo = "Score d'entrée et de sortie, par participant"
    elif portee == "formation":
        duo = [(s["date_texte"][:11], s["moy_init"], s["moy_fin"]) for s in liste]
        titre_duo = "Score moyen d'entrée et de sortie, par session"
    else:
        duo = [(f["formation"][:13], f["moy_init"], f["moy_fin"]) for f in tableau_formations]
        titre_duo = "Score moyen d'entrée et de sortie, par formation"
    duo_colonnes = _qd_duo([x for x in duo if x[1] is not None or x[2] is not None])
    barres_satis = []
    for q in sat["questions"]:
        if q["note"] is not None:
            couleur = "#0f9e6a" if q["note"] >= 4 else ("#d4890a" if q["note"] >= 3 else "#d03b3b")
            barres_satis.append({"libelle": q["libelle"], "note": q["note"],
                                 "largeur": int(round(100.0 * q["note"] / 5)), "couleur": couleur})
    barres_axes = []
    for a in sat["axes"]:
        if a["note"] is not None:
            couleur = "#0f9e6a" if a["note"] >= 4 else ("#d4890a" if a["note"] >= 3 else "#d03b3b")
            barres_axes.append({"libelle": a["libelle"], "note": a["note"],
                                "largeur": int(round(100.0 * a["note"] / 5)), "couleur": couleur})
    maitrisees = [q for q in questions if q["fin"] is not None][-3:][::-1]
    fragiles = [q for q in questions if q["fin"] is not None][:3]
    coherence = None
    if portee in ("session", "formation") and liste:
        try:
            coherence = _coh_comparer(liste[0]["formation_code"])
        except Exception:
            coherence = None
    operationnel = None
    if portee == "session" and codes:
        try:
            operationnel = _qd_operationnel(codes[0])
        except Exception:
            operationnel = None
    return {"operationnel": operationnel,
            "coherence": coherence,
            "portee": portee, "titre": titre, "sous": sous, "contexte": contexte,
            "reference": reference, "periode": libelle_periode,
            "sessions": liste, "synth": synth, "formations": tableau_formations,
            "praticiens": len(mails), "villes": top_villes,
            "stats_init": _qd_stats(tous_init), "stats_fin": _qd_stats(tous_fin),
            "stats_prog": _qd_stats(tous_prog), "stats_satis": _qd_stats(tous_satis),
            "progresses": progresses, "stables": stables, "regresses": regresses,
            "promoteurs": promoteurs, "passifs": passifs, "detracteurs": detracteurs,
            "sat": sat, "objectifs": objectifs, "personnes": personnes,
            "questions": questions, "maitrisees": maitrisees, "fragiles": fragiles,
            "seuil": seuil,
            "donut_objectifs": donut_objectifs, "donut_reponses": donut_reponses,
            "donut_progression": donut_progression, "donut_reco": donut_reco,
            "histo_scores": histo_scores, "histo_prog": histo_prog,
            "duo": duo_colonnes, "titre_duo": titre_duo,
            "barres_satis": barres_satis, "barres_axes": barres_axes,
            "edite": dt.now().strftime("%d/%m/%Y")}
@app.route("/questionnaires/bilan")
def bilan_global():
    d = _qd_bilan("global", None, request.args.get("periode") or "")
    return render_template("bilan.html", d=d, **_bilan_entete())
@app.route("/questionnaires/bilan/formation/<code>")
def bilan_formation(code):
    d = _qd_bilan("formation", code, request.args.get("periode") or "")
    return render_template("bilan.html", d=d, **_bilan_entete())
@app.route("/questionnaires/<code>/bilan")
def bilan_session(code):
    if code not in SESSIONS:
        return "Session inconnue", 404
    S = fiche_session(code)
    d = _qd_bilan("session", code, "")
    return render_template("bilan.html", d=d, organisme=S.get("organisme") or "",
                           marque=S.get("marque") or "", formateur=S.get("formateur") or "")
@app.route("/questionnaires/export.csv")
def export_questionnaires():
    from flask import Response
    lignes = ["Session;Formation;Date;Praticien;Mail;Score entree;Score sortie;Progression;Seuil;Objectifs atteints;Satisfaction sur 5"]
    for s in _qd_sessions():
        for g in s["gens"]:
            prog = ""
            atteint = ""
            if g["init"] is not None and g["fin"] is not None:
                prog = str(round(g["fin"] - g["init"], 1))
            if g["fin"] is not None:
                atteint = "oui" if g["fin"] >= s["seuil"] else "non"
            lignes.append(";".join([
                s["code"], s["formation"], s["date_texte"], g["nom"], g["mail"],
                "" if g["init"] is None else str(g["init"]),
                "" if g["fin"] is None else str(g["fin"]),
                prog, str(s["seuil"]), atteint,
                "" if g["satisfaction"] is None else str(g["satisfaction"])]))
    corps = "\ufeff" + "\n".join(lignes)
    return Response(corps, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=questionnaires.csv"})
def _pr_recap(code, mail):
    import questionnaires as Q
    S = fiche_session(code)
    fcode = SESSIONS.get(code, {}).get("formation") or ""
    # Le corrige envoye au praticien doit montrer les questions ET les bonnes
    # reponses telles qu'elles etaient le jour de la session, pas celles
    # d'aujourd'hui. D'ou l'instantane plutot que la bibliotheque.
    ev = Q.modele_session(code, fcode)
    if not ev:
        return None
    mail = (mail or "").strip().lower()
    try:
        recues = _sb("Questionnaires?session_code=eq." + code + "&mail=eq." + mail + "&select=nom,type,reponses")
    except Exception:
        recues = []
    par_type = {}
    nom = ""
    for r in recues:
        par_type[r.get("type")] = r.get("reponses") or {}
        if r.get("nom"):
            nom = r["nom"]
    if not nom:
        for l in _lignes_onglet(S):
            if (l.get("mail") or "").strip().lower() == mail:
                nom = ((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip()
    res_init = Q.corriger_avec(ev, par_type.get("init") or {}) if "init" in par_type else None
    res_fin = Q.corriger_avec(ev, par_type.get("fin") or {}) if "fin" in par_type else None
    lignes = []
    for q in ev["questions"]:
        props = q.get("propositions") or []
        attendu = q["reponse"]
        def lire(source):
            if source is None:
                return None
            v = source.get(q["id"])
            try:
                return int(v)
            except Exception:
                return None
        ri = lire(par_type.get("init"))
        rf = lire(par_type.get("fin"))
        lignes.append({
            "id": q["id"], "objectif": q.get("objectif", ""), "enonce": q["enonce"],
            "propositions": props, "poids": q.get("poids", 1),
            "attendu": attendu,
            "attendu_texte": props[attendu] if attendu < len(props) else "",
            "init": ri, "init_texte": props[ri] if (ri is not None and ri < len(props)) else "",
            "fin": rf, "fin_texte": props[rf] if (rf is not None and rf < len(props)) else "",
            "init_juste": (ri is not None and ri == attendu),
            "fin_juste": (rf is not None and rf == attendu),
            "explication": q.get("explication", ""),
        })
    objectifs = []
    libelles = ev.get("objectifs") or {}
    for cle in sorted(libelles):
        oi = (res_init or {}).get("par_objectif", {}).get(cle)
        of = (res_fin or {}).get("par_objectif", {}).get(cle)
        objectifs.append({"cle": cle, "libelle": libelles[cle], "init": oi, "fin": of,
                          "progression": (of - oi) if (oi is not None and of is not None) else None})
    seuil = ev.get("seuil", Q.seuil_defaut())
    score_init = res_init["score"] if res_init else None
    score_fin = res_fin["score"] if res_fin else None
    justes_fin = len([l for l in lignes if l["fin_juste"]])
    gagnees = len([l for l in lignes if l["fin_juste"] and not l["init_juste"]])
    perdues = len([l for l in lignes if l["init_juste"] and not l["fin_juste"]])
    return {"code": code, "mail": mail, "nom": nom or mail,
            "formation": S.get("nom_formation") or "", "titre": S.get("titre_complet") or "",
            "date_texte": S.get("date_texte") or "", "seuil": seuil,
            "score_init": score_init, "score_fin": score_fin,
            "progression": (score_fin - score_init) if (score_init is not None and score_fin is not None) else None,
            "atteint": (score_fin is not None and score_fin >= seuil),
            "objectifs": objectifs, "questions": lignes,
            "total": len(lignes), "justes_fin": justes_fin,
            "gagnees": gagnees, "perdues": perdues,
            "a_init": res_init is not None, "a_fin": res_fin is not None}
@app.route("/session/<code>/recap/<mail>")
def recap_praticien(code, mail):
    if code not in SESSIONS:
        return "Session inconnue", 404
    from datetime import datetime as dt
    S = fiche_session(code)
    r = _pr_recap(code, mail)
    if not r:
        return "Aucun questionnaire defini pour cette formation", 404
    if not r["a_fin"]:
        return "Ce praticien n'a pas encore repondu a l'evaluation de sortie", 404
    return render_template("recap.html", r=r, edite=dt.now().strftime("%d/%m/%Y"),
                           organisme=S.get("organisme") or "", marque=S.get("marque") or "",
                           formateur=S.get("signature_mail") or S.get("formateur") or "")
@app.route("/session/<code>/dossier/<mail>")
def dossier_apprenant(code, mail):
    """Le dossier de preuves d'une personne, imprimable tel quel.

    Se distingue du recap voisin : le recap est pedagogique et destine a
    l'apprenant, il exige une evaluation de sortie. Celui-ci est destine a un
    controle, il fonctionne meme sur un parcours incomplet, et il restitue la
    satisfaction et l'evaluation a froid que rien ne montrait individuellement.
    """
    import preuve as _preuve
    from datetime import datetime as dt
    if code not in SESSIONS:
        return "Session inconnue", 404
    try:
        d = _preuve.dossier(code, mail)
    except _preuve.LectureRatee as e:
        return ("Le suivi de cette session n'a pas pu être lu (%s). "
                "Réessayez dans un instant : ce n'est pas une pièce manquante." % e), 503
    if not d:
        return "Cette personne n'est pas inscrite sur cette session", 404
    S = fiche_session(code)
    return render_template("dossier.html", d=d, edite=dt.now().strftime("%d/%m/%Y"),
                           organisme=S.get("organisme") or "", marque=S.get("marque") or "")
@app.route("/session/<code>/questionnaire/<mail>/<type_>")
def questionnaire_rempli(code, mail, type_):
    """Un questionnaire tel qu'une personne l'a rempli, question par question.

    Le dossier de preuves voisin montre les SCORES ; cette page montre les
    REPONSES. C'est elle qu'on ouvre quand un auditeur demande a voir le
    questionnaire d'un apprenant — il n'y avait rien a lui montrer avant.
    """
    import preuve as _preuve
    from datetime import datetime as dt
    if code not in SESSIONS:
        return "Session inconnue", 404
    if type_ not in _preuve._INTITULES:
        return "Type de questionnaire inconnu", 404
    try:
        f = _preuve.formulaire(code, mail, type_)
    except _preuve.LectureRatee as e:
        return ("Le suivi de cette session n'a pas pu être lu (%s). "
                "Réessayez dans un instant : ce n'est pas une pièce manquante." % e), 503
    if not f:
        return ("Cette personne n'a pas rempli ce questionnaire, "
                "ou n'est pas inscrite sur cette session"), 404
    S = fiche_session(code)
    return render_template("questionnaire_rempli.html", f=f,
                           edite=dt.now().strftime("%d/%m/%Y"),
                           organisme=S.get("organisme") or "", marque=S.get("marque") or "")
@app.route("/session/<code>/recap/<mail>/envoyer", methods=["POST"])
def envoyer_recap(code, mail):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("mail")
    if _g:
        return jsonify({"ok": False, "message": _g})
    _v = _et_verrou(code, "mail")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import base64
    import journal
    S = fiche_session(code)
    r = _pr_recap(code, mail)
    if not r:
        return jsonify({"ok": False, "message": "Aucun questionnaire defini pour cette formation"})
    if not r["a_fin"]:
        return jsonify({"ok": False, "message": "Ce praticien n'a pas repondu a l'evaluation de sortie"})
    marque = S.get("marque") or S.get("organisme") or ""
    signature = S.get("signature_mail") or S.get("formateur") or ""
    prenom = (r["nom"] or "").split(" ")[0]
    # La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
    # ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
    # au demarrage du script, meme quand aucun mail n'etait a envoyer.
    logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
    C = {"vert": "#0f9e6a", "rouge": "#d03b3b", "gris": "#6b7280", "bleu": "#4f7ef8"}
    h = []
    h.append("<div style=\"font-family:'Helvetica Neue',Arial,sans-serif;max-width:620px;margin:0 auto;color:#2b2f3a;line-height:1.6\">")
    h.append("<div style=\"padding:20px 0 4px\"><img src=\"cid:logo\" alt=\"" + marque + "\" style=\"height:60px\"></div>")
    h.append("<div style=\"height:1px;background:#e6e9f2;margin:8px 0 24px\"></div>")
    h.append("<p><strong>Bonjour " + prenom + ",</strong></p>")
    h.append("<p>Voici le r&eacute;capitulatif de votre &eacute;valuation pour la formation <strong>&laquo; "
             + (r["titre"] or r["formation"]) + " &raquo;</strong> du " + r["date_texte"] + ".</p>")
    h.append("<table style=\"width:100%;border-collapse:collapse;margin:22px 0\"><tr>")
    for lab, val, coul in (("&Agrave; l'entr&eacute;e", (str(r["score_init"]) + " %") if r["score_init"] is not None else "&mdash;", C["gris"]),
                           ("En sortie", str(r["score_fin"]) + " %", C["vert"]),
                           ("Progression", (("+" if r["progression"] >= 0 else "") + str(r["progression"]) + " pts") if r["progression"] is not None else "&mdash;", C["bleu"])):
        h.append("<td style=\"width:33%;text-align:center;border:1px solid #e0e8fb;padding:14px 8px\">"
                 "<div style=\"font-size:11px;color:#8a90a2;text-transform:uppercase;letter-spacing:.5px\">" + lab + "</div>"
                 "<div style=\"font-size:26px;font-weight:600;color:" + coul + ";margin-top:4px\">" + val + "</div></td>")
    h.append("</tr></table>")
    if r["gagnees"]:
        h.append("<p style=\"background:#eafaf3;border-left:3px solid #0f9e6a;padding:11px 14px;font-size:14px\">"
                 "Vous avez acquis <strong>" + str(r["gagnees"]) + " notion(s)</strong> au cours de la journ&eacute;e, "
                 "et vous r&eacute;pondez juste &agrave; <strong>" + str(r["justes_fin"]) + " question(s) sur "
                 + str(r["total"]) + "</strong>.</p>")
    if r["objectifs"]:
        h.append("<p style=\"margin-top:24px\"><strong>Par objectif p&eacute;dagogique</strong></p>")
        h.append("<table style=\"width:100%;border-collapse:collapse;font-size:13px\">")
        for o in r["objectifs"]:
            fleche = ""
            if o["init"] is not None and o["fin"] is not None:
                fleche = str(o["init"]) + " % &rarr; <strong>" + str(o["fin"]) + " %</strong>"
            h.append("<tr><td style=\"padding:7px 0;border-bottom:1px solid #eef0f5\">" + o["libelle"]
                     + "</td><td style=\"padding:7px 0;border-bottom:1px solid #eef0f5;text-align:right;white-space:nowrap\">"
                     + (fleche or "&mdash;") + "</td></tr>")
        h.append("</table>")
    h.append("<p style=\"margin-top:26px\"><strong>Le corrig&eacute; comment&eacute;</strong></p>")
    for i, q in enumerate(r["questions"], 1):
        bord = C["vert"] if q["fin_juste"] else C["rouge"]
        h.append("<div style=\"border-left:3px solid " + bord + ";padding:2px 0 2px 13px;margin-bottom:18px\">")
        h.append("<div style=\"font-size:11px;color:#8a90a2\">Question " + str(i) + "</div>")
        h.append("<div style=\"font-size:14px;font-weight:600;margin:3px 0 7px\">" + q["enonce"] + "</div>")
        if not q["fin_juste"] and q["fin_texte"]:
            h.append("<div style=\"font-size:13px;color:" + C["rouge"] + "\">Votre r&eacute;ponse : " + q["fin_texte"] + "</div>")
        h.append("<div style=\"font-size:13px;color:" + C["vert"] + "\">R&eacute;ponse attendue : <strong>" + q["attendu_texte"] + "</strong></div>")
        if q["explication"]:
            h.append("<div style=\"font-size:13px;color:#5b6172;margin-top:5px;font-style:italic\">" + q["explication"] + "</div>")
        h.append("</div>")
    h.append("<p style=\"font-size:13px;color:#5b6172;margin-top:26px\">Ce r&eacute;capitulatif est personnel. "
             "N'h&eacute;sitez pas &agrave; r&eacute;pondre &agrave; ce mail si une r&eacute;ponse vous surprend ou m&eacute;rite discussion.</p>")
    h.append("<p style=\"margin-top:22px\">Bien &agrave; vous,<br><strong>" + signature + ", " + marque + "</strong></p></div>")
    try:
        message = MIMEMultipart("related")
        message["To"] = r["mail"]
        import mails as _m_exp
        _exp = _m_exp.expediteur(S if "S" in dir() else None)
        if _exp:
            message["From"] = _exp
        message["Subject"] = "Votre progression et le corrige commente \u00b7 " + (r["titre"] or r["formation"])
        corps = MIMEMultipart("alternative")
        import mails as _mails
        corps.attach(MIMEText(_mails.poser_logo("".join(h), logo_bytes), "html"))
        message.attach(corps)
        logo = MIMEImage(logo_bytes)
        logo.add_header("Content-ID", "<logo>")
        logo.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(logo)
        # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
        # decide d'ou part le mail — deux entites, deux adresses.
        courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
    except Exception as e:
        return jsonify({"ok": False, "message": "Envoi impossible : " + str(e)})
    try:
        journal.ecrire("Récapitulatif pédagogique envoyé", r["nom"], str(r["score_fin"]) + " %", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "nom": r["nom"], "mail": r["mail"]})
def _ap_dossier(mail):
    import suivi as _suivi
    import questionnaires as Q
    mail = (mail or "").strip().lower()
    fiches = {code: fiche_session(code) for code in SESSIONS}
    brut = _grilles_suivi(list(fiches))
    identite = {}
    parcours = []
    for code in SESSIONS:
        S = fiches[code]
        for numero, r in enumerate(brut.get(code, [])[1:], 2):
            if not r or len(r) <= _suivi.COL["mail"]:
                continue
            d = {}
            for cle, idx in _suivi.COL.items():
                d[cle] = (r[idx] if len(r) > idx else "") or ""
            if (d.get("mail") or "").strip().lower() != mail:
                continue
            if not identite or d.get("horodateur", "") > identite.get("_h", ""):
                identite = {"nom": (d.get("nom") or "").upper(), "prenom": d.get("prenom") or "",
                            "mail": d.get("mail") or "", "telephone": d.get("telephone") or "",
                            "ville": d.get("ville") or "", "_h": d.get("horodateur") or ""}
            try:
                montant = float(str(d.get("montant_recu") or 0).replace(",", ".") or 0)
            except Exception:
                montant = 0
            try:
                du = float(str(d.get("montant_du") or S.get("tarif") or 0).replace(",", ".") or 0)
            except Exception:
                du = 0
            statut = _suivi.calculer_statut(d)
            docs = []
            if d.get("lien_pdf"):
                docs.append({"nom": "Convention signée", "lien": d["lien_pdf"], "icone": "ti-file-check"})
            if d.get("lien_facture"):
                docs.append({"nom": "Facture", "lien": d["lien_facture"], "icone": "ti-receipt"})
            if d.get("lien_attestation"):
                docs.append({"nom": "Attestation", "lien": d["lien_attestation"], "icone": "ti-certificate"})
            etapes = [
                {"libelle": "Convention signée", "fait": bool(d.get("signe_le"))},
                {"libelle": "Règlement reçu", "fait": bool(d.get("paiement_recu_le"))},
                {"libelle": "Facture envoyée", "fait": bool(d.get("facture_envoyee_le") or d.get("lien_facture"))},
                {"libelle": "Évaluation d'entrée", "fait": bool(d.get("eval_init_le"))},
                {"libelle": "Évaluation de sortie", "fait": bool(d.get("eval_fin_le"))},
                {"libelle": "Satisfaction", "fait": bool(d.get("satisfaction_le"))},
                {"libelle": "Attestation", "fait": bool(d.get("lien_attestation"))},
            ]
            def nb(v):
                try:
                    return float(str(v).replace(",", "."))
                except Exception:
                    return None
            parcours.append({
                "numero": numero, "feuille": S["sheet_suivi"], "onglet": S["onglet_suivi"],
                "identite": {"nom": (d.get("nom") or "").upper(), "prenom": d.get("prenom") or "",
                             "telephone": d.get("telephone") or "", "ville": d.get("ville") or ""},
                "code": code, "formation": S.get("nom_formation") or "",
                "titre": S.get("titre_complet") or "", "date_texte": S.get("date_texte") or "",
                "debut": S.get("date_debut") or "", "adresse": S.get("adresse") or "",
                "montant_du": du, "montant_recu": montant, "statut": statut,
                "annule": bool(d.get("annule_le")), "present": bool(d.get("present")),
                "score_init": nb(d.get("score_init")), "score_fin": nb(d.get("score_fin")),
                "satisfaction": nb(d.get("note_satisfaction")),
                "docs": docs, "etapes": etapes,
                # Les questionnaires REELLEMENT remplis, pour ouvrir la
                # restitution directement depuis la fiche. Les dates de relevee
                # sont deja dans le suivi : aucun appel supplementaire.
                "questionnaires": [q for q in (
                    {"type": "init", "nom": "Évaluation d'entrée",
                     "fait": bool(d.get("eval_init_le"))},
                    {"type": "fin", "nom": "Évaluation de sortie",
                     "fait": bool(d.get("eval_fin_le"))},
                    {"type": "satisfaction", "nom": "Satisfaction",
                     "fait": bool(d.get("satisfaction_le"))},
                ) if q["fait"]],
                "horodateur": d.get("horodateur") or "",
                "dates": {"inscription": (d.get("horodateur") or "")[:10],
                          "signe": (d.get("signe_le") or "")[:10],
                          "paye": (d.get("paiement_recu_le") or "")[:10],
                          "eval_fin": (d.get("eval_fin_le") or "")[:10],
                          "attestation": (d.get("attestation_le") or "")[:10]},
            })
    parcours.sort(key=lambda x: x["debut"], reverse=True)
    satisfactions = []
    try:
        if parcours:
            recues = _sb("Questionnaires?type=eq.satisfaction&mail=eq." + mail + "&select=session_code,reponses")
            for r in recues:
                rep = r.get("reponses") or {}
                # Chaque reponse vient de SA session : c'est son modele fige
                # qui dit quelles questions ont ete posees (C5).
                _sc = r.get("session_code") or ""
                _mod = Q.SATISFACTION
                try:
                    _fc = SESSIONS.get(_sc, {}).get("formation") or ""
                    _m = _Q.modele_session(_sc, _fc, "satisfaction")
                    if _m and _m.get("notes"):
                        _mod = _m
                except Exception:
                    pass
                notes = []
                detail = []
                for n in _mod["notes"]:
                    try:
                        v = float(rep.get(n["id"]))
                    except Exception:
                        continue
                    notes.append(v)
                    detail.append({"libelle": n["libelle"], "note": v,
                                   "largeur": int(round(100.0 * v / 5))})
                verbatims = []
                for o in _mod["ouvertes"]:
                    t = rep.get(o["id"])
                    if isinstance(t, str) and t.strip():
                        verbatims.append({"question": o["libelle"], "texte": t.strip()})
                reco = None
                try:
                    reco = float(rep.get(_mod["recommandation"]["id"]))
                except Exception:
                    pass
                nomf = ""
                for p in parcours:
                    if p["code"] == r.get("session_code"):
                        nomf = p["formation"]
                satisfactions.append({"session": r.get("session_code"), "formation": nomf,
                                      "globale": round(sum(notes) / len(notes), 1) if notes else None,
                                      "detail": detail, "reco": reco, "verbatims": verbatims})
    except Exception:
        pass
    actifs = [p for p in parcours if not p["annule"]]
    ca = sum(p["montant_recu"] for p in actifs)
    attendu = sum(p["montant_du"] for p in actifs)
    complets = len([p for p in actifs if p["montant_recu"] and p["docs"]])
    evenements = []
    for p in parcours:
        for cle, libelle in (("inscription", "Inscription à"), ("signe", "Convention signée pour"),
                             ("paye", "Règlement reçu pour"), ("eval_fin", "Questionnaires complétés pour"),
                             ("attestation", "Attestation émise pour")):
            v = p["dates"].get(cle)
            if v:
                evenements.append({"date": v, "texte": libelle + " " + p["formation"],
                                   "code": p["code"], "type": cle})
    def tri(e):
        v = e["date"]
        if "/" in v:
            p = v.split("/")
            return (p[2] + p[1] + p[0]) if len(p) == 3 else v
        return v.replace("-", "")
    evenements.sort(key=tri, reverse=True)
    premiere = ""
    if parcours:
        dates = [p["dates"]["inscription"] for p in parcours if p["dates"]["inscription"]]
        if dates:
            premiere = sorted(dates, key=lambda v: tri({"date": v}))[0]
    if not identite:
        identite = {"nom": "", "prenom": "", "mail": mail, "telephone": "", "ville": ""}
    initiales = ((identite.get("prenom") or " ")[0] + (identite.get("nom") or " ")[0]).upper().strip()
    ordonnees = sorted(parcours, key=lambda x: x.get("horodateur") or "", reverse=True)
    ecarts = []
    if len(ordonnees) > 1:
        ref = ordonnees[0]["identite"]
        for cle, libelle in (("nom", "Nom"), ("prenom", "Prénom"),
                             ("telephone", "Téléphone"), ("ville", "Ville")):
            valeurs = {(o["identite"].get(cle) or "").strip() for o in ordonnees if (o["identite"].get(cle) or "").strip()}
            if len(valeurs) > 1:
                ecarts.append({"cle": cle, "libelle": libelle, "retenu": (ref.get(cle) or "").strip()})
    return {"fiches": ordonnees, "nb_fiches": len(ordonnees), "ecarts": ecarts,
            "identite": identite, "initiales": initiales or "?",
            "parcours": parcours, "actifs": len(actifs), "annulees": len(parcours) - len(actifs),
            "ca": ca, "attendu": attendu,
            "completion": int(round(100.0 * complets / len(actifs))) if actifs else None,
            "premiere": premiere, "satisfactions": satisfactions,
            "evenements": evenements[:12],
            "formations": sorted({p["formation"] for p in parcours})}
@app.route("/apprenant/<mail>")
def fiche_apprenant(mail):
    """Conservee : d'anciens liens y menent. Elle rend la MEME fiche, volet
    contact compris quand la personne figure dans la base."""
    import contacts as C
    volet = None
    try:
        volet = _ct_contexte(C.rapprocher(mail=mail))
    except Exception:
        pass
    return render_template("apprenant.html", d=_ap_dossier(mail), c=volet)
@app.route("/session/<code>/attestations/liste")
def liste_attestations(code):
    """Inscrits actifs de la session, avec l'etat de leur attestation.
    Alimente la fenetre de validation avant envoi."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    try:
        lignes = _lignes_onglet(S)
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)})
    gens = []
    for l in lignes:
        if l.get("annule_le") or "recontact" in (l.get("demande") or "").lower():
            continue
        if l.get("file_attente_le") and not l.get("promu_le"):
            continue
        lien = l.get("lien_attestation") or ""
        gens.append({"mail": (l.get("mail") or "").strip(),
                     "nom": ((l.get("nom") or "").upper() + " " + (l.get("prenom") or "")).strip(),
                     "prete": bool(lien and "/d/" in lien),
                     "lien": lien,
                     "envoyee_le": l.get("attestation_envoyee_le") or ""})
    gens.sort(key=lambda g: g["nom"])
    return jsonify({"ok": True, "gens": gens,
                    "formation": S.get("nom_formation") or "",
                    "date_texte": S.get("date_texte") or "",
                    "pretes": len([g for g in gens if g["prete"]])})
def _pointer_presences(code, mails_presents):
    """Ecrit la colonne `present` : coche pour les destinataires retenus,
    vide pour les autres. Rend le nombre de presences enregistrees.
    Ne bloque jamais l'envoi : une presence non ecrite est signalee, pas fatale."""
    from connexion import service_sheets
    import suivi as _suivi
    import journal
    try:
        S = fiche_session(code)
        lignes = _lignes_onglet(S)
    except Exception:
        return {"ok": False, "nb": 0, "message": "suivi illisible"}
    retenus = {m.strip().lower() for m in mails_presents}
    donnees, presents = [], []
    for l in lignes:
        if l.get("annule_le"):
            continue
        m = (l.get("mail") or "").strip().lower()
        valeur = "oui" if m in retenus else ""
        if (l.get("present") or "") == valeur:
            continue
        donnees.append((l["_numero"], {"present": valeur}))
        if valeur:
            presents.append(((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip())
    if not donnees:
        return {"ok": True, "nb": 0, "message": "presences deja a jour"}
    try:
        _suivi.ecrire_lignes(donnees, code)
    except Exception as e:
        return {"ok": False, "nb": 0, "message": str(e)[:120]}
    for qui in presents:
        try:
            journal.ecrire("Présence pointée", qui, "", "", code)
        except Exception:
            pass
    return {"ok": True, "nb": len(presents), "modifiees": len(donnees)}
@app.route("/session/<code>/attestations/envoyer", methods=["POST"])
def envoyer_attestations(code):
    """Envoie les attestations aux seuls destinataires coches dans la fenetre.
    Les non retenus conservent leur PDF dans le Drive et pourront etre
    servis plus tard : rien n'est supprime ni regenere."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _g = _of_garde("attestation")
    if _g:
        return jsonify({"ok": False, "message": _g})
    mails = [m.strip().lower() for m in (request.form.get("mails") or "").split(",") if m.strip()]
    if not mails:
        return jsonify({"ok": False, "message": "Aucun destinataire selectionne."})
    # Le geste « decochez les personnes absentes » exprime deja la presence :
    # on l'enregistre. Sans cela, la colonne `present` n'etait plus ecrite par
    # personne depuis la suppression de pointer_presences.py (C7), et le
    # compteur nb_presents du bilan restait a zero — une attestation atteste
    # pourtant d'une presence effective.
    presences = _pointer_presences(code, mails)
    r = subprocess.run([sys.executable, "envoyer_attestation.py", code, ",".join(mails)],
                       capture_output=True, text=True, cwd=DOSSIER, timeout=600)
    sortie = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    if r.returncode != 0:
        d = [l.strip() for l in r.stderr.splitlines() if l.strip()]
        return jsonify({"ok": False, "message": "Envoi impossible : "
                        + (d[-1][:180] if d else "erreur inconnue"), "sortie": sortie[-12:]})
    envoyes = len([l for l in sortie if "Attestation envoyee" in l])
    return jsonify({"ok": True, "envoyes": envoyes, "demandes": len(mails),
                    "presences": presences, "sortie": sortie[-20:]})
@app.route("/session/<code>/emargement/generer", methods=["POST"])
def regenerer_emargement(code):
    """Reconstruit la feuille d'emargement vierge a partir des inscrits actuels.
    Le code de session est transmis au script : sans lui, il travaillerait sur
    SESSION_ACTIVE et produirait la feuille d'une autre session (point A2)."""
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    _v = _et_verrou(code, "structure")
    if _v:
        return jsonify({"ok": False, "message": _v})
    from datetime import datetime as dt
    S = fiche_session(code)
    try:
        signe_le = SESSIONS_MOD.etat(code)["emargement_signe_le"]
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture de l'état : " + str(e)})
    if signe_le and (request.form.get("confirmer") or "") != "1":
        return jsonify({"ok": False, "signe": True, "signe_le": signe_le,
                        "message": "Une feuille d'émargement signée a été reçue le "
                                   + signe_le + ". En régénérer une vierge laisserait "
                                   "deux feuilles contradictoires dans le même dossier : "
                                   "celle qui a été signée, et une nouvelle dont la liste "
                                   "des participants est différente."})
    r = subprocess.run([sys.executable, "generer_emargement.py", code],
                       capture_output=True, text=True, cwd=DOSSIER, timeout=300)
    if r.returncode != 0:
        d = [l.strip() for l in r.stderr.splitlines() if l.strip()]
        return jsonify({"ok": False, "message": "Génération impossible : "
                        + (d[-1][:180] if d else "erreur inconnue")})
    lien, resume = _lien_produit(r.stdout), ""
    for l in r.stdout.splitlines():
        if "participant(s)" in l:
            resume = l.strip().lstrip("-> ")
    if not lien:
        return jsonify({"ok": False, "message": "La feuille n'a pas été produite. " + resume})
    maintenant = dt.now().strftime("%d/%m/%Y %H:%M")
    try:
        SESSIONS_MOD.poser_etats(code, {"emargement_genere_le": maintenant,
                                        "lien_emargement": lien})
    except Exception as e:
        return jsonify({"ok": False, "message": "Feuille générée mais lien non enregistré : " + str(e)})
    return jsonify({"ok": True, "lien": lien, "le": maintenant, "resume": resume})
@app.route("/session/<code>/emargement/supprimer", methods=["POST"])
def supprimer_emargement(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import journal
    S = fiche_session(code)
    try:
        # On delie la feuille SIGNEE : la vierge et sa date de generation restent.
        SESSIONS_MOD.poser_etats(code, {"emargement_signe_le": "",
                                        "lien_emargement_signe": ""})
    except Exception as e:
        return jsonify({"ok": False, "message": "Écriture de l'état : " + str(e)})
    try:
        journal.ecrire("Émargement signé délié", "", S.get("nom_formation") or code, "", code)
    except Exception:
        pass
    return jsonify({"ok": True})
_ID_NOTES = ["s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08",
             "s21", "s22", "s23", "s24", "s25", "s26", "s27", "s28", "s29", "s30"]
_ID_OUVERTES = ["s11", "s12", "s13", "s14", "s15"]
def _ed_texte(v, defaut=""):
    if v is None:
        return defaut
    return str(v).strip() or defaut
def _ed_id_libre(prefixe, utilises):
    """Premier identifiant disponible de la forme q01, q02... pour ce prefixe."""
    n = 1
    while ("%s%02d" % (prefixe, n)) in utilises:
        n += 1
    return "%s%02d" % (prefixe, n)
def _ed_garder_id(brut, prefixe, utilises, reserve=None):
    """Conserve l'identifiant existant d'un element, ou en attribue un neuf.

    C'EST LA CLE SOUS LAQUELLE LES REPONSES DES PARTICIPANTS SONT DEJA
    STOCKEES DANS SUPABASE. La reattribuer — ce que faisait la version
    precedente, par position — rendait toutes les reponses des sessions
    passees inexploitables : Q.corriger ne retrouvait plus ses questions et
    comptait tout faux, sans le moindre message d'erreur.

    reserve : liste d'identifiants imposee (les notes de satisfaction et les
    questions ouvertes tirent les leurs de _ID_NOTES et _ID_OUVERTES)."""
    ident = _ed_texte(brut.get("id"))
    if ident and ident not in utilises:
        utilises.add(ident)
        return ident
    if reserve is not None:
        for candidat in reserve:
            if candidat not in utilises:
                utilises.add(candidat)
                return candidat
        return ""
    neuf = _ed_id_libre(prefixe, utilises)
    utilises.add(neuf)
    return neuf
def _ed_normaliser_evaluation(brut):
    objectifs = {}
    for o in (brut.get("objectifs") or []):
        cle = _ed_texte(o.get("cle")).upper()[:2]
        libelle = _ed_texte(o.get("libelle"))
        if cle and libelle:
            objectifs[cle] = libelle
    questions = []
    utilises = set()
    for q in (brut.get("questions") or []):
        enonce = _ed_texte(q.get("enonce"))
        if not enonce:
            continue
        type_ = "vf" if _ed_texte(q.get("type")) == "vf" else "qcm"
        if type_ == "vf":
            props = ["Vrai", "Faux"]
        else:
            props = [_ed_texte(p) for p in (q.get("propositions") or [])]
            props = [p for p in props if p][:4]
            while len(props) < 2:
                props.append("Proposition " + str(len(props) + 1))
        try:
            reponse = int(q.get("reponse") or 0)
        except Exception:
            reponse = 0
        if reponse < 0 or reponse >= len(props):
            reponse = 0
        try:
            poids = int(q.get("poids") or 1)
        except Exception:
            poids = 1
        obj = _ed_texte(q.get("objectif")).upper()[:2]
        if obj not in objectifs:
            obj = sorted(objectifs)[0] if objectifs else "A"
        questions.append({"id": _ed_garder_id(q, "q", utilises), "objectif": obj, "type": type_,
                          "poids": max(1, min(3, poids)), "enonce": enonce,
                          "propositions": props, "reponse": reponse,
                          "explication": _ed_texte(q.get("explication"))})
    try:
        seuil = int(brut.get("seuil") or 70)
    except Exception:
        seuil = 70
    return {"titre": _ed_texte(brut.get("titre"), "Questionnaire d'évaluation"),
            "seuil": max(0, min(100, seuil)),
            "objectifs": objectifs or {"A": "Objectif principal"},
            "questions": questions}
def _ed_normaliser_satisfaction(brut):
    axes = {}
    for a in (brut.get("axes") or []):
        cle = _ed_texte(a.get("cle"))
        libelle = _ed_texte(a.get("libelle"))
        if cle and libelle:
            axes[cle] = libelle
    if not axes:
        axes = {"avant": "Avant la formation", "pendant": "Pendant la formation", "apres": "Résultats et suites"}
    notes = []
    pris = set()
    for n in (brut.get("notes") or []):
        libelle = _ed_texte(n.get("libelle"))
        if not libelle:
            continue
        axe = _ed_texte(n.get("axe"))
        if axe not in axes:
            axe = sorted(axes)[0]
        ident = _ed_garder_id(n, "s", pris, _ID_NOTES)
        if not ident:
            continue
        notes.append({"id": ident, "axe": axe, "libelle": libelle})
    ouvertes = []
    pris_o = set()
    for o in (brut.get("ouvertes") or []):
        libelle = _ed_texte(o.get("libelle"))
        if not libelle:
            continue
        ident = _ed_garder_id(o, "o", pris_o, _ID_OUVERTES)
        if ident:
            ouvertes.append({"id": ident, "libelle": libelle})
    reco = brut.get("recommandation") or {}
    ad = brut.get("adaptation") or {}
    props = [_ed_texte(p) for p in (ad.get("propositions") or [])]
    props = [p for p in props if p]
    if len(props) < 2:
        props = ["Non concerné", "Oui, pris en compte", "Oui, partiellement pris en compte", "Oui, non pris en compte"]
    return {"titre": _ed_texte(brut.get("titre"), "Questionnaire de satisfaction"),
            "axes": axes, "notes": notes,
            "recommandation": {"id": _ed_texte(reco.get("id")) or "s09",
                               "libelle": _ed_texte(reco.get("libelle"), "Recommanderiez-vous cette formation ?")},
            "adaptation": {"id": _ed_texte(ad.get("id")) or "s10",
                           "libelle": _ed_texte(ad.get("libelle"), "Aviez-vous un besoin particulier d'adaptation ?"),
                           "propositions": props},
            "ouvertes": ouvertes}
# Mails encore construits en dur dans le code : ils apparaissent dans la
# bibliotheque pour que l'ecart soit visible, marques comme non modifiables.
# Croire qu'on peut modifier un mail fige serait pire que de savoir qu'il l'est.
_TP_MAILS_FIGES = [
    ("Demande d'annulation", "Accusé de réception d'une demande d'annulation", "app.py"),
    ("Relance de signature", "Relance manuelle depuis la fiche de session", "app.py"),
    ("Relance de règlement", "Relance manuelle depuis la fiche de session", "app.py"),
    ("Envoi groupé", "Renvoi d'un document à plusieurs inscrits", "app.py"),
    ("Ouverture d'un questionnaire", "Invitation à répondre à un questionnaire", "app.py"),
    ("Récapitulatif pédagogique", "Bilan envoyé au participant après la formation", "app.py"),
]
_TP_FAMILLES = [
    ("evaluation",   "Évaluation des connaissances", "ti-school",       "#4f7ef8", "modele_evaluation"),
    ("satisfaction", "Satisfaction",                 "ti-star",         "#d4890a", "modele_satisfaction"),
    ("froid",        "Évaluation à froid",           "ti-clock-hour-9", "#7c5bf7", "modele_froid"),
]
def _tp_nom_formation(code):
    from sessions import FORMATIONS
    return (FORMATIONS.get(code) or {}).get("nom_formation") or code
def _tp_sans_modele(cle):
    """Formations qui n'ont AUCUN modele rattache pour cette cle : ce sont elles
    qui retombent sur le texte fourni avec DFM. C'est ce qui donne son sens au
    statut « fourni avec DFM » — ce n'est pas decoratif, c'est la valeur par
    defaut effective."""
    from sessions import FORMATIONS
    return [{"code": c, "nom": _tp_nom_formation(c)}
            for c, f in FORMATIONS.items() if not (f or {}).get(cle)]
def _tp_usages_mail(usage, identifiant):
    from sessions import FORMATIONS
    return [c for c, f in FORMATIONS.items()
            if (f or {}).get("modele_mail_" + usage) == identifiant]
def _tp_lignes():
    """Une ligne par modele, toutes familles confondues, pour la liste."""
    import modeles
    import mails as _mails
    import questionnaires as Q
    from sessions import FORMATIONS
    lignes = []
    for type_, nom_famille, icone, couleur, cle in _TP_FAMILLES:
        for m in modeles.lister(type_):
            n = len(m.get("questions") or m.get("notes") or [])
            lignes.append({
                "famille": type_, "famille_nom": nom_famille,
                "icone": icone, "couleur": couleur,
                "id": m["id"], "titre": m.get("titre") or m["id"],
                "detail": ("%d question(s)" % n) if type_ == "evaluation" else ("%d item(s) noté(s)" % n),
                "usages": [{"code": c, "nom": _tp_nom_formation(c)}
                           for c in modeles.utilise_par(type_, m["id"])],
                "source": "perso", "modifie_le": m.get("modifie_le") or "",
                "apercu": "/templates/questionnaire/%s/%s/apercu" % (type_, m["id"]),
                "dupliquer": "/templates/questionnaire/%s/%s/dupliquer" % (type_, m["id"]),
                "edition": "/templates/questionnaire/%s/%s" % (type_, m["id"]),
            })
        if type_ == "evaluation":
            for code, ev in Q.EVALUATIONS.items():
                sert = ([{"code": code, "nom": _tp_nom_formation(code)}]
                        if code in FORMATIONS and not (FORMATIONS[code] or {}).get(cle) else [])
                lignes.append({
                    "famille": type_, "famille_nom": nom_famille,
                    "icone": icone, "couleur": couleur,
                    "id": code, "titre": (ev.get("titre") or code) + " — trame DFM",
                    "detail": "%d question(s)" % len(ev.get("questions") or []),
                    "usages": sert, "source": "dfm", "modifie_le": "",
                    "apercu": "/templates/questionnaire/evaluation/%s/apercu" % code,
                    "edition": "/templates/questionnaire/evaluation/%s" % code,
                })
        else:
            trame = Q.FROID if type_ == "froid" else Q.SATISFACTION
            lignes.append({
                "famille": type_, "famille_nom": nom_famille,
                "icone": icone, "couleur": couleur,
                "id": "type", "titre": (trame.get("titre") or type_) + " — trame DFM",
                "detail": "%d item(s) noté(s)" % len(trame.get("notes") or []),
                "usages": _tp_sans_modele(cle), "source": "dfm", "modifie_le": "",
                "apercu": "/templates/questionnaire/%s/type/apercu" % type_,
                "edition": "/templates/questionnaire/%s/type" % type_,
            })
    for usage, infos in _mails.USAGES.items():
        for m in _mails.lister(usage):
            lignes.append({
                "famille": "mail", "famille_nom": "Mails",
                "icone": infos.get("icone") or "ti-mail",
                "couleur": infos.get("couleur") or "#0f9e6a",
                "id": m["id"], "usage": usage, "titre": m.get("titre") or m["id"],
                "detail": "%d bloc(s) · %s" % (len(m.get("blocs") or []), infos["nom"].lower()),
                "usages": [{"code": c, "nom": _tp_nom_formation(c)}
                           for c in _tp_usages_mail(usage, m["id"])],
                "source": "perso", "modifie_le": m.get("modifie_le") or "",
                "apercu": "/templates/mail/%s/%s/apercu" % (usage, m["id"]),
                "dupliquer": "/templates/mail/%s/%s/dupliquer" % (usage, m["id"]),
                "edition": "/templates/mail/%s/%s" % (usage, m["id"]),
            })
        d = _mails.DEFAUTS.get(usage) or {}
        lignes.append({
            "famille": "mail", "famille_nom": "Mails",
            "icone": infos.get("icone") or "ti-mail",
            "couleur": infos.get("couleur") or "#0f9e6a",
            "id": "defaut-" + usage, "usage": usage,
            "titre": (d.get("titre") or infos["nom"]) + " — trame DFM",
            "detail": "%d bloc(s) · %s" % (len(_mails.BLOCS_DEFAUTS.get(usage) or []), infos["nom"].lower()),
            "usages": _tp_sans_modele("modele_mail_" + usage), "source": "dfm", "modifie_le": "",
            "apercu": "/templates/mail/%s/defaut/apercu" % usage,
            "edition": "/templates/mail/%s/defaut" % usage,
        })
    for nom, quand, ou in _TP_MAILS_FIGES:
        lignes.append({
            "famille": "mail", "famille_nom": "Mails",
            "icone": "ti-lock", "couleur": "#8a90a2",
            "id": "", "usage": "", "titre": nom,
            "detail": quand + " · écrit dans " + ou,
            "usages": [], "source": "fige", "modifie_le": "",
            "edition": "",
        })
    return lignes
@app.route("/templates")
def page_templates():
    import mails as _mails
    lignes = _tp_lignes()
    familles = [{"cle": c, "nom": n, "icone": i, "couleur": co}
                for c, n, i, co, _ in _TP_FAMILLES]
    familles.append({"cle": "mail", "nom": "Mails", "icone": "ti-mail", "couleur": "#0f9e6a"})
    # COMMUNICATIONS : messages qui ne dependent d'aucune session. Famille a
    # part pour que l'editeur ne propose jamais de balise de session — une
    # balise offerte finit par etre utilisee, et le message partirait troue.
    familles.append({"cle": "communication", "nom": "Communications",
                     "icone": "ti-speakerphone", "couleur": "#c2492f"})
    for f in familles:
        f["lignes"] = [l for l in lignes if l["famille"] == f["cle"]]
    import communications as _com
    for m in _com.lister():
        for f in familles:
            if f["cle"] == "communication":
                f["lignes"].append({
                    "famille": "communication", "famille_nom": "Communications",
                    "icone": "ti-speakerphone", "couleur": "#c2492f",
                    "id": m["id"], "titre": m.get("titre") or m["id"],
                    "detail": m.get("objet") or "", "usages": [],
                    "source": "perso", "modifie_le": m.get("modifie_le") or "",
                    "apercu": "/templates/communication/%s/apercu" % m["id"],
                    "lien": "/templates/communication/%s" % m["id"]})
    return render_template("templates.html", familles=familles,
                           usages_mail=[{"cle": u, "nom": i["nom"]} for u, i in _mails.USAGES.items()],
                           total=len(lignes),
                           nb_dfm=len([l for l in lignes if l["source"] == "dfm"]),
                           nb_orphelins=len([l for l in lignes if not l["usages"]]))
@app.route("/templates/questionnaire/<type_>/<identifiant>")
def editeur_questionnaire(type_, identifiant):
    import modeles
    import questionnaires as Q
    if type_ not in ("evaluation", "satisfaction", "froid"):
        return redirect("/templates")
    fiche = None
    if identifiant not in ("nouveau",):
        fiche = modeles.modele(type_, identifiant)
        if fiche is None and type_ == "evaluation":
            interne = Q.EVALUATIONS.get(identifiant)
            if interne:
                fiche = dict(interne)
                fiche["id"] = ""
                fiche["titre"] = (interne.get("titre") or identifiant) + " (copie)"
        if fiche is None and identifiant == "type":
            source = Q.FROID if type_ == "froid" else Q.SATISFACTION
            fiche = dict(source)
            fiche["id"] = ""
            fiche["titre"] = (source.get("titre") or "Modèle") + " (copie)"
    if fiche is None:
        if type_ == "evaluation":
            depart = {"A": "", "B": "", "C": ""}
            proposes = [x for x in (request.args.get("objectifs") or "").split("|") if x.strip()]
            if proposes:
                depart = {}
                for i, libelle in enumerate(proposes[:8]):
                    depart[chr(65 + i)] = libelle.strip()
            fiche = {"id": "", "titre": "", "seuil": 70,
                     "objectifs": depart, "questions": []}
        else:
            fiche = dict(Q.FROID if type_ == "froid" else Q.SATISFACTION)
            fiche["id"] = ""
            fiche["titre"] = ""
    return render_template("editeur.html", type_=type_, fiche=fiche,
                           retour=request.args.get("retour") or "")
@app.route("/templates/questionnaire/<type_>", methods=["POST"])
def enregistrer_questionnaire(type_):
    import modeles
    import journal
    if type_ not in ("evaluation", "satisfaction", "froid"):
        return jsonify({"ok": False, "message": "Type inconnu"})
    brut = request.get_json(silent=True) or {}
    if type_ == "evaluation":
        fiche = _ed_normaliser_evaluation(brut)
        if not fiche["questions"]:
            return jsonify({"ok": False, "message": "Aucune question valide : chaque question doit avoir un enonce."})
    else:
        fiche = _ed_normaliser_satisfaction(brut)
        if type_ == "froid":
            fiche["adaptation"] = None
        if not fiche["notes"]:
            return jsonify({"ok": False, "message": "Aucun item note : ajoute au moins une question notee."})
    if not fiche["titre"]:
        return jsonify({"ok": False, "message": "Donne un titre a ce modele."})
    identifiant = _ed_texte(brut.get("id"))
    try:
        identifiant = modeles.sauver(type_, identifiant, fiche)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    try:
        journal.ecrire("Modèle de questionnaire enregistré", "", fiche["titre"])
    except Exception:
        pass
    return jsonify({"ok": True, "id": identifiant, "titre": fiche["titre"],
                    "nb": len(fiche.get("questions") or fiche.get("notes") or [])})
@app.route("/templates/questionnaire/<type_>/<identifiant>/supprimer", methods=["POST"])
def supprimer_questionnaire(type_, identifiant):
    import modeles
    if type_ not in ("evaluation", "satisfaction", "froid"):
        return jsonify({"ok": False, "message": "Type inconnu"})
    usages = modeles.utilise_par(type_, identifiant)
    if usages:
        noms = [{"code": c, "nom": _tp_nom_formation(c)} for c in usages]
        return jsonify({"ok": False, "usages": noms,
                        "message": "Ce modèle est rattaché à " + str(len(noms))
                        + " formation(s). Le supprimer les ferait retomber sans "
                        "prévenir sur le texte fourni avec DFM."})
    if modeles.supprimer(type_, identifiant):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "message": "Modele introuvable"})
@app.route("/templates/liste/<type_>")
def liste_modeles(type_):
    import modeles
    import questionnaires as Q
    if type_ not in ("evaluation", "satisfaction", "froid"):
        return jsonify({"ok": False, "message": "Type inconnu"})
    sortie = []
    for m in modeles.lister(type_):
        sortie.append({"id": m["id"], "titre": m.get("titre") or m["id"],
                       "nb": len(m.get("questions") or m.get("notes") or [])})
    if type_ == "satisfaction":
        sortie.insert(0, {"id": "", "titre": "Trame type fournie avec DFM",
                          "nb": len(Q.SATISFACTION.get("notes") or [])})
    if type_ == "froid":
        sortie.insert(0, {"id": "", "titre": "Questionnaire standard fourni avec DFM",
                          "nb": len(Q.FROID.get("notes") or [])})
    return jsonify({"ok": True, "modeles": sortie})
def _coh_normaliser(t):
    import re as _r
    return _r.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()
def _coh_objectifs_formation(code_formation):
    try:
        from sessions import FORMATIONS
    except Exception:
        return []
    f = FORMATIONS.get(code_formation) or {}
    return [x for x in (f.get("objectifs") or []) if (x or "").strip()]
def _coh_modele(code_formation):
    import questionnaires as Q
    ev = Q.pour_formation(code_formation)
    if not ev:
        return {}
    return dict(ev.get("objectifs") or {})
def _coh_comparer(code_formation):
    formation = _coh_objectifs_formation(code_formation)
    modele = _coh_modele(code_formation)
    libelles = [modele[c] for c in sorted(modele)]
    a = [_coh_normaliser(x) for x in formation]
    b = [_coh_normaliser(x) for x in libelles]
    manquants = [formation[i] for i, x in enumerate(a) if x not in b]
    en_trop = [libelles[i] for i, x in enumerate(b) if x not in a]
    return {"formation": formation, "modele": libelles,
            "identiques": (a == b),
            "manquants": manquants, "en_trop": en_trop,
            "ecart": bool(manquants or en_trop or a != b),
            "vide": not formation}
@app.route("/templates/objectifs/<identifiant>")
def objectifs_modele(identifiant):
    import modeles
    import questionnaires as Q
    fiche = modeles.modele("evaluation", identifiant)
    if not fiche:
        fiche = Q.EVALUATIONS.get(identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Modele introuvable"})
    o = fiche.get("objectifs") or {}
    return jsonify({"ok": True, "id": identifiant, "titre": fiche.get("titre") or identifiant,
                    "objectifs": [{"cle": c, "libelle": o[c]} for c in sorted(o)]})
@app.route("/templates/questionnaire/evaluation/<identifiant>/realigner", methods=["POST"])
def realigner_objectifs(identifiant):
    import modeles
    import journal
    fiche = modeles.modele("evaluation", identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Ce modele n'est pas dans la bibliotheque, il ne peut pas etre modifie."})
    brut = request.get_json(silent=True) or {}
    cibles = [x.strip() for x in (brut.get("objectifs") or []) if (x or "").strip()]
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun objectif a reprendre."})
    anciens = fiche.get("objectifs") or {}
    cles = sorted(anciens)
    nouveaux = {}
    for i, libelle in enumerate(cibles):
        cle = cles[i] if i < len(cles) else chr(65 + i)
        nouveaux[cle] = libelle
    for c in cles:
        if c not in nouveaux:
            nouveaux[c] = anciens[c]
    fiche["objectifs"] = nouveaux
    questions = fiche.get("questions") or []
    for q in questions:
        if q.get("objectif") not in nouveaux:
            q["objectif"] = sorted(nouveaux)[0]
    modeles.sauver("evaluation", identifiant, fiche)
    try:
        journal.ecrire("Objectifs du questionnaire réalignés", "", fiche.get("titre") or identifiant)
    except Exception:
        pass
    return jsonify({"ok": True, "objectifs": [{"cle": c, "libelle": nouveaux[c]} for c in sorted(nouveaux)]})
@app.route("/formations/<code>/objectifs")
def objectifs_formation(code):
    return jsonify({"ok": True, "code": code, "objectifs": _coh_objectifs_formation(code)})
@app.route("/templates/questionnaire/evaluation/<identifiant>/dupliquer/<formation>", methods=["POST"])
def dupliquer_pour(identifiant, formation):
    import modeles
    import journal
    from sessions import FORMATIONS, enregistrer_formation
    source = modeles.modele("evaluation", identifiant)
    if not source:
        return jsonify({"ok": False, "message": "Modele introuvable"})
    if formation not in FORMATIONS:
        return jsonify({"ok": False, "message": "Formation inconnue"})
    objectifs = _coh_objectifs_formation(formation)
    fiche = {"titre": (source.get("titre") or identifiant) + " \u2014 " + formation,
             "seuil": source.get("seuil", 70),
             "objectifs": {}, "questions": []}
    if objectifs:
        for i, libelle in enumerate(objectifs[:8]):
            fiche["objectifs"][chr(65 + i)] = libelle
    else:
        fiche["objectifs"] = dict(source.get("objectifs") or {})
    cles = sorted(fiche["objectifs"])
    for q in (source.get("questions") or []):
        c = dict(q)
        if c.get("objectif") not in fiche["objectifs"]:
            c["objectif"] = cles[0] if cles else "A"
        fiche["questions"].append(c)
    nouveau = modeles.sauver("evaluation", "", fiche)
    f = dict(FORMATIONS[formation])
    f["modele_evaluation"] = nouveau
    enregistrer_formation(formation, f)
    try:
        journal.ecrire("Questionnaire dupliqué pour une formation", "", formation)
    except Exception:
        pass
    return jsonify({"ok": True, "id": nouveau, "titre": fiche["titre"]})
def _cv_iso(valeur):
    v = (valeur or "")[:10]
    p = v.split("/")
    if len(p) == 3 and len(p[2]) == 4:
        return p[2] + "-" + p[1] + "-" + p[0]
    return ""
def _cv_jours(valeur):
    from datetime import datetime as dt, date as dd
    try:
        return (dd.today() - dt.strptime((valeur or "")[:10], "%d/%m/%Y").date()).days
    except Exception:
        return None
def _cv_avant(date_iso):
    from datetime import datetime as dt, date as dd
    try:
        return (dt.strptime(date_iso, "%Y-%m-%d").date() - dd.today()).days
    except Exception:
        return None
def _cv_lignes():
    import sessions as _sessions
    from connexion import service_sheets
    import suivi as _suivi
    fiches = {code: fiche_session(code) for code in SESSIONS}
    brut = _grilles_suivi(list(fiches))
    PALETTE = ["#4f7ef8", "#7c5bf7", "#0f9e6a", "#d4890a", "#d03b3b"]
    sortie = []
    formations = {}
    for i, code in enumerate(_sessions.visibles()):
        S = fiches[code]
        couleur = PALETTE[i % len(PALETTE)]
        nomf = S.get("nom_formation") or ""
        fcode = SESSIONS[code].get("formation") or ""
        avant = _cv_avant(S.get("date_debut") or "")
        for r in brut.get(code, [])[1:]:
            if not r or len(r) <= _suivi.COL["mail"]:
                continue
            d = {}
            for cle, idx in _suivi.COL.items():
                d[cle] = (r[idx] if len(r) > idx else "") or ""
            if not d.get("mail") or d.get("annule_le"):
                continue
            if "recontact" in (d.get("demande") or "").lower():
                continue
            if d.get("file_attente_le") and not d.get("promu_le"):
                continue
            signe = bool(d.get("signe_le"))
            envoye = bool(d.get("mail1_envoye_le"))
            lien = d.get("lien_pdf") or ""
            if signe:
                statut = "signee"
            elif envoye:
                statut = "attente"
            else:
                statut = "non_envoyee"
            relances = [x.strip() for x in (d.get("relance_signature_le") or "").split("|") if x.strip()]
            anomalie = ""
            if signe and not lien:
                anomalie = "Signée mais aucun document dans le Drive : la génération a échoué."
            elif signe and "/d/" not in lien:
                anomalie = "Le lien enregistré ne pointe pas vers un fichier Drive."
            jours = _cv_jours(d.get("mail1_envoye_le")) if statut == "attente" else None
            urgence = ""
            if statut != "signee" and avant is not None and avant >= 0:
                if avant <= 7:
                    urgence = "haute"
                elif avant <= 20:
                    urgence = "moyenne"
            formations[nomf] = formations.get(nomf, 0) + 1
            sortie.append({
                "nom": (d.get("nom") or "").upper() + " " + (d.get("prenom") or ""),
                "mail": (d.get("mail") or "").strip(),
                "formation": nomf, "formation_code": fcode, "couleur": couleur,
                "session": code, "session_texte": S.get("date_texte") or "",
                "debut": S.get("date_debut") or "", "avant": avant,
                "statut": statut, "signe_le": (d.get("signe_le") or "")[:10],
                "envoye_le": (d.get("mail1_envoye_le") or "")[:10],
                "genere_le": (d.get("convention_pdf_le") or "")[:10],
                "genere_iso": _cv_iso(d.get("convention_pdf_le")),
                "lien": lien, "jours": jours, "urgence": urgence,
                "relances": len(relances), "derniere_relance": relances[-1][:10] if relances else "",
                "anomalie": anomalie,
            })
    sortie.sort(key=lambda x: (x["debut"], x["nom"]), reverse=True)
    return sortie, sorted(formations.items())
@app.route("/conventions")
def page_conventions():
    lignes, formations = _cv_lignes()
    signees = [l for l in lignes if l["statut"] == "signee"]
    attente = [l for l in lignes if l["statut"] == "attente"]
    non_envoyees = [l for l in lignes if l["statut"] == "non_envoyee"]
    urgentes = [l for l in lignes if l["urgence"] in ("haute", "moyenne")]
    anomalies = [l for l in lignes if l["anomalie"]]
    annees = sorted({(l["debut"] or "0000")[:4] for l in lignes if l["debut"]}, reverse=True)
    return render_template("conventions.html", lignes=lignes, formations=formations,
                           annees=annees,
                           nb_total=len(lignes), nb_signees=len(signees),
                           nb_attente=len(attente), nb_non_envoyees=len(non_envoyees),
                           nb_urgentes=len(urgentes), nb_anomalies=len(anomalies),
                           taux=int(round(100.0 * len(signees) / len(lignes))) if lignes else None, periode_defaut=_par_periode())
@app.route("/conventions/export.csv")
def export_conventions():
    from flask import Response
    lignes, _ = _cv_lignes()
    ETIQ = {"signee": "Signee", "attente": "En attente de signature", "non_envoyee": "Pas encore envoyee"}
    out = ["Praticien;Mail;Formation;Identifiant formation;Session;Dates;Statut;Envoyee le;Signee le;Generee le;Relances;Lien"]
    for l in lignes:
        out.append(";".join([l["nom"], l["mail"], l["formation"], l["formation_code"],
                             l["session"], l["session_texte"], ETIQ.get(l["statut"], l["statut"]),
                             l["envoye_le"], l["signe_le"], l["genere_le"],
                             str(l["relances"]), l["lien"]]))
    return Response("\ufeff" + "\n".join(out), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=conventions.csv"})
def _ap_toutes_lignes():
    """Toutes les inscriptions, toutes sessions confondues, avec leur session."""
    from connexion import service_sheets
    import suivi as _suivi
    fiches = {code: fiche_session(code) for code in SESSIONS}
    brut = _grilles_suivi(list(fiches))
    lignes = []
    for code in SESSIONS:
        for r in brut.get(code, [])[1:]:
            if not r or len(r) <= _suivi.COL["mail"]:
                continue
            d = {cle: (r[i] if len(r) > i else "") or "" for cle, i in _suivi.COL.items()}
            if not (d.get("mail") or "").strip():
                continue
            # Une inscription annulee reste une trace : on l'exclut du
            # rapprochement, elle ne represente plus une personne a suivre.
            if d.get("annule_le"):
                continue
            d["_session"] = code
            lignes.append(d)
    return lignes
@app.route("/apprenants/doublons")
def page_doublons():
    """Porte desormais sur TOUTE la base de contacts, apprenants compris —
    puisqu'ils y figurent tous. L'ancienne version ne voyait que le classeur,
    et ignorait donc les prospects, c'est-a-dire l'immense majorite."""
    import doublons as _d
    import contacts as C
    try:
        fiches = C.lister(limite=20000)[0]
    except C.Indisponible as e:
        return render_template("doublons.html", erreur=str(e), r=None, nb_fiches=0,
                               nb_inscriptions=0, libelles={})
    r = _d.chercher_contacts(fiches)
    return render_template("doublons.html", r=r, erreur=None, nb_fiches=len(fiches),
                           nb_inscriptions=len(fiches),
                           libelles={m["cle"]: m["libelle"] for m in C.marqueurs()})
@app.route("/contacts/fusionner", methods=["POST"])
def fusionner_contacts():
    """Fusionne deux fiches en UNE. La fiche gardee est celle que vous
    designez ; l'autre lui cede ce qu'elle possede et QU'ELLE SEULE possede.

    Rien n'est ecrase : une valeur deja renseignee sur la fiche gardee reste
    telle quelle. Les marqueurs des deux se cumulent, la qualite d'apprenant
    comprise. Puis la fiche cedee est supprimee — c'est la seule perte, et
    elle est annoncee."""
    import contacts as C
    try:
        garde = int(request.form.get("garde") or 0)
        cede = int(request.form.get("cede") or 0)
    except ValueError:
        return jsonify({"ok": False, "message": "Fiches non identifiées."})
    if not garde or not cede or garde == cede:
        return jsonify({"ok": False, "message": "Il faut deux fiches différentes."})
    try:
        a, b = C.par_id(garde), C.par_id(cede)
        if not a or not b:
            return jsonify({"ok": False, "message": "Une des deux fiches n'existe plus."})
        a_poser = {}
        for champ in ("nom", "prenom", "mail", "telephone", "ville"):
            if not (a.get(champ) or "").strip() and (b.get(champ) or "").strip():
                a_poser[champ] = b[champ]
        ensemble = sorted(set(a.get("marqueurs") or []) | set(b.get("marqueurs") or []))
        if ensemble != sorted(a.get("marqueurs") or []):
            a_poser["marqueurs"] = ensemble
        if b.get("ne_plus_contacter") and not a.get("ne_plus_contacter"):
            a_poser["ne_plus_contacter"] = True
        if a_poser:
            C.modifier(garde, a_poser)
        C.supprimer([cede])
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    try:
        journal.ecrire("Contacts fusionnés", C.nom_affiche(a),
                       "fiche « " + C.nom_affiche(b) + " » absorbée")
    except Exception:
        pass
    return jsonify({"ok": True, "repris": sorted(a_poser)})
@app.route("/apprenants/doublons/ecarter", methods=["POST"])
def ecarter_doublon():
    """Ecarte durablement un rapprochement. Deux confreres homonymes ne doivent
    pas etre resignales a chaque passage."""
    import doublons as _d
    import journal
    a = (request.form.get("a") or "").strip().lower()
    b = (request.form.get("b") or "").strip().lower()
    motif = (request.form.get("motif") or "").strip()
    if not a or not b:
        return jsonify({"ok": False, "message": "Deux adresses sont necessaires."})
    _d.ecarter(a, b, motif)
    try:
        journal.ecrire("Rapprochement écarté", "", a + " / " + b + (" — " + motif if motif else ""))
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/apprenants/doublons/reprendre", methods=["POST"])
def reprendre_doublon():
    import doublons as _d
    a = (request.form.get("a") or "").strip().lower()
    b = (request.form.get("b") or "").strip().lower()
    return jsonify({"ok": _d.reprendre(a, b)})
BD_PAR_PAGE = 50
def _bd_cle_date(brut):
    """Une date francaise rendue comparable : « 03/08/2026 17:57 » -> tri sur
    l'annee, puis le mois, puis le jour. Rend "" si la forme est inconnue, ce
    qui place la ligne en dernier plutot que de la faire gagner par hasard."""
    import re as _re
    m = _re.match(r"\s*(\d{2})/(\d{2})/(\d{4})[ T]*([\d:]*)", str(brut or ""))
    if m:
        return "%s-%s-%s %s" % (m.group(3), m.group(2), m.group(1), m.group(4))
    m = _re.match(r"\s*(\d{4})-(\d{2})-(\d{2})[ T]*([\d:]*)", str(brut or ""))
    if m:
        return "%s-%s-%s %s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    return ""


def _bd_classeur():
    """Ce que le classeur sait des personnes : identite la plus recente, et
    parcours de formation. Rendu sous deux formes — une liste d'identites pour
    la synchronisation, un index par cle de rapprochement pour l'affichage.

    Les simples demandes de renseignement sont ecartees : ce ne sont pas des
    inscriptions, donc pas des apprenants. Elles restent visibles comme
    prospects si elles figurent par ailleurs dans la base de contacts."""
    import contacts as C
    par_cle, noms = {}, {}
    for l in _ap_toutes_lignes():
        if "recontact" in (l.get("demande") or "").lower():
            continue
        cle = C.norm_mail(l.get("mail")) or C.norm_tel(l.get("telephone"))
        if not cle:
            continue
        p = par_cle.setdefault(cle, {"_h": "", "identite": {}, "parcours": []})
        # LE PLUS RECENT, CHRONOLOGIQUEMENT. La comparaison portait sur le TEXTE
        # de la date francaise : « 31/07/2026 » passait pour posterieur a
        # « 03/08/2026 » puisque 3 > 0. L'identite d'un contact pouvait donc
        # venir d'une inscription perimee — ancien telephone, ancienne ville.
        _h = _bd_cle_date(l.get("horodateur"))
        if _h >= p["_h"]:
            p["_h"] = _h
            p["identite"] = {"nom": l.get("nom") or "", "prenom": l.get("prenom") or "",
                             "mail": l.get("mail") or "", "telephone": l.get("telephone") or "",
                             "ville": l.get("ville") or "",
                             # La FONCTION descend elle aussi du classeur vers la
                             # fiche : sans elle, la chaine s'arretait a mi-course
                             # — le formulaire la demandait, le suivi la stockait,
                             # et la fiche contact l'ignorait.
                             "fonction": l.get("fonction") or ""}
        code = l.get("_session") or ""
        if code and code not in noms:
            try:
                noms[code] = fiche_session(code).get("nom_formation") or code
            except Exception:
                noms[code] = code
        p["parcours"].append({
            "code": code, "formation": noms.get(code, code),
            "statut": _suivi_statut(l),
            "annulee": bool(l.get("annule_le")),
        })
    return par_cle
def _bd_date(brut):
    """« 2026-08-02T23:13:33 » -> « 02/08/2026 ». La date d'entree dit d'ou
    vient une fiche autant qu'un marqueur : importee ce jour-la, ou connue
    depuis longtemps."""
    t = str(brut or "")[:10]
    if len(t) == 10 and t[4] == "-":
        return t[8:10] + "/" + t[5:7] + "/" + t[:4]
    return ""
def _bd_enrichir(fiches, index):
    """Colle a chaque fiche ce que le classeur en dit. Le parcours n'est JAMAIS
    recopie dans Supabase : il est lu a l'affichage, pour la page en cours
    seulement, donc toujours a jour."""
    import contacts as C
    sortie = []
    for f in fiches:
        cle = (f.get("mail_norm") or "") or (f.get("tel_norm") or "")
        info = index.get(f.get("mail_norm") or "") or index.get(f.get("tel_norm") or "") or {}
        parcours = info.get("parcours") or []
        visibles = [m for m in (f.get("marqueurs") or []) if not C.est_reserve(m)]
        sortie.append({
            "id": f["id"], "nom_affiche": C.nom_affiche(f),
            "sans_nom": not ((f.get("nom") or "").strip() or (f.get("prenom") or "").strip()),
            "mail": f.get("mail") or "", "telephone": f.get("telephone") or "",
            "ville": f.get("ville") or "", "joignable": C.contactable(f),
            "npc": bool(f.get("ne_plus_contacter")),
            "apprenant": C.RESERVE_APPRENANT in (f.get("marqueurs") or []),
            # La pastille doit dire la meme chose que le filtre, sinon on
            # cherche pourquoi quelqu'un affiche « Prospect » sans apparaitre
            # dans les prospects. Fonction vide = chirurgien-dentiste, comme
            # partout ailleurs.
            "hors_prospect": bool((f.get("fonction") or "").strip())
                             and (f.get("fonction") or "") not in C.PROSPECTABLES,
            "marqueurs": visibles, "parcours": parcours,
            "nb_inscriptions": len(parcours),
            "source": f.get("source") or "",
            "entree": _bd_date(f.get("cree_le")),
        })
    # Les injoignables en fin de page, quel que soit le tri demande. On ne
    # peut pas le faire cote Supabase — « avoir un mail OU un telephone » n'est
    # pas une colonne — donc le classement porte sur LA PAGE AFFICHEE, pas sur
    # la base entiere. C'est dit a l'ecran plutot que laisse croire.
    sortie.sort(key=lambda f: 0 if f["joignable"] else 1)
    return sortie
BD_TRIS = [("recent", "Entrée récente", "cree_le.desc"),
           ("ancien", "Entrée ancienne", "cree_le.asc"),
           ("az", "Nom A → Z", "nom.asc"),
           ("za", "Nom Z → A", "nom.desc")]
def _bd_tri(cle):
    """Le plus recent d'abord par defaut : dans une base qui grossit par
    imports, ce qui vient d'entrer est ce qu'on cherche."""
    for c, _, ordre in BD_TRIS:
        if c == cle:
            return ordre
    return BD_TRIS[0][2]
def _bd_lien(q, qualite, sel, npc, tri="", fonction=""):
    """Fabrique les adresses des filtres en conservant les autres criteres.
    Changer un filtre ramene TOUJOURS a la premiere page : rester en page 7
    d'une liste qui vient d'en perdre six donne un ecran vide sans raison
    apparente."""
    import urllib.parse as _up
    def lien(**chg):
        v_tri = chg.get("tri", tri)
        v_qualite = chg.get("qualite", qualite)
        v_fonction = chg.get("fonction", fonction)
        v_sel = list(sel)
        if "bascule" in chg:
            b = chg["bascule"]
            v_sel = [x for x in v_sel if x != b] if b in v_sel else v_sel + [b]
        v_npc = chg.get("npc", npc)
        v_page = chg.get("page", 1)
        p = []
        if q:
            p.append(("q", q))
        if v_qualite:
            p.append(("qualite", v_qualite))
        if v_fonction:
            p.append(("f", v_fonction))
        if v_sel:
            p.append(("m", ",".join(v_sel)))
        if v_npc:
            p.append(("npc", "1"))
        if v_tri and v_tri != BD_TRIS[0][0]:
            p.append(("tri", v_tri))
        if v_page and int(v_page) > 1:
            p.append(("page", str(v_page)))
        return "/contacts" + ("?" + _up.urlencode(p) if p else "")
    return lien
@app.route("/messagerie/piece", methods=["POST"])
def messagerie_piece():
    """Depose un fichier destine a accompagner une communication.

    DEUX USAGES POSSIBLES pour le meme fichier, et c'est l'expediteur qui
    tranche : ATTACHE au message, ou proposé en LIEN de telechargement.

    Le seuil recommande est bas — 1 Mo — parce qu'une piece attachee part avec
    CHAQUE exemplaire : sur 178 destinataires, un PDF d'un mega represente 178
    megas expedies, un envoi qui traine, et un mail lourd adresse a beaucoup de
    monde, ce que les filtres n'aiment pas.
    """
    from connexion import service_drive
    from googleapiclient.http import MediaInMemoryUpload
    import communications as _com
    fichier = request.files.get("piece")
    if not fichier or not fichier.filename:
        return jsonify({"ok": False, "message": "Aucun fichier reçu."})
    contenu = fichier.read()
    if len(contenu) > _com.PLAFOND_PIECE:
        return jsonify({"ok": False, "message":
                        "Fichier trop lourd (%s). Gmail refuse souvent au-delà de 10 Mo — "
                        "déposez-le sur le Drive et proposez-le en lien."
                        % _com.poids_lisible(len(contenu))})
    try:
        drive = service_drive()
        import dossiers, profil as _pr
        parent = dossiers.trouver(drive, _pr.charger() or {}, "dossier_templates", "Templates")
        sous = dossiers.sous_dossier(drive, parent, "Pièces des communications") if parent else ""
        f = drive.files().create(
            body={"name": fichier.filename, "parents": [sous] if sous else []},
            media_body=MediaInMemoryUpload(contenu, mimetype=fichier.mimetype or "application/octet-stream"),
            fields="id").execute()
        drive.permissions().create(fileId=f["id"], body={"type": "anyone", "role": "reader"}).execute()
        lourd = len(contenu) > _com.SEUIL_PIECE
        return jsonify({"ok": True, "piece": {
            "drive": f["id"], "nom": fichier.filename, "taille": len(contenu),
            "type": fichier.mimetype or "application/octet-stream",
            # Au-dela du seuil, on PROPOSE le lien par defaut. L'expediteur peut
            # revenir dessus : c'est une recommandation, pas une interdiction.
            "mode": "lien" if lourd else "jointe",
            "lien": "https://drive.google.com/file/d/" + f["id"] + "/view"},
            "poids": _com.poids_lisible(len(contenu)), "lourd": lourd})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:200]})


@app.route("/messagerie/apercu", methods=["POST"])
def messagerie_apercu():
    """Le message rendu, pied compris, par le MEME moteur que l'envoi.

    Refaire le rendu en JavaScript aurait donne deux implementations a tenir
    d'accord : l'apercu aurait fini par mentir, et c'est precisement ce qu'on
    ne peut pas se permettre sur un envoi irreversible.
    """
    from flask import Response
    import json as _j, mails, campagnes as K, profil, sessions as _s
    try:
        blocs = _j.loads(request.form.get("blocs") or "[]")
    except Exception:
        blocs = []
    O = profil.charger() or {}
    O.setdefault("url_signature", _s.COMMUN.get("url_signature") or "")
    # L'ADRESSE SE COMPOSE DEPUIS LE PROFIL VISE, elle ne se replie plus sur
    # les donnees communes : celles-ci suivent l'organisme ACTIF, si bien
    # qu'un mail Smileclub portait l'adresse de DSF (61 rue Balard) au lieu
    # de la sienne (4 rue Joseph Granier). Constate le 23/08/2026.
    O.setdefault("adresse_organisme",
                 profil.adresse_complete(O, repli=False) or "")
    corps = mails.html_depuis_blocs(blocs) or "<p style='color:#8a90a2'>(message vide)</p>"
    return Response(K.rendre(corps, {"id": 0}, O), mimetype="text/html")


@app.route("/messagerie/image", methods=["POST"])
def messagerie_image():
    """Depose une image et rend son adresse publique, prete a poser dans un mail.

    POURQUOI PASSER PAR LE DRIVE. Une image ne peut pas vivre dans le message :
    l'attacher en piece jointe la fait apparaitre comme telle chez la plupart
    des clients, et l'inclure en base64 fait exploser le poids et declenche les
    filtres. Un lien vers un fichier public est la seule voie qui s'affiche
    partout.

    LE FICHIER EST RENDU LISIBLE PAR TOUS — c'est indispensable pour qu'il
    s'affiche chez le destinataire, et cela vaut d'etre dit : ne deposez ici
    que ce que vous accepteriez de rendre public.
    """
    from connexion import service_drive
    from googleapiclient.http import MediaInMemoryUpload
    fichier = request.files.get("image")
    if not fichier or not fichier.filename:
        return jsonify({"ok": False, "message": "Aucune image reçue."})
    contenu = fichier.read()
    if len(contenu) > 5 * 1024 * 1024:
        return jsonify({"ok": False, "message":
                        "Image trop lourde (5 Mo maximum). Une image de mail dépasse "
                        "rarement 300 Ko — au-delà, elle ralentit l'ouverture."})
    if not (fichier.mimetype or "").startswith("image/"):
        return jsonify({"ok": False, "message": "Ce fichier n'est pas une image."})
    try:
        drive = service_drive()
        import dossiers, profil as _pr
        parent = dossiers.trouver(drive, _pr.charger() or {}, "dossier_templates", "Templates")
        sous = dossiers.sous_dossier(drive, parent, "Images des communications") if parent else ""
        f = drive.files().create(
            body={"name": fichier.filename, "parents": [sous] if sous else []},
            media_body=MediaInMemoryUpload(contenu, mimetype=fichier.mimetype),
            fields="id").execute()
        drive.permissions().create(fileId=f["id"], body={"type": "anyone", "role": "reader"}).execute()
        # « lh3 » sert l'image elle-meme ; l'adresse « /file/d/…/view » renverrait
        # la page Drive, et le mail afficherait un cadre vide.
        return jsonify({"ok": True, "src": "https://lh3.googleusercontent.com/d/" + f["id"],
                        "nom": fichier.filename})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:200]})


@app.route("/templates/communication/nouveau")
@app.route("/templates/communication/<identifiant>")
def editeur_communication(identifiant=""):
    import communications as _com
    return render_template("communication.html",
                           m=_com.un(identifiant) if identifiant else None,
                           blocs_neufs=_com.MODELE_NEUF)


@app.route("/templates/communication/enregistrer", methods=["POST"])
def enregistrer_communication():
    import communications as _com
    import json as _j
    titre = (request.form.get("titre") or "").strip()
    objet = (request.form.get("objet") or "").strip()
    try:
        blocs = _j.loads(request.form.get("blocs") or "[]")
    except Exception:
        blocs = []
    if not (titre and objet):
        return jsonify({"ok": False, "message": "Un titre et un objet sont nécessaires."})
    if not blocs:
        return jsonify({"ok": False, "message": "Le message est vide : ajoutez au moins un bloc."})
    try:
        pieces = _j.loads(request.form.get("pieces") or "[]")
    except Exception:
        pieces = []
    ident = _com.enregistrer(request.form.get("id") or "", titre, objet, blocs, pieces=pieces)
    try:
        import journal
        journal.ecrire("Modèle de communication enregistré", "", titre, "", "")
    except Exception:
        pass
    return jsonify({"ok": True, "id": ident})


@app.route("/templates/communication/supprimer", methods=["POST"])
def supprimer_communication():
    import communications as _com
    _com.supprimer((request.form.get("id") or "").strip())
    return jsonify({"ok": True})


@app.route("/templates/communication/<identifiant>/apercu")
def apercu_communication(identifiant):
    """Le modele rendu tel qu'il partirait, PIED COMPRIS. Un apercu sans le
    pied laisserait croire qu'on peut envoyer sans lien de desinscription."""
    from flask import Response
    import communications as _com, campagnes as K, profil, sessions as _s
    m = _com.un(identifiant) or {}
    O = profil.charger() or {}
    O.setdefault("url_signature", _s.COMMUN.get("url_signature") or "")
    # L'ADRESSE SE COMPOSE DEPUIS LE PROFIL VISE, elle ne se replie plus sur
    # les donnees communes : celles-ci suivent l'organisme ACTIF, si bien
    # qu'un mail Smileclub portait l'adresse de DSF (61 rue Balard) au lieu
    # de la sienne (4 rue Joseph Granier). Constate le 23/08/2026.
    O.setdefault("adresse_organisme",
                 profil.adresse_complete(O, repli=False) or "")
    return Response(K.rendre(m.get("corps") or "<p>(modèle vide)</p>", {"id": 0}, O),
                    mimetype="text/html")


@app.route("/messagerie/modeles")
def messagerie_modeles():
    """La liste des modeles, pour le choix dans l'ecran Messagerie."""
    import communications as _com
    return jsonify({"ok": True, "modeles": [
        {"id": m["id"], "titre": m.get("titre") or m["id"],
         "objet": m.get("objet") or "", "corps": m.get("corps") or "",
         "blocs": m.get("blocs") or [], "pieces": m.get("pieces") or []}
        for m in _com.lister()]})


def _pieces_demandees():
    """Les pieces envoyees par l'ecran, telles quelles. Recopiees dans la
    campagne : ce qui est parti ne doit pas changer si le modele evolue."""
    import json as _j
    try:
        p = _j.loads(request.form.get("pieces") or "[]")
        return p if isinstance(p, list) else []
    except Exception:
        return []


def _ms_filtres():
    """Les criteres de ciblage lus depuis la requete. Les marqueurs se cumulent
    et se combinent en ET avec le reste — meme regle que l'ecran Contacts."""
    import contacts as C
    fonction = (request.form.get("fonction") or "").strip()
    return {"qualite": (request.form.get("qualite") or "").strip(),
            "fonction": fonction if fonction in C.FONCTIONS else "",
            "marqueurs": [m for m in (request.form.get("m") or "").split(",") if m.strip()]}


@app.route("/sessions/supprimees")
def page_sessions_supprimees():
    """Les pieces des sessions retirees de DFM.

    QUALIOPI. Supprimer une session ne detruit rien — l'onglet est renomme, les
    documents restent sur le Drive — mais plus aucun ecran ne savait qu'ils
    existaient. Un controle portant sur une formation supprimee mettait
    l'organisme en defaut alors que tout etait conserve.

    Cet ecran parcourt les DEUX organismes, quel que soit le profil actif : une
    session supprimee n'appartient plus a rien.
    """
    import supprimees as _sup
    liste = _sup.lister()
    for s in liste:
        try:
            s["pieces"] = _sup.dossiers_drive(s)
        except Exception:
            s["pieces"] = []
    return render_template("supprimees.html", liste=liste)


@app.route("/messagerie")
def page_messagerie():
    import contacts as C, campagnes as K
    try:
        marqueurs = [m for m in C.marqueurs() if not C.est_reserve(m["cle"])]
    except Exception:
        marqueurs = []
    return render_template("messagerie.html", marqueurs=marqueurs,
                           fonctions=C.FONCTIONS, campagnes=K.lister())


@app.route("/messagerie/compter", methods=["POST"])
def messagerie_compter():
    """Le decompte affiche AVANT tout envoi. Il montre d'ou vient l'ecart :
    un nombre inexplicable n'inspire pas confiance quand l'action ne se
    rattrape pas."""
    import campagnes as K
    f = _ms_filtres()
    try:
        return jsonify({"ok": True, "bilan": K.compter(f["qualite"], f["marqueurs"], f["fonction"])})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:200]})


@app.route("/messagerie/essai", methods=["POST"])
def messagerie_essai():
    """Un envoi a SOI, obligatoire avant la campagne. On ne relit jamais aussi
    bien qu'en recevant — et le pied, le lien de desinscription et le rendu
    reel ne se verifient pas autrement."""
    import campagnes as K, profil, subprocess, sys, tempfile, json as _j
    objet = (request.form.get("objet") or "").strip()
    corps = (request.form.get("corps") or "").strip()
    if not objet or not corps:
        return jsonify({"ok": False, "message": "Un objet et un corps sont nécessaires."})
    adresse = (profil.charger() or {}).get("mail_contact") or ""
    if "@" not in adresse:
        return jsonify({"ok": False, "message": "Aucune adresse de contact sur la fiche de l'organisme."})
    f = _ms_filtres()
    cibles, bilan = K.destinataires(f["qualite"], f["marqueurs"], f["fonction"])
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun destinataire : l'essai ne prouverait rien."})
    # Une campagne PROVISOIRE, le temps de l'essai : elle porte le vrai premier
    # destinataire, pour que le lien de desinscription du message d'essai soit
    # verifiable. Elle est retiree juste apres.
    c = K.creer(objet, corps, cibles[:1], bilan, organisme=profil.actif(), filtres=f,
                pieces=_pieces_demandees())
    r = subprocess.run([sys.executable, "envoyer_campagne.py", c["id"], "--essai=" + adresse],
                       capture_output=True, text=True, timeout=120)
    d = K.tout()
    d.pop(c["id"], None)
    K._ecrire(d)
    if r.returncode != 0:
        return jsonify({"ok": False, "message": (r.stdout or r.stderr or "").strip()[-200:]})
    return jsonify({"ok": True, "adresse": adresse})


@app.route("/messagerie/envoyer", methods=["POST"])
def messagerie_envoyer():
    """Cree la campagne puis lance l'envoi EN TACHE DE FOND.

    Plusieurs centaines de mails prennent plusieurs minutes : une requete web
    ne doit pas rester suspendue pendant ce temps, et l'utilisateur doit
    pouvoir quitter l'ecran.
    """
    import campagnes as K, profil, subprocess, sys
    objet = (request.form.get("objet") or "").strip()
    corps = (request.form.get("corps") or "").strip()
    if not objet or not corps:
        return jsonify({"ok": False, "message": "Un objet et un corps sont nécessaires."})
    f = _ms_filtres()
    cibles, bilan = K.destinataires(f["qualite"], f["marqueurs"], f["fonction"])
    if not cibles:
        return jsonify({"ok": False, "message": "Aucun destinataire."})
    c = K.creer(objet, corps, cibles, bilan, organisme=profil.actif(), filtres=f,
                pieces=_pieces_demandees())
    subprocess.Popen([sys.executable, "envoyer_campagne.py", c["id"]],
                     cwd=os.path.dirname(os.path.abspath(__file__)),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"ok": True, "id": c["id"], "destinataires": len(cibles)})


@app.route("/messagerie/campagne/<ident>")
def messagerie_campagne(ident):
    """Le message TEL QU'IL EST PARTI. On rend l'archive, jamais le modele :
    modifier un modele six mois plus tard ne doit pas reecrire l'histoire."""
    from flask import Response
    import campagnes as K, profil, sessions as _s
    c = K.tout().get(ident)
    if not c:
        return render_template("erreur.html", titre="Campagne introuvable",
                               message="Cette campagne n'existe plus."), 404
    O = (profil.charger(c.get("organisme")) if c.get("organisme") else profil.charger()) or {}
    O.setdefault("url_signature", _s.COMMUN.get("url_signature") or "")
    # L'ADRESSE SE COMPOSE DEPUIS LE PROFIL VISE, elle ne se replie plus sur
    # les donnees communes : celles-ci suivent l'organisme ACTIF, si bien
    # qu'un mail Smileclub portait l'adresse de DSF (61 rue Balard) au lieu
    # de la sienne (4 rue Joseph Granier). Constate le 23/08/2026.
    O.setdefault("adresse_organisme",
                 profil.adresse_complete(O, repli=False) or "")
    vises = c.get("vises") or []
    apercu = {"id": vises[0] if vises else 0}
    return Response(K.rendre(c.get("corps") or "", apercu, O), mimetype="text/html")


@app.route("/contacts")
def page_contacts():
    import contacts as C
    pret, souci = C.disponible()
    if not pret:
        return render_template("contacts.html", pret=False, souci=souci,
                               fiches=[], marqueurs=[], compte={}, page=1, pages=1,
                               q="", qualite="", sel=[], npc=False, total=0, libelles={}, couleurs={}, familles={}, tb={},
                               tri="recent", tris=BD_TRIS,
                               bd_lien=_bd_lien("", "", [], False))
    q = (request.args.get("q") or "").strip()
    qualite = (request.args.get("qualite") or "").strip()
    sel = [m for m in (request.args.get("m") or "").split(",") if m.strip()]
    npc = (request.args.get("npc") or "") == "1"
    tri = (request.args.get("tri") or BD_TRIS[0][0]).strip()
    page = max(1, int(request.args.get("page") or 1))
    # CIBLAGE PAR FONCTION : une communication peut ne concerner que les
    # assistantes, ou que les praticiens. Valeur libre refusee — seules les
    # fonctions du catalogue sont acceptees, sinon le filtre ne rendrait rien.
    fonction = (request.args.get("f") or "").strip()
    if fonction not in C.FONCTIONS:
        fonction = ""
    try:
        brut, total = C.lister(recherche=q, filtre_marqueurs=sel, qualite=qualite,
                               fonction=fonction,
                               exclure_npc=npc, depuis=(page - 1) * BD_PAR_PAGE,
                               limite=BD_PAR_PAGE, tri=_bd_tri(tri))
    except C.Indisponible as e:
        return render_template("contacts.html", pret=False, souci=str(e), fiches=[],
                               marqueurs=[], compte={}, page=1, pages=1, q=q,
                               qualite=qualite, sel=sel, npc=npc, total=0, libelles={}, couleurs={}, familles={}, tb={},
                               tri=tri, tris=BD_TRIS,
                               fonction=fonction, fonctions=C.FONCTIONS,
                               bd_lien=_bd_lien(q, qualite, sel, npc, fonction=fonction))
    index = {}
    try:
        index = _bd_classeur()
    except Exception:
        pass          # le classeur peut etre injoignable : la base reste lisible
    # LE BANDEAU CHIFFRE TIENT EN UNE REQUETE — 08/10/2026. Il en demandait
    # six : chacune ne rapatriait rien, mais chacune attendait son aller-retour.
    # Voir contacts.tableau_de_bord, qui porte les regles de comptage.
    compte, tb = C.tableau_de_bord()
    return render_template(
        "contacts.html", pret=True, souci="",
        fiches=_bd_enrichir(brut, index), total=total, page=page,
        pages=max(1, (total + BD_PAR_PAGE - 1) // BD_PAR_PAGE),
        marqueurs=[m for m in C.marqueurs() if not C.est_reserve(m["cle"])],
        compte=compte, q=q, qualite=qualite, sel=sel, npc=npc, tb=tb,
        tri=tri, tris=BD_TRIS,
        familles=C.marqueurs_par_famille(),
        libelles={m["cle"]: m["libelle"] for m in C.marqueurs()},
        couleurs={m["cle"]: m["couleur"] for m in C.marqueurs()},
        fonction=fonction, fonctions=C.FONCTIONS,
        bd_lien=_bd_lien(q, qualite, sel, npc, tri, fonction))
_MIROIR = os.path.join(DOSSIER, "miroir_contacts.json")
@app.route("/contacts/miroir", methods=["POST"])
def miroir_contacts():
    """Recopie toute la base dans un classeur Google, POUR LECTURE SEULEMENT.

    DFM n'y lit JAMAIS rien : c'est une photographie, pas une source. Une
    modification faite a la main dans ce classeur n'aura donc aucun effet et
    sera effacee au prochain passage — l'entete le dit en toutes lettres, en
    premiere ligne, pour que personne ne s'y trompe.

    Le classeur est distinct du suivi des inscriptions : un prospect n'a ni
    session, ni convention, ni reglement, il n'a rien a y faire."""
    import contacts as C
    import json as _json
    from datetime import datetime as _dt
    from connexion import service_sheets, service_drive
    try:
        fiches, _ = C.lister(limite=20000, tri="cree_le.desc")
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    libelles = {m["cle"]: m["libelle"] for m in C.marqueurs()}
    ident = ""
    try:
        ident = (_json.load(open(_MIROIR, encoding="utf-8")) or {}).get("id") or ""
    except Exception:
        ident = ""
    sheets, drive = service_sheets(), service_drive()
    if ident:
        try:
            drive.files().get(fileId=ident, fields="id").execute()
        except Exception:
            ident = ""          # supprime ou vide la corbeille : on en refait un
    neuf = not ident
    if neuf:
        ident = sheets.spreadsheets().create(body={
            "properties": {"title": "Contacts DFM — miroir"},
            "sheets": [{"properties": {"title": "Contacts"}}]}).execute()["spreadsheetId"]
        import fichiers
        fichiers.ecrire(_MIROIR, {"id": ident})
    entete = ["Nom", "Prénom", "Adresse mail", "Téléphone", "Ville", "Statut",
              "Marqueurs", "Ne plus contacter", "Date d'entrée", "Origine"]
    valeurs = [["COPIE EN LECTURE SEULE — produite par DFM le "
                + _dt.now().strftime("%d/%m/%Y à %H:%M")
                + ". Toute modification faite ici sera perdue au prochain passage."]
               + [""] * (len(entete) - 1), entete]
    for f in fiches:
        marques = [libelles.get(m, m) for m in (f.get("marqueurs") or []) if not C.est_reserve(m)]
        valeurs.append([
            f.get("nom") or "", f.get("prenom") or "", f.get("mail") or "",
            f.get("telephone") or "", f.get("ville") or "",
            "Apprenant" if C.RESERVE_APPRENANT in (f.get("marqueurs") or []) else "Prospect",
            " · ".join(marques), "oui" if f.get("ne_plus_contacter") else "",
            _bd_date(f.get("cree_le")), f.get("source") or ""])
    try:
        sheets.spreadsheets().values().clear(
            spreadsheetId=ident, range="'Contacts'!A1:Z100000", body={}).execute()
        sheets.spreadsheets().values().update(
            spreadsheetId=ident, range="'Contacts'!A1",
            valueInputOption="RAW", body={"values": valeurs}).execute()
    except Exception as e:
        return jsonify({"ok": False, "message": "Écriture impossible : " + str(e)[:150]})
    try:
        journal.ecrire("Miroir des contacts mis à jour", "", str(len(fiches)) + " fiche(s)")
    except Exception:
        pass
    return jsonify({"ok": True, "lignes": len(fiches), "neuf": neuf,
                    "lien": "https://docs.google.com/spreadsheets/d/" + ident})
@app.route("/session/<code>/reglement-client", methods=["POST"])
def enregistrer_reglement_client(code):
    """Le reglement d'une session CLIENT, saisi a la main.

    Rien ne peut le deviner : le virement arrive sur un compte bancaire, DFM ne
    le voit pas. Le parcours individuel a ses colonnes de suivi ; ici la trace
    vit sur la fiche de session, comme le reste de la chaine client.

    La REFERENCE est facultative — un virement en porte une, un cheque non — et
    l'absence de reference ne doit pas empecher de constater un paiement.
    """
    import sessions as _S
    if code not in _S.SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    if not _S.est_client(code):
        return jsonify({"ok": False, "message": "Cette session n'est pas une session client."})
    brutes = _S._charger_json(_S._FICHIER_S)
    fiche = dict(brutes.get(code) or {})
    if not fiche:
        return jsonify({"ok": False, "message": "Fiche de session introuvable"})
    if (request.form.get("annuler") or "") == "1":
        # RETRAIT D'UN REGLEMENT SAISI PAR ERREUR. Meme regle que du cote
        # individuel : un reglement efface sans trace serait pire que pas
        # d'effacement. La piste d'audit doit montrer qu'il a existe, qu'il a
        # ete retire, et pourquoi. Un controleur qui voit un montant disparaitre
        # sans explication a raison de s'inquieter.
        motif = (request.form.get("motif") or "").strip()
        if not motif:
            return jsonify({"ok": False, "message": "Un motif est nécessaire pour retirer un règlement."})
        if not (fiche.get("reglement_client_le") or "").strip():
            return jsonify({"ok": False, "message": "Aucun règlement enregistré sur cette session."})
        ancien = {"date": fiche.get("reglement_client_le") or "",
                  "reference": fiche.get("reglement_client_reference") or ""}
        fiche.pop("reglement_client_le", None)
        fiche.pop("reglement_client_reference", None)
        _S.enregistrer_session(code, fiche)
        try:
            import journal, clients as _CL
            journal.ecrire(
                "Règlement client retiré",
                (_CL.client(_S.client_de(code)) or {}).get("raison_sociale") or "",
                "règlement du " + ancien["date"]
                + (" — réf. " + ancien["reference"] if ancien["reference"] else "")
                + " · motif : " + motif, "", code)
        except Exception:
            pass
        return jsonify({"ok": True})
    date = (request.form.get("date") or "").strip()
    if not date:
        return jsonify({"ok": False, "message": "La date du règlement est nécessaire."})
    # Le champ HTML rend AAAA-MM-JJ ; on stocke au format francais, celui que
    # lisent les ecrans et les mails.
    try:
        from datetime import datetime as _dt
        date = _dt.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        pass
    fiche["reglement_client_le"] = date
    fiche["reglement_client_reference"] = (request.form.get("reference") or "").strip()
    _S.enregistrer_session(code, fiche)
    try:
        import journal, clients as _CL
        journal.ecrire("Règlement client enregistré",
                       (_CL.client(_S.client_de(code)) or {}).get("raison_sociale") or "",
                       date + (" — réf. " + fiche["reglement_client_reference"]
                               if fiche["reglement_client_reference"] else ""), "", code)
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/session/<code>/participants", methods=["POST"])
def ajouter_participants(code):
    """Saisie des participants d'une session CLIENT.

    Le centre fournit sa liste, on la saisit : ces praticiens ne remplissent
    aucun formulaire. Chaque participant devient une ligne ordinaire de
    l'onglet de suivi — meme structure, memes 49 colonnes — pour que tout ce
    qui reste individuel continue de fonctionner sans une ligne de code :
    attestations, questionnaires, emargement, base apprenants.

    Les colonnes du parcours individuel restent VIDES : convention, signature,
    reglement et facture sont collectifs en mode client."""
    import sessions as _sessions
    import suivi as _suivi
    from connexion import service_sheets
    from datetime import datetime as _dt
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    if not _sessions.est_client(code):
        return jsonify({"ok": False, "message":
                        "Cette session est à inscriptions individuelles : les praticiens "
                        "s'inscrivent par le formulaire, ils ne se saisissent pas ici."})
    S = fiche_session(code)
    # json n'est pas importe au niveau du module — seulement _json, plus bas.
    # Un « json.loads » y levait un NameError que la capture large travestissait
    # en « Liste illisible » : le message accusait la liste d'un defaut de code.
    import json as _js
    try:
        gens = _js.loads(request.form.get("participants") or "[]")
    except ValueError:
        return jsonify({"ok": False, "message": "Liste illisible."})
    if not isinstance(gens, list):
        return jsonify({"ok": False, "message": "Liste illisible."})
    try:
        connus = {(l.get("mail") or "").strip().lower() for l in _lignes_onglet(S)}
    except Exception as e:
        return jsonify({"ok": False, "message": "Lecture du Sheet : " + str(e)[:120]})

    retenus, ecartes = [], []
    vus = set()
    for n, g in enumerate(gens, 1):
        nom = (g.get("nom") or "").strip()
        prenom = (g.get("prenom") or "").strip()
        mail = (g.get("mail") or "").strip()
        if not (nom or prenom):
            ecartes.append({"ligne": n, "motif": "aucun nom"})
            continue
        # L'ADRESSE MAIL N'EST PAS OBLIGATOIRE. Un centre fournit parfois une
        # liste de noms sans adresses ; refuser l'inscription pour autant
        # bloquerait la session entiere. Le participant entre dans le suivi,
        # emarge et recevra son attestation en main propre. Il n'aura
        # simplement pas de fiche de contact, faute de cle de rapprochement.
        if mail and "@" not in mail:
            ecartes.append({"ligne": n, "motif": "adresse mail invalide",
                            "qui": (prenom + " " + nom).strip()})
            continue
        cle = mail.lower() if mail else ""
        if cle and cle in connus:
            ecartes.append({"ligne": n, "motif": "déjà inscrit à cette session",
                            "qui": (prenom + " " + nom).strip()})
            continue
        if cle and cle in vus:
            ecartes.append({"ligne": n, "motif": "en double dans la liste saisie",
                            "qui": (prenom + " " + nom).strip()})
            continue
        if cle:
            vus.add(cle)
        import contacts as _C
        retenus.append({"nom": nom, "prenom": prenom, "mail": mail,
                        "telephone": (g.get("telephone") or "").strip(),
                        "ville": (g.get("ville") or "").strip(),
                        # DEUX VALEURS, et c'est voulu. « fonction » est validee :
                        # la convention liste chaque participant avec la sienne, et
                        # une case vide y serait un trou dans un acte. « fonction_saisie »
                        # garde ce qui a REELLEMENT ete declare, vide compris.
                        # RIEN DE DECLARE RESTE VIDE. « fonction_valide » ramene
                        # tout ce qu'elle ne reconnait pas — le vide compris — a
                        # « Chirurgien-dentiste ». Appliquee sans condition, elle
                        # inventait une fonction pour chaque participant, et la
                        # convention l'imprimait comme une declaration.
                        "fonction": (_C.fonction_valide(g.get("fonction"))
                                     if (g.get("fonction") or "").strip() else ""),
                        # LA CSP EST ENREGISTREE, PAS RECALCULEE A CHAQUE LECTURE.
                        # Le portail OPCO l'exige pour chaque salarie ; elle se
                        # deduit de la fonction, mais la deduire au vol la ferait
                        # changer retroactivement le jour ou la regle change —
                        # y compris sur des dossiers deja deposes.
                        "csp": _C.csp(_C.fonction_valide(g.get("fonction"))
                                      if (g.get("fonction") or "").strip() else ""),
                        "fonction_saisie": (g.get("fonction") or "").strip()})
    if request.form.get("verifier") == "1":
        return jsonify({"ok": True, "apercu": True, "retenus": retenus, "ecartes": ecartes})
    if not retenus:
        return jsonify({"ok": False, "message": "Aucun participant exploitable.", "ecartes": ecartes})

    horodateur = _dt.now().strftime("%d/%m/%Y %H:%M:%S")
    lignes = [{"horodateur": horodateur, "nom": p["nom"], "prenom": p["prenom"],
               "mail": p["mail"], "telephone": p["telephone"], "ville": p["ville"],
               "date_formation": S.get("date_texte") or "",
               "demande": "Inscrit par " + (S.get("client") or "son organisme"),
               "statut": "Inscrit", "fonction": p.get("fonction") or "",
               # ON GARDE CE QUI A ETE DECLARE, vide compris. Le commentaire
               # plus haut annonce deux valeurs depuis le debut, mais seule la
               # premiere arrivait jusqu'au suivi : « fonction_saisie » etait
               # calculee puis jetee. Sans elle, impossible de distinguer un
               # chirurgien-dentiste declare d'une case laissee vide et comblee
               # par le defaut — et c'est justement la difference qui compte
               # sur une convention.
               "fonction_saisie": p.get("fonction_saisie") or "",
               "csp": p.get("csp") or ""}
              for p in retenus]
    try:
        _suivi.ajouter_plusieurs(lignes, code)
    except Exception as e:
        return jsonify({"ok": False, "message": "Écriture impossible : " + str(e)[:140]})
    # Les fiches de contact naissent MAINTENANT, pas pendant la frappe : une
    # saisie abandonnee ne doit pas laisser de demi-contacts derriere elle.
    import contacts as _C
    import sessions as _sess
    marqueur = ""
    try:
        import clients as _CL
        marqueur = (_CL.client(_sess.client_de(code)) or {}).get("marqueur") or ""
    except Exception:
        marqueur = ""
    fiches, rattaches = 0, 0
    for p in retenus:
        if not (p["mail"] or p["telephone"]):
            continue          # sans coordonnee, aucune fiche rapprochable
        try:
            deja = _C.rapprocher(mail=p["mail"], telephone=p["telephone"])
            if deja:
                a_poser = {}
                if marqueur and marqueur not in (deja.get("marqueurs") or []):
                    a_poser["marqueurs"] = sorted(set(deja.get("marqueurs") or []) | {marqueur})
                # On n'ecrit sur la FICHE que ce qui a ete declare. Y poser la
                # valeur par defaut ferait passer une supposition pour un fait —
                # et empecherait ensuite la vraie reponse du formulaire d'y
                # descendre, la synchronisation ne remplissant que les vides.
                if p.get("fonction_saisie") and not (deja.get("fonction") or "").strip():
                    a_poser["fonction"] = p["fonction"]
                if a_poser:
                    _C.modifier(deja["id"], a_poser)
                    rattaches += 1
            else:
                _C.creer(dict(p, source="session client " + code,
                              marqueurs=[marqueur] if marqueur else []))
                fiches += 1
        except Exception:
            pass          # une fiche de contact ratee ne doit pas perdre l'inscription
    try:
        journal.ecrire("Participants saisis", "", str(len(lignes)) + " participant(s)", "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "ajoutes": len(lignes), "ecartes": ecartes,
                    "fiches_creees": fiches, "fiches_rattachees": rattaches})
@app.route("/contacts/suggestions")
def suggestions_contacts():
    """Propositions pour la saisie des participants : on tape, DFM cherche.
    Trois caracteres minimum — en deca, la recherche ramenerait la moitie de
    la base sans rien apprendre a personne."""
    import contacts as C
    q = (request.args.get("q") or "").strip()
    if len(q) < 3:
        return jsonify({"ok": True, "gens": []})
    try:
        lignes, _ = C.lister(recherche=q, limite=8)
    except C.Indisponible:
        return jsonify({"ok": True, "gens": []})
    return jsonify({"ok": True, "gens": [{
        "id": f["id"], "nom": f.get("nom") or "", "prenom": f.get("prenom") or "",
        "affiche": C.nom_affiche(f), "mail": f.get("mail") or "",
        "telephone": f.get("telephone") or "",
        "fonction": f.get("fonction") or C.FONCTION_DEFAUT} for f in lignes]})
@app.route("/clients")
def page_clients():
    import clients as CL
    import contacts as C
    fiches = CL.liste()
    compte = {}
    try:
        compte = C.compter_par_marqueur()
    except Exception:
        pass
    # TABLEAU DE BORD PAR CLIENT (palier 8). Le cumul se lit dans le REGISTRE
    # des factures, pas dans les sessions : c'est ce qui a ete facture qui
    # compte pour le plafond OPCO, a la date de facture — une formation de
    # decembre facturee en janvier pese sur l'annee neuve.
    #
    # Le cumul ignore volontairement l'organisme : c'est le CLIENT qui a un
    # plafond, pas sa relation avec l'une ou l'autre de vos entites. Un centre
    # qui achete a Smileclub et a DSF consomme une seule enveloppe.
    import factures as REG
    import sessions as SE
    bilan = {}
    for f in fiches:
        plafond = CL.plafond(f) or 0
        cumul = REG.cumul_client(f["id"])
        pieces = REG.du_client(f["id"])
        # Les sessions de ce client, TOUS organismes confondus.
        codes = [c for c, s in SE.SESSIONS.items() if (s or {}).get("client") == f["id"]]
        bilan[f["id"]] = {
            "plafond": plafond, "cumul": cumul,
            "reste": (plafond - cumul) if plafond else 0,
            # Borne a 100 pour l'affichage : une barre ne depasse pas son cadre.
            # Le DEPASSEMENT reste visible par le montant et la couleur.
            "part": min(100, round(cumul * 100.0 / plafond)) if plafond else 0,
            "depasse": bool(plafond and cumul > plafond),
            "factures": pieces, "nb_factures": len(pieces),
            "nb_sessions": len(codes),
        }
    return render_template("clients.html", clients=fiches, champs=CL.CHAMPS,
                           choix=CL.CHOIX, strict=sorted(CL.CHOIX_STRICT), compte=compte,
                           bilan=bilan, annee=__import__("datetime").datetime.now().year,
                           manques={f["id"]: CL.complet(f) for f in fiches})
@app.route("/clients/enregistrer", methods=["POST"])
def enregistrer_client():
    import clients as CL
    donnees = {cle: request.form.get(cle) for cle, _, _ in CL.CHAMPS}
    ident = (request.form.get("id") or "").strip()
    try:
        fiche = CL.modifier(ident, donnees) if ident else CL.creer(donnees)
    except ValueError as e:
        return jsonify({"ok": False, "message": str(e)})
    try:
        journal.ecrire("Client modifié" if ident else "Client créé",
                       fiche["raison_sociale"], "marqueur « " + fiche["marqueur"] + " »")
    except Exception:
        pass
    return jsonify({"ok": True, "id": fiche["id"], "marqueur": fiche["marqueur"],
                    "manques": CL.complet(fiche)})
@app.route("/clients/<identifiant>/supprimer", methods=["POST"])
def supprimer_client(identifiant):
    """Le MARQUEUR RESTE et redevient ordinaire, sans proposition ni condition.
    Les praticiens qui le portent le gardent : ils ont bien ete formes par ce
    centre. C'est a l'utilisateur de le retirer, fiche par fiche, s'il le veut."""
    import clients as CL
    fiche = CL.supprimer(identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Client introuvable."})
    try:
        journal.ecrire("Client supprimé", fiche["raison_sociale"],
                       "le marqueur « " + fiche["marqueur"] + " » est conservé")
    except Exception:
        pass
    return jsonify({"ok": True, "marqueur": fiche["marqueur"]})
@app.route("/contacts/creer", methods=["POST"])
def creer_contact():
    """Saisie a la main. Le seul chemin d'entree qui manquait : jusqu'ici une
    fiche ne pouvait naitre que d'un import ou du classeur."""
    import contacts as C
    fiche = {cle: (request.form.get(cle) or "").strip()
             for cle in ("nom", "prenom", "mail", "telephone", "ville")}
    fiche["marqueurs"] = [m for m in (request.form.get("marqueurs") or "").split(",") if m.strip()]
    fiche["source"] = "saisie manuelle"
    if not (C.norm_mail(fiche["mail"]) or C.norm_tel(fiche["telephone"])):
        return jsonify({"ok": False, "message": "Il faut au moins une adresse mail ou un téléphone."})
    try:
        # On previent d'un doublon AVANT de creer, sinon la meme personne
        # existerait deux fois sans que rien ne l'ait signale.
        deja = C.rapprocher(mail=fiche["mail"], telephone=fiche["telephone"])
        if deja and (request.form.get("confirme") or "") != "1":
            return jsonify({"ok": False, "doublon": True, "id": deja["id"],
                            "qui": C.nom_affiche(deja),
                            "mail": deja.get("mail") or "", "tel": deja.get("telephone") or ""})
        f = C.creer(fiche)
    except ValueError as e:
        return jsonify({"ok": False, "message": str(e)})
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    return jsonify({"ok": True, "id": f["id"], "nom": C.nom_affiche(f)})
@app.route("/contacts/marqueurs")
def liste_marqueurs():
    import contacts as C
    compte = {}
    try:
        compte = C.compter_par_marqueur()
    except Exception:
        pass
    return jsonify({"ok": True, "marqueurs": [
        dict(m, portees=compte.get(m["cle"], 0))
        for m in C.marqueurs() if not C.est_reserve(m["cle"])]})
@app.route("/contacts/export.csv")
def export_contacts():
    """Exporte CE QUE L'ECRAN MONTRE : les memes filtres, sans la pagination.
    Pas de second jeu de criteres a comprendre — ce que vous voyez est ce que
    vous emportez.

    Le fichier commence par une marque d'octets UTF-8 : sans elle, Excel sur
    Windows affiche « Dupont » en « Ã©tienne » et le fichier parait corrompu."""
    import contacts as C
    import csv as _csv
    import io as _io
    from flask import Response
    q = (request.args.get("q") or "").strip()
    qualite = (request.args.get("qualite") or "").strip()
    sel = [m for m in (request.args.get("m") or "").split(",") if m.strip()]
    npc = (request.args.get("npc") or "") == "1"
    tri = (request.args.get("tri") or BD_TRIS[0][0]).strip()
    try:
        lignes, total = C.lister(recherche=q, filtre_marqueurs=sel, qualite=qualite,
                                 exclure_npc=npc, limite=20000, tri=_bd_tri(tri))
    except C.Indisponible as e:
        return "Export impossible : " + str(e), 503
    libelles = {m["cle"]: m["libelle"] for m in C.marqueurs()}
    tampon = _io.StringIO()
    plume = _csv.writer(tampon, delimiter=";", quoting=_csv.QUOTE_MINIMAL)
    plume.writerow(["Nom", "Prénom", "Adresse mail", "Téléphone", "Ville",
                    "Statut", "Marqueurs", "Ne plus contacter", "Date d'entrée", "Origine"])
    for f in lignes:
        marques = [libelles.get(m, m) for m in (f.get("marqueurs") or []) if not C.est_reserve(m)]
        plume.writerow([
            f.get("nom") or "", f.get("prenom") or "", f.get("mail") or "",
            f.get("telephone") or "", f.get("ville") or "",
            "Apprenant" if C.RESERVE_APPRENANT in (f.get("marqueurs") or []) else "Prospect",
            " · ".join(marques), "oui" if f.get("ne_plus_contacter") else "",
            _bd_date(f.get("cree_le")), f.get("source") or ""])
    from datetime import datetime as _dt
    nom = "contacts-dfm-" + _dt.now().strftime("%Y%m%d") + ".csv"
    return Response("﻿" + tampon.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="' + nom + '"'})
@app.route("/contacts/synchro", methods=["POST"])
def contacts_synchro():
    import contacts as C
    try:
        index = _bd_classeur()
        bilan = C.synchroniser_apprenants([p["identite"] for p in index.values()])
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:200]})
    try:
        if bilan["crees"] or bilan["marques"] or bilan["completes"]:
            journal.ecrire("Contacts synchronisés", "",
                           "%d créé(s), %d rattaché(s), %d complété(s)"
                           % (bilan["crees"], bilan["marques"], bilan["completes"]))
    except Exception:
        pass
    return jsonify({"ok": True, **bilan})
def _ct_contexte(fiche):
    """Le volet « contact » ajoute a la fiche apprenant : statut, marqueurs,
    coordonnees. C'est le meme ecran pour tout le monde — un prospect et un
    apprenant se consultent au meme endroit, avec la meme presentation."""
    import contacts as C
    if not fiche:
        return None
    return {"fiche": fiche,
            # La FONCTION vient d'une liste fermee : une saisie libre finirait
            # par produire « assistante », « Assistante », « assist. » — et le
            # ciblage d'un envoi ne retrouverait plus personne.
            "fonctions": C.FONCTIONS,
            "fonction_defaut": C.FONCTION_DEFAUT,
            "apprenant": C.RESERVE_APPRENANT in (fiche.get("marqueurs") or []),
            "joignable": C.contactable(fiche),
            "poses": [m for m in (fiche.get("marqueurs") or []) if not C.est_reserve(m)],
            "catalogue": [m for m in C.marqueurs() if not C.est_reserve(m["cle"])],
            "libelles": {m["cle"]: m["libelle"] for m in C.marqueurs()},
            "couleurs": {m["cle"]: m["couleur"] for m in C.marqueurs()}}
def _ct_dossier_minimal(fiche):
    """Le dossier d'une personne que le classeur ne connait pas. La fiche est
    la meme, ses rubriques sont simplement vides — plutot qu'un second ecran,
    plus pauvre, qu'il faudrait maintenir en parallele."""
    import contacts as C
    nom = (fiche.get("nom") or "").strip()
    prenom = (fiche.get("prenom") or "").strip()
    initiales = ((nom[:1] or "") + (prenom[:1] or "")).upper() or "?"
    return {"identite": {"nom": nom or (C.nom_affiche(fiche) if not prenom else ""),
                         "prenom": prenom, "mail": fiche.get("mail") or "",
                         "telephone": fiche.get("telephone") or "",
                         "ville": fiche.get("ville") or ""},
            "initiales": initiales, "parcours": [], "actifs": 0, "annulees": 0,
            "ca": 0, "attendu": 0, "completion": None, "premiere": "",
            "satisfactions": [], "evenements": [], "formations": [],
            "nb_fiches": 1, "ecarts": []}
@app.route("/contact/<int:identifiant>")
def fiche_contact(identifiant):
    """UNE SEULE FICHE pour tout le monde. Elle reprend le modele de la fiche
    apprenant — historique, chiffre d'affaires, satisfaction, activite — et y
    ajoute le statut et les marqueurs. Un prospect y apparait avec les memes
    rubriques, simplement vides."""
    import contacts as C
    try:
        f = C.par_id(identifiant)
    except C.Indisponible as e:
        return render_template("erreur.html", titre="Base indisponible", message=str(e)), 503
    if not f:
        return render_template("erreur.html", titre="Fiche introuvable",
                               message="Cette fiche n'existe plus."), 404
    d = None
    if (f.get("mail") or "").strip():
        try:
            dossier = _ap_dossier(f["mail"])
            if dossier and (dossier.get("parcours") or dossier.get("identite", {}).get("nom")):
                d = dossier
        except Exception:
            d = None
    return render_template("apprenant.html", d=d or _ct_dossier_minimal(f),
                           c=_ct_contexte(f))
@app.route("/contact/<int:identifiant>/modifier", methods=["POST"])
def modifier_contact(identifiant):
    """Coordonnees et marqueurs. Les marqueurs arrivent en LISTE COMPLETE :
    l'ecran envoie l'etat voulu, pas une difference — c'est ce qui permet d'en
    retirer un aussi simplement que d'en poser un."""
    import contacts as C
    champs = {}
    for cle in ("nom", "prenom", "mail", "telephone", "ville"):
        if cle in request.form:
            champs[cle] = (request.form.get(cle) or "").strip()
    # La FONCTION passe par le validateur, qui rend "" s'il ne reconnait rien.
    # Il ramenait autrefois sur « Chirurgien-dentiste » ; ce repli est retire
    # depuis que la convention refuse de s'editer sans fonction plutot que d'en
    # inventer une. Une valeur vide se voit et se corrige ; une valeur inventee
    # se signe.
    if "fonction" in request.form:
        champs["fonction"] = C.fonction_valide(request.form.get("fonction"))
    if "marqueurs" in request.form:
        champs["marqueurs"] = [m for m in (request.form.get("marqueurs") or "").split(",") if m.strip()]
    if "ne_plus_contacter" in request.form:
        champs["ne_plus_contacter"] = (request.form.get("ne_plus_contacter") or "") == "1"
    if not champs:
        return jsonify({"ok": False, "message": "Rien à modifier."})
    try:
        avant = C.par_id(identifiant)
        if "marqueurs" in champs and avant:
            # La qualite d'apprenant est calculee, elle n'appartient pas a
            # l'utilisateur : on la reporte telle quelle, sinon un simple
            # enregistrement de fiche la ferait disparaitre.
            reserves = [m for m in (avant.get("marqueurs") or []) if C.est_reserve(m)]
            champs["marqueurs"] = sorted(set(champs["marqueurs"]) | set(reserves))
        if not (champs.get("mail", avant.get("mail") if avant else "")
                or champs.get("telephone", avant.get("telephone") if avant else "")):
            return jsonify({"ok": False,
                            "message": "Il faut au moins une adresse mail ou un téléphone."})
        f = C.modifier(identifiant, champs)
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    return jsonify({"ok": True, "nom": C.nom_affiche(f or {})})
@app.route("/contact/<int:identifiant>/supprimer", methods=["POST"])
def supprimer_contact(identifiant):
    import contacts as C
    try:
        C.supprimer([identifiant])
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    return jsonify({"ok": True})
def _im_fichiers():
    """Les fichiers de liste poses dans le dossier DFM. Plus simple qu'un
    televersement : l'utilisateur depose son fichier et le retrouve ici."""
    import lecteur
    sortie = []
    for nom in sorted(os.listdir(DOSSIER)):
        ext = os.path.splitext(nom)[1].lower()
        if ext not in lecteur.FORMATS_CONNUS or nom == "requirements.txt":
            continue
        chemin = os.path.join(DOSSIER, nom)
        sortie.append({"nom": nom, "taille": os.path.getsize(chemin) // 1024})
    return sortie
def _im_chemin(nom):
    """Un nom de fichier, jamais un chemin : sans cela « ../../ » sortirait du
    dossier et donnerait a lire n'importe quel fichier de l'ordinateur."""
    nom = os.path.basename((nom or "").strip())
    chemin = os.path.join(DOSSIER, nom)
    if not nom or not os.path.exists(chemin):
        raise ValueError("Fichier introuvable dans le dossier DFM.")
    return chemin
@app.route("/contacts/import")
def page_import():
    import contacts as C
    pret, souci = C.disponible()
    return render_template("contacts_import.html", pret=pret, souci=souci,
                           fichiers=_im_fichiers(),
                           marqueurs=[m for m in C.marqueurs() if not C.est_reserve(m["cle"])])
@app.route("/contacts/import/televerser", methods=["POST"])
def import_televerser():
    """Recoit un fichier depuis l'ecran — bouton ou glisser-deposer — et le
    range dans le dossier DFM. Il n'y avait jusqu'ici aucun moyen d'en deposer
    un sans passer par le Finder, ce qui rendait l'ecran inutilisable.

    Trois garde-fous : l'extension doit etre lue par DFM, le nom est reduit a
    son dernier element pour qu'aucun chemin ne sorte du dossier, et un fichier
    de meme nom est numerote plutot qu'ecrase — on n'efface pas la liste de
    quelqu'un parce qu'il a rimporte le meme nom."""
    import lecteur
    envoye = request.files.get("fichier")
    if not envoye or not (envoye.filename or "").strip():
        return jsonify({"ok": False, "message": "Aucun fichier reçu."})
    nom = os.path.basename(envoye.filename.replace("\\", "/")).strip()
    ext = os.path.splitext(nom)[1].lower()
    if ext in lecteur.FORMATS_REFUSES:
        return jsonify({"ok": False,
                        "message": "Format non lu — c'est " + lecteur.FORMATS_REFUSES[ext]})
    if ext not in lecteur.FORMATS_CONNUS:
        return jsonify({"ok": False, "message": "Format non lu. Déposez un .csv ou un .xlsx."})
    base, _ = os.path.splitext(nom)
    cible, n = os.path.join(DOSSIER, nom), 1
    while os.path.exists(cible):
        cible = os.path.join(DOSSIER, "%s (%d)%s" % (base, n, ext))
        n += 1
    try:
        envoye.save(cible)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)[:120]})
    if os.path.getsize(cible) > 25 * 1024 * 1024:
        os.remove(cible)
        return jsonify({"ok": False, "message": "Fichier trop volumineux (plus de 25 Mo)."})
    return jsonify({"ok": True, "nom": os.path.basename(cible),
                    "taille": os.path.getsize(cible) // 1024})
@app.route("/contacts/import/analyser", methods=["POST"])
def import_analyser():
    """Lit le fichier et propose une correspondance. N'ECRIT RIEN."""
    import lecteur, imports as I
    try:
        chemin = _im_chemin(request.form.get("fichier"))
        d = lecteur.lire(chemin)
    except (ValueError, Exception) as e:
        if isinstance(e, lecteur.Illisible) or isinstance(e, ValueError):
            return jsonify({"ok": False, "message": str(e)})
        return jsonify({"ok": False, "message": "Lecture impossible : " + str(e)[:150]})
    colonnes = I.reconnaitre(d["entetes"], d["lignes"])
    bilan = I.preparer(d["entetes"], d["lignes"], colonnes)
    return jsonify({"ok": True, "detail": d["detail"], "avec_entetes": d["avec_entetes"],
                    "colonnes": colonnes, "libelles": I.LIBELLES,
                    "apercu": I.apercu(d["entetes"], d["lignes"], colonnes),
                    "bilan": {k: v for k, v in bilan.items() if k != "retenues"},
                    "retenus": len(bilan["retenues"])})
@app.route("/contacts/import/recalculer", methods=["POST"])
def import_recalculer():
    """Rejoue l'apercu avec la correspondance corrigee par l'utilisateur.
    Toujours sans ecrire : c'est ce qui permet d'essayer avant de decider."""
    import lecteur, imports as I
    try:
        d = lecteur.lire(_im_chemin(request.form.get("fichier")))
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:150]})
    colonnes = _im_colonnes(request.form.get("plan"), d["entetes"])
    bilan = I.preparer(d["entetes"], d["lignes"], colonnes)
    return jsonify({"ok": True, "apercu": I.apercu(d["entetes"], d["lignes"], colonnes),
                    "bilan": {k: v for k, v in bilan.items() if k != "retenues"},
                    "retenus": len(bilan["retenues"])})
def _im_colonnes(plan_json, entetes):
    """Le plan renvoye par l'ecran : [{index, champ, ordre}, ...]."""
    import json as _json
    import imports as I
    brut = _json.loads(plan_json or "[]")
    sortie = []
    for i, titre in enumerate(entetes):
        c = next((x for x in brut if int(x.get("index", -1)) == i), {})
        champ = c.get("champ") or "ignore"
        if champ not in I.CHAMPS:
            champ = "ignore"
        sortie.append({"index": i, "titre": titre, "champ": champ,
                       "ordre": c.get("ordre") or "nom_prenom", "raison": "", "exemples": []})
    return sortie
@app.route("/contacts/import/executer", methods=["POST"])
def import_executer():
    import lecteur, imports as I, contacts as C
    from datetime import datetime as _dt
    try:
        nom = os.path.basename((request.form.get("fichier") or "").strip())
        d = lecteur.lire(_im_chemin(nom))
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:150]})
    colonnes = _im_colonnes(request.form.get("plan"), d["entetes"])
    cles = [c for c in (request.form.get("marqueurs") or "").split(",") if c.strip()]
    bilan = I.preparer(d["entetes"], d["lignes"], colonnes)
    lot = _dt.now().strftime("%Y%m%d-%H%M%S")
    try:
        rapport = I.executer(bilan["retenues"], cles, lot, source=nom)
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    try:
        journal.ecrire("Contacts importés", nom,
                       "%d créé(s), %d complété(s)" % (rapport["crees"], rapport["completes"]),
                       "", "", lot)
    except Exception:
        pass
    rapport.update({"ok": True, "fichier": nom, "ecartees": bilan["ecartees"],
                    "doublons_internes": bilan["doublons_internes"], "lues": bilan["lues"]})
    return jsonify(rapport)
@app.route("/contacts/import/annuler", methods=["POST"])
def import_annuler():
    """Retire les fiches CREEES par un import. Les completions apportees aux
    fiches deja presentes ne sont pas defaites : elles n'ont comble que du
    vide, et le rendre a son vide n'aurait aucun sens."""
    import contacts as C
    lot = (request.form.get("lot") or "").strip()
    try:
        n = C.supprimer_lot(lot)
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    try:
        if n:
            journal.ecrire("Import annulé", "", "%d fiche(s) retirée(s)" % n)
    except Exception:
        pass
    return jsonify({"ok": True, "retirees": n})
@app.route("/contacts/marqueur", methods=["POST"])
def contacts_marqueur():
    """Cree, renomme ou supprime un marqueur du catalogue."""
    import contacts as C
    action = (request.form.get("action") or "").strip()
    try:
        if action == "creer":
            # Aucune couleur transmise : elle est attribuee d'office selon le
            # rang. L'utilisateur ne veut pas avoir a la choisir, et un gris
            # par defaut annulait justement l'attribution automatique.
            cle = C.creer_marqueur(request.form.get("libelle") or "")
            return jsonify({"ok": True, "cle": cle})
        if action == "renommer":
            C.renommer_marqueur(request.form.get("cle") or "",
                                request.form.get("libelle") or "",
                                request.form.get("couleur") or None)
            return jsonify({"ok": True})
        if action == "supprimer":
            cle = (request.form.get("cle") or "").strip()
            portees = C.lister(filtre_marqueurs=[cle], limite=1)[1]
            if portees and (request.form.get("confirme") or "") != "1":
                # On ne supprime pas un marqueur porte par des fiches sans
                # l'avoir dit : c'est une perte de classement irreversible.
                return jsonify({"ok": False, "confirmation": True, "portees": portees})
            if portees:
                lignes = C.lister(filtre_marqueurs=[cle], limite=5000)[0]
                C.poser_marqueurs([f["id"] for f in lignes], [cle], retirer=True)
            C.supprimer_marqueur(cle)
            return jsonify({"ok": True, "retires": portees})
    except ValueError as e:
        return jsonify({"ok": False, "message": str(e)})
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    return jsonify({"ok": False, "message": "Action inconnue"})
@app.route("/contacts/poser", methods=["POST"])
def contacts_poser():
    """Pose ou retire des marqueurs sur une selection de fiches."""
    import contacts as C
    ids = [int(x) for x in (request.form.get("ids") or "").split(",") if x.strip().isdigit()]
    cles = [c for c in (request.form.get("cles") or "").split(",") if c.strip()]
    retirer = (request.form.get("retirer") or "") == "1"
    if not ids or not cles:
        return jsonify({"ok": False, "message": "Rien à modifier."})
    try:
        n = C.poser_marqueurs(ids, cles, retirer=retirer)
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    return jsonify({"ok": True, "touches": n})
@app.route("/contacts/<int:identifiant>/npc", methods=["POST"])
def contacts_npc(identifiant):
    import contacts as C
    valeur = (request.form.get("valeur") or "") == "1"
    try:
        C.modifier(identifiant, {"ne_plus_contacter": valeur})
    except C.Indisponible as e:
        return jsonify({"ok": False, "message": str(e)})
    return jsonify({"ok": True, "valeur": valeur})
@app.route("/apprenant/<mail>/fusionner", methods=["POST"])
def fusionner_apprenant(mail):
    from connexion import service_sheets
    import suivi as _suivi
    import journal
    d = _ap_dossier(mail)
    if d["nb_fiches"] < 2 or not d["ecarts"]:
        return jsonify({"ok": False, "message": "Rien a fusionner : les fiches sont identiques."})
    ref = d["fiches"][0]
    # ON REGROUPE PAR SESSION, plus par classeur. Une meme personne inscrite a
    # plusieurs sessions a une ligne dans chaque onglet ; c'est la session qui
    # designe l'onglet, et c'est elle que la couche de suivi comprend.
    par_session = {}
    alignees = 0
    for o in d["fiches"][1:]:
        maj = {}
        for e in d["ecarts"]:
            cle = e["cle"]
            cible = (ref["identite"].get(cle) or "").strip()
            actuel = (o["identite"].get(cle) or "").strip()
            if not cible or cible == actuel:
                continue
            maj[cle] = cible
        if maj:
            par_session.setdefault(o["code"], []).append((o["numero"], maj))
            alignees += 1
    if not par_session:
        return jsonify({"ok": False, "message": "Rien a ecrire."})
    for code_s, lignes_maj in par_session.items():
        try:
            _suivi.ecrire_lignes(lignes_maj, code_s)
        except Exception as e:
            return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    nom = ((ref["identite"].get("prenom") or "") + " " + (ref["identite"].get("nom") or "")).strip()
    try:
        journal.ecrire("Fiches apprenant fusionnées", nom,
                       str(alignees) + " fiche(s) alignee(s) sur la plus recente")
    except Exception:
        pass
    return jsonify({"ok": True, "alignees": alignees,
                    "champs": [e["libelle"] for e in d["ecarts"]]})
_SESS_COL = {"code": 0, "nom": 1, "debut": 2, "fin": 3, "statut": 4, "cloture_le": 5,
             "emargement_le": 6, "lien_emargement": 7, "emargement_signe_le": 8,
             "lien_signe": 9, "places_max": 10, "terminee_le": 11, "report_le": 12,
             "alerte_le": 13}
def _et_lire(code=None):
    """L'etat de vie des sessions, depuis la base.

    « numero » — le numero de ligne dans l'onglet Google — a disparu : il n'y a
    plus de ligne a retrouver. Il est conserve a None pour les appelants qui le
    lisent encore, et il ne sert plus a ecrire.
    """
    try:
        etats = SESSIONS_MOD.etats()
    except Exception:
        return {}
    return {code_s: {"numero": None,
                     "statut": e.get("statut_session") or "ouverte",
                     "cloture_le": e.get("cloture_le", ""),
                     "terminee_le": e.get("terminee_le", ""),
                     "report_le": e.get("report_le", ""),
                     "alerte_le": e.get("alerte_le", "") or e.get("alerte_cloture_le", "")}
            for code_s, e in etats.items()}
def _et_session(code):
    d = _et_lire(code).get(code) or {}
    terminee = bool(d.get("terminee_le"))
    cloturee = (d.get("statut") == "cloturee") or terminee
    return {"numero": d.get("numero"),
            "statut": "terminee" if terminee else ("cloturee" if cloturee else "ouverte"),
            "cloturee": cloturee, "terminee": terminee,
            "cloture_le": d.get("cloture_le", ""), "terminee_le": d.get("terminee_le", ""),
            "report_le": d.get("report_le", ""), "alerte_le": d.get("alerte_le", "")}
# Les noms courts de _SESS_COL vers les champs de la base. Les deux vocabulaires
# coexistent : l'un vient des colonnes de l'onglet, l'autre de la table.
_ET_VERS_BASE = {"statut": "statut_session", "cloture_le": "cloture_le",
                 "emargement_le": "emargement_genere_le",
                 "lien_emargement": "lien_emargement",
                 "emargement_signe_le": "emargement_signe_le",
                 "lien_signe": "lien_emargement_signe",
                 "terminee_le": "terminee_le", "report_le": "report_le",
                 "alerte_le": "alerte_cloture_le"}


def _et_ecrire(code, champ, valeur):
    """Ecrit un champ d'etat. Rend True — il n'y a plus de ligne a trouver.

    L'ancienne version rendait False quand la session n'etait pas dans l'onglet,
    et les appelants traitaient ce cas comme un echec. Une session absente de la
    base n'existe plus : son etat est simplement cree.
    """
    cible = _ET_VERS_BASE.get(champ)
    if not cible:
        return False
    SESSIONS_MOD.poser_etat(code, cible, valeur)
    return True
_ET_BLOQUE_CLOTURE = ("inscription", "convention")
_ET_BLOQUE_TERMINEE = ("inscription", "convention", "mail", "promotion", "structure", "suppression")
def _et_verrou(code, action):
    etat = _et_session(code)
    if etat["terminee"] and action in _ET_BLOQUE_TERMINEE:
        return ("Cette session est terminée et archivée. Déverrouillez-la depuis sa fiche "
                "si vous devez vraiment agir dessus.")
    if etat["cloturee"] and action in _ET_BLOQUE_CLOTURE:
        return "Les inscriptions de cette session sont clôturées."
    return ""
def _et_controle(code):
    S = fiche_session(code)
    lignes = _lignes_onglet(S)
    actifs = [l for l in lignes if not l.get("annule_le")
              and "recontact" not in (l.get("demande") or "").lower()
              and not (l.get("file_attente_le") and not l.get("promu_le"))]
    def sans(champ):
        return [((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip() or l.get("mail", "")
                for l in actifs if not l.get(champ)]
    controles = [
        {"quoi": "convention signée", "noms": sans("signe_le"), "grave": True, "icone": "ti-writing-sign"},
        {"quoi": "règlement encaissé", "noms": sans("paiement_recu_le"), "grave": True, "icone": "ti-coin"},
        {"quoi": "attestation émise", "noms": sans("lien_attestation"), "grave": False, "icone": "ti-certificate"},
        {"quoi": "évaluation de sortie", "noms": sans("eval_fin_le"), "grave": False, "icone": "ti-school"},
        {"quoi": "questionnaire de satisfaction", "noms": sans("satisfaction_le"), "grave": False, "icone": "ti-star"},
    ]
    manque = [c for c in controles if c["noms"]]
    faits = [c["quoi"] for c in controles if not c["noms"]]
    try:
        emargement = bool(SESSIONS_MOD.etat(code)["emargement_signe_le"])
    except Exception:
        emargement = False
    return {"participants": len(actifs), "manque": manque, "faits": faits,
            "graves": len([c for c in manque if c["grave"]]),
            "emargement_signe": emargement}
@app.route("/session/<code>/controle")
def controle_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    S = fiche_session(code)
    d = _et_controle(code)
    d["ok"] = True
    d["etat"] = _et_session(code)
    d["formation"] = S.get("nom_formation") or ""
    d["date_texte"] = S.get("date_texte") or ""
    return jsonify(d)
@app.route("/session/<code>/rouvrir", methods=["POST"])
def rouvrir_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import journal
    etat = _et_session(code)
    if etat["terminee"]:
        return jsonify({"ok": False, "message": "Session terminée : déverrouillez-la d'abord."})
    if not etat["cloturee"]:
        return jsonify({"ok": False, "message": "Les inscriptions sont déjà ouvertes."})
    if not _et_ecrire(code, "statut", "ouverte"):
        return jsonify({"ok": False, "message": "Session absente de l'onglet Sessions."})
    _et_ecrire(code, "cloture_le", "")
    S = fiche_session(code)
    try:
        journal.ecrire("Inscriptions rouvertes", "", S.get("nom_formation") or code, "", code)
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/session/<code>/terminer", methods=["POST"])
def terminer_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    from datetime import datetime as dt
    import journal
    etat = _et_session(code)
    if etat["terminee"]:
        return jsonify({"ok": False, "message": "Cette session est déjà terminée."})
    maintenant = dt.now().strftime("%d/%m/%Y %H:%M")
    if not _et_ecrire(code, "terminee_le", maintenant):
        return jsonify({"ok": False, "message": "Session absente de l'onglet Sessions."})
    if not etat["cloturee"]:
        _et_ecrire(code, "statut", "cloturee")
        _et_ecrire(code, "cloture_le", maintenant)
    _et_ecrire(code, "report_le", "")
    d = _et_controle(code)
    S = fiche_session(code)
    try:
        journal.ecrire("Session terminée et archivée", "",
                       (S.get("nom_formation") or code) + " — " + str(d["participants"]) + " participant(s)",
                       "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "le": maintenant, "participants": d["participants"],
                    "restait": len(d["manque"])})
@app.route("/session/<code>/deverrouiller", methods=["POST"])
def deverrouiller_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    import journal
    if (request.form.get("confirmation") or "").strip() != code:
        return jsonify({"ok": False, "message": "Le code recopié ne correspond pas."})
    etat = _et_session(code)
    if not etat["terminee"]:
        return jsonify({"ok": False, "message": "Cette session n'est pas archivée."})
    if not _et_ecrire(code, "terminee_le", ""):
        return jsonify({"ok": False, "message": "Session absente de l'onglet Sessions."})
    S = fiche_session(code)
    try:
        journal.ecrire("Session déverrouillée", "",
                       (S.get("nom_formation") or code) + " — archivée le " + etat["terminee_le"],
                       "", code)
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/session/<code>/reporter", methods=["POST"])
def reporter_cloture(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    from datetime import datetime as dt, timedelta
    import journal
    dans_deux_mois = (dt.now() + timedelta(days=60)).strftime("%d/%m/%Y")
    if not _et_ecrire(code, "report_le", dans_deux_mois):
        return jsonify({"ok": False, "message": "Session absente de l'onglet Sessions."})
    try:
        journal.ecrire("Clôture reportée", "", "prochaine relance le " + dans_deux_mois, "", code)
    except Exception:
        pass
    return jsonify({"ok": True, "prochaine": dans_deux_mois})
@app.route("/session/<code>/etat")
def etat_session(code):
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue"})
    etat = _et_session(code)
    etat["ok"] = True
    etat["code"] = code
    return jsonify(etat)
@app.route("/templates/mail/<usage>/<identifiant>")
def editeur_mail(usage, identifiant):
    import mails
    if usage not in mails.USAGES:
        return redirect("/templates")
    fiche = None
    if identifiant not in ("nouveau", "defaut"):
        fiche = mails.modele(identifiant)
    if fiche is None:
        fiche = mails.defaut(usage)
        if identifiant == "nouveau" and fiche:
            fiche = dict(fiche)
            fiche["titre"] = ""
        elif fiche:
            fiche = dict(fiche)
            fiche["titre"] = (fiche.get("titre") or usage) + " (copie)"
    if fiche is None:
        return redirect("/templates")
    fiche["usage"] = usage
    if not fiche.get("blocs"):
        fiche["blocs"] = [dict(x) for x in mails.BLOCS_DEFAUTS.get(usage, [])]
    fiche.setdefault("objet", "")
    fiche.setdefault("objet_promu", "")
    fiche.setdefault("titre", "")
    return render_template("editeur_mail.html", usage=usage, fiche=fiche,
                           infos=mails.USAGES[usage], balises=mails.BALISES,
                           exemple=mails.exemple(), enveloppe=mails.ENVELOPPE,
                           retour=request.args.get("retour") or "")
@app.route("/templates/mail/<usage>", methods=["POST"])
def enregistrer_mail(usage):
    import mails
    import journal
    if usage not in mails.USAGES:
        return jsonify({"ok": False, "message": "Usage inconnu"})
    brut = request.get_json(silent=True) or {}
    titre = (brut.get("titre") or "").strip()
    blocs = brut.get("blocs") or []
    objet = (brut.get("objet") or "").strip()
    if not titre:
        return jsonify({"ok": False, "message": "Donnez un nom a ce modele."})
    if not objet:
        return jsonify({"ok": False, "message": "L'objet du mail ne peut pas etre vide."})
    if not blocs:
        return jsonify({"ok": False, "message": "Le mail ne contient aucun bloc."})
    orphelines = mails.inconnues(mails.html_depuis_blocs(blocs) + " " + objet)
    fiche = {"usage": usage, "titre": titre, "objet": objet, "blocs": blocs}
    if brut.get("objet_promu"):
        fiche["objet_promu"] = (brut.get("objet_promu") or "").strip()
    identifiant = (brut.get("id") or "").strip()
    try:
        identifiant = mails.sauver(identifiant, fiche)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)})
    try:
        journal.ecrire("Modèle de mail enregistré", "", titre)
    except Exception:
        pass
    return jsonify({"ok": True, "id": identifiant, "titre": titre, "orphelines": orphelines})
@app.route("/templates/mail/<usage>/<identifiant>/supprimer", methods=["POST"])
def supprimer_mail(usage, identifiant):
    import mails
    try:
        from sessions import FORMATIONS
        usages = [c for c, f in FORMATIONS.items()
                  if (f or {}).get("modele_mail_" + usage) == identifiant]
    except Exception:
        usages = []
    if usages:
        noms = [{"code": c, "nom": _tp_nom_formation(c)} for c in usages]
        return jsonify({"ok": False, "usages": noms,
                        "message": "Ce modèle est rattaché à " + str(len(noms))
                        + " formation(s). Le supprimer les ferait retomber sans "
                        "prévenir sur le texte fourni avec DFM."})
    if mails.supprimer(identifiant):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "message": "Modele introuvable"})
@app.route("/templates/mail/apercu", methods=["POST"])
def apercu_mail():
    import mails
    brut = request.get_json(silent=True) or {}
    blocs = brut.get("blocs") or []
    fiche = {"objet": brut.get("objet") or "", "blocs": blocs,
             "objet_promu": brut.get("objet_promu") or ""}
    contexte = mails.exemple()
    rendu = mails.rendre(fiche, contexte, promu=bool(brut.get("promu")))
    source = mails.html_depuis_blocs(blocs)
    return jsonify({"ok": True, "objet": rendu["objet"], "html": _apercu_logo(rendu["html"]),
                    "code": source,
                    "orphelines": mails.inconnues(source + " " + (brut.get("objet") or ""))})
@app.route("/templates/mails/liste/<usage>")
def liste_mails(usage):
    import mails
    if usage not in mails.USAGES:
        return jsonify({"ok": False, "message": "Usage inconnu"})
    sortie = [{"id": "", "titre": "Texte fourni avec DFM", "defaut": True}]
    for m in mails.lister(usage):
        sortie.append({"id": m["id"], "titre": m.get("titre") or m["id"], "defaut": False})
    return jsonify({"ok": True, "modeles": sortie})
@app.route("/templates/balises")
def page_balises():
    import mails
    return render_template("balises.html", balises=mails.BALISES,
                           usages=mails.USAGES, exemple=mails.exemple())
def _ml_verifier(fiche):
    import mails
    soucis = []
    blocs = fiche.get("blocs") or []
    objet = (fiche.get("objet") or "").strip()
    if len(objet) > 60:
        soucis.append({"grave": False, "texte": "L'objet fait " + str(len(objet))
                       + " caracteres. Au-dela de 60, les boites mail le coupent."})
    if not objet:
        soucis.append({"grave": True, "texte": "L'objet est vide."})
    texte = mails.html_depuis_blocs(blocs)
    for i, b in enumerate(blocs, 1):
        if b.get("type") == "bouton":
            lien = (b.get("lien") or "").strip()
            if not lien or lien == "#":
                soucis.append({"grave": True, "texte": "Le bouton du bloc " + str(i)
                               + " n'a pas de destination."})
            if not (b.get("libelle") or "").strip():
                soucis.append({"grave": True, "texte": "Le bouton du bloc " + str(i)
                               + " n'a pas de texte."})
        if b.get("type") == "lien" and not (b.get("lien") or "").strip():
            soucis.append({"grave": True, "texte": "Le lien du bloc " + str(i)
                           + " n'a pas de destination."})
    types = [b.get("type") for b in blocs]
    if "signature" not in types:
        soucis.append({"grave": False, "texte": "Aucun bloc Signature : le mail se terminera sans votre nom."})
    orphelines = mails.inconnues(texte + " " + objet)
    for o in orphelines:
        soucis.append({"grave": True, "texte": "La balise {{" + o + "}} n'existe pas : elle laissera un vide."})
    usage = fiche.get("usage")
    if usage == "confirmation":
        if "{{lien_paiement}}" not in texte and "{{iban}}" not in texte:
            soucis.append({"grave": False, "texte": "Ce mail ne mentionne ni lien de paiement ni virement."})
    if usage == "signature":
        if "{{lien_signature}}" not in texte:
            soucis.append({"grave": True, "texte": "Ce mail ne contient pas le lien de signature : "
                           "le praticien ne pourra pas signer sa convention."})
    return soucis
_LOGO_CACHE = {"id": "", "octets": None, "type": "image/png"}
def _logo_octets():
    """Les octets du logo de l'organisme, en cache. None si indisponible.

    Sert deux besoins : rendre l'image dans l'apercu, et en LIRE les
    dimensions pour que la balise <img> de l'apercu soit celle qui partira
    reellement. Un apercu qui ne montre pas les vraies proportions ne
    previent de rien.

    LE LOGO EST UN REGLAGE D'ORGANISME depuis le 16/08 : profil.logo() lit le
    fichier depose, et ne retombe sur le Drive que pour un organisme qui n'en a
    pas encore. Le cache reste utile — cet apercu se redessine a chaque frappe
    dans l'editeur de modeles.

    LA CLE DU CACHE INCLUT LA DATE ET LA TAILLE du fichier : sans cela, un
    nouveau logo depose sous le meme nom n'apparaitrait qu'au redemarrage."""
    import profil
    p = profil.chemin_image("logo_fichier")
    if p:
        try:
            st = os.stat(p)
            cle = "%s:%s:%s" % (p, st.st_mtime, st.st_size)
        except OSError:
            cle = p
        type_ = "image/jpeg" if p.lower().endswith((".jpg", ".jpeg")) else "image/png"
    else:
        cle = str((profil.charger() or {}).get("logo_id") or "")
        type_ = "image/png"
    if not cle:
        return None
    if _LOGO_CACHE["id"] != cle or _LOGO_CACHE["octets"] is None:
        octets = profil.logo()
        if not octets:
            return None
        _LOGO_CACHE["octets"] = octets
        _LOGO_CACHE["type"] = type_
        _LOGO_CACHE["id"] = cle
    return _LOGO_CACHE["octets"]
def _apercu_logo(html):
    """Le HTML d'un apercu : logo dimensionne, servi par la route locale.
    cid:logo ne veut rien dire pour un navigateur — il faut une adresse."""
    import mails
    octets = _logo_octets()
    if not octets:
        return (html or "").replace("cid:logo", "/logo-organisme")
    return mails.poser_logo(html, octets, source="/logo-organisme")
@app.route("/logo-organisme")
def logo_organisme():
    """Sert le logo de l'organisme actif, pour l'apercu des mails.
    A l'envoi reel, le logo est joint au message et reference par cid:logo —
    une reference qu'un navigateur ne sait pas resoudre. Sans cette route,
    l'apercu afficherait une image cassee la ou le destinataire verra le logo."""
    from flask import Response, abort
    octets = _logo_octets()
    if not octets:
        abort(404)
    return Response(octets, mimetype=_LOGO_CACHE["type"],
                    headers={"Cache-Control": "private, max-age=600"})
@app.route("/templates/mail/<usage>/<identifiant>/apercu")
def apercu_mail_enregistre(usage, identifiant):
    """Apercu d'un modele DEJA enregistre, depuis la bibliotheque.
    Distinct de /templates/mail/apercu, qui previsualise un brouillon en cours
    d'edition et recoit donc ses blocs dans le corps de la requete."""
    import mails
    fiche = mails.defaut(usage) if identifiant == "defaut" else mails.modele(identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Modèle introuvable"})
    rendu = mails.rendre(fiche, mails.exemple())
    html = _apercu_logo(rendu["html"] or "")
    return jsonify({"ok": True, "titre": fiche.get("titre") or usage,
                    "objet": rendu["objet"], "html": html,
                    "modifie_le": fiche.get("modifie_le") or ""})
@app.route("/templates/mail/<usage>/<identifiant>/dupliquer", methods=["POST"])
def dupliquer_mail(usage, identifiant):
    import mails
    fiche = mails.defaut(usage) if identifiant == "defaut" else mails.modele(identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Modèle introuvable"})
    copie = dict(fiche)
    copie.pop("id", None)
    copie.pop("modifie_le", None)
    copie["usage"] = usage
    copie["titre"] = ((fiche.get("titre") or usage) + " (copie)")[:120]
    # La copie ne reprend AUCUN rattachement : elle n'est utilisee par personne
    # tant qu'on ne l'a pas choisie dans une fiche formation.
    neuf = mails.sauver("", copie)
    try:
        journal.ecrire("Modèle dupliqué", "", copie["titre"])
    except Exception:
        pass
    return jsonify({"ok": True, "id": neuf,
                    "edition": "/templates/mail/%s/%s" % (usage, neuf)})
@app.route("/templates/questionnaire/<type_>/<identifiant>/apercu")
def apercu_questionnaire(type_, identifiant):
    """Apercu d'un questionnaire : les questions telles qu'elles seront posees."""
    import modeles
    import questionnaires as Q
    if identifiant == "type":
        fiche = dict(Q.FROID if type_ == "froid" else Q.SATISFACTION)
    elif type_ == "evaluation" and identifiant in Q.EVALUATIONS:
        fiche = dict(Q.EVALUATIONS[identifiant])
    else:
        fiche = modeles.modele(type_, identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Modèle introuvable"})
    # Noms de champs reels d'une question : enonce / propositions / reponse
    # (l'indice de la bonne), tels que corriger_avec() les lit.
    libelles_obj = fiche.get("objectifs") or {}
    items = []
    for q in (fiche.get("questions") or []):
        choix = []
        for i, c in enumerate(q.get("propositions") or []):
            texte = c if isinstance(c, str) else (c.get("texte") or "")
            choix.append({"texte": texte, "juste": i == q.get("reponse")})
        obj = q.get("objectif") or ""
        if isinstance(libelles_obj, dict) and libelles_obj.get(obj):
            obj = str(obj) + " · " + str(libelles_obj[obj])
        items.append({"genre": "question", "libelle": q.get("enonce") or "",
                      "choix": choix, "objectif": obj,
                      "explication": q.get("explication") or ""})
    for n in (fiche.get("notes") or []):
        items.append({"genre": "note", "libelle": n.get("libelle") or "",
                      "choix": [], "objectif": (fiche.get("axes") or {}).get(n.get("axe"), "")})
    for o in (fiche.get("ouvertes") or []):
        items.append({"genre": "ouverte", "libelle": o.get("libelle") or "",
                      "choix": [], "objectif": ""})
    return jsonify({"ok": True, "titre": fiche.get("titre") or identifiant,
                    "items": items, "seuil": fiche.get("seuil"),
                    "modifie_le": fiche.get("modifie_le") or ""})
@app.route("/templates/questionnaire/<type_>/<identifiant>/dupliquer", methods=["POST"])
def dupliquer_questionnaire(type_, identifiant):
    import modeles
    fiche = modeles.modele(type_, identifiant)
    if not fiche:
        return jsonify({"ok": False, "message": "Modèle introuvable"})
    copie = dict(fiche)
    copie.pop("id", None)
    copie.pop("modifie_le", None)
    copie["titre"] = ((fiche.get("titre") or identifiant) + " (copie)")[:120]
    neuf = modeles.sauver(type_, "", copie)
    try:
        journal.ecrire("Modèle dupliqué", "", copie["titre"])
    except Exception:
        pass
    return jsonify({"ok": True, "id": neuf,
                    "edition": "/templates/questionnaire/%s/%s" % (type_, neuf)})
@app.route("/templates/mail/verifier", methods=["POST"])
def verifier_mail():
    brut = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "soucis": _ml_verifier(brut)})
@app.route("/templates/mail/test", methods=["POST"])
def tester_mail():
    import mails
    from connexion import service_drive
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from sessions import COMMUN, session as _session
    import base64
    brut = request.get_json(silent=True) or {}
    destinataire = (brut.get("destinataire") or "").strip()
    if "@" not in destinataire:
        return jsonify({"ok": False, "message": "Adresse de destination invalide."})
    try:
        S = _session()
    except Exception:
        S = dict(COMMUN)
    ligne = {"prenom": "Camille", "nom": "Durand", "mail": destinataire, "ville": "Bordeaux"}
    contexte = mails.contexte(S, ligne, {
        "lien_signature": "https://exemple.test/signature",
        "lien_paiement": S.get("stripe_lien") or "https://exemple.test/paiement",
        "lien_annulation": "https://exemple.test/annulation",
        "intro": "<p>Ceci est un envoi de test : les informations sont fictives.</p>"})
    fiche = {"objet": brut.get("objet") or "", "objet_promu": brut.get("objet_promu") or "",
             "blocs": brut.get("blocs") or [], "usage": brut.get("usage") or ""}
    rendu = mails.rendre(fiche, contexte, promu=bool(brut.get("promu")))
    entete = ('<div style="max-width:560px;margin:0 auto 14px;padding:11px 14px;'
              'background:#fdf3e3;border:1px solid #f0cf94;border-radius:9px;'
              'font-family:Arial,sans-serif;font-size:12px;color:#8a5a06">'
              '<b>Envoi de test depuis DFM.</b> Les informations sont fictives. '
              'Ce message ne concerne aucun praticien reel.</div>')
    try:
        # La connexion Gmail a disparu d'ici : l'envoi passe par « courrier », qui
        # ouvre lui-meme ce dont il a besoin. Cette ligne ouvrait une session OAuth
        # au demarrage du script, meme quand aucun mail n'etait a envoyer.
        # Telecharge avant l'assemblage : l'envoi de test doit produire
        # exactement le meme <img> que l'envoi reel, dimensions comprises.
        logo_bytes = None
        try:
            logo_bytes = __import__("profil").logo(__import__("sessions").organisme_de(S["code"]))
        except Exception:
            pass
        message = MIMEMultipart("related")
        message["To"] = destinataire
        import mails as _m_exp
        _exp = _m_exp.expediteur(S if "S" in dir() else None)
        if _exp:
            message["From"] = _exp
        message["Subject"] = "[TEST] " + (rendu["objet"] or "Sans objet")
        corps = MIMEMultipart("alternative")
        corps.attach(MIMEText(entete + mails.poser_logo(rendu["html"], logo_bytes), "html"))
        message.attach(corps)
        if logo_bytes:
            logo = MIMEImage(logo_bytes)
            logo.add_header("Content-ID", "<logo>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            message.attach(logo)
        # L'ENVOI PASSE PAR LA PORTE « courrier ». L'organisme de la session
        # decide d'ou part le mail — deux entites, deux adresses.
        courrier.envoyer(message, SESSIONS_MOD.organisme_de(S["code"]))
    except Exception as e:
        return jsonify({"ok": False, "message": "Envoi impossible : " + str(e)[:140]})
    return jsonify({"ok": True, "destinataire": destinataire})
@app.route("/parametres")
def page_parametres():
    import parametres as P
    valeurs = P.toutes()
    sections = []
    for cle, nom, icone, aide in P.SECTIONS:
        reglages = []
        for p in P.SCHEMA:
            if p["section"] != cle:
                continue
            f = dict(p)
            f.update(valeurs.get(p["cle"], {}))
            reglages.append(f)
        sections.append({"cle": cle, "nom": nom, "icone": icone, "aide": aide,
                         "reglages": reglages,
                         "modifies": len([r for r in reglages if r.get("modifie")])})
    return render_template("parametres.html", sections=sections,
                           total=len(P.SCHEMA),
                           modifies=len([c for c in valeurs.values() if c.get("modifie")]))
@app.route("/parametres/enregistrer", methods=["POST"])
def enregistrer_parametres():
    import parametres as P
    import journal
    donnees = request.get_json(silent=True) or {}
    modifies, refuses = P.sauver(donnees)
    if modifies:
        try:
            journal.ecrire("Paramètres modifiés", "", ", ".join(modifies[:6])
                           + (" et " + str(len(modifies) - 6) + " autre(s)" if len(modifies) > 6 else ""))
        except Exception:
            pass
    return jsonify({"ok": True, "modifies": modifies, "refuses": refuses})
@app.route("/parametres/reinitialiser", methods=["POST"])
def reinitialiser_parametres():
    import parametres as P
    import journal
    cle = (request.form.get("cle") or "").strip()
    n = P.reinitialiser(cle or None)
    try:
        journal.ecrire("Paramètres réinitialisés", "", cle or "tous les réglages")
    except Exception:
        pass
    return jsonify({"ok": True, "remis": n})
@app.route("/parametres/export.json")
def export_parametres():
    from flask import Response
    from datetime import datetime as dt
    import parametres as P
    import json as _json
    try:
        import modeles
        bibliotheque = modeles.charger()
    except Exception:
        bibliotheque = {}
    try:
        import mails as _mails
        modeles_mail = _mails.charger()
    except Exception:
        modeles_mail = {}
    try:
        from sessions import FORMATIONS
        formations = dict(FORMATIONS)
    except Exception:
        formations = {}
    corps = {
        "exporte_le": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "parametres": P.charger(),
        "questionnaires": bibliotheque,
        "mails": modeles_mail,
        "formations": formations,
    }
    nom = "dfm-configuration-" + dt.now().strftime("%Y%m%d") + ".json"
    return Response(_json.dumps(corps, ensure_ascii=False, indent=1),
                    mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=" + nom})
def _par(cle, defaut=None):
    try:
        import parametres
        return parametres.valeur(cle, defaut)
    except Exception:
        return defaut
def _par_capacite():
    try:
        import parametres
        return int(parametres.valeur("capacite_defaut", 14))
    except Exception:
        return 14
def _par_periode():
    try:
        import parametres
        return parametres.valeur("periode_defaut", "m6")
    except Exception:
        return "m6"
@app.route("/profils")
def page_profils():
    import profil as PR
    if not PR.lister():
        PR.creer("Mon organisme")
    liste = []
    for p in PR.lister():
        d = PR.charger(p["id"])
        chiffres = {"sessions": 0, "participants": 0, "ca": 0}
        if p["id"] == PR.actif():
            try:
                g = donnees.global_kpi()
                chiffres["sessions"] = len(g.get("sessions") or [])
                chiffres["participants"] = sum(int(x.get("inscrits") or 0) for x in (g.get("sessions") or []))
                chiffres["ca"] = int(g.get("ca_encaisse") or 0)
            except Exception:
                pass
        liste.append({"id": p["id"], "nom": p["nom"], "couleur": p["couleur"],
                      "organisme": d.get("organisme") or "",
                      "siret": d.get("siret") or "",
                      "nda": d.get("numero_declaration") or "",
                      "iban": d.get("iban") or "",
                      "sessions": chiffres["sessions"],
                      "participants": chiffres["participants"],
                      "ca": chiffres["ca"]})
    return render_template("profils.html", profils=liste, actif=PR.actif())
@app.route("/profil")
def page_profil():
    """La fiche d'un organisme. Celle de l'actif par defaut, sinon celle demandee.

    DEFAUT CORRIGE LE 21/08/2026. L'ecran des profils proposait « Voir » sur les
    organismes non actifs, avec un lien « /profil?id=... » — mais cette route ne
    lisait jamais ce parametre. Toutes ses lectures portaient sur l'organisme
    actif : on cliquait « Voir » sur Smileclub, on lisait « Smileclub » en titre,
    et on voyait les valeurs de DSF en dessous. Deux entites juridiques, deux
    Qualiopi a defendre separement : c'est le genre de confusion qui finit par
    produire un document au mauvais nom.

    LA FICHE D'UN AUTRE ORGANISME EST EN LECTURE SEULE. Le libelle du bouton
    l'annonce deja — « Modifier » sur l'actif, « Voir » sur les autres — et c'est
    la reponse la plus sure : « /profil/enregistrer » ecrit sur l'organisme
    ACTIF, sans savoir lequel la page affichait. Offrir un formulaire modifiable
    sur une autre fiche aurait ecrit les valeurs de l'une dans l'autre.

    ON NE BASCULE PAS POUR REGARDER. « profil.basculer() » change l'etat de
    toute l'application : un aller-retour rate laisserait DFM sur le mauvais
    organisme, et le passage suivant du pipeline ecrirait sous cette identite.
    On lit avec un organisme explicite, ce que profil.py sait faire.
    """
    import profil as PR
    if not PR.lister():
        PR.creer("Mon organisme")
    _actif = PR.actif()
    _connus = {p["id"] for p in PR.lister()}
    _demande = (request.args.get("id") or "").strip()
    # Un identifiant inconnu ramene a l'actif plutot que de rendre une erreur :
    # un lien perime ne doit pas casser un ecran.
    _vu = _demande if _demande in _connus else _actif
    lecture_seule = (_vu != _actif)
    # « None » plutot que l'identifiant pour l'actif : c'est le chemin habituel,
    # avec ses valeurs communes, et il ne change pas d'un iota.
    _org = _vu if lecture_seule else None
    valeurs = PR.toutes(_org)
    sections = []
    for cle, nom, icone, aide in PR.SECTIONS:
        champs = []
        for p in PR.SCHEMA:
            if p["section"] != cle:
                continue
            f = dict(p)
            f.update(valeurs.get(p["cle"], {}))
            champs.append(f)
        remplis = len([c for c in champs if c.get("rempli")])
        sections.append({"cle": cle, "nom": nom, "icone": icone, "aide": aide,
                         "champs": champs, "remplis": remplis, "total": len(champs)})
    # L'ETAT DE L'ENVOI accompagne la fiche : la section « Envoi des mails »
    # doit dire ce qui se passe AUJOURD'HUI, pas seulement offrir un champ.
    try:
        import courrier as _c
        _ad = (PR.charger(_org) or {}).get("mail_contact") or ""
        _env = {"installe": _c.installe(_vu), "adresse": _ad,
                "serveur": (_c.reglages(_vu) or {}).get("serveur", ""),
                # LE FOURNISSEUR EST DEVINE DEPUIS L'ADRESSE : l'ecran doit
                # parler de Google a qui a une adresse Google, et de « votre
                # hebergeur » a qui a son propre domaine.
                "f": _c.deviner(_ad)}
    except Exception:
        _env = {"installe": False, "adresse": "", "serveur": "",
                "f": {"connu": False, "nom": "", "special": "", "serveur": "", "port": 587}}
    _fiche = PR.charger(_org)
    # « repli=False » sur une fiche consultee : ce que l'organisme regarde ne
    # doit jamais etre complete en douce par les valeurs de l'actif.
    _r = {} if not lecture_seule else {"donnees": _fiche, "repli": False}
    return render_template("profil.html", sections=sections, envoi=_env,
                           profils=PR.lister(), actif=_actif,
                           vu=_vu, lecture_seule=lecture_seule,
                           vu_nom=next((p["nom"] for p in PR.lister() if p["id"] == _vu), _vu),
                           fiche=_fiche,
                           soucis=PR.verifier(_fiche if lecture_seule else None, _org),
                           manquants=PR.manquants(_org),
                           clause=PR.clause_parties({"prenom": "Bruce", "nom": "WAYNE", "ville": "Paris 9"}, **_r),
                           pied=PR.pied_legal(**_r), tva=PR.mention_tva(**_r))
@app.route("/profil/enregistrer", methods=["POST"])
def enregistrer_profil():
    import profil as PR
    import journal
    donnees = request.get_json(silent=True) or {}
    soucis = PR.verifier(donnees)
    graves = [s for s in soucis if s["grave"]]
    if graves and not donnees.get("_forcer"):
        return jsonify({"ok": False, "soucis": soucis, "bloquant": True})
    donnees.pop("_forcer", None)
    brut_logo = donnees.pop("logo_donnees", None)
    if brut_logo and brut_logo.startswith("data:image"):
        try:
            import base64 as _b64
            from connexion import service_drive
            from googleapiclient.http import MediaInMemoryUpload
            entete, corps64 = brut_logo.split(",", 1)
            octets = _b64.b64decode(corps64)
            genre = "image/png" if "png" in entete else "image/jpeg"
            ext = ".png" if "png" in entete else ".jpg"
            support = MediaInMemoryUpload(octets, mimetype=genre)
            ancien = PR.valeur("logo_id")
            drive = service_drive()
            if ancien:
                try:
                    drive.files().update(fileId=ancien, media_body=support).execute()
                    donnees["logo_id"] = ancien
                except Exception:
                    ancien = None
            if not ancien:
                cree = drive.files().create(
                    body={"name": "logo-" + PR.actif() + ext},
                    media_body=support, fields="id").execute()
                donnees["logo_id"] = cree.get("id")
            donnees["logo_apercu"] = brut_logo
        except Exception as e:
            return jsonify({"ok": False, "message": "Envoi du logo impossible : " + str(e)[:120]})
    modifies, refuses = PR.sauver(donnees)
    if modifies:
        try:
            journal.ecrire("Profil de l'organisme modifié", "",
                           ", ".join(modifies[:6]) + (" et " + str(len(modifies) - 6) + " autre(s)" if len(modifies) > 6 else ""))
        except Exception:
            pass
    return jsonify({"ok": True, "modifies": modifies, "refuses": refuses, "soucis": PR.verifier()})
@app.route("/profil/basculer", methods=["POST"])
def basculer_profil():
    import profil as PR
    import journal
    i = (request.form.get("id") or "").strip()
    if not PR.basculer(i):
        return jsonify({"ok": False, "message": "Ce profil n'existe pas."})
    import sessions as _sessions
    _sessions.appliquer_identite()
    try:
        journal.ecrire("Changement d'organisme", "", i)
    except Exception:
        pass
    return jsonify({"ok": True, "actif": i})
@app.route("/profil/creer", methods=["POST"])
def creer_profil():
    import profil as PR
    import journal
    nom = (request.form.get("nom") or "").strip()
    depuis = (request.form.get("depuis") or "").strip()
    if not nom:
        return jsonify({"ok": False, "message": "Donnez un nom a cet organisme."})
    i = PR.creer(nom, depuis or None)
    PR.basculer(i)
    # Creer un organisme rend actif : sans cela COMMUN reste pointe sur le
    # precedent pour toute la duree du processus, et DFM produit des documents
    # au nom d'un organisme en en visant les classeurs d'un autre.
    import sessions as _sessions
    _sessions.appliquer_identite()
    try:
        journal.ecrire("Organisme créé", "", nom)
    except Exception:
        pass
    return jsonify({"ok": True, "id": i})
@app.route("/profil/supprimer", methods=["POST"])
def supprimer_profil_route():
    import profil as PR
    import journal
    i = (request.form.get("id") or "").strip()
    if (request.form.get("confirmation") or "").strip() != i:
        return jsonify({"ok": False, "message": "Le nom recopie ne correspond pas."})
    if not PR.supprimer_profil(i):
        return jsonify({"ok": False, "message": "Impossible : c'est votre dernier organisme."})
    # Supprimer l'organisme actif bascule sur un autre. Sans reappliquer
    # l'identite, DFM continuerait d'ecrire dans les classeurs d'un profil qui
    # n'existe plus — y compris le journal.
    import sessions as _sessions
    _sessions.appliquer_identite()
    try:
        journal.ecrire("Organisme supprimé", "", i)
    except Exception:
        pass
    return jsonify({"ok": True})
@app.route("/profil/image", methods=["POST"])
def profil_deposer_image():
    """Depose la signature ou le tampon de l'organisme actif."""
    import profil as _pr
    f = request.files.get("fichier")
    if not f or not f.filename:
        return jsonify({"ok": False, "message": "Aucun fichier reçu."})
    # Le second retour est un SOUCI quand le depot echoue, une NOTE quand il
    # reussit — « réduite de 4000 à 1600 pixels ». Les deux se disent, mais
    # pas de la meme facon.
    nom, mot = _pr.deposer_image((request.form.get("cle") or "").strip(),
                                 f.filename, f.read(), f.mimetype or "")
    if not nom:
        return jsonify({"ok": False, "message": mot})
    return jsonify({"ok": True, "nom": nom, "note": mot})
@app.route("/profil/image/<cle>/retirer", methods=["POST"])
def profil_retirer_image(cle):
    import profil as _pr
    _pr.retirer_image(cle)
    return jsonify({"ok": True})
@app.route("/profil/image/<cle>")
def profil_voir_image(cle):
    """Sert l'image pour l'apercu de l'ecran. Sans cache : elle change juste
    apres un depot, et une image en cache ferait croire a un echec."""
    from flask import Response, abort
    import profil as _pr
    # DE QUEL ORGANISME ? Corrige le 21/08/2026 : la route servait toujours le
    # fichier de l'organisme ACTIF. En consultant la fiche de Smileclub depuis
    # DSF, on voyait donc la signature et le tampon de DSF sous le nom de
    # Smileclub — le defaut meme que la lecture par organisme venait de corriger,
    # survivant dans les deux seules images de la page.
    _dem = (request.args.get("id") or "").strip()
    _org = _dem if _dem in {p["id"] for p in _pr.lister()} else None
    chemin = _pr.chemin_image(cle, _org)
    if not chemin:
        abort(404)
    import mimetypes
    with open(chemin, "rb") as f:
        return Response(f.read(), mimetype=mimetypes.guess_type(chemin)[0] or "image/png",
                        headers={"Cache-Control": "no-store"})
@app.route("/profil/apercu", methods=["POST"])
def apercu_profil():
    import profil as PR
    donnees = request.get_json(silent=True) or {}
    # DE QUEL ORGANISME PARLE-T-ON ? Corrige le 21/08/2026. Sans cette lecture,
    # l'apercu fusionnait les valeurs affichees sur les donnees de l'organisme
    # ACTIF, puis verifiait sans savoir a qui elles appartenaient : en consultant
    # Smileclub depuis DSF, il comparait Smileclub a Smileclub et annoncait
    # « ce SIRET est deja celui de Smileclub Formations ». Trois alertes fausses
    # sur une fiche saine, produites par une route que la page appelle toute
    # seule pendant la saisie — invisible dans le rendu, donc introuvable en
    # relisant le gabarit.
    _dem = (donnees.pop("_organisme", "") or "").strip()
    _org = _dem if _dem in {x["id"] for x in PR.lister()} else None
    _autre = bool(_org) and _org != PR.actif()
    ancien = PR.charger(_org)
    fusion = dict(ancien)
    fusion.update({k: v for k, v in donnees.items() if k in [p["cle"] for p in PR.SCHEMA]})
    # L'apercu ne touche plus au fichier de l'organisme (B4). L'ancienne version
    # ecrivait la fusion, lisait, puis restaurait : pendant cet intervalle, toute
    # autre requete — envoi de mail, generation de convention — lisait des valeurs
    # non enregistrees, et un arret du serveur les figeait definitivement.
    # « repli=False » des qu'il s'agit d'un autre organisme : ses champs vides ne
    # doivent pas etre combles par ceux de l'actif.
    _r = {"repli": False} if _autre else {}
    sortie = {"clause": PR.clause_parties({"prenom": "Bruce", "nom": "WAYNE", "ville": "Paris 9"}, fusion, **_r),
              "pied": PR.pied_legal(fusion, **_r), "tva": PR.mention_tva(fusion, **_r),
              "adresse": PR.adresse_complete(fusion, **({"repli": False} if _autre else {})),
              "soucis": PR.verifier(fusion, _org)}
    return jsonify({"ok": True, **sortie})
@app.context_processor
def _injecter_profil():
    try:
        import profil as PR
        i = PR.actif()
        d = PR.charger(i)
        return {"of_actif": {
            "id": i,
            "nom": d.get("marque") or d.get("organisme") or "Organisme sans nom",
            "raison": d.get("organisme") or "",
            "couleur": d.get("couleur") or "#4f7ef8",
            "complet": bool(d.get("siret") and d.get("numero_declaration") and d.get("iban")),
            "nombre": len(PR.lister())}}
    except Exception:
        return {"of_actif": None}
_OF_EXIGENCES = {
    "convention": ("organisme", "adresse", "code_postal", "ville", "siret",
                   "numero_declaration", "formateur"),
    "facture": ("organisme", "adresse", "code_postal", "ville", "siret", "format_facture"),
    "reglement": ("organisme", "iban", "bic"),
    "mail": ("marque", "signature_mail", "mail_contact"),
    "attestation": ("organisme", "numero_declaration", "formateur"),
}
_OF_NOMS = {
    "convention": "générer une convention",
    "facture": "émettre une facture",
    "reglement": "communiquer vos coordonnées bancaires",
    "mail": "envoyer un mail",
    "attestation": "délivrer une attestation",
}
def _of_garde(quoi):
    try:
        import profil as PR
    except Exception:
        return ""
    exigences = _OF_EXIGENCES.get(quoi)
    if not exigences:
        return ""
    index = {p["cle"]: p for p in PR.SCHEMA}
    manque = []
    for cle in exigences:
        if not str(PR.valeur(cle) or "").strip():
            manque.append(index.get(cle, {}).get("libelle", cle))
    if not manque:
        return ""
    return ("Impossible de " + _OF_NOMS.get(quoi, "réaliser cette action")
            + " : votre organisme n'a pas de " + ", ".join(manque[:4]).lower()
            + (" et " + str(len(manque) - 4) + " autre(s) information(s)" if len(manque) > 4 else "")
            + ". Complétez la fiche de votre organisme dans Profils OF.")
@app.route("/profil/envoi", methods=["POST"])
def profil_envoi():
    """Installe le mot de passe d'envoi de l'organisme actif.

    LE MOT DE PASSE NE VA PAS DANS LE PROFIL. Il rejoint « smtp.json », traite
    comme les identifiants Google : exclu des sauvegardes, lisible par le seul
    compte de la machine. Un profil se copie, s'exporte, se montre — pas un
    moyen d'ecrire du courrier au nom de l'organisme.
    """
    import json as _json
    import os as _os
    import stat as _stat
    import courrier as _c
    import profil as PR
    org = PR.actif()
    mot = (request.form.get("mot_de_passe") or "").replace(" ", "").strip()
    if not mot:
        return jsonify({"ok": False, "message": "Aucun mot de passe saisi."})
    fiche = PR.charger(org) or {}
    adresse = (fiche.get("mail_contact") or "").strip()
    if not adresse or "@" not in adresse:
        return jsonify({"ok": False, "message":
                        "Renseignez d'abord l'adresse de contact, dans Coordonnées : "
                        "c'est elle qui sert d'identifiant d'envoi."})
    try:
        d = {}
        if _os.path.exists(_c.FICHIER_SECRETS):
            with open(_c.FICHIER_SECRETS, encoding="utf-8") as f:
                d = _json.load(f) or {}
        # LE SERVEUR VIENT DU FORMULAIRE quand il est fourni, du fournisseur
        # devine sinon. Sans cela, une adresse chez OVH ou Gandi partirait vers
        # smtp.gmail.com et echouerait sur une authentification refusee — en
        # laissant croire que le mot de passe est faux.
        devine = _c.deviner(adresse)
        serveur = (request.form.get("serveur") or "").strip() or devine.get("serveur") \
            or _c.DEFAUTS["serveur"]
        try:
            port = int(request.form.get("port") or devine.get("port") or 587)
        except ValueError:
            port = 587
        d[org] = {"adresse": adresse, "mot_de_passe": mot,
                  "serveur": serveur, "port": port, "tls": True}
        with open(_c.FICHIER_SECRETS, "w", encoding="utf-8") as f:
            _json.dump(d, f, ensure_ascii=False, indent=2)
        _os.chmod(_c.FICHIER_SECRETS, 0o600)
    except Exception as e:
        return jsonify({"ok": False, "message": "Enregistrement impossible : " + str(e)[:140]})
    # ON ESSAIE TOUT DE SUITE. Un reglage enregistre mais non verifie donne la
    # pire des impressions : celle que tout va bien jusqu'a la premiere
    # convention qui ne part pas.
    ok, msg = _c.essai(org, adresse)
    try:
        import journal
        journal.ecrire("Envoi des mails configuré", "",
                       ("essai réussi" if ok else "essai en échec") + " · " + adresse, "", "")
    except Exception:
        pass
    return jsonify({"ok": ok, "message": msg, "installe": True})


@app.route("/profil/envoi/chercher", methods=["POST"])
def profil_envoi_chercher():
    """Cherche le serveur d'envoi tout seul, depuis le DNS du domaine.

    « Demandez a votre hebergeur son serveur SMTP » laissait l'utilisateur
    devant une question qu'il ne sait pas poser. L'information est publique :
    les enregistrements MX du domaine disent qui heberge son courrier.
    """
    import courrier as _c
    import profil as PR
    adresse = (request.form.get("adresse") or "").strip() \
        or (PR.charger() or {}).get("mail_contact") or ""
    if not adresse:
        return jsonify({"ok": False, "message": "Renseignez d'abord l'adresse de contact."})
    r = _c.chercher_serveur(adresse)
    return jsonify({"ok": bool(r.get("trouve")), "serveur": r.get("serveur", ""),
                    "port": r.get("port", 587), "hebergeur": r.get("hebergeur", ""),
                    "message": r.get("comment", "")})


@app.route("/profil/envoi/essai", methods=["POST"])
def profil_envoi_essai():
    """Renvoie un mail d'essai, sans rien reconfigurer."""
    import courrier as _c
    import profil as PR
    org = PR.actif()
    dest = (request.form.get("destinataire") or "").strip()
    ok, msg = _c.essai(org, dest)
    return jsonify({"ok": ok, "message": msg})


@app.route("/profil/envoi/retirer", methods=["POST"])
def profil_envoi_retirer():
    """Retire le mot de passe : DFM repart par le chemin de secours."""
    import json as _json
    import os as _os
    import courrier as _c
    import profil as PR
    org = PR.actif()
    try:
        d = {}
        if _os.path.exists(_c.FICHIER_SECRETS):
            with open(_c.FICHIER_SECRETS, encoding="utf-8") as f:
                d = _json.load(f) or {}
        if org in d:
            del d[org]
            with open(_c.FICHIER_SECRETS, "w", encoding="utf-8") as f:
                _json.dump(d, f, ensure_ascii=False, indent=2)
            _os.chmod(_c.FICHIER_SECRETS, 0o600)
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)[:140]})
    return jsonify({"ok": True, "message": "Mot de passe retiré. DFM repart par le chemin de secours."})


@app.route("/profil/etat")
def etat_profil():
    import profil as PR
    e = PR.pret()
    index = {p["cle"]: p for p in PR.SCHEMA}
    blocages = {}
    for quoi in _OF_EXIGENCES:
        m = _of_garde(quoi)
        if m:
            blocages[quoi] = m
    return jsonify({"ok": True, "pret": e["pret"], "manquants": e["manquants"],
                    "bloquants": e["bloquants"], "actions_bloquees": blocages})
@app.route("/synchro/etat")
def etat_synchro():
    import json as _json
    import os as _os
    chemin = _os.path.join(DOSSIER, "derniere_synchro.json")
    try:
        with open(chemin, encoding="utf-8") as f:
            d = _json.load(f)
    except Exception:
        return jsonify({"ok": True, "jamais": True})
    return jsonify({"ok": True, "jamais": False, "rapport": d})
@app.route("/synchro/relancer", methods=["POST"])
def relancer_synchro():
    import subprocess, sys
    import journal
    r = subprocess.run([sys.executable, "dfm.py"], capture_output=True,
                       text=True, cwd=DOSSIER, timeout=600)
    import json as _json, os as _os
    try:
        with open(_os.path.join(DOSSIER, "derniere_synchro.json"), encoding="utf-8") as f:
            rapport = _json.load(f)
    except Exception:
        rapport = {"ok": r.returncode == 0, "etapes": [], "echec": None}
    try:
        _journaliser_synchro(rapport)
    except Exception:
        pass
    return jsonify({"ok": True, "rapport": rapport,
                    "sortie": [l for l in r.stdout.splitlines() if l.strip()][-40:]})
# LA CHAINE CLIENT, DANS SON ORDRE REEL. La facture precede la contresignature
# parce qu'elle voyage EN PIECE JOINTE du mail de contresignature.
CHAINE_CLIENT = [
    ("Convention client", "generer_convention_client.py"),
    ("Envoi au client", "envoyer_mail_signature_client.py"),
    ("Relevé de la signature", "relever_signature_client.py"),
    ("Facture client", "generer_facture_client.py"),
    ("Contresignée + facture", "generer_convention_client_signee.py"),
    ("Attestations", "generer_attestations.py"),
]


@app.route("/session/<code>/avancer", methods=["POST"])
def session_avancer(code):
    """Fait avancer CE dossier, tout de suite.

    POURQUOI CETTE ROUTE EXISTE. La carte du parcours annoncait « a faire
    maintenant » sur une etape, et n'offrait aucun moyen de la faire : la seule
    action disponible etait « Synchroniser », qui relance le pipeline ENTIER,
    toutes sessions confondues. Entre une signature recue et la contresignature
    envoyee, il fallait donc attendre le passage de 8h30 — vingt et une heures
    dans le cas constate le 19/08/2026.

    CHAQUE ETAPE EST IDEMPOTENTE : elles refusent d'elles-memes ce qui est deja
    fait — « convention deja envoyee, rien n'est renvoye ». Relancer n'expedie
    donc jamais deux fois le meme document.
    """
    if code not in SESSIONS:
        return jsonify({"ok": False, "message": "Session inconnue."})
    import sessions as _S
    if not _S.est_client(code):
        return jsonify({"ok": False, "message":
                        "Cette action ne concerne que les sessions client."})
    # L'ETAT AVANT. Chaque etape de la chaine refuse ce qui est deja fait, donc
    # le cas le plus frequent est « rien n'a bouge » — et l'ecran annoncait
    # pourtant « Dossier avance ». On ne le devine plus : on compare la fiche
    # avant et apres. Un code de retour a zero dit que le script s'est bien
    # execute, jamais qu'il a fait quelque chose.
    _avant = dict(_S._charger_json(_S._FICHIER_S).get(code) or {})
    etapes, sortie = [], []
    for titre, script in CHAINE_CLIENT:
        try:
            r = subprocess.run([sys.executable, script, code], capture_output=True,
                               text=True, cwd=DOSSIER, timeout=300)
        except subprocess.TimeoutExpired:
            etapes.append({"titre": titre, "ok": False, "resume": "n'a pas rendu la main"})
            sortie.append("[%s] interrompu apres 5 minutes." % titre)
            break
        lignes = [l.rstrip() for l in r.stdout.splitlines() if l.strip()]
        etapes.append({"titre": titre, "ok": r.returncode == 0,
                       "resume": (lignes[-1][:120] if lignes else "")})
        sortie.append("── %s" % titre)
        sortie.extend(lignes[-8:])
    _apres = dict(_S._charger_json(_S._FICHIER_S).get(code) or {})
    return jsonify({"ok": all(e["ok"] for e in etapes), "etapes": etapes,
                    "change": _avant != _apres, "sortie": sortie[-60:]})


@app.route("/planificateur/etat")
def planificateur_etat():
    """Le planificateur est-il vivant, et qu'a-t-il fait ?

    SUR UN SERVEUR, ON NE VOIT PAS LE TERMINAL. Un fil d'execution mort ne
    previent personne : le guet des signatures s'arreterait et les dossiers
    stagneraient sans qu'aucun ecran ne le dise. Cette route repond a la seule
    question qui compte — tourne-t-il encore ?
    """
    try:
        import planificateur as _p
        return jsonify({"ok": True, "actif": _p.actif(),
                        "guet_minutes": _p.GUETTEUR_SECONDES // 60,
                        "passages": ["%dh%02d" % h for h in _p.PASSAGE_HEURES],
                        "sauvegarde": "%dh%02d" % _p.SAUVEGARDE_HEURE,
                        "journal": _p.journal()[:40]})
    except Exception as e:
        return jsonify({"ok": False, "actif": False, "message": str(e)[:200]})


@app.route("/lancer", methods=["POST"])
def lancer():
    # Delai de garde, comme /synchro/relancer. Sans lui, un dfm.py bloque fige
    # la requete et son thread Flask jusqu'au redemarrage du serveur.
    try:
        r = subprocess.run([sys.executable, "dfm.py"], capture_output=True,
                           text=True, cwd=DOSSIER, timeout=900)
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "delai": True,
                        "sortie": ["Le traitement n'a pas rendu la main en 15 minutes.",
                                   "Il a ete interrompu. Verifiez la connexion Google :",
                                   "un jeton expire ouvre une demande d'autorisation qui attend."]})
    lignes = [l for l in r.stdout.splitlines() if l.strip()]
    return jsonify({"ok": r.returncode == 0, "sortie": lignes[-40:]})
# ==========================================================================
# ACCES — qui a le droit d'ouvrir DFM
#
# Jusqu'au 05/08/2026, les 151 routes etaient ouvertes a quiconque atteignait
# l'adresse. Sans consequence sur une machine personnelle ; catastrophique des
# la premiere publication.
#
# TANT QU'AUCUN MOT DE PASSE N'EST DEFINI, rien ne change : DFM s'ouvre comme
# avant. La protection s'active avec `python3 mot_de_passe.py`.
# ==========================================================================
import acces as _acces

app.secret_key = _acces.secret()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,      # inaccessible au JavaScript
    SESSION_COOKIE_SAMESITE="Strict",  # jamais envoye depuis un autre site
    PERMANENT_SESSION_LIFETIME=_acces.duree(),
    # EN LIGNE, LE COOKIE NE VOYAGE QU'EN HTTPS. Pas sur le Mac : en local DFM
    # parle http, et un cookie « Secure » n'y serait jamais enregistre — la
    # page de connexion tournerait en boucle sans jamais s'ouvrir. C'est le
    # service systemd qui pose la variable, la ou le HTTPS existe.
    SESSION_COOKIE_SECURE=(os.environ.get("DFM_PROXY") or "").strip().lower()
                           in ("1", "oui", "true"),
)

# UNE SEULE CONNEXION POUR PLUSIEURS OUTILS SUR LE MEME DOMAINE.
#
# Pose DFM_COOKIE_DOMAINE=".exemple.fr" et le cookie de session voyage vers tous
# les sous-domaines : on se connecte une fois, on passe de « dfm.exemple.fr » a
# « opco.exemple.fr » sans redonner le mot de passe. Les deux applications lisent
# le meme acces.json — donc la meme empreinte et le meme secret de signature — et
# aucune n'a besoin de connaitre l'autre.
#
# VIDE PAR DEFAUT, ET C'EST VOULU : sans cette variable, le cookie reste attache
# au seul hote qui l'a pose, exactement comme avant. Un reglage d'hebergement ne
# doit rien changer pour qui ne l'emploie pas — le Mac en premier.
#
# SameSite=Strict n'y fait pas obstacle : deux sous-domaines d'un meme domaine
# enregistrable sont « same-site », le cookie voyage donc entre eux.
_cookie_dom = (os.environ.get("DFM_COOKIE_DOMAINE") or "").strip()
if _cookie_dom:
    app.config["SESSION_COOKIE_DOMAIN"] = _cookie_dom

# Les seules adresses joignables sans etre connecte.
_LIBRES = {"/connexion", "/favicon.ico"}


@app.before_request
def _garde():
    # 1. CSRF — une requete qui MODIFIE doit venir de DFM lui-meme.
    #
    # On verifie l'origine plutot que de poser un jeton dans chacun des 86
    # formulaires : le cookie est deja en SameSite=Strict, l'origine est le
    # second verrou, et aucune page existante n'a besoin d'etre touchee. Une
    # modification oubliee serait une faille ; ici il n'y a rien a oublier.
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origine = request.headers.get("Origin") or request.headers.get("Referer") or ""
        if origine:
            from urllib.parse import urlparse
            venue = urlparse(origine).netloc
            if venue and venue != request.host:
                return jsonify({"ok": False, "message":
                                "Requête refusée : elle ne vient pas de DFM."}), 403

    # 2. PUBLIE SANS MOT DE PASSE : DFM REFUSE DE REPONDRE.
    #
    # POURQUOI ICI, ET PAS SEULEMENT AU DEMARRAGE. Le garde-fou de servir.py
    # regarde DFM_HOTE. Or l'hebergement recommande laisse DFM sur 127.0.0.1
    # et met nginx devant : le garde-fou voit une machine locale et laisse
    # passer, pendant que nginx publie tout. Constate le 19/08/2026 en
    # preparant le serveur.
    #
    # ON REGARDE L'ADRESSE DEMANDEE, PAS LES EN-TETES DU MANDATAIRE.
    # Premiere version : on cherchait X-Forwarded-For. Essai du 19/08/2026 a
    # travers le reseau — la requete passait quand meme. Waitress EFFACE tous
    # les X-Forwarded-* tant qu'aucun mandataire n'est declare de confiance
    # (clear_untrusted_proxy_headers vaut True depuis la version 2). Le garde
    # ne voyait donc jamais rien et n'aurait jamais rien protege. Un essai en
    # memoire, lui, repondait 503 : il ne passait pas par waitress. C'est
    # l'essai par le reseau qui a montre la verite.
    #
    # LE NOM D'HOTE, LUI, ARRIVE TOUJOURS : nginx transmet « Host », et c'est
    # precisement ce qui distingue « je travaille sur ma machine » de « on
    # m'atteint par un domaine ». On repond alors la meme chose a tout le
    # monde — au visiteur comme au proprietaire, car c'est lui qui doit poser
    # le mot de passe.
    if not _acces.protege():
        _h = (request.host or "").lower()
        _h = _h[1:].split("]")[0] if _h.startswith("[") else _h.split(":")[0]
        if (_h not in ("127.0.0.1", "localhost", "::1", "")
                or request.headers.get("X-Forwarded-For")
                or request.headers.get("X-Forwarded-Proto")
                or (os.environ.get("DFM_PROXY") or "").strip().lower() in ("1", "oui", "true")):
            return ("<!doctype html><meta charset=utf-8>"
                    "<title>DFM — non configuré</title>"
                    "<body style=\"font:16px/1.6 system-ui;max-width:34em;margin:6em auto;padding:0 1.5em\">"
                    "<h1 style=\"font-size:1.4em\">DFM ne peut pas s'ouvrir</h1>"
                    "<p>Il est publié sur internet alors qu'aucun mot de passe "
                    "n'est posé. Il ne répondra pas tant que "
                    "<code>python3 mot_de_passe.py</code> n'aura pas été lancé "
                    "sur le serveur.</p>"
                    "<p style=\"color:#666\">Ce message protège vos contacts, vos "
                    "conventions signées et vos factures.</p>"), 503
        return None
    if request.path in _LIBRES or request.path.startswith("/static/"):
        return None
    if _session.get("ouvert"):
        return None
    # Une requete de fond doit recevoir un refus lisible, pas une page HTML :
    # sans cela l'ecran affiche « erreur inattendue » au lieu de « reconnectez-vous ».
    if request.headers.get("X-Requested-With") or request.method != "GET":
        return jsonify({"ok": False, "message": "Session expirée. Rechargez la page."}), 401
    return redirect("/connexion?suite=" + request.path)


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    suite = (request.values.get("suite") or "/").strip()
    if not suite.startswith("/") or suite.startswith("//"):
        suite = "/"          # jamais de redirection vers un autre site
    if not _acces.protege():
        return redirect(suite)
    if request.method == "POST":
        if _acces.verifier(request.form.get("mot_de_passe") or ""):
            _session.permanent = True
            _session["ouvert"] = True
            try:
                import journal
                journal.ecrire("Connexion à DFM", "", "", "", "")
            except Exception:
                pass
            return redirect(suite)
        return render_template("connexion.html", suite=suite,
                               souci="Mot de passe incorrect."), 401
    return render_template("connexion.html", suite=suite, souci="")


@app.route("/deconnexion")
def deconnexion():
    _session.clear()
    return redirect("/connexion")


if __name__ == "__main__":
    # LE MODE DEBUG N'EST PLUS ACTIF PAR DEFAUT. Le debogueur de Werkzeug
    # s'ouvre a la moindre exception et permet d'executer du code Python depuis
    # le navigateur : publie en l'etat, une simple adresse malformee donnait la
    # main sur la machine, donc sur credentials.json et le Drive entier.
    #
    # Pour le retrouver pendant un developpement : DFM_DEBUG=1 python3 app.py
    _debug = os.environ.get("DFM_DEBUG") == "1"
    _hote = os.environ.get("DFM_HOTE") or "127.0.0.1"
    print("\n  DFM demarre sur http://%s:5001" % _hote)
    if _debug:
        print("  MODE DEBUG ACTIF — ne jamais publier ainsi.")
    if not _acces.protege():
        print("  Aucun mot de passe : DFM s'ouvre sans rien demander.")
        print("  Avant toute publication : python3 mot_de_passe.py")
    # LE PLANIFICATEUR VIT DANS DFM, plus dans macOS. Un fil demon : il meurt
    # avec le serveur, aucun processus orphelin ne survit. Voir planificateur.py.
    #
    # DEMARRE ICI ET PAS AU CHARGEMENT DU MODULE : app.py est importe par les
    # scripts de controle et par le pipeline lui-meme. Un planificateur lance a
    # l'import se serait mis en marche depuis un script en ligne de commande,
    # puis serait mort avec lui — ou pire, aurait relance le pipeline depuis le
    # pipeline.
    try:
        import planificateur as _plan
        if _plan.demarrer():
            print("  Planificateur actif : guet des signatures toutes les %d min,"
                  % (_plan.GUETTEUR_SECONDES // 60))
            print("  passage complet a %s."
                  % " et ".join("%dh%02d" % h for h in _plan.PASSAGE_HEURES))
    except Exception as _e:
        print("  Planificateur non demarre : %s" % str(_e)[:120])
    print("  Ctrl+C pour arreter\n")
    app.run(debug=_debug, port=5001, host=_hote)
