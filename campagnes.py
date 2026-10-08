"""Les campagnes de communication : ciblage, envoi, journal.

CE QUI DISTINGUE UNE COMMUNICATION D'UN MAIL DU PARCOURS. Un mail de parcours
execute un contrat : convention a signer, facture, attestation. Il part a une
personne precise, pour une raison precise, et elle ne peut pas s'y soustraire.
Une communication, non : elle se subit, et doit donc pouvoir se refuser.

D'ou trois regles qui ne sont pas negociables dans ce module :

1. LES DESINSCRITS SONT EXCLUS, toujours, sans option pour les inclure. Un
   filtre qu'on peut decocher finit par etre decoche.
2. LE PIED EST AJOUTE PAR DFM, pas par le modele. Identite de l'organisme et
   lien de desinscription. On ne peut pas oublier ce qu'on n'ecrit jamais.
3. LE MESSAGE ARCHIVE EST LE MESSAGE RENDU, pas le modele. Modifier un modele
   six mois plus tard ne doit pas reecrire l'histoire.

AUCUNE PERSONNALISATION. Decide le 04/08/2026 apres mesure : 174 contacts sur
181 n'ont pas de prenom. « Bonjour , » serait parti a 96 % de la base. Le
message est le meme pour tout le monde, et c'est l'ORGANISME qui ecrit, pas une
personne — donc pas de bloc de signature non plus.

L'ENVOI REPREND OU IL S'EST ARRETE. Gmail impose un rythme : quelques centaines
de mails partent en plusieurs minutes, et une interruption est probable. Chaque
destinataire servi est note au fur et a mesure ; relancer la campagne ne
reexpedie a personne.
"""
import json
import os
import re
import time
from datetime import datetime

_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campagnes.json")

# Pause entre deux envois. Gmail ne documente pas de cadence, mais enchainer
# sans repit est le comportement qui declenche ses protections. Une seconde
# reste supportable — 180 destinataires en trois minutes.
PAUSE = 1.0


# --------------------------------------------------------------------------
# Ciblage
# --------------------------------------------------------------------------
def destinataires(qualite="", marqueurs=None, fonction=""):
    """Les contacts reellement joignables pour une communication.

    Trois exclusions, toutes silencieuses pour l'appelant mais comptees :
    les desinscrits, ceux sans adresse mail, et les doublons d'adresse — deux
    fiches partageant une adresse ne doivent pas produire deux envois.
    """
    import contacts as C
    fiches, _ = C.lister(qualite=qualite, filtre_marqueurs=marqueurs or [],
                         fonction=fonction, limite=5000)
    retenus, vus = [], set()
    exclus = {"desinscrits": 0, "sans_adresse": 0, "doublons": 0}
    for f in fiches:
        if f.get("ne_plus_contacter"):
            exclus["desinscrits"] += 1
            continue
        adresse = (f.get("mail") or "").strip()
        if not adresse or "@" not in adresse:
            exclus["sans_adresse"] += 1
            continue
        cle = adresse.lower()
        if cle in vus:
            exclus["doublons"] += 1
            continue
        vus.add(cle)
        retenus.append(f)
    return retenus, {"base": len(fiches), **exclus, "destinataires": len(retenus)}


def compter(qualite="", marqueurs=None, fonction=""):
    """Le decompte seul, pour l'ecran. Le nombre affiche est celui d'APRES
    exclusion : voir « 181 » puis n'en servir que 174 serait un mensonge."""
    _, bilan = destinataires(qualite, marqueurs, fonction)
    return bilan


# --------------------------------------------------------------------------
# Le pied, ajoute a chaque message
# --------------------------------------------------------------------------
def pied(contact, fiche_organisme=None):
    """Identite de l'expediteur, mention, et lien de desinscription.

    NON MODIFIABLE DEPUIS UN MODELE. C'est la garantie qu'aucune campagne ne
    puisse partir sans moyen de se desinscrire.
    """
    import desinscription as D
    o = fiche_organisme or {}
    marque = (o.get("marque") or "").strip()
    adresse = (o.get("adresse_organisme") or "").strip()
    contact_mail = (o.get("mail_contact") or "").strip()
    lien = D.lien(contact.get("id"), o.get("url_signature") or "")
    if marque:
        import urllib.parse
        lien += "&" + urllib.parse.urlencode({"marque": marque})
    bouts = [x for x in (marque, adresse, contact_mail) if x]
    return (
        '<div style="margin-top:34px;padding-top:16px;border-top:1px solid #e5e8f0;'
        'font-size:11.5px;color:#8b90a0;line-height:1.7;text-align:center">'
        + " &middot; ".join(bouts)
        + '<br>Vous recevez ce message parce que vous figurez dans nos contacts '
          'professionnels.<br>'
        + '<a href="' + lien + '" style="color:#8b90a0;text-decoration:underline">'
          'Ne plus recevoir nos communications</a>'
        + "</div>"
    )


