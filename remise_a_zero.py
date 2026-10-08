"""Remise a zero de DFM : effacer les donnees de test, garder le travail.

SIMULATION PAR DEFAUT. Sans argument, ce script n'ecrit RIEN : il affiche
exactement ce qu'il effacerait, ou, et combien. Il faut l'argument explicite
--executer pour qu'il agisse.

    python3 remise_a_zero.py              # simulation, aucune ecriture
    python3 remise_a_zero.py --executer   # execution reelle, apres confirmation

Ce qui est CONSERVE dans tous les cas :
    parametres.json, profils/, bibliotheque.json, mails.json,
    credentials.json, token.json, les sauvegardes .avant-*,
    formateurs.json et les dossiers des formateurs,
    les pieces que vous avez deposees — programmes, plans d'acces, RIB,
    reglements interieurs, CV, diplomes,
    la table Supabase « Organismes_publics »,
    les dossiers Drive Templates / Documents d'envoi / envoi J-20,
    la structure des onglets et des tables.

MIS A JOUR LE 19/08/2026. Il ignorait trois choses qui n'existaient pas quand il
a ete ecrit : la base locale dfm.db — devenue l'autorite le 17/08 —, les
documents produits sur le disque depuis la migration hors Google, et les tables
du formulaire d'inscription maison. Le lancer avant cette mise a jour aurait
vide les classeurs Google en laissant la base pleine.
"""
import sys
import os
import json
import re

DOSSIER = os.path.dirname(os.path.abspath(__file__))
EXECUTER = "--executer" in sys.argv[1:]

