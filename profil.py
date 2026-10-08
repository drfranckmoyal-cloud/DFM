import json
import os
_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profil.json")
SECTIONS = [
    ("identite", "Identité", "ti-id-badge",
     "Le nom sous lequel vous apparaissez dans vos documents et vos mails."),
    ("coordonnees", "Coordonnées", "ti-map-pin",
     "Adresse et moyens de contact, repris sur vos factures et conventions."),
    ("legal", "Mentions légales", "ti-scale",
     "Obligatoires sur vos documents contractuels et vos factures."),
    ("banque", "Règlements", "ti-building-bank",
     "Coordonnées bancaires communiquées à vos participants."),
    ("qualiopi", "Qualiopi", "ti-certificate",
     "Ce qu'un auditeur attend de nommé et de joignable : un référent handicap, "
     "une adresse où adresser une réclamation. Ces informations sont reprises "
     "automatiquement sur vos convocations et vos documents."),
    ("logo", "Logo", "ti-photo",
     "Affiché en tête de chaque mail et de chaque document."),
    # L'ENVOI DES MAILS A SA SECTION, et ce n'est pas cosmetique. Sans elle,
    # un organisme nouvellement cree n'envoie rien et RIEN NE LE DIT : la
    # premiere convention echoue, et l'utilisateur n'a aucune raison de deviner
    # qu'il lui manque un « mot de passe d'application » Google. Le probleme se
    # decouvrait au pire moment, devant un client qui attend son document.
    ("envoi", "Envoi des mails", "ti-mail-forward",
     "Par où partent vos conventions, factures et attestations. "
     "Tant que ce n'est pas configuré, DFM utilise un chemin de secours qui "
     "peut cesser de fonctionner sans prévenir."),
    ("signature", "Signature et tampon", "ti-writing-sign",
     "Apposés au bas de vos conventions. Chaque organisme a les siens : "
     "le jour où une structure a son propre signataire, il suffit de déposer "
     "son image ici."),
]
SCHEMA = [
    {"cle": "organisme", "section": "identite", "type": "texte", "defaut": "",
     "libelle": "Raison sociale", "obligatoire": True,
     "aide": "Le nom juridique de votre structure, tel qu'il figure au registre du commerce.",
     "exemple": "SAS EXEMPLE FORMATION"},
    {"cle": "forme_juridique", "section": "identite", "type": "texte", "defaut": "",
     "libelle": "Forme juridique",
     "aide": "Facultatif. Apparaît sur les documents contractuels si renseigné.",
     "exemple": "Société par actions simplifiée"},
    {"cle": "marque", "section": "identite", "type": "texte", "defaut": "",
     "libelle": "Nom commercial", "obligatoire": True,
     "aide": "Le nom que connaissent vos participants. Il peut différer de la raison sociale.",
     "exemple": "Odonto Formations"},
    {"cle": "couleur", "section": "identite", "type": "couleur", "defaut": "#4f7ef8",
     "libelle": "Couleur de repérage",
     "aide": "Teinte l'interface entière quand cet organisme est actif. Deux couleurs bien distinctes évitent les confusions."},
    {"cle": "formateur", "section": "identite", "type": "texte", "defaut": "",
     "libelle": "Responsable pédagogique", "obligatoire": True,
     "aide": "Signe les conventions et les attestations.",
     "exemple": "DUPONT Marie"},
    {"cle": "signature_mail", "section": "identite", "type": "texte", "defaut": "",
     "libelle": "Signature des mails", "obligatoire": True,
     "aide": "Le nom qui apparaît en fin de chaque mail envoyé.",
     "exemple": "Marie Dupont"},
    {"cle": "adresse", "section": "coordonnees", "type": "texte", "defaut": "",
     "libelle": "Adresse", "obligatoire": True,
     "aide": "Numéro et voie du siège social.", "exemple": "12 rue des Lilas"},
    {"cle": "code_postal", "section": "coordonnees", "type": "texte", "defaut": "",
     "libelle": "Code postal", "obligatoire": True, "court": True, "exemple": "75011"},
    {"cle": "ville", "section": "coordonnees", "type": "texte", "defaut": "",
     "libelle": "Ville", "obligatoire": True, "exemple": "Paris"},
    {"cle": "pays", "section": "coordonnees", "type": "texte", "defaut": "France",
     "libelle": "Pays", "exemple": "France"},
    {"cle": "mail_contact", "section": "coordonnees", "type": "texte", "defaut": "",
     "libelle": "Adresse de contact", "obligatoire": True,
     "aide": "Communiquée aux participants pour vous joindre. Peut différer de l'adresse d'envoi.",
     "exemple": "contact@exemple.fr"},
    {"cle": "telephone_contact", "section": "coordonnees", "type": "texte", "defaut": "",
     "libelle": "Téléphone", "exemple": "06 00 00 00 00"},
    {"cle": "site_web", "section": "coordonnees", "type": "texte", "defaut": "",
     "libelle": "Site internet", "aide": "Facultatif.", "exemple": "https://exemple.fr"},
    {"cle": "siret", "section": "legal", "type": "texte", "defaut": "",
     "libelle": "SIRET", "obligatoire": True,
     "aide": "Quatorze chiffres. Obligatoire sur vos factures.", "exemple": "12345678900012"},
    {"cle": "numero_declaration", "section": "legal", "type": "texte", "defaut": "",
     "libelle": "Numéro de déclaration d'activité", "obligatoire": True,
     "aide": "Délivré par la DREETS. Obligatoire sur vos conventions de formation.",
     "exemple": "11750000075"},
    {"cle": "prefecture_declaration", "section": "legal", "type": "texte", "defaut": "",
     "libelle": "Enregistré auprès de",
     "aide": "La région qui a enregistré votre déclaration.",
     "exemple": "la préfecture de région d'Île-de-France"},
    {"cle": "tva_franchise", "section": "legal", "type": "booleen", "defaut": True,
     "libelle": "Franchise en base de TVA",
     "aide": "Si vous êtes en franchise, vos factures portent la mention de l'article 293 B et aucune TVA n'est facturée. Décochez si vous êtes assujetti : c'est une décision fiscale, pas un choix d'affichage."},
    {"cle": "tva_numero", "section": "legal", "type": "texte", "defaut": "",
     "libelle": "Numéro de TVA intracommunautaire",
     "aide": "Seulement si vous êtes assujetti.", "exemple": "FR00123456789"},
    {"cle": "tva_taux", "section": "legal", "type": "nombre", "defaut": 20,
     "libelle": "Taux de TVA appliqué", "unite": "%",
     "aide": "Seulement si vous êtes assujetti. La formation professionnelle peut être exonérée sous conditions."},
    {"cle": "capital", "section": "legal", "type": "texte", "defaut": "",
     "libelle": "Capital social", "aide": "Facultatif.", "exemple": "1 000 €"},
    {"cle": "logo_id", "section": "logo", "type": "drive", "defaut": "",
     "libelle": "Identifiant du logo dans Drive", "aide": "Rempli automatiquement à l'envoi du logo."},
    # SIGNATURE ET TAMPON — type « image », rangees EN LOCAL et non dans le
    # Drive comme le logo. Deux raisons : le chantier d'independance vis-a-vis
    # de Google n'a pas a se voir ajouter une dependance de plus, et une
    # convention doit pouvoir s'editer meme quand le jeton Google est expire.
    #
    # La valeur est le nom du fichier range sous « identite/<organisme>/ ».
    # Elle est ecrite par la route de depot, pas saisie a la main.
    {"cle": "signature_fichier", "section": "signature", "type": "image", "defaut": "",
     "libelle": "Signature du signataire", "obligatoire": True,
     "aide": "Apposée au bas des conventions, sous le nom du signataire. "
             "Fond transparent de préférence."},
    {"cle": "logo_fichier", "section": "logo", "type": "image", "defaut": "",
     "libelle": "Logo",
     "aide": "En-tête de vos mails et de vos documents. Remplace le logo du Drive."},
    {"cle": "tampon_fichier", "section": "signature", "type": "image", "defaut": "",
     "libelle": "Tampon de l'organisme", "obligatoire": True,
     "aide": "Apposé à côté de la signature sur les conventions."},
    {"cle": "titulaire_compte", "section": "banque", "type": "texte", "defaut": "",
     "libelle": "Titulaire du compte",
     "aide": "Tel qu'il apparaît sur votre relevé bancaire. Souvent identique à la raison sociale.",
     "exemple": "SAS EXEMPLE FORMATION"},
    {"cle": "iban", "section": "banque", "type": "texte", "defaut": "",
     "libelle": "IBAN", "obligatoire": True,
     "aide": "Communiqué dans le mail de confirmation pour les règlements par virement.",
     "exemple": "FR76 0000 0000 0000 0000 0000 000"},
    {"cle": "bic", "section": "banque", "type": "texte", "defaut": "",
     "libelle": "BIC", "obligatoire": True, "court": True, "exemple": "XXXXFRPPXXX"},
    {"cle": "compte_stripe", "section": "banque", "type": "texte", "defaut": "",
     "libelle": "Compte Stripe utilisé",
     "aide": "Simple repère : les liens de paiement sont propres à chaque formation, définis dans l'assistant de création. Ce champ vous rappelle quel compte est en vigueur pour cet organisme.",
     "exemple": "compte@exemple.fr"},
    {"cle": "format_facture", "section": "banque", "type": "texte", "defaut": "F{annee}-{numero}",
     "libelle": "Numérotation des factures",
     "aide": "Utilisez {annee}, {mois} et {numero}. La numérotation doit être continue et sans rupture : c'est une obligation comptable.",
     "exemple": "F{annee}-{numero}"},

    # --- Qualiopi : ce qui doit etre NOMME et JOIGNABLE ---
    # L'indicateur 26 n'attend pas une intention mais une personne identifiee.
    # DFM demandait deja aux inscrits s'ils avaient un besoin d'acces PMR et ne
    # montrait la reponse a personne : la question sans le referent, c'est
    # collecter une donnee sensible pour rien.
    {"cle": "referent_handicap", "section": "qualiopi", "type": "texte", "defaut": "",
     "libelle": "Référent handicap",
     "aide": "La personne à qui s'adresse un participant ayant besoin d'une adaptation. "
             "Elle est nommée sur vos convocations. Ce peut être vous : l'indicateur 26 "
             "demande qu'un référent soit identifié, pas qu'il soit à plein temps.",
     "exemple": "DUPONT Marie"},
    {"cle": "referent_handicap_contact", "section": "qualiopi", "type": "texte", "defaut": "",
     "libelle": "Contact du référent handicap",
     "aide": "Adresse mail ou téléphone communiqué aux participants. Sans moyen de "
             "joindre le référent, le nommer ne prouve rien.",
     "exemple": "handicap@exemple.fr"},
    {"cle": "reglement_interieur_id", "section": "qualiopi", "type": "drive", "defaut": "",
     "libelle": "Règlement intérieur",
     "aide": "Le PDF remis aux stagiaires avant l'entrée en formation. Il part "
             "automatiquement en pièce jointe de la convocation J-20, ce qui trace "
             "sa remise. Videz ce champ pour cesser de l'envoyer."},
    {"cle": "reclamations_contact", "section": "qualiopi", "type": "texte", "defaut": "",
     "libelle": "Adresse pour les réclamations",
     "aide": "Où un participant, un client ou un formateur adresse une réclamation. "
             "Figure sur le règlement intérieur et les convocations — indicateur 31.",
     "exemple": "reclamations@exemple.fr"},
    {"cle": "nouvel_entrant", "section": "qualiopi", "type": "booleen", "defaut": False,
     "libelle": "Nouvel entrant",
     "aide": "Première année d'activité comme organisme de formation, ou début d'activité "
             "sur une nouvelle catégorie d'actions. Sur onze indicateurs, seule la "
             "FORMALISATION du processus est vérifiée à l'audit initial ; la mise en œuvre "
             "l'est à l'audit de surveillance. L'assistant d'audit en tient compte."},
    {"cle": "reclamations_delai", "section": "qualiopi", "type": "nombre", "defaut": 15,
     "libelle": "Délai de réponse annoncé", "unite": "jours",
     "aide": "Le délai sous lequel vous vous engagez à répondre à une réclamation. "
             "Un délai annoncé et tenu est ce que l'auditeur vérifie."},
]

_DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profils")
_ACTIF = os.path.join(_DOSSIER, "actif.txt")
def _assurer():
    if not os.path.isdir(_DOSSIER):
        os.makedirs(_DOSSIER, exist_ok=True)
def _chemin(identifiant):
    _assurer()
    return os.path.join(_DOSSIER, identifiant + ".json")
def actif():
    _assurer()
    try:
        with open(_ACTIF, encoding="utf-8") as f:
            i = f.read().strip()
        if i and os.path.exists(_chemin(i)):
            return i
    except Exception:
        pass
    tous = lister()
    return tous[0]["id"] if tous else ""
def basculer(identifiant):
    _assurer()
    if not os.path.exists(_chemin(identifiant)):
        return False
    # Une seule ligne, mais c'est elle qui designe l'organisme : ecrite a
    # moitie, DFM ne saurait plus a qui appartiennent les documents.
    import fichiers
    fichiers.ecrire_texte(_ACTIF, identifiant)
    return True
def lister():
    _assurer()
    out = []
    try:
        for f in sorted(os.listdir(_DOSSIER)):
            if not f.endswith(".json"):
                continue
            i = f[:-5]
            try:
                with open(os.path.join(_DOSSIER, f), encoding="utf-8") as fh:
                    d = json.load(fh)
            except Exception:
                d = {}
            out.append({"id": i, "nom": d.get("marque") or d.get("organisme") or i,
                        "organisme": d.get("organisme") or "",
                        "couleur": d.get("couleur") or "#4f7ef8"})
    except Exception:
        pass
    return out
