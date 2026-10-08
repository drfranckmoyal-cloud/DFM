"""Le contexte de securite des appels HTTPS directs de DFM.

POURQUOI CE FICHIER EXISTE. Le Python livre par python.org arrive SANS AUCUNE
autorite de certification : `ssl.get_default_verify_paths()` y rend
`cafile: None, capath: None`. Tout appel HTTPS fait avec urllib echoue alors
sur « CERTIFICATE_VERIFY_FAILED », y compris vers Supabase.

Le Python d'Apple, lui, s'appuie sur le trousseau du systeme et n'a jamais eu
le probleme — d'ou un defaut qui n'apparait QUE depuis le lanceur, et pas en
ligne de commande. C'est ce qui l'a rendu si discret.

Google passait malgre tout : sa bibliotheque embarque ses propres certificats
et n'utilise pas le magasin du systeme. Seuls les appels directs tombaient, et
leurs appelants rattrapent l'erreur en silence — un ecran vide, aucun message.

La solution officielle est de lancer « Install Certificates.command » livre
avec Python. Personne ne le fait, et rien ne le rappelle. On ne compte donc pas
dessus : si le magasin est vide, on charge celui de certifi, deja present
puisque les bibliotheques Google en dependent.
"""
import ssl

_CONTEXTE = [None]


def contexte():
    """Un contexte SSL qui verifie vraiment, sur les deux Python."""
    if _CONTEXTE[0] is not None:
        return _CONTEXTE[0]
    ctx = ssl.create_default_context()
    try:
        vide = ctx.cert_store_stats().get("x509_ca", 0) == 0
    except Exception:
        vide = False
    if vide:
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            # On NE DESACTIVE PAS la verification. Mieux vaut un appel qui
            # echoue franchement qu'une connexion qui se croit sure : ce lien
            # transporte des donnees personnelles et une cle secrete.
            pass
    _CONTEXTE[0] = ctx
    return ctx


def diagnostic():
    """De quoi dire, en clair, d'ou vient un echec de certificat."""
    chemins = ssl.get_default_verify_paths()
    ctx = contexte()
    try:
        autorites = ctx.cert_store_stats().get("x509_ca", 0)
    except Exception:
        autorites = -1
    try:
        import certifi
        secours = certifi.where()
    except Exception:
        secours = ""
    return {"cafile_systeme": chemins.cafile, "capath_systeme": chemins.capath,
            "autorites_chargees": autorites, "secours_certifi": secours}
