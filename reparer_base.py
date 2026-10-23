"""Reconstruire la base apres une corruption, sans rien perdre et sans rien inventer.

LE DEFAUT DU 23/10/2026. La base s'est retrouvee avec ses INDEX faux : la table
du journal contenait bien ses lignes, mais l'index de la cle primaire pretendait
qu'elles n'existaient pas. Tout DFM s'est mis a repondre « database disk image is
malformed » — ecrans vides, journal non ecrit, miroir bloque. C'etait la deuxieme
fois en trois jours.

LA REGLE DE CETTE REPARATION : on ne repare pas une base abimee, ON EN FABRIQUE
UNE NEUVE A COTE, et on ne remplace rien avant de l'avoir verifiee. Une
reparation en place qui echoue a la moitie laisse un etat dont personne ne sait
plus rien ; un fichier separe, lui, se jette sans consequence.

TROIS SOURCES, chacune pour ce qu'elle sait le mieux :

1. LA SAUVEGARDE DE LA NUIT, pour le journal. C'est le seul endroit ou les
   entrees restent completes : la table abimee, elle, en avait perdu seize.
2. LA BASE ABIMEE, pour les inscrits et l'etat des sessions. Ces deux tables
   restaient lisibles, et elles sont les seules a jour — la sauvegarde ignore
   les inscriptions de la journee.
3. LE CLASSEUR GOOGLE, pour les entrees de journal plus recentes que la
   sauvegarde. Le classeur garde le scelle de chaque ligne : une entree n'est
   RECOPIEE QUE SI SON SCELLE SE RECALCULE A L'IDENTIQUE. C'est tout l'interet
   d'avoir scelle le journal — on peut recoller un morceau en le prouvant.

CE QUI RESTE PERDU est dit en clair a la fin. Une entree de journal qui n'est ni
dans la sauvegarde ni dans le classeur n'existe plus nulle part ; la taire
laisserait croire que la piste d'audit est complete, ce qui serait pire que le
trou lui-meme.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta

DOSSIER = os.path.dirname(os.path.abspath(__file__))
TABLES_A_JOUR = ("suivi", "session_etat")   # les tables reprises de la base abimee
EPOQUE_SHEETS = datetime(1899, 12, 30)      # jour 0 des numeros de date de Google


def _dire(s=""):
    print(s)
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
#  Lire ce que le classeur garde du journal
# --------------------------------------------------------------------------- #

def _depuis_serie(valeur):
    """Rendre a un numero de date Google les trois formats que DFM ecrit.

    Google convertit « 2026-10-22 08:34:56 » en nombre de jours. On refait le
    chemin inverse — et le scelle dira si la reconversion est exacte.
    """
    try:
        d = EPOQUE_SHEETS + timedelta(days=float(valeur))
    except (TypeError, ValueError):
        return None
    if d.microsecond >= 500000:
        d += timedelta(seconds=1)
    d = d.replace(microsecond=0)
    return d


def _candidats(brut, formate):
    """Les ecritures possibles d'une ligne du classeur, la plus probable d'abord.

    Google rend soit le texte tel qu'il a ete ecrit, soit un nombre s'il a cru
    reconnaitre une date. On essaie les deux, plus la reconversion du nombre.
    """
    sorties = []

    def _poser(l):
        l = [("" if v is None else str(v)) for v in l][:9]
        l += [""] * (9 - len(l))
        if l not in sorties:
            sorties.append(l)

    _poser(formate)
    _poser(brut)
    d = _depuis_serie(brut[0] if brut else "")
    if d:
        for base_ligne in (formate, brut):
            l = list(base_ligne) + [""] * 9
            _poser([d.strftime("%Y-%m-%d %H:%M:%S"),
                    d.strftime("%d/%m/%Y"),
                    d.strftime("%H:%M")] + list(l[3:9]))
    return sorties


def _lire_classeur(feuille, premier, dernier):
    """Les lignes `premier`..`dernier` de l'onglet Journal, en brut et en formate."""
    from connexion import service_sheets
    import journal as _journal
    s = service_sheets()
    if not s:
        raise RuntimeError("pas de session Google : impossible de lire le classeur")
    plage = "'%s'!A%d:J%d" % (_journal.ONGLET, premier, dernier)
    lire = lambda rendu: (s.spreadsheets().values()
                          .get(spreadsheetId=feuille, range=plage,
                               valueRenderOption=rendu).execute().get("values", []))
    brut, formate = lire("UNFORMATTED_VALUE"), lire("FORMATTED_VALUE")
    sortie = {}
    for i in range(max(len(brut), len(formate))):
        b = list(brut[i]) if i < len(brut) else []
        f = list(formate[i]) if i < len(formate) else []
        if not b and not f:
            continue
        b += [""] * (10 - len(b))
        f += [""] * (10 - len(f))
        scelle = str(f[9] or b[9] or "").strip()
        if not scelle:
            continue                       # sans scelle, rien a prouver : on laisse
        sortie[premier + i] = (b[:9], f[:9], scelle)
    return sortie