def nouvel_id(nom):
    import re as _re
    base = _re.sub(r"[^a-z0-9]+", "-", (nom or "organisme").lower()).strip("-") or "organisme"
    _assurer()
    if not os.path.exists(_chemin(base)):
        return base
    n = 2
    while os.path.exists(_chemin(base + "-" + str(n))):
        n += 1
    return base + "-" + str(n)
def creer(nom, depuis=None):
    _assurer()
    i = nouvel_id(nom)
    fiche = {}
    if depuis:
        try:
            with open(_chemin(depuis), encoding="utf-8") as f:
                fiche = dict(json.load(f))
        except Exception:
            fiche = {}
        for cle in ("siret", "numero_declaration", "iban", "bic", "tva_numero",
                    "stripe_lien", "mail_contact", "logo_id"):
            fiche.pop(cle, None)
    fiche["marque"] = nom
    fiche.setdefault("organisme", nom)
    fiche.setdefault("couleur", "#4f7ef8")
    import fichiers
    fichiers.ecrire(_chemin(i), fiche)
    return i
def supprimer_profil(identifiant):
    if len(lister()) <= 1:
        return False
    try:
        os.remove(_chemin(identifiant))
    except Exception:
        return False
    if actif() == identifiant:
        tous = lister()
        if tous:
            basculer(tous[0]["id"])
    return True

