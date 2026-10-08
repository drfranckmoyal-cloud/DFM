"""Convention UNIQUE d'une session client, au nom de la structure.

Une session client ne produit pas une convention par praticien : elle en produit
UNE, entre l'organisme de formation et le centre, signee par le representant
legal. Les praticiens y figurent, avec leur fonction.

    python3 generer_convention_client.py <code_session>

CE SCRIPT NE PASSE PLUS PAR GOOGLE DOCS. Il appelle convention.fabriquer(),
qui rend le PDF depuis un gabarit HTML local (voir convention.py et pdf.py).
Ce qui disparait, mesure sur ce seul script : la copie du modele, le
remplacement des balises, l'export PDF par le Drive, et la suppression de la
copie temporaire — quatre appels reseau, et un modele qui vivait ailleurs que
le code qui le remplissait.

CE SCRIPT NE MENTIONNE PLUS GOOGLE. Il confie le PDF a documents.ranger(), qui
l'ecrit en local et en pousse une copie d'archive. Le jour ou le stockage passe
en ligne, ce fichier ne bougera pas.

L'IDENTIFIANT DU FICHIER NE CHANGE PAS d'une regeneration a l'autre : un lien
deja transmis au client reste valide.

NON BLOQUANT : un echec ici ne doit pas arreter le pipeline.
"""
import sys

from sessions import session
import convention

CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
print(f"-> Session : {S['nom_formation']} ({S['code']})")

# TOUTES LES VERIFICATIONS SONT DANS LE MODULE : session individuelle, fiche
# client incomplete, aucun participant, signature ou tampon manquants. Le
# script ne les redit pas — deux jeux de regles finissent toujours par diverger.
donnees, souci = convention.pour(CODE)
if not donnees:
    print("-> " + souci)
    raise SystemExit(0)

print(f"-> {donnees['nb_participants']} participant(s) :")
for p in donnees["participants"]:
    print(f"   . {p['nom']} — {p['fonction']}")
print(f"-> {donnees['tarif']} EUR x {donnees['nb_participants']} = {donnees['total']} EUR")

# ON NE REFABRIQUE PAS UNE CONVENTION QUI N'A PAS CHANGE — 19/08/2026.
#
# Ce script refabriquait le PDF a CHAQUE passage, et ecrivait une entree de
# journal a chaque fois. Un pipeline quotidien en produisait une par jour ; le
# bouton « Faire avancer ce dossier » en produit une par clic. Constate le
# 19/08/2026 : quatre « Convention client editee » pour une seule convention,
# dont trois n'apportaient rien. Une piste d'audit ou le meme evenement se
# repete sans raison devient illisible, et c'est exactement ce qu'un auditeur
# regarde.
#
# L'EMPREINTE EXISTE DEJA : envoyer_mail_signature_client s'en sert pour decider
# d'un renvoi. On la reutilise ici plutot que d'en inventer une seconde. Elle
# porte ce qui change une convention — le nombre de participants et le montant.
# Un participant ajoute, et la convention se refait comme il se doit.
_empreinte = "%s participant(s), %s EUR" % (donnees["nb_participants"], donnees["total"])
try:
    import sessions as _S
    _brute = (_S._charger_json(_S._FICHIER_S).get(CODE) or {})
except Exception:
    _brute = {}
if (str(_brute.get("convention_client_envoyee_le") or "").strip()
        and str(_brute.get("convention_client_empreinte") or "").strip() == _empreinte
        and "--forcer" not in sys.argv[1:]):
    print("-> Convention deja etablie et inchangee (%s)." % _empreinte)
    print("   Rien n'est refabrique. Pour la refaire quand meme : --forcer")
    raise SystemExit(0)

try:
    import pdf as _pdf
    contenu = _pdf.depuis_html(convention.html(donnees))
except Exception as e:
    print(f"   ECHEC de la fabrication : {str(e)[:160]}", file=sys.stderr)
    raise SystemExit(0)

# LE RANGEMENT PASSE PAR LA COUCHE « documents ». Ce script ne sait plus ou
# vont ses PDF : ni dossier Drive, ni chemin de disque. C'est ce qui permettra
# de basculer vers un stockage en ligne sans le rouvrir.
import documents

cible = "Convention - " + (donnees["client_denomination"] or "client") + ".pdf"
ref, lien, souci = documents.ranger(CODE, "convention", cible, contenu)
if not ref:
    print("   ECHEC : " + souci, file=sys.stderr)
    raise SystemExit(0)
if lien:
    print("-> Convention prete : " + lien)
else:
    print("-> Convention rangee en local. Copie Drive non partie : " + souci)
    print("   Elle repartira au prochain passage.")
try:
    import journal
    journal.ecrire("Convention client éditée", donnees["client_denomination"],
                   "%s participant(s) — %s EUR" % (donnees["nb_participants"],
                                                   donnees["total"]),
                   "", S["code"])
except Exception:
    pass
raise SystemExit(0)