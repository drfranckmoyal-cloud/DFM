COMMUN = {
    # CE BLOC NE CONTIENT PLUS AUCUNE IDENTITE. Il portait la marque, le nom du
    # formateur, le telephone, l'adresse de contact — et surtout l'IBAN ET LE BIC
    # de Smileclub, ecrits en dur.
    #
    # LE DEFAUT ETAIT SERIEUX. Un organisme nouvellement cree n'a rien dans sa
    # fiche : DFM retombait alors sur ces valeurs. Une facture emise par cet
    # organisme serait partie avec les COORDONNEES BANCAIRES DE SMILECLUB, et son
    # client aurait paye sur le mauvais compte. Constate le 18/08/2026 sur un
    # organisme d'essai qui affichait « smileclubformations@gmail.com » sans que
    # personne ne l'ait saisi.
    #
    # L'IDENTITE APPARTIENT AU PROFIL, un fichier par organisme. Rien ici ne doit
    # la suppleer : une valeur absente doit se VOIR — l'ecran Profil la reclame —
    # plutot que d'etre remplacee en silence par celle du voisin.
    #
    # NE RESTE QUE LE PARTAGE : le site public sert tous les organismes, et les
    # identifiants Drive historiques attendent d'etre repris par les profils.
    "url_signature": "https://gestion-des-formations.netlify.app",
    "sheet_suivi": "1RcrrRQAsvdczQ680-aL4_XX_yxknIiVQFgofoufMQfc",
    "logo_id": "1U3pE5KdyzqUoDRCfzzlUhh7AaQi3lZJt",
    "rib_id": "1UaxpKvIHffn0qG2_KmF_6X4helC6vd7I",
    "dossier_conventions": "16Hyzmzk0UpbiXhPz2wo3z2BiQg8S-WOz",
    "dossier_signees": "1xYIE6X9a_9AOzco6Hv83QyHHPiN_yPP2",
    # Vides, deliberement : mieux vaut une mention absente qu'une fausse.
    "organisme": "",
    "formateur": "",
    "marque": "",
    "telephone_contact": "",
    "iban": "",
    "bic": "",
    "numero_declaration": "",
    "mail_contact": "",
    "signature_mail": "",
}
# Aucune donnee ecrite en dur ici : formations et sessions vivent dans
# formations.json et sessions.json, un seul endroit chacune. Les litteraux
# qui s'y trouvaient etaient masques par le JSON charge juste apres — et
# celui de « usures » gardait des identifiants de modeles PERIMES, qui
# seraient ressortis en silence le jour ou le JSON aurait ete vide.
FORMATIONS = {}
SESSIONS = {}
import json as _json
import os as _os
_DOSSIER = _os.path.dirname(_os.path.abspath(__file__))
_FICHIER_F = _os.path.join(_DOSSIER, "formations.json")
_FICHIER_S = _os.path.join(_DOSSIER, "sessions.json")
def extraire_id(valeur):
    """Identifiant Drive depuis un lien complet OU un identifiant nu.
    Rend "" si la valeur n'est ni l'un ni l'autre. Extracteur unique de
    l'application : formulaire de formation, Parametres, profil, sessions."""
    import re as _re
    v = (valeur or "").strip()
    if not v:
        return ""
    # UNE REFERENCE LOCALE PASSE INTACTE. Depuis le 19/08/2026 un champ de
    # document peut porter « _formations/usures/programme/Programme.pdf ».
    # Sans cette porte, l'extracteur n'y reconnaissait aucun lien Drive et
    # rendait "" — c'est-a-dire qu'il EFFACAIT le document qu'on venait de
    # deposer, a la premiere reouverture de la fiche.
    if "/" in v and not v.lower().startswith(("http://", "https://")):
        return v
    m = _re.search(r"/d/([a-zA-Z0-9-_]{20,})", v) or _re.search(r"[?&]id=([a-zA-Z0-9-_]{20,})", v)
    if m:
        return m.group(1)
    m = _re.search(r"/folders/([a-zA-Z0-9-_]{20,})", v)
    if m:
        return m.group(1)
    return v if _re.fullmatch(r"[a-zA-Z0-9-_]{20,}", v) else ""
