"""Les journees d'une formation, et la maniere de les ecrire.

POURQUOI CE MODULE EXISTE. DFM ne connaissait qu'une date de debut et une date
de fin, reliees par « et » : « lundi 10 et mardi 25 aout 2026 ». Juste pour une
formation de deux jours, faux pour tout le reste — cette phrase annonce deux
journees la ou il y en a peut-etre cinq, dispersees sur trois semaines.

Le defaut n'etait pas que d'affichage. Sans liste de journees, la feuille
d'emargement imprimait une plage continue, et rien ne pouvait dire combien de
jours de formation avaient reellement eu lieu.

TROIS INFORMATIONS, ET ELLES NE DISENT PAS LA MEME CHOSE :

  date_debut / date_fin  Les bornes de l'action. Elles figurent SEPAREMENT sur
                         la convention : un OPCO les lit comme deux champs, et
                         accepte qu'elles soient distantes de six mois.
  jours                  Les journees reellement travaillees, entre ces bornes.
  duree                  7 heures par journee, quels que soient les horaires.

LES BORNES SUIVENT LA LISTE, elles ne se saisissent pas. Un champ librement
modifiable a cote d'une liste finit toujours par la contredire, et c'est
exactement l'ecart qu'un financeur releve.

LE DIMANCHE N'EST JAMAIS PRE-COCHE. Le samedi si : des formations s'y tiennent.
"""
from datetime import date, datetime, timedelta

NOMS_JOUR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
NOMS_MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

# Duree d'une journee de formation, en heures. Reglage plutot que litteral :
# ce nombre apparait sur des conventions, et une formation a 6 h ou 8 h ne doit
# pas demander de toucher au code.
HEURES_DEFAUT = 7


def heures_par_jour():
    try:
        import parametres
        v = parametres.valeur("heures_par_jour", HEURES_DEFAUT)
        return float(str(v).replace(",", ".")) if str(v).strip() else HEURES_DEFAUT
    except Exception:
        return HEURES_DEFAUT


def _d(valeur):
    """Une date, quelle que soit la forme recue. None si illisible."""
    if isinstance(valeur, date) and not isinstance(valeur, datetime):
        return valeur
    if isinstance(valeur, datetime):
        return valeur.date()
    t = str(valeur or "").strip()[:10]
    for forme in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, forme).date()
        except ValueError:
            continue
    return None


def normaliser(liste):
    """Des dates ISO, triees, sans doublon, sans valeur illisible."""
    vues, sortie = set(), []
    for x in (liste or []):
        d = _d(x)
        if d and d.isoformat() not in vues:
            vues.add(d.isoformat())
            sortie.append(d)
    return [d.isoformat() for d in sorted(sortie)]


def periode(debut, fin, sans_dimanche=True):
    """Toutes les journees entre deux bornes, dimanche exclu par defaut.

    Sert a proposer une pre-selection, jamais a decider : l'utilisateur retire
    ce qui n'est pas travaille.
    """
    a, b = _d(debut), _d(fin)
    if not a:
        return []
    if not b or b < a:
        b = a
    sortie, courant = [], a
    while courant <= b:
        if not (sans_dimanche and courant.weekday() == 6):
            sortie.append(courant.isoformat())
        courant += timedelta(days=1)
    return sortie


def depuis_bornes(debut, fin):
    """La liste d'une session ecrite avant l'existence de ce module.

    DEUX JOURNEES, PAS UNE PLAGE. Les sessions existantes ont ete saisies avec
    la logique « debut et fin », qui decrivait deux journees reliees par « et ».
    Les relire comme une plage continue changerait retroactivement leur sens —
    et le nombre d'heures inscrit sur des attestations deja emises.
    """
    a, b = _d(debut), _d(fin)
    if not a:
        return []
    if not b or b == a:
        return [a.isoformat()]
    return [a.isoformat(), b.isoformat()]


def bornes(liste):
    """(premier, dernier) de la liste. ("", "") si elle est vide."""
    j = normaliser(liste)
    return (j[0], j[-1]) if j else ("", "")


def duree(liste, heures=None):
    """Le total en heures. Un entier quand c'est un entier."""
    h = heures_par_jour() if heures is None else float(heures)
    t = len(normaliser(liste)) * h
    return int(t) if float(t).is_integer() else t


