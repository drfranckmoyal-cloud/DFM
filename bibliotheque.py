"""L'inventaire de tous les documents que DFM detient.

POURQUOI CE MODULE EXISTE. DFM rangeait ses documents PAR PROVENANCE, jamais par
nature : un programme la ou l'ecran Formation savait ecrire, un logo la ou
l'ecran Profil savait ecrire, un CV ailleurs encore. Quatre mondes de rangement,
six ecrans pour deposer, et AUCUN pour regarder. Pour savoir quels documents DFM
detenait pour un organisme, il fallait ouvrir six ecrans — et le Drive.

Ce module ne deplace rien. Il REGARDE partout et rend une seule liste.

CE QU'IL NE FAIT PAS. Il ne devine pas : une piece dont le champ est vide est
« absente », une piece dont le champ pointe vers un identifiant Drive que le
disque ne connait pas est « seulement dans le Drive ». Les deux se disent
differemment parce qu'ils se soignent differemment — l'une se depose, l'autre se
rapatrie.
"""
import os

import documents

# Ce que porte un ORGANISME, dans l'ordre ou un auditeur les demande.
PIECES_ORGANISME = (
    ("reglement_interieur_id", "reglement", "Règlement intérieur",
     "Remis avant l'entrée en formation — indicateur 1."),
    ("rib_id", "rib", "RIB",
     "Joint aux mails de confirmation et aux factures."),
)

# Ce que porte une FORMATION. Elle est commune aux organismes : son programme
# l'est aussi, et le recopier par organisme creerait deux verites a tenir
# d'accord.
PIECES_FORMATION = (
    ("programme_id", "programme", "Programme",
     "Le contenu detaille, joint aux conventions et aux convocations."),
    ("acces_id", "acces", "Plan d'accès",
     "Adresse, transports, horaires — joint aux convocations."),
)

# Les images d'identite ont leur propre rangement depuis longtemps : on les
# montre ici pour completer le tableau, sans toucher a leur voie.
IMAGES_ORGANISME = (
    ("logo_fichier", "Logo", "En-tête des documents et des mails."),
    ("signature_fichier", "Signature", "Apposée sur les conventions et attestations."),
    ("tampon_fichier", "Tampon", "Apposé à côté de la signature."),
)


def _etat_piece(valeur):
    """(etat, fiche) pour une valeur de champ document.

    etat vaut « local », « drive » ou « absent ». On ne rend « local » que si le
    fichier est REELLEMENT lisible : un champ rempli qui pointe vers du vide est
    un manque, et doit se voir comme tel.
    """
    valeur = str(valeur or "").strip()
    if not valeur:
        return "absent", None
    if documents.est_reference(valeur):
        f = documents.fiche_piece(valeur)
        return ("local", f) if f else ("absent", None)
    # Identifiant Drive : lisible ici seulement s'il est passe par le cache.
    import fichiers
    connu = (fichiers.lire(documents._INDEX_PIECES, {}) or {}).get(valeur)
    if not connu:
        return "drive", {"nom": "", "poids": "", "quand": "", "ref": valeur}
    chem = os.path.join(documents._PIECES, documents._sain(valeur))
    poids = ""
    try:
        o = float(os.path.getsize(chem))
        for u in ("o", "Ko", "Mo"):
            if o < 1024 or u == "Mo":
                poids = ("%d %s" if u == "o" else "%.1f %s") % (o, u)
                break
            o /= 1024
    except Exception:
        pass
    return "local", {"nom": connu.get("nom") or "", "poids": poids,
                     "quand": (connu.get("modifie") or "")[:10], "ref": valeur}


def _ligne(cle, type_piece, libelle, aide, valeur, porteur, portee):
    etat, f = _etat_piece(valeur)
    return {"cle": cle, "type": type_piece, "libelle": libelle, "aide": aide,
            "porteur": porteur, "portee": portee, "etat": etat,
            "nom": (f or {}).get("nom") or "", "poids": (f or {}).get("poids") or "",
            "quand": (f or {}).get("quand") or "", "ref": (f or {}).get("ref") or "",
            "valeur": str(valeur or "").strip()}


