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
import io
import json
import os
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

# L'ALERTE PART PAR MAIL — 19/10/2026, apres que Franck l'a demande en ces
# termes : « si je n'avais pas lu la banderole d'erreur je n'aurais jamais su
# qu'elle etait inscrite ».
#
# Un bandeau a l'ecran suppose qu'on ouvre DFM et qu'on le remarque. Ce n'est
# pas un garde-fou, c'est un espoir. Une inscription sans fiche est le defaut
# le plus grave de DFM — sans les inscrits, DFM ne sert a rien — alors elle
# vient chercher Franck au lieu de l'attendre.
#
# ELLE PART A L'ADRESSE DE CONTACT DE L'ORGANISME, celle declaree dans son
# profil : chaque organisme recoit les siennes. Pour en changer, c'est le champ
# « Adresse de contact » de l'ecran Profil.
#
# PAS DEUX FOIS LA MEME. Le controle passe toutes les dix minutes : alerter a
# chaque passage noierait l'alerte. On n'ecrit que si la liste des personnes
# concernees a CHANGE, ou si six heures ont passe — quelqu'un qui attend
# toujours doit se rappeler a nous, mais une fois par demi-journee.
HEURES_ENTRE_DEUX_ALERTES = 6
MEMOIRE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "etat_alerte_inscriptions.json")


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


