"""La convention de formation, fabriquee sans Google.

POURQUOI CE MODULE EXISTE. La convention passait par un modele Google Docs :
DFM copiait le document, remplacait ses balises, puis demandait au Drive de
l'exporter en PDF. Trois appels reseau, un jeton qui expire, et un texte
contractuel qui vit ailleurs que le code qui le remplit — donc modifiable par
accident, sans trace, et illisible en relecture.

CE MODULE REND LE MEME DOCUMENT, en local, par le meme moteur que les
attestations et l'emargement : un gabarit HTML rendu par Chrome (voir pdf.py).

LE TEXTE JURIDIQUE EST REPRODUIT MOT POUR MOT depuis le modele « Convention de
formation — modele unique ». Aucune reformulation : un acte contractuel deja
signe par des clients ne se reecrit pas a l'occasion d'un changement d'outil.
Les seules differences voulues sont dites dans le gabarit.

CE MODULE NE FABRIQUE RIEN TOUT SEUL. Il assemble le dossier ; l'appelant
decide d'en faire un PDF, de l'afficher, ou de le comparer a l'ancien.
"""
import os
from datetime import datetime


# Les moyens pedagogiques etaient ECRITS EN DUR dans le modele Docs — matériel
# de travaux pratiques compris. C'est le meme defaut que le titre grave dans les
# anciennes attestations : un « modele unique » qui ne l'est pas vraiment. Le
# texte devient un reglage, avec pour valeur par defaut EXACTEMENT celui du
# modele, afin que le document ne change pas tant que personne ne le decide.
MOYENS_DEFAUT = [
    "2 modèles de travail frasaco",
    "1 kit d'instruments LM arte",
    "1 contre angle bague rouge",
    "1 contre angle bague bleue",
    "1 kit de fraises de polissage",
    "1 kit de matriçage",
    "une cassette de matériel : collages et préparations",
]

# Meme raison : le prerequis etait grave dans le modele. Il exigeait un
# « Diplome de Chirurgie Dentaire » alors que les conventions listent desormais
# des assistant(e)s dentaires : le meme acte reclamait un diplome et accueillait
# quelqu'un qui ne l'a pas. Corrige le 17/08/2026, sur decision de l'utilisateur.
PREREQUIS_DEFAUT = ("Être Chirurgien-dentiste, Assistant(e)-dentaire ou étudiant "
                    "en chirurgie-dentaire.")


def categorie(S):
    """Le libellé de la catégorie L.6313-1, LU A LA MEME SOURCE que l'attestation.

    La convention annoncait « adaptation et developpement des competences des
    salaries » pendant que l'attestation cochait « acquisition, entretien ou
    perfectionnement des connaissances » : deux actes pour la meme action,
    deux categories. Un auditeur qui les pose cote a cote le voit.

    Plutot que de recopier le bon libelle ici — ce qui laisserait les deux
    documents libres de diverger a nouveau —, on lit la meme fiche et la meme
    liste que l'attestation. Changer la nature d'une formation change les deux
    documents, ou aucun.
    """
    import attestation as _a
    cle = (S.get("nature_action") or _a.NATURE_DEFAUT).strip()
    for c, libelle in _a.CATEGORIES:
        if c == cle:
            return libelle
    return dict(_a.CATEGORIES).get(_a.NATURE_DEFAUT, "")


# LA SIGNATURE ET LE TAMPON viennent du PROFIL de l'organisme, deposes depuis
# l'ecran Profil — trace a la souris ou image envoyee. Ils etaient colles dans
# le modele Google Docs, donc invisibles pour le code et perdus sans bruit le
# jour ou l'on sort de Docs.
#
# ILS SONT EXIGES. Une convention sans signature ni tampon n'est pas un acte
# presentable, et l'ancien modele en portait toujours : produire un document
# muet la ou il y en avait un signe serait une regression silencieuse. On
# refuse, en disant ou aller les deposer.