def nombre(valeur, defaut=0.0):
    """Nombre a partir d'une saisie humaine : "975", "975 €", "1 200", "1200,50".
    Rend `defaut` si rien d'exploitable. Le formulaire accepte du texte libre et
    donnees.py convertissait sans filet : "975 €" suffisait a mettre le tableau
    de bord en erreur 500 (B6)."""
    if isinstance(valeur, (int, float)):
        return float(valeur)
    s = str(valeur or "").strip()
    if not s:
        return defaut
    s = s.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    s = s.replace("€", "").replace("EUR", "").replace("CHF", "").replace("$", "")
    s = s.replace(",", ".")
    gardees = "".join(c for c in s if c.isdigit() or c in ".-")
    if gardees.count(".") > 1:
        entier, _, reste = gardees.partition(".")
        gardees = entier + "." + reste.replace(".", "")
    try:
        return float(gardees)
    except ValueError:
        return defaut
from datetime import datetime as _datetime


def date_fr(brut, avec_heure=True):
    """Une date lisible par un client francais : 03/08/2026 a 19h23.

    Supabase rend ses horodatages en ISO (« 2026-08-03T19:23:11 »), l'annee en
    tete. Tel quel dans un mail, cela se lit mal — et se confond avec un format
    americain. Cette fonction accepte les DEUX formes, l'ISO et le francais
    deja converti, pour que les traces ecrites avant sa creation s'affichent
    correctement elles aussi.

    Rend la chaine d'origine si elle n'est reconnue ni comme l'une ni comme
    l'autre : mieux vaut une date brute qu'une date vide."""
    s = str(brut or "").strip()
    if not s:
        return ""
    s = s.replace("T", " ").replace(" a ", " ").replace(" à ", " ")
    for forme in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                  "%d/%m/%Y %Hh%M", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            d = _datetime.strptime(s[:len(_datetime.now().strftime(forme))], forme)
        except ValueError:
            continue
        if avec_heure and "%H" in forme:
            return d.strftime("%d/%m/%Y à %Hh%M")
        return d.strftime("%d/%m/%Y")
    return str(brut)


def cle_nom(valeur):
    """Cle de rapprochement d'un nom de praticien, insensible a la casse, aux
    accents, aux tirets et aux espaces multiples.
    Le site de signature et le formulaire d'inscription sont remplis par deux
    personnes differentes : "Marie-Claire Dupont" d'un cote, "Marie Claire
    Dupont" de l'autre, et le praticien restait bloque en attente de signature
    indefiniment, sans le moindre message (B7)."""
    import unicodedata
    s = unicodedata.normalize("NFD", str(valeur or "")).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return " ".join(s.split())
def _charger_json(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}
def _ecrire_json(chemin, donnees):
    import fichiers
    fichiers.ecrire(chemin, donnees)
FORMATIONS.update(_charger_json(_FICHIER_F))
SESSIONS.update(_charger_json(_FICHIER_S))
def enregistrer_formation(code, fiche):
    ajouts = _charger_json(_FICHIER_F)
    ajouts[code] = fiche
    _ecrire_json(_FICHIER_F, ajouts)
    FORMATIONS[code] = fiche
    return code
# --------------------------------------------------------------------------
# Le mode d'une session
# --------------------------------------------------------------------------
# INDIVIDUEL : des praticiens s'inscrivent chacun pour eux. Convention,
#   signature, facture et reglement par personne. C'est le seul cas traite
#   jusqu'ici, et celui de toutes les sessions existantes.
# CLIENT : une structure achete la formation pour ses praticiens. Une seule
#   convention, une seule facture, un seul reglement — mais des attestations,
#   des questionnaires et un emargement individuels.
#
# UNE SESSION EST L'UN OU L'AUTRE, jamais les deux. Le mode se choisit a la
# creation et ne se change pas ensuite : les documents emis en dependent.
#
# ABSENCE = INDIVIDUEL. Les sessions ecrites avant l'existence de ce champ ne
# portent rien et restent individuelles, sans qu'aucune ait a etre modifiee.
MODES = {"individuel": "Inscriptions individuelles",
         "client": "Formation réalisée pour un client"}