# Modeles conserves PAR DEFAUT : choix de l'utilisateur du 02/08/2026. Ce sont
# ses questionnaires — du vrai travail, qu'il rattachera aux formations
# recreees. Les mettre en dur ici plutot qu'en option evite qu'un oubli
# d'argument les emporte.
GARDER_DEFAUT = [
    "trame-type",                              # satisfaction, unique modele
    "usures",                                  # evaluation
    "evaluation-des-connaissances-masterclass",  # evaluation
]
GARDER_MODELES = list(GARDER_DEFAUT)
GARDER_MODELES += [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--garder-modele=")]
# Retrait explicite d'un modele du filet, si l'utilisateur le decide un jour.
for _a in sys.argv[1:]:
    if _a.startswith("--supprimer-modele="):
        _c = _a.split("=", 1)[1]
        if _c in GARDER_MODELES:
            GARDER_MODELES.remove(_c)

# --------------------------------------------------------------------------
# Presentation
# --------------------------------------------------------------------------
_actions = []


def prevu(zone, quoi, detail="", danger=False):
    _actions.append({"zone": zone, "quoi": quoi, "detail": detail, "danger": danger})
    marque = "  !!" if danger else "   ."
    print(f"{marque} [{zone}] {quoi}" + (f"  — {detail}" if detail else ""))


def titre(t):
    print()
    print("=" * 74)
    print("  " + t)
    print("=" * 74)


# --------------------------------------------------------------------------
titre("REMISE A ZERO DE DFM" + ("  —  EXECUTION REELLE" if EXECUTER else "  —  SIMULATION"))
if not EXECUTER:
    print("  Aucune ecriture ne sera faite. Ce qui suit est ce qui SERAIT efface.")
else:
    print("  ATTENTION : ce passage ECRIT reellement.")

# --------------------------------------------------------------------------
titre("1. CODE — les fiches ecrites en dur dans sessions.py")
# Vider les JSON ne suffit pas : usures et usures-nov26 sont des litteraux du
# module, ils reapparaitraient au redemarrage.
src = open(os.path.join(DOSSIER, "sessions.py"), encoding="utf-8").read()
import ast

_arbre = ast.parse(src)
for _n in _arbre.body:
    if isinstance(_n, ast.Assign) and getattr(_n.targets[0], "id", "") in ("FORMATIONS", "SESSIONS"):
        _d = ast.literal_eval(_n.value)
        for _c in _d:
            prevu("sessions.py", f"{_n.targets[0].id}['{_c}'] retire du litteral",
                  "sinon reapparait au redemarrage", danger=True)
if "SESSION_ACTIVE" in src:
    _m = re.search(r'SESSION_ACTIVE\s*=\s*"([^"]*)"', src)
    prevu("sessions.py", "SESSION_ACTIVE vide", f"actuellement {_m.group(1) if _m else '?'}", danger=True)

# --------------------------------------------------------------------------
titre("2. FICHIERS LOCAUX")
A_VIDER = {
    "formations.json": "toutes les fiches formation",
    "sessions.json": "toutes les sessions",
    "questionnaires_etat.json": "etat d'ouverture des questionnaires",
    "derniere_synchro.json": "dernier rapport de synchronisation",
    # Ajoute le 04/08/2026 avec le registre lui-meme. Sans cela, la
    # numerotation ne repartirait PAS a 001 : elle se calcule desormais sur le
    # maximum du registre ET des PDF du Drive, pas sur les seuls noms de
    # fichiers. Un registre laisse en place ferait demarrer la nouvelle
    # comptabilite a F2026-012.
    "factures.json": "REGISTRE DES FACTURES — pieces comptables",
    # Meme raison, ajoute le 06/08/2026 avec le modele unique d'attestation :
    # le numero AT2026-xxx est attribue une fois et conserve dans ce registre.
    # Laisse en place, il ferait redemarrer la numerotation la ou elle s'etait
    # arretee, sur des sessions qui n'existent plus.
    "attestations.json": "REGISTRE DES ATTESTATIONS — numeros AT2026-xxx",
}
for f, quoi in A_VIDER.items():
    p = os.path.join(DOSSIER, f)
    if not os.path.exists(p):
        continue
    try:
        n = len(json.load(open(p, encoding="utf-8")))
    except Exception:
        n = "?"
    prevu("local", f"{f} vide", f"{quoi} ({n} entree(s))")

_fig = os.path.join(DOSSIER, "questionnaires_figes")
if os.path.isdir(_fig):
    _k = [x for x in os.listdir(_fig) if x.endswith(".json")]
    if _k:
        prevu("local", f"questionnaires_figes/ vide", f"{len(_k)} instantane(s) de session")

# --------------------------------------------------------------------------
# LA BASE LOCALE. Ajoutee le 19/08/2026, avec un an de retard sur elle-meme :
# dfm.db fait autorite depuis le 17/08 — journal, etat des sessions, suivi des
# inscrits. Le script vidait deja l'onglet Journal DU CLASSEUR GOOGLE, qui n'en
# est que le miroir. Laisser l'original plein aurait produit le pire resultat
# possible : DFM affichant encore tous vos inscrits face a des classeurs vides,
# sans qu'aucun message ne dise lequel des deux a raison.
titre("2b. BASE LOCALE — dfm.db")
_BASE_A_VIDER = {
    "journal": "la piste d'audit scellee",
    "session_etat": "l'avancement de chaque session",
    "suivi": "les inscrits",
}
try:
    import sqlite3 as _sq
    _cx = _sq.connect(os.path.join(DOSSIER, "dfm.db"))
    for _t, _quoi in _BASE_A_VIDER.items():
        try:
            _n = _cx.execute("SELECT COUNT(*) FROM %s" % _t).fetchone()[0]
        except Exception:
            continue
        prevu("base", f"table « {_t} » videe", f"{_quoi} ({_n} ligne(s))", danger=True)
    _cx.close()
except Exception as _e:
    print("   base illisible :", str(_e)[:90])

# --------------------------------------------------------------------------
# LES DOCUMENTS PRODUITS EN LOCAL. Ajoutes le 19/08/2026 : depuis la migration
# hors Google, conventions, factures, attestations et emargements sont ECRITS
# ICI, le Drive n'en gardant qu'une copie d'archive. Vider le Drive sans vider
# le disque laisserait les documents des sessions effacees.
#
# ON NE TOUCHE PAS AUX PIECES QUE VOUS AVEZ DEPOSEES. Programmes, plans d'acces,
# RIB, reglements interieurs, CV et diplomes des formateurs sont du travail, pas
# des donnees de test — meme raison que les modeles.
titre("2c. DOCUMENTS PRODUITS — sur le disque")
_DOCS = os.path.join(DOSSIER, "documents")
_GARDES_DOCS = ("_pieces", "_formateurs", "_formations", "_vignettes", "_corbeille")
if os.path.isdir(_DOCS):
    for _d in sorted(os.listdir(_DOCS)):
        _pd = os.path.join(_DOCS, _d)
        if not os.path.isdir(_pd) or _d in _GARDES_DOCS:
            continue
        for _sess in sorted(os.listdir(_pd)):
            _ps = os.path.join(_pd, _sess)
            if not os.path.isdir(_ps):
                continue
            _n = sum(len(fs) for _r, _ds, fs in os.walk(_ps))
            if _n:
                prevu("documents", f"[{_d}] {_sess} mis de cote",
                      f"{_n} document(s) — deplace dans documents/_corbeille")
    print()
    print("   CONSERVES : les pieces que vous avez deposees —")
    print("               programmes, plans d'acces, RIB, reglements interieurs,")
    print("               CV, diplomes et photos des formateurs.")

print()
print("  CONSERVES : parametres.json, profils/, bibliotheque.json, mails.json,")
print("              credentials.json, token.json, toutes les sauvegardes .avant-*")

# --------------------------------------------------------------------------
titre("3. MODELES — a cocher, rien n'est supprime sans votre choix")
try:
    import modeles as _mod
    import mails as _mails
    from sessions import FORMATIONS as _F

    _lignes = []
    for _t in ("evaluation", "satisfaction", "froid"):
        for _m in _mod.lister(_t):
            _lie = _mod.utilise_par(_t, _m["id"])
            _lignes.append((_t, _m["id"], _m.get("titre") or _m["id"], _lie))
    for _id, _f in (_mails.charger() or {}).items():
        _lignes.append(("mail", _id, _f.get("titre") or _id, []))
    if not _lignes:
        print("   aucun modele personnel")
    for _t, _id, _titre, _lie in _lignes:
        _garde = _id in GARDER_MODELES
        _note = ""
        if _lie:
            _note = "lie a " + ", ".join(_lie) + " — formation(s) qui disparaissent"
        if re.search(r"test|essai", _titre, re.I):
            _note = (_note + " · " if _note else "") + "le titre evoque un essai"
        etat = "GARDE" if _garde else "supprime"
        print(f"   [{'x' if _garde else ' '}] {_t:<13} {_id[:38]:<38} {etat}")
        print(f"        « {_titre[:56]} »" + (f"  — {_note}" if _note else ""))
    print()
    print("   Pour en conserver un : --garder-modele=<identifiant>, repetable.")
    print("   Les trames fournies avec DFM ne sont jamais touchees.")
except Exception as _e:
    print("   inventaire indisponible :", str(_e)[:90])

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# LES DEUX ORGANISMES, pas seulement l'actif.
#
# DEFAUT CORRIGE LE 04/08/2026. Ce script lisait « la » feuille de suivi et
# « les » dossiers du profil actif. Depuis le cloisonnement, il en existe DEUX
# jeux : lance sous Smileclub, il effacait Smileclub en annoncant tout effacer,
# et laissait DSF intact — sans le moindre message. Sur un outil dont c'est le
# role de tout effacer, une moitie oubliee est pire qu'un echec franc.
def _tous_les_organismes():
    """Rend [(identifiant, fiche)] pour chaque profil connu, l'actif compris."""
    try:
        import profil as _pr
        sortie = []
        for _p in _pr.lister():
            _ident = _p["id"] if isinstance(_p, dict) else _p
            _f = _pr.charger(_ident) or {}
            if _f:
                sortie.append((_ident, _f))
        return sortie
    except Exception:
        return []


def _classeurs_de_suivi():
    """Les feuilles de suivi DISTINCTES. Deux organismes peuvent partager la
    meme : on ne la traite alors qu'une fois."""
    vues, sortie = set(), []
    for ident, f in _tous_les_organismes():
        cle = (f.get("sheet_suivi") or "").strip()
        if cle and cle not in vues:
            vues.add(cle)
            sortie.append((ident, cle))
    return sortie


def _dossiers_a_vider():
    """Les dossiers de production, par IDENTIFIANT et non par nom.

    L'ancienne version cherchait des noms en dur, dont « Emargements » au
    pluriel alors que vos dossiers s'appellent « Emargement » : les feuilles
    signees n'etaient donc jamais nettoyees. Les identifiants viennent de la
    fiche de chaque organisme, comme partout ailleurs depuis dossiers.py.
    """
    vues, sortie = set(), []
    for ident, f in _tous_les_organismes():
        for cle in ("dossier_conventions", "dossier_signees", "dossier_factures",
                    "dossier_attestations", "dossier_emargement"):
            fid = (f.get(cle) or "").strip()
            if fid and fid not in vues:
                vues.add(fid)
                sortie.append((ident, cle.replace("dossier_", ""), fid))
    return sortie


# --------------------------------------------------------------------------
titre("4. GOOGLE SHEETS")
try:
    from connexion import service_sheets
    import sessions as _s
    import journal as _j

    _sh = service_sheets()
    _onglets_session = {(_s.SESSIONS[c].get("onglet_suivi") or "") for c in _s.SESSIONS}
    _classeurs = _classeurs_de_suivi()
    if not _classeurs:
        print("   AUCUN classeur trouve : verifiez les fiches d'organisme.")
    for _ident, _feuille in _classeurs:
        _meta = _sh.spreadsheets().get(spreadsheetId=_feuille).execute()
        print(f"   --- organisme « {_ident} » : {_meta['properties']['title']}")
        for _x in _meta["sheets"]:
            _t = _x["properties"]["title"]
            if _t in _onglets_session or _t.startswith("ZZ-supprimee-"):
                _v = _sh.spreadsheets().values().get(
                    spreadsheetId=_feuille, range=f"'{_t}'!A2:A1000").execute().get("values", [])
                prevu("Sheets", f"[{_ident}] onglet « {_t} » supprime",
                      f"{len([r for r in _v if r])} inscrit(s)", danger=True)
            elif _t == _j.ONGLET:
                _v = _sh.spreadsheets().values().get(
                    spreadsheetId=_feuille, range=f"'{_t}'!A2:A5000").execute().get("values", [])
                prevu("Sheets", f"[{_ident}] onglet « {_t} » vide (en-tetes gardes)",
                      f"{len([r for r in _v if r])} entree(s)")
            elif _t == "Sessions":
                _v = _sh.spreadsheets().values().get(
                    spreadsheetId=_feuille, range=f"'{_t}'!A2:A200").execute().get("values", [])
                prevu("Sheets", f"[{_ident}] onglet « {_t} » vide (en-tetes gardes)",
                      f"{len([r for r in _v if r])} ligne(s)")
            else:
                print(f"      (conserve : [{_ident}] onglet « {_t} »)")
except Exception as _e:
    print("   inventaire indisponible :", str(_e)[:90])

# --------------------------------------------------------------------------
titre("5. GOOGLE DRIVE — mise a la CORBEILLE, jamais suppression definitive")
try:
    from connexion import service_drive

    _dr = service_drive()

    def _dossier(nom):
        q = ("name='" + nom.replace("'", "\\'") + "' and "
             "mimeType='application/vnd.google-apps.folder' and trashed=false")
        return _dr.files().list(q=q, fields="files(id,name)").execute().get("files", [])

    def _enfants(pid):
        return _dr.files().list(q=f"'{pid}' in parents and trashed=false",
                                fields="files(id,name,mimeType)", pageSize=300).execute().get("files", [])

    _cibles_drive = _dossiers_a_vider()
    if not _cibles_drive:
        print("   AUCUN dossier trouve : verifiez les fiches d'organisme.")
    for _ident, _quoi, _fid in _cibles_drive:
        try:
            _nomd = _dr.files().get(fileId=_fid, fields="name").execute()["name"]
        except Exception:
            print(f"      ([{_ident}] {_quoi} : dossier introuvable, ignore)")
            continue
        for _e in _enfants(_fid):
            if _e["mimeType"].endswith("folder"):
                _k = _enfants(_e["id"])
                prevu("Drive", f"[{_ident}] {_nomd}/{_e['name']} a la corbeille",
                      f"{len(_k)} fichier(s)", danger=True)
            else:
                prevu("Drive", f"[{_ident}] {_nomd}/{_e['name']} a la corbeille", "", danger=True)
    print()
    print("   CONSERVES : Templates, Documents d'envoi, envoi J-20, logos, RIB")
    print("   La numerotation des factures repart a 001 quand les PDF quittent le")
    print("   Drive ET que factures.json est vide : elle se calcule sur le maximum")
    print("   des deux. Le registre est bien dans la liste des fichiers locaux.")
except Exception as _e:
    print("   inventaire indisponible :", str(_e)[:90])

# --------------------------------------------------------------------------
titre("6. SUPABASE")
try:
    import config
    from supabase import create_client

    _sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    # « Organismes_publics » N'EST PAS DE LA PARTIE : cette table porte
    # l'identite de vos organismes sur la page publique d'inscription — nom,
    # couleur, accroche, contact. C'est du meme ordre que profils/, qu'on
    # conserve. La vider rendrait le formulaire anonyme jusqu'a republication.
    for _t in ("Signatures", "Annulations", "Questionnaires", "Sessions_publiques",
               "Inscriptions", "Sessions_inscription"):
        try:
            _r = _sb.table(_t).select("*").execute()
            if _r.data:
                prevu("Supabase", f"table {_t} videe", f"{len(_r.data)} ligne(s)", danger=True)
            else:
                print(f"      (deja vide : {_t})")
        except Exception as _e:
            print(f"      ({_t} : {str(_e)[:60]})")
except Exception as _e:
    print("   inventaire indisponible :", str(_e)[:90])

# --------------------------------------------------------------------------
titre("RECAPITULATIF")
_dang = [a for a in _actions if a["danger"]]
print(f"  {len(_actions)} operation(s) prevue(s), dont {len(_dang)} irreversible(s) hors corbeille.")
print()
if not EXECUTER:
    print("  SIMULATION — rien n'a ete touche.")
    print()
    print("  Pour executer, les TROIS preuves suivantes sont exigees :")
    print("    --sauvegarde=<dossier>   copie complete du dossier DFM")
    print("    --export=<fichier.xlsx>  export du classeur Google Sheets")
    print("    --modeles-relus          vous avez relu la liste ci-dessus")
    print()
    print("  Exemple :")
    print("    python3 remise_a_zero.py --executer \\")
    print("      --sauvegarde=~/Desktop/DFM-avant-remise-a-zero \\")
    print("      --export=~/Desktop/DFM-classeur.xlsx --modeles-relus")
    sys.exit(0)


# ==========================================================================
# EXECUTION — trois preuves verifiees, pas declarees
# ==========================================================================
def _arg(prefixe):
    for a in sys.argv[1:]:
        if a.startswith(prefixe):
            return os.path.expanduser(a.split("=", 1)[1].strip())
    return ""


titre("PREALABLES — verifies, non declaratifs")
_soucis = []

# 1. copie du dossier : doit exister, et contenir ce qui n'est pas regenerable
_sauv = _arg("--sauvegarde=")
if not _sauv:
    _soucis.append("--sauvegarde=<dossier> manquant")
elif not os.path.isdir(_sauv):
    _soucis.append(f"le dossier de sauvegarde n'existe pas : {_sauv}")
else:
    _manque = [x for x in ("app.py", "credentials.json", "token.json", "formations.json")
               if not os.path.exists(os.path.join(_sauv, x))]
    if _manque:
        _soucis.append("sauvegarde incomplete, il manque : " + ", ".join(_manque))
    else:
        _a_jour = os.path.getmtime(os.path.join(_sauv, "formations.json")) >= \
                  os.path.getmtime(os.path.join(DOSSIER, "formations.json"))
        if not _a_jour:
            _soucis.append("la sauvegarde est plus ancienne que les donnees actuelles")
        else:
            print(f"   OK  copie du dossier : {_sauv}")

# 2. export du classeur : doit exister, etre non vide, et etre un vrai xlsx
_exp = _arg("--export=")
if not _exp:
    _soucis.append("--export=<fichier.xlsx> manquant")
elif not os.path.isfile(_exp):
    _soucis.append(f"l'export du classeur n'existe pas : {_exp}")
elif os.path.getsize(_exp) < 4096:
    _soucis.append(f"l'export du classeur parait vide ({os.path.getsize(_exp)} octets)")
else:
    with open(_exp, "rb") as _fh:
        _magique = _fh.read(2)
    if _magique != b"PK":
        _soucis.append("l'export n'est pas un fichier .xlsx valide")
    else:
        print(f"   OK  export du classeur : {_exp}  ({os.path.getsize(_exp)//1024} Ko)")

# 3. relecture des modeles : declaration explicite
if "--modeles-relus" not in sys.argv[1:]:
    _soucis.append("--modeles-relus manquant (relisez la section 3 ci-dessus)")
else:
    print(f"   OK  modeles relus — {len(GARDER_MODELES)} conserve(s) : "
          + ", ".join(GARDER_MODELES))

if _soucis:
    print()
    print("  EXECUTION REFUSEE — " + str(len(_soucis)) + " prealable(s) non satisfait(s) :")
    for _x in _soucis:
        print("     . " + _x)
    print()
    print("  Rien n'a ete touche.")
    sys.exit(1)

print()
print("  Pour confirmer, recopiez exactement :  REMISE A ZERO")
try:
    if input("  > ").strip() != "REMISE A ZERO":
        print("  Confirmation incorrecte. Rien n'a ete touche.")
        sys.exit(1)
except (EOFError, KeyboardInterrupt):
    print()
    print("  Interrompu. Rien n'a ete touche.")
    sys.exit(1)

# --------------------------------------------------------------------------
_faits, _echecs = [], []


def faire(quoi, fn):
    """Chaque operation est isolee : un echec n'arrete pas les suivantes, il est
    consigne. Une remise a zero a moitie faite doit etre lisible."""
    try:
        fn()
        _faits.append(quoi)
        print(f"   OK  {quoi}")
    except Exception as e:
        _echecs.append((quoi, str(e)[:150]))
        print(f"   ECHEC  {quoi} : {str(e)[:110]}")


# --- 1. code -------------------------------------------------------------
titre("EXECUTION 1/7 — sessions.py")


def _vider_litteraux():
    import shutil
    p = os.path.join(DOSSIER, "sessions.py")
    shutil.copy2(p, p + ".avant-REMISE")
    s = open(p, encoding="utf-8").read()
    a = ast.parse(s)
    lignes = s.split("\n")
    remplacements = []
    for n in a.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("FORMATIONS", "SESSIONS"):
            remplacements.append((n.lineno, n.end_lineno, n.targets[0].id))
    for deb, fin, nom in sorted(remplacements, reverse=True):
        lignes[deb - 1:fin] = [nom + " = {}"]
    s = "\n".join(lignes)
    s = re.sub(r'SESSION_ACTIVE\s*=\s*"[^"]*"', 'SESSION_ACTIVE = ""', s)
    open(p, "w", encoding="utf-8").write(s)
    import py_compile as _pc
    _pc.compile(p, doraise=True)


faire("sessions.py : FORMATIONS, SESSIONS et SESSION_ACTIVE vides", _vider_litteraux)

# --- 2. fichiers locaux --------------------------------------------------
titre("EXECUTION 2/7 — fichiers locaux")
for _f in A_VIDER:
    _p = os.path.join(DOSSIER, _f)
    if os.path.exists(_p):
        faire(f"{_f} vide",
              (lambda p=_p: open(p, "w", encoding="utf-8").write("{}\n")))
if os.path.isdir(_fig):
    for _k in [x for x in os.listdir(_fig) if x.endswith(".json")]:
        faire(f"questionnaires_figes/{_k} supprime",
              (lambda k=_k: os.remove(os.path.join(_fig, k))))

# --- 3. modeles ----------------------------------------------------------
titre("EXECUTION 3/7 — modeles non conserves")
try:
    import modeles as _mod2
    import mails as _mails2
    for _t in ("evaluation", "satisfaction", "froid"):
        for _m in list(_mod2.lister(_t)):
            if _m["id"] not in GARDER_MODELES:
                faire(f"modele {_t} « {_m.get('titre') or _m['id']} » supprime",
                      (lambda t=_t, i=_m["id"]: _mod2.supprimer(t, i)))
    for _id in list((_mails2.charger() or {})):
        if _id not in GARDER_MODELES:
            faire(f"modele mail {_id} supprime",
                  (lambda i=_id: _mails2.supprimer(i)))
except Exception as _e:
    _echecs.append(("modeles", str(_e)[:150]))

# --- 4. Sheets -----------------------------------------------------------
titre("EXECUTION 4/7 — Google Sheets")
try:
    from connexion import service_sheets as _ss
    import sessions as _s2
    import journal as _j2
    _sh2 = _ss()
    _cibles = {(_s2.SESSIONS[c].get("onglet_suivi") or "") for c in _s2.SESSIONS}
    # TOUS les classeurs, un par organisme. Voir _classeurs_de_suivi().
    for _ident2, _feuille in _classeurs_de_suivi():
        _meta2 = _sh2.spreadsheets().get(spreadsheetId=_feuille).execute()
        for _x in _meta2["sheets"]:
            _p2 = _x["properties"]
            _t2, _id2 = _p2["title"], _p2["sheetId"]
            if _t2 in _cibles or _t2.startswith("ZZ-supprimee-"):
                faire(f"[{_ident2}] onglet « {_t2} » supprime",
                      (lambda i=_id2, f=_feuille: _sh2.spreadsheets().batchUpdate(
                          spreadsheetId=f,
                          body={"requests": [{"deleteSheet": {"sheetId": i}}]}).execute()))
            elif _t2 in (_j2.ONGLET, "Sessions"):
                faire(f"[{_ident2}] onglet « {_t2} » vide, en-tetes gardes",
                      (lambda t=_t2, f=_feuille: _sh2.spreadsheets().values().clear(
                          spreadsheetId=f, range=f"'{t}'!A2:Z10000", body={}).execute()))
except Exception as _e:
    _echecs.append(("Sheets", str(_e)[:150]))

# --- 5. Drive ------------------------------------------------------------
titre("EXECUTION 5/7 — Google Drive (corbeille)")
try:
    from connexion import service_drive as _sd
    _dr2 = _sd()

    # Par IDENTIFIANT, organisme par organisme. La recherche par nom manquait
    # « Emargement » (ecrit au pluriel dans l'ancienne liste) et ne distinguait
    # pas les deux jeux de dossiers. Voir _dossiers_a_vider().
    for _ident3, _quoi3, _fid3 in _dossiers_a_vider():
        try:
            _nomd3 = _dr2.files().get(fileId=_fid3, fields="name").execute()["name"]
        except Exception:
            _echecs.append(("Drive", f"[{_ident3}] {_quoi3} : dossier introuvable"))
            continue
        _enf = _dr2.files().list(q=f"'{_fid3}' in parents and trashed=false",
                                 fields="files(id,name)", pageSize=300).execute().get("files", [])
        for _e2 in _enf:
            faire(f"[{_ident3}] {_nomd3}/{_e2['name']} a la corbeille",
                  (lambda i=_e2["id"]: _dr2.files().update(
                      fileId=i, body={"trashed": True}).execute()))
except Exception as _e:
    _echecs.append(("Drive", str(_e)[:150]))

# --- 6. base locale et documents -----------------------------------------
titre("EXECUTION 6/7 — base locale dfm.db et documents produits")
try:
    import sqlite3 as _sq2
    _cx2 = _sq2.connect(os.path.join(DOSSIER, "dfm.db"))
    for _t4 in ("journal", "session_etat", "suivi"):
        faire(f"table « {_t4} » videe",
              (lambda t=_t4: (_cx2.execute("DELETE FROM %s" % t), _cx2.commit())))
    _cx2.close()
except Exception as _e:
    _echecs.append(("base locale", str(_e)[:150]))

try:
    import shutil as _sh4
    _DOCS2 = os.path.join(DOSSIER, "documents")
    _GARDES2 = ("_pieces", "_formateurs", "_formations", "_vignettes", "_corbeille")
    _CORB = os.path.join(_DOCS2, "_corbeille")
    for _d2 in sorted(os.listdir(_DOCS2) if os.path.isdir(_DOCS2) else []):
        _pd2 = os.path.join(_DOCS2, _d2)
        if not os.path.isdir(_pd2) or _d2 in _GARDES2:
            continue
        for _s5 in sorted(os.listdir(_pd2)):
            _ps2 = os.path.join(_pd2, _s5)
            if not os.path.isdir(_ps2):
                continue
            # DEPLACE, JAMAIS DETRUIT — meme regle que le Drive, ou l'on met a
            # la corbeille. Une convention signee effacee ne se refabrique pas.
            _cible = os.path.join(_CORB, _d2, _s5)
            faire(f"[{_d2}] {_s5} mis de cote",
                  (lambda src=_ps2, dst=_cible: (
                      os.makedirs(os.path.dirname(dst), exist_ok=True),
                      _sh4.rmtree(dst, ignore_errors=True),
                      _sh4.move(src, dst))))
except Exception as _e:
    _echecs.append(("documents", str(_e)[:150]))

# --- 7. Supabase ---------------------------------------------------------
titre("EXECUTION 7/7 — Supabase")
try:
    import config as _cfg
    from supabase import create_client as _cc
    _sb2 = _cc(_cfg.SUPABASE_URL, _cfg.SUPABASE_KEY)
    for _t3 in ("Signatures", "Annulations", "Questionnaires", "Sessions_publiques",
                "Inscriptions", "Sessions_inscription"):
        faire(f"table {_t3} videe",
              (lambda t=_t3: _sb2.table(t).delete().neq("id", -1).execute()))
except Exception as _e:
    _echecs.append(("Supabase", str(_e)[:150]))

# --------------------------------------------------------------------------
titre("TERMINE")
print(f"  {len(_faits)} operation(s) reussie(s), {len(_echecs)} en echec.")
for _q, _m in _echecs:
    print(f"     ECHEC  {_q} : {_m}")
print()
print("  A verifier maintenant :")
print("    1. DFM demarre :  ./DFM.command")
print("    2. aucun ecran en erreur")
print("    3. vos modeles, profils et parametres sont intacts")
print()
print("  Le Drive garde 30 jours ce qui est a la corbeille.")
print("  Vos documents produits sont dans documents/_corbeille — sans expiration.")
print("  Sauvegarde de sessions.py : sessions.py.avant-REMISE")
sys.exit(0 if not _echecs else 1)
