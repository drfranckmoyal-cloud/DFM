# -*- coding: utf-8 -*-
"""Envoie un exemplaire de CHAQUE mail automatique, pour verification.

    venv/bin/python essai_mails.py                     # montre, sans envoyer
    venv/bin/python essai_mails.py --envoyer           # a l'adresse de l'organisme
    venv/bin/python essai_mails.py --envoyer a@b.fr    # a une adresse precise
    venv/bin/python essai_mails.py --envoyer --of dsf  # les mails de DSF

POURQUOI CE SCRIPT EXISTE. Un en-tete de mail ne se juge pas sur une maquette :
il se juge dans une vraie boite, sur un vrai telephone. Celui-ci fabrique les
mails PAR LE MEME CHEMIN QUE LES VRAIS — meme bibliotheque de modeles, meme
enveloppe, meme logo joint — pour que ce qui est verifie soit ce qui partira.

CE QU'IL NE FAIT PAS, ET C'EST VOULU : il n'ecrit ni dans le suivi, ni dans le
journal, ni dans le classeur. Il ne touche a aucune inscription. Les noms sont
fictifs, et l'objet de chaque message commence par « [ESSAI] » : aucun de ces
mails ne peut etre confondu avec un vrai.

LES PIECES JOINTES NE SONT PAS DU VOYAGE. Un vrai mail de convention porte le
programme et la convention ; les joindre ici alourdirait l'essai sans rien
montrer de plus sur la mise en page. Seul le LOGO est joint, parce que lui,
justement, fait partie de l'en-tete.
"""
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import courrier
import mails as _mails
import profil
import sessions as _s

ENVOYER = "--envoyer" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ORGANISME = "dsf" if "--of" in sys.argv and "dsf" in ARGS else "mon-organisme"
VERS = next((a for a in ARGS if "@" in a), "")

# LA PERSONNE DE L'ESSAI EST FICTIVE, et porte un nom qui le dit.
PRATICIENNE = {
    "prenom": "Camille", "nom": "ESSAI", "mail": "camille.essai@exemple.test",
    "ville": "Paris", "telephone": "06 00 00 00 00",
    "fonction": "Chirurgien-dentiste", "montant_du": "", "invite_le": "",
    "demande": "Je confirme ma demande d'inscription",
}
# Pour les modeles reserves aux invites, la meme, invitee.
INVITEE = dict(PRATICIENNE, invite_le="21/10/2026 10:00", montant_du="0")

# L'ordre d'envoi suit la vie d'une inscription, pour qu'on les relise dans
# l'ordre ou un praticien les recoit.
PARCOURS = [
    ("accuse-reception", "Demande bien recue", PRATICIENNE),
    ("signature", "Convention a signer (mail 1)", PRATICIENNE),
    ("confirmation", "Inscription confirmee (mail 2)", PRATICIENNE),
    ("confirmation", "Inscription confirmee — vue d'un INVITE", INVITEE),
    ("rappel", "Rappel J-20", PRATICIENNE),
    ("facture", "Facture acquittee", PRATICIENNE),
    ("attestation", "Attestation de formation", PRATICIENNE),
    ("attente", "Place en file d'attente", PRATICIENNE),
    ("invitation", "Apprenant invite", INVITEE),
    ("invitation-inscription", "Invitation a s'inscrire", PRATICIENNE),
]


def _session_temoin():
    """Une session REELLE de l'organisme, pour des dates et un tarif credibles.

    On la lit, on n'y touche pas. Une session inventee donnerait un mail aux
    dates vides, et c'est justement la mise en page qu'on veut juger.
    """
    candidates = [c for c in sorted(_s.SESSIONS)
                  if _s.organisme_de(c) == ORGANISME
                  and (_s.session(c) or {}).get("mode") != "client"]
    if not candidates:
        return None
    # La plus lointaine : ses dates sont a venir, donc le mail se lit bien.
    candidates.sort(key=lambda c: (_s.session(c) or {}).get("date_debut") or "")
    return _s.session(candidates[-1])


def main():
    S = _session_temoin()
    if not S:
        print("-> Aucune session pour %s : rien a montrer." % ORGANISME)
        return 1
    fiche = profil.charger(ORGANISME) or {}
    vers = VERS or (fiche.get("mail_contact") or "").strip()
    if not vers:
        print("-> Aucune adresse de destination. Donnez-en une en argument.")
        return 1

    logo = None
    try:
        logo = profil.logo(ORGANISME)
    except Exception:
        pass
    couleur, degrade = _mails._couleur_filet(S)

    print("-> Organisme   : %s (%s)" % (fiche.get("marque") or ORGANISME, ORGANISME))
    print("-> Session lue : %s — %s" % (S.get("code"), S.get("date_texte") or "?"))
    print("-> Destination : %s" % vers)
    print("-> Logo        : %s" % ("%d Ko" % (len(logo) // 1024) if logo else "ABSENT"))
    print("-> Filet       : %s%s" % (couleur, "" if degrade == "none" else " + degrade"))
    print("-> %d mail(s) a envoyer :" % len(PARCOURS))

    envoyes = 0
    for usage, libelle, ligne in PARCOURS:
        modele = _mails.pour_formation(S.get("formation", ""), usage)
        if not modele:
            print("   . %-38s AUCUN MODELE" % libelle)
            continue
        rendu = _mails.rendre(modele, _mails.contexte(S, ligne))
        html = _mails.poser_logo(rendu["html"], logo)
        oublies = [m for m in ("{{", "}}") if m in html]
        print("   . %-38s %5d octets%s"
              % (libelle, len(html), "   BALISE OUBLIEE" if oublies else ""))
        if not ENVOYER:
            continue
        message = MIMEMultipart("related")
        message["To"] = vers
        exp = _mails.expediteur(S)
        if exp:
            message["From"] = exp
        message["Subject"] = "[ESSAI] " + rendu["objet"]
        corps = MIMEMultipart("alternative")
        corps.attach(MIMEText(html, "html"))
        message.attach(corps)
        if logo:
            img = MIMEImage(logo)
            img.add_header("Content-ID", "<logo>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            message.attach(img)
        try:
            courrier.envoyer(message, ORGANISME)
            envoyes += 1
        except Exception as e:
            print("     ECHEC : %s" % str(e)[:110])

    print()
    if ENVOYER:
        print("-> Termine : %d mail(s) d'essai envoye(s) a %s." % (envoyes, vers))
        print("   Aucune inscription, aucun journal, aucun classeur n'a ete touche.")
    else:
        print("-> SIMULATION : rien n'est parti. Ajouter --envoyer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
