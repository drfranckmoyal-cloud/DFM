# -*- coding: utf-8 -*-
"""Les codes promo, saisis par le praticien sur le formulaire d'inscription.

POURQUOI UN REGISTRE DANS DFM — 08/11/2026, demande de Franck : « un code promo
a l'inscription, repercute sur le prix et la convention ». Meme raison que les
invitations : un code qui ne vivrait que dans la page publique serait celui que
n'importe qui peut forger. DFM tient la liste ; il la PUBLIE vers Supabase pour
que le formulaire montre le prix reduit avant l'envoi, et il la RELIT a l'import
pour arreter le prix. Le formulaire annonce, DFM decide.

UN CODE APPARTIENT A UN ORGANISME. Deux entites, deux Qualiopi, deux politiques
commerciales : un code Smileclub ne vaut rien sur le formulaire de DSF, meme
s'il porte le meme nom.

LA REMISE S'ECRIT SUR LA LIGNE, UNE FOIS. A l'import, la ligne recoit le code,
la remise en euros et le prix qui en resulte (« montant_du »). Tout DFM lit deja
ce prix-la — convention, facture, mails, relances, reglements : rien d'autre
n'a a connaitre les codes. Modifier ou desactiver un code ensuite ne touche
aucune inscription deja faite.

UN CODE NE S'EFFACE PAS. On le desactive : il reste au registre, avec qui l'a
cree et quand. C'est la trace d'une pratique commerciale, et des factures le
citent.

LA REMISE SE CALCULE AU CENTIME, COMME STRIPE — 08/11/2026. Elle etait
arrondie a l'euro (10 % de 975 = 98) pour que les documents restent en euros
entiers ; mais le premier coupon cree dans Stripe, REMISE10, en pourcentage,
encaissait 877,50 euros quand la convention en annoncait 877. Le paiement par
carte et l'acte signe doivent dire le meme chiffre : la convention, la facture
et les mails savent ecrire « 877,50 ».
"""
import os as _os
import re as _re
from datetime import date, datetime

import fichiers

_DOSSIER = _os.path.dirname(_os.path.abspath(__file__))
FICHIER = _os.path.join(_DOSSIER, "codes_promo.json")
TABLE = "Codes_promo"

TYPES = ("pourcentage", "montant")
_FORME = _re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,29}$")


def normaliser(code):
    """« bienvenue 26 » et « BIENVENUE26 » sont le meme code."""
    return _re.sub(r"\s+", "", str(code or "")).upper()


def forme_valide(code):
    return bool(_FORME.match(normaliser(code)))


def lister(organisme):
    """Les codes de cet organisme, le plus recent d'abord."""
    lot = fichiers.lire(FICHIER, {}).get(organisme) or {}
    sortie = []
    for code, d in lot.items():
        e = dict(d or {})
        e["code"] = code
        sortie.append(e)
    sortie.sort(key=lambda e: e.get("cree_le_iso") or "", reverse=True)
    return sortie


def trouver(organisme, code):
    d = (fichiers.lire(FICHIER, {}).get(organisme) or {}).get(normaliser(code))
    if not d:
        return None
    e = dict(d)
    e["code"] = normaliser(code)
    return e


def montant_texte(x):
    """« 877 » ou « 877.50 » : un montant tel qu'il s'ecrit sur la ligne."""
    x = round(float(x or 0), 2)
    return ("%d" % x) if x == int(x) else ("%.2f" % x)


def remise(regle, tarif):
    """La remise en euros, au centime, comme Stripe la calcule. Jamais plus que le tarif."""
    try:
        t = float(str(tarif or 0).replace(",", ".").replace(" ", ""))
    except ValueError:
        return 0.0
    if t <= 0 or not regle:
        return 0.0
    v = float(regle.get("valeur") or 0)
    # round(t * v) / 100 : 975 x 10 = 9750 centimes, sans erreur d'arrondi
    # binaire — le meme calcul que la fonction Netlify (inscrire.js).
    r = round(t * v) / 100.0 if regle.get("type") == "pourcentage" else v
    return float(max(0.0, min(float(r), t)))


def libelle(regle):
    """« 10 % » ou « 150 € » : ce que l'ecran et la page publique affichent."""
    v = float(regle.get("valeur") or 0)
    nombre = ("%d" % v) if v == int(v) else ("%.2f" % v).replace(".", ",")
    return nombre + (" %" if regle.get("type") == "pourcentage" else " €")


def _jour(le):
    if le is None:
        return date.today()
    if isinstance(le, datetime):
        return le.date()
    if isinstance(le, date):
        return le
    # Seul le jour compte : l'horodateur du suivi (« 08/11/2026 14:02:11 ») ou
    # une date ISO.
    s = str(le).strip()[:10]
    for forme in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, forme).date()
        except ValueError:
            continue
    return date.today()


