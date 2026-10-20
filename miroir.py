# -*- coding: utf-8 -*-
"""La copie vers le classeur Google, sortie du chemin du clic.

LE PROBLEME MESURE LE 18/10/2026. Un aller-retour vers Google coute entre
trois dixiemes et sept dixiemes de seconde, et pres de deux secondes au
premier appel. Or chaque enregistrement en faisait DEUX — le suivi, puis le
journal — et DFM les attendait avant de repondre. Tout clic qui enregistrait
quelque chose coutait donc de six dixiemes a une seconde et demie d'attente.
Les ecrans, eux, sortent en deux a huit centiemes : la lenteur etait entiere
dans cette attente.

ET ELLE N'ETAIT ATTENDUE POUR RIEN. La donnee est deja enregistree dans la
base locale, qui fait foi, AVANT que la copie ne commence — le code le disait
deja : « le miroir n'est pas une ecriture, c'est une copie ». On attendait la
fin d'une copie dont l'echec n'a jamais rien coute.

CE QUE FAIT CE MODULE. La copie est inscrite dans une file, dans la base, et
la reponse part aussitot. Un fil unique vide la file en arriere-plan.

TROIS CHOSES QUI COMPTENT, ET QUI ONT DICTE LA FORME :

- LA FILE EST DURABLE. En memoire seule, elle s'evaporerait au redemarrage et
  le classeur resterait en retard sans que personne le sache. Dans la base,
  elle survit au redemarrage, a la panne reseau et a la coupure de courant :
  au demarrage suivant, le fil la retrouve et la vide.

- L'ORDRE EST RESPECTE. Deux copies qui touchent la meme cellule doivent
  s'appliquer dans l'ordre decide, sinon l'ancienne ecrase la recente. Un seul
  fil, par id croissant, et une copie qui echoue ARRETE la passe au lieu
  d'etre sautee.

- RIEN N'EST ABANDONNE EN SILENCE. Avant ce module, une copie ratee affichait
  une ligne dans un journal technique que personne ne lit, et rien ne la
  rattrapait jamais. Desormais elle reste en file, et l'ecran le dit.
"""
import threading
import time
from datetime import datetime

import base

# Au-dela, une copie cesse de bloquer la file : elle y reste, mais les
# suivantes passent devant. Sans cela une copie impossible — un onglet
# supprime, par exemple — arreterait tout le classeur pour toujours.
ESSAIS_MAX = 10
# Un echec ne se retente pas dans la seconde : Google qui refuse refusera
# encore. Laisse aussi le temps a une panne reseau de se terminer.
REPOS_APRES_ECHEC = 30
# Le fil se reveille au depot, et de toute facon regulierement : c'est ce qui
# rattrape une file laissee par un script ou par le redemarrage.
RONDE = 60

_reveil = threading.Event()
_fil = None
_verrou_fil = threading.Lock()
# DEUX PASSES NE SE CHEVAUCHENT JAMAIS. Le fil de fond et le bouton
# « rattraper » peuvent tomber en meme temps : sans ce verrou, les deux
# liraient la meme tete de file et appliqueraient deux fois la meme copie —
# ou, pire, dans l'ordre inverse.
_verrou_passe = threading.Lock()
_dernier_echec = [0.0]


def deposer(organisme, feuille, donnees, quoi=""):
    """Met une copie en attente. NE PARLE PAS A GOOGLE : rend la main tout de
    suite, c'est tout l'objet du module."""
    if not feuille or not donnees:
        return 0
    try:
        ident = base.miroir_deposer(organisme, feuille, donnees, quoi)
    except Exception as e:
        # La file elle-meme est indisponible : on retombe sur l'ancien
        # comportement plutot que de perdre la copie — mieux vaut un clic lent
        # qu'un classeur muet.
        print("   (file des copies indisponible, copie immediate : %s)" % str(e)[:70])
        try:
            _executer(feuille, donnees)
        except Exception as e2:
            print("   (copie vers le classeur en retard : %s)" % str(e2)[:80])
        return 0
    demarrer()
    _reveil.set()
    return ident


def _executer(feuille, donnees):
    """L'appel a Google. Le seul endroit du module qui sort de la machine."""
    from connexion import service_sheets
    s = service_sheets()
    if not s:
        raise RuntimeError("pas de session Google")
    s.spreadsheets().values().batchUpdate(
        spreadsheetId=feuille,
        body={"valueInputOption": "USER_ENTERED", "data": donnees}).execute()


