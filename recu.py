"""Le recu d'un versement, fabrique comme la facture et a cote d'elle.

POURQUOI UN RECU, ET PAS UNE FACTURE DE PLUS — decision de Franck, 25/10/2026.
Un apprenant d'Esthetique 360 verse trois ou quatre fois dans l'annee. Emettre
une facture par virement multiplierait les pieces comptables pour une seule
creance, et la somme des factures ne dirait plus le prix de la formation. La
pratique courante en organisme de formation est l'inverse : UNE facture, pour
la somme entiere, puis UN RECU par versement.

CE QUE LE RECU DIT, ET QUE LA FACTURE NE DIT PAS : ce qui a ete verse ce
jour-la, ce qui l'a ete en tout, et ce qu'il reste. C'est cela qu'un praticien
cherche quand il relit ses virements, et c'est cela qui fait la trace.

IL N'A PAS DE NUMERO DE FACTURE. La serie des factures est une suite continue,
cloisonnee par organisme, tenue au registre : y meler des recus la trouerait.
Le recu porte donc une reference qui lui est propre — « R2026-0043-2 », le
numero de la facture suivi du rang du versement — et n'entre pas au registre.
Si la facture n'existe pas encore, il porte la reference du versement.
"""
from datetime import datetime


def pour(S, reference, destinataire, versement, verse, du, civilite="",
         numero_facture="", echeance=""):
    """Le dossier d'un recu, pret pour le gabarit.

    `versement` est l'un des dictionnaires rendus par suivi.versements().
    `verse` est le total encaisse APRES ce versement, `du` la somme entiere.
    """
    import sessions as _s
    import suivi as _suivi
    ident = _s.balises_identite(S)

    def b(cle):
        return (ident.get("{{%s}}" % cle) or "").strip()

    iban, bic = b("iban"), b("bic")
    montant = _suivi.euros((versement or {}).get("montant"))
    reste = max(0.0, du - verse)

    def sous(v):
        """« 2 000 » et non « 2000 » : la meme regle que la convention et les
        mails, au meme endroit, pour que les trois ne divergent pas."""
        try:
            import convention as _cv
            return _cv._euros(v)
        except Exception:
            return ("%.2f" % v).rstrip("0").rstrip(".") if v % 1 else "%.0f" % v

    j = {}
    try:
        import jours as _J
        r = _J.resume(S or {})
        if r["jours"]:
            j = {"texte": r["texte"]}
    except Exception:
        j = {}
    return {
        "organisme": b("organisme"),
        "adresse_organisme": b("adresse_organisme"),
        "siret": b("siret"),
        "mention_declaration": b("mention_declaration"),
        "marque": b("marque") or b("organisme"),
        "numero": reference,
        "date_facture": datetime.now().strftime("%d/%m/%Y"),
        "civilite": civilite,
        "destinataire": destinataire,
        "titre_formation": S.get("titre_complet") or S.get("nom_formation") or "",
        "date_formation": j.get("texte") or S.get("date_texte") or "",
        "paiement": {"le": (versement or {}).get("le") or "",
                     "mode": (versement or {}).get("mode") or "virement",
                     "reference": (versement or {}).get("reference") or "-"},
        "facture": numero_facture or "",
        "unitaire": sous(montant),
        "verse": sous(verse),
        "total": sous(du),
        # Vide — et non « 0 » — quand le compte est solde : le gabarit s'en sert
        # comme d'un interrupteur, et « 0 » est vrai en Jinja.
        "reste": sous(reste) if reste > 0 else "",
        "echeance": echeance,
        "iban": iban, "bic": bic,
        "rib": ("IBAN : %s   —   BIC : %s" % (iban, bic)) if iban else "",
    }


def html(donnees):
    from flask import render_template
    import app as _app
    with _app.app.app_context():
        return render_template("recu.html", f=donnees)


def fabriquer(*args, **kwargs):
    """Les octets du PDF. Memes arguments que pour()."""
    import pdf as _pdf
    return _pdf.depuis_html(html(pour(*args, **kwargs)))
