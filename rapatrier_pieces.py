"""Rapatrie sur le disque toutes les pieces qui ne vivent encore que dans le Drive.

POURQUOI CE SCRIPT EXISTE. Le 18/08/2026, la migration hors Google s'est achevee
cote CODE : plus aucun script d'envoi ni de generation n'a besoin du Drive pour
travailler. Mais certains FICHIERS, eux, n'avaient jamais ete copies en local —
reglements interieurs, plans d'acces, articles joints aux convocations. Tant
qu'ils ne sont qu'a distance, une convocation part sans ses pieces jointes.

A LANCER UNE FOIS, autorisation Google valide. Ensuite, plus jamais : chaque
piece lue passe desormais par le cache, qui se remplit tout seul.

    python3 rapatrier_pieces.py            # rapatrie ce qui manque
    python3 rapatrier_pieces.py --etat     # dit seulement ce qui manque

IL NE TOUCHE A RIEN D'AUTRE. Aucune fiche modifiee, aucun fichier distant
deplace ni supprime : il ne fait que descendre des copies.
"""
import json
import sys

import documents
import profil
import sessions


def _pieces_attendues():
    """Chaque identifiant Drive attendu, avec ce qu'il est et pour qui.

    On passe par session(), pas par les fiches brutes : c'est elle qui applique
    l'organisme PROPRIETAIRE, et le reglement interieur de DSF n'est pas celui
    de Smileclub.
    """
    LISIBLE = {"reglement": "règlement intérieur", "rib": "RIB",
               "acces": "plan d'accès", "programme": "programme",
               "convocation": "pièce jointe à la convocation"}
    vus = {}

    def note(ident, quoi, pour):
        ident = str(ident or "").strip()
        if ident:
            vus.setdefault(ident, {"quoi": quoi, "libelle": LISIBLE.get(quoi, quoi),
                                   "pour": []})["pour"].append(pour)

    # LA CLE EST CELLE DE documents.PIECES, PAS UN LIBELLE HUMAIN : elle est
    # inscrite dans l'index du cache, et deux graphies du meme role — « RIB » et
    # « rib » — y font deux entrees pour une seule chose. Le libelle lisible
    # vit a cote, sous « libelle ».
    for code in sessions.SESSIONS:
        S = sessions.session(code)
        note(S.get("reglement_interieur_id"), "reglement", code)
        note(S.get("programme_id"), "programme", code)
        note(S.get("acces_id"), "acces", code)
        note(S.get("rib_id"), "rib", code)
        for p in (S.get("pieces_rappel") or []):
            note(p, "convocation", code)

    # Les pieces posees sur les ORGANISMES, qu'aucune session ne reclame
    # peut-etre aujourd'hui mais qu'une session de demain reclamera.
    for p in profil.lister():
        ident = p["id"] if isinstance(p, dict) else p
        fiche = profil.charger(ident) or {}
        for champ, quoi in (("reglement_interieur_id", "reglement"),
                            ("rib_id", "rib"), ("acces_id", "acces")):
            note(fiche.get(champ), quoi, "organisme " + ident)
    # LE LOGO N'EST PAS DE LA PARTIE. Il a sa propre voie locale depuis la
    # migration precedente — profil.logo() lit « logo_fichier » sur le disque et
    # ne descend au Drive qu'a defaut. Le faire passer aussi par le cache des
    # pieces le rangerait deux fois, et l'annoncerait manquant alors qu'il est la.
    return vus


def _en_cache():
    import fichiers
    return fichiers.lire(documents._INDEX_PIECES, {}) or {}


def etat():
    attendues = _pieces_attendues()
    cache = _en_cache()
    presentes = [i for i in attendues if i in cache]
    absentes = [i for i in attendues if i not in cache]
    print("  %d pièce(s) attendue(s) : %d en local, %d encore seulement dans le Drive"
          % (len(attendues), len(presentes), len(absentes)))
    if absentes:
        print()
        for i in absentes:
            a = attendues[i]
            print("    MANQUE  %-36s %-32s %s"
                  % (i, a["libelle"], ", ".join(sorted(set(a["pour"])))[:44]))
    return attendues, cache, absentes


