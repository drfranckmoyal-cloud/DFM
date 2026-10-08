import json
import os
from datetime import datetime as _datetime
import re
import struct
_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mails.json")
USAGES = {
    "signature": {"nom": "Convention à signer",
                  "quand": "Part dès l'import d'une inscription confirmée",
                  "icone": "ti-writing-sign", "couleur": "#4f7ef8"},
    "confirmation": {"nom": "Inscription confirmée",
                     "quand": "Part dès que la convention est signée",
                     "icone": "ti-circle-check", "couleur": "#0f9e6a"},
    "attente": {"nom": "Place en file d'attente",
                "quand": "Part quand une inscription arrive sur une session complète ou clôturée",
                "icone": "ti-hourglass", "couleur": "#d4890a"},
    "rappel": {"nom": "Rappel J-20",
               "quand": "Part 20 jours avant la formation, avec les informations pratiques",
               "icone": "ti-bell-ringing", "couleur": "#7c5bf7"},
    "facture": {"nom": "Facture acquittée",
                "quand": "Part dès que le règlement est enregistré",
                "icone": "ti-file-euro", "couleur": "#0f9e6a"},
    "attestation": {"nom": "Attestation de formation",
                    "quand": "Part à la clôture, après validation manuelle",
                    "icone": "ti-certificate", "couleur": "#4f7ef8"},
    "invitation": {"nom": "Apprenant invité",
                   "quand": "Part uniquement quand vous marquez quelqu'un comme invité — jamais par le pipeline",
                   "icone": "ti-gift", "couleur": "#d4890a"},
}
BALISES = [
    ("Praticien", [
        ("prenom", "Prénom seul", "Camille"),
        ("nom", "Nom de famille", "DURAND"),
        ("nom_prenom", "Prénom et nom", "Camille DURAND"),
        ("mail", "Adresse du praticien", "camille.durand@exemple.fr"),
        ("ville", "Ville d'exercice", "Bordeaux"),
    ]),
    ("Formation", [
        ("formation", "Intitulé court", "Ma formation"),
        ("titre_formation", "Titre complet", "Intitulé complet de la formation"),
        ("dates", "Dates en toutes lettres", "jeudi 12 et vendredi 13 mars 2027"),
        ("date_debut", "Date de début, seule", "12/03/2027"),
        ("date_fin", "Date de fin, seule", "13/03/2027"),
        ("jours_formation", "Chaque journée avec sa durée",
         "jeudi 12 mars 2027 (7 heures)<br>vendredi 13 mars 2027 (7 heures)"),
        ("nb_jours", "Nombre de journées", "2"),
        ("horaires", "Horaires", "9h00 – 17h30"),
        ("lieu", "Adresse du lieu", "12 avenue des Exemples, 75000 Ville"),
        ("duree", "Durée", "14 heures"),
        ("tarif", "Tarif en euros", "000"),
        ("formateur", "Nom du formateur", "NOM Prénom"),
    ]),
    ("Liens", [
        ("lien_signature", "Bouton de signature", "https://exemple.test/signature"),
        ("lien_paiement", "Lien de paiement Stripe", "https://exemple.test/paiement"),
        ("lien_annulation", "Lien d'annulation", "https://exemple.test/annulation"),
    ]),
    ("Organisme", [
        ("organisme", "Raison sociale", "VOTRE SOCIÉTÉ"),
        ("marque", "Nom commercial", "Votre marque"),
        ("signature", "Signature du mail", "Prénom Nom"),
        ("mail_contact", "Adresse de contact", "contact@exemple.test"),
        ("telephone", "Téléphone", "00 00 00 00 00"),
        ("iban", "IBAN", "FR76 0000 0000 0000 0000 0000 000"),
        ("bic", "BIC", "XXXXFRPPXXX"),
    ]),
    ("Qualiopi", [
        ("accessibilite", "Mention d'accessibilité et référent handicap",
         "Accessibilité : si vous avez besoin d'une adaptation…"),
        ("reclamations", "Voie de réclamation et délai de réponse",
         "Une remarque, un désaccord ? Écrivez à…"),
        ("referent_handicap", "Nom du référent handicap seul", "NOM Prénom"),
        ("lien_reclamation", "Lien vers la page de réclamation",
         "https://exemple.test/reclamation.html"),
        ("delai_reclamation", "Délai de réponse annoncé, en jours", "15"),
    ]),
    ("Particulier", [
        ("delai_reglement", "Délai de règlement en jours", "20"),
        ("intro", "Phrase d'accroche, varie selon le cas", "<p>Merci pour votre inscription.</p>"),
    ]),
]
ENVELOPPE = ('<div style="font-family: \'Helvetica Neue\', Arial, sans-serif; max-width: 560px;'
             ' margin: 0 auto; color: #2b2f3a; line-height: 1.6;">\n'
             '  <div style="padding: 20px 0 4px;">\n'
             '    <img src="cid:logo" alt="{{marque}}" style="height: 60px;">\n'
             '  </div>\n'
             '  <div style="height:1px; background:#e6e9f2; margin: 8px 0 24px;"></div>\n'
             '{CORPS}\n'
             '</div>')
