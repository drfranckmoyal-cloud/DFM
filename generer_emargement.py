from connexion import service_drive
from sessions import session
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime
import html as htmlmod
import sys
import pdf as _pdf
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
FORMATEUR = S["formateur"]
ORGANISME = S.get("organisme") or ""
# La mention de declaration d'activite disparait entierement si le numero
# n'est pas renseigne dans le profil : mieux vaut une mention absente
# qu'un faux numero sur une piece contractuelle.
_num = (S.get("numero_declaration") or "").strip()
MENTION_ORGANISME = ORGANISME + (
    " &mdash; d&eacute;claration d'activit&eacute; : " + _num if _num else "")
# « drive = service_drive() » retire le 18/08/2026 : voir plus bas.
print(f"-> Session : {S['nom_formation']} ({S['code']})")
lignes = suivi.lire_lignes_de(CODE)
participants = [l for l in lignes
                if "recontact" not in l["demande"].lower()
                and not l["annule_le"] and not l["annulation_demandee_le"]]
if not participants:
    print("-> Aucun participant.")
    exit()
participants.sort(key=lambda l: l["nom"].upper())
print(f"-> {len(participants)} participant(s) + le formateur.")
# Par IDENTIFIANT. L'ancien reperage passait par le dossier « Templates » pour
# en deduire la racine de l'organisme : avec deux organismes, il designait
# celle du mauvais. Il ne sert plus que de secours, pour qu'un organisme neuf
# obtienne quand meme son dossier.
# LE DOSSIER DRIVE A ETE RETIRE LE 18/08/2026. Il ne servait plus qu'a une
# chose : barrer la route. La feuille est rangee par documents.ranger(), sur le
# disque, depuis le branchement de la couche « documents » — mais on s'arretait
# encore ici sur un « Dossier 'Emargement' introuvable » quand Google ne
# repondait pas. Un document qu'on sait ecrire ne doit pas dependre d'un dossier
# distant ou on ne l'ecrit plus.
titre_propre = htmlmod.unescape(S["titre_complet"])
# LES COLONNES SUIVENT LES JOURNEES REELLES. Elles etaient au nombre de quatre,
# ecrites en dur : « Jour 1 matin / Jour 1 apres-midi / Jour 2 matin / Jour 2
# apres-midi ». Une formation de cinq jours n'avait donc nulle part ou signer
# trois de ses journees — et l'emargement est LA preuve de presence exigee par
# un financeur. Defaut corrige le 06/08/2026, avec le chantier des dates.
import jours as _jours
_j = _jours.resume(S)
_dates = _j["jours"] or [S.get("date_debut")]
debut = datetime.strptime(_j["date_debut"], "%Y-%m-%d").strftime("%d/%m/%Y") \
    if _j["date_debut"] else ""
fin = datetime.strptime(_j["date_fin"], "%Y-%m-%d").strftime("%d/%m/%Y") \
    if _j["date_fin"] else debut
C = "border:1px solid #333;padding:7px 6px;"


def _entete_jour(iso, rang):
    """« Jour 1 · lun. 10/08 » — le rang ET la date, pour qu'une feuille
    imprimee a l'avance reste attribuable au bon jour."""
    d = _jours._d(iso)
    if not d:
        return "Jour %d" % rang
    return "Jour %d<br>%s %s" % (rang, _jours.NOMS_JOUR[d.weekday()][:3] + ".",
                                 d.strftime("%d/%m"))


entetes_sig = []
for i, iso in enumerate(_dates, 1):
    entetes_sig.append(_entete_jour(iso, i) + "<br>matin")
    entetes_sig.append(_entete_jour(iso, i) + "<br>apr&egrave;s-midi")
_n_cols = len(entetes_sig)
# Au-dela de six journees, les colonnes deviennent trop etroites pour une
# signature : on le DIT plutot que de produire une feuille insignable.
if _n_cols > 12:
    print(f"-> ATTENTION : {len(_dates)} journees, soit {_n_cols} colonnes de signature.")
    print("   La feuille sera dense a l'impression. A verifier avant la formation.")
_larg = max(38, int(560 / _n_cols)) if _n_cols else 80
th = "".join(f'<td style="{C}background:#eef2fa;text-align:center;font-size:7pt;'
             f'font-weight:bold;width:{_larg}px;">{e}</td>' for e in entetes_sig)
rangs = ""
for p in participants:
    nom = f"{p['nom'].upper()} {p['prenom']}"
    rangs += (f'<tr><td style="{C}font-size:9pt;">{htmlmod.escape(nom)}</td>'
              + f'<td style="{C}"></td>' * _n_cols + "</tr>")
rangs += (f'<tr><td style="{C}font-size:9pt;background:#f5f8ff;font-weight:bold;">{FORMATEUR}'
          f'<span style="font-weight:normal;font-size:7.5pt;color:#5b6172;"> &mdash; formateur</span></td>'
          + f'<td style="{C}background:#f5f8ff;"></td>' * _n_cols + "</tr>")
