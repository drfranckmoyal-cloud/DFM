# -*- coding: utf-8 -*-
"""Dit a la personne que sa demande est arrivee. Sans dependre de rien.

    venv/bin/python accuser_reception.py               # envoie
    venv/bin/python accuser_reception.py --simulation  # montre, sans envoyer

IL ENVOIE PAR DEFAUT, comme les autres courriers de DFM : c'est une etape du
traitement automatique, qui tourne toutes les dix minutes. Un indicateur
« --executer » a fournir aurait fait qu'elle ne partait jamais.

POURQUOI CETTE ETAPE EXISTE, ET POURQUOI ELLE EST LA PREMIERE DE TOUTES.

Le 18/10/2026, Talia GUEZ s'est inscrite a 11h56. Une erreur de code cassait
l'import : elle est restee un jour sans fiche, donc sans convention. Franck ne
l'a su qu'en lisant par hasard un bandeau d'alerte. Et elle, de son cote,
n'avait AUCUNE trace de son inscription — elle avait vu un message a l'ecran,
rien dans sa boite. Donc aucune raison de relancer, et aucun moyen de savoir
que quelque chose n'allait pas.

CE COURRIER NE TOUCHE NI LE SUIVI, NI LE CLASSEUR, NI UNE CONVENTION. Il lit
la demande recue et il repond. C'est tout. Il aurait donc fonctionne le 18/10
avec le code casse, et il fonctionnera le jour ou autre chose cassera.

SA DERNIERE PHRASE EST LE VRAI FILET : « si rien ne vous parvient d'ici une
semaine, repondez simplement a ce message ». Elle fait de chaque inscrite une
deuxieme paire d'yeux sur la chaine.

LE REGISTRE EMPECHE LE DOUBLON. Les identifiants deja accuses sont gardes dans
accuses_reception.json. AU PREMIER PASSAGE, les demandes deja presentes y sont
inscrites SANS RIEN ENVOYER : elles sont anciennes, leurs conventions sont
parties depuis longtemps, et leur ecrire aujourd'hui serait absurde.

GARDE-FOU DE DATE : on n'accuse jamais une demande de plus de sept jours, meme
si le registre disparaissait. Mieux vaut un accuse manquant qu'un accuse de
reception envoye six mois trop tard.
"""
import io
import json
import os
import sys
from datetime import datetime, timezone

DOSSIER = os.path.dirname(os.path.abspath(__file__))
REGISTRE = os.path.join(DOSSIER, "accuses_reception.json")
JOURS_MAX = 7
SIMULATION = "--simulation" in sys.argv


def _registre():
    try:
        d = json.load(io.open(REGISTRE, encoding="utf-8"))
    except Exception:
        return None                       # absent : premier passage
    return {str(x) for x in (d.get("accuses") or [])}


def _ecrire_registre(ids):
    try:
        io.open(REGISTRE, "w", encoding="utf-8").write(json.dumps(
            {"accuses": sorted(ids), "maj": datetime.now().strftime("%d/%m/%Y %H:%M:%S")},
            ensure_ascii=False, indent=1))
    except Exception as e:
        print("   ATTENTION : registre non ecrit (%s)." % str(e)[:90])
        print("   Un accuse pourrait repartir au prochain passage.")


def _age_jours(brut):
    s = str(brut or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - d).total_seconds() / 86400.0


def _fiche_de(code):
    """La session, ou un repli lisible si DFM ne la connait pas.

    Une demande peut viser une session renommee ou supprimee. On accuse quand
    meme reception : la personne a rempli le formulaire, elle n'y est pour
    rien. Le controle des inscriptions, lui, signale l'orpheline a Franck.
    """
    try:
        import sessions as _s
        if code in _s.SESSIONS:
            return _s.session(code), True
    except Exception:
        pass
    return {"code": code, "nom_formation": "", "titre_complet": "",
            "date_texte": "", "organisme": ""}, False