def _index():
    return {p["cle"]: p for p in SCHEMA}
def charger(identifiant=None):
    i = identifiant or actif()
    if not i:
        try:
            with open(_FICHIER, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    try:
        with open(_chemin(i), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}
def enregistrer(tout, identifiant=None):
    i = identifiant or actif()
    if not i:
        i = creer(tout.get("marque") or "Mon organisme")
        basculer(i)
    import fichiers
    fichiers.ecrire(_chemin(i), tout)
def valeur(cle, defaut=None, organisme=None):
    """La valeur d'un champ. Sans « organisme », celle du profil actif.

    UN ORGANISME EXPLICITE COUPE TOUT REPLI. Sans cette regle, lire la fiche de
    Smileclub depuis DSF rendrait les valeurs partagees de DSF pour tout ce que
    Smileclub ne stocke pas : un ecran qui affiche « Smileclub » en titre et les
    valeurs de l'autre en dessous. C'est exactement le defaut constate le
    21/08/2026, et le repli silencieux en etait la moitie.

    Meme raisonnement que profil._lecteur(repli=False) : l'absence d'une valeur
    chez un organisme est une information, pas un trou a combler avec celle du
    voisin.
    """
    stocke = charger(organisme)
    if cle in stocke and stocke[cle] not in ("", None):
        return stocke[cle]
    if organisme is None:
        try:
            from sessions import COMMUN
            if cle in COMMUN and COMMUN[cle] not in ("", None):
                return COMMUN[cle]
        except Exception:
            pass
    fiche = _index().get(cle)
    if fiche is not None:
        return fiche["defaut"]
    return defaut
def toutes(organisme=None):
    """Tous les champs du profil. Sans « organisme », ceux du profil actif."""
    stocke = charger(organisme)
    sortie = {}
    for p in SCHEMA:
        cle = p["cle"]
        v = valeur(cle, organisme=organisme)
        sortie[cle] = {"valeur": v, "rempli": bool(str(v).strip()) if p["type"] != "booleen" else True,
                       "personnalise": cle in stocke}
    return sortie
def manquants(organisme=None):
    """Les champs obligatoires vides. Sans « organisme », ceux du profil actif."""
    out = []
    for p in SCHEMA:
        if not p.get("obligatoire"):
            continue
        v = valeur(p["cle"], organisme=organisme)
        if not str(v or "").strip():
            out.append(p["libelle"])
    return out
def normaliser(cle, brut):
    fiche = _index().get(cle)
    if not fiche:
        return None
    t = fiche["type"]
    if t == "couleur":
        v = str(brut).strip()
        if len(v) == 7 and v.startswith("#"):
            return v
        return fiche["defaut"]
    if t == "booleen":
        return bool(brut) if not isinstance(brut, str) else brut.lower() in ("1", "true", "oui", "on")
    if t == "nombre":
        try:
            return int(str(brut).strip() or fiche["defaut"])
        except Exception:
            return fiche["defaut"]
    return str(brut).strip()
def sauver(donnees):
    """Rend (modifies, refuses) — meme contrat que parametres.sauver."""
    stocke = charger()
    modifies, refuses = [], []
    for cle, brut in (donnees or {}).items():
        fiche = _index().get(cle)
        if not fiche:
            continue
        # Les images ne se saisissent pas : elles se deposent. La valeur est
        # ecrite par deposer_image() et ne doit jamais etre modifiee par un
        # envoi de formulaire — un nom de fichier tape a la main pointerait
        # vers un fichier inexistant, et la convention partirait sans signature.
        if fiche["type"] == "image":
            continue
        if fiche["type"] == "drive":
            texte = str(brut or "").strip()
            if not texte:
                v = ""
            else:
                from sessions import extraire_id
                v = extraire_id(texte)
                if not v:
                    refuses.append({"cle": cle, "libelle": fiche["libelle"],
                                    "message": "« " + texte[:60] + " » n'est ni un lien Drive "
                                    "reconnaissable, ni un identifiant. Valeur non enregistrée."})
                    continue
        else:
            v = normaliser(cle, brut)
            if v is None:
                continue
        if stocke.get(cle) != v:
            modifies.append(cle)
        stocke[cle] = v
    enregistrer(stocke)
    return modifies, refuses
def _lecteur(donnees=None, repli=True):
    """Lecture d'un champ : depuis un dictionnaire fourni, sinon depuis la fiche
    enregistree. Permet de composer un apercu SANS ecrire dans le fichier reel
    de l'organisme, ce que faisait /profil/apercu (B4) — pendant cet instant,
    toute autre requete lisait des valeurs non enregistrees.

    repli=True : un champ absent du dictionnaire est cherche dans le profil
    ACTIF. C'est ce que veut l'apercu, ou le dictionnaire est une saisie
    PARTIELLE du meme organisme.

    repli=False : le dictionnaire fait autorite, y compris dans ses vides.
    C'est ce que veut la lecture d'un AUTRE organisme.

    DEFAUT CORRIGE LE 18/08/2026. Il n'y avait pas de repli=False, et
    sessions.py lisait l'adresse d'un autre organisme par ici. Un organisme
    neuf, sans adresse, recevait donc CELLE DE L'ORGANISME ACTIF — et le
    piege valait aussi pour un profil a moitie rempli : une rue saisie, pas
    de ville, et la ville du voisin venait completer la ligne."""
    if donnees is None:
        return valeur
    if not repli:
        def lire_seul(cle, defaut=None):
            x = donnees.get(cle)
            return defaut if x in (None, "") else x
        return lire_seul
    def lire(cle, defaut=None):
        x = donnees.get(cle)
        if x in (None, ""):
            return valeur(cle, defaut)
        return x
    return lire
def adresse_complete(donnees=None, repli=True):
    valeur = _lecteur(donnees, repli)
    bouts = [valeur("adresse"), " ".join([str(valeur("code_postal") or ""), str(valeur("ville") or "")]).strip()]
    pays = valeur("pays")
    if pays and str(pays).lower() not in ("france", ""):
        bouts.append(pays)
    return ", ".join([b for b in bouts if str(b).strip()])
def mention_tva(donnees=None, repli=True):
    valeur = _lecteur(donnees, repli)
    if valeur("tva_franchise"):
        return "TVA non applicable, article 293 B du Code général des impôts."
    numero = valeur("tva_numero")
    taux = valeur("tva_taux")
    bout = "TVA au taux de " + str(taux) + " %"
    if numero:
        bout += " — numéro " + str(numero)
    return bout + "."
def pied_legal(donnees=None, repli=True):
    valeur = _lecteur(donnees, repli)
    bouts = [str(valeur("organisme") or "")]
    a = adresse_complete(donnees, repli)
    if a:
        bouts.append(a)
    if valeur("siret"):
        bouts.append("SIRET : " + str(valeur("siret")))
    if valeur("numero_declaration"):
        d = "Déclaration d'activité n° " + str(valeur("numero_declaration"))
        p = valeur("prefecture_declaration")
        if p:
            d += " auprès de " + str(p)
        bouts.append(d)
    return " — ".join([b for b in bouts if b.strip()])

def _luhn_siret(v):
    chiffres = [int(c) for c in str(v) if c.isdigit()]
    if len(chiffres) != 14:
        return False
    total = 0
    for i, c in enumerate(chiffres):
        if i % 2 == 0:
            c *= 2
            if c > 9:
                c -= 9
        total += c
    return total % 10 == 0
def _iban_valide(v):
    t = "".join(str(v).split()).upper()
    if len(t) < 15 or len(t) > 34 or not t[:2].isalpha():
        return False
    t = t[4:] + t[:4]
    nombre = ""
    for c in t:
        nombre += str(ord(c) - 55) if c.isalpha() else c
    try:
        return int(nombre) % 97 == 1
    except Exception:
        return False
def verifier(donnees=None, organisme=None):
    """Ce qui cloche dans une fiche. Sans « organisme », celle du profil actif.

    L'ORGANISME COMPTE POUR DEUX RAISONS, decouvertes le 21/08/2026 en rendant
    la fiche d'un organisme non actif :

      1. Les doublons se cherchent CHEZ LES AUTRES. Sans savoir de qui est la
         fiche, la fonction s'excluait de l'actif et comparait donc Smileclub a
         Smileclub : « ce SIRET est deja celui de Smileclub Formations ». Trois
         reproches absurdes s'affichaient sur une fiche parfaitement saine.
      2. Un champ vide ne se comble pas avec la valeur du voisin. Sinon on
         validerait l'IBAN de DSF en croyant valider celui de Smileclub.
    """
    d = donnees if donnees is not None else charger(organisme)
    def v(cle):
        x = d.get(cle)
        if x in (None, ""):
            x = valeur(cle, organisme=organisme)
        return str(x or "").strip()
    soucis = []
    for p in SCHEMA:
        if p.get("obligatoire") and not v(p["cle"]):
            soucis.append({"grave": True, "champ": p["cle"],
                           "texte": p["libelle"] + " est obligatoire."})
    siret = v("siret")
    if siret:
        propre = "".join(c for c in siret if c.isdigit())
        if len(propre) != 14:
            soucis.append({"grave": True, "champ": "siret",
                           "texte": "Le SIRET doit comporter exactement quatorze chiffres, il en a " + str(len(propre)) + "."})
        elif not _luhn_siret(propre):
            soucis.append({"grave": False, "champ": "siret",
                           "texte": "La clé de contrôle du SIRET semble incorrecte. Vérifiez la saisie."})
    nda = v("numero_declaration")
    if nda:
        propre = "".join(c for c in nda if c.isdigit())
        if len(propre) != 11:
            soucis.append({"grave": False, "champ": "numero_declaration",
                           "texte": "Un numéro de déclaration d'activité comporte habituellement onze chiffres."})
    iban = v("iban")
    if iban and not _iban_valide(iban):
        soucis.append({"grave": True, "champ": "iban",
                       "texte": "Cet IBAN ne passe pas le contrôle de validité. Une erreur de saisie empêcherait vos virements."})
    bic = v("bic")
    if bic and len(bic.replace(" ", "")) not in (8, 11):
        soucis.append({"grave": False, "champ": "bic",
                       "texte": "Un BIC comporte huit ou onze caractères."})
    mail = v("mail_contact")
    if mail and ("@" not in mail or "." not in mail.split("@")[-1]):
        soucis.append({"grave": True, "champ": "mail_contact",
                       "texte": "Cette adresse de contact ne ressemble pas à une adresse valide."})
    cp = v("code_postal")
    if cp and not cp.replace(" ", "").isdigit():
        soucis.append({"grave": False, "champ": "code_postal",
                       "texte": "Le code postal ne devrait contenir que des chiffres."})
    fmt = v("format_facture")
    if fmt and "{numero}" not in fmt:
        soucis.append({"grave": True, "champ": "format_facture",
                       "texte": "Le format de facture doit contenir {numero}, sinon toutes vos factures porteraient le même numéro."})
    mien = organisme or actif()
    for autre in lister():
        if autre["id"] == mien:
            continue
        d2 = charger(autre["id"])
        for cle, libelle in (("siret", "SIRET"), ("iban", "IBAN"),
                             ("numero_declaration", "numéro de déclaration")):
            a_moi = "".join(str(v(cle)).split()).upper()
            a_lui = "".join(str(d2.get(cle) or "").split()).upper()
            if a_moi and a_moi == a_lui:
                soucis.append({"grave": True, "champ": cle,
                               "texte": "Ce " + libelle + " est déjà celui de « " + autre["nom"]
                               + " ». Deux organismes ne peuvent pas le partager."})
    if not d.get("tva_franchise", valeur("tva_franchise")):
        if not v("tva_numero"):
            soucis.append({"grave": False, "champ": "tva_numero",
                           "texte": "Vous n'êtes pas en franchise : le numéro de TVA est attendu sur vos factures."})
    return soucis
def clause_parties(praticien=None, donnees=None, repli=True):
    valeur = _lecteur(donnees, repli)
    p = praticien or {}
    bouts = []
    org = str(valeur("organisme") or "").strip()
    forme = str(valeur("forme_juridique") or "").strip()
    debut = "Entre les soussignés : " + org
    if forme:
        debut += ", " + forme
    capital = str(valeur("capital") or "").strip()
    if capital:
        debut += " au capital de " + capital
    a = adresse_complete(donnees, repli)
    if a:
        debut += ", dont le siège social est situé " + a
    siret = str(valeur("siret") or "").strip()
    if siret:
        debut += ", immatriculée sous le numéro SIRET " + siret
    nda = str(valeur("numero_declaration") or "").strip()
    if nda:
        debut += ", déclarée en tant qu'organisme de formation sous le numéro " + nda
        pref = str(valeur("prefecture_declaration") or "").strip()
        if pref:
            debut += " auprès de " + pref
    debut += ", représentée par " + str(valeur("formateur") or "") + ", ci-après dénommée « l'organisme de formation »,"
    bouts.append(debut)
    nom = (str(p.get("prenom") or "") + " " + str(p.get("nom") or "")).strip()
    seconde = "et " + (nom if nom else "le praticien")
    ville_p = str(p.get("ville") or "").strip()
    if ville_p:
        seconde += ", exerçant à " + ville_p
    seconde += ", ci-après dénommé « le bénéficiaire »,"
    bouts.append(seconde)
    bouts.append("il a été convenu ce qui suit.")
    return "\n\n".join(bouts)
def pret():
    m = manquants()
    graves = [x for x in verifier() if x["grave"]]
    return {"pret": not m and not graves,
            "manquants": m,
            "bloquants": [x["texte"] for x in graves]}


# --------------------------------------------------------------------------
# SIGNATURE ET TAMPON : des images, rangees par organisme, EN LOCAL.
#
# Elles etaient collees dans le modele Google Docs de la convention — donc
# invisibles pour le code, et perdues sans bruit le jour ou l'on sort de Docs.
# Elles deviennent un reglage du profil, au meme titre que le logo.
#
# EN LOCAL et non dans le Drive : une convention doit pouvoir s'editer meme
# quand le jeton Google est expire, et le chantier d'independance n'a pas a se
# voir ajouter une dependance de plus.
# --------------------------------------------------------------------------
IMAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "identite")