def verifier(organisme, code_session, code, tarif, le=None, utilisations=None,
             actif_requis=True):
    """(regle, remise, "") si le code vaut pour cette session, (None, 0, motif) sinon.

    `le` est le jour de la demande : un code valable jusqu'au 30 et saisi le 30
    reste acquis si l'import ne passe que le 1er. `utilisations` est le nombre
    d'inscriptions qui le portent deja ; None ne verifie pas le plafond — c'est
    le cas de l'import, le formulaire l'ayant verifie au moment de l'envoi.

    A L'IMPORT, UN CODE DESACTIVE ENTRE-TEMPS RESTE ACQUIS (actif_requis=False) :
    la personne a vu le prix reduit et envoye sa demande sur cette foi. Seule
    la page publique peut ecrire une demande, et elle a juge le code a ce
    moment-la.
    """
    c = normaliser(code)
    if not c:
        return None, 0.0, "Aucun code saisi."
    r = trouver(organisme, c)
    if not r:
        return None, 0.0, "Ce code n'existe pas."
    if actif_requis and not r.get("actif", True):
        return None, 0.0, "Ce code n'est plus valable."
    sessions = r.get("sessions") or []
    if sessions and code_session not in sessions:
        return None, 0.0, "Ce code ne s'applique pas à cette formation."
    fin = (r.get("jusqu_au") or "").strip()
    if fin and _jour(le).isoformat() > fin:
        return None, 0.0, "Ce code a expiré."
    plafond = int(r.get("max") or 0)
    if utilisations is not None and plafond and utilisations >= plafond:
        return None, 0.0, "Ce code a déjà été utilisé le nombre de fois prévu."
    montant = remise(r, tarif)
    try:
        t = float(str(tarif or 0).replace(",", "."))
    except ValueError:
        t = 0.0
    # UN CODE NE REND PAS UNE FORMATION GRATUITE. Une formation offerte passe par
    # l'invitation, qui a son statut, sa convention a zero et sa mention.
    if montant <= 0 or montant >= t:
        return None, 0.0, "Ce code ne s'applique pas à cette formation."
    return r, montant, ""


