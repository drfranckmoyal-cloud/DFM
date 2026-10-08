"""Reprend dans le suivi les demandes recues par le formulaire public.

    python3 importer_demandes.py [<code_session>]

Sans argument : toutes les sessions. C'est le pendant de
importer_inscriptions.py, qui va chercher les reponses d'un formulaire Google ;
celui-ci lit la table remplie par notre propre page.

LES DEUX PEUVENT COEXISTER. Une session alimentee par l'ancien formulaire
continue de l'etre ; une session publiee sur la nouvelle page passe par ici.
Rien n'oblige a tout basculer le meme jour.

CE QUI EST REPRIS DE L'IMPORT GOOGLE, MOT POUR MOT : la regle de capacite, le
passage en file d'attente quand la session est pleine ou cloturee, le sort des
demandes de rappel. Deux imports qui jugeraient differemment finiraient par
produire deux comportements sur la meme question.

IDEMPOTENT. Chaque demande reprise est marquee « importee_le » DANS SUPABASE,
avant meme d'ecrire la suite : une interruption ne peut pas la faire reprendre
deux fois, et deux lignes de suivi pour une personne produiraient deux
conventions.
"""
import sys
from datetime import datetime

import inscription as I
import journal
import sessions as _s
import suivi

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CODE = ARGS[0] if ARGS else None

# Les champs du formulaire, et leur colonne dans le suivi. Nommes plutot que
# recopies par position : une question deplacee ne doit rien decaler.
CHAMPS = ("nom", "prenom", "mail", "telephone", "ville", "demande", "connu_par",
          "dejeuner", "restrictions", "image", "pmr", "fonction")


def _horodateur(brut):
    """L'horodatage de Supabase, dans la forme du suivi.

    Supabase rend de l'ISO (« 2026-08-18T07:50:42.546896+00:00 ») ; le suivi
    attend « 18/08/2026 09:50:42 ». Cette valeur SERT DE MARQUE D'UNICITE dans
    l'onglet : mal formee, elle ferait reimporter la personne au passage suivant.
    """
    s = str(brut or "").strip()
    if not s:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone()
        return d.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return s[:19]


def _capacite(code):
    """(occupees, maxi, complete) — la meme regle que l'import Google."""
    try:
        lignes = suivi.lire_lignes_de(code)
    except Exception:
        return 0, 0, False
    occupees = len([l for l in lignes
                    if "recontact" not in (l["demande"] or "").lower()
                    and not l["annule_le"] and not l["annulation_demandee_le"]
                    and suivi.calculer_statut(l) != "File d'attente"])
    maxi = int(_s.session(code).get("places_max") or 0)
    return occupees, maxi, (maxi > 0 and occupees >= maxi)


