# -*- coding: utf-8 -*-
"""Les formations d'AVANT DFM — reprises le 15/11/2026.

POURQUOI. De septembre 2025 a juin 2026, LBS FORMATION (Smileclub) a tenu cinq
sessions hors de DFM : leurs inscrits vivaient dans des tableaux Numbers, leurs
conventions, factures et attestations dans les dossiers « FM FORMATION ». Le
premier bilan pedagogique et financier de LBS couvre pourtant tout son premier
exercice (30/06/2025 - 31/12/2026) : sans ces sessions, il serait faux.

D'OU VIENNENT LES DONNEES. Un rapprochement fait le 15/11/2026 entre les releves
Banque Populaire du compte de LBS (septembre 2025 a octobre 2026) et, pour chaque
session, le tableau Numbers, les conventions, les factures PDF et les
attestations. Chaque personne y porte un STATUT (rapproche, ecart de montant,
facture sans paiement retrouve...) et la liste de ses ECARTS. Le detail complet
est dans le classeur « Rapprochement pré-DFM LBS.xlsx » (Bureau du Mac).

LECTURE SEULE. Ces sessions ne se gerent pas dans DFM : on n'y envoie rien, on
n'y signe rien. Le fichier « pre_dfm.json » est une archive, refaite s'il le
faut par le rapprochement, jamais modifiee a la main par l'interface.

« PRESENT » veut dire : une attestation est archivee. Aucun emargement signe ne
l'est ; pour les usures de janvier 2026, aucune attestation non plus.
"""
import io
import json
import os
import datetime as dt

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER = os.path.join(DOSSIER, "pre_dfm.json")

STATUTS = ["Facturé, paiement non retrouvé", "Présent(e) sans facture ni paiement", "Écart de montant",
           "Payé sans facture", "Inscription sans suite visible", "Rapproché", "Invité(e)",
           "À recontacter (sans suite)", "Prospect sans suite"]
A_VERIFIER = set(STATUTS[:5])


def donnees():
    try:
        d = json.load(io.open(FICHIER, encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def sessions(organisme=None):
    """{code: fiche}, du plus ancien au plus recent, pour un organisme."""
    s = donnees().get("sessions") or {}
    out = {c: f for c, f in s.items() if not organisme or f.get("organisme") == organisme}
    return dict(sorted(out.items(), key=lambda x: (x[1].get("jours") or [""])[0]))


def personnes(code=None, organisme=None):
    codes = set(sessions(organisme))
    return [p for p in (donnees().get("personnes") or [])
            if p.get("session") in codes and (code is None or p.get("session") == code)]


def _d(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except Exception:
        try:
            return dt.datetime.strptime(str(s), "%d/%m/%Y").date()
        except Exception:
            return None


def pour_bilan(organisme, debut, fin):
    """Ce que les sessions pre-DFM apportent a un exercice : des lignes de
    session au format de bpf.chiffres, les factures, et des alertes."""
    lignes, factures, alertes, formateurs_h = [], [], [], 0.0
    for code, s in sessions(organisme).items():
        tous = [x for x in (_d(j) for j in s.get("jours") or []) if x]
        dedans = [j for j in tous if debut <= j <= fin]
        if not dedans:
            continue
        h = float(s.get("heures") or 0) * len(dedans) / max(len(tous), 1)
        ps = personnes(code, organisme)
        presents = [p for p in ps if p.get("present")]
        payants_sans_preuve = [p for p in ps if not p.get("present") and (p.get("facture_total") or p.get("paye_total"))
                               and p.get("statut") not in ("Invité(e)",)]
        if not s.get("presence_archivee", True):
            alertes.append("%s (pré-DFM) : aucune attestation archivée — %d inscrits facturés ou payants, "
                           "présence à confirmer avant de les compter." % (s.get("formation"), len(payants_sans_preuve)))
        lignes.append({"code": code, "titre": "%s — avant DFM" % (s.get("titre") or code),
                       "dates": ", ".join(j.strftime("%d/%m/%Y") for j in tous), "jours": len(dedans),
                       "jours_total": len(tous), "heures": round(h, 1), "mode": "individuel",
                       "formateur": "Dr Franck Moyal", "confirmes": len(presents),
                       "a_confirmer": len(payants_sans_preuve) if not s.get("presence_archivee", True) else 0,
                       "prevus": 0, "heures_stagiaires": round(len(presents) * h, 1), "passee": True,
                       "pre_dfm": True})
        formateurs_h += h
        for p in ps:
            for f in p.get("factures") or []:
                if f.get("retenue") is False:
                    continue      # un numero en double : seule la version payee compte
                d = _d(f.get("date"))
                if d and debut <= d <= fin:
                    factures.append({"numero": f.get("numero") or "sans n°", "date": d,
                                     "client": f.get("adressee_a") or p.get("nom"), "session": code,
                                     "type": f.get("type") or "individuel", "total": float(f.get("total") or 0),
                                     "pre_dfm": True})
    return lignes, factures, alertes, formateurs_h


def sous_traitance(organisme, debut, fin):
    """Les sommes recues d'autres organismes de formation qui ont confie une
    action a LBS (UP CARE, 15/11/2026). Le bilan les declare a part : produits
    « contrats avec d'autres organismes de formation », stagiaires au cadre F-2."""
    if not sessions(organisme):
        return []
    out = []
    for c in donnees().get("credits") or []:
        if c.get("nature") != "sous-traitance":
            continue
        d = _d(c.get("date"))
        if d and debut <= d <= fin:
            out.append({"date": d, "montant": float(c.get("montant") or 0), "payeur": c.get("payeur") or ""})
    return out


def csv_lignes(organisme):
    out = [["Session", "Dates", "Nom", "Mail", "Statut", "Factures", "Facturé", "Paiements", "Encaissé",
            "Attestation", "Convention", "Écarts"]]
    e = lambda x: ("%.2f" % (x or 0)).replace(".", ",")
    for code, s in sessions(organisme).items():
        for p in personnes(code, organisme):
            out.append([s.get("formation"), " / ".join(s.get("jours") or []), p.get("nom"), p.get("mail"), p.get("statut"),
                        " ; ".join("%s %s %s" % (f.get("numero"), f.get("date"), e(f.get("total"))) for f in p.get("factures") or []),
                        e(p.get("facture_total")),
                        " ; ".join("%s %s %s" % (x.get("date"), e(x.get("montant")), x.get("payeur")) for x in p.get("paiements") or []),
                        e(p.get("paye_total")), "oui" if p.get("present") else "", p.get("convention") or "",
                        " ; ".join(p.get("ecarts") or [])])
    return out
