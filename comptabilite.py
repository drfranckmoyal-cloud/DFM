# -*- coding: utf-8 -*-
"""Le volet comptable : chaque encaissement avec sa piece, chaque facture avec
son encaissement — 15/11/2026.

POURQUOI. Franck prepare le bilan comptable de LBS FORMATION : il doit pouvoir
produire, pour chaque somme recue, la facture (ou la piece) qui la justifie, et
pour chaque facture emise, le reglement qui la solde. Jusqu'ici les deux vivaient
a part : les virements sur les releves de la banque, les factures dans DFM ou,
avant DFM, dans les dossiers « FM FORMATION ».

D'OU VIENNENT LES DONNEES. Le fichier « compta.json » est construit hors de DFM
par le rapprochement (dossier « LBS - Pré-DFM › travail (rapprochement) » du
Mac) : il lit les extraits de compte Banque Populaire, les factures d'avant DFM
et le registre des factures de DFM. Les factures d'avant DFM sont recopiees
sous documents/<organisme>/compta/pieces-pre-dfm/ ; celles de DFM restent a leur
place, sous documents/<organisme>/<session>/facture/.

PERIMETRE : l'activite 2026 (decision de Franck, 15/11/2026), releves jusqu'au
dernier extrait fourni. Un virement plus recent n'y est pas encore.

LECTURE SEULE POUR L'INSTANT. L'etape suivante — combler les vides, consigner
les explications — ecrira a cote, sans toucher a ce registre.
"""
import io
import json
import os
import zipfile

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER = os.path.join(DOSSIER, "compta.json")

# Les statuts qui demandent un geste, dans l'ordre ou on les traite.
A_TRAITER_ENC = ("Non rattaché", "Sans facture", "Justifié — montant différent",
                 "Versement Stripe — relevé à joindre", "Sous-traitance — facture à joindre",
                 "Hors formation — justificatif à joindre")
A_TRAITER_FAC = ("Payée selon DFM, virement non retrouvé", "Non encaissée", "Facture d'essai",
                 "Inscription annulée", "Encaissée — montant différent", "Payée par carte")


def donnees(organisme=None):
    try:
        d = json.load(io.open(FICHIER, encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(d, dict) or (organisme and d.get("organisme") != organisme):
        return {}
    return d


def chemin_piece(organisme, relatif):
    """Le chemin absolu d'une piece, ou None. Refuse tout ce qui sortirait des
    documents de l'organisme : le lien vient d'un fichier, mais il passe dans
    une adresse que n'importe qui peut modifier."""
    rel = str(relatif or "").strip().lstrip("/")
    racine = os.path.realpath(os.path.join(DOSSIER, "documents", organisme))
    p = os.path.realpath(os.path.join(DOSSIER, rel))
    if not rel or not p.startswith(racine + os.sep) or not p.lower().endswith(".pdf"):
        return None
    return p if os.path.isfile(p) else None


def resume(organisme):
    d = donnees(organisme)
    enc = d.get("encaissements") or []
    fac = d.get("factures") or []
    just = [e for e in enc if e["statut"] == "Justifié"]
    return {
        "nb_enc": len(enc), "total_enc": round(sum(e["montant"] for e in enc), 2),
        "nb_just": len(just), "total_just": round(sum(e["montant"] for e in just), 2),
        "nb_fac": len(fac), "total_fac": round(sum(f["montant"] for f in fac), 2),
        "fac_enc": round(sum(f["montant"] for f in fac if f["statut"].startswith("Encaissée")), 2),
    }


def _e(x):
    return ("%.2f" % float(x or 0)).replace(".", ",")


def csv_encaissements(organisme):
    out = [["Réf.", "Date", "Montant", "Payeur", "Nature", "Rattaché à", "Session", "Pièce(s)", "Statut", "Écart", "Libellé du relevé"]]
    for e in donnees(organisme).get("encaissements") or []:
        r = e.get("rattachement") or {}
        out.append([e["id"], e["date"], _e(e["montant"]), e["payeur"], e["nature"], r.get("nom", ""), r.get("session_libelle", ""),
                    " ; ".join("%s (%s €)" % (p["numero"], _e(p["montant"])) for p in e.get("pieces") or []),
                    e["statut"], e.get("ecart", ""), e.get("libelle", "")])
    return out


def csv_factures(organisme):
    out = [["Numéro", "Date", "Client", "Session", "Montant", "Origine", "Encaissé", "Encaissements", "Statut", "Note", "Fichier"]]
    for f in donnees(organisme).get("factures") or []:
        out.append([f["numero"], f["date"], f["client"], f["session_libelle"], _e(f["montant"]), f["origine"],
                    _e(f.get("encaisse")), " ; ".join(f.get("encaissements") or []), f["statut"], f.get("note", ""),
                    os.path.basename(f.get("chemin") or "")])
    return out


def dossier_zip(organisme):
    """Le dossier pour l'expert-comptable : les deux tableaux et toutes les
    pieces disponibles, rangees par mois. Rend les octets du ZIP."""
    import csv
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, lignes in (("encaissements.csv", csv_encaissements(organisme)), ("factures.csv", csv_factures(organisme))):
            t = io.StringIO()
            w = csv.writer(t, delimiter=";")
            for l in lignes:
                w.writerow(l)
            z.writestr(nom, "﻿" + t.getvalue())
        vus = set()
        for f in donnees(organisme).get("factures") or []:
            p = chemin_piece(organisme, f.get("chemin"))
            if not p or p in vus:
                continue
            vus.add(p)
            mois = (f.get("date") or "0000-00")[:7]
            z.write(p, "factures/%s/%s" % (mois, os.path.basename(p)))
    return tampon.getvalue()
