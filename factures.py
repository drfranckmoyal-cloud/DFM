"""Registre des factures : la piece comptable, independante des sessions.

POURQUOI UN REGISTRE SEPARE
---------------------------
Une facture emise engage la comptabilite de l'organisme. Elle doit survivre a
tout : a la suppression de sa session, a la disparition d'un client de la base,
a un menage dans le Drive. Le suivi et les fiches de session decrivent une
activite en cours ; le registre, lui, decrit ce qui a ete EMIS.

Chaque entree est donc DENORMALISEE : elle porte le nom du client et
l'intitule de la formation en toutes lettres, pas seulement leurs identifiants.
Une facture de 2026 doit rester lisible en 2036, meme si le client a ete
supprime entre-temps.

DEUX SERIES INDEPENDANTES
-------------------------
Smileclub et DSF sont deux entites juridiques : leurs numeros de facture
forment deux suites continues et separees. C'est une obligation comptable, pas
un confort. Avant ce module, la recherche du dernier numero balayait tout le
Drive sans distinction — la facture F2026-008 de DSF a ainsi pris un numero
dans la serie de Smileclub.

Le numero est calcule sur le MAXIMUM de deux sources : le registre et les PDF
presents dans le dossier Factures de l'organisme. Tant que d'anciennes factures
n'existent que sur le Drive, elles comptent quand meme — on ne peut pas
reattribuer un numero deja porte par un document remis a un client.

CE MODULE N'EMET RIEN. Il tient les comptes ; la fabrication du document et son
envoi sont ailleurs.
"""
import json
import os
import re
from datetime import datetime

_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "factures.json")


def tout():
    """Le registre entier, indexe par numero de facture."""
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)


def prefixe(annee=None):
    return "F%d-" % (annee or datetime.now().year)


def _numeros_du_registre(organisme, annee):
    """Les numeros deja inscrits pour CET organisme, cette annee.

    ON LIT LE CHAMP « numero », PAS LA CLE. Depuis le 18/08/2026 une entree peut
    etre rangee sous « dsf/F2026-011 » quand « F2026-011 » est deja pris par une
    autre serie : la cle n'est plus le numero, elle n'est qu'une adresse.
    """
    p = prefixe(annee)
    sortie = []
    for cle, e in tout().items():
        if (e.get("organisme") or "") != organisme:
            continue
        m = re.match(r"^" + re.escape(p) + r"(\d{3})(?!\d)", str(e.get("numero") or cle))
        if m:
            sortie.append(int(m.group(1)))
    return sortie


def _numeros_des_sessions(organisme, annee):
    """Les numeros portes par les FICHES DE SESSION de cet organisme.

    Troisieme source, et elle n'est pas theorique : la facture client F2026-011
    de DSF ne vivait plus QUE la, son entree au registre ayant ete ecrasee. Sans
    cette lecture, la serie de DSF repartait a F2026-001 et reattribuait onze
    numeros deja emis.
    """
    p = prefixe(annee)
    sortie = []
    try:
        import sessions as _S
        for _code, f in (_S._charger_json(_S._FICHIER_S) or {}).items():
            if (f.get("organisme") or "").strip() != organisme:
                continue
            m = re.match(r"^" + re.escape(p) + r"(\d{3})(?!\d)",
                         str(f.get("facture_client_numero") or "").strip())
            if m:
                sortie.append(int(m.group(1)))
    except Exception:
        pass
    return sortie


def _numeros_du_drive(drive, dossier, annee):
    """Les factures deja posees dans le dossier de CET organisme.

    Borne au dossier : c'est tout l'objet de la separation des series. Une
    recherche globale ramenerait celles de l'autre entite.
    """
    if not (drive and dossier):
        return []
    p = prefixe(annee)
    sortie = []
    try:
        pile = [dossier]
        vus = set()
        while pile:
            courant = pile.pop()
            if courant in vus:
                continue
            vus.add(courant)
            for f in drive.files().list(
                    q="'%s' in parents and trashed=false" % courant,
                    fields="files(id,name,mimeType)", pageSize=1000).execute().get("files", []):
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    pile.append(f["id"])
                    continue
                m = re.match(r"^Facture " + re.escape(p) + r"(\d{3})(?!\d)", f["name"])
                if m:
                    sortie.append(int(m.group(1)))
    except Exception:
        return sortie
    return sortie


