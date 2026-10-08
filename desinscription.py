"""Le lien de desinscription, et rien d'autre.

POURQUOI CE MODULE EST LE PREMIER ECRIT DU CHANTIER MESSAGERIE. Un envoi de
communication sans moyen de se desinscrire n'a pas le droit de partir. Le
construire en dernier, c'est se donner l'occasion de l'oublier.

UN LIEN QUI NE SE DEVINE PAS. L'adresse ne porte pas le seul numero de fiche :
avec « ?c=42 », n'importe qui desinscrirait n'importe qui en changeant un
chiffre. Elle porte le numero ET une signature calculee a partir d'un secret
que seuls DFM et la fonction Netlify connaissent.

    ?c=42.a3f9c1b8e2d7...

AUCUNE COLONNE A AJOUTER. La signature se CALCULE, elle ne se stocke pas :
rien a creer dans Supabase, rien a migrer, et un contact cree demain a son lien
sans que personne y pense.

LE SECRET EST LA CLE SUPABASE, deja partagee entre DFM et le site — c'est ce
qui evite une variable de plus a tenir synchronisee entre deux endroits. Une
signature HMAC ne revele pas la cle qui l'a produite, l'usage est sain.
"""
import hmac
import hashlib

_LONGUEUR = 24          # 96 bits : indevinable, et l'adresse reste courte


def _secret():
    from config import SUPABASE_KEY
    return (SUPABASE_KEY or "").encode("utf-8")


def signature(identifiant):
    """La preuve que ce lien vient bien de nous, pour CE contact."""
    return hmac.new(_secret(), str(identifiant).encode("utf-8"),
                    hashlib.sha256).hexdigest()[:_LONGUEUR]


def jeton(identifiant):
    """« 42.a3f9c1b8… » — ce qui voyage dans l'adresse."""
    return "%s.%s" % (identifiant, signature(identifiant))


def verifier(jeton_recu):
    """Rend l'identifiant si la signature est valable, sinon None.

    La comparaison passe par compare_digest : comparer deux chaines avec « == »
    s'arrete au premier caractere different, et le TEMPS de reponse renseigne
    alors sur le nombre de caracteres justes. C'est une attaque connue, et elle
    ne coute rien a eviter.
    """
    brut = str(jeton_recu or "").strip()
    if "." not in brut:
        return None
    identifiant, _, sig = brut.partition(".")
    if not identifiant.isdigit() or not sig:
        return None
    if not hmac.compare_digest(sig, signature(identifiant)):
        return None
    return int(identifiant)


def lien(identifiant, base=""):
    """L'adresse complete, a poser dans le pied de chaque communication."""
    racine = (base or "").rstrip("/")
    if not racine:
        try:
            import sessions
            racine = (sessions.COMMUN.get("url_signature") or "").rstrip("/")
        except Exception:
            racine = ""
    return racine + "/desinscription.html?c=" + jeton(identifiant)