# --------------------------------------------------------------------------- #
#  Fabriquer la base neuve
# --------------------------------------------------------------------------- #

def _colonnes(cx, table, base_attachee="main"):
    # « PRAGMA rec.table_info(suivi) » et non « PRAGMA table_info(rec.suivi) » :
    # le nom de la base attachee se met AVANT le pragma.
    return [r[1] for r in cx.execute("PRAGMA %s.table_info(%s)" % (base_attachee, table))]


def construire(source, recuperee, sortie, avec_classeur=True):
    for f in (source, recuperee):
        if not os.path.exists(f):
            _dire("ARRET : fichier introuvable — %s" % f)
            return None
    if os.path.exists(sortie):
        os.remove(sortie)
    for suffixe in ("-wal", "-shm"):
        if os.path.exists(sortie + suffixe):
            os.remove(sortie + suffixe)

    _dire("1. SOCLE : la sauvegarde %s" % source)
    shutil.copy2(source, sortie)
    cx = sqlite3.connect(sortie)
    cx.execute("PRAGMA journal_mode=DELETE")       # pas de wal pendant le montage
    etat = cx.execute("PRAGMA integrity_check").fetchone()[0]
    if etat != "ok":
        _dire("   ARRET : la sauvegarde elle-meme est abimee (%s)" % etat)
        return None
    _dire("   integrite de la sauvegarde : ok")

    # --- 2. les tables a jour, reprises telles quelles de la base abimee ---
    _dire()
    _dire("2. TABLES A JOUR, reprises de la base abimee")
    cx.execute("ATTACH ? AS rec", (recuperee,))
    for t in TABLES_A_JOUR:
        a, b = _colonnes(cx, t), _colonnes(cx, t, "rec")
        if a != b:
            _dire("   ARRET : la table %s n'a pas les memes colonnes des deux cotes" % t)
            _dire("      sauvegarde : %s" % ", ".join(a))
            _dire("      recuperee  : %s" % ", ".join(b))
            return None
        avant = cx.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
        apres = cx.execute("SELECT COUNT(*) FROM rec.%s" % t).fetchone()[0]
        if apres < avant:
            _dire("   ARRET : %s reculerait de %d a %d lignes — on ne perd pas de lignes"
                  % (t, avant, apres))
            return None
        cx.execute("DELETE FROM %s" % t)
        cx.execute("INSERT INTO %s SELECT * FROM rec.%s" % (t, t))
        _dire("   %-14s %d lignes (la sauvegarde en avait %d)" % (t, apres, avant))

    # --- 3. le journal : la sauvegarde fait foi, et on verifie qu'elle contient
    #        bien tout ce que la base abimee savait encore ---
    _dire()
    _dire("3. JOURNAL : la sauvegarde, completee par le classeur")
    manquantes = cx.execute("""
        SELECT organisme, rang, horodateur, type_action, praticien FROM rec.journal r
         WHERE NOT EXISTS (SELECT 1 FROM journal j
                            WHERE j.organisme = r.organisme AND j.rang = r.rang)
         ORDER BY organisme, rang""").fetchall()
    if manquantes:
        _dire("   ARRET : la base abimee garde %d entrees que la sauvegarde ignore."
              % len(manquantes))
        _dire("   Il faudrait les reprendre une par une — on ne fabrique pas une")
        _dire("   piste d'audit plus courte que celle qui existe.")
        for m in manquantes[:10]:
            _dire("      %s rang %s : %s %s %s" % m)
        return None
    differentes = cx.execute("""
        SELECT COUNT(*) FROM journal j JOIN rec.journal r USING (organisme, rang)
         WHERE j.scelle <> r.scelle OR j.horodateur <> r.horodateur
            OR j.type_action <> r.type_action OR j.praticien <> r.praticien
            OR j.code_session <> r.code_session OR j.detail <> r.detail
            OR j.montant <> r.montant OR j.details <> r.details
            OR j.auteur <> r.auteur""").fetchone()[0]
    if differentes:
        _dire("   ARRET : %d entrees communes racontent deux choses differentes."
              % differentes)
        _dire("   Le journal est scelle : cela ne doit pas arriver. A regarder a la main.")
        return None
    communes = cx.execute("SELECT COUNT(*) FROM journal j JOIN rec.journal r "
                          "USING (organisme, rang)").fetchone()[0]
    _dire("   %d entrees communes aux deux bases, aucune divergence" % communes)
    # Refermer la transaction AVANT de detacher : sqlite refuse de detacher une
    # base encore engagee dans une lecture, et la copie du suivi en a ouvert une.
    cx.commit()
    cx.execute("DETACH rec")

    recolles, perdues = [], []
    if avec_classeur:
        recolles, perdues = _recoller(cx)

    cx.commit()
    cx.close()
    # LE MODE WAL SE POSE SUR UN FICHIER AU REPOS. Le demander sur la connexion
    # qui vient d'ecrire laisse un verrou de table et la bascule echoue : on
    # referme, on rouvre, on bascule, on referme.
    cx = sqlite3.connect(sortie)
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cx.close()
    return {"recolles": recolles, "perdues": perdues}


