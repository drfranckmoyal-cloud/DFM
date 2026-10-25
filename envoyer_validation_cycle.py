"""Demander aux demandeurs d'un cycle de confirmer definitivement leur inscription.

    venv/bin/python envoyer_validation_cycle.py <session> --essai
    venv/bin/python envoyer_validation_cycle.py <session> --liste liste.txt

POURQUOI UN SCRIPT A PART, et pas une etape de dfm.py. Ce courriel part AVANT
que les gens soient dans DFM : ce sont des DEMANDEURS, pas des inscrits
(decision D11 du 23/10/2026). Leur liste vient d'ailleurs — un ancien formulaire
Google, un echange de mails — et c'est justement ce courriel qui leur demande de
remplir le formulaire de DFM, lequel creera leur fiche. Le mettre dans la chaine
automatique supposerait des lignes de suivi qui n'existent pas encore.

CE QUI PART AVEC. Les deux pieces de la fiche formation : le programme et la
fiche « materiel et prerequis ». Elles sont relues a chaque envoi depuis le
magasin de documents, jamais recopiees ici.

LE TEXTE N'EST PAS DANS CE FICHIER. Il vit dans DFM, comme modele de mail, donc
modifiable a l'ecran sans toucher au code — et reutilisable pour le cycle
suivant, avec ses propres dates (decision D23). Ce script ne fait que choisir
qui, relire les pieces, et poster.

TROIS MODES, ET LE PREMIER EST LE DEFAUT :

  --essai            un seul envoi, a l'adresse de contact de l'organisme.
                     C'est le mode par defaut : un script d'envoi groupe ne doit
                     pas partir chez vingt praticiens parce qu'on a oublie un
                     argument.
  --liste <fichier>  une adresse par ligne, « prenom;nom;mail » ou « mail » seul.
  --a <mail>         une seule adresse nommee.

ET LA RELANCE, SEPT JOURS PLUS TARD :

  --relance          envoie le courriel 01 BIS au lieu du 01, et ECARTE DE LA
                     LISTE ceux qui ont rempli le questionnaire depuis. C'est
                     le seul moyen de relancer sans relancer quelqu'un qui a
                     deja repondu — et c'est ce qui serait arrive en reprenant
                     la liste de depart telle quelle.

RIEN N'EST ECRIT DANS LE SUIVI. Ces personnes n'y sont pas : il n'y a pas de
ligne a marquer. Le journal, lui, garde la trace de l'envoi.
"""
import argparse
import os
import sys
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import courrier
import documents
import mails as _mails
import profil
import sessions as _sessions

MODELE = "invitation-inscription-esthetique360-validation"
MODELE_RELANCE = "relance-inscription-esth-tique-360-relance-du-questionnaire-d-inscription"


def _destinataires(o, S):
    """(prenom, nom, mail) de chacun. En essai : l'organisme, et lui seul."""
    contact = (S.get("mail_contact") or "").strip()
    if o.liste:
        if not os.path.exists(o.liste):
            raise SystemExit("Liste introuvable : %s" % o.liste)
        sortie = []
        for brut in open(o.liste, encoding="utf-8"):
            brut = brut.strip()
            if not brut or brut.startswith("#"):
                continue
            bouts = [x.strip() for x in brut.split(";")]
            if len(bouts) >= 3:
                sortie.append((bouts[0], bouts[1], bouts[2]))
            else:
                sortie.append(("", "", bouts[-1]))
        return sortie
    if o.a:
        return [("", "", o.a.strip())]
    if not contact:
        raise SystemExit("Aucune adresse de contact sur l'organisme : rien a essayer.")
    return [("Franck", "MOYAL", contact)]