def _images(code_session=None):
    """(signature, tampon) en adresses « data: », et ce qui manque.

    ELLES SUIVENT L'ORGANISME DE LA SESSION, pas l'organisme actif a l'ecran.
    Ma premiere version lisait le profil actif : une convention Smileclub
    editee pendant que DSF etait a l'ecran serait partie avec l'en-tete de
    Smileclub et LA SIGNATURE DE DSF. Le reste du document suit deja la
    session, via sessions.balises_identite ; il n'y avait que ces deux images
    pour regarder ailleurs.
    """
    import profil as _p
    organisme = None
    if code_session:
        try:
            import sessions as _s
            organisme = _s.organisme_de(code_session) or None
        except Exception:
            organisme = None
    sig = _p.image_en_ligne("signature_fichier", organisme)
    tam = _p.image_en_ligne("tampon_fichier", organisme)
    manque = [n for n, v in (("la signature", sig), ("le tampon", tam)) if not v]
    return sig, tam, manque


def _nombre(valeur):
    try:
        return float(str(valeur or 0).replace(",", ".").replace(" ", ""))
    except ValueError:
        return 0.0


def _liste(valeur):
    """Une fiche formation peut porter une liste la ou le document attend du
    texte, et inversement. On rend toujours une liste de lignes."""
    if isinstance(valeur, (list, tuple)):
        return [str(x).strip() for x in valeur if str(x).strip()]
    t = str(valeur or "").strip()
    return [l.strip() for l in t.splitlines() if l.strip()] if t else []


def _jours(S):
    try:
        import jours as _J
        r = _J.resume(S or {})
        if not r["jours"]:
            return {}
        return {"date_debut": _J._d(r["date_debut"]).strftime("%d/%m/%Y"),
                "date_fin": _J._d(r["date_fin"]).strftime("%d/%m/%Y"),
                "detail": r["detail"], "nb": str(r["nb"]),
                "duree": "%s heures" % r["duree"], "texte": r["texte"]}
    except Exception:
        return {}