# PORTRAIT JUSQU'A DEUX JOURNEES, PAYSAGE AU-DELA. Une case de signature trop
# etroite ne se signe pas : a partir de six colonnes, la largeur d'une A4
# portrait ne suffit plus. L'orientation suit donc le nombre de journees, elle
# ne se regle pas a la main.
_orientation = "portrait" if _n_cols <= 4 else "landscape"
doc_html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Emargement - {htmlmod.escape(S['dossier_session'])}</title>
<style>
@page {{ size: A4 {_orientation}; margin: 12mm 13mm; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #1a1d2e; margin: 0; }}
/* Une ligne de signature ne se coupe jamais entre deux pages : un nom d'un
   cote et sa case de l'autre rendrait la feuille inexploitable. */
tr {{ page-break-inside: avoid; }}
</style></head><body>
<p style="font-size:13pt;font-weight:bold;text-align:center;margin:0 0 3px;">FEUILLE D'&Eacute;MARGEMENT</p>
<p style="font-size:10pt;text-align:center;margin:0 0 12px;">{titre_propre}</p>
<table style="width:100%;border-collapse:collapse;font-size:8pt;margin-bottom:11px;">
<tr><td style="border:1px solid #ccc;padding:4px 7px;background:#f5f8ff;width:100px;">Organisme</td>
<td style="border:1px solid #ccc;padding:4px 7px;">{MENTION_ORGANISME}</td></tr>
<tr><td style="border:1px solid #ccc;padding:4px 7px;background:#f5f8ff;">Dates</td>
<td style="border:1px solid #ccc;padding:4px 7px;">{_jours.texte(_dates)} &mdash; {_j['duree']} heures ({_j['nb']} journ&eacute;e{'s' if _j['nb'] > 1 else ''}) &mdash; {S.get('horaires') or '9h00 &agrave; 17h00'}</td></tr>
<tr><td style="border:1px solid #ccc;padding:4px 7px;background:#f5f8ff;">D&eacute;but / fin</td>
<td style="border:1px solid #ccc;padding:4px 7px;">{debut} &mdash; {fin}</td></tr>
<tr><td style="border:1px solid #ccc;padding:4px 7px;background:#f5f8ff;">Lieu</td>
<td style="border:1px solid #ccc;padding:4px 7px;">{S['adresse']}</td></tr>
</table>
<table style="width:100%;border-collapse:collapse;">
<tr><td style="{C}background:#eef2fa;font-size:8pt;font-weight:bold;width:170px;">Nom et pr&eacute;nom</td>{th}</tr>
{rangs}
</table>
<p style="font-size:7.5pt;color:#5b6172;margin:11px 0 0;">Je soussign&eacute; {FORMATEUR}, formateur, certifie l'exactitude des pr&eacute;sences ci-dessus.</p>
<table style="width:100%;border:none;margin-top:16px;"><tr>
<td style="border:none;width:58%;"></td>
<td style="border:none;font-size:8pt;">Signature et cachet de l'organisme :<br><br><br></td>
</tr></table>
</body></html>"""
# UN PDF, PLUS UN DOCUMENT GOOGLE. La feuille se signe sur papier : elle n'a
# jamais eu vocation a etre modifiee dans le Drive, et un Google Docs se
# repagine tout seul selon le poste qui l'ouvre — une colonne de signature
# pouvait passer a la page suivante entre l'ecran et l'imprimante. Le PDF fixe
# la mise en page une fois pour toutes.
try:
    contenu = _pdf.depuis_html(doc_html)
except _pdf.Indisponible as e:
    print("-> " + str(e))
    exit()
import documents
nom_fichier = f"Emargement - {S['dossier_session']}.pdf"
ref, lien, _souci = documents.ranger(CODE, "emargement", nom_fichier, contenu)
if not ref:
    print("-> ECHEC : " + _souci)
    raise SystemExit(0)
if lien:
    print("-> Feuille rangee. " + lien)
else:
    print("-> Feuille rangee en local ; copie Drive non partie : " + _souci)

# L'ANCIEN GOOGLE DOCS PORTE LE MEME NOM SANS « .pdf ». On le SIGNALE sans y
# toucher : c'est une piece deja produite, parfois deja imprimee et signee.
try:
    import dossiers
    from connexion import service_drive
    _d = service_drive()
    _p = dossiers.trouver(_d, S, "dossier_emargement", "Emargement")
    _legs = _d.files().list(
        q="name='Emargement - %s' and '%s' in parents and trashed=false"
          % (S["dossier_session"], _p), fields="files(id)").execute().get("files", []) if _p else []
    if _legs:
        print("-> NOTE : %d ancienne(s) feuille(s) au format Google Docs porte(nt)" % len(_legs))
        print("   encore le meme nom sans « .pdf ». Laissee(s) en place.")
except Exception:
    pass

print(f"\n-> Feuille d'emargement generee en PDF, {_orientation} "
      f"({len(participants)} participant(s) + formateur, {_n_cols} colonnes).")
import journal
journal.ecrire("Feuille d'émargement générée", "", f"{len(participants)} participant(s)", "", S["code"])
