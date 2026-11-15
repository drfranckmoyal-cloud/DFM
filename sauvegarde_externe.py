# -*- coding: utf-8 -*-
"""La copie CHIFFREE de la sauvegarde du soir, hors du serveur — 15/11/2026.

POURQUOI. Les sauvegardes de DFM vivaient sur le serveur qu'elles protegent :
un disque perdu, une machine supprimee par erreur, et les conventions signees,
les factures et le journal scelle disparaissaient avec leurs copies. Pour un
organisme, perdre ses conventions signees, c'est perdre sa certification
(CHANTIER-SAAS, 3.2). Franck a donne son accord le 15/11/2026.

CE QUE FAIT CE MODULE, chaque soir apres l'archive de 19h30 :
    1. il CHIFFRE l'archive (openssl, AES-256, phrase de 44 caracteres) ;
    2. il l'ENVOIE dans un espace de stockage objet chez Scaleway, a Paris ;
    3. il verifie que la taille recue est la bonne ;
    4. il RETIRE les copies de plus de 30 jours ;
    5. le dimanche, il en RAPATRIE une, la dechiffre et verifie qu'elle
       s'ouvre : une sauvegarde jamais restauree n'est pas une sauvegarde.
En cas d'echec, un mail part a l'adresse de contact (alerte.prevenir).

AUCUNE DEPENDANCE NOUVELLE. curl sait signer une requete S3 (--aws-sigv4) et
openssl sait chiffrer : les deux sont deja sur le serveur.

LES SECRETS restent dans « stockage_externe.json » (droits 600), jamais dans
le depot ni dans le miroir du Mac. La phrase de chiffrement est AUSSI rangee
dans le trousseau du Mac par le lanceur « 8 — Configurer la sauvegarde
externe » : sans elle, une copie est illisible, y compris pour nous.

RESTAURER A LA MAIN, depuis n'importe quelle machine :
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
        -in DFM-local-AAAA-MM-JJ-HHMM.zip.enc -out DFM.zip -pass pass:'<phrase>'
puis ouvrir DFM.zip.

NE TOURNE AUTOMATIQUEMENT QUE SUR LE SERVEUR (DFM_PROXY=1) : le Mac fait aussi
son archive du soir, et l'enverrait en double.
"""
import datetime as dt
import glob
import io
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

DOSSIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(DOSSIER, "stockage_externe.json")
ETAT = os.path.join(DOSSIER, "etat_sauvegarde_externe.json")
PREFIXE = "dfm/"
GARDER_JOURS = 30
ITERATIONS = "200000"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


class Souci(Exception):
    pass


def serveur():
    return (os.environ.get("DFM_PROXY") or "").strip().lower() in ("1", "oui", "true")


def config():
    """La configuration, ou None si elle manque ou est incomplete."""
    try:
        c = json.load(io.open(CONFIG, encoding="utf-8"))
    except Exception:
        return None
    if not all(str(c.get(k) or "").strip() for k in ("bucket", "cle_acces", "cle_secrete", "phrase")):
        return None
    c.setdefault("region", "fr-par")
    c.setdefault("point", "https://s3.%s.scw.cloud" % c["region"])
    c.setdefault("garder_jours", GARDER_JOURS)
    return c


def configuree():
    return config() is not None


def etat():
    try:
        return json.load(io.open(ETAT, encoding="utf-8"))
    except Exception:
        return {}


def _noter(**valeurs):
    e = etat()
    e.update(valeurs)
    try:
        import fichiers
        fichiers.ecrire(ETAT, e)
    except Exception:
        io.open(ETAT, "w", encoding="utf-8").write(json.dumps(e, ensure_ascii=False, indent=1))


def _fichier_secret(contenu):
    """Un fichier temporaire lisible du seul proprietaire. Les secrets passent
    par lui, jamais par la ligne de commande : « ps » la montre a tous."""
    fd, chemin = tempfile.mkstemp(prefix="dfm-se-")
    os.chmod(chemin, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(contenu)
    return chemin


def _curl(c, methode, cle="", entree=None, sortie=None, requete="", tete=False):
    """Une requete S3 signee. Rend le texte de la reponse (vide si `sortie`)."""
    url = "%s/%s/%s%s" % (c["point"].rstrip("/"), c["bucket"], cle, ("?" + requete) if requete else "")
    k = _fichier_secret('user = "%s:%s"\n' % (c["cle_acces"].strip(), c["cle_secrete"].strip()))
    try:
        cmd = ["curl", "--fail-with-body", "-sS", "--max-time", "1200",
               "--aws-sigv4", "aws:amz:%s:s3" % c["region"], "-K", k]
        if tete:
            cmd.append("--head")
        else:
            cmd += ["-X", methode]
        if entree:
            cmd += ["-T", entree]
        if sortie:
            cmd += ["-o", sortie]
        cmd.append(url)
        r = subprocess.run(cmd, capture_output=True)
        texte = r.stdout.decode("utf-8", "replace")
        if r.returncode != 0:
            msg = (r.stderr.decode("utf-8", "replace") + " " + texte).strip()
            raise Souci("stockage injoignable ou refus (%s) : %s" % (methode, msg[:300]))
        return texte
    finally:
        os.remove(k)


def _openssl(c, sens, src, dst):
    p = _fichier_secret(c["phrase"])
    try:
        cmd = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", ITERATIONS, "-salt",
               "-in", src, "-out", dst, "-pass", "file:" + p]
        if sens == "dechiffrer":
            cmd.insert(2, "-d")
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            raise Souci("openssl (%s) : %s" % (sens, r.stderr.decode("utf-8", "replace")[:200]))
    finally:
        os.remove(p)


def derniere_archive():
    l = sorted(glob.glob(os.path.join(DOSSIER, ".sauvegardes", "DFM-local-*.zip")))
    return l[-1] if l else None


def envoyer(archive=None):
    """Chiffre et envoie une archive. Rend un compte rendu, ou None si rien
    n'est configure. Leve Souci en cas d'echec."""
    c = config()
    if not c:
        return None
    archive = archive or derniere_archive()
    if not archive or not os.path.exists(archive):
        raise Souci("aucune archive locale a envoyer")
    chiffree = archive + ".enc"
    try:
        _openssl(c, "chiffrer", archive, chiffree)
        taille = os.path.getsize(chiffree)
        cle = PREFIXE + os.path.basename(chiffree)
        _curl(c, "PUT", cle, entree=chiffree)
        tete = _curl(c, "HEAD", cle, tete=True)
        recu = next((int(l.split(":", 1)[1]) for l in tete.splitlines()
                     if l.lower().startswith("content-length:")), -1)
        if recu != taille:
            raise Souci("taille recue %s au lieu de %s" % (recu, taille))
    finally:
        if os.path.exists(chiffree):
            os.remove(chiffree)
    maintenant = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    _noter(dernier_envoi=maintenant, derniere_cle=cle, derniere_taille=taille, dernier_souci="")
    return {"cle": cle, "taille": taille, "le": maintenant}