def inventaire(organisme=None):
    """Tout ce que DFM detient, pour cet organisme et pour les formations."""
    import profil
    import sessions as S
    org = organisme or profil.actif() or ""
    fiche = profil.charger(org) or {}

    # --- l'organisme ---
    pieces_org = [_ligne(cle, t, lib, aide, fiche.get(cle), org, "organisme")
                  for cle, t, lib, aide in PIECES_ORGANISME]

    images = []
    for cle, lib, aide in IMAGES_ORGANISME:
        chem = profil.chemin_image(cle, org)
        images.append({"cle": cle, "libelle": lib, "aide": aide,
                       "etat": "local" if chem else "absent",
                       "nom": os.path.basename(chem) if chem else ""})

    # --- les formations ---
    formations = []
    for code, f in sorted(S.FORMATIONS.items(),
                          key=lambda x: (x[1].get("nom_formation") or x[0]).lower()):
        lignes = [_ligne(cle, t, lib, aide, f.get(cle), code, "formation")
                  for cle, t, lib, aide in PIECES_FORMATION]
        convocation = []
        for v in (f.get("pieces_rappel") or []):
            if not str(v or "").strip():
                continue
            convocation.append(_ligne("pieces_rappel", "convocation",
                                      "Pièce jointe à la convocation",
                                      "Partie avec la convocation, à J-20.",
                                      v, code, "formation"))
        formations.append({"code": code,
                           "nom": f.get("nom_formation") or code,
                           "titre": f.get("titre_complet") or "",
                           "couleur": f.get("couleur") or "",
                           "pieces": lignes, "convocation": convocation})

    # --- les formateurs ---
    formateurs = []
    try:
        import formateurs as _f
        for g in _f.lister(org):
            p = _f.pieces(g["id"], org)
            formateurs.append({"id": g["id"], "nom": g["nom_complet"],
                               "manques": g.get("manques") or [],
                               "cv": p.get("cv"), "diplome": p.get("diplome"),
                               "autres": p.get("autres") or []})
    except Exception:
        pass

    # --- ce que DFM a produit ---
    produits = []
    racine = os.path.join(documents.RACINE, documents._sain(org))
    if os.path.isdir(racine):
        for session in sorted(os.listdir(racine)):
            if session.startswith("_"):
                continue
            chemin_s = os.path.join(racine, session)
            if not os.path.isdir(chemin_s):
                continue
            cats = []
            for cat in sorted(os.listdir(chemin_s)):
                d = os.path.join(chemin_s, cat)
                if not os.path.isdir(d):
                    continue
                fs = sorted(x for x in os.listdir(d) if not x.startswith("."))
                if fs:
                    cats.append({"categorie": cat, "nombre": len(fs),
                                 "fichiers": [{"nom": x,
                                               "ref": "/".join((documents._sain(org),
                                                                session, cat, x))}
                                              for x in fs]})
            if cats:
                titre = session
                try:
                    titre = S.session(session).get("titre_complet") or session
                except Exception:
                    pass
                produits.append({"session": session, "titre": titre, "categories": cats})

    # --- les justificatifs de veille ---
    veille = []
    try:
        import veille as _v
        base = os.path.join(_v.JUSTIFICATIFS, documents._sain(org))
        for axe in (sorted(os.listdir(base)) if os.path.isdir(base) else []):
            d = os.path.join(base, axe)
            if os.path.isdir(d):
                fs = [x for x in sorted(os.listdir(d)) if not x.startswith(".")]
                if fs:
                    veille.append({"axe": axe, "nombre": len(fs), "fichiers": fs})
    except Exception:
        pass

    return {"organisme": org, "marque": fiche.get("marque") or org,
            "pieces_organisme": pieces_org, "images": images,
            "formations": formations, "formateurs": formateurs,
            "produits": produits, "veille": veille}


def resume(inv):
    """Les trois nombres qui disent l'etat : posees, manquantes, restees au Drive."""
    local = manque = drive = 0
    for p in inv["pieces_organisme"]:
        local += p["etat"] == "local"; manque += p["etat"] == "absent"; drive += p["etat"] == "drive"
    for f in inv["formations"]:
        for p in f["pieces"] + f["convocation"]:
            local += p["etat"] == "local"; manque += p["etat"] == "absent"; drive += p["etat"] == "drive"
    for i in inv["images"]:
        local += i["etat"] == "local"; manque += i["etat"] == "absent"
    return {"local": local, "manque": manque, "drive": drive}