def traiter(code, demandes):
    """Reprend les demandes d'UNE session. Rend le nombre de lignes creees."""
    S = _s.session(code)
    print("\n-> Session : %s (%s)" % (S.get("nom_formation") or "?", code))

    # LES DEJA-CONNUS PROTEGENT CONTRE UNE MARQUE PERDUE. « importee_le » est
    # la garde principale ; celle-ci rattrape le cas ou elle n'aurait pas ete
    # ecrite — reseau coupe entre l'ecriture du suivi et le marquage.
    try:
        connus = {(l.get("mail") or "").strip().lower()
                  for l in suivi.lire_lignes_de(code) if l.get("mail")}
    except Exception as e:
        print("   Suivi illisible : %s" % str(e)[:120])
        print("   Rien n'est repris pour cette session.")
        return 0

    occupees, maxi, complete = _capacite(code)
    etat = _s.etat(code)
    cloturee = (etat.get("statut_session") or "ouverte") == "cloturee"
    en_attente = complete or cloturee
    print("   Capacite : %s/%s%s" % (occupees, maxi, "  COMPLET" if complete else ""))
    if en_attente:
        motif = "session cloturee" if cloturee else "capacite atteinte"
        print("   %s : les confirmations partent en file d'attente." % motif.upper())

    quand = datetime.now().strftime("%d/%m/%Y %H:%M")
    a_creer, reprises, ignorees = [], [], 0
    for d in demandes:
        mail = (d.get("mail") or "").strip().lower()
        qui = ((d.get("prenom") or "") + " " + (d.get("nom") or "")).strip() or mail
        if mail and mail in connus:
            # Deja dans le suivi : la marque a du se perdre. On la repose sans
            # rien recreer, plutot que de laisser la demande revenir sans fin.
            print("   . %-28s deja dans le suivi, marquee sans doublon" % qui)
            ignorees += 1
            try:
                I.marquer_importee(d["id"])
            except Exception:
                pass
            continue
        ligne = {c: (d.get(c) or "") for c in CHAMPS}
        ligne["horodateur"] = _horodateur(d.get("horodateur"))
        ligne["date_formation"] = S.get("date_texte") or ""
        ligne["montant_du"] = str(S.get("tarif") or "")
        rappel = "recontact" in (ligne["demande"] or "").lower()
        a_creer.append((d, ligne, qui, rappel))
        marque = "à recontacter" if rappel else ("file d'attente" if en_attente else "inscrit")
        print("   . %-28s %s" % (qui, marque))

    if not a_creer:
        if ignorees:
            print("   %d demande(s) deja connue(s), rien de neuf." % ignorees)
        else:
            print("   Rien a reprendre.")
        return 0

    try:
        numeros = suivi.ajouter_plusieurs([l for _d, l, _q, _r in a_creer], code)
    except Exception as e:
        print("   ECHEC de l'ecriture dans le suivi : %s" % str(e)[:160])
        print("   AUCUNE demande n'est marquee : le prochain passage reprendra tout.")
        return 0

    for (d, ligne, qui, rappel), numero in zip(a_creer, numeros):
        # LA MARQUE D'ABORD. Si le journal ou la file d'attente echouent ensuite,
        # la ligne de suivi existe deja : la reprendre creerait un doublon.
        try:
            I.marquer_importee(d["id"])
        except Exception as e:
            print("   ATTENTION : %s repris mais non marque (%s)." % (qui, str(e)[:70]))
            print("   Verifiez le suivi avant le prochain passage.")
        try:
            if rappel:
                journal.ecrire("Demande de rappel reçue", qui, "à recontacter", "", code)
            elif en_attente:
                journal.ecrire("Place en file d'attente", qui,
                               "session cloturee" if cloturee else "capacite atteinte", "", code)
            else:
                journal.ecrire("Nouvelle inscription", qui, d.get("mail") or "", "", code)
        except Exception:
            pass

    # LA FILE D'ATTENTE NE CONCERNE QUE LES CONFIRMATIONS. Une demande de
    # rappel n'attend pas une place : elle attend un appel.
    if en_attente:
        for (d, ligne, qui, rappel), numero in zip(a_creer, numeros):
            if rappel:
                continue
            try:
                suivi.ecrire(numero, "file_attente_le", quand, code)
            except Exception as e:
                print("   %s : file d'attente non posee (%s)" % (qui, str(e)[:60]))

    try:
        suivi.rafraichir_statuts(code)
    except Exception:
        pass

    print("   -> %d ligne(s) creee(s)." % len(a_creer))
    return len(a_creer)


def main():
    if CODE and CODE not in _s.SESSIONS:
        print("-> Session inconnue : %s" % CODE)
        raise SystemExit(1)

    demandes = I.en_attente()
    if CODE:
        demandes = [d for d in demandes if d.get("code_session") == CODE]
    if not demandes:
        print("-> Aucune demande a reprendre.")
        raise SystemExit(0)

    # ON REGROUPE PAR SESSION : la capacite, la cloture et la file d'attente se
    # jugent session par session, jamais demande par demande.
    par_session = {}
    orphelines = []
    for d in demandes:
        c = d.get("code_session") or ""
        if c in _s.SESSIONS:
            par_session.setdefault(c, []).append(d)
        else:
            orphelines.append(d)

    print("-> %d demande(s) en attente, sur %d session(s)."
          % (len(demandes), len(par_session)))
    total = 0
    for c in sorted(par_session):
        total += traiter(c, par_session[c])

    if orphelines:
        # ON NE LES MARQUE PAS. Une session supprimee apres une inscription
        # laisse quelqu'un qui a rempli le formulaire et attend une reponse ;
        # l'effacer en silence serait le pire des traitements.
        print("\n-> ATTENTION : %d demande(s) visent une session inconnue de DFM."
              % len(orphelines))
        for d in orphelines[:6]:
            print("   . %s %s — session « %s »"
                  % (d.get("prenom") or "", d.get("nom") or "", d.get("code_session")))
        print("   Elles restent en attente : a traiter a la main.")

    print("\n-> Termine : %d inscription(s) reprise(s)." % total)


if __name__ == "__main__":
    main()