def rendre(corps_html, contact, fiche_organisme=None):
    """Le message complet tel qu'il partira : enveloppe, balise, pied."""
    import mails
    o = fiche_organisme or {}
    html = mails.ENVELOPPE.replace("{CORPS}", corps_html + pied(contact, o))
    return html.replace("{{marque}}", o.get("marque") or "")


# --------------------------------------------------------------------------
# Le registre
# --------------------------------------------------------------------------
def tout():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire(d):
    import fichiers
    fichiers.ecrire(_FICHIER, d)


def _identifiant():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def creer(objet, corps_html, cibles, bilan, organisme="", filtres=None, pieces=None):
    """Inscrit une campagne AVANT le premier envoi.

    Ecrite avant et non apres : une campagne interrompue doit rester
    retrouvable, avec la liste de ceux qui ont deja recu.

    Sous verrou : deux campagnes lancees coup sur coup relisent et reecrivent
    le meme fichier, et la seconde effacerait la premiere.
    """
    import fichiers
    ident = _identifiant()
    fiche = {
        "id": ident,
        "quand": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "organisme": organisme,
        "objet": objet,
        "corps": corps_html,
        "filtres": filtres or {},
        # Les pieces sont RECOPIEES dans la campagne, pas referencees. Modifier
        # le modele six mois plus tard ne doit pas changer ce qui est parti.
        "pieces": pieces or [],
        "bilan": bilan,
        "vises": [c.get("id") for c in cibles],
        "servis": [],
        "echecs": [],
        "etat": "en cours",
    }
    with fichiers.modifier(_FICHIER, {}) as d:
        # L'identifiant est une horodate a la seconde : deux campagnes lancees
        # dans la meme seconde se disputeraient la meme cle.
        while ident in d:
            ident += "b"
            fiche["id"] = ident
        d[ident] = fiche
    return fiche


def marquer_servi(ident, contact_id, souci=""):
    """Note qu'une personne a recu — ou n'a pas recu — et pourquoi.

    APPELEE APRES CHAQUE DESTINATAIRE, depuis envoyer_campagne.py, qui est un
    PROCESSUS DISTINCT de Flask. Elle relit tout le fichier, modifie sa part et
    reecrit tout : sans verrou, une campagne creee pendant l'envoi ecrase la
    liste des servis, et la relance repart a des gens deja servis.

    Mesure faite le 05/08/2026 sur le mecanisme precedent : 8 processus
    ecrivant en parallele, 92 % des ecritures perdues. Le verrou porte sur tout
    le cycle lecture-modification-ecriture, seule maniere correcte de faire.
    """
    import fichiers
    with fichiers.modifier(_FICHIER, {}) as d:
        c = d.get(ident)
        if not c:
            return
        if souci:
            c["echecs"] = [x for x in c.get("echecs", []) if x.get("id") != contact_id]
            c["echecs"].append({"id": contact_id, "souci": souci[:120]})
        else:
            if contact_id not in c["servis"]:
                c["servis"].append(contact_id)
            c["echecs"] = [x for x in c.get("echecs", []) if x.get("id") != contact_id]
        reste = [x for x in c["vises"] if x not in c["servis"]]
        c["etat"] = "terminee" if not reste else "en cours"


def reste_a_servir(ident):
    """Ceux qui n'ont pas encore recu. C'est ce qui permet de relancer une
    campagne interrompue sans reexpedier a personne."""
    c = tout().get(ident) or {}
    servis = set(c.get("servis") or [])
    return [x for x in (c.get("vises") or []) if x not in servis]


def lister(limite=50):
    """Le journal, la plus recente d'abord."""
    return sorted(tout().values(), key=lambda c: c.get("id") or "", reverse=True)[:limite]