def mode(code=None):
    fiche = SESSIONS.get(code or SESSION_ACTIVE) or {}
    m = (fiche.get("mode") or "").strip()
    return m if m in MODES else "individuel"


def est_client(code=None):
    return mode(code) == "client"


def client_de(code=None):
    """L'identifiant du client d'une session, ou "" si elle est individuelle."""
    if not est_client(code):
        return ""
    return ((SESSIONS.get(code or SESSION_ACTIVE) or {}).get("client") or "").strip()


# --------------------------------------------------------------------------
# A quel organisme appartient une session
# --------------------------------------------------------------------------
# Deux entites juridiques distinctes, deux comptabilites, DEUX CERTIFICATIONS
# QUALIOPI a defendre separement. Un auditeur venu examiner l'une ne doit voir
# que ses sessions, ses indicateurs, ses documents.
#
# AUCUN DEFAUT ICI, contrairement au mode. Pour le mode, l'absence vaut
# « individuel » : un defaut sur : il decrit ce qui existait deja. Pour
# l'organisme, un defaut serait DANGEREUX — une session creee sans organisme
# tomberait en silence chez l'un et apparaitrait dans l'audit de l'autre. Une
# session orpheline doit se VOIR, pas se deviner.
def organisme_de(code=None):
    """L'identifiant du profil proprietaire, ou "" si la session est orpheline."""
    fiche = SESSIONS.get(code or SESSION_ACTIVE) or {}
    return (fiche.get("organisme") or "").strip()


def orphelines():
    """Les sessions qui n'appartiennent a personne. Doit rester vide."""
    return sorted(c for c in SESSIONS if not organisme_de(c))


def visibles(profil=None):
    """Les codes de session que l'INTERFACE doit montrer.

    Le cloisonnement porte sur ce que l'on VOIT et ce que l'on ATTESTE, pas
    sur ce qui TOURNE. Un auditeur examine des ecrans et des documents, jamais
    la synchronisation. Restreindre le moteur ferait taire les envois de
    l'organisme inactif sans que personne s'en apercoive — un cloisonnement
    qui casse le service n'est pas un cloisonnement, c'est une panne.

    D'ou : le moteur continue de lire SESSIONS en entier, les ecrans passent
    par ici. Un seul point de passage, plutot qu'un filtre a recopier dans
    trente ecrans dont un manquera."""
    if profil is None:
        try:
            import profil as _p
            profil = (_p.actif() or "").strip()
        except Exception:
            profil = ""
    if not profil:
        return list(SESSIONS)           # profil illisible : on ne cache rien
    return [c for c in SESSIONS if organisme_de(c) == profil]


def refuser_si_client(code, raison):
    """Arrete proprement une etape du pipeline qui n'a pas de sens en mode
    client. NE LEVE PAS D'ERREUR : le rapport de synchronisation doit rester
    vert, parce qu'il ne s'est rien passe d'anormal — cette etape n'avait
    simplement rien a faire.

    Sortie 0 : dfm.py juge l'echec sur le code de retour, et une session
    client qui ferait rougir le rapport a chaque passage finirait par rendre
    le rapport illisible, donc inutile."""
    if not est_client(code):
        return
    fiche = SESSIONS.get(code or SESSION_ACTIVE) or {}
    print("-> Session CLIENT (" + (fiche.get("client") or "?") + ") : " + raison)
    print("   Etape sans objet ici. Rien n'a ete fait, et ce n'est pas une erreur.")
    raise SystemExit(0)


def enregistrer_session(code, fiche):
    ajouts = _charger_json(_FICHIER_S)
    ajouts[code] = fiche
    _ecrire_json(_FICHIER_S, ajouts)
    SESSIONS[code] = fiche
    return code
def supprimer_formation(code):
    ajouts = _charger_json(_FICHIER_F)
    if code in ajouts:
        del ajouts[code]
        _ecrire_json(_FICHIER_F, ajouts)
    FORMATIONS.pop(code, None)