def compte_connecte():
    """L'adresse du compte Google auquel DFM est relie, ou "".

    LA TROISIEME CAUSE D'ECHEC, ET LA PLUS TROMPEUSE. Un jeton peut etre
    parfaitement valide, avoir toutes les autorisations, et ne rien pouvoir
    lire : il suffit qu'il ouvre le Drive d'un AUTRE compte. Google renvoie
    alors 404 — « ce fichier n'existe pas » — la ou il faudrait lire « ce
    fichier n'est pas a vous ». Constate le 19/08/2026 : une reconnexion faite
    sur drfranckmoyal@gmail.com au lieu du compte proprietaire des pieces.
    """
    try:
        from connexion import service_drive
        a = service_drive().about().get(fields="user(emailAddress)").execute()
        return ((a.get("user") or {}).get("emailAddress") or "").strip()
    except Exception:
        return ""


def main():
    print("=" * 62)
    print("  Rapatriement des pièces encore hébergées dans le Drive")
    print("=" * 62)
    qui = compte_connecte()
    if qui:
        print("  Compte Google connecté : %s" % qui)
        print()
    attendues, cache, absentes = etat()
    if "--etat" in sys.argv[1:]:
        return 0
    if not absentes:
        print("\n  Rien à rapatrier : tout est déjà sur le disque.")
        return 0

    print()
    reussies, echouees = [], []
    for i in absentes:
        a = attendues[i]
        octets = documents.piece_par_ident(i, a["quoi"])
        if octets:
            nom = documents.nom_piece(i) or "(sans nom)"
            print("    OK      %-36s %8d o  %s" % (i, len(octets), nom[:34]))
            reussies.append(i)
        else:
            print("    ECHEC   %-36s %s" % (i, a["libelle"]))
            echouees.append(i)

    print()
    print("  %d rapatriée(s), %d en échec." % (len(reussies), len(echouees)))
    if echouees:
        print()
        if qui and len(echouees) == len(absentes):
            # TOUT echoue alors que le Drive repond : ce n'est pas un fichier
            # perdu, c'est le mauvais compte. Le dire franchement, parce que le
            # message de Google — 404 — envoie chercher au mauvais endroit.
            print("  TOUTES les pièces ont échoué, alors que Google répond.")
            print("  Ce n'est donc pas un problème d'autorisation : c'est le COMPTE.")
            print()
            print("    DFM est connecté à : %s" % qui)
            print("    Ce compte ne possède pas ces fichiers — Google répond « introuvable »")
            print("    là où il faudrait lire « pas à vous ».")
            print()
            print("  POUR CHANGER DE COMPTE :")
            print("    1. supprimez le fichier token.json dans le dossier DFM ;")
            print("    2. relancez DFM.command ;")
            print("    3. sur la page Google, choisissez le compte qui possède votre Drive")
            print("       de formation — celui où sont rangés vos programmes et règlements.")
            return 1
        print("  UN ECHEC A TROIS CAUSES POSSIBLES, et elles ne se soignent pas pareil :")
        print("    - l'autorisation Google est expirée : fermez DFM, relancez DFM.command,")
        print("      la page de connexion s'ouvre, puis relancez ce script ;")
        print("    - DFM est connecté au MAUVAIS COMPTE Google : supprimez token.json,")
        print("      relancez DFM.command et choisissez le compte propriétaire des fichiers ;")
        print("    - le fichier n'existe plus dans le Drive : l'identifiant inscrit sur la")
        print("      fiche pointe vers du vide. Reposez la pièce depuis l'écran concerné.")
        return 1
    print("  Toutes les pièces sont désormais lisibles hors ligne.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