def contigus(liste):
    """Les journees se suivent-elles jour apres jour, dimanches compris ?"""
    j = [_d(x) for x in normaliser(liste)]
    if len(j) < 2:
        return True
    return all((j[i + 1] - j[i]).days == 1 for i in range(len(j) - 1))


def blocs(liste):
    """Les journees regroupees en blocs de jours qui se suivent.

    POURQUOI CE REGROUPEMENT — 24/10/2026, avec le cycle Esthetique 360. Une
    formation de deux jours n'a qu'un bloc, et le module n'avait pas besoin de
    la notion. Un cycle annuel, lui, est fait de cinq blocs de trois jours
    separes par deux mois : sans regroupement, « les mercredi 6, jeudi 7,
    vendredi 8 janvier, mercredi 10… » enumere quinze dates d'affilee, et plus
    personne ne voit les cinq modules.

    Le dimanche ne coupe pas un bloc : il n'est jamais travaille, mais un
    samedi et un lundi encadrant un dimanche font bien une seule venue.
    """
    j = [_d(x) for x in normaliser(liste)]
    if not j:
        return []
    sortie = [[j[0]]]
    for precedent, suivant in zip(j, j[1:]):
        ecart = (suivant - precedent).days
        if ecart == 1 or (ecart == 2 and (precedent + timedelta(days=1)).weekday() == 6):
            sortie[-1].append(suivant)
        else:
            sortie.append([suivant])
    return sortie


def _jour(d, avec_mois=True, avec_annee=True):
    # « 1er » ET NON « 1 » — 24/10/2026. Le francais l'exige pour le premier du
    # mois, et ces phrases s'impriment sur des conventions. Aucune session en
    # service ne tombe un premier, la correction ne reecrit donc rien.
    numero = "1er" if d.day == 1 else str(d.day)
    t = "%s %s" % (NOMS_JOUR[d.weekday()], numero)
    if avec_mois:
        t += " " + NOMS_MOIS[d.month]
    if avec_annee:
        t += " %d" % d.year
    return t


def _bloc_texte(bloc, avec_annee=True):
    """La phrase d'UN bloc : « du mercredi 6 au vendredi 8 janvier 2027 »."""
    if not bloc:
        return ""
    if len(bloc) == 1:
        return _jour(bloc[0], avec_annee=avec_annee)
    meme_mois = len({(d.year, d.month) for d in bloc}) == 1
    premier = _jour(bloc[0], avec_mois=not meme_mois,
                    avec_annee=(not meme_mois) and avec_annee)
    dernier = _jour(bloc[-1], avec_annee=avec_annee)
    if len(bloc) == 2:
        return "%s et %s" % (premier, dernier)
    return "du %s au %s" % (premier, dernier)