def _envoyer(demande, fiche):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import courrier
    import mails as _mails
    import sessions as _s

    organisme = (demande.get("organisme") or fiche.get("organisme")
                 or _s.organisme_de(demande.get("code_session") or "") or "")
    ligne = {"prenom": demande.get("prenom") or "", "nom": demande.get("nom") or "",
             "mail": demande.get("mail") or "", "ville": demande.get("ville") or ""}
    modele = _mails.pour_formation(fiche.get("formation", ""), "accuse-reception")
    rendu = _mails.rendre(modele, _mails.contexte(fiche, ligne))
    logo = None
    try:
        import profil
        logo = profil.logo(organisme)
    except Exception:
        pass
    message = MIMEMultipart("related")
    message["To"] = ligne["mail"]
    exp = _mails.expediteur(fiche)
    if exp:
        message["From"] = exp
    message["Subject"] = rendu["objet"]
    corps = MIMEMultipart("alternative")
    corps.attach(MIMEText(_mails.poser_logo(rendu["html"], logo), "html"))
    message.attach(corps)
    if logo:
        img = MIMEImage(logo)
        img.add_header("Content-ID", "<logo>")
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(img)
    courrier.envoyer(message, organisme)
    return organisme


def main():
    import inscription as I
    try:
        toutes = I._sb("Inscriptions?select=*")
    except Exception as e:
        print("-> Boite aux lettres injoignable : %s" % str(e)[:110])
        print("   Aucun accuse n'est envoye. Le passage suivant reessaiera.")
        return 0

    deja = _registre()
    tous_ids = {str(e.get("id")) for e in toutes if e.get("id") is not None}
    if deja is None:
        # PREMIER PASSAGE : on prend date, sans ecrire a personne.
        #
        # ET IL FAUT LE FAIRE TOT, PAS AU PREMIER INSCRIT. Si le registre
        # naissait au moment ou une nouvelle demande arrive, cette demande
        # ferait partie de la prise de date et n'aurait PAS son accuse — la
        # premiere personne protegee par ce courrier serait justement la seule
        # a ne pas l'avoir.
        if SIMULATION:
            print("-> Premier passage : %d demande(s) seraient inscrite(s) au registre,"
                  % len(tous_ids))
            print("   sans aucun mail. Relancer sans --simulation pour prendre date.")
            return 0
        _ecrire_registre(tous_ids)
        print("-> Premier passage : %d demande(s) deja recue(s) inscrite(s) au registre."
              % len(tous_ids))
        print("   AUCUN mail envoye : ces demandes sont anciennes.")
        print("   Les suivantes seront accusees dans les dix minutes.")
        return 0

    a_faire = []
    for e in toutes:
        ident = str(e.get("id"))
        if ident in deja or not (e.get("mail") or "").strip():
            continue
        age = _age_jours(e.get("horodateur"))
        if age is not None and age > JOURS_MAX:
            # Trop vieille : on l'inscrit au registre sans ecrire, pour ne pas
            # la reexaminer a chaque passage.
            deja.add(ident)
            continue
        a_faire.append(e)

    if not a_faire:
        print("-> Aucun accuse de reception a envoyer.")
        # On enregistre quand meme : des demandes trop vieilles viennent
        # peut-etre d'etre ecartees, et il ne faut pas les reexaminer.
        _ecrire_registre(deja)
        return 0

    print("-> %d accuse(s) de reception a envoyer :" % len(a_faire))
    envoyes = 0
    for e in a_faire:
        qui = ((e.get("prenom") or "") + " " + (e.get("nom") or "")).strip()
        code = e.get("code_session") or ""
        fiche, connue = _fiche_de(code)
        print("   . %-28s <%s> %s%s"
              % (qui[:28], e.get("mail"), code, "" if connue else "  (session inconnue de DFM)"))
        if SIMULATION:
            continue
        try:
            organisme = _envoyer(e, fiche)
            deja.add(str(e.get("id")))
            envoyes += 1
            try:
                import journal
                journal.ecrire("Demande bien reçue", qui,
                               (e.get("mail") or "") + " — accusé de réception",
                               "", code if connue else "")
            except Exception:
                pass
            print("     envoye sous l'identite de %s." % organisme)
        except Exception as ex:
            print("     ECHEC : %s" % str(ex)[:110])
            print("     La demande reste non accusee : le passage suivant reessaiera.")

    if SIMULATION:
        print("-> SIMULATION : rien n'est parti, et le registre n'a pas bouge.")
    else:
        _ecrire_registre(deja)
        print("-> Termine : %d accuse(s) envoye(s)." % envoyes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