# --------------------------------------------------------------------------
# Le logo, dans un mail
# --------------------------------------------------------------------------
# Une messagerie n'est pas un navigateur. Trois regles apprises sur ce seul
# <img>, qui expliquent qu'un meme mail paraisse correct ici, minuscule la, et
# completement etire ailleurs :
#
#   1. Outlook (moteur de rendu Word) IGNORE les dimensions ecrites en CSS et
#      affiche l'image a sa taille reelle. Sans attribut width= / height= HTML,
#      un fichier de 500 px s'affiche en 500 px, quoi qu'en dise le style.
#   2. Gmail sur Android, et plusieurs webmails, imposent leur propre largeur
#      aux images. Une HAUTEUR fixee SANS LARGEUR laisse la largeur etre
#      recalculee sur le conteneur : le rapport est perdu, l'image s'etire.
#   3. Une hauteur ne dit rien du CONTENU. Le fichier de l'organisme est carre
#      alors que la marque y est large : a 60 px de haut, la marque elle-meme
#      ne mesure que 27 px. Correct, et illisible.
#
# D'ou la regle unique appliquee partout : les dimensions sont LUES DANS LE
# FICHIER, jamais devinees, et ecrites deux fois — en attributs HTML pour
# Outlook, en CSS pour les autres — largeur et hauteur toujours ensemble.
# Un fichier remplace par un autre rapport se redimensionne donc tout seul.
_MOTIF_LOGO = re.compile(r"<img[^>]*?cid:logo[^>]*?>", re.I)
_MOTIF_ALT = re.compile(r'alt\s*=\s*"([^"]*)"', re.I)
HAUTEUR_LOGO = 60          # hauteur visee, en pixels
LARGEUR_MAX_LOGO = 260     # au-dela, c'est la largeur qui commande


def dimensions_image(octets):
    """(largeur, hauteur) lues dans l'en-tete du fichier. None si illisible.

    On lit l'en-tete plutot que d'installer une bibliotheque d'images : trois
    formats couvrent tout ce qu'un logo peut etre, et une dependance de plus
    serait une panne de plus le jour d'une reinstallation."""
    try:
        o = octets or b""
        if o[:8] == b"\x89PNG\r\n\x1a\n" and o[12:16] == b"IHDR":
            return struct.unpack(">II", o[16:24])
        if o[:3] == b"GIF":
            return struct.unpack("<HH", o[6:10])
        if o[:2] == b"\xff\xd8":                      # JPEG : chercher le SOFn
            i = 2
            while i < len(o) - 9:
                if o[i] != 0xFF:
                    i += 1
                    continue
                marqueur = o[i + 1]
                if marqueur in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, l = struct.unpack(">HH", o[i + 5:i + 9])
                    return (l, h)
                if marqueur in (0xD8, 0xD9) or 0xD0 <= marqueur <= 0xD7:
                    i += 2
                    continue
                i += 2 + struct.unpack(">H", o[i + 2:i + 4])[0]
    except Exception:
        pass
    return None


def taille_logo(octets, hauteur=HAUTEUR_LOGO, largeur_max=LARGEUR_MAX_LOGO):
    """Dimensions d'affichage, rapport respecte, tenant dans la boite."""
    d = dimensions_image(octets)
    if not d or not d[0] or not d[1]:
        return None
    largeur = int(round(hauteur * d[0] / float(d[1])))
    if largeur > largeur_max:                 # logo tres large : la largeur prime
        hauteur = int(round(largeur_max * d[1] / float(d[0])))
        largeur = largeur_max
    return (max(largeur, 1), max(hauteur, 1))


def html_logo(octets, alt="", source="cid:logo"):
    """La balise <img> du logo, dimensionnee, ou "" si le fichier est illisible."""
    t = taille_logo(octets)
    if not t:
        return ""
    l, h = t
    return ('<img src="%s" alt="%s" width="%d" height="%d" '
            'style="width:%dpx; height:%dpx; max-width:%dpx; display:block; '
            'border:0; outline:none; text-decoration:none; '
            '-ms-interpolation-mode:bicubic;">' % (source, alt, l, h, l, h, l))


def poser_logo(html, octets, source="cid:logo"):
    """Remplace la balise logo du HTML par sa version dimensionnee.

    Appelee au moment de l'assemblage du message, la ou les octets du fichier
    sont deja disponibles. Si le fichier est illisible ou absent, le HTML
    ressort INCHANGE : un logo mal dimensionne vaut mieux qu'un mail casse."""
    if not octets or not html:
        return html
    remplacante = html_logo(octets, source=source)
    if not remplacante:
        return html

    def _un(m):
        origine = m.group(0)
        alt = _MOTIF_ALT.search(origine)
        return remplacante.replace('alt=""', 'alt="%s"' % (alt.group(1) if alt else ""))

    return _MOTIF_LOGO.sub(_un, html)


DEFAUTS = {
 "signature": {
  "titre": "Convention à signer — texte d'origine",
  "objet": "Convention à signer · {{titre_formation}}",
  "objet_promu": "Une place s'est libérée · {{titre_formation}}",
  "corps": """  <p>Bonjour <strong>{{prenom}}</strong>,</p>
  {{intro}}
  <p>Pour <strong>valider ton inscription</strong>, il te suffit de signer ta convention de formation en ligne, en un clic :</p>
  <div style="text-align:center; margin: 28px 0;">
    <a href="{{lien_signature}}" style="display:inline-block; background:#0f9e6a; color:#fff; padding:14px 32px; text-decoration:none; border-radius:8px; font-weight:600; font-size:15px;">Signer ma convention</a>
  </div>
  <p>Tu trouveras &eacute;galement ci-joint le <strong>programme de formation</strong>.</p>
  <p>Une fois ta convention sign&eacute;e, tu recevras un second mail avec les modalit&eacute;s de r&egrave;glement.</p>
  <p>En cas de question, n'h&eacute;site pas &agrave; r&eacute;pondre &agrave; ce mail.</p>
  <p style="margin-top: 24px;">Bonne journ&eacute;e,<br>
  <strong>{{signature}}, {{marque}}</strong></p>
  <p style="text-align:center; margin:26px 0 0; font-size:12px;">
    <a href="{{lien_annulation}}" style="color:#8a90a2; text-decoration:underline;">Je souhaite annuler mon inscription</a>
  </p>""",
 },
 "confirmation": {
  "titre": "Inscription confirmée — texte d'origine",
  "objet": "Inscription confirmee · {{titre_formation}}",
  "corps": """  <p><strong>Bonjour {{prenom}},</strong></p>
  <p>Ta convention est sign&eacute;e et ton inscription &agrave; la formation
  <strong>&laquo; {{titre_formation}} &raquo;</strong>,
  qui aura lieu le <strong>{{dates}}</strong>, est confirm&eacute;e &mdash; merci !</p>
  <p>Tu trouveras ci-joint ta <strong>convention sign&eacute;e</strong> des deux parties.</p>
  <p>Il ne te reste plus qu'&agrave; r&eacute;gler ta formation
  (<strong>{{tarif}} &euro;</strong>, d&eacute;jeuners inclus), jusqu'&agrave; <strong>20 jours avant</strong> la formation.</p>
  <p><em>Deux options :</em></p>
  <div style="text-align:center; margin: 24px 0;">
    <a href="{{lien_paiement}}" style="display:inline-block; background:#635BFF; color:#fff; padding:14px 32px; text-decoration:none; border-radius:8px; font-weight:600; font-size:15px;">R&eacute;gler ma formation</a>
    <div style="font-size:12px; color:#8a90a2; margin-top:6px;">(paiement par carte bancaire)</div>
  </div>
  <p style="margin-bottom:8px;"><strong>Ou par virement :</strong><br>
  <span style="font-size:13px; color:#5b6172;">Motif : {{formation}} + Nom Pr&eacute;nom</span></p>
  <table style="width:100%; border-collapse:collapse; font-size:13px; margin: 8px 0 20px;">
    <tr><td style="padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb; font-weight:600; width:120px;">Titulaire</td>
        <td style="padding:8px 10px; border:1px solid #e0e8fb;">{{organisme}}</td></tr>
    <tr><td style="padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb; font-weight:600;">IBAN</td>
        <td style="padding:8px 10px; border:1px solid #e0e8fb;">{{iban}}</td></tr>
    <tr><td style="padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb; font-weight:600;">BIC</td>
        <td style="padding:8px 10px; border:1px solid #e0e8fb;">{{bic}}</td></tr>
  </table>
  <p>Tu trouveras &eacute;galement en pi&egrave;ce jointe les <strong>informations d'acc&egrave;s</strong> au site de formation.</p>
  <p>Un mail de rappel te sera envoy&eacute; <strong>20 jours avant</strong> la formation avec un rappel sur les modalit&eacute;s d'acc&egrave;s.</p>
  <p>En cas de question, r&eacute;ponds simplement &agrave; ce mail.</p>
  <p style="margin-top: 24px;">Bonne journ&eacute;e,<br>
  <strong>{{signature}}, {{marque}}</strong></p>
  <p style="text-align:center; margin:26px 0 0; font-size:12px;">
    <a href="{{lien_annulation}}" style="color:#8a90a2; text-decoration:underline;">Je souhaite annuler mon inscription</a>
  </p>""",
 },
 "attente": {"titre": "Place en file d'attente — texte d'origine", "objet": "Votre demande d'inscription · {{titre_formation}}"},
 "rappel": {"titre": "Rappel J-20 — texte d'origine", "objet": "Votre formation approche · {{titre_formation}}"},
 "facture": {"titre": "Facture acquittée — texte d'origine", "objet": "Votre facture · {{titre_formation}}"},
 "attestation": {"titre": "Attestation de formation — texte d'origine", "objet": "Votre attestation · {{titre_formation}}"},
 "invitation": {"titre": "Apprenant invité — texte d'origine",
                "objet": "Vous êtes invité·e · {{titre_formation}}"},
}
TYPES_BLOCS = {
    "texte": {"nom": "Paragraphe", "icone": "ti-align-left",
              "aide": "Un ou plusieurs paragraphes. Laissez une ligne vide entre deux paragraphes."},
    "encadre": {"nom": "Encadré", "icone": "ti-square-rounded",
                "aide": "Un bloc sur fond coloré, pour une information qu'on ne doit pas manquer."},
    "bouton": {"nom": "Bouton", "icone": "ti-hand-click",
               "aide": "Un gros bouton cliquable et centré, pour l'action principale du mail."},
    "tableau": {"nom": "Tableau", "icone": "ti-table",
                "aide": "Deux colonnes, pour des coordonnées bancaires ou des détails pratiques."},
    "signature": {"nom": "Signature", "icone": "ti-signature",
                  "aide": "La formule de politesse et votre nom, en fin de mail."},
    "lien": {"nom": "Lien discret", "icone": "ti-link",
             "aide": "Un petit lien gris et centré, pour l'annulation par exemple."},
    "espace": {"nom": "Espace", "icone": "ti-arrows-vertical",
               "aide": "Une respiration entre deux blocs."},
    "brut": {"nom": "Texte automatique", "icone": "ti-wand",
             "aide": "Un contenu que DFM compose seul selon la situation. Ne se modifie pas."},
    # IMAGE — ajoutee pour les communications, ou le visuel compte autant que
    # le texte. Utilisable aussi dans les mails du parcours : rien ne s'y oppose.
    "image": {"nom": "Image", "icone": "ti-photo",
              "aide": "Une image pleine largeur ou centree. Elle doit etre hebergee "
                      "sur le Drive — DFM s'en charge a l'import."},
    "colonnes": {"nom": "Deux colonnes", "icone": "ti-columns-2",
                 "aide": "Une image d'un cote, du texte de l'autre. Les deux passent "
                         "l'une sous l'autre sur telephone."},
}
TONS = {"bleu": ("#f0f4ff", "#c5d4fb", "#185fa5"),
        "vert": ("#eafaf3", "#9fe1cb", "#0f6e56"),
        "orange": ("#fdf6ec", "#f5dda6", "#8a5a06"),
        "gris": ("#f7f8fb", "#e6e9f2", "#5b6172")}
COULEURS = {"vert": "#0f9e6a", "bleu": "#4f7ef8", "violet": "#635BFF",
            "orange": "#d4890a", "noir": "#2b2f3a"}
TAILLES = {"petit": "13px", "normal": "", "grand": "17px"}
def _echapper(t):
    """Pour un ATTRIBUT HTML — alt, title. Le guillemet double doit partir,
    sinon un texte contenant « " » referme l'attribut et casse la balise."""
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _riche(t):
    t = (t or "")
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"__(.+?)__", r"<u>\1</u>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", t)
    # LIENS DANS LE TEXTE : [libelle](adresse). Absents jusqu'au 05/08/2026 —
    # un message de communication renvoie presque toujours quelque part, et
    # obliger a passer par un bloc bouton pour un simple lien dans une phrase
    # rendait les textes bavards.
    #
    # L'adresse est bornee a http, https et mailto : « javascript: » dans un
    # href serait sans effet dans un mail, mais l'apercu s'affiche, lui, dans
    # un navigateur.
    def _lien(m):
        cible = m.group(2).strip()
        if not re.match(r"^(https?://|mailto:)", cible, re.I):
            return m.group(1)
        return ('<a href="' + cible.replace('"', "%22")
                + '" style="color:#4f7ef8; text-decoration:underline;">' + m.group(1) + "</a>")
    t = re.sub(r"\[([^\[\]]+)\]\((https?://[^\s()]+|mailto:[^\s()]+)\)", _lien, t)
    for _ in range(4):
        neuf = re.sub(r"\[\[(#[0-9a-fA-F]{3,6})\|([^\[\]]*)\]\]",
                      r'<span style="color:\1">\2</span>', t)
        if neuf == t:
            break
        t = neuf
    return t
def _style_bloc(b):
    bouts = []
    taille = TAILLES.get(b.get("taille") or "normal", "")
    if taille:
        bouts.append("font-size:" + taille)
    if b.get("align") and b.get("align") != "gauche":
        bouts.append("text-align:" + ("center" if b["align"] == "centre" else "right"))
    if b.get("couleur_texte"):
        bouts.append("color:" + b["couleur_texte"])
    espace = b.get("espace")
    if espace == "serre":
        bouts.append("margin:6px 0")
    elif espace == "large":
        bouts.append("margin:22px 0")
    return "; ".join(bouts)
def _paragraphes(t, style=""):
    out = []
    brut = (t or "").replace("\r\n", "\n")
    morceaux = re.split(r"\n\s*\n", brut)
    for m in morceaux:
        m = m.strip("\n")
        if not m.strip():
            out.append('  <div style="height:14px"></div>')
            continue
        out.append("  <p" + (' style="' + style + '"' if style else "") + ">"
                   + _riche(m).replace("\n", "<br>") + "</p>")
    return "\n".join(out)
def html_bloc(b):
    t = b.get("type")
    if t == "texte":
        return _paragraphes(b.get("contenu"), _style_bloc(b))
    if t == "encadre":
        fond, bord, couleur = TONS.get(b.get("ton") or "orange", TONS["orange"])
        return ('  <div style="background:' + fond + '; border:1px solid ' + bord
                + '; border-radius:10px; padding:16px; margin:22px 0; color:' + couleur + ';">\n'
                + _paragraphes(b.get("contenu"), "margin:0; font-size:14px;") + "\n  </div>")
    if t == "bouton":
        couleur = COULEURS.get(b.get("couleur") or "vert", COULEURS["vert"])
        h = ('  <div style="text-align:center; margin: 28px 0;">\n'
             '    <a href="' + (b.get("lien") or "#") + '" style="display:inline-block; background:'
             + couleur + '; color:#fff; padding:14px 32px; text-decoration:none; border-radius:8px;'
             ' font-weight:600; font-size:15px;">' + _riche(b.get("libelle") or "Cliquer ici") + "</a>")
        if (b.get("sous") or "").strip():
            h += ('\n    <div style="font-size:12px; color:#8a90a2; margin-top:6px;">'
                  + _riche(b.get("sous")) + "</div>")
        return h + "\n  </div>"
    if t == "tableau":
        h = ""
        if (b.get("titre") or "").strip():
            h += "  <p style=\"margin-bottom:8px;\">" + _riche(b.get("titre")).replace("\n", "<br>") + "</p>\n"
        h += '  <table style="width:100%; border-collapse:collapse; font-size:13px; margin: 8px 0 20px;">\n'
        for ligne in (b.get("lignes") or []):
            h += ('    <tr><td style="padding:8px 10px; background:#f5f8ff; border:1px solid #e0e8fb;'
                  ' font-weight:600; width:120px;">' + _riche(ligne.get("cle") or "") + "</td>\n"
                  '        <td style="padding:8px 10px; border:1px solid #e0e8fb;">'
                  + _riche(ligne.get("valeur") or "") + "</td></tr>\n")
        return h + "  </table>"
    if t == "signature":
        return ('  <p style="margin-top: 24px;">'
                + _riche(b.get("contenu") or "").replace("\n", "<br>\n  ") + "</p>")
    if t == "lien":
        return ('  <p style="text-align:center; margin:26px 0 0; font-size:12px;">\n'
                '    <a href="' + (b.get("lien") or "#")
                + '" style="color:#8a90a2; text-decoration:underline;">'
                + _riche(b.get("libelle") or "Lien") + "</a>\n  </p>")
    if t == "espace":
        h = {"petit": "10px", "normal": "22px", "grand": "40px"}.get(b.get("hauteur") or "normal", "22px")
        return '  <div style="height:' + h + '"></div>'
    if t == "image":
        # LARGEUR ET HAUTEUR EN ATTRIBUTS, pas seulement en CSS : Outlook ignore
        # les dimensions declarees en style et affiche l'image a sa taille
        # native, ce qui fait exploser la mise en page. Meme lecon que le logo.
        src = (b.get("src") or "").strip()
        if not src:
            return ""
        largeur = str(b.get("largeur") or "560").strip() or "560"
        alt = _echapper(b.get("alt") or "")
        img = ('<img src="' + src + '" alt="' + alt + '" width="' + largeur
               + '" style="width:100%; max-width:' + largeur + 'px; height:auto; display:block;'
               ' border:0; outline:none; text-decoration:none; -ms-interpolation-mode:bicubic;'
               ' border-radius:8px;">')
        if (b.get("lien") or "").strip():
            img = '<a href="' + b["lien"].strip() + '">' + img + "</a>"
        h = '  <div style="text-align:center; margin:22px 0;">\n    ' + img
        if (b.get("legende") or "").strip():
            h += ('\n    <div style="font-size:12px; color:#8a90a2; margin-top:7px;">'
                  + _riche(b.get("legende")) + "</div>")
        return h + "\n  </div>"
    if t == "colonnes":
        # UN TABLEAU, pas du flex : Outlook ne connait ni flexbox ni grid. Les
        # cellules passent l'une sous l'autre sur telephone grace a la largeur
        # en pourcentage et au « max-width » de l'image.
        src = (b.get("src") or "").strip()
        texte = _paragraphes(b.get("contenu"), "margin:0; font-size:14px;")
        cellule_img = ""
        if src:
            cellule_img = ('<td width="45%" style="padding:0 14px 0 0; vertical-align:top;">'
                           '<img src="' + src + '" alt="' + _echapper(b.get("alt") or "")
                           + '" width="240" style="width:100%; max-width:240px; height:auto;'
                           ' display:block; border:0; border-radius:8px;"></td>')
        return ('  <table style="width:100%; border-collapse:collapse; margin:22px 0;">\n'
                '    <tr>' + cellule_img
                + '<td style="vertical-align:top;">' + texte + "</td></tr>\n  </table>")
    if t == "brut":
        return "  " + (b.get("contenu") or "")
    return ""
def html_depuis_blocs(blocs):
    return "\n".join([h for h in [html_bloc(b) for b in (blocs or [])] if h])
BLOCS_DEFAUTS = {
 "signature": [
  {"type": "texte", "contenu": "Bonjour **{{prenom}}**,"},
  {"type": "brut", "contenu": "{{intro}}"},
  {"type": "texte", "contenu": "Pour **valider ton inscription**, il te suffit de signer ta convention de formation en ligne, en un clic :"},
  {"type": "bouton", "libelle": "Signer ma convention", "lien": "{{lien_signature}}", "couleur": "vert", "sous": ""},
  {"type": "texte", "contenu": "Tu trouveras également ci-joint le **programme de formation**."},
  {"type": "texte", "contenu": "Une fois ta convention signée, tu recevras un second mail avec les modalités de règlement."},
  {"type": "texte", "contenu": "En cas de question, n'hésite pas à répondre à ce mail."},
  {"type": "signature", "contenu": "Bonne journée,\n**{{signature}}, {{marque}}**"},
  {"type": "lien", "libelle": "Je souhaite annuler mon inscription", "lien": "{{lien_annulation}}"},
 ],
 "confirmation": [
  {"type": "texte", "contenu": "**Bonjour {{prenom}},**"},
  {"type": "texte", "contenu": "Ta convention est signée et ton inscription à la formation **« {{titre_formation}} »**, qui aura lieu le **{{dates}}**, est confirmée — merci !"},
  {"type": "texte", "contenu": "Tu trouveras ci-joint ta **convention signée** des deux parties."},
  {"type": "texte", "contenu": "Il ne te reste plus qu'à régler ta formation (**{{tarif}} €**, déjeuners inclus), jusqu'à **20 jours avant** la formation."},
  {"type": "texte", "contenu": "*Deux options :*"},
  {"type": "bouton", "libelle": "Régler ma formation", "lien": "{{lien_paiement}}", "couleur": "violet", "sous": "(paiement par carte bancaire)"},
  {"type": "texte", "contenu": "**Ou par virement :**\nMotif : {{formation}} + Nom Prénom"},
  {"type": "tableau", "titre": "", "lignes": [
     {"cle": "Titulaire", "valeur": "{{organisme}}"},
     {"cle": "IBAN", "valeur": "{{iban}}"},
     {"cle": "BIC", "valeur": "{{bic}}"}]},
  {"type": "texte", "contenu": "Tu trouveras également en pièce jointe les **informations d'accès** au site de formation."},
  {"type": "texte", "contenu": "Un mail de rappel te sera envoyé **20 jours avant** la formation avec un rappel sur les modalités d'accès."},
  {"type": "texte", "contenu": "En cas de question, réponds simplement à ce mail."},
  {"type": "signature", "contenu": "Bonne journée,\n**{{signature}}, {{marque}}**"},
  {"type": "lien", "libelle": "Je souhaite annuler mon inscription", "lien": "{{lien_annulation}}"},
 ],
 "attente": [
  {"type": "brut", "contenu": "<p><strong>Bonjour {{prenom}},</strong></p>"},
  {"type": "brut", "contenu": "<p>Merci pour ta demande d'inscription &agrave; la formation"},
  {"type": "brut", "contenu": "<strong>&laquo; {{titre_formation}} &raquo;</strong> ({{dates}}).</p>\n  {{encadre}}\n  {{suite}}"},
  {"type": "brut", "contenu": "<p>Nous organisons r&eacute;guli&egrave;rement de nouvelles sessions. Si tu pr&eacute;f&egrave;res &ecirc;tre positionn&eacute; sur une date ult&eacute;rieure,\n  dis-le-nous simplement en r&eacute;pondant &agrave; ce mail.</p>"},
  {"type": "brut", "contenu": "<p>N'h&eacute;site pas &agrave; nous &eacute;crire &agrave; <a href=\"mailto:{{mail_contact}}\">{{mail_contact}}</a> pour toute question.</p>"},
  {"type": "brut", "contenu": "<p style=\"margin-top: 24px;\">Bien &agrave; toi,<br>"},
  {"type": "brut", "contenu": "<strong>{{signature}}, {{marque}}</strong></p>"},
 ],
 "rappel": [
  {"type": "brut", "contenu": "<p><strong>Bonjour {{prenom}},</strong></p>"},
  {"type": "brut", "contenu": "<p>Ta formation <strong>&laquo; {{titre_formation}} &raquo;</strong> arrive &agrave; grands pas !</p>"},
  {"type": "brut", "contenu": "<p>Voici les informations pour pr&eacute;parer au mieux ton arriv&eacute;e :</p>"},
  {"type": "brut", "contenu": "<ul style=\"padding-left:20px;margin:14px 0;\">\n    <li style=\"margin-bottom:8px;\"><strong>Adresse</strong> : {{lieu}}</li>\n    <li style=\"margin-bottom:8px;\"><strong>Accueil</strong> &agrave; partir de 8h30, avec petit d&eacute;jeuner</li>\n    <li style=\"margin-bottom:8px;\"><strong>D&eacute;but de la formation</strong> &agrave; 9h00</li>\n    <li style=\"margin-bottom:8px;\">Le <strong>d&eacute;jeuner est inclus</strong> (restaurant &agrave; quelques m&egrave;tres du centre)</li>\n    <li style=\"margin-bottom:8px;\">Si tu pr&eacute;f&egrave;res apporter ton repas, tu pourras le r&eacute;chauffer sur place</li>\n    <li style=\"margin-bottom:8px;\"><strong>Fin de la formation</strong> aux alentours de 17h00</li>\n    <li>Tu trouveras <strong>en pi&egrave;ces jointes</strong> les informations pratiques pour te rendre sur le lieu de formation, ainsi que quelques articles int&eacute;ressants &agrave; lire avant de venir</li>"},
  {"type": "brut", "contenu": "</ul>{{bloc_reglement}}"},
  {"type": "brut", "contenu": "<p>En cas de question, r&eacute;ponds simplement &agrave; ce mail.</p>"},
  {"type": "brut", "contenu": "<p style=\"margin-top: 24px;\">Bonne semaine et &agrave; tr&egrave;s bient&ocirc;t,<br>"},
  {"type": "brut", "contenu": "<strong>{{signature}}, {{marque}}</strong></p>"},
 ],
 "facture": [
  {"type": "brut", "contenu": "<p><strong>Bonjour {{prenom}},</strong></p>"},
  {"type": "brut", "contenu": "<p>Nous avons bien re&ccedil;u ton r&egrave;glement pour la formation"},
  {"type": "brut", "contenu": "<strong>&laquo; {{titre_formation}} &raquo;</strong> &mdash; merci !</p>"},
  {"type": "brut", "contenu": "<p>Tu trouveras ci-joint ta <strong>facture acquitt&eacute;e</strong>.</p>"},
  {"type": "brut", "contenu": "<p>Nous te donnons rendez-vous le <strong>{{dates}}</strong>. Un mail de rappel avec les modalit&eacute;s d'acc&egrave;s te parviendra 20 jours avant la formation.</p>"},
  {"type": "brut", "contenu": "<p>En cas de question, r&eacute;ponds simplement &agrave; ce mail.</p>"},
  {"type": "brut", "contenu": "<p style=\"margin-top: 24px;\">Bonne journ&eacute;e,<br>"},
  {"type": "brut", "contenu": "<strong>{{signature}}, {{marque}}</strong></p>"},
 ],
 "attestation": [
  {"type": "brut", "contenu": "<p><strong>Bonjour {{prenom}},</strong></p>"},
  {"type": "brut", "contenu": "<p>Merci d'avoir particip&eacute; &agrave; la formation"},
  {"type": "brut", "contenu": "<strong>&laquo; {{titre_formation}} &raquo;</strong>. Ce fut un plaisir de te compter parmi nous.</p>"},
  {"type": "brut", "contenu": "<p>Tu trouveras ci-joint ton <strong>attestation de formation</strong>, &agrave; conserver pour ton dossier\n  de formation continue.</p>"},
  {"type": "brut", "contenu": "<p>Si tu as des questions sur les cas abord&eacute;s pendant ces deux jours, ou si tu souhaites un avis\n  sur une situation clinique, n'h&eacute;site pas &agrave; m'&eacute;crire &mdash; je reste disponible.</p>"},
  {"type": "brut", "contenu": "<p>De nouvelles sessions et d'autres formations sont r&eacute;guli&egrave;rement propos&eacute;es.\n  Nous te tiendrons inform&eacute;.</p>"},
  {"type": "brut", "contenu": "<p style=\"margin-top: 24px;\">Bien &agrave; toi,<br>"},
  {"type": "brut", "contenu": "<strong>{{signature}}, {{marque}}</strong></p>"},
  # LA VOIE DE RECLAMATION, VISIBLE. C'etait une phrase grise de 13 px collee
  # sous la signature : illisible, et personne ne la voyait. L'indicateur 31
  # demande que la voie de reclamation soit PORTEE A LA CONNAISSANCE du
  # beneficiaire — une mention qu'on ne voit pas ne la porte a la connaissance
  # de personne. D'ou un encadre titre, a la taille du reste du message.
  # Construit en TABLE et non en div : Outlook ignore les bordures et le fond
  # d'un div, et le bloc y apparaitrait sans son cadre.
  {"type": "brut", "contenu": "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" width=\"100%\" style=\"margin-top:26px;border-collapse:collapse;\"><tr><td style=\"border:1px solid #dbe1f0;border-left:4px solid #4f7ef8;border-radius:8px;padding:15px 18px;background:#f7f9ff;\">"},
  {"type": "brut", "contenu": "<p style=\"margin:0 0 7px;font-size:15px;font-weight:bold;color:#1a1d2e;\">R&eacute;clamation</p>"},
  {"type": "brut", "contenu": "<p style=\"margin:0 0 12px;font-size:14px;line-height:1.55;color:#3d4250;\">Une remarque, une insatisfaction sur le d&eacute;roulement de cette formation ? Dis-le-nous : nous accusons r&eacute;ception et te r&eacute;pondons sous <strong>{{delai_reclamation}} jours</strong>.</p>"},
  {"type": "brut", "contenu": "<p style=\"margin:0;\"><a href=\"{{lien_reclamation}}\" style=\"display:inline-block;background:#4f7ef8;color:#ffffff;text-decoration:none;font-size:14px;font-weight:bold;padding:10px 20px;border-radius:7px;\">Adresser une r&eacute;clamation</a></p>"},
  {"type": "brut", "contenu": "</td></tr></table>"},
 ],
 "invitation": [
  {"type": "texte", "contenu": "Bonjour **{{prenom}}**,"},
  {"type": "texte", "contenu": "Nous avons le plaisir de vous convier à la formation **« {{titre_formation}} »**, qui se tiendra le **{{dates}}**."},
  {"type": "encadre", "ton": "vert", "contenu": "Vous êtes **cordialement invité·e par {{marque}}** : **aucune démarche de règlement** n'est à effectuer de votre part.\nSi vous avez reçu un message mentionnant des modalités de paiement, il ne vous concerne pas."},
  {"type": "texte", "contenu": "Tout le reste se déroule normalement : convention de formation, feuille d'émargement, questionnaires et attestation de fin de formation."},
  {"type": "texte", "contenu": "En cas de question, répondez simplement à ce mail."},
  {"type": "signature", "contenu": "Au plaisir de vous accueillir,\n**{{signature}}, {{marque}}**"},
 ],
}
def expediteur(fiche_session=None):
    """L'adresse d'ou part le mail, selon l'ORGANISME actif.

    Sans cela, Gmail met l'adresse du compte connecte — smileclubformations —
    sur TOUS les mails. Un praticien inscrit chez DSF recevrait sa convention
    depuis l'adresse de Smileclub. Deux entites juridiques, deux Qualiopi :
    l'expediteur n'est pas un detail cosmetique.

    L'adresse doit avoir ete declaree dans Gmail (« Envoyer des e-mails en tant
    que ») et verifiee. Sinon Gmail refuse l'envoi — on prefere ce refus franc
    a un mail parti sous la mauvaise identite.

    Rend "" si rien n'est connu : Gmail reprend alors son comportement
    d'origine, celui d'avant cette fonction."""
    S = fiche_session
    if S is None:
        try:
            import sessions as _s
            S = _s.COMMUN
        except Exception:
            return ""
    adresse = str((S or {}).get("mail_contact") or "").strip()
    if not adresse or "@" not in adresse:
        return ""
    nom = str((S or {}).get("marque") or (S or {}).get("organisme") or "").strip()
    if not nom:
        return adresse
    # Le nom affiche est encode : un accent brut dans un en-tete casse le mail.
    from email.header import Header
    return str(Header(nom, "utf-8")) + " <" + adresse + ">"