def supprimer_session(code):
    ajouts = _charger_json(_FICHIER_S)
    if code in ajouts:
        del ajouts[code]
        _ecrire_json(_FICHIER_S, ajouts)
    SESSIONS.pop(code, None)
# PLUS DE SESSION ACTIVE. Les deux sessions d'essai de Smileclub ont ete
# supprimees le 01/10/2026, avant d'integrer la premiere vraie formation.
# La valeur vide est celle que remise_a_zero.py pose lui-meme : toutes les
# lectures passent par « SESSIONS.get(code or SESSION_ACTIVE) or {} », qui
# la supporte. La premiere vraie session la renseignera.
SESSION_ACTIVE = ""
class Inconnue(ValueError):
    """Session ou formation introuvable.

    Etait un SystemExit : celui-ci herite de BaseException, que Flask
    n'intercepte pas — une seule session dont la formation avait ete supprimee
    coupait brutalement /reglements, /conventions, /questionnaires (B5).
    ValueError se comporte normalement des deux cotes : page d'erreur lisible
    sous Flask, message clair en fin de trace pour les scripts en ligne de
    commande, que dfm.py reprend deja comme cause dans son rapport."""
def formation(code):
    if code not in FORMATIONS:
        raise Inconnue(f"Formation inconnue : {code} (disponibles : {', '.join(FORMATIONS)})")
    fiche = dict(FORMATIONS[code])
    fiche["code_formation"] = code
    return fiche

def _appliquer_parametres():
    try:
        import parametres
    except Exception:
        return
    # LES QUATRE « template_* » ONT ETE RETIRES LE 19/08/2026. Ils designaient
    # des Google Docs et Slides servant de gabarits — convention, attestation,
    # facture. Plus AUCUN generateur ne les lisait : conventions, attestations
    # et factures sortent de gabarits HTML locaux passes dans Chrome, et
    # service_docs() n'etait appele nulle part. DFM reclamait pourtant ces
    # documents a chaque creation de formation, et avertissait quand deux
    # formations en partageaient un.
    for cle in ("sheet_suivi", "url_signature", "logo_id", "rib_id",
                "dossier_conventions", "dossier_signees"):
        try:
            v = parametres.charger().get(cle)
        except Exception:
            v = None
        if v:
            COMMUN[cle] = v
COMMUN.setdefault("siret", "")
COMMUN.setdefault("adresse_organisme", "")
_COMMUN_BASE = dict(COMMUN)          # etat d'origine, avant toute surcharge
_CLES_PROFIL = ("organisme", "marque", "formateur", "signature_mail",
                "mail_contact", "telephone_contact", "iban", "bic",
                "numero_declaration", "siret", "logo_id",
                # Qualiopi : ces quatre valeurs appartiennent a l'ORGANISME et
                # doivent suivre chaque session, sans quoi une convocation DSF
                # partirait avec le reglement interieur de Smileclub — ou avec
                # aucun. Meme famille que le cloisonnement corrige le 04/08.
                "reglement_interieur_id", "referent_handicap",
                "referent_handicap_contact", "reclamations_contact")
# Le STOCKAGE appartient a l'organisme, pas aux Parametres. Deux entites
# juridiques ne partagent ni leur classeur de suivi, ni leurs dossiers de
# conventions, ni leur RIB — et la numerotation des factures se separe d'elle
# meme des que les dossiers le sont, puisqu'elle cherche le dernier numero
# dans le dossier de l'organisme.
#
# Le modele de facture, lui, RESTE COMMUN : verifie le 03/08/2026, il ne
# contient aucune identite en dur, seulement des balises remplies au moment de
# la generation depuis le profil actif. Le meme document sert les deux.
#
# Les quatre derniers ont ete ajoutes le 03/08/2026. Ils n'etaient pas
# cloisonnes : les scripts cherchaient un dossier nomme « Factures »,
# « Attestations », « Emargement » ou « Templates » dans TOUT le Drive et
# prenaient le premier. Depuis qu'il en existe deux de chaque, une facture DSF
# pouvait etre rangee chez Smileclub sans qu'aucun message ne le signale.
# Voir dossiers.py, qui porte la recherche et son secours.
_CLES_STOCKAGE = ("sheet_suivi", "dossier_conventions", "dossier_signees",
                  "rib_id",
                  "dossier_factures", "dossier_attestations",
                  "dossier_emargement", "dossier_templates")


