"""Recherche de doublons dans la base apprenants.

Deux familles, volontairement distinctes parce qu'elles n'appellent pas la
meme action :

  1. MEME MAIL, identites divergentes — c'est le cas deja traite fiche par
     fiche. Une seule personne, plusieurs inscriptions, des informations qui
     ont change entre-temps. La fusion existante s'applique.

  2. MAILS DIFFERENTS, meme personne probable — un praticien inscrit une fois
     avec son adresse professionnelle, une fois avec sa personnelle. Aucune
     fusion automatique n'est possible : deux adresses sont deux identites du
     point de vue du suivi. On signale, l'utilisateur tranche.

CRITERES DE RAPPROCHEMENT, choisis pour signaler peu mais juste :

  - « telephone » : meme numero (chiffres seuls, au moins 8) ET meme nom de
    famille. Deux personnes distinctes partagent rarement les deux. Quasi sur.
  - « identite » : meme nom ET meme prenom, normalises (casse, accents,
    tirets, espaces multiples). Fort, mais des homonymes existent — d'ou la
    possibilite d'ecarter durablement un rapprochement.

Ecarte volontairement : la proximite orthographique (Levenshtein et
consorts). Sur des noms propres francais, elle rapproche « Martin » et
« Martine », « Bernard » et « Benard » — beaucoup de bruit pour peu de
trouvailles, et c'est exactement ce que l'utilisateur ne veut pas.

Les rapprochements ecartes sont memorises localement et ne sont plus jamais
resignales.
"""
import json
import os
import re
import unicodedata
from datetime import datetime

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
_ECARTES = os.path.join(_DOSSIER, "doublons_ecartes.json")


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------
def plat(valeur):
    """Casse, accents, tirets et espaces multiples effaces."""
    s = unicodedata.normalize("NFD", str(valeur or "")).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return " ".join(s.split())


def telephone(valeur):
    """Chiffres seuls. Rend "" si moins de 8 chiffres — un numero tronque ou
    un « 0600000000 » de test ne doit pas rapprocher des inconnus."""
    n = re.sub(r"\D", "", str(valeur or ""))
    if len(n) < 8:
        return ""
    # Un numero visiblement bidon ne rapproche personne.
    if len(set(n)) <= 2:
        return ""
    return n[-9:]          # on ignore l'indicatif : 0612345678 == +33612345678


# --------------------------------------------------------------------------
# Rapprochements ecartes
# --------------------------------------------------------------------------
def _cle_paire(mail_a, mail_b):
    return "|".join(sorted([(mail_a or "").strip().lower(), (mail_b or "").strip().lower()]))