def _deja_alerte(signature):
    """Cette meme alerte est-elle partie il y a moins de six heures ?"""
    from datetime import datetime
    try:
        d = json.load(io.open(MEMOIRE, encoding="utf-8"))
    except Exception:
        return False
    if d.get("signature") != signature:
        return False                  # la liste a change : on previent
    try:
        quand = datetime.strptime(d.get("le") or "", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return (datetime.now() - quand).total_seconds() < HEURES_ENTRE_DEUX_ALERTES * 3600


def _noter_alerte(signature):
    from datetime import datetime
    try:
        io.open(MEMOIRE, "w", encoding="utf-8").write(json.dumps(
            {"signature": signature,
             "le": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False))
    except Exception:
        pass


def _oublier_alerte():
    """Plus d'ecart : la prochaine alerte repartira sans attendre six heures."""
    try:
        if os.path.exists(MEMOIRE):
            os.remove(MEMOIRE)
    except Exception:
        pass


def _prevenir(soucis, par_organisme):
    """Ecrit a l'organisme concerne. Ne leve jamais : un mail qui ne part pas
    ne doit pas empecher le controle de s'afficher."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import courrier
    import profil
    partis = []
    for organisme, lignes in sorted(par_organisme.items()):
        try:
            fiche = profil.charger(organisme) or {}
            vers = (fiche.get("mail_contact") or "").strip()
            marque = fiche.get("marque") or organisme
            if not vers:
                print("   (pas d'adresse de contact pour %s : aucune alerte envoyee)"
                      % organisme)
                continue
            n = len(lignes)
            objet = ("DFM — %d inscription%s sans fiche"
                     % (n, "s" if n > 1 else ""))
            corps = (
                '<div style="font:15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;'
                'color:#1a1d26;max-width:36em">'
                "<p><b>%s a recu %d inscription%s qui n'%s pas de fiche dans DFM.</b></p>"
                "<ul>%s</ul>"
                "<p>Ces personnes ont rempli le formulaire et attendent leur convention. "
                "Tant qu'elles n'ont pas de fiche, <b>aucun courrier ne leur partira</b>.</p>"
                "<p>DFM reessaie tout seul toutes les dix minutes. Si ce message revient, "
                "c'est que la reprise echoue&nbsp;: ouvrez DFM, le detail est dans "
                "l'alerte en haut de l'ecran.</p>"
                "<p style=\"color:#6b7280;font-size:12.5px\">Message automatique du controle "
                "des inscriptions. Il ne part qu'en cas d'ecart, et au plus une fois "
                "par demi-journee.</p></div>"
                % (marque, n, "s" if n > 1 else "", "ont" if n > 1 else "a",
                   "".join("<li>%s</li>" % s for s in lignes)))
            message = MIMEMultipart("alternative")
            message["To"] = vers
            message["Subject"] = objet
            try:
                import mails as _mails
                exp = _mails.expediteur({"organisme": organisme})
                if exp:
                    message["From"] = exp
            except Exception:
                pass
            message.attach(MIMEText(corps, "html"))
            courrier.envoyer(message, organisme)
            partis.append(vers)
            print("   Alerte envoyee a %s." % vers)
        except Exception as e:
            print("   (alerte non envoyee a %s : %s)" % (organisme, str(e)[:90]))
    return partis


def main():
    try:
        toutes = I._sb("Inscriptions?select=*")
    except Exception as e:
        print("-> Boite aux lettres injoignable : %s" % str(e)[:120])
        print("   Le controle ne conclut rien. Ce n'est pas un ecart.")
        return 0

    codes = [CODE] if CODE else sorted(_s.SESSIONS)
    soucis = []
    par_organisme = {}      # a qui ecrire : chaque organisme recoit les siens

    def noter(organisme, phrase):
        soucis.append(phrase)
        par_organisme.setdefault(organisme or "mon-organisme", []).append(phrase)

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
            noter(e.get("organisme") or _s.organisme_de(code),
                  "%s <%s> a demandé %s — %s, et ne figure PAS dans le suivi"
                  % (qui, e.get("mail") or "?", code, etat))

        for e in lot:
            if e.get("importee_le"):
                continue
            age = _vieille_de(e.get("horodateur"))
            if age is not None and age > HEURES_AVANT_ALERTE:
                qui = ("%s %s" % (e.get("prenom") or "", e.get("nom") or "")).strip()
                noter(e.get("organisme") or _s.organisme_de(code),
                      "%s <%s> attend depuis %d h sans être reprise"
                      % (qui, e.get("mail") or "?", age))

    # LES ORPHELINES NE SE RATTACHENT A AUCUNE SESSION, donc aucune etape de
    # session ne les verra jamais. Si on ne les regarde pas ici, personne ne les
    # regarde : ce sont de vraies personnes inscrites sur une session renommee
    # ou supprimee depuis.
    orphelines = [e for e in toutes
                  if (e.get("code_session") or "") not in _s.SESSIONS]
    for e in orphelines:
        qui = ("%s %s" % (e.get("prenom") or "", e.get("nom") or "")).strip()
        noter(e.get("organisme"),
              "%s <%s> s'est inscrit sur « %s », session inconnue de DFM"
              % (qui, e.get("mail") or "?", e.get("code_session") or "(vide)"))

    total = len([e for e in toutes
                 if not CODE or (e.get("code_session") or "") == CODE])
    if not soucis:
        print("-> %d demande(s) controlee(s) : toutes sont dans le suivi." % total)
        _oublier_alerte()
        return 0

    print("-> %d ECART(S) entre les demandes recues et le suivi :" % len(soucis))
    for s in soucis:
        print("   . " + s)
    print("   Une demande recue et absente du suivi, c'est quelqu'un qui attend")
    print("   une convention qui ne partira jamais.")

    # L'ALERTE VIENT CHERCHER FRANCK. Le bandeau a l'ecran suppose qu'il ouvre
    # DFM ; le mail, non. Sans argument « --sans-mail », qui ne sert qu'aux
    # essais.
    signature = "|".join(sorted(soucis))
    if "--sans-mail" in sys.argv:
        print("   (alerte par mail volontairement sautee)")
    elif _deja_alerte(signature):
        print("   (meme alerte deja envoyee il y a moins de %d h : pas de second mail)"
              % HEURES_ENTRE_DEUX_ALERTES)
    else:
        if _prevenir(soucis, par_organisme):
            _noter_alerte(signature)
    return 1


if __name__ == "__main__":
    sys.exit(main())