def _recoller(cx):
    """Completer le journal avec ce que le classeur garde de plus recent."""
    import profil
    import scellement
    recolles, perdues = [], []
    for p in profil.lister():
        ident = p["id"] if isinstance(p, dict) else p
        fiche = profil.charger(ident) or {}
        feuille = fiche.get("sheet_suivi")
        marque = fiche.get("marque") or ident
        if not feuille:
            continue
        dernier = cx.execute("SELECT MAX(rang) FROM journal WHERE organisme=?",
                             (ident,)).fetchone()[0] or 1
        try:
            lignes = _lire_classeur(feuille, dernier + 1, dernier + 200)
        except Exception as e:
            _dire("   %s : classeur illisible (%s) — rien de recolle"
                  % (marque, str(e)[:70]))
            continue
        if not lignes:
            _dire("   %s : le classeur ne va pas plus loin que la base (rang %d)"
                  % (marque, dernier))
            continue
        for rang in sorted(lignes):
            brut, formate, scelle = lignes[rang]
            avant = cx.execute("SELECT scelle FROM journal WHERE organisme=? AND rang=?",
                               (ident, rang - 1)).fetchone()
            if rang == 2:
                precedent = scellement._RACINE
            elif avant is None:
                perdues.append((marque, rang, "le rang precedent manque : "
                                              "la chaine ne peut pas se refermer"))
                break
            else:
                precedent = avant[0] or ""
            trouve = None
            for valeurs in _candidats(brut, formate):
                if scellement.empreinte(rang, valeurs, precedent, "") == scelle:
                    trouve = valeurs
                    break
            if trouve is None:
                perdues.append((marque, rang, "scelle non reproductible : "
                                              "le classeur a ete reformate"))
                break
            cx.execute("INSERT INTO journal (organisme, rang, horodateur, date, heure,"
                       " type_action, praticien, code_session, detail, montant, details,"
                       " scelle, auteur) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'')",
                       tuple([ident, rang] + list(trouve) + [scelle]))
            recolles.append((marque, rang, trouve[0], trouve[3], trouve[4]))
            _dire("   %s rang %d RECOLLE et prouve : %s | %s | %s"
                  % (marque, rang, trouve[0], trouve[3], trouve[4]))
    return recolles, perdues


# --------------------------------------------------------------------------- #
#  Verifier, avant de proposer quoi que ce soit
# --------------------------------------------------------------------------- #

