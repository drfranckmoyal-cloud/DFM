from connexion import service_sheets
from sessions import session
from datetime import datetime
import sys
import suivi
CODE = sys.argv[1] if len(sys.argv) > 1 else None
S = session(CODE)
# Palier 3 : cette etape ne concerne que les sessions individuelles.
import sessions as _sessions
_sessions.refuser_si_client(CODE, "les participants sont saisis a la main, il n'y a pas de formulaire.")

# ON SORT AVANT D'APPELER GOOGLE — 19/08/2026. Ce controle vivait plus bas, dans
# verifier_entetes(), donc APRES « sheets = service_sheets() ». Consequence : une
# session sans formulaire Google — l'etat normal depuis que les inscriptions
# passent par le formulaire DFM — ouvrait quand meme une session OAuth, et
# mourait avec elle quand l'autorisation etait expiree. Le dernier script du
# pipeline a mourir de Google mourait pour ne rien faire.
if not (S.get("sheet_reponses") or "").strip():
    print(f"-> Session : {S['nom_formation']} ({S['code']})")
    print("-> Aucun formulaire Google sur cette session : les inscriptions")
    print("   passent par le formulaire DFM, reprises a l'etape suivante.")
    print("   Etape sans objet ici. Rien n'a ete fait, et ce n'est pas une erreur.")
    raise SystemExit(0)

sheets = service_sheets()
print(f"-> Session : {S['nom_formation']} ({S['code']})")
# L'ETAT VIENT DE LA BASE LOCALE. Il fallait lire deux cents lignes de l'onglet
# Google pour retrouver une session par son code et lire une cellule.
import sessions as _sess
statut_session = _sess.etat(CODE).get("statut_session") or "ouverte"
print(f"-> Statut : {statut_session}")
def _norm_entete(v):
    return " ".join((v or "").split()).casefold()
def _colonne(i):
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i] if i < 26 else "colonne " + str(i + 1)
def _refuser(lignes, resume):
    """Diagnostic sur la sortie d'erreur, puis arret.
    dfm.py reprend les 6 dernieres lignes de stderr dans le rapport de synchro,
    et la toute derniere comme cause affichee : le resume vient donc en dernier."""
    for l in lignes:
        print(l, file=sys.stderr)
    print(resume, file=sys.stderr)
    sys.exit(1)