def _appliquer_profil():
    """Recopie l'identite de l'organisme actif dans COMMUN. Sans cela, les mails
    et les documents restent sur les valeurs ecrites en dur ci-dessus, quel que
    soit le profil selectionne (points C6 et C10)."""
    try:
        import profil
        fiche = profil.charger() or {}
    except Exception:
        return
    for cle in _CLES_PROFIL + _CLES_STOCKAGE:
        v = fiche.get(cle)
        if isinstance(v, str):
            v = v.strip()
        if v:
            COMMUN[cle] = v
    # adresse_organisme : adresse postale de l'organisme, composee.
    # Volontairement distincte de "adresse", qui designe le lieu de la formation
    # et est ecrasee par la fiche formation dans session().
    try:
        import profil as _p
        a = _p.adresse_complete()
        if a:
            COMMUN["adresse_organisme"] = a
    except Exception:
        pass
def balises_identite(fiche=None):
    """Balises d'identite de l'organisme, communes aux trois modeles Google
    (convention, facture, attestation).

    PASSER LA FICHE DE SESSION quand on genere un document : l'identite doit
    etre celle de l'organisme PROPRIETAIRE de la session, jamais celle du
    profil actif au moment ou l'on clique.

    Toutes sont TOUJOURS presentes, meme quand la valeur est vide : une balise
    absente de ce dictionnaire resterait affichee en clair dans le document
    genere. Une valeur vide produit donc du vide, jamais "{{siret}}".

    mention_declaration est un cas a part : elle porte son propre intitule et
    disparait entierement quand le numero n'est pas renseigne, pour eviter
    un libelle sans valeur sur une facture."""
    # LA SOURCE EST LA SESSION, PAS LA GLOBALE. Defaut corrige le 04/08/2026 :
    # cette fonction lisait COMMUN, c'est-a-dire l'organisme ACTIF. Une
    # convention DSF editee pendant que Smileclub etait actif sortait au nom de
    # SAS LBS FORMATION, avec le SIRET de Smileclub — sur un acte contractuel.
    # Le meme defaut touchait factures et attestations.
    #
    # La fiche de session porte deja la bonne identite : _appliquer_proprietaire
    # y recopie les valeurs du profil PROPRIETAIRE. Il suffisait de la lire.
    # Sans fiche, on garde COMMUN : les appels existants ne changent pas de
    # comportement.
    source = fiche if isinstance(fiche, dict) else None

    def v(cle):
        if source is not None:
            val = str(source.get(cle) or "").strip()
            if val:
                return val
        return str(COMMUN.get(cle) or "").strip()
    num = v("numero_declaration")
    # Variante longue, pour la clause des parties d'une convention : elle ajoute
    # l'autorite d'enregistrement quand le profil la renseigne. Comme la forme
    # courte, elle disparait entierement si le numero est absent.
    longue = ""
    if num:
        longue = "Déclaration d'activité : " + num
        # Meme regle : la prefecture vient de la fiche si elle y est, et non du
        # profil actif. Le repli sur profil.valeur ne sert qu'aux appels sans
        # fiche, ou l'organisme actif est bien la seule reference disponible.
        pref = v("prefecture_declaration")
        if not pref:
            try:
                import profil as _p
                pref = str(_p.valeur("prefecture_declaration") or "").strip()
            except Exception:
                pref = ""
        if pref:
            longue += " auprès de la " + pref
    return {
        "{{organisme}}": v("organisme"),
        "{{marque}}": v("marque"),
        "{{adresse_organisme}}": v("adresse_organisme"),
        "{{siret}}": v("siret"),
        "{{numero_declaration}}": num,
        "{{mention_declaration}}": ("Déclaration d'activité : " + num) if num else "",
        "{{mention_declaration_longue}}": longue,
        "{{formateur}}": v("formateur"),
        "{{mail_contact}}": v("mail_contact"),
        "{{telephone}}": v("telephone_contact"),
        "{{iban}}": v("iban"),
        "{{bic}}": v("bic"),
    }