def _deja_inscrits(CODE):
    """Les adresses qui ont DEJA rempli le questionnaire, en minuscules.

    On regarde le suivi de la session : remplir le formulaire y cree une ligne,
    meme en attente de validation. Une personne qui a repondu ne doit pas
    recevoir de relance — c'est le genre de courriel qui fait douter de
    l'organisme qui l'envoie.

    LA LECTURE PEUT ECHOUER, et alors on ne relance personne : mieux vaut un
    envoi reporte qu'une relance a quelqu'un qui a deja fait ce qu'on lui
    demande.
    """
    import suivi as _suivi
    return {(l.get("mail") or "").strip().lower()
            for l in _suivi.lire_lignes_de(CODE)
            if (l.get("mail") or "").strip()}


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("session")
    a.add_argument("--essai", action="store_true",
                   help="un seul envoi, a l'adresse de l'organisme (defaut)")
    a.add_argument("--liste", default="", help="fichier d'adresses")
    a.add_argument("--a", default="", help="une seule adresse")
    a.add_argument("--relance", action="store_true",
                   help="le courriel 01 bis, en ecartant ceux qui ont deja repondu")
    o = a.parse_args()

    CODE = o.session
    S = _sessions.session(CODE)
    _sessions.refuser_si_client(CODE, "une session client n'a pas de demandeurs a relancer.")
    org = _sessions.organisme_de(CODE)

    reference = MODELE_RELANCE if o.relance else MODELE
    modele = _mails.modele(reference)
    if not modele:
        raise SystemExit("Modele introuvable : %s. Posez-le avant d'envoyer." % reference)
    print("-> Courriel : %s" % (modele.get("titre") or reference))

    # LES PIECES, RELUES MAINTENANT. Si l'une manque, on le dit et on s'arrete :
    # un courriel qui annonce « tu trouveras en piece jointe » sans piece jointe
    # fait perdre la confiance qu'on vient de demander.
    pieces = []
    for cle, joli in (("programme", "Programme"), ("prerequis", "Materiel et prerequis")):
        ref = (_sessions.FORMATIONS.get(S.get("formation") or "") or {}).get(
            documents.PIECES.get(cle) or "")
        octets = documents.piece_par_ident(ref, cle) if ref else None
        if not octets:
            raise SystemExit("La piece « %s » manque sur la fiche formation. "
                             "Rien n'a ete envoye." % joli)
        nom = os.path.basename(str(ref)) or (joli + ".pdf")
        pieces.append((nom, octets))
        print("-> Piece jointe : %-46s %7d octets" % (nom, len(octets)))

    logo = profil.logo(org)
    gens = _destinataires(o, S)
    essai = not (o.liste or o.a)
    print("-> Session : %s (%s)" % (S.get("nom_formation"), CODE))

    # UNE RELANCE ECARTE CEUX QUI ONT REPONDU. Sans cela, reprendre la liste de
    # depart relancerait les gens qui viennent de s'inscrire.
    if o.relance and not essai:
        try:
            repondu = _deja_inscrits(CODE)
        except Exception as e:
            raise SystemExit("Suivi illisible (%s) : aucune relance envoyee. "
                             "On ne relance pas a l'aveugle." % str(e)[:70])
        gardes, ecartes = [], []
        for prenom, nom, adresse in gens:
            (ecartes if adresse.strip().lower() in repondu else gardes).append(
                (prenom, nom, adresse))
        for prenom, nom, adresse in ecartes:
            print("   ecarte, a deja repondu : %s" % adresse)
        print("-> %d deja inscrit(s) ecarte(s) de la relance" % len(ecartes))
        gens = gardes
        if not gens:
            print("-> Personne a relancer : tout le monde a repondu.")
            return 0

    print("-> %d destinataire(s)%s" % (len(gens), "  [ESSAI]" if essai else ""))

    envoyes = 0
    for prenom, nom, adresse in gens:
        ligne = {"prenom": prenom, "nom": nom, "mail": adresse}
        rendu = _mails.rendre(modele, _mails.contexte(S, ligne))
        html = _mails.poser_logo(rendu["html"], logo)
        objet = rendu["objet"] + ("  [ESSAI]" if essai else "")

        message = MIMEMultipart("related")
        message["To"] = adresse
        exp = _mails.expediteur(S)
        if exp:
            message["From"] = exp
        message["Subject"] = objet
        corps = MIMEMultipart("alternative")
        corps.attach(MIMEText(html, "html"))
        message.attach(corps)
        if logo:
            img = MIMEImage(logo)
            img.add_header("Content-ID", "<logo>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            message.attach(img)
        for nom_pj, octets in pieces:
            pj = MIMEApplication(octets, _subtype="pdf")
            pj.add_header("Content-Disposition", "attachment", filename=nom_pj)
            message.attach(pj)

        print("-> Envoi a %s..." % adresse)
        courrier.envoyer(message, org)
        envoyes += 1
        # UN ESSAI NE VA PAS AU JOURNAL. La piste d'audit dit ce qui a ete
        # envoye aux apprenants ; un mail que Franck s'envoie a lui-meme pour
        # relire la mise en page n'en fait pas partie, et l'y ecrire noierait
        # les vrais envois.
        if essai:
            continue
        try:
            import journal as _j
            _j.ecrire("Relance du questionnaire envoyée" if o.relance
                      else "Demande de confirmation envoyée",
                      (prenom + " " + nom).strip() or adresse, adresse, "", CODE)
        except Exception as e:
            print("   (journal non ecrit : %s)" % str(e)[:70])

    print("-> Termine : %d envoi(s)%s." % (envoyes, " d'essai" if essai else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