def texte(liste):
    """La phrase des dates, telle qu'elle part dans un mail ou une convention.

      1 jour            vendredi 15 août 2026
      2 jours           mercredi 4 et jeudi 5 novembre 2026
      3+ contigus       du lundi 10 au vendredi 14 août 2026
      3+ disperses      les vendredi 15, samedi 16 et mercredi 22 août 2026

    Le mois et l'annee ne se repetent que s'ils changent : « les vendredi 15,
    samedi 16 et mercredi 22 aout 2026 » se lit, « les vendredi 15 aout 2026,
    samedi 16 aout 2026 et… » non.
    """
    j = [_d(x) for x in normaliser(liste)]
    if not j:
        return ""
    if len(j) == 1:
        return _jour(j[0])

    # PLUSIEURS VENUES : on enonce les blocs, pas les journees — 24/10/2026.
    # Quinze journees enumerees une a une ne se lisent pas. Ce chemin ne peut
    # pas toucher une session existante : il demande AU MOINS DEUX BLOCS et au
    # moins trois journees, et aucune des sessions en service n'a plus de deux
    # journees, toutes contigues.
    groupes = blocs(j)
    if len(groupes) >= 2 and len(j) >= 3:
        meme_annee_g = len({d.year for d in j}) == 1
        morceaux = [_bloc_texte(b, avec_annee=not meme_annee_g) for b in groupes]
        if meme_annee_g:
            morceaux[-1] = _bloc_texte(groupes[-1], avec_annee=True)
        if len(morceaux) == 2:
            return "%s et %s" % (morceaux[0], morceaux[1])
        return "%s et %s" % (", ".join(morceaux[:-1]), morceaux[-1])

    meme_mois = len({(d.year, d.month) for d in j}) == 1
    meme_annee = len({d.year for d in j}) == 1

    if len(j) == 2:
        if meme_mois:
            return "%s et %s" % (_jour(j[0], avec_mois=False, avec_annee=False), _jour(j[1]))
        if meme_annee:
            return "%s et %s" % (_jour(j[0], avec_annee=False), _jour(j[1]))
        return "%s et %s" % (_jour(j[0]), _jour(j[1]))

    if contigus(j):
        if meme_mois:
            return "du %s au %s" % (_jour(j[0], avec_mois=False, avec_annee=False), _jour(j[-1]))
        if meme_annee:
            return "du %s au %s" % (_jour(j[0], avec_annee=False), _jour(j[-1]))
        return "du %s au %s" % (_jour(j[0]), _jour(j[-1]))

    if meme_mois:
        morceaux = [_jour(d, avec_mois=False, avec_annee=False) for d in j[:-1]]
        return "les %s et %s" % (", ".join(morceaux), _jour(j[-1]))
    if meme_annee:
        morceaux = [_jour(d, avec_annee=False) for d in j[:-1]]
        return "les %s et %s" % (", ".join(morceaux), _jour(j[-1]))
    morceaux = [_jour(d) for d in j[:-1]]
    return "les %s et %s" % (", ".join(morceaux), _jour(j[-1]))


def detail(liste, heures=None):
    """Une ligne par journee, avec sa duree — ce que reclame un financeur.

        vendredi 15 août 2026 (7 heures)
        samedi 16 août 2026 (7 heures)
    """
    h = heures_par_jour() if heures is None else float(heures)
    mot = int(h) if float(h).is_integer() else h
    return ["%s (%s heures)" % (_jour(d), mot) for d in (_d(x) for x in normaliser(liste))]


def detail_texte(liste, heures=None, separateur="\n"):
    return separateur.join(detail(liste, heures))


# ---------------------------------------------------------------------------
# LES MODULES D'UN CYCLE
#
# POURQUOI — 24/10/2026, avec Esthetique 360. Une formation de deux jours se
# saisit en deux dates. Un cycle annuel compte cinq modules de trois jours
# repartis sur l'annee : l'ecran proposait une case a cocher par jour entre la
# premiere et la derniere date, soit TROIS CENT TRENTE CASES. Inutilisable.
#
# LA FORMATION DIT LA FORME, LA SESSION DIT LES DATES. La fiche de formation
# porte « Essentiels | 3 » : cinq intitules et leur nombre de journees. La
# session ne fournit donc qu'UNE DATE PAR MODULE — son premier jour — et DFM en
# deduit les journees. Cinq champs au lieu de trois cent trente cases.
#
# LES JOURNEES RESOLUES SE RANGENT DANS LA SESSION, pas seulement les dates de
# depart. Renommer un module de la formation, ou en changer la duree, ne doit
# pas reecrire apres coup une session dont la convocation est partie : ce qui a
# ete annonce aux inscrits reste ce qui est ecrit.
# ---------------------------------------------------------------------------

def _suite_ouvree(depart, nombre):
    """`nombre` journees a partir de `depart`, le dimanche passe sans compter."""
    d = _d(depart)
    if not d or nombre < 1:
        return []
    sortie = []
    while len(sortie) < nombre:
        if d.weekday() != 6:
            sortie.append(d.isoformat())
        d += timedelta(days=1)
    return sortie


def depuis_modules(modules, departs):
    """Les journees d'un cycle, depuis la forme des modules et leurs departs.

    `modules` vient de la fiche de formation : [{"titre", "jours"}, ...].
    `departs` est la date du premier jour de chaque module, dans le meme ordre ;
    un depart vide laisse le module sans date, ce qui est le cas normal d'une
    session en cours de saisie.

    Rend {"jours": liste plate, "modules": modules resolus, "manquants": n}.
    """
    resolus, plates, manquants = [], [], 0
    for i, m in enumerate(modules or []):
        titre = str((m or {}).get("titre") or "").strip() or "Module %d" % (i + 1)
        try:
            nombre = int((m or {}).get("jours") or 0)
        except (TypeError, ValueError):
            nombre = 0
        depart = (departs[i] if i < len(departs or []) else "") or ""
        js = _suite_ouvree(depart, nombre) if str(depart).strip() else []
        if not js:
            manquants += 1
        resolus.append({"numero": i + 1, "titre": titre, "jours": js,
                        "nb": len(js), "texte": _bloc_texte([_d(x) for x in js])})
        plates += js
    return {"jours": normaliser(plates), "modules": resolus, "manquants": manquants}