def balises_stagiaire(fiche, ligne):
    """Les balises propres a UN PRATICIEN, pour le modele de convention unique.

    LE MEME DOCUMENT sert les sessions clients et individuelles depuis le
    04/08/2026. Ce qui change n'est pas le document mais ce qui le remplit : la
    seconde partie de la clause « Entre les soussignes », le bloc de signature,
    et la liste des participants reduite a une personne.

    LA VILLE N'Y FIGURE PAS — decision de Franck du 04/08/2026. Le champ est de
    la saisie libre (« Paris 9 », « MARSEILLE », « Tel aviv ») et rien n'oblige
    a faire figurer un domicile professionnel dans un acte entre un organisme
    et un praticien. Ce qu'on n'ecrit pas ne peut pas etre faux.
    """
    nom = ((ligne.get("prenom") or "") + " " + (ligne.get("nom") or "")).strip()
    fonction = (ligne.get("fonction") or "").strip() or "Chirurgien-dentiste"
    tarif = str(fiche.get("tarif") or "")
    objectifs = fiche.get("objectifs")
    if isinstance(objectifs, (list, tuple)):
        objectifs = "\n".join("• " + str(x).strip() for x in objectifs if str(x).strip())
    return {
        "{{seconde_partie}}": "Docteur %s, désigné ci-après « le Stagiaire »." % nom,
        # Bloc de signature : le praticien signe en son nom propre. Il n'y a
        # aucune personne morale a nommer sous sa signature, d'ou la
        # denomination laissee vide plutot qu'une ligne inventee.
        "{{client_representant}}": "Docteur " + nom,
        "{{client_fonction}}": fonction,
        "{{client_denomination}}": "",
        "{{nom_prenom}}": nom,
        "{{participants}}": "• %s — %s" % (nom, fonction),
        "{{nb_participants}}": "1",
        # Un seul stagiaire : le total EST le tarif. La balise existe quand meme,
        # sinon elle resterait affichee en clair sur le document.
        "{{tarif}}": tarif,
        "{{total}}": tarif,
        "{{titre_formation}}": fiche.get("titre_complet") or fiche.get("nom_formation") or "",
        "{{objectifs}}": objectifs or "",
        "{{duree}}": fiche.get("duree_heures") or "",
        "{{lieu}}": fiche.get("adresse") or "",
        "{{horaires}}": fiche.get("horaires") or "",
        "{{date_formation}}": (ligne.get("date_formation") or "").strip()
                              or fiche.get("date_texte") or "",
    }


def appliquer_identite():
    """Reconstruit COMMUN : valeurs d'origine, puis parametres, puis profil actif.
    Le passage par _COMMUN_BASE evite qu'une valeur d'un profil precedent
    survive a une bascule vers un profil ou le champ est vide."""
    COMMUN.clear()
    COMMUN.update(_COMMUN_BASE)
    _appliquer_parametres()
    _appliquer_profil()
appliquer_identite()

def session(code=None):
    code = code or SESSION_ACTIVE
    if code not in SESSIONS:
        raise Inconnue(f"Session inconnue : {code} (disponibles : {', '.join(SESSIONS)})")
    brute = SESSIONS[code]
    fiche = dict(COMMUN)
    fiche.update(formation(brute["formation"]))
    fiche.update(brute)
    fiche["code"] = code
    fiche["dossier_session"] = f"{fiche['nom_formation']}-{fiche['code_session']}"
    # DEUX SENS POUR UN MEME MOT. Dans une session, « organisme » designe
    # l'IDENTIFIANT du profil proprietaire ; dans un profil, il designe la
    # RAISON SOCIALE. Le second ecrasait le premier. On garde l'identifiant
    # sous un nom qui ne peut pas entrer en collision.
    fiche["organisme_code"] = (brute.get("organisme") or "").strip()
    # La session vient d'ecraser « organisme » avec son identifiant : on rend
    # a ce champ son sens de RAISON SOCIALE, celui qu'attendent les documents.
    fiche["organisme"] = COMMUN.get("organisme") or ""
    _appliquer_proprietaire(fiche)
    return fiche


