# -*- coding: utf-8 -*-
"""Classe des conventions signees RECUES PAR MAIL et marque la ligne de suivi.

Ces praticiens ont renvoye leur convention signee a lbs.dentalformations@gmail.com,
hors du circuit de signature electronique de DFM. Le document existe : il est range
au meme endroit que les conventions produites par DFM, et la ligne de suivi le dit.

VERROU : une ligne qui porte DEJA une signature n'est jamais touchee. Celui qui a
resigne dans DFM garde la convention de DFM — c'est elle qui fait foi.
"""
import json, os, sys
import suivi, documents

ENTRANTS = "/home/dfm/entrants"
PLAN = json.load(open(os.path.join(ENTRANTS, "plan.json"), encoding="utf-8"))
EXEC = "--executer" in sys.argv

for e in PLAN:
    code = e["code"]
    cibles = [l for l in suivi.lire_lignes_de(code)
              if (l.get("mail") or "").strip().lower() == e["mail"].strip().lower()]
    if len(cibles) != 1:
        print("REFUS %s : %d ligne(s) trouvee(s)." % (e["mail"], len(cibles)))
        continue
    ligne = cibles[0]
    qui = ("%s %s" % (ligne["prenom"], ligne["nom"])).strip()
    if (ligne.get("signe_le") or "").strip():
        print("PASSE  %-28s deja signe dans DFM le %s : on garde la convention DFM."
              % (qui, ligne["signe_le"]))
        continue
    chemin = os.path.join(ENTRANTS, e["fichier"])
    octets = open(chemin, "rb").read()
    nom_pdf = "Convention SIGNEE - %s.pdf" % qui
    print("CLASSE %-28s %-9s %7d o   signe le %s" % (qui, code[:9], len(octets), e["signe_le"]))
    if not EXEC:
        continue
    ref, lien, souci = documents.ranger(code, "convention_signee", nom_pdf, octets)
    if not ref:
        print("       ECHEC rangement : %s" % souci)
        continue
    detail = "convention signee recue par mail le %s (lbs.dentalformations@gmail.com) - %s" % (
        e["signe_le"], lien or ref)
    suivi.marquer(ligne, "signe_le", valeur=e["signe_le"], code=code, detail=detail)
    if lien:
        suivi.ecrire(ligne["_numero"], "lien_pdf", lien, code)
        ligne["lien_pdf"] = lien
    suivi.marquer(ligne, "convention_pdf_le", code=code, detail=lien or ref)
    print("       range : %s%s" % (ref, "" if lien else "   (pas de copie Drive)"))
print("Termine." if EXEC else "SIMULATION : rien n'a ete ecrit. Relancer avec --executer.")