def ecartes():
    try:
        with open(_ECARTES, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def ecarter(mail_a, mail_b, motif=""):
    import fichiers
    with fichiers.modifier(_ECARTES, {}) as d:
        d[_cle_paire(mail_a, mail_b)] = {
            "quand": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "mails": sorted([mail_a, mail_b]),
            "motif": motif,
        }
    return True


def reprendre(mail_a, mail_b):
    """Remet un rapprochement dans le circuit — si l'on s'est trompe."""
    import fichiers
    c = _cle_paire(mail_a, mail_b)
    with fichiers.modifier(_ECARTES, {}) as d:
        if c not in d:
            return False
        del d[c]
    return True


def est_ecarte(mail_a, mail_b):
    return _cle_paire(mail_a, mail_b) in ecartes()


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
def _identite_recente(lignes):
    """L'identite la plus recente parmi les inscriptions d'un meme mail."""
    ref = {}
    for l in lignes:
        if not ref or (l.get("horodateur") or "") > ref.get("_h", ""):
            ref = {"nom": (l.get("nom") or "").strip(),
                   "prenom": (l.get("prenom") or "").strip(),
                   "telephone": (l.get("telephone") or "").strip(),
                   "ville": (l.get("ville") or "").strip(),
                   "_h": l.get("horodateur") or ""}
    return ref


def chercher(toutes_lignes):
    """toutes_lignes : liste de dicts, chacun avec au moins mail, nom, prenom,
    telephone, ville, horodateur, et _session (code) pour l'affichage.

    Rend {"meme_mail": [...], "personnes": [...], "ecartes": n}
    """
    par_mail = {}
    for l in toutes_lignes:
        m = (l.get("mail") or "").strip().lower()
        if not m:
            continue
        par_mail.setdefault(m, []).append(l)

    # ---- 1. meme mail, identites divergentes -----------------------------
    meme_mail = []
    for m, lignes in par_mail.items():
        if len(lignes) < 2:
            continue
        divergences = []
        for cle, libelle in (("nom", "Nom"), ("prenom", "Prénom"),
                             ("telephone", "Téléphone"), ("ville", "Ville")):
            valeurs = sorted({(l.get(cle) or "").strip() for l in lignes
                              if (l.get(cle) or "").strip()})
            if len(valeurs) > 1:
                divergences.append({"cle": cle, "libelle": libelle, "valeurs": valeurs})
        if not divergences:
            continue
        ref = _identite_recente(lignes)
        meme_mail.append({
            "mail": m,
            "nom": (ref.get("prenom", "") + " " + ref.get("nom", "")).strip() or m,
            "nb_fiches": len(lignes),
            "divergences": divergences,
            "sessions": sorted({l.get("_session") or "" for l in lignes if l.get("_session")}),
        })
    meme_mail.sort(key=lambda x: (-len(x["divergences"]), x["nom"]))

    # ---- 2. mails differents, meme personne probable ----------------------
    # Une entree par MAIL, avec son identite la plus recente.
    fiches = []
    for m, lignes in par_mail.items():
        ref = _identite_recente(lignes)
        fiches.append({
            "mail": m, "nom": ref.get("nom", ""), "prenom": ref.get("prenom", ""),
            "telephone": ref.get("telephone", ""), "ville": ref.get("ville", ""),
            "nb_inscriptions": len(lignes),
            "sessions": sorted({l.get("_session") or "" for l in lignes if l.get("_session")}),
        })

    personnes, vus = [], set()
    n_ecartes = 0
    for i, a in enumerate(fiches):
        for b in fiches[i + 1:]:
            if a["mail"] == b["mail"]:
                continue
            na, nb = plat(a["nom"]), plat(b["nom"])
            pa, pb = plat(a["prenom"]), plat(b["prenom"])
            ta, tb = telephone(a["telephone"]), telephone(b["telephone"])
            motif, force = None, 0
            if ta and ta == tb and na and na == nb:
                motif, force = "telephone", 2
            elif na and na == nb and pa and pa == pb:
                motif, force = "identite", 1
            if not motif:
                continue
            if est_ecarte(a["mail"], b["mail"]):
                n_ecartes += 1
                continue
            cle = _cle_paire(a["mail"], b["mail"])
            if cle in vus:
                continue
            vus.add(cle)
            ecarts = []
            for c, lib in (("nom", "Nom"), ("prenom", "Prénom"),
                           ("telephone", "Téléphone"), ("ville", "Ville")):
                va, vb = (a.get(c) or "").strip(), (b.get(c) or "").strip()
                if va != vb:
                    ecarts.append({"libelle": lib, "a": va or "—", "b": vb or "—"})
            personnes.append({
                "motif": motif,
                "certitude": "quasi certain" if force == 2 else "à vérifier",
                "force": force,
                "explication": ("Même numéro de téléphone et même nom de famille."
                                if force == 2 else
                                "Mêmes nom et prénom, mais rien d'autre ne le confirme — "
                                "deux confrères peuvent être homonymes."),
                "a": a, "b": b, "ecarts": ecarts,
            })
    personnes.sort(key=lambda x: (-x["force"], x["a"]["nom"]))
    return {"meme_mail": meme_mail, "personnes": personnes, "ecartes": n_ecartes}


# --------------------------------------------------------------------------
# La base de contacts
# --------------------------------------------------------------------------
# La version ci-dessus travaille sur les INSCRIPTIONS du classeur : plusieurs
# lignes par personne, rapprochees par leur adresse. La base de contacts est
# d'une autre nature — une ligne par personne, et un nom qui n'est plus
# decoupe en nom et prenom depuis que l'on enregistre la saisie telle quelle.
#
# TROIS DEGRES, et le troisieme est un simple signalement :
#   force 3 — meme adresse mail. Certain : c'est la meme boite.
#   force 2 — meme telephone ET noms proches. Quasi certain.
#   force 1 — meme nom complet, rien d'autre. A VERIFIER : deux confreres
#             peuvent etre homonymes. C'est le degre que l'utilisateur a
#             demande de conserver comme signalement, pour trancher au cas
#             par cas — jamais pour fusionner tout seul.
def nom_complet(fiche):
    """« Bitton » + « Aaron » -> « aaron bitton ». L'ordre est neutralise :
    depuis qu'on enregistre la saisie telle quelle, « Aaron Bitton » et
    « Bitton Aaron » designent la meme personne et doivent se rapprocher."""
    brut = ((fiche.get("prenom") or "") + " " + (fiche.get("nom") or "")).strip()
    mots = plat(brut).split()
    return " ".join(sorted(mots))


def chercher_contacts(fiches):
    """fiches : les enregistrements de la base de contacts.
    Rend {"paires": [...], "ecartes": n}."""
    par_mail, par_tel, par_nom = {}, {}, {}
    for f in fiches:
        m = (f.get("mail_norm") or "").strip()
        t = (f.get("tel_norm") or "").strip()
        n = nom_complet(f)
        if m:
            par_mail.setdefault(m, []).append(f)
        if t:
            par_tel.setdefault(t, []).append(f)
        if n:
            par_nom.setdefault(n, []).append(f)

    trouvees, vus, n_ecartes = [], set(), 0

    def poser(a, b, force, motif, explication):
        cle = _cle_paire(a.get("mail") or str(a["id"]), b.get("mail") or str(b["id"]))
        if cle in vus:
            return
        if est_ecarte(a.get("mail") or str(a["id"]), b.get("mail") or str(b["id"])):
            return "ecarte"
        vus.add(cle)
        ecarts = []
        for c, lib in (("nom", "Nom"), ("prenom", "Prénom"), ("mail", "Adresse"),
                       ("telephone", "Téléphone"), ("ville", "Ville")):
            va, vb = (a.get(c) or "").strip(), (b.get(c) or "").strip()
            if va != vb:
                ecarts.append({"libelle": lib, "a": va or "—", "b": vb or "—"})
        trouvees.append({"a": a, "b": b, "force": force, "motif": motif,
                         "certitude": {3: "certain", 2: "quasi certain", 1: "à vérifier"}[force],
                         "explication": explication, "ecarts": ecarts})

    for groupe in par_mail.values():
        for i, a in enumerate(groupe):
            for b in groupe[i + 1:]:
                if poser(a, b, 3, "mail", "Même adresse mail : c'est la même boîte.") == "ecarte":
                    n_ecartes += 1
    for groupe in par_tel.values():
        for i, a in enumerate(groupe):
            for b in groupe[i + 1:]:
                if (a.get("mail_norm") or "") == (b.get("mail_norm") or "") and a.get("mail_norm"):
                    continue                      # deja signale par l'adresse
                proche = nom_complet(a) and nom_complet(a) == nom_complet(b)
                if poser(a, b, 2 if proche else 1, "telephone",
                         "Même numéro de téléphone" + (" et même nom." if proche else
                                                       ", mais des noms différents.")) == "ecarte":
                    n_ecartes += 1
    for groupe in par_nom.values():
        for i, a in enumerate(groupe):
            for b in groupe[i + 1:]:
                if poser(a, b, 1, "nom",
                         "Mêmes nom et prénom, rien d'autre ne le confirme — "
                         "deux confrères peuvent être homonymes.") == "ecarte":
                    n_ecartes += 1

    trouvees.sort(key=lambda x: (-x["force"], nom_complet(x["a"])))
    return {"paires": trouvees, "ecartes": n_ecartes}