def _appliquer_proprietaire(fiche):
    """Une session est lue avec les valeurs de SON organisme, jamais celles du
    profil actif.

    DEFAUT CORRIGE LE 03/08/2026. Depuis que le stockage descend dans le profil,
    COMMUN portait celui de l'organisme ACTIF. Consequence : une session
    Smileclub consultee pendant que DSF etait actif cherchait son onglet dans
    le classeur de DSF, ne l'y trouvait pas, et le pipeline s'arretait sur
    « la ligne 1 est vide » — un message qui accusait les en-tetes alors que
    c'etait le classeur qui n'etait pas le bon.

    Meme lecon que A1 : l'adresse vient de la session, jamais d'une globale.
    Et cela vaut aussi pour l'IDENTITE — une convention Smileclub doit porter
    le SIRET de Smileclub, meme editee un jour ou DSF est actif."""
    proprietaire = (fiche.get("organisme_code") or "").strip()
    if not proprietaire:
        return                       # session orpheline : on ne devine rien
    try:
        import profil as _p
        if proprietaire == (_p.actif() or "").strip():
            return                   # deja le bon profil, rien a reprendre
        autre = _p.charger(proprietaire) or {}
    except Exception:
        return
    # L'ABSENCE DU PROPRIETAIRE EST UNE VALEUR. On reprend TOUT, y compris ce
    # qui est vide chez lui.
    #
    # DEFAUT CORRIGE LE 18/08/2026. La regle etait « on ne remplace que si le
    # proprietaire a quelque chose ». Un organisme neuf n'a rien : ses sessions
    # gardaient donc les valeurs de COMMUN, c'est-a-dire celles de l'organisme
    # ACTIF — son IBAN, son SIRET, son adresse de contact. Une facture emise
    # par le nouvel organisme serait partie avec les COORDONNEES BANCAIRES DU
    # VOISIN, et son client aurait paye sur le mauvais compte.
    #
    # Un champ manquant doit SE VOIR — l'ecran Profil le reclame, les documents
    # laissent un blanc — plutot que d'etre comble en silence par autrui.
    for cle in _CLES_PROFIL + _CLES_STOCKAGE:
        v = autre.get(cle)
        fiche[cle] = v.strip() if isinstance(v, str) else (v if v is not None else "")
    try:
        # Meme regle : l'adresse du proprietaire, meme absente. repli=False
        # sinon profil.py comble les trous avec le profil ACTIF.
        fiche["adresse_organisme"] = _p.adresse_complete(autre, repli=False) or ""
    except Exception:
        fiche["adresse_organisme"] = ""
def sessions_de(code_formation):
    return [c for c, s in SESSIONS.items() if s["formation"] == code_formation]
def lister():
    for code_f, f in FORMATIONS.items():
        sess = sessions_de(code_f)
        print(f"  {f['nom_formation']}  ({f['tarif']} EUR, {f['places_max']} places)")
        for c in sess:
            actif = "  <- active" if c == SESSION_ACTIVE else ""
            print(f"     . {c} : {SESSIONS[c]['date_texte']}{actif}")
        if not sess:
            print("     (aucune session)")


# ---------------------------------------------------------------------------
# L'ETAT DE VIE D'UNE SESSION
#
# Une session etait coupee en deux : sa CONFIGURATION ici, dans sessions.json,
# et son ETAT — cloture, emargement, report, alertes — dans un onglet Google.
# Une vingtaine d'endroits lisaient l'onglet entier pour retrouver une ligne par
# son code et modifier une cellule. L'etat est desormais dans la base locale, et
# ces trois fonctions sont tout ce que les appelants ont a connaitre.
#
# LE CLASSEUR RESTE TENU A JOUR, en miroir. DFM n'y lit plus.
# ---------------------------------------------------------------------------