def charger():
    try:
        with open(_FICHIER, encoding="utf-8") as f:
            tout = json.load(f)
    except Exception:
        tout = {}
    return tout if isinstance(tout, dict) else {}
def enregistrer(tout):
    import fichiers
    fichiers.ecrire(_FICHIER, tout)
def lister(usage=None):
    tout = charger()
    sortie = []
    for cle, fiche in tout.items():
        if usage and fiche.get("usage") != usage:
            continue
        f = dict(fiche)
        f["id"] = cle
        sortie.append(f)
    sortie.sort(key=lambda x: (x.get("titre") or "").lower())
    return sortie
def modele(identifiant):
    if not identifiant:
        return None
    f = charger().get(identifiant)
    if not f:
        return None
    g = dict(f)
    g["id"] = identifiant
    return g
def defaut(usage):
    f = DEFAUTS.get(usage)
    if not f:
        return None
    g = dict(f)
    g["id"] = ""
    g["usage"] = usage
    g["blocs"] = [dict(b) for b in BLOCS_DEFAUTS.get(usage, [])]
    g.pop("corps", None)
    return g
def nouvel_id(usage, titre):
    base = re.sub(r"[^a-z0-9]+", "-", (titre or usage).lower()).strip("-") or usage
    base = usage + "-" + base
    tout = charger()
    if base not in tout:
        return base
    n = 2
    while (base + "-" + str(n)) in tout:
        n += 1
    return base + "-" + str(n)
def sauver(identifiant, fiche):
    tout = charger()
    if not identifiant:
        identifiant = nouvel_id(fiche.get("usage") or "mail", fiche.get("titre"))
    fiche = dict(fiche)
    fiche["modifie_le"] = _datetime.now().strftime("%d/%m/%Y %H:%M")
    tout[identifiant] = fiche
    enregistrer(tout)
    return identifiant
def supprimer(identifiant):
    tout = charger()
    if identifiant in tout:
        del tout[identifiant]
        enregistrer(tout)
        return True
    return False
def pour_formation(code_formation, usage):
    try:
        from sessions import FORMATIONS
        ref = (FORMATIONS.get(code_formation) or {}).get("modele_mail_" + usage)
    except Exception:
        ref = None
    if ref:
        f = modele(ref)
        if f:
            return f
    return defaut(usage)
def _jours_de(S):
    """Les journees de la session, mises en forme pour un document.

    Rend un dictionnaire vide plutot que de lever : une balise absente vaut
    mieux qu'un mail qui ne part pas.
    """
    try:
        import jours as _J
        r = _J.resume(S or {})
        if not r["jours"]:
            return {}
        return {
            "date_debut": _J._d(r["date_debut"]).strftime("%d/%m/%Y"),
            "date_fin": _J._d(r["date_fin"]).strftime("%d/%m/%Y"),
            "jours_formation": "<br>".join(r["detail"]),
            "nb_jours": str(r["nb"]),
            "duree_texte": "%s heures" % r["duree"],
        }
    except Exception:
        return {}