def lister(c=None):
    """Les copies presentes, de la plus ancienne a la plus recente : (cle, date, taille)."""
    c = c or config()
    if not c:
        return []
    sortie, jeton = [], ""
    while True:
        req = "list-type=2&prefix=" + PREFIXE + (("&continuation-token=" + jeton) if jeton else "")
        racine = ET.fromstring(_curl(c, "GET", "", requete=req))
        for o in racine.findall(NS + "Contents"):
            cle = o.findtext(NS + "Key") or ""
            quand = (o.findtext(NS + "LastModified") or "")[:19]
            try:
                d = dt.datetime.strptime(quand, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                d = None
            sortie.append((cle, d, int(o.findtext(NS + "Size") or 0)))
        if (racine.findtext(NS + "IsTruncated") or "").lower() != "true":
            break
        jeton = racine.findtext(NS + "NextContinuationToken") or ""
        if not jeton:
            break
    return sorted(sortie, key=lambda x: (x[1] or dt.datetime.min, x[0]))


def purger(maintenant=None):
    """Retire les copies de plus de `garder_jours`. Garde toujours la plus
    recente, meme ancienne : mieux vaut une vieille copie que rien."""
    c = config()
    if not c:
        return 0
    maintenant = maintenant or dt.datetime.utcnow()
    limite = maintenant - dt.timedelta(days=int(c.get("garder_jours") or GARDER_JOURS))
    copies = lister(c)
    n = 0
    for cle, d, _ in copies[:-1]:
        if d and d < limite:
            _curl(c, "DELETE", cle)
            n += 1
    return n


def essai_restauration():
    """Rapatrie la copie la plus recente, la dechiffre, verifie l'archive."""
    c = config()
    if not c:
        return None
    copies = lister(c)
    if not copies:
        raise Souci("aucune copie dans le stockage externe")
    cle = copies[-1][0]
    dossier = tempfile.mkdtemp(prefix="dfm-restauration-", dir=os.path.join(DOSSIER, ".sauvegardes")
                               if os.path.isdir(os.path.join(DOSSIER, ".sauvegardes")) else None)
    chiffree = os.path.join(dossier, "copie.zip.enc")
    claire = os.path.join(dossier, "copie.zip")
    try:
        _curl(c, "GET", cle, sortie=chiffree)
        _openssl(c, "dechiffrer", chiffree, claire)
        with zipfile.ZipFile(claire) as z:
            abime = z.testzip()
            noms = z.namelist()
        if abime:
            raise Souci("archive abimee : %s" % abime)
        base = any(n.endswith("dfm.db") for n in noms)
        docs = len([n for n in noms if n.startswith("documents/")])
        if not base:
            raise Souci("la base dfm.db manque dans la copie")
    finally:
        for f in (chiffree, claire):
            if os.path.exists(f):
                os.remove(f)
        try:
            os.rmdir(dossier)
        except OSError:
            pass
    maintenant = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    _noter(dernier_essai=maintenant, dernier_essai_cle=cle, dernier_essai_fichiers=len(noms))
    return {"cle": cle, "fichiers": len(noms), "documents": docs, "le": maintenant}


def passage_du_soir(archive, dimanche=None):
    """Appele par le planificateur apres l'archive locale. Rend des lignes de
    journal. Previent par mail en cas d'echec."""
    if not (serveur() and configuree()):
        return []
    lignes = []
    try:
        r = envoyer(archive)
        lignes.append("Copie externe envoyee : %s (%d Mo)." % (r["cle"], r["taille"] // 1048576))
        n = purger()
        if n:
            lignes.append("Copies externes de plus de %d jours retirees : %d." % (GARDER_JOURS, n))
        if dimanche if dimanche is not None else dt.date.today().weekday() == 6:
            t = essai_restauration()
            lignes.append("Essai de restauration reussi : %s, %d fichiers." % (t["cle"], t["fichiers"]))
        try:
            import alerte
            alerte.oublier("sauvegarde-externe")
        except Exception:
            pass
    except Exception as e:
        msg = str(e)[:300]
        _noter(dernier_souci="%s — %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M"), msg))
        lignes.append("Copie externe en echec : %s" % msg)
        try:
            import alerte
            alerte.prevenir("sauvegarde-externe", "DFM : la copie externe de la sauvegarde a échoué",
                            ["La sauvegarde du soir a bien été faite sur le serveur, mais sa copie "
                             "chiffrée n'a pas pu partir vers le stockage externe.",
                             "Motif : %s" % msg],
                            heures=24, signature="sauvegarde-externe",
                            quoi_faire="Rien d'urgent si cela ne dure pas : la copie repart chaque "
                                       "soir. Si le message revient plusieurs jours, demander à Claude "
                                       "de regarder la configuration du stockage.")
        except Exception:
            pass
    return lignes


if __name__ == "__main__":
    if "--etat" in sys.argv:
        print(json.dumps({"configuree": configuree(), **etat()}, ensure_ascii=False, indent=1))
        sys.exit(0)
    if "--essai" in sys.argv:
        if not configuree():
            print("La sauvegarde externe n'est pas configuree (stockage_externe.json manque ou est incomplet).")
            sys.exit(1)
        try:
            archive = derniere_archive()
            if not archive:
                import sauvegarde_locale as _sl
                archive, _ = _sl.fabriquer()
            r = envoyer(archive)
            print("Envoi : OK — %s (%d Mo)" % (r["cle"], r["taille"] // 1048576))
            t = essai_restauration()
            print("Restauration d'essai : OK — %d fichiers, dont %d documents, base comprise."
                  % (t["fichiers"], t["documents"]))
            print("Copies presentes : %d" % len(lister()))
        except Souci as e:
            print("ECHEC : %s" % e)
            sys.exit(2)
        sys.exit(0)
    print(__doc__)
