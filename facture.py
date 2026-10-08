"""La facture, fabriquee sans Google.

POURQUOI CE MODULE EXISTE. Meme raison que convention.py : la facture passait
par un modele Google Docs copie, dont on remplacait les balises avant de
demander au Drive de l'exporter en PDF. Trois appels reseau et un document
contractuel vivant ailleurs que le code qui le remplit.

DEUX FORMES, UN SEUL DOCUMENT. La facture d'un praticien et celle d'une
structure ne different que par le destinataire, la quantite et la mention de
reglement — jamais par le texte. Le modele Docs l'avait deja compris ; on le
garde.

LE TEXTE EST REPRIS MOT POUR MOT du modele « Facture — modele unique », y
compris les trois mentions legales du pied : article 293 B, enregistrement
prefectoral, penalites de retard. Une facture est une piece comptable ; ses
mentions ne se reformulent pas a l'occasion d'un changement d'outil.
"""
from datetime import datetime


def _nombre(valeur):
    try:
        return float(str(valeur or 0).replace(",", ".").replace(" ", ""))
    except ValueError:
        return 0.0


def _jours(S):
    try:
        import jours as _J
        r = _J.resume(S or {})
        if not r["jours"]:
            return {}
        return {"detail": r["detail"], "texte": r["texte"],
                "duree": "%s heures" % r["duree"], "nb": str(r["nb"])}
    except Exception:
        return {}


def pour(S, numero, destinataire, unitaire, quantite, civilite="",
         mention_reglement="", ligne_reglement="", paiement=None):
    """Le dossier d'une facture, prêt pour le gabarit.

    `destinataire` est le praticien ou la raison sociale : la facture ne
    distingue pas les deux ailleurs que sur cette ligne.
    """
    import sessions as _s
    ident = _s.balises_identite(S)

    def b(cle):
        return (ident.get("{{%s}}" % cle) or "").strip()

    # Un profil sans IBAN ne doit pas produire « IBAN :   —   BIC : » : la
    # ligne disparait entierement, comme la mention de declaration.
    iban, bic = b("iban"), b("bic")
    j = _jours(S)
    total = unitaire * quantite
    return {
        "organisme": b("organisme"),
        "adresse_organisme": b("adresse_organisme"),
        "siret": b("siret"),
        "mention_declaration": b("mention_declaration"),
        "marque": b("marque") or b("organisme"),
        "numero": numero,
        "date_facture": datetime.now().strftime("%d/%m/%Y"),
        "civilite": civilite,
        "destinataire": destinataire,
        "titre_formation": S.get("titre_complet") or S.get("nom_formation") or "",
        "quantite": quantite,
        "date_formation": j.get("texte") or S.get("date_texte") or "",
        "jours_formation": j.get("detail") or [],
        "duree": j.get("duree") or str(S.get("duree_heures") or S.get("duree") or ""),
        "unitaire": "%.0f" % unitaire,
        "total": "%.0f" % total,
        "mention_reglement": mention_reglement,
        "ligne_reglement": ligne_reglement,
        "iban": iban, "bic": bic,
        "rib": ("IBAN : %s   —   BIC : %s" % (iban, bic)) if iban else "",
        # Une facture deja reglee porte la trace du paiement ; une facture a
        # regler porte les coordonnees bancaires. Jamais les deux.
        "paiement": paiement or None,
    }


def html(donnees):
    from flask import render_template
    import app as _app
    with _app.app.app_context():
        return render_template("facture.html", f=donnees)


def fabriquer(*args, **kwargs):
    """Les octets du PDF. Mêmes arguments que pour()."""
    import pdf as _pdf
    return _pdf.depuis_html(html(pour(*args, **kwargs)))
