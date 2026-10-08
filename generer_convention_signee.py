from sessions import session, cle_nom
import convention
from supabase import create_client
from datetime import datetime
import config
import base64
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "la convention signee est unique, au nom du client.")
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
a_generer = [l for l in lignes if suivi.calculer_statut(l) == "Convention a generer"]
if not a_generer:
    print("-> Aucune convention a generer.")
    exit()
print(f"-> {len(a_generer)} convention(s) a generer.")
date_jour = datetime.now().strftime("%d/%m/%Y")
compte = 0
for ligne in a_generer:
    nom_prenom = f"{ligne['prenom']} {ligne['nom']}".strip()
    print(f"-> Traitement de {nom_prenom}...")
    # Verrou anti-melange (B7) : la signature doit venir de CETTE formation.
    # Le filtre exact sur le nom est remplace par un rapprochement normalise :
    # un tiret ou un accent de difference laissait la convention non generee,
    # avec pour seul message un "Signature introuvable" trompeur.
    # Le lien de signature transmet l'intitule COMPLET depuis le 03/08/2026,
    # le nom court avant. Les deux formes coexistent dans la table : filtrer
    # sur le seul nom court laissait « Signature introuvable » sur toute
    # signature recente, et la convention n'etait jamais editee.
    _formes = [f for f in dict.fromkeys([S.get("nom_formation") or "",
                                         S.get("titre_complet") or ""]) if f]
    reponse = _avec_reprise(lambda: supabase.table("Signatures").select("*").in_(
        "formation", _formes).order("created_at", desc=True).execute())
    cible = cle_nom(nom_prenom)
    import preuves
    _classees = preuves.par_session(reponse.data, CODE)
    trouvees = [x for x in _classees if cle_nom(x.get("praticien")) == cible]
    if not trouvees:
        print("   Signature introuvable dans Supabase. Ignore.")
        noms = sorted({(x.get("praticien") or "") for x in (reponse.data or [])})
        if noms:
            print("   Signatures connues pour cette formation : " + ", ".join(noms[:6]))
        continue
    if (trouvees[0].get("praticien") or "") != nom_prenom:
        print(f"   Rapproche par nom normalise : « {trouvees[0].get('praticien')} ».")
    # LA SIGNATURE ARRIVE DEJA EN « data: ». L'ancien script la deposait dans
    # le Drive PUIS la rendait publique, uniquement pour qu'un Google Docs
    # puisse l'afficher : deux appels reseau et une signature manuscrite
    # exposee par lien, pour une image qu'on avait sous la main.
    signature_data = (trouvees[0].get("signature_images") or "").strip()
    if not signature_data.startswith("data:"):
        print("   Signature illisible : rien n'est edite pour cette personne.")
        continue
    pdf_bytes, souci = convention.fabriquer(CODE, signature_client=signature_data,
                                            ligne=ligne)
    if not pdf_bytes:
        print("   " + souci)
        continue
    # Le rangement passe par la couche « documents ».
    import documents
    nom_pdf = f"Convention SIGNEE - {nom_prenom}.pdf"
    ref, lien_pdf, _souci = documents.ranger(CODE, "convention_signee", nom_pdf, pdf_bytes)
    if not ref:
        print("   ECHEC : " + _souci)
        continue
    suivi.ecrire(ligne["_numero"], "lien_pdf", lien_pdf, CODE)
    ligne["lien_pdf"] = lien_pdf
    # Detail = lien du document : sans lui, impossible de retrouver la piece.
    suivi.marquer(ligne, "convention_pdf_le", code=CODE, detail=lien_pdf)
    print("   PDF genere et enregistre dans le suivi.")
    compte += 1
print(f"-> Termine : {compte} convention(s) signee(s) generee(s).")
