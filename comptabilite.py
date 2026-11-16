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
JUSTIFIE = ("Justifié", "Justifié (versement Stripe détaillé)", "Justifié (sous-traitance)")
A_TRAITER_ENC = ("Non rattaché", "Sans facture", "Versement Stripe — paiement sans facture",
                 "Justifié — montant différent", "Versement Stripe — relevé à joindre",
                 "Sous-traitance — facture à joindre", "Hors formation — justificatif à joindre")
ENCAISSEE = ("Encaissée", "Encaissée (carte)")
A_TRAITER_FAC = ("Payée selon DFM, virement non retrouvé", "Non encaissée", "Facture d'essai",
                 "Inscription annulée", "Encaissée — montant différent", "Payée par carte",
                 "Payée par carte, versement après le dernier relevé", "Payée par carte, versement Stripe à venir")
# Une facture annulee par une facture rectificative (16/11/2026) : gardee a la
# liste, son numero ne disparait pas, mais elle ne compte plus dans les totaux.
REMPLACEE = "Annulée et remplacée"
ANNULEE_AVOIR = "Annulée par avoir"
AVOIR = "Avoir"
CLASSEES = (REMPLACEE, ANNULEE_AVOIR, AVOIR)


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
    just = [e for e in enc if e["statut"] in JUSTIFIE]
    return {
        "nb_enc": len(enc), "total_enc": round(sum(e["montant"] for e in enc), 2),
        "nb_just": len(just), "total_just": round(sum(e["montant"] for e in just), 2),
        "nb_fac": len([f for f in fac if f["statut"] not in (REMPLACEE, AVOIR)]),
        "total_fac": round(sum(f["montant"] for f in fac if f["statut"] != REMPLACEE), 2),
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


# ---------------------------------------------------------------------------
# L'EXPORT DES VENTES POUR LE COMPTABLE — 16/11/2026
#
# Demande de Franck : « exporter toutes les ventes ET les factures qui vont avec
# pour pouvoir transmettre en batch a la compta ». Une vente = une piece emise :
# facture, facture rectificative ou avoir. La source est VIVANTE : le registre
# des factures de DFM (tout ce que DFM a emis), complete des factures d'avant DFM
# et de la sous-traitance que seul le rapprochement connait. Le reglement vient
# du rapprochement bancaire quand il a vu la piece, sinon de la ligne
# d'inscription.
# ---------------------------------------------------------------------------
import glob as _glob
import re as _re
import unicodedata as _ud


def _jetons(t):
    t = "".join(c for c in _ud.normalize("NFD", str(t or "")) if _ud.category(c) != "Mn").lower()
    return {x for x in _re.split(r"[^a-z]+", t) if len(x) >= 3}


def _iso(fr):
    """« 16/11/2026 » ou « 2026-11-16 » -> « 2026-11-16 » ; "" si illisible."""
    s = str(fr or "").strip()
    m = _re.match(r"^(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
    return s[:10] if _re.match(r"^\d{4}-\d{2}-\d{2}", s) else ""


def _fr(iso):
    s = _iso(iso)
    return "%s/%s/%s" % (s[8:10], s[5:7], s[:4]) if s else ""


def _pdf(organisme, numero, *indices):
    """Le PDF d'une piece, chemin RELATIF a DFM, ou "". Cherche d'abord aux
    adresses connues (rapprochement, registre), puis dans les dossiers « facture »
    des sessions de l'organisme."""
    for rel in indices:
        if rel and not str(rel).startswith("http") and chemin_piece(organisme, rel):
            return str(rel).lstrip("/")
    if not numero:
        return ""
    racine = os.path.join(DOSSIER, "documents", organisme)
    for motif in (os.path.join(racine, "*", "facture", "* %s - *.pdf" % numero),
                  os.path.join(racine, "compta", "*", "%s *.pdf" % numero)):
        for p in sorted(_glob.glob(motif)):
            rel = os.path.relpath(p, DOSSIER)
            if chemin_piece(organisme, rel):
                return rel
    return ""


def _reglement_dfm(code, client, cache):
    """Ce que la ligne d'inscription dit du reglement, ou None."""
    if code not in cache:
        try:
            import suivi as _s
            cache[code] = _s.lire_lignes_de(code)
        except Exception:
            cache[code] = []
    t = _jetons(client)
    best, bs = None, 0
    for l in cache[code]:
        s = len(t & _jetons("%s %s" % (l.get("prenom"), l.get("nom"))))
        if s > bs:
            best, bs = l, s
    if not best or bs < min(2, len(t)):
        return None
    try:
        recu = float(str(best.get("montant_recu") or 0).replace(",", "."))
    except ValueError:
        recu = 0.0
    return {"le": best.get("paiement_recu_le") or "", "mode": best.get("mode_paiement") or "",
            "reference": best.get("reference_paiement") or "", "recu": recu,
            "annule": bool(best.get("annule_le"))}


def ventes(organisme, du=None, au=None):
    """Toutes les pieces de vente de l'organisme, de la plus ancienne a la plus
    recente : factures, rectificatives, avoirs. « du » et « au » (AAAA-MM-JJ)
    bornent la DATE DE LA PIECE."""
    import factures as _F
    try:
        import sessions as _S
        libelles = {c: (s.get("titre_complet") or s.get("nom_formation") or "", s.get("date_texte") or "")
                    for c, s in (_S.SESSIONS or {}).items()}
    except Exception:
        libelles = {}
    compta = donnees(organisme)
    par_num = {}
    for f in compta.get("factures") or []:
        par_num.setdefault(f.get("numero"), f)
    # Les sessions d'avant DFM : leurs dates, et ce que chaque personne a verse.
    try:
        import pre_dfm as _P
        import jours as _J
        pre = _P.sessions(organisme)
        pre_dates = {c: _J.texte(_J.normaliser(s.get("jours") or [])) for c, s in pre.items()}
        pre_pers = _P.personnes(organisme=organisme)
    except Exception:
        pre, pre_dates, pre_pers = {}, {}, []
    # Les encaissements rapproches : la date et la nature de chacun.
    enc = {e["id"]: e for e in compta.get("encaissements") or [] if e.get("id")}

    def _depuis_banque(ids):
        """(le, mode, reference) du premier encaissement rapproche, ou None."""
        e = next((enc[i] for i in ids or [] if i in enc), None)
        if not e:
            return None
        mode = "carte (versement Stripe)" if e.get("nature") == "stripe" else (
            "virement (sous-traitance)" if e.get("nature") == "sous-traitance" else "virement")
        return _fr(e.get("date")), mode, e["id"]

    def _note(note):
        """La note du rapprochement, sans ce que la piece dit deja."""
        return [p for p in str(note or "").split(" ; ") if p and not p.startswith(
            ("annulée par l'avoir", "facture rectificative", "avoir sur"))]
    cache, sortie, vus = {}, [], set()

    for e in sorted(_F.tout().values(), key=lambda e: (_iso(e.get("date")), str(e.get("numero")))):
        if not isinstance(e, dict) or (e.get("organisme") or "") != organisme:
            continue
        num = e.get("numero") or ""
        if not num or num in vus:
            continue
        vus.add(num)
        c = par_num.get(num) or {}
        code = e.get("session") or ""
        titre, dates = libelles.get(code, ("", pre_dates.get(code, "")))
        titre = e.get("formation") or titre or (pre.get(code) or {}).get("titre") or ""
        if c.get("session_libelle") and " · " in c["session_libelle"]:
            titre = titre or c["session_libelle"].split(" · ")[0]
            dates = dates or c["session_libelle"].split(" · ")[-1]
        avoir = e.get("nature") == "avoir"
        type_piece = "Avoir" if avoir else ("Facture rectificative" if e.get("remplace") else "Facture")
        remarque = []
        if e.get("remplace"):
            remarque.append("annule et remplace %s" % e["remplace"])
        if e.get("remplacee_par"):
            remarque.append("annulée et remplacée par %s" % e["remplacee_par"])
        if e.get("avoir"):
            remarque.append("annulée par l'avoir %s" % e["avoir"])
        if avoir:
            remarque.append("avoir sur %s%s" % (e.get("annule") or "?", (" — " + e["motif"]) if e.get("motif") else ""))
        regle = {"le": "", "mode": "", "reference": "", "encaisse": c.get("encaisse") if c else None}
        statut = c.get("statut") or ""
        if not avoir:
            remarque += _note(c.get("note"))
        if not avoir and not e.get("remplacee_par") and code in libelles:
            r = _reglement_dfm(code, e.get("client"), cache)
            if r and r["le"] and not r["annule"]:
                regle.update(le=r["le"], mode=r["mode"], reference=r["reference"])
                if regle["encaisse"] is None:
                    regle["encaisse"] = r["recu"]
                    statut = statut or "Réglée selon DFM"
        if not avoir and not regle["le"] and c.get("encaissements"):
            b = _depuis_banque(c["encaissements"])
            if b:
                regle.update(le=b[0], mode=b[1], reference=b[2])
        if not avoir and not e.get("remplacee_par") and code in pre and not regle["le"]:
            tj = _jetons(e.get("client"))
            p = next((p for p in pre_pers if p["session"] == code and len(tj & _jetons(p["nom"])) >= min(2, len(tj))), None)
            pay = (p or {}).get("paiements") or []
            if pay:
                regle.update(le=_fr(pay[-1].get("date")), mode="virement", reference=pay[-1].get("id") or "")
                if regle["encaisse"] is None:
                    regle["encaisse"] = round(sum(x.get("montant") or 0 for x in pay), 2)
                    statut = statut or "Réglée (relevé bancaire)"
        if avoir:
            statut = AVOIR
        elif e.get("remplacee_par"):
            statut = REMPLACEE
        elif e.get("avoir"):
            statut = ANNULEE_AVOIR
        sortie.append({"numero": num, "type": type_piece, "date": _iso(e.get("date")), "client": e.get("client") or "",
                       "session": code, "formation": titre, "dates": dates, "montant": float(e.get("total") or 0),
                       "regle_le": regle["le"], "mode": regle["mode"], "reference": regle["reference"],
                       "encaisse": regle["encaisse"], "statut": statut or "Non réglée",
                       "remarque": " ; ".join(x for x in remarque if x),
                       "fichier": _pdf(organisme, num, c.get("chemin"), e.get("lien")), "origine": "DFM"})

    # Ce que seul le rapprochement connait : factures d'avant DFM, sous-traitance.
    for f in compta.get("factures") or []:
        num = f.get("numero") or ""
        if not str(f.get("origine") or "").startswith("avant DFM") or (num, f.get("client")) in vus:
            continue
        vus.add((num, f.get("client")))
        lib = f.get("session_libelle") or ""
        b = _depuis_banque(f.get("encaissements")) or ("", "", "")
        sortie.append({"numero": num, "type": "Facture", "date": _iso(f.get("date")), "client": f.get("client") or "",
                       "session": f.get("session") or "",
                       "formation": (pre.get(f.get("session")) or {}).get("titre") or lib.split(" · ")[0],
                       "dates": pre_dates.get(f.get("session")) or (lib.split(" · ")[-1] if " · " in lib else ""),
                       "montant": float(f.get("montant") or 0),
                       "regle_le": b[0], "mode": b[1], "reference": b[2], "encaisse": f.get("encaisse"),
                       "statut": f.get("statut") or "", "remarque": " ; ".join(_note(f.get("note"))),
                       "fichier": _pdf(organisme, "", f.get("chemin")), "origine": f.get("origine") or "avant DFM"})

    sortie = [v for v in sortie if (not du or v["date"] >= du) and (not au or v["date"] <= au)]
    sortie.sort(key=lambda v: (v["date"], v["numero"]))
    return sortie


def csv_ventes(liste):
    out = [["N° pièce", "Type", "Date", "Client", "Formation", "Dates de la formation", "Session",
            "Montant (€)", "Réglé le", "Mode", "Référence", "Encaissé (€)", "Statut", "Remarque", "Fichier PDF"]]
    for v in liste:
        out.append([v["numero"], v["type"], _fr(v["date"]), v["client"], v["formation"], v["dates"], v["session"],
                    _e(v["montant"]), v["regle_le"], v["mode"], v["reference"],
                    _e(v["encaisse"]) if v["encaisse"] is not None else "", v["statut"], v["remarque"],
                    v.get("_dans_zip") or ("" if v["fichier"] else "PDF manquant")])
    return out


def resume_ventes(liste):
    comptees = [v for v in liste if v["statut"] != REMPLACEE]
    return {"nb": len(liste), "nb_factures": len([v for v in liste if v["type"] != "Avoir"]),
            "nb_avoirs": len([v for v in liste if v["type"] == "Avoir"]),
            "total": round(sum(v["montant"] for v in comptees), 2),
            "sans_pdf": [v["numero"] for v in liste if not v["fichier"]]}


def export_ventes_zip(organisme, du=None, au=None, marque=""):
    """Le lot pour le comptable : le journal des ventes, les encaissements
    rapproches, et chaque piece en PDF rangee par mois. Rend (octets, liste)."""
    import csv
    from datetime import datetime as _dt
    liste = ventes(organisme, du, au)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        noms = set()
        for v in liste:
            p = chemin_piece(organisme, v["fichier"]) if v["fichier"] else None
            if not p:
                continue
            nom = "pieces/%s/%s" % (v["date"][:7] or "sans-date", os.path.basename(p))
            if nom not in noms:
                noms.add(nom)
                z.write(p, nom)
            v["_dans_zip"] = nom
        tous_enc = csv_encaissements(organisme)
        gardes = {e["id"] for e in donnees(organisme).get("encaissements") or []
                  if (not du or e["date"] >= du) and (not au or e["date"] <= au)}
        for nom, lignes in (("ventes.csv", csv_ventes(liste)),
                            ("encaissements.csv", tous_enc[:1] + [l for l in tous_enc[1:] if l[0] in gardes])):
            t = io.StringIO()
            w = csv.writer(t, delimiter=";")
            for l in lignes:
                w.writerow(l)
            z.writestr(nom, "﻿" + t.getvalue())
        r = resume_ventes(liste)
        fs = sorted(((donnees(organisme).get("stripe_detail") or {}).get("factures_stripe")) or [])
        periode = ("du %s au %s" % (_fr(du) or "début", _fr(au) or "ce jour")) if (du or au) else "toutes les pièces"
        z.writestr("LISEZ-MOI.txt", "\n".join([
            "Export des ventes — %s" % (marque or organisme),
            "Fait le %s depuis DFM. Période : %s (date de la pièce)." % (_dt.now().strftime("%d/%m/%Y à %H:%M"), periode),
            "",
            "ventes.csv        une ligne par pièce : facture, facture rectificative ou avoir (montant négatif).",
            "                  « Annulée et remplacée » : la rectificative la remplace ; elle ne compte plus.",
            "                  « Annulée par avoir » : l'avoir, négatif, la compense.",
            "encaissements.csv les entrées d'argent du compte bancaire et la pièce qui justifie chacune",
            "                  (rapprochement jusqu'au dernier relevé fourni).",
            "pieces/AAAA-MM/   chaque pièce en PDF, rangée par mois d'émission.",
            "",
            "%d pièces (%d factures, %d avoirs) ; total net : %s €." % (r["nb"], r["nb_factures"], r["nb_avoirs"], _e(r["total"])),
            ("Pièces sans PDF dans DFM : %s." % ", ".join(r["sans_pdf"])) if r["sans_pdf"] else "Toutes les pièces ont leur PDF.",
            "",
            "TVA non applicable, article 293 B du CGI.",
            "Paiements par carte : encaissés par Stripe, qui verse le net de ses frais sur le compte ;",
            "le détail, versement par versement, figure dans DFM, rubrique Comptabilité.",
        ] + ([
            "",
            "Factures Stripe : %s émises automatiquement par Stripe (%s à %s) pour des ventes"
            % (len(fs), fs[0], fs[-1]),
            "que DFM a aussi facturées. La pièce comptable est la facture DFM ; l'émission",
            "automatique par Stripe a été coupée le 16/11/2026.",
        ] if fs else [])) + "\n")
    return tampon.getvalue(), liste