def pour(code_session, signature_client="", ligne=None):
    """Le dossier complet d'une convention client, prêt pour le gabarit.

    `signature_client` est la signature relevee sur la page publique, telle
    qu'elle sort de Supabase : une adresse « data: ». En HTML elle s'insere
    directement. Le modele Docs obligeait a la deposer dans le Drive PUIS a la
    rendre publique pour qu'un document puisse l'afficher — deux appels reseau
    et un fichier expose, pour une image qu'on avait deja sous la main.

    Rend (dossier, souci). Le souci est une phrase a montrer : on refuse
    d'editer un acte incomplet plutot que d'y laisser des vides a la place du
    SIRET ou du representant — c'est la regle du script d'origine, conservee.
    """
    import clients as CL
    import sessions as _s
    import suivi as _su

    S = _s.session(code_session)

    # DEUX CAS, UN SEUL DOCUMENT — comme le modele Docs depuis le 04/08/2026.
    # Ce qui change n'est pas le texte mais la SECONDE PARTIE de la clause
    # « Entre les soussignes », le bloc de signature et la liste des
    # participants. `ligne` designe un praticien ; sans elle, on traite la
    # session cliente.
    if ligne is not None:
        return _individuelle(S, ligne, signature_client, code_session)

    if not _s.est_client(code_session):
        return None, ("Session à inscriptions individuelles : passez la ligne du "
                      "praticien à convention.pour(code, ligne=...).")

    fiche = CL.client(_s.client_de(code_session)) or {}
    if not fiche:
        return None, "Le client de cette session est introuvable dans la base clients."
    manques = CL.complet(fiche)
    if manques:
        return None, ("Fiche client incomplète : " + ", ".join(manques) +
                      ". La convention ne peut pas être éditée.")

    lignes = [l for l in _su.lire_lignes_de(code_session) if not l["annule_le"]]
    if not lignes:
        return None, "Aucun participant saisi."

    # UNE CONVENTION N'INVENTE PAS UNE FONCTION. Elle etait comblee par
    # « Chirurgien-dentiste » des qu'elle manquait : une assistante dentaire s'y
    # trouvait declaree chirurgien-dentiste, sur un acte signe par les deux
    # parties. Tranche par Franck le 22/08/2026 : on refuse d'editer, et on dit qui.
    _sans = [(l["prenom"] + " " + l["nom"]).strip()
             for l in lignes if not (l.get("fonction") or "").strip()]
    if _sans:
        return None, ("La fonction n'est pas renseignée pour %s%s. Une convention ne "
                      "peut pas l'inventer : complétez-la dans la saisie des "
                      "participants."
                      % (", ".join(_sans[:6]),
                         " et %d autre(s)" % (len(_sans) - 6) if len(_sans) > 6 else ""))
    participants = [{"nom": (l["prenom"] + " " + l["nom"]).strip(),
                     "fonction": (l.get("fonction") or "").strip()}
                    for l in lignes]

    sig, tam, manque = _images(code_session)
    if manque:
        return None, ("Il manque %s de %s. Déposez-%s dans Profil → Signature et "
                      "tampon : une convention ne part pas sans."
                      % (" et ".join(manque), S.get("marque") or "l'organisme",
                         "les" if len(manque) > 1 else "la"))

    unitaire = _nombre(S.get("tarif"))
    total = unitaire * len(participants)
    ident = _s.balises_identite(S)

    def b(cle):
        return (ident.get("{{%s}}" % cle) or "").strip()

    j = _jours(S)
    return {
        "marque": b("marque") or b("organisme"),
        "organisme": b("organisme"),
        "adresse_organisme": b("adresse_organisme"),
        "siret": b("siret"),
        "mail_contact": b("mail_contact"),
        "mention_declaration_longue": b("mention_declaration_longue"),
        "formateur": b("formateur"),
        # La clause « Entre les soussignes », seconde partie. Balise unique
        # depuis le 04/08/2026 pour que le meme modele serve aux sessions
        # individuelles : un praticien n'a ni SIRET ni representant, et les
        # lignes vides d'un acte contractuel ne sont pas acceptables.
        "seconde_partie": (
            "%s, %s (Siret : %s), représentée par %s, en sa qualité de %s, "
            "désignée ci-après « le Client »." % (
                fiche.get("raison_sociale") or "", fiche.get("adresse") or "",
                fiche.get("siret") or "", fiche.get("representant") or "",
                fiche.get("representant_fonction") or "")),
        "client_denomination": fiche.get("raison_sociale") or "",
        "client_representant": fiche.get("representant") or "",
        "client_fonction": fiche.get("representant_fonction") or "",
        "titre_formation": S.get("titre_complet") or S.get("nom_formation") or "",
        "objectifs": _liste(S.get("objectifs")),
        "categorie": categorie(S),
        "moyens": _liste(S.get("moyens")) or MOYENS_DEFAUT,
        "prerequis": (S.get("prerequis") or "").strip() or PREREQUIS_DEFAUT,
        "duree": j.get("duree") or str(S.get("duree_heures") or ""),
        "lieu": S.get("adresse") or "",
        "horaires": S.get("horaires") or "",
        "date_formation": j.get("texte") or S.get("date_texte") or "",
        "date_debut": j.get("date_debut", ""),
        "date_fin": j.get("date_fin", ""),
        "jours_formation": j.get("detail") or [],
        "nb_jours": j.get("nb", ""),
        "participants": participants,
        "nb_participants": len(participants),
        "tarif": "%.0f" % unitaire,
        "total": "%.0f" % total,
        "ville": (S.get("ville_organisme") or "Paris"),
        "date_du_jour": datetime.now().strftime("%d/%m/%Y"),
        "signature": sig,
        "tampon": tam,
        "signature_client": signature_client or "",
    }, ""


