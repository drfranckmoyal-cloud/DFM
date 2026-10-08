from supabase import create_client
from sessions import session, cle_nom
import config
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "les annulations individuelles passent par un lien qui n'est pas envoye ici.")
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
actifs = [l for l in lignes if not l["annulation_demandee_le"] and not l["annule_le"]]
if not actifs:
    print("-> Aucune inscription active.")
    exit()
print("-> Interrogation de Supabase...")
# Verrou anti-melange (B7) : seules les demandes de CETTE formation.
# Meme correction que dans relever_signatures.py : le lien transmet l'intitule
# COMPLET depuis le 03/08/2026, la table contient donc les deux formes. Filtrer
# sur le seul nom court laissait passer les demandes d'annulation recentes.
_formes = [f for f in dict.fromkeys([S.get("nom_formation") or "",
                                     S.get("titre_complet") or ""]) if f]
import preuves as _pv
reponse = _avec_reprise(lambda: _pv.lire(
    lambda: supabase.table("Annulations").select(
        "praticien, motif, created_at, session").in_("formation", _formes).order(
        "created_at", desc=True).execute(),
    lambda: supabase.table("Annulations").select(
        "praticien, motif, created_at").in_("formation", _formes).order(
        "created_at", desc=True).execute()))
# Cle normalisee : casse, accents et tirets ne doivent pas empecher le
# rapprochement d'une demande d'annulation (B7).
demandes = {}
import preuves
for e in preuves.par_session(reponse.data, CODE):
    nom = (e.get("praticien") or "").strip()
    cle = cle_nom(nom)
    if cle and cle not in demandes:
        demandes[cle] = (nom, e.get("motif", ""))
compte = 0
rapprochees = set()
for ligne in actifs:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    cle = cle_nom(nom_prenom)
    if cle in demandes:
        rapprochees.add(cle)
        motif = demandes[cle][1] or "non precise"
        suivi.ecrire(ligne["_numero"], "motif_annulation", motif, CODE)
        ligne["motif_annulation"] = motif
        suivi.marquer(ligne, "annulation_demandee_le", code=CODE)
        print(f"   . {nom_prenom} demande l'annulation (motif : {motif})")
        compte += 1
orphelines = [v[0] for k, v in demandes.items() if k not in rapprochees]
if orphelines:
    print(f"-> ATTENTION : {len(orphelines)} demande(s) d'annulation sans inscrit correspondant :")
    for o in orphelines:
        print(f"   . « {o} » a demande l'annulation, sans correspondance dans cette session.")
if compte:
    print(f"\n-> {compte} demande(s) enregistree(s). Statut : Annulation demandee.")
    print("   A valider depuis la fiche de session, bouton Annulation.")
else:
    print("-> Aucune nouvelle demande d'annulation.")
