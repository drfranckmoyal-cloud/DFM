from supabase import create_client
from sessions import session, cle_nom
import config
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "il n'y a pas de signature individuelle a relever.")
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
def _avec_reprise(executer):
    """Seconde tentative apres un delai reseau : le projet Supabase (offre
    gratuite) se met en pause apres inactivite, et la premiere requete du matin
    expire. DEUX tentatives maximum : au-dela, ce n'est plus un reveil a froid
    mais une vraie panne, et elle doit se voir dans le rapport de synchro."""
    try:
        return executer()
    except Exception:
        import time
        time.sleep(4)
        resultat = executer()
        print("-> Supabase a repondu a la seconde tentative (reveil a froid probable).")
        return resultat

print(f"-> Session : {S['nom_formation']} ({S['code']})")
print("-> Lecture du suivi...")
lignes = suivi.lire_lignes_de(CODE)
en_attente = [l for l in lignes if suivi.calculer_statut(l) == "En attente signature"]
if not en_attente:
    print("-> Personne en attente de signature.")
    exit()
print(f"-> {len(en_attente)} praticien(s) en attente de signature.")
print("-> Interrogation de Supabase...")
# Verrou anti-melange (B7) : une signature Masterclass ne doit jamais marquer
# "signe" un homonyme inscrit sur Usures. La table porte la formation.
#
# DEUX FORMES COEXISTENT dans la table. Jusqu'au 03/08/2026 le lien de
# signature transmettait le nom court (« Usures ») ; depuis, il transmet
# l'intitule complet (« Usures : savoir realiser un cas de A a Z »), demande
# pour la fenetre de signature. La relevee cherchait toujours le nom court :
# toute signature posee apres ce changement restait invisible, et le praticien
# attendait indefiniment. On interroge donc sur les deux formes — le verrou
# anti-melange tient toujours, Masterclass et Usures restent distinctes.
_formes = [f for f in dict.fromkeys([S.get("nom_formation") or "",
                                     S.get("titre_complet") or ""]) if f]
import preuves as _pv
reponse = _avec_reprise(lambda: _pv.lire(
    lambda: supabase.table("Signatures").select(
        "praticien, created_at, session").in_("formation", _formes).execute(),
    lambda: supabase.table("Signatures").select(
        "praticien, created_at").in_("formation", _formes).execute()))
# Rapprochement par cle normalisee : casse, accents et tirets ne doivent pas
# empecher de reconnaitre un signataire (B7).
# TRI PAR SESSION. Le nom de formation ne suffit pas : « Usures » est dispensee
# par les deux organismes et plusieurs fois par an. On prend d'abord les
# signatures portant le code de CETTE session, puis les anciennes qui n'en
# portent aucun. Celles d'une autre session sont ecartees — et signalees.
import preuves
_classees = preuves.par_session(reponse.data, CODE)
_autres = preuves.ecartes(reponse.data, CODE)
if _autres:
    print(f"   ({len(_autres)} signature(s) appartiennent a une autre session, ignorees.)")
signataires = {}
for enregistrement in _classees:
    nom = (enregistrement.get("praticien") or "").strip()
    cle = cle_nom(nom)
    # PREMIER GAGNE : la liste est deja ordonnee du plus sur au moins sur.
    if nom and cle not in signataires:
        signataires[cle] = (nom, enregistrement.get("created_at", ""))
compte = 0
rapproches = set()
for ligne in en_attente:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    cle = cle_nom(nom_prenom)
    if cle in signataires:
        rapproches.add(cle)
        suivi.marquer(ligne, "signe_le", code=CODE,
                      detail="signe le " + str(signataires[cle][1])[:16].replace("T", " a "))
        tel_quel = signataires[cle][0]
        ecart = "" if tel_quel == nom_prenom else f"  (signe « {tel_quel} »)"
        print(f"   . {nom_prenom} a signe -> enregistre dans le suivi.{ecart}")
        compte += 1
    else:
        print(f"   . {nom_prenom} : pas encore signe.")
# Une signature qui ne correspond a personne restait invisible : le praticien
# attendait indefiniment sans qu'aucun message ne le signale.
# Comparaison sur TOUS les inscrits de la session, pas seulement ceux en attente
# de signature : sinon chaque personne ayant deja signe fait apparaitre sa propre
# signature comme orpheline a tous les passages suivants. Faux positif introduit
# avec le controle lui-meme, corrige apres l'avoir vu se declencher en reel.
connus = {cle_nom((l["prenom"] or "") + " " + (l["nom"] or "")) for l in lignes}
# Les signataires CLIENTS ne sont pas des orphelins : une structure signe pour
# sa propre session client, qui porte la meme formation que les sessions
# individuelles. Sans cette exclusion, chaque relevee individuelle d'Usures
# annoncerait « PROMOTION DENTAIRE PARIS CENTRE a signe, mais aucun inscrit ne
# porte ce nom » — une alerte qui n'appelle aucune action.
try:
    import clients as _cl
    connus |= {cle_nom(c.get("raison_sociale") or "") for c in (_cl.tous() or {}).values()}
except Exception:
    pass
orphelines = [v[0] for k, v in signataires.items() if k not in rapproches and k not in connus]
if orphelines:
    print(f"-> ATTENTION : {len(orphelines)} signature(s) sans inscrit correspondant :")
    for o in orphelines:
        print(f"   . « {o} » a signe, mais aucun inscrit de cette session ne porte ce nom.")
    print("   Verifie l'orthographe dans l'onglet de suivi, ou la session d'origine.")
print(f"-> Termine : {compte} signature(s) relevee(s).")
