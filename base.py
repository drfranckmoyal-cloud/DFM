"""La base locale de DFM. Une porte, pas un fichier.

POURQUOI CE MODULE EXISTE. Les donnees vivantes de DFM — le journal, l'etat des
sessions, le suivi des inscrits — vivaient dans des classeurs Google. Chaque
lecture etait un appel reseau, chaque ecriture aussi, et une panne de Google
arretait le logiciel. Trois mille lignes de journal se lisaient cellule par
cellule.

CE MODULE EST UNE PORTE, comme documents.py. L'appelant demande « le journal de
cet organisme » ou « ajoute cette entree » ; il n'apprend jamais que c'est du
SQLite. Le jour ou DFM passe en ligne, SEUL CE FICHIER change — la base devient
distante et les appelants ne bougent pas. C'est la meme promesse, tenue au meme
endroit.

POURQUOI SQLITE ET PAS DU JSON. Le journal fait plus de cinq mille lignes et ne
fait que grossir : chaque ajout reecrirait le fichier entier. Le serveur est
multi-taches, donc deux ecritures peuvent se croiser. Et SQLite vers une base
en ligne est un chemin balise, ce que le passage en SaaS demandera. Rien a
installer : c'est dans Python.

LE CLASSEUR GOOGLE RESTE TENU A JOUR, en miroir. DFM n'y lit plus, mais continue
d'y ecrire : l'habitude d'ouvrir le classeur est conservee, et un defaut apres
bascule se rattrape. Le miroir se coupe d'un reglage, pas d'une reecriture.
"""
import os
import sqlite3
import threading

_DOSSIER = os.path.dirname(os.path.abspath(__file__))
CHEMIN = os.path.join(_DOSSIER, "dfm.db")

# UNE CONNEXION PAR FIL D'EXECUTION. sqlite3 refuse qu'un objet de connexion
# traverse les threads, et Flask en lance un par requete. Les partager avec
# check_same_thread=False marcherait mais melangerait les transactions de deux
# requetes simultanees — un bug invisible jusqu'au jour ou il ne l'est plus.
_LOCAL = threading.local()
_SCHEMA_POSE = threading.Event()
_VERROU_SCHEMA = threading.Lock()

SCHEMA = """
-- LE JOURNAL. Le RANG est conserve tel quel depuis le classeur : le scelle de
-- chaque ligne se calcule sur son rang, et le renumeroter invaliderait toute
-- la chaine. Migrer une piste d'audit ne doit pas la casser.
--
-- La cle porte l'ORGANISME : chaque entite a son classeur, donc sa propre
-- chaine de scelles. Les melanger reviendrait a joindre deux comptabilites.
CREATE TABLE IF NOT EXISTS journal (
    organisme    TEXT NOT NULL,
    rang         INTEGER NOT NULL,
    horodateur   TEXT NOT NULL DEFAULT '',
    date         TEXT NOT NULL DEFAULT '',
    heure        TEXT NOT NULL DEFAULT '',
    type_action  TEXT NOT NULL DEFAULT '',
    praticien    TEXT NOT NULL DEFAULT '',
    code_session TEXT NOT NULL DEFAULT '',
    detail       TEXT NOT NULL DEFAULT '',
    montant      TEXT NOT NULL DEFAULT '',
    details      TEXT NOT NULL DEFAULT '',
    scelle       TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (organisme, rang)
);
CREATE INDEX IF NOT EXISTS journal_session ON journal (organisme, code_session);
CREATE INDEX IF NOT EXISTS journal_ordre   ON journal (organisme, rang DESC);

-- L'ETAT DE VIE DES SESSIONS. Une session etait coupee en deux : sa
-- CONFIGURATION dans sessions.json — code, dates, tarif, identifiants — et son
-- ETAT dans un onglet Google. Deux moities du meme objet dans deux magasins,
-- d'ou une vingtaine d'endroits qui lisaient tout l'onglet pour retrouver une
-- ligne par son code et modifier une cellule.
--
-- SEUL L'ETAT EST ICI. Le nom de la formation, les dates et le nombre de places
-- restent dans sessions.json : les recopier ferait deux verites, et c'est
-- exactement ce qu'on est en train de defaire. Le miroir Google les recompose
-- au moment d'ecrire.
CREATE TABLE IF NOT EXISTS session_etat (
    organisme             TEXT NOT NULL,
    code_session          TEXT NOT NULL,
    statut_session        TEXT NOT NULL DEFAULT '',
    cloture_le            TEXT NOT NULL DEFAULT '',
    emargement_genere_le  TEXT NOT NULL DEFAULT '',
    lien_emargement       TEXT NOT NULL DEFAULT '',
    emargement_signe_le   TEXT NOT NULL DEFAULT '',
    lien_emargement_signe TEXT NOT NULL DEFAULT '',
    terminee_le           TEXT NOT NULL DEFAULT '',
    report_le             TEXT NOT NULL DEFAULT '',
    alerte_cloture_le     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (organisme, code_session)
);
"""

