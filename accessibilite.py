"""Les besoins d'adaptation declares, et ce qu'on en fait.

POURQUOI CE MODULE EXISTE. Le formulaire d'inscription demande depuis toujours
« Je suis porteur(euse) d'un handicap ou necessite un acces PMR ». La reponse
est enregistree en colonne M du suivi. Elle n'etait affichee NULLE PART.

C'est le pire cas de figure. Ne pas poser la question serait un manque ;
la poser et ne jamais regarder la reponse, c'est collecter une donnee de sante
sans finalite — contraire au RGPD — tout en laissant arriver le jour J une
personne dont on savait qu'elle avait un besoin. L'indicateur 26 ne demande pas
qu'on interroge, il demande qu'on prenne en compte.

CE MODULE NE DECIDE RIEN. Il rend visible, nomme le referent, et laisse
l'organisme agir. Une adaptation se discute avec la personne, pas avec un
logiciel.
"""

# Reponses du formulaire valant declaration d'un besoin. La question est
# fermee, mais les imports anciens et les saisies manuelles ont produit des
# variantes : mieux vaut un « oui » de trop repere qu'un besoin manque.
_OUI = ("oui", "yes", "o", "vrai", "true", "1", "x")


def declare(ligne):
    """Cette personne a-t-elle declare un besoin d'adaptation ?"""
    v = str((ligne or {}).get("pmr") or "").strip().lower()
    if not v:
        return False
    if v in _OUI:
        return True
    # « Oui, fauteuil roulant » : une precision libre reste un oui.
    return v.startswith("oui")


def concernes(lignes):
    """Les personnes ayant declare un besoin, dans l'ordre du suivi."""
    sortie = []
    for l in lignes or []:
        if not declare(l):
            continue
        # Une annulation retire le besoin : la personne ne viendra pas.
        if (l.get("annule_le") or "").strip():
            continue
        sortie.append({
            "nom": ((l.get("prenom") or "") + " " + (l.get("nom") or "")).strip()
                   or (l.get("mail") or "Sans nom"),
            "mail": l.get("mail") or "",
            "telephone": l.get("telephone") or "",
            "precision": str(l.get("pmr") or "").strip(),
        })
    return sortie


def referent(fiche_organisme=None):
    """Le referent handicap declare, et de quoi le joindre.

    Rend « nomme » a False tant que rien n'est renseigne : c'est ce manque qui
    doit remonter a l'ecran, pas un champ vide qui passe inapercu.
    """
    f = fiche_organisme
    if f is None:
        try:
            import profil
            f = profil.charger() or {}
        except Exception:
            f = {}
    nom = str(f.get("referent_handicap") or "").strip()
    contact = str(f.get("referent_handicap_contact") or "").strip()
    return {"nom": nom, "contact": contact, "nomme": bool(nom and contact)}


def phrase(fiche_organisme=None):
    """La mention d'accessibilite reprise sur les convocations et documents.

    Formulee au present et sans conditionnel : une mention qui dit « nous
    pourrions etudier » n'engage a rien et ne prouve rien.
    """
    r = referent(fiche_organisme)
    if not r["nomme"]:
        return ""
    return ("Accessibilité : si vous avez besoin d'une adaptation pour suivre cette "
            "formation, contactez %s, référent handicap, à %s. Nous étudions avec "
            "vous les aménagements possibles et, si nous ne pouvons pas y répondre, "
            "nous vous orientons vers un organisme en mesure de le faire."
            % (r["nom"], r["contact"]))