def contexte(S, ligne=None, extras=None):
    ligne = ligne or {}
    def n(v):
        return "" if v is None else str(v)
    prenom = n(ligne.get("prenom")).strip()
    nom = n(ligne.get("nom")).strip().upper()
    c = {
        "prenom": prenom,
        "nom": nom,
        "nom_prenom": (prenom + " " + nom).strip(),
        "mail": n(ligne.get("mail")).strip(),
        "ville": n(ligne.get("ville")),
        "formation": n(S.get("nom_formation")),
        "titre_formation": n(S.get("titre_complet") or S.get("nom_formation")),
        "dates": n(S.get("date_texte")),
        "horaires": n(S.get("horaires")),
        "lieu": n(S.get("adresse")),
        # La duree se DEDUIT des journees retenues : 7 h par journee. Le champ
        # « duree_heures » de la fiche formation reste le repli, pour les
        # sessions ecrites avant l'existence de la liste.
        "duree": n(_jours_de(S).get("duree_texte") or S.get("duree") or S.get("duree_heures")),
        "tarif": n(ligne.get("montant_du") or S.get("tarif")),
        "formateur": n(S.get("formateur")),
        "organisme": n(S.get("organisme")),
        "marque": n(S.get("marque") or S.get("organisme")),
        "signature": n(S.get("signature_mail") or S.get("formateur")),
        "mail_contact": n(S.get("mail_contact")),
        "telephone": n(S.get("telephone_contact")),
        "iban": n(S.get("iban")),
        "bic": n(S.get("bic")),
        "lien_paiement": n(S.get("stripe_lien")),
        "lien_signature": "",
        "lien_annulation": "",
        "delai_reglement": "",
        "intro": "",
    }
    try:
        import parametres
        c["delai_reglement"] = str(parametres.valeur("delai_reglement", 20))
    except Exception:
        c["delai_reglement"] = "20"
    # --- Mentions Qualiopi, disponibles dans tous les modeles ---
    # Elles se resolvent a VIDE tant que la fiche de l'organisme n'est pas
    # renseignee : un mail qui annoncerait un referent sans nom, ou une adresse
    # de reclamation inexistante, serait pire que le silence.
    try:
        import accessibilite as _acc
        c["accessibilite"] = _acc.phrase(S)
    except Exception:
        c["accessibilite"] = ""
    contact_rec = n(S.get("reclamations_contact")).strip()
    delai_rec = n(S.get("reclamations_delai")).strip() or "15"
    c["reclamations"] = ("Une remarque, un désaccord ? Écrivez à %s : nous accusons "
                         "réception et vous répondons sous %s jours."
                         % (contact_rec, delai_rec)) if contact_rec else ""
    c["referent_handicap"] = n(S.get("referent_handicap")).strip()
    # Debut, fin et detail des journees : un financeur lit les bornes comme
    # deux champs distincts, et verifie le detail en regard.
    _j = _jours_de(S)
    for cle in ("date_debut", "date_fin", "jours_formation", "nb_jours"):
        c[cle] = _j.get(cle, "")
    # Le lien de depot d'une reclamation, prerempli du nom et de l'adresse du
    # destinataire quand on les connait : une personne mecontente ne doit pas
    # avoir a ressaisir ce que l'organisme sait deja.
    try:
        import reclamations as _rec
        c["lien_reclamation"] = _rec.lien(contact_ligne=dict(ligne, _session=S.get("code") or ""))
    except Exception:
        c["lien_reclamation"] = ""
    c["delai_reclamation"] = n(S.get("reclamations_delai")).strip() or "15"
    for cle, valeur in (extras or {}).items():
        if valeur is not None:
            c[cle] = str(valeur)
    return c
def remplacer(texte, contexte):
    if not texte:
        return ""
    def sub(m):
        cle = m.group(1).strip()
        v = contexte.get(cle)
        return "" if v is None else str(v)
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", sub, texte)
def rendre(fiche, contexte, promu=False):
    objet = fiche.get("objet_promu") if (promu and fiche.get("objet_promu")) else fiche.get("objet")
    if fiche.get("blocs"):
        corps = remplacer(html_depuis_blocs(fiche.get("blocs")), contexte)
    else:
        corps = remplacer(fiche.get("corps") or "", contexte)
    html = ENVELOPPE.replace("{CORPS}", corps)
    html = remplacer(html, contexte)
    return {"objet": remplacer(objet or "", contexte), "html": html}
def exemple():
    c = {}
    for _, groupe in BALISES:
        for cle, _, valeur in groupe:
            c[cle] = valeur
    return c
def inconnues(texte):
    connues = set()
    for _, groupe in BALISES:
        for cle, _, _ in groupe:
            connues.add(cle)
    return sorted({m for m in re.findall(r"\{\{\s*(\w+)\s*\}\}", texte or "") if m not in connues})