# Les colonnes d'etat, dans l'ordre ou elles apparaissent dans l'onglet Google.
CHAMPS_ETAT = ("statut_session", "cloture_le", "emargement_genere_le",
               "lien_emargement", "emargement_signe_le", "lien_emargement_signe",
               "terminee_le", "report_le", "alerte_cloture_le")

SCHEMA_SUIVI = """
-- LE SUIVI DES INSCRITS. Une ligne par personne et par session.
--
-- LE CONTENU EST UN OBJET JSON, PAS CINQUANTE COLONNES. C'est un choix, et il
-- se discute. Cinquante colonnes seraient plus verifiables — une faute de frappe
-- sur un nom de champ echouerait tout de suite. Mais la liste des champs est
-- deja definie une fois, dans suivi.COL, et elle BOUGE : « fonction » a ete
-- ajoutee le 03/08/2026, et ajouter_colonnes.py existe pour ca. La recopier ici
-- ferait deux definitions a tenir d'accord, et la premiere divergence passerait
-- inapercue. Le garde-fou est donc dans suivi.py, qui refuse un champ absent
-- de COL avant d'ecrire.
--
-- LE NUMERO EST CELUI DE LA LIGNE DANS L'ONGLET, conserve. Il circule partout
-- sous le nom « _numero » et sert de cle a suivi.ecrire ; le renumeroter
-- casserait tout ce qui le detient deja.
CREATE TABLE IF NOT EXISTS suivi (
    organisme    TEXT NOT NULL,
    code_session TEXT NOT NULL,
    numero       INTEGER NOT NULL,
    donnees      TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (organisme, code_session, numero)
);
CREATE INDEX IF NOT EXISTS suivi_session ON suivi (organisme, code_session, numero);
"""


def _conn():
    """La connexion de ce fil. Ouvre la base et pose le schema au besoin."""
    c = getattr(_LOCAL, "conn", None)
    if c is not None:
        return c
    c = sqlite3.connect(CHEMIN, timeout=15)
    c.row_factory = sqlite3.Row
    # WAL : un lecteur ne bloque pas un ecrivain. Sans lui, afficher le journal
    # pendant un envoi groupe rendrait « database is locked ».
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    # NORMAL et non FULL : on accepte de perdre la toute derniere transaction
    # si la machine s'eteint brutalement, en echange d'ecritures dix fois plus
    # rapides. Le classeur Google, tenu en miroir, rattrape ce cas.
    c.execute("PRAGMA synchronous=NORMAL")
    _LOCAL.conn = c
    if not _SCHEMA_POSE.is_set():
        with _VERROU_SCHEMA:
            if not _SCHEMA_POSE.is_set():
                c.executescript(SCHEMA)
                c.executescript(SCHEMA_SUIVI)
                c.commit()
                _SCHEMA_POSE.set()
    return c


def fermer():
    """Ferme la connexion de ce fil. Utile aux scripts, inutile au serveur."""
    c = getattr(_LOCAL, "conn", None)
    if c is not None:
        c.close()
        _LOCAL.conn = None


# --------------------------------------------------------------------------
# LE JOURNAL
# --------------------------------------------------------------------------

CHAMPS_JOURNAL = ("horodateur", "date", "heure", "type_action", "praticien",
                  "code_session", "detail", "montant", "details", "scelle")


def journal_ajouter(organisme, valeurs, rang=None, scelle=""):
    """Ajoute une entree et rend son rang.

    `valeurs` est la ligne telle qu'elle part aussi dans le classeur : neuf
    colonnes, dans l'ordre. Le scelle se pose apres, quand il est calcule.

    LE RANG SUIT CELUI DU CLASSEUR. On ne le laisse pas a SQLite : la premiere
    ligne de donnees est le rang 2, parce que le rang 1 est l'en-tete de la
    feuille. Ce decalage n'est pas cosmetique — il entre dans le calcul du
    scelle, et le perdre invaliderait la chaine.
    """
    c = _conn()
    if rang is None:
        r = c.execute("SELECT MAX(rang) FROM journal WHERE organisme=?",
                      (organisme,)).fetchone()[0]
        rang = (r + 1) if r else 2
    plates = [str(v or "") for v in (valeurs or [])][:9]
    plates += [""] * (9 - len(plates))
    c.execute(
        "INSERT OR REPLACE INTO journal (organisme, rang, horodateur, date, heure,"
        " type_action, praticien, code_session, detail, montant, details, scelle)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [organisme, rang] + plates + [scelle])
    c.commit()
    return rang


def journal_sceller(organisme, rang, scelle):
    """Pose le scelle d'une entree deja ecrite."""
    c = _conn()
    c.execute("UPDATE journal SET scelle=? WHERE organisme=? AND rang=?",
              (scelle, organisme, rang))
    c.commit()


def journal_lire(organisme, code_session=None, limite=200):
    """Les entrees les plus recentes, la derniere d'abord."""
    c = _conn()
    if code_session:
        q = ("SELECT * FROM journal WHERE organisme=? AND code_session=?"
             " ORDER BY rang DESC LIMIT ?")
        r = c.execute(q, (organisme, code_session, int(limite)))
    else:
        q = "SELECT * FROM journal WHERE organisme=? ORDER BY rang DESC LIMIT ?"
        r = c.execute(q, (organisme, int(limite)))
    return [dict(x) for x in r.fetchall()]


def journal_ligne(organisme, rang):
    """Une entree precise, ou None."""
    r = _conn().execute("SELECT * FROM journal WHERE organisme=? AND rang=?",
                        (organisme, rang)).fetchone()
    return dict(r) if r else None


def journal_toutes(organisme):
    """Toutes les entrees, dans l'ordre des rangs. Pour verifier la chaine."""
    r = _conn().execute("SELECT * FROM journal WHERE organisme=? ORDER BY rang",
                        (organisme,))
    return [dict(x) for x in r.fetchall()]


def journal_dernier_rang(organisme):
    r = _conn().execute("SELECT MAX(rang) FROM journal WHERE organisme=?",
                        (organisme,)).fetchone()[0]
    return r or 1


def journal_compte(organisme=None):
    c = _conn()
    if organisme:
        return c.execute("SELECT COUNT(*) FROM journal WHERE organisme=?",
                         (organisme,)).fetchone()[0]
    return c.execute("SELECT COUNT(*) FROM journal").fetchone()[0]


def organismes_du_journal():
    r = _conn().execute("SELECT DISTINCT organisme FROM journal ORDER BY organisme")
    return [x[0] for x in r.fetchall()]


# --------------------------------------------------------------------------
# L'ETAT DE VIE DES SESSIONS
# --------------------------------------------------------------------------

def etat_lire(organisme, code_session):
    """L'etat d'une session. Un dictionnaire toujours complet, jamais None.

    Rendre None obligerait chaque appelant a s'en garder, et le premier qui
    l'oublierait planterait. Une session inconnue a simplement un etat vide —
    ce qui est vrai : elle n'a rien vecu.
    """
    r = _conn().execute(
        "SELECT * FROM session_etat WHERE organisme=? AND code_session=?",
        (organisme, code_session)).fetchone()
    if r:
        return {c: (r[c] or "") for c in CHAMPS_ETAT}
    return {c: "" for c in CHAMPS_ETAT}


def etat_poser(organisme, code_session, champ, valeur):
    """Ecrit UN champ d'etat. Rend l'etat complet apres ecriture."""
    if champ not in CHAMPS_ETAT:
        raise ValueError("Champ d'etat inconnu : %s" % champ)
    c = _conn()
    c.execute("INSERT OR IGNORE INTO session_etat (organisme, code_session)"
              " VALUES (?,?)", (organisme, code_session))
    c.execute("UPDATE session_etat SET %s=? WHERE organisme=? AND code_session=?"
              % champ, (str(valeur or ""), organisme, code_session))
    c.commit()
    return etat_lire(organisme, code_session)


def etat_poser_plusieurs(organisme, code_session, valeurs):
    """Ecrit plusieurs champs d'un coup, en une seule transaction.

    Cloturer une session en touche trois. Les ecrire un par un laisserait, le
    temps de deux instructions, un etat mi-cloture mi-ouvert visible par une
    autre requete.
    """
    inconnus = [k for k in valeurs if k not in CHAMPS_ETAT]
    if inconnus:
        raise ValueError("Champ(s) d'etat inconnu(s) : %s" % ", ".join(inconnus))
    c = _conn()
    c.execute("INSERT OR IGNORE INTO session_etat (organisme, code_session)"
              " VALUES (?,?)", (organisme, code_session))
    if valeurs:
        sets = ", ".join("%s=?" % k for k in valeurs)
        c.execute("UPDATE session_etat SET %s WHERE organisme=? AND code_session=?" % sets,
                  [str(v or "") for v in valeurs.values()] + [organisme, code_session])
    c.commit()
    return etat_lire(organisme, code_session)


def etat_supprimer(organisme, code_session):
    """Retire l'etat d'une session. Rend True si une ligne a disparu."""
    c = _conn()
    r = c.execute("DELETE FROM session_etat WHERE organisme=? AND code_session=?",
                  (organisme, code_session))
    c.commit()
    return r.rowcount > 0


def etats(organisme=None):
    """Tous les etats connus : {code_session: etat}."""
    c = _conn()
    if organisme:
        r = c.execute("SELECT * FROM session_etat WHERE organisme=? ORDER BY code_session",
                      (organisme,))
    else:
        r = c.execute("SELECT * FROM session_etat ORDER BY organisme, code_session")
    return {x["code_session"]: {k: (x[k] or "") for k in CHAMPS_ETAT}
            for x in r.fetchall()}


# --------------------------------------------------------------------------
# LE SUIVI DES INSCRITS
# --------------------------------------------------------------------------

def suivi_lire(organisme, code_session):
    """Les lignes d'une session : [(numero, {champ: valeur}), ...], par numero."""
    import json
    r = _conn().execute(
        "SELECT numero, donnees FROM suivi WHERE organisme=? AND code_session=?"
        " ORDER BY numero", (organisme, code_session))
    sortie = []
    for x in r.fetchall():
        try:
            d = json.loads(x["donnees"] or "{}")
        except Exception:
            d = {}
        sortie.append((x["numero"], d if isinstance(d, dict) else {}))
    return sortie


def suivi_ligne(organisme, code_session, numero):
    """Une ligne precise, ou None."""
    import json
    r = _conn().execute(
        "SELECT donnees FROM suivi WHERE organisme=? AND code_session=? AND numero=?",
        (organisme, code_session, int(numero))).fetchone()
    if not r:
        return None
    try:
        d = json.loads(r["donnees"] or "{}")
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def suivi_poser(organisme, code_session, numero, valeurs):
    """Fusionne des champs dans une ligne. Rend la ligne complete apres ecriture.

    FUSION ET NON REMPLACEMENT : les appelants ecrivent un champ a la fois, et
    remplacer l'objet entier effacerait les quarante-neuf autres.
    """
    import json
    c = _conn()
    numero = int(numero)
    actuel = suivi_ligne(organisme, code_session, numero)
    if actuel is None:
        actuel = {}
        c.execute("INSERT OR IGNORE INTO suivi (organisme, code_session, numero, donnees)"
                  " VALUES (?,?,?,?)", (organisme, code_session, numero, "{}"))
    actuel.update({k: ("" if v is None else str(v)) for k, v in (valeurs or {}).items()})
    c.execute("UPDATE suivi SET donnees=? WHERE organisme=? AND code_session=? AND numero=?",
              (json.dumps(actuel, ensure_ascii=False), organisme, code_session, numero))
    c.commit()
    return actuel


def suivi_ajouter(organisme, code_session, valeurs, numero=None):
    """Ajoute une ligne et rend son numero.

    Comme le journal, le premier numero est 2 : la ligne 1 de l'onglet est
    l'en-tete. Ce decalage circule dans tout DFM sous le nom « _numero ».
    """
    c = _conn()
    if numero is None:
        r = c.execute("SELECT MAX(numero) FROM suivi WHERE organisme=? AND code_session=?",
                      (organisme, code_session)).fetchone()[0]
        numero = (r + 1) if r else 2
    import json
    c.execute("INSERT OR REPLACE INTO suivi (organisme, code_session, numero, donnees)"
              " VALUES (?,?,?,?)",
              (organisme, code_session, int(numero),
               json.dumps({k: ("" if v is None else str(v))
                           for k, v in (valeurs or {}).items()}, ensure_ascii=False)))
    c.commit()
    return int(numero)


def suivi_compte(organisme=None, code_session=None):
    c = _conn()
    if organisme and code_session:
        return c.execute("SELECT COUNT(*) FROM suivi WHERE organisme=? AND code_session=?",
                         (organisme, code_session)).fetchone()[0]
    return c.execute("SELECT COUNT(*) FROM suivi").fetchone()[0]


def suivi_sessions():
    """Les sessions qui ont des lignes : [(organisme, code_session, nb), ...]."""
    r = _conn().execute(
        "SELECT organisme, code_session, COUNT(*) n FROM suivi"
        " GROUP BY organisme, code_session ORDER BY organisme, code_session")
    return [(x["organisme"], x["code_session"], x["n"]) for x in r.fetchall()]


def etat():
    """De quoi afficher l'etat de la base sans la connaitre."""
    taille = os.path.getsize(CHEMIN) if os.path.exists(CHEMIN) else 0
    return {"chemin": CHEMIN, "octets": taille,
            "journal": {o: journal_compte(o) for o in organismes_du_journal()},
            "sessions": len(etats()),
            "suivi": {"%s/%s" % (o, c): n for o, c, n in suivi_sessions()}}