def modules_depuis_jours(liste, modules):
    """Apparier les blocs d'une liste de journees avec les intitules des modules.

    Sert quand une session porte deja ses journees sans ses modules resolus —
    une session ancienne, ou une liste reprise a la main. On apparie dans
    l'ordre, et on dit si les comptes ne tombent pas juste plutot que de
    renommer un bloc au hasard.
    """
    groupes = blocs(liste)
    titres = [str((m or {}).get("titre") or "").strip() for m in (modules or [])]
    sortie = []
    for i, b in enumerate(groupes):
        titre = titres[i] if i < len(titres) else ""
        sortie.append({"numero": i + 1, "titre": titre or "Module %d" % (i + 1),
                       "jours": [d.isoformat() for d in b], "nb": len(b),
                       "texte": _bloc_texte(b)})
    souci = ""
    if titres and len(groupes) != len(titres):
        souci = ("la session compte %d venue(s) et la formation %d module(s)"
                 % (len(groupes), len(titres)))
    return {"modules": sortie, "souci": souci}


def texte_modules(resolus, numeroter=True):
    """La liste des modules telle qu'elle part dans un courriel.

        1 · Essentiels — du mercredi 6 au vendredi 8 janvier 2027
        2 · Composites — du mercredi 10 au vendredi 12 mars 2027

    Un module sans date est annonce comme tel : mieux vaut « dates a venir »
    qu'une ligne muette qui laisse croire a un oubli de mise en page.
    """
    lignes = []
    for m in resolus or []:
        tete = ("%d · %s" % (m.get("numero") or 0, m.get("titre") or "")) if numeroter \
            else (m.get("titre") or "")
        lignes.append("%s — %s" % (tete, m.get("texte") or "dates à venir"))
    return "\n".join(lignes)


_LETTRES = ["zéro", "une", "deux", "trois", "quatre", "cinq", "six", "sept",
            "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze",
            "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf", "vingt"]


def en_lettres(n):
    """Un nombre de journees, en toutes lettres : 15 -> « quinze ».

    LE FEMININ, parce que le mot compte est TOUJOURS « journee » ici : on écrit
    « une journée » et « vingt et une journées », jamais « un journée ».
    Au-dela de trente, le chiffre se lit mieux que la lettre — aucune formation
    ne dure si longtemps, et une regle qui s'arrete est plus sure qu'une regle
    qui improvise.
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n < 0 or n > 30:
        return str(n)
    if n <= 20:
        return _LETTRES[n]
    if n == 21:
        return "vingt et une"
    if n == 30:
        return "trente"
    return "vingt-" + _LETTRES[n - 20]


def resume(fiche):
    """Tout ce dont un document a besoin, depuis une fiche de session.

    Se debrouille avec une fiche ancienne, sans liste : les bornes en tiennent
    lieu, exactement comme elles se lisaient avant.
    """
    liste = normaliser(fiche.get("jours") or [])
    if not liste:
        liste = depuis_bornes(fiche.get("date_debut"), fiche.get("date_fin"))
    d, f = bornes(liste)
    # LES MODULES RESOLUS DE LA SESSION, s'ils y ont ete ranges. On ne les
    # recalcule pas depuis la formation : voir le commentaire des modules.
    mods = [m for m in (fiche.get("modules") or []) if (m or {}).get("jours")]
    return {"jours": liste, "date_debut": d, "date_fin": f,
            "nb": len(liste), "duree": duree(liste),
            "texte": texte(liste), "detail": detail(liste),
            "contigus": contigus(liste),
            "blocs": [[x.isoformat() for x in b] for b in blocs(liste)],
            "modules": mods,
            "modules_texte": texte_modules(mods) if mods else ""}