def verifier_entetes():
    """Le formulaire est recopie par position dans les colonnes A:M du suivi.
    Un ecart d'ordre y ferait atterrir les donnees dans les mauvaises colonnes,
    sans lever la moindre erreur. Pire, les horodateurs importes deviendraient
    "connus" : une relance apres correction les ignorerait, et les lignes fausses
    resteraient en place. On interrompt donc plutot que d'ecrire."""
    # LE CLASSEUR EST-IL SEULEMENT LISIBLE ? Sans ce controle, toute panne de
    # lecture — classeur supprime, acces revoque, reseau coupe — retombait sur
    # « la ligne 1 du Sheet de reponses est vide ». Le message accusait les
    # en-tetes alors que le document n'avait jamais ete ouvert : on cherchait
    # une virgule dans un formulaire parfaitement sain.

    def _lire(feuille, plage, quoi):
        try:
            return sheets.spreadsheets().values().get(
                spreadsheetId=feuille, range=plage).execute().get("values", [[]])[0]
        except Exception as e:
            code = getattr(getattr(e, "resp", None), "status", 0)
            if code == 404:
                cause = "introuvable — il a ete supprime, ou l'identifiant est faux"
            elif code == 403:
                cause = "inaccessible — le compte connecte n'a pas les droits dessus"
            elif code:
                cause = "illisible (erreur %s)" % code
            else:
                cause = "illisible : " + str(e)[:70]
            _refuser(["Import interrompu : le %s est %s." % (quoi, cause)],
                     "Import interrompu : le %s de %s est %s. Identifiant : %s. "
                     "Aucune ligne importee." % (quoi, S["code"], cause, feuille))

    form = _lire(S["sheet_reponses"], "A1:Z1", "classeur de reponses")
    cible = _lire(S["sheet_suivi"], f"'{S['onglet_suivi']}'!A1:M1", "classeur de suivi")
    if not cible:
        _refuser(["Import interrompu : l'onglet de suivi n'a pas d'en-tetes."],
                 "Import interrompu : la ligne 1 de l'onglet " + S["onglet_suivi"]
                 + " est vide. Recree la session ou renseigne ses en-tetes.")
    if not form:
        _refuser(["Import interrompu : le formulaire n'a pas d'en-tetes."],
                 "Import interrompu : la ligne 1 du Sheet de reponses est vide.")
    # LA QUESTION « FONCTION » n'a pas de colonne en face dans le bloc A:M —
    # elle est rangee en AX. On la met donc de cote avant de comparer, sinon le
    # controle verrait une question de trop et refuserait un formulaire
    # parfaitement correct.
    #
    # ELLE PEUT ETRE N'IMPORTE OU dans le formulaire, pas seulement en dernier.
    # Le critere d'acceptation est strict : son retrait doit faire coincider
    # EXACTEMENT les 13 questions restantes avec les 13 colonnes du suivi. Un
    # intitule contenant « fonction » par hasard — « Comment fonctionne votre
    # cabinet ? » — ne passerait donc pas ce test, puisque l'ecarter laisserait
    # les autres questions decalees.
    global COLONNE_FONCTION
    COLONNE_FONCTION = -1
    if len(form) == len(cible) + 1:
        # « fonction » comme MOT ENTIER : « Comment fonctionne votre cabinet ? »
        # ne doit pas etre pris pour la question de la fonction. Sa reponse
        # serait ramenee a « Chirurgien-dentiste » sans que rien ne le signale.
        import re as _re
        _mot = _re.compile(r"\bfonction\b")
        candidats = [i for i, x in enumerate(form) if _mot.search(_norm_entete(x))]
        for i in candidats:
            essai = form[:i] + form[i + 1:]
            if all(_norm_entete(a) == _norm_entete(b) for a, b in zip(essai, cible)):
                COLONNE_FONCTION = i
                form = essai
                print("-> Le formulaire pose la question de la fonction (colonne %s)."
                      % _colonne(i))
                break
        if COLONNE_FONCTION < 0 and candidats:
            print("-> Une question evoque la fonction (colonne %s), mais l'ecarter ne"
                  % _colonne(candidats[0]))
            print("   fait pas coincider les autres : elle n'est pas traitee comme telle.")
    ecarts = []
    for i in range(max(len(form), len(cible))):
        a = form[i] if i < len(form) else ""
        b = cible[i] if i < len(cible) else ""
        if _norm_entete(a) != _norm_entete(b):
            ecarts.append((i, b, a))
    if not ecarts:
        print(f"-> En-tetes conformes ({len(cible)} colonnes).")
        return
    lignes = ["Import interrompu : les questions du formulaire ne correspondent plus aux colonnes du suivi.",
              "Onglet " + S["onglet_suivi"] + " : " + str(len(form))
              + " question(s) au formulaire, " + str(len(cible)) + " colonne(s) au suivi."]
    for i, attendu, trouve in ecarts[:3]:
        lignes.append("  colonne " + _colonne(i) + " : attendu "
                      + (repr(attendu) if attendu else "(aucune colonne)")
                      + ", trouve " + (repr(trouve) if trouve else "(aucune question)"))
    if len(ecarts) > 3:
        lignes.append("  ... et " + str(len(ecarts) - 3) + " autre(s) ecart(s).")
    _refuser(lignes,
             "Import interrompu : " + str(len(ecarts)) + " colonne(s) divergente(s) sur "
             + S["code"] + ", la premiere en colonne " + _colonne(ecarts[0][0])
             + ". Aucune ligne importee. Verifie l'ordre des questions du Google Form.")
verifier_entetes()
# On lit une colonne de plus que le bloc recopie : la 14e porte la fonction
# quand le formulaire la demande. Sans question posee, elle est simplement vide.
reponses = sheets.spreadsheets().values().get(
    spreadsheetId=S["sheet_reponses"], range="A1:N1000"
).execute().get("values", [])
if len(reponses) < 2:
    print("-> Aucune inscription dans le Form.")
    exit()
inscriptions = reponses[1:]
# LES DEJA-CONNUS VIENNENT DE LA BASE. L'horodateur du formulaire sert de
# marque d'unicite : c'est lui qui evite de reimporter deux fois la meme
# inscription. Il etait relu dans le classeur ; il est desormais local, donc
# un import reste possible meme si Google ne repond pas en lecture.
connus = [l["horodateur"] for l in suivi.lire_lignes_de(CODE) if l.get("horodateur")]
print(f"   {len(inscriptions)} dans le Form, {len(connus)} deja suivie(s).")
nouvelles = [l for l in inscriptions if l and l[0] and l[0] not in connus]
if not nouvelles:
    print("-> Rien a importer.")
    exit()
lignes = suivi.lire_lignes_de(CODE)
occupees = len([l for l in lignes
                if "recontact" not in l["demande"].lower()
                and not l["annule_le"] and not l["annulation_demandee_le"]
                and suivi.calculer_statut(l) != "File d'attente"])