# Les quatre colonnes de configuration de l'onglet, reconstituees a l'ecriture
# depuis sessions.json. Elles n'ont jamais ete stockees deux fois volontairement :
# les recopier dans la base ferait deux verites, ce qu'on est en train de defaire.
_COLONNES_ONGLET = ["code_session", "nom_formation", "date_debut", "date_fin",
                    "statut_session", "cloture_le", "emargement_genere_le",
                    "lien_emargement", "emargement_signe_le",
                    "lien_emargement_signe", "places_max", "terminee_le",
                    "report_le", "alerte_cloture_le"]


def etat(code=None):
    """L'etat de vie d'une session. Toujours un dictionnaire complet."""
    import base
    code = code or SESSION_ACTIVE
    return base.etat_lire(organisme_de(code) or "", code)


def etats(organisme=None):
    """Les etats connus d'un organisme : {code_session: etat}."""
    import base
    return base.etats(organisme)


def poser_etat(code, champ, valeur, miroir=True):
    """Ecrit un champ d'etat. Rend l'etat complet apres ecriture."""
    return poser_etats(code, {champ: valeur}, miroir=miroir)


def poser_etats(code, valeurs, miroir=True):
    """Ecrit plusieurs champs d'etat en une fois, puis met a jour le miroir.

    L'ECRITURE LOCALE N'ATTEND PAS GOOGLE. Un miroir en echec laisse une trace
    a l'ecran et rien de plus : l'etat est deja enregistre. C'est la lecon du
    journal, ou une panne de reseau faisait disparaitre l'evenement.
    """
    import base
    org = organisme_de(code) or ""
    apres = base.etat_poser_plusieurs(org, code, valeurs)
    if miroir:
        _miroir(code, org, apres)
    return apres


def _miroir(code, organisme, etat_apres):
    """Recopie la ligne de la session dans l'onglet Google.

    ON NE MIROITE QUE LES SESSIONS CONNUES. L'onglet garde des lignes de
    sessions supprimees — trois sur six le 17/08/2026 — dont la configuration
    n'existe plus dans sessions.json. Les reecrire les viderait de leur nom et
    de leurs dates. Elles ne sont de toute facon jamais modifiees.
    """
    if code not in SESSIONS:
        return
    # session(code) ET NON SESSIONS[code] : le dictionnaire brut ne porte que ce
    # qui est propre a la session ; le nom de la formation vient de la FORMATION
    # et n'y figure pas. Avec le dictionnaire brut, le miroir a efface le nom
    # « Usures » d'une ligne du classeur — corrige le 17/08/2026 des le premier
    # essai, mais c'est exactement ainsi qu'un miroir detruit ce qu'il copie.
    S = session(code)
    try:
        import profil
        from connexion import service_sheets
        feuille = (profil.charger(organisme) or {}).get("sheet_suivi") or ""
        if not feuille:
            return
        sh = service_sheets()
        codes = sh.spreadsheets().values().get(
            spreadsheetId=feuille, range="'Sessions'!A2:A200"
        ).execute().get("values", [])
        rang = None
        for i, l in enumerate(codes):
            if l and str(l[0] or "").strip() == code:
                rang = i + 2
                break
        ligne = [code, S.get("nom_formation") or "", S.get("date_debut") or "",
                 S.get("date_fin") or ""]
        ligne += [etat_apres.get(c, "") for c in
                  ("statut_session", "cloture_le", "emargement_genere_le",
                   "lien_emargement", "emargement_signe_le", "lien_emargement_signe")]
        ligne += [str(S.get("places_max") or "")]
        ligne += [etat_apres.get(c, "") for c in
                  ("terminee_le", "report_le", "alerte_cloture_le")]
        if rang:
            sh.spreadsheets().values().update(
                spreadsheetId=feuille, range="'Sessions'!A%d:N%d" % (rang, rang),
                valueInputOption="USER_ENTERED", body={"values": [ligne]}).execute()
        else:
            sh.spreadsheets().values().append(
                spreadsheetId=feuille, range="'Sessions'!A:N",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values": [ligne]}).execute()
    except Exception as e:
        print("   (miroir Sessions en retard, etat bien enregistre : %s)" % str(e)[:80])