# 15 Mo A L'ENVOI : un tampon scanne a plat sort volontiers a plusieurs
# millions de pixels, et refuser le fichier tel qu'il sort du scanner obligerait
# a le retoucher ailleurs avant de le deposer.
TAILLE_MAX_IMAGE = 15 * 1024 * 1024

# MAIS ON LE REDUIT AVANT DE LE RANGER. Cette image est embarquee dans CHAQUE
# convention : un scan de 12 Mo produirait des PDF de 12 Mo, penibles a envoyer
# et lents a ouvrir. 1600 pixels de large suffisent largement pour une signature
# ou un tampon imprimes a quelques centimetres.
LARGEUR_MAX_IMAGE = 1600

# LA LARGEUR NE SUFFIT PAS. Un tampon de 479 x 318 pixels est arrive a
# 3,8 Mo — un PNG encode sans compression utile. Ne regarder que les pixels
# laissait passer une image cent fois trop lourde, embarquee dans CHAQUE
# convention. On plafonne donc aussi le poids, en reencodant.
POIDS_CIBLE_IMAGE = 400 * 1024

TYPES_IMAGE = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def _reduire(octets, ext):
    """Allege une image trop large ou trop lourde. Rend (octets, note).

    N'echoue jamais : si la reduction n'est pas possible, on garde l'original
    plutot que de refuser un depot pour une question de confort.
    """
    try:
        import fitz
        d = fitz.open(stream=octets, filetype=ext if ext != "jpg" else "jpeg")
        p = d[0]
        largeur = p.rect.width
        if largeur <= LARGEUR_MAX_IMAGE and len(octets) <= POIDS_CIBLE_IMAGE:
            return octets, ""

        notes, cible = [], min(largeur, LARGEUR_MAX_IMAGE)
        if largeur > LARGEUR_MAX_IMAGE:
            notes.append("réduite de %d à %d pixels de large" % (largeur, LARGEUR_MAX_IMAGE))
        # alpha=True : une signature a fond transparent le reste.
        reduit = p.get_pixmap(dpi=int(72 * cible / largeur), alpha=True).tobytes("png")
        # Un reencodage suffit le plus souvent. S'il ne suffit pas, on retrecit
        # par paliers plutot que de renoncer — mais jamais sous 700 pixels, en
        # dessous desquels un tampon imprime devient flou.
        while len(reduit) > POIDS_CIBLE_IMAGE and cible > 700:
            cible = int(cible * 0.75)
            reduit = p.get_pixmap(dpi=int(72 * cible / largeur), alpha=True).tobytes("png")
        if len(reduit) < len(octets):
            notes.append("allégée de %d à %d Ko" % (len(octets) // 1024, len(reduit) // 1024))
            return reduit, ", ".join(notes)
        return octets, ""
    except Exception:
        return octets, ""


def _sain(t):
    return "".join(c for c in str(t or "") if c.isalnum() or c in "-_") or "x"


def dossier_images(organisme=None):
    d = os.path.join(IMAGES, _sain(organisme or actif() or "sans-organisme"))
    os.makedirs(d, exist_ok=True)
    return d


def deposer_image(cle, nom_fichier, octets, type_mime="", organisme=None):
    """Range une image du profil. Rend (nom_range, souci)."""
    fiche = _index().get(cle)
    if not fiche or fiche.get("type") != "image":
        return None, "Ce réglage n'attend pas une image."
    if not octets:
        return None, "Fichier vide."
    if len(octets) > TAILLE_MAX_IMAGE:
        return None, ("Image trop lourde (%.1f Mo). La limite est de %d Mo."
                      % (len(octets) / 1048576.0, TAILLE_MAX_IMAGE // 1048576))
    ext = TYPES_IMAGE.get((type_mime or "").lower())
    if not ext:
        bout = str(nom_fichier or "").rsplit(".", 1)[-1].lower()
        ext = bout if bout in ("png", "jpg", "jpeg", "webp") else None
    if not ext:
        return None, "Format non accepté. Déposez un PNG, un JPG ou un WebP."
    octets, note = _reduire(octets, ext)
    if note:
        ext = "png"     # la reduction rend toujours du PNG
    # Le nom est fixe, derive de la cle : on REMPLACE l'image precedente
    # plutot que d'accumuler des versions dont on ne saurait plus laquelle sert.
    nom = "%s.%s" % (cle.replace("_fichier", ""), "jpg" if ext == "jpeg" else ext)
    d = dossier_images(organisme)
    for vieux in os.listdir(d):
        if vieux.rsplit(".", 1)[0] == nom.rsplit(".", 1)[0] and vieux != nom:
            try:
                os.remove(os.path.join(d, vieux))
            except OSError:
                pass
    import fichiers
    fichiers.ecrire_octets(os.path.join(d, nom), octets)
    # CHAQUE ORGANISME A SON FICHIER, sous profils/<id>.json. « profil.json »
    # ne sert que tant qu'aucun organisme n'existe : y ecrire ici rangeait la
    # signature dans un fichier que personne ne relit.
    with fichiers.modifier(_chemin(organisme or actif()), {}) as fiche:
        fiche[cle] = nom
    return nom, note


def retirer_image(cle, organisme=None):
    import fichiers
    o = organisme or actif()
    nom = (charger(o) or {}).get(cle) or ""
    if nom:
        try:
            os.remove(os.path.join(dossier_images(o), nom))
        except OSError:
            pass
    with fichiers.modifier(_chemin(o), {}) as fiche:
        fiche.pop(cle, None)
    return True


def chemin_image(cle, organisme=None):
    """Le chemin absolu d'une image du profil, ou None."""
    o = organisme or actif()
    nom = (charger(o) or {}).get(cle) or ""
    if not nom:
        return None
    p = os.path.join(dossier_images(o), os.path.basename(nom))
    return p if os.path.exists(p) else None


def image_en_ligne(cle, organisme=None):
    """L'image en adresse « data: », prête pour un document. "" si absente.

    En data: et non par une adresse : un PDF doit se fabriquer sans reseau ni
    serveur, comme le logo des attestations.
    """
    p = chemin_image(cle, organisme)
    if not p:
        return ""
    import mimetypes
    with open(p, "rb") as f:
        octets = f.read()
    import base64
    t = mimetypes.guess_type(p)[0] or "image/png"
    return "data:%s;base64,%s" % (t, base64.b64encode(octets).decode())


def logo(organisme=None):
    """Les octets du logo de l'organisme. None s'il n'y en a pas.

    UN SEUL POINT DE PASSAGE. Le logo etait retelecharge depuis le Drive a
    CHAQUE mail et a chaque document — 17 appels reseau dispersés dans autant
    de fichiers, pour une image de 10 a 25 Ko qui ne change jamais.

    L'ordre est : le fichier local d'abord, le Drive ensuite. Le repli est
    volontaire et temporaire : il laisse fonctionner les organismes dont le
    logo n'a pas encore ete depose, sans quoi la bascule serait un tout ou rien.
    """
    p = chemin_image("logo_fichier", organisme)
    if p:
        with open(p, "rb") as f:
            return f.read()
    ident = (charger(organisme) or {}).get("logo_id") or ""
    if not ident:
        return None
    try:
        from connexion import service_drive
        return service_drive().files().get_media(fileId=ident).execute()
    except Exception:
        return None