def _commun(S):
    """Ce que les deux conventions partagent : l'organisme, la formation,
    les dates. Ecrit une seule fois pour que les deux ne divergent pas."""
    import sessions as _s
    ident = _s.balises_identite(S)

    def b(cle):
        return (ident.get("{{%s}}" % cle) or "").strip()

    j = _jours(S)
    return {
        "marque": b("marque") or b("organisme"),
        "organisme": b("organisme"),
        "adresse_organisme": b("adresse_organisme"),
        "siret": b("siret"),
        "mail_contact": b("mail_contact"),
        "mention_declaration_longue": b("mention_declaration_longue"),
        "formateur": b("formateur"),
        "titre_formation": S.get("titre_complet") or S.get("nom_formation") or "",
        "objectifs": _liste(S.get("objectifs")),
        "categorie": categorie(S),
        "moyens": _liste(S.get("moyens")) or MOYENS_DEFAUT,
        "prerequis": (S.get("prerequis") or "").strip() or PREREQUIS_DEFAUT,
        "duree": j.get("duree") or str(S.get("duree_heures") or ""),
        "lieu": S.get("adresse") or "",
        "horaires": S.get("horaires") or "",
        "date_formation": j.get("texte") or S.get("date_texte") or "",
        "date_debut": j.get("date_debut", ""),
        "date_fin": j.get("date_fin", ""),
        "jours_formation": j.get("detail") or [],
        "nb_jours": j.get("nb", ""),
        "ville": (S.get("ville_organisme") or "Paris"),
        "date_du_jour": datetime.now().strftime("%d/%m/%Y"),
    }


def _individuelle(S, ligne, signature_client="", code_session=None):
    """La convention d'UN praticien, qui signe en son nom propre.

    LA VILLE DU PRATICIEN N'Y FIGURE PAS — decision du 04/08/2026. Le champ est
    de la saisie libre (« Paris 9 », « MARSEILLE », « Tel aviv ») et rien
    n'oblige a faire figurer un domicile professionnel dans un acte entre un
    organisme et un praticien. Ce qu'on n'ecrit pas ne peut pas etre faux.
    """
    nom = ((ligne.get("prenom") or "") + " " + (ligne.get("nom") or "")).strip()
    if not nom:
        return None, "Ligne de suivi sans nom : rien n'est édité."
    # MEME REGLE COTE INDIVIDUEL : on ne comble pas, on refuse.
    fonction = (ligne.get("fonction") or "").strip()
    if not fonction:
        return None, ("La fonction de %s n'est pas renseignée. Une convention ne "
                      "peut pas l'inventer." % nom)

    sig, tam, manque = _images(code_session)
    if manque:
        return None, ("Il manque %s de %s. Déposez-%s dans Profil → Signature et "
                      "tampon : une convention ne part pas sans."
                      % (" et ".join(manque), S.get("marque") or "l'organisme",
                         "les" if len(manque) > 1 else "la"))

    tarif = _nombre(S.get("tarif"))
    d = _commun(S)
    d.update({
        # Formulations reprises telles quelles de sessions.balises_stagiaire :
        # ce sont des clauses d'un acte deja signe par des praticiens.
        "seconde_partie": "Docteur %s, désigné ci-après « le Stagiaire »." % nom,
        "client_representant": "Docteur " + nom,
        "client_fonction": fonction,
        # Aucune personne morale a nommer sous sa signature : on laisse vide
        # plutot que d'inventer une ligne.
        "client_denomination": "",
        "participants": [{"nom": nom, "fonction": fonction}],
        "nb_participants": 1,
        # Un seul stagiaire : le total EST le tarif.
        "tarif": "%.0f" % tarif, "total": "%.0f" % tarif,
        "date_formation": (ligne.get("date_formation") or "").strip() or d["date_formation"],
        "signature": sig, "tampon": tam,
        "signature_client": signature_client or "",
    })
    return d, ""


def html(donnees):
    from flask import render_template
    import app as _app
    with _app.app.app_context():
        return render_template("convention.html", c=donnees)


def fabriquer(code_session, signature_client="", ligne=None):
    """Les octets du PDF, ou (None, souci)."""
    import pdf as _pdf
    d, souci = pour(code_session, signature_client, ligne)
    if not d:
        return None, souci
    return _pdf.depuis_html(html(d)), ""