def _passe(limite=50):
    """Tente les copies en attente, dans l'ordre. Rend (faites, souci).

    S'ARRETE A LA PREMIERE QUI ECHOUE : la suivante pourrait toucher la meme
    cellule, et la passer avant reviendrait a appliquer les deux a l'envers.
    """
    faites, souci = 0, ""
    with _verrou_passe:
        for entree in base.miroir_prochaines(limite, ESSAIS_MAX):
            try:
                _executer(entree["feuille"], entree["donnees"])
            except Exception as e:
                souci = str(e)[:160]
                base.miroir_echec(entree["id"], souci)
                _dernier_echec[0] = time.time()
                break
            base.miroir_retirer(entree["id"])
            faites += 1
    return faites, souci


def rattraper(limite=500):
    """Vide la file ICI ET MAINTENANT, en attendant Google.

    C'est le bouton « rattraper le classeur » de l'ecran, et la derniere etape
    d'un script : sans elle, un script qui depose puis s'arrete laisserait sa
    copie attendre le prochain reveil du serveur.
    """
    total, souci = 0, ""
    while total < limite:
        faites, souci = _passe(min(50, limite - total))
        total += faites
        if faites == 0 or souci:
            break
    etat_ = base.miroir_etat(ESSAIS_MAX)
    return total, etat_.get("attente", 0), souci


# En dessous, le classeur n'est pas « en retard » : une copie vient de partir
# et le fil la traite. Un bandeau qui clignote a chaque clic ne serait pas une
# alerte, ce serait du bruit — et une alerte qu'on apprend a ignorer ne sert
# plus a rien.
RETARD_VISIBLE_MINUTES = 5


def etat():
    """Ou en est le classeur. Appele par l'ecran : doit rester instantane."""
    try:
        e = dict(base.miroir_etat(ESSAIS_MAX))
    except Exception as ex:
        return {"attente": 0, "bloquees": 0, "plus_vieille": "", "souci": {},
                "fil": False, "retard_minutes": 0, "a_signaler": False,
                "lisible": False, "pourquoi": str(ex)[:90]}
    e["fil"] = bool(_fil and _fil.is_alive())
    e["lisible"] = True
    e["retard_minutes"] = _age_minutes(e.get("plus_vieille"))
    # ON NE SIGNALE QUE CE QUI MERITE UN GESTE : une copie bloquee apres dix
    # essais, ou une file qui ne se vide plus depuis cinq minutes.
    e["a_signaler"] = bool(e.get("bloquees")
                           or e["retard_minutes"] >= RETARD_VISIBLE_MINUTES)
    return e


def _age_minutes(quand):
    """Depuis combien de minutes la plus vieille copie attend-elle ?"""
    s = str(quand or "").strip()
    if not s:
        return 0
    for forme in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            d = datetime.strptime(s, forme)
        except ValueError:
            continue
        return max(0, int((datetime.now() - d).total_seconds() // 60))
    return 0


def _boucle():
    while True:
        _reveil.wait(timeout=RONDE)
        _reveil.clear()
        if time.time() - _dernier_echec[0] < REPOS_APRES_ECHEC:
            continue
        try:
            _passe()
        except Exception as e:
            # Le fil ne meurt jamais : s'il mourait, la file ne se viderait
            # plus et personne ne le verrait avant longtemps.
            print("   (fil des copies : %s)" % str(e)[:90])
            time.sleep(5)
        # IL NE GARDE PAS SA CONNEXION ENTRE DEUX TOURS — 21/10/2026.
        #
        # Ce fil est le premier element de DFM a vivre des heures d'affilee, et
        # c'est lui qui a signale le premier « database disk image is malformed »
        # le 20/10 a 17h25. Avant lui, toutes les connexions de DFM etaient
        # courtes, le temps d'une page. Une connexion gardee des heures est
        # exposee a tout ce qui peut arriver au fichier pendant ce temps.
        #
        # Il la rend donc a chaque tour. La reouverture ne coute presque rien —
        # le schema n'est pose qu'une fois par processus — et elle borne
        # l'exposition a une minute au lieu d'une journee.
        try:
            base.fermer()
        except Exception:
            pass


def demarrer():
    """Lance le fil s'il ne tourne pas. Sans effet s'il tourne deja."""
    global _fil
    if _fil is not None and _fil.is_alive():
        return _fil
    with _verrou_fil:
        if _fil is not None and _fil.is_alive():
            return _fil
        _fil = threading.Thread(target=_boucle, name="miroir-classeur", daemon=True)
        _fil.start()
    return _fil
