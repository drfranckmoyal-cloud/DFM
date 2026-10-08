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


def _jour(d, avec_mois=True, avec_annee=True):
    t = "%s %d" % (NOMS_JOUR[d.weekday()], d.day)
    if avec_mois:
        t += " " + NOMS_MOIS[d.month]
    if avec_annee:
        t += " %d" % d.year
    return t


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


def resume(fiche):
    """Tout ce dont un document a besoin, depuis une fiche de session.

    Se debrouille avec une fiche ancienne, sans liste : les bornes en tiennent
    lieu, exactement comme elles se lisaient avant.
    """
    liste = normaliser(fiche.get("jours") or [])
    if not liste:
        liste = depuis_bornes(fiche.get("date_debut"), fiche.get("date_fin"))
    d, f = bornes(liste)
    return {"jours": liste, "date_debut": d, "date_fin": f,
            "nb": len(liste), "duree": duree(liste),
            "texte": texte(liste), "detail": detail(liste),
            "contigus": contigus(liste)}