maxi = S["places_max"]
complete = occupees >= maxi
print(f"\n-> Capacite : {occupees}/{maxi}{'  COMPLET' if complete else ''}")
print(f"-> {len(nouvelles)} nouvelle(s) inscription(s) :")
for l in nouvelles:
    nom = l[1] if len(l) > 1 else "?"
    prenom = l[2] if len(l) > 2 else "?"
    demande = l[7] if len(l) > 7 else ""
    marque = "confirme" if "confirme" in demande.lower() else "a recontacter"
    print(f"   . {prenom} {nom} ({marque})")
en_attente = complete or statut_session == "cloturee"
if en_attente:
    motif = "session cloturee" if statut_session == "cloturee" else "capacite atteinte"
    print(f"\n-> {motif.upper()} : les nouvelles confirmations partent en file d'attente.")
    print("   Pour en faire monter une : fiche de session, bouton Promouvoir.")
# LA FONCTION va en AX, pas dans le bloc du formulaire. On etale donc chaque
# ligne jusqu'a cette colonne : les cases intermediaires sont celles que DFM
# remplira lui-meme au fil du parcours, et elles sont vides sur une inscription
# neuve. Sans question posee au formulaire, on ecrit A:M comme avant.
# LES TREIZE PREMIERES COLONNES du suivi sont, dans l'ordre, celles du
# formulaire. On les nomme plutot que de recopier un bloc par position : une
# question deplacee dans le Form decalait silencieusement tout le reste.
_BLOC_FORM = ["horodateur", "nom", "prenom", "mail", "telephone", "ville",
              "date_formation", "demande", "connu_par", "dejeuner",
              "restrictions", "image", "pmr"]
_a_ajouter = []
for l in nouvelles:
    if COLONNE_FONCTION >= 0:
        brute = (l[COLONNE_FONCTION] if len(l) > COLONNE_FONCTION else "")
        # On RETIRE la colonne de la fonction, ou qu'elle soit, avant de recopier
        # le bloc du formulaire. Prendre « les 13 premieres » ne vaudrait que si
        # la question etait en dernier.
        bloc = [x for i, x in enumerate(l) if i != COLONNE_FONCTION][:13]
    else:
        brute, bloc = "", list(l[:13])
    bloc += [""] * (13 - len(bloc))
    d = dict(zip(_BLOC_FORM, bloc))
    if str(brute).strip():
        import contacts as _C
        # Une reponse hors catalogue est ramenee, jamais refusee : une
        # inscription ne doit pas echouer sur un libelle inattendu.
        d["fonction"] = _C.fonction_valide(brute)
    _a_ajouter.append(d)
suivi.ajouter_plusieurs(_a_ajouter, CODE)
print(f"\n-> {len(nouvelles)} ligne(s) ajoutee(s).")
import journal
journal.ecrire("Inscriptions importées", "", f"{len(nouvelles)} nouvelle(s)", "", S["code"])
# ON PARCOURT LES DICTIONNAIRES, plus les listes brutes du formulaire.
# L'ancienne version indexait « nouvelles » par position — 1 le nom, 2 le
# prenom, 7 la demande — ce qui ne valait qu'apres avoir retire la colonne de
# la fonction. Selon l'endroit ou cette question se trouve dans le Form, ces
# positions se decalaient et le journal nommait la mauvaise personne.
for _l in _a_ajouter:
    _nom = (_l.get("nom") or "").strip()
    _prenom = (_l.get("prenom") or "").strip()
    _demande = (_l.get("demande") or "").lower()
    _qui = (_prenom + " " + _nom.upper()).strip() or "un praticien"
    if "recontact" in _demande:
        journal.ecrire("Demande de rappel reçue", _qui, "à recontacter", "", S["code"])
    elif en_attente:
        journal.ecrire("Place en file d'attente", _qui, motif, "", S["code"])
    else:
        journal.ecrire("Nouvelle inscription", _qui, "", "", S["code"])
if en_attente:
    maintenant = datetime.now().strftime("%d/%m/%Y %H:%M")
    neufs = [l.get("horodateur") for l in _a_ajouter if l.get("horodateur")]
    for ligne in suivi.lire_lignes_de(CODE):
        if ligne["horodateur"] in neufs and "confirme" in ligne["demande"].lower():
            suivi.marquer(ligne, "file_attente_le", maintenant, CODE)
            print(f"   . {ligne['prenom']} {ligne['nom']} -> file d'attente")
lignes = suivi.lire_lignes_de(CODE)
occupees = len([l for l in lignes
                if "recontact" not in l["demande"].lower()
                and not l["annule_le"] and not l["annulation_demandee_le"]
                and suivi.calculer_statut(l) != "File d'attente"])
if occupees >= maxi and statut_session != "cloturee":
    print("\n" + "=" * 58)
    print(f"  SESSION COMPLETE : {occupees}/{maxi} places occupees.")
    print("  Tu peux cloturer les inscriptions depuis l'interface,")
    print("  bouton Cloturer les inscriptions.")
    print("=" * 58)
