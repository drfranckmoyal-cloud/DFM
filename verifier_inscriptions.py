# -*- coding: utf-8 -*-
"""Controle : toute demande recue est-elle bien dans le suivi ?

    venv/bin/python verifier_inscriptions.py [code_session]

POURQUOI CETTE ETAPE EXISTE. Le 9 octobre 2026, quatre demandes ont ete
marquees « reprises » sans que la fiche soit creee. Quatre praticiennes
inscrites le 8 au soir n'ont rien recu pendant CINQ JOURS, et rien ne l'a dit —
ni ecran, ni alerte, ni rapport. On ne l'a su qu'en comparant a la main, parce
que Franck trouvait une liste etrange.

DEUX CORRECTIONS ONT SUIVI : l'importateur relit le suivi avant de poser sa
marque, et un numero attribue d'office n'ecrase plus personne. Elles rendent
l'incident improbable. Elles ne le rendent pas IMPOSSIBLE, et surtout elles ne
le rendent pas VISIBLE s'il revient sous une autre forme.

C'est le role de ce controle : il ne repare rien, il compare. A chaque passage,
il met face a face ce que le formulaire a recu et ce que le suivi contient. Au
moindre ecart il echoue, donc il s'affiche en rouge dans la fenetre du
traitement. La garantie n'est pas « ca n'arrivera plus » — c'est « vous le
saurez dans la demi-journee » .

NON BLOQUANT. Un controle qui arrete la chaine ferait rater conventions,
factures et attestations pour signaler un ecart d'une ligne. Il parle, il
n'interrompt pas.
"""
import sys

import inscription as I
import sessions as _s
import suivi

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CODE = ARGS[0] if ARGS else None

# Au-dela de ce delai, une demande qui n'est toujours pas reprise n'est plus
# « en route » : elle est coincee. Deux passages par jour, donc douze heures
# laissent passer le cas normal et attrapent le cas anormal.
HEURES_AVANT_ALERTE = 18


def _vieille_de(brut):
    """Age d'une demande, en heures. None si la date ne se lit pas."""
    from datetime import datetime, timezone
    s = str(brut or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - d).total_seconds() / 3600.0


def main():
    try:
        toutes = I._sb("Inscriptions?select=*")
    except Exception as e:
        print("-> Boite aux lettres injoignable : %s" % str(e)[:120])
        print("   Le controle ne conclut rien. Ce n'est pas un ecart.")
        return 0

    codes = [CODE] if CODE else sorted(_s.SESSIONS)
    soucis = []

    for code in codes:
        if code not in _s.SESSIONS:
            continue
        lot = [e for e in toutes if (e.get("code_session") or "") == code]
        if not lot:
            continue
        try:
            connus = {(l.get("mail") or "").strip().lower()
                      for l in suivi.lire_lignes_de(code) if l.get("mail")}
        except Exception as e:
            print("   Suivi de %s illisible : %s" % (code, str(e)[:90]))
            continue

        absents = [e for e in lot
                   if (e.get("mail") or "").strip().lower() not in connus]
        for e in absents:
            qui = ("%s %s" % (e.get("prenom") or "", e.get("nom") or "")).strip()
            etat = "reprise" if e.get("importee_le") else "pas encore reprise"
            soucis.append("%s <%s> a demandé %s — %s, et ne figure PAS dans le suivi"
                          % (qui, e.get("mail") or "?", code, etat))

        for e in lot:
            if e.get("importee_le"):
                continue
            age = _vieille_de(e.get("horodateur"))
            if age is not None and age > HEURES_AVANT_ALERTE:
                qui = ("%s %s" % (e.get("prenom") or "", e.get("nom") or "")).strip()
                soucis.append("%s <%s> attend depuis %d h sans être reprise"
                              % (qui, e.get("mail") or "?", age))

    # LES ORPHELINES NE SE RATTACHENT A AUCUNE SESSION, donc aucune etape de
    # session ne les verra jamais. Si on ne les regarde pas ici, personne ne les
    # regarde : ce sont de vraies personnes inscrites sur une session renommee
    # ou supprimee depuis.
    orphelines = [e for e in toutes
                  if (e.get("code_session") or "") not in _s.SESSIONS]
    for e in orphelines:
        qui = ("%s %s" % (e.get("prenom") or "", e.get("nom") or "")).strip()
        soucis.append("%s <%s> s'est inscrit sur « %s », session inconnue de DFM"
                      % (qui, e.get("mail") or "?", e.get("code_session") or "(vide)"))

    total = len([e for e in toutes
                 if not CODE or (e.get("code_session") or "") == CODE])
    if not soucis:
        print("-> %d demande(s) controlee(s) : toutes sont dans le suivi." % total)
        return 0

    print("-> %d ECART(S) entre les demandes recues et le suivi :" % len(soucis))
    for s in soucis:
        print("   . " + s)
    print("   Une demande recue et absente du suivi, c'est quelqu'un qui attend")
    print("   une convention qui ne partira jamais. A regarder aujourd'hui.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