def poser(organisme, code, type_remise, valeur, sessions=None, jusqu_au="",
          plafond=0, note="", stripe=False, par=""):
    """Cree ou modifie un code. Rend (ok, message)."""
    c = normaliser(code)
    if not forme_valide(c):
        return False, ("Un code fait de 3 à 30 lettres ou chiffres, sans espace "
                       "ni accent (tirets acceptés).")
    if type_remise not in TYPES:
        return False, "Choisissez une remise en pourcentage ou en euros."
    try:
        v = float(str(valeur).replace(",", ".").replace(" ", "").replace("€", "").replace("%", ""))
    except ValueError:
        return False, "La remise doit être un nombre."
    if type_remise == "pourcentage" and not (0 < v < 100):
        return False, ("Un pourcentage entre 1 et 99. Pour offrir la formation, "
                       "utilisez l'invitation.")
    if type_remise == "montant" and v <= 0:
        return False, "La remise doit être supérieure à zéro."
    v = float(int(round(v)))
    fin = (jusqu_au or "").strip()
    if fin:
        try:
            fin = datetime.strptime(fin, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return False, "La date de fin n'est pas lisible."
    try:
        plafond = max(0, int(plafond or 0))
    except ValueError:
        return False, "Le nombre d'utilisations doit être un nombre entier."
    quand = datetime.now()
    with fichiers.modifier(FICHIER, {}) as tout:
        lot = tout.setdefault(organisme, {})
        deja = lot.get(c) or {}
        lot[c] = {
            "type": type_remise, "valeur": v,
            "sessions": sorted({s for s in (sessions or []) if s}),
            "jusqu_au": fin, "max": plafond, "note": (note or "").strip()[:200],
            "stripe": bool(stripe), "actif": deja.get("actif", True),
            "cree_le": deja.get("cree_le") or quand.strftime("%d/%m/%Y %H:%M"),
            "cree_le_iso": deja.get("cree_le_iso") or quand.isoformat(timespec="seconds"),
            "par": deja.get("par") or par or "",
            "modifie_le": quand.strftime("%d/%m/%Y %H:%M") if deja else "",
        }
    return True, ("Code %s modifié." if deja else "Code %s créé.") % c


def activer(organisme, code, actif):
    c = normaliser(code)
    with fichiers.modifier(FICHIER, {}) as tout:
        d = (tout.get(organisme) or {}).get(c)
        if not d:
            return False
        d["actif"] = bool(actif)
        d["modifie_le"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return True


def sessions_de(organisme):
    import sessions as _s
    return [c for c in _s.SESSIONS if (_s.organisme_de(c) or "") == organisme]


def utilisations(organisme, code=None):
    """{CODE: [inscrits]} — les lignes, non annulees, qui portent un code."""
    import suivi
    c = normaliser(code) if code else None
    vus = {}
    for s in sessions_de(organisme):
        try:
            lignes = suivi.lire_lignes_de(s)
        except Exception:
            continue
        for l in lignes:
            k = normaliser(l.get("code_promo"))
            if not k or (c and k != c) or l.get("annule_le"):
                continue
            vus.setdefault(k, []).append({
                "qui": ("%s %s" % (l.get("prenom") or "", l.get("nom") or "")).strip(),
                "session": s, "remise": l.get("remise") or ""})
    return vus


def appliquer(ligne, S, code_session, code, le=None):
    """Pose le code sur une ligne qui va naitre. Rend (applique, message).

    Le prix arrete est celui de la session moins la remise : c'est l'import
    qui l'ecrit, comme il ecrit deja le tarif pour tout le monde.
    """
    import sessions as _s
    org = _s.organisme_de(code_session) or ""
    r, montant, motif = verifier(org, code_session, code, S.get("tarif"), le=le,
                                 actif_requis=False)
    if not r:
        return False, motif
    tarif = float(str(S.get("tarif") or 0).replace(",", "."))
    ligne["code_promo"] = r["code"]
    ligne["remise"] = montant_texte(montant)
    ligne["montant_du"] = montant_texte(tarif - montant)
    return True, "%s : %s de remise, reste %s €" % (r["code"], libelle(r),
                                                     montant_texte(tarif - montant))


def remise_de(ligne, tarif_session, du):
    """(remise, code) a ecrire sur un document, ou (0.0, "") s'il n'y en a pas.

    LA REMISE NE S'AFFICHE QUE SI ELLE EXPLIQUE LE PRIX. Un prix repris a la
    main apres coup — un cycle dont le montant se fixe a la validation —
    ferait lire « 975 moins 98 » au-dessus d'un total qui ne vaut pas 877 :
    un acte qui ne s'additionne pas. Dans ce cas on ecrit le prix seul.
    """
    import suivi
    ligne = ligne or {}
    code = normaliser(ligne.get("code_promo"))
    r = suivi.euros(ligne.get("remise"))
    if not code or r <= 0:
        return 0.0, ""
    if abs((suivi.euros(tarif_session) - r) - float(du or 0)) >= 0.005:
        return 0.0, ""
    return r, code


def lien_paiement(S, ligne):
    """Le lien de paiement par carte de CETTE personne. "" si elle n'en a pas.

    LE LIEN STRIPE D'UNE SESSION EST A PRIX FIXE. Il encaisse le tarif de la
    session, quoi qu'on ait convenu avec la personne. Le donner a quelqu'un qui
    doit moins, c'est lui faire payer trop : il ne sert donc qu'a qui doit
    exactement ce tarif. Les autres reglent par virement, sauf si le code existe
    aussi dans Stripe — le lien le saisit alors pour eux.
    """
    import suivi
    base = (S.get("stripe_lien") or "").strip()
    if not base:
        return ""
    ligne = ligne or {}
    tarif = suivi.euros(S.get("tarif"))
    du = suivi.montant_attendu(ligne, S.get("tarif"))
    if abs(du - tarif) < 0.005:
        return base
    _r, code = remise_de(ligne, S.get("tarif"), du)
    if code and du > 0:
        import sessions as _s
        r = trouver(_s.organisme_de(S.get("code") or "") or "", code)
        if r and r.get("stripe"):
            import urllib.parse
            return base + ("&" if "?" in base else "?") + \
                "prefilled_promo_code=" + urllib.parse.quote(code)
    return ""


def publier(organisme):
    """Recopie les codes de l'organisme vers Supabase. Rend (ok, message).

    Le formulaire public ne lit que cette copie. Elle n'emporte que ce qu'il
    faut pour juger un code : ni la note, ni l'auteur.
    """
    import inscription as I
    import urllib.error
    lignes = [{
        "organisme": organisme, "code": r["code"], "type": r.get("type") or "montant",
        "valeur": float(r.get("valeur") or 0), "sessions": r.get("sessions") or [],
        "jusqu_au": r.get("jusqu_au") or None, "max_utilisations": int(r.get("max") or 0),
        "actif": bool(r.get("actif", True)),
        "maj": datetime.now().astimezone().isoformat(timespec="seconds"),
    } for r in lister(organisme)]
    if not lignes:
        return True, "Aucun code à publier."
    try:
        I._sb(TABLE + "?on_conflict=organisme,code", "POST", lignes,
              "resolution=merge-duplicates")
    except urllib.error.HTTPError as e:
        return False, "Supabase : " + e.read().decode("utf-8")[:200]
    except Exception as e:
        return False, str(e)[:200]
    return True, "%d code(s) à jour sur le formulaire." % len(lignes)