def verifier(fichier, inscrits_attendus=None):
    """Les trois controles qui autorisent le remplacement. Tout ou rien."""
    _dire()
    _dire("4. CONTROLES SUR LE FICHIER NEUF")
    verdicts = []

    cx = sqlite3.connect("file:%s?mode=ro" % fichier, uri=True)
    etat = [r[0] for r in cx.execute("PRAGMA integrity_check")]
    ok1 = etat == ["ok"]
    verdicts.append(("integrite du fichier", ok1, "ok" if ok1 else "; ".join(etat[:4])))

    n = cx.execute("SELECT COUNT(*) FROM suivi").fetchone()[0]
    ok2 = inscrits_attendus is None or n == inscrits_attendus
    verdicts.append(("les inscrits sont la", ok2,
                     "%d inscrits%s" % (n, "" if inscrits_attendus is None
                                        else " (attendu %d)" % inscrits_attendus)))
    for t in ("journal", "session_etat", "miroir_attente"):
        cx.execute("SELECT COUNT(*) FROM %s" % t).fetchone()
    cx.close()

    # La chaine des scelles, recalculee avec la vraie cle de l'installation.
    ok3, detail3 = _chaine(fichier)
    verdicts.append(("chaine des scelles", ok3, detail3))

    for nom, ok, detail in verdicts:
        _dire("   %s %-24s %s" % ("OK  " if ok else "ECHEC", nom, detail))
    return all(ok for _n, ok, _d in verdicts)


def _chaine(fichier):
    """Recalculer la chaine du journal du fichier donne, organisme par organisme."""
    import scellement
    cx = sqlite3.connect("file:%s?mode=ro" % fichier, uri=True)
    cx.row_factory = sqlite3.Row
    champs = ("horodateur", "date", "heure", "type_action", "praticien",
              "code_session", "detail", "montant", "details")
    ruptures, total = [], 0
    orgs = [r[0] for r in cx.execute("SELECT DISTINCT organisme FROM journal "
                                     "ORDER BY organisme")]
    for org in orgs:
        precedent = scellement._RACINE
        attendu_rang = 2
        for l in cx.execute("SELECT * FROM journal WHERE organisme=? ORDER BY rang", (org,)):
            while attendu_rang < l["rang"]:          # trou : le scelle vide fait l'ancetre
                precedent = ""
                attendu_rang += 1
            total += 1
            if not (l["scelle"] or ""):
                precedent = ""
                attendu_rang += 1
                continue
            calcule = scellement.empreinte(l["rang"], [l[c] for c in champs],
                                           precedent, l["auteur"] or "")
            if calcule != l["scelle"]:
                ruptures.append((org, l["rang"]))
            precedent = l["scelle"]
            attendu_rang += 1
    cx.close()
    if ruptures:
        return False, ("%d entrees, %d rupture(s) : %s" %
                       (total, len(ruptures),
                        ", ".join("%s rang %s" % r for r in ruptures[:5])))
    return True, "%d entrees, chaine intacte sur %d organismes" % (total, len(orgs))


def main():
    a = argparse.ArgumentParser(description="Reconstruire la base apres corruption")
    a.add_argument("--sauvegarde", required=True, help="la base saine de depart")
    a.add_argument("--recuperee", required=True,
                   help="ce que « sqlite3 abime.db .recover » a rendu")
    a.add_argument("--sortie", required=True, help="le fichier neuf a fabriquer")
    a.add_argument("--inscrits", type=int, default=None,
                   help="nombre d'inscrits attendu : le controle refuse autre chose")
    a.add_argument("--sans-classeur", action="store_true",
                   help="ne pas aller chercher les entrees recentes dans Google")
    o = a.parse_args()

    _dire("REPARATION DE LA BASE — %s" % datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    _dire()
    bilan = construire(o.sauvegarde, o.recuperee, o.sortie,
                       avec_classeur=not o.sans_classeur)
    if bilan is None:
        _dire()
        _dire("RIEN N'A ETE REMPLACE. Le fichier neuf n'a pas pu etre fabrique.")
        return 1
    if not verifier(o.sortie, o.inscrits):
        _dire()
        _dire("RIEN N'A ETE REMPLACE. Un controle au moins a echoue.")
        return 1

    _dire()
    _dire("5. CE QUI RESTE PERDU")
    if bilan["perdues"]:
        for marque, rang, pourquoi in bilan["perdues"]:
            _dire("   %s, a partir du rang %d : %s" % (marque, rang, pourquoi))
    else:
        _dire("   Aucun trou detecte au-dela de ce que le classeur garde.")
    _dire("   Les entrees ecrites apres la derniere ligne du classeur n'existaient")
    _dire("   que dans la base abimee : elles sont irrecuperables. Le detail de ce")
    _dire("   qu'elles journalisaient est a reconstituer a la main.")
    _dire()
    _dire("FICHIER NEUF PRET : %s" % o.sortie)
    _dire("Il n'a remplace personne. La mise en place est une etape separee.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
