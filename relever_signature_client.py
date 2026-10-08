"""Relever la signature du representant legal d'une session client.

    python3 relever_signature_client.py <code_session>

UNE SEULE SIGNATURE A RELEVER, pas une par praticien : c'est la structure qui
s'engage, par son representant. Le pendant individuel — relever_signatures.py —
refuse explicitement les sessions clients ; ce script fait l'inverse.

OU EST ECRITE LA TRACE : sur la fiche de session, pas dans le suivi. Les
colonnes du suivi decrivent un parcours individuel ; une signature collective
n'y a pas sa place. Meme choix que pour l'envoi de la convention.

POURQUOI C'EST LA PIECE CENTRALE : la facture client se declenche a la
validation de la convention signee (choix du 03/08/2026). Sans cette relevee,
rien ne peut declencher la facturation.

NON BLOQUANT : un echec ici ne doit pas arreter le pipeline.
"""
import sys
from datetime import datetime

from sessions import session, est_client, client_de, cle_nom, date_fr
import config

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CODE = ARGS[0] if ARGS else None
S = session(CODE)
print(f"-> Session : {S['nom_formation']} ({S['code']})")

if not est_client(CODE):
    print("-> Session individuelle : les signatures se relevent une par une.")
    raise SystemExit(0)

import clients as CL
fiche_client = CL.client(client_de(CODE)) or {}
if not fiche_client:
    print("-> Client introuvable dans la base. Rien a relever.")
    raise SystemExit(0)
raison = (fiche_client.get("raison_sociale") or "").strip()
if not raison:
    print("-> Le client n'a pas de raison sociale : impossible de reconnaitre sa signature.")
    raise SystemExit(0)

# Deja relevee ? On ne refait pas le travail, et surtout on n'ecrit pas une
# seconde fois dans le journal a chaque passage du pipeline.
import sessions as _S
_BRUTES = _S._charger_json(_S._FICHIER_S)
_fiche_brute = dict(_BRUTES.get(CODE) or {})
deja = str(_fiche_brute.get("convention_client_signee_le") or "").strip()
if deja:
    print(f"-> Convention deja signee le {deja} par {raison}.")
    raise SystemExit(0)

from supabase import create_client
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


def _avec_reprise(executer):
    """Seconde tentative apres un delai reseau : le projet Supabase (offre
    gratuite) se met en pause apres inactivite, et la premiere requete du matin
    expire. Meme garde que dans relever_signatures.py."""
    try:
        return executer()
    except Exception:
        import time
        time.sleep(4)
        resultat = executer()
        print("-> Supabase a repondu a la seconde tentative (reveil a froid probable).")
        return resultat


# DEUX FORMES du nom de formation coexistent dans la table : le nom court
# jusqu'au 03/08/2026, l'intitule complet depuis. On interroge sur les deux,
# sinon aucune signature recente ne serait trouvee.
_formes = [f for f in dict.fromkeys([S.get("nom_formation") or "",
                                     S.get("titre_complet") or ""]) if f]
print(f"-> Recherche de la signature de « {raison} »...")
import preuves as _pv
reponse = _avec_reprise(lambda: _pv.lire(
    lambda: supabase.table("Signatures").select(
        "praticien, created_at, session").in_("formation", _formes).order(
        "created_at", desc=True).execute(),
    lambda: supabase.table("Signatures").select(
        "praticien, created_at").in_("formation", _formes).order(
        "created_at", desc=True).execute()))

# Rapprochement par cle normalisee : casse, accents, parentheses et tirets ne
# doivent pas empecher de reconnaitre le signataire.
attendue = cle_nom(raison)
trouvee = None
import preuves
for enregistrement in preuves.par_session(reponse.data, CODE):
    nom = (enregistrement.get("praticien") or "").strip()
    if nom and cle_nom(nom) == attendue:
        trouvee = (nom, enregistrement.get("created_at", ""))
        break

if not trouvee:
    print("   Pas encore signee.")
    autres = {(e.get("praticien") or "").strip() for e in (reponse.data or [])}
    autres = {a for a in autres if a and cle_nom(a) != attendue}
    if autres:
        print("   (%d autre(s) signataire(s) sur cette formation : ce sont les"
              % len(autres))
        print("    praticiens des sessions individuelles, c'est normal.)")
    raise SystemExit(0)

tel_quel, quand = trouvee
# Format francais des l'ecriture : la trace est relue telle quelle dans les
# mails au client, et « 2026-08-03 » s'y lisait mal.
horodatage = date_fr(quand)
print(f"   Signee le {horodatage} par « {tel_quel} ».")
if tel_quel != raison:
    print(f"   (la fiche client porte « {raison} » — rapprochement par nom normalise)")

# La trace, sur la fiche de session. Ecrite APRES avoir trouve, jamais avant.
if _fiche_brute:
    _fiche_brute["convention_client_signee_le"] = horodatage
    _fiche_brute["convention_client_signataire"] = tel_quel
    _S.enregistrer_session(CODE, _fiche_brute)
    print("   Trace ecrite sur la fiche de session.")
else:
    print("   ATTENTION : fiche de session introuvable, la trace n'a pas ete ecrite.")

try:
    import journal
    journal.ecrire("Convention client signée", raison,
                   f"signée le {horodatage}", "", S["code"])
except Exception:
    pass
raise SystemExit(0)