def prochain_numero(organisme, drive=None, dossier=None, annee=None):
    """Le prochain numero libre de la serie de CET organisme.

    Le maximum des deux sources, jamais le compte des entrees : un trou dans la
    suite (facture annulee, entree supprimee a la main) ne doit pas faire
    reattribuer un numero deja emis.
    """
    annee = annee or datetime.now().year
    # TROIS SOURCES, ET LE DRIVE N'EST QUE LA TROISIEME. Il etait indispensable
    # tant qu'il connaissait des factures que le registre ignorait ; depuis le
    # 18/08/2026 les deux sources locales suffisent, et son absence — jeton
    # revoque, hors ligne — ne fait plus repartir une serie a zero.
    connus = (_numeros_du_registre(organisme, annee)
              + _numeros_des_sessions(organisme, annee)
              + _numeros_du_drive(drive, dossier, annee))
    return "%s%03d" % (prefixe(annee), (max(connus) + 1) if connus else 1)


def enregistrer(numero, organisme, client_id, client_nom, session_code,
                formation, total, participants=1, unitaire=None, lien="",
                type_facture="client", date_facture=None):
    """Inscrit une facture au registre.

    Ecrase l'entree de meme numero DU MEME ORGANISME — une reemission corrige
    la precedente. Jamais celle d'un autre organisme : leurs series sont
    distinctes, et deux numeros identiques y designent deux factures.

    La DATE est celle de l'emission, et c'est elle qui compte pour le cumul
    OPCO : une formation de decembre facturee en janvier pese sur l'annee neuve.
    """
    import fichiers
    with fichiers.modifier(_FICHIER, {}) as d:
        # DEFAUT CORRIGE LE 18/08/2026. La cle etait le numero seul, et la
        # docstring disait « ecrase l'entree de meme numero » — ecrite du temps
        # d'une serie unique. Chaque organisme ayant desormais la sienne,
        # F2026-011 de DSF et F2026-011 de Smileclub partageaient une cle : la
        # seconde emission A EFFACE la premiere du registre. C'est arrive le
        # 17/08/2026, et la facture DSF du 04/08 n'existait plus que par le
        # numero inscrit sur sa fiche de session.
        #
        # On ne renumerote rien et on ne deplace rien : une entree deja rangee
        # sous son numero y reste. Seule une entree qui ECRASERAIT celle d'un
        # AUTRE organisme prend une cle qui porte le sien.
        cle = numero
        occupe = d.get(numero)
        if occupe and (occupe.get("organisme") or "") != (organisme or ""):
            cle = "%s/%s" % (organisme or "sans-organisme", numero)
        d[cle] = _fiche(numero, organisme, client_id, client_nom, session_code,
                        formation, total, participants, unitaire, lien,
                        type_facture, date_facture)
        return d[cle]


def _fiche(numero, organisme, client_id, client_nom, session_code, formation,
           total, participants, unitaire, lien, type_facture, date_facture):
    return {
        "numero": numero,
        "organisme": organisme,
        "date": date_facture or datetime.now().strftime("%d/%m/%Y"),
        "client_id": client_id,
        "client": client_nom,
        "session": session_code,
        "formation": formation,
        "participants": participants,
        "unitaire": unitaire,
        "total": total,
        "lien": lien,
        "type": type_facture,
    }


def _annee_de(entree):
    try:
        return datetime.strptime(entree.get("date") or "", "%d/%m/%Y").year
    except Exception:
        m = re.match(r"^F(\d{4})-", str(entree.get("numero") or ""))
        return int(m.group(1)) if m else 0


def cumul_client(client_id, annee=None, organisme=None):
    """Total facture a un client sur une annee civile, DATE DE FACTURE.

    Sert a situer le client par rapport a son plafond annuel OPCO. Le cumul
    ignore l'organisme par defaut : c'est le client qui a un plafond, pas la
    relation avec l'une ou l'autre de vos entites.
    """
    annee = annee or datetime.now().year
    somme = 0.0
    for e in tout().values():
        if e.get("client_id") != client_id:
            continue
        if organisme and e.get("organisme") != organisme:
            continue
        if _annee_de(e) != annee:
            continue
        try:
            somme += float(e.get("total") or 0)
        except (TypeError, ValueError):
            continue
    return somme


def du_client(client_id):
    """Toutes les factures d'un client, la plus recente d'abord."""
    l = [e for e in tout().values() if e.get("client_id") == client_id]
    return sorted(l, key=lambda e: (_annee_de(e), e.get("numero") or ""), reverse=True)


def de_la_session(session_code):
    """Les factures rattachees a une session. Elles LUI SURVIVENT : la session
    peut disparaitre, l'entree reste, avec le nom du client en clair."""
    return [e for e in tout().values() if e.get("session") == session_code]


def de_l_organisme(organisme, annee=None):
    l = [e for e in tout().values() if e.get("organisme") == organisme]
    if annee:
        l = [e for e in l if _annee_de(e) == annee]
    return sorted(l, key=lambda e: e.get("numero") or "")
