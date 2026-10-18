// LE JAVASCRIPT COMMUN DE DFM — sorti des pages le 18/10/2026.
//
// POURQUOI CE FICHIER EXISTE. Il etait ecrit DANS base.html : 23 Ko recopies
// dans chaque page, retelecharges et recompiles a chaque clic, sans jamais
// pouvoir etre gardes. Ici, une fois, puis garde un an.
//
// IL EST CHARGE PLUS TOT QU'AVANT, et c'est sans danger : le contenu des
// pages s'insere APRES (base.html, « block corps »), donc une page qui
// appelait une de ces fonctions la trouve toujours — et en trouve meme
// davantage qu'avant, puisque tout est defini avant elle.
//
// L'ORDRE DES BLOCS EST CELUI DE base.html.
// --- bloc 1 ---

function tkDuree(m){
  if(m < 60) return "il y a " + m + " min";
  var h = Math.floor(m / 60);
  if(h < 24) return "il y a " + h + " h";
  return "il y a " + Math.floor(h / 24) + " jour(s)";
}
function tkCharger(){
  fetch("/taches").then(function(r){return r.json()}).then(function(j){
    var z = document.getElementById("dfm_taches");
    if(!z || !j.ok || !j.taches || !j.taches.length){ if(z) z.innerHTML = ""; return; }
    var h = '<div class="tk-boite">';
    j.taches.forEach(function(t){
      h += '<div class="tk ' + (t.urgence === "haute" ? "" : "moyenne") + '">';
      h += '<div class="tk-ic"><i class="ti ti-bell-ringing"></i></div>';
      h += '<div class="tk-x"><div class="tk-t">À envoyer : ' + t.titre + '</div>';
      h += '<div class="tk-d">' + t.detail + ' · ' + tkDuree(t.retard) + (t.auto ? " · envoi automatique activé" : "") + '</div></div>';
      h += '<a class="tk-b" href="' + t.lien + '">Ouvrir la session</a></div>';
    });
    h += '</div>';
    z.innerHTML = h;
  }).catch(function(){});
}
tkCharger();
setInterval(tkCharger, 120000);
function tkReleve(){
  var p = window.location.pathname;
  var interesse = (p === "/" || p.indexOf("/questionnaires") === 0 || p.indexOf("/session/") === 0);
  if(!interesse) return;
  fetch("/questionnaires/relever-tout", {method: "POST"})
  .then(function(r){return r.json()}).then(function(j){
    if(j && j.traites > 0 && (p === "/" || p.indexOf("/questionnaires") === 0)){
      window.location.reload();
    }
  }).catch(function(){});
}
tkReleve();

// --- bloc 2 ---

var SY_RAPPORT = null;
function syCharger(){
  fetch("/synchro/etat").then(function(r){return r.json()}).then(function(j){
    if(!j.ok || j.jamais || !j.rapport || j.rapport.ok){ return; }
    SY_RAPPORT = j.rapport;
    var e = j.rapport.echec || {};
    var etapes = j.rapport.etapes || [];
    // UN ECHEC N'EST PLUS UN ABANDON. Depuis que des etapes sont non bloquantes,
    // une etape peut echouer sans que la suite s'arrete ; le bandeau annoncait
    // pourtant « les etapes suivantes n'ont pas ete executees » dans tous les
    // cas. Il faut COMPTER, pas supposer — une alarme qui se trompe sur ce
    // qu'elle annonce cesse d'etre lue, et c'est la seule chose qu'on ne peut
    // pas se permettre d'une alarme.
    var abandonnees = etapes.filter(function(x){ return !x.executee; }).length;
    var ratees = etapes.filter(function(x){ return !x.ok; }).length;
    var titre, detail;
    if(abandonnees > 0){
      titre = "Le traitement s'est interrompu à l'étape " + (e.numero || "?")
            + " : " + (e.titre || "");
      detail = abandonnees + " étape(s) n'ont pas été exécutées — conventions, "
             + "confirmations et factures peuvent être en retard.";
    } else {
      titre = ratees + " étape(s) ont échoué, le traitement a continué";
      detail = "Rien n'a été abandonné. Ce qui a échoué sera repris au prochain passage.";
    }
    // NOMMER LA CAUSE QUAND ELLE EST UNIQUE. Treize echecs qui n'en font qu'un
    // — une autorisation morte — se lisaient « 13 étapes ont échoué » : un
    // compte, la ou il fallait un geste. On regarde si tout retombe sur la meme
    // cause, et si oui on la dit, avec ce qu'il y a a faire.
    var cause = syCauseCommune(etapes);
    if(cause){
      // QUAND DES ETAPES ONT ETE ABANDONNEES, LE TITRE RESTE L'ABANDON. La
      // cause est utile, l'abandon est grave : la cause descend dans le detail
      // plutot que de prendre la place du seul fait qui presse.
      if(abandonnees > 0){ detail = cause.detail + " " + detail; }
      else { titre = cause.titre; detail = cause.detail + " " + detail; }
    }
    document.getElementById("sy_titre").textContent = titre;
    document.getElementById("sy_detail").textContent =
      detail + " Dernier essai le " + (j.rapport.quand || "") + ".";
    // Un echec sans abandon se signale en orange : le rouge dit ce qui n'a pas
    // eu lieu, et il perd son sens s'il sert aussi a ce qui a eu lieu.
    document.getElementById("sy_bandeau").classList.toggle("attention", abandonnees === 0);
    document.getElementById("sy_bandeau").classList.add("on");
  }).catch(function(){});
}
function syCauseCommune(etapes){
  var ratees = etapes.filter(function(x){ return !x.ok; });
  if(ratees.length < 2){ return null; }
  var google = ratees.filter(function(x){
    var c = (x.cause || "") + " " + (x.details || "");
    return /utorisation Google|invalid_grant|revoqu|révoqu/i.test(c);
  }).length;
  if(google === ratees.length){
    return {titre: "L'autorisation Google est expirée — " + ratees.length
                 + " étape(s) en dépendent",
            detail: "Pour la renouveler : fermez DFM, puis double-cliquez DFM.command. "
                  + "Une page de connexion Google s'ouvre une fois."};
  }
  // Toute autre cause partagee mot pour mot par TOUS les echecs.
  var premiere = (ratees[0].cause || "").trim();
  if(premiere && ratees.every(function(x){ return (x.cause || "").trim() === premiere; })){
    return {titre: ratees.length + " étape(s) ont échoué, toutes pour la même raison",
            detail: premiere};
  }
  return null;
}
function syMasquer(){ document.getElementById("sy_bandeau").classList.remove("on"); }
function syDetails(){
  if(!SY_RAPPORT){ return; }
  var e = SY_RAPPORT.echec || {};
  // RIEN D'INTERROMPU N'EST PAS « INTERROMPU » — 07/10/2026. Le bandeau comptait
  // deja les etapes abandonnees avant de parler d'interruption ; cette fenetre,
  // elle, affichait « Traitement interrompu » en rouge pour TOUT echec, y compris
  // celui d'une etape NON BLOQUANTE apres laquelle les quatre-vingt-dix autres
  // s'etaient deroulees. Un import de formulaire qui tombe et un traitement
  // reellement arrete ne demandent pas la meme reaction : leur donner le meme
  // titre noie le vrai arret dans les faux, et une alarme qu'on cesse de lire ne
  // sert plus a rien. Meme regle que le bandeau, meme vocabulaire.
  var restantes = (SY_RAPPORT.etapes || []).filter(function(x){ return !x.executee; }).length;
  var arrete = restantes > 0 ||
    (SY_RAPPORT.etapes || []).some(function(x){ return x.ok === false && x.bloquant; });
  var h = '<div class="dfm-bloc dfm-b-' + (arrete ? "dan" : "att") + '"><b>' + (e.titre || "") + '</b><br>' + (e.cause || "Cause inconnue") + '</div>';
  h += '<div class="dfm-liste">';
  (SY_RAPPORT.etapes || []).forEach(function(x){
    var ok = x.ok;
    h += '<div class="dfm-liste-l"><i class="ti ' + (ok ? "ti-circle-check" : "ti-alert-circle")
       + '" style="color:' + (ok ? "var(--success)" : "var(--danger)") + '"></i><span>' + x.titre;
    if(x.resume && x.resume.length){
      h += '<br><span style="font-size:11px;color:var(--muted)">' + x.resume.join(" · ") + '</span>';
    }
    h += '</span></div>';
  });
  h += '</div>';
  if(restantes > 0){
    h += '<div class="dfm-bloc dfm-b-att">' + restantes + ' étape(s) n\'ont pas été exécutées.</div>';
  } else {
    h += '<div class="dfm-bloc dfm-b-ok">Rien n\'a été abandonné : toutes les autres étapes '
       + 'se sont déroulées. Ce qui a échoué sera repris au prochain passage.</div>';
  }
  dfmFenetre({ton: arrete ? "danger" : "attention",
    titre: arrete ? "Traitement interrompu" : "Traitement terminé, avec un avertissement",
    sous: "Dernier essai le " + (SY_RAPPORT.quand || ""), corps: h,
    boutons: [{libelle: "Fermer", style: "neutre"},
              {libelle: "Relancer", style: arrete ? "danger" : "neutre", icone: "ti-refresh",
               action: function(){ syRelancer(null); }}]});
}
function syRelancer(bouton){
  if(bouton){ bouton.disabled = true; bouton.textContent = "En cours…"; }
  dfmFenetre({ton: "info", titre: "Traitement en cours",
    corps: "<p>Les douze étapes s'exécutent. Cela peut prendre une minute.</p>", boutons: []});
  fetch("/synchro/relancer", {method: "POST"})
  .then(function(r){return r.json()}).then(function(j){
    var rap = j.rapport || {};
    if(rap.ok){
      dfmFenetre({ton: "succes", titre: "Traitement terminé",
        corps: '<div class="dfm-bloc dfm-b-ok">Les douze étapes se sont déroulées sans erreur.</div>',
        boutons: [{libelle: "Fermer", style: "primaire",
                   action: function(){ window.location.reload(); }}]});
      return;
    }
    SY_RAPPORT = rap;
    syDetails();
  }).catch(function(e){
    dfmInfo("Erreur", "<p>" + e + "</p>", "danger");
  });
}
setTimeout(syCharger, 700);
function miCharger(){
  fetch("/miroir/etat").then(function(r){return r.json()}).then(function(j){
    if(!j.ok || !j.a_signaler){ return; }
    var n = j.attente || 0, bl = j.bloquees || 0;
    document.getElementById("mi_titre").textContent =
      "Le classeur Google est en retard de " + n + " écriture" + (n > 1 ? "s" : "");
    var d = "Rien n'est perdu : tout est enregistré dans DFM, c'est la recopie vers "
          + "le classeur qui attend.";
    if(bl){
      d += " " + bl + " n'y arrive" + (bl > 1 ? "nt" : "") + " pas";
      if(j.souci && j.souci.souci){ d += " — " + j.souci.souci; }
      d += ".";
    } else if(j.retard_minutes){
      d += " La plus ancienne attend depuis " + j.retard_minutes + " minute"
         + (j.retard_minutes > 1 ? "s" : "") + ".";
    }
    document.getElementById("mi_detail").textContent = d;
    document.getElementById("mi_bandeau").classList.add("on");
  }).catch(function(){});
}
function miMasquer(){ document.getElementById("mi_bandeau").classList.remove("on"); }
function miRattraper(bouton){
  var t = bouton.textContent;
  bouton.disabled = true;
  bouton.textContent = "Versement...";
  fetch("/miroir/rattraper", {method:"POST", headers:{"X-Requested-With":"fetch"}})
  .then(function(r){ return r.json(); })
  .then(function(j){
    bouton.disabled = false;
    bouton.textContent = t;
    document.getElementById("mi_detail").textContent = j.message || "";
    if(j.ok){ setTimeout(miMasquer, 2500); }
  })
  .catch(function(){
    bouton.disabled = false;
    bouton.textContent = t;
    document.getElementById("mi_detail").textContent = "DFM n'a pas répondu.";
  });
}
setTimeout(miCharger, 900);
/* ------------------------------------------------------------------
   Brouillons — module commun aux ecrans de saisie longue.

   Deux signaux, et un brouillon n'est retenu que si les DEUX concordent :
     1. un evenement input/change a eu lieu (une consultation n'en produit
        aucun : une affectation .value en JS ne declenche rien) ;
     2. l'empreinte de l'etat differe de celle prise au demarrage.
   Le second seul produirait un faux positif a chaque remplissage
   asynchrone ; le premier seul en produirait un si l'on tape puis efface.

   Stockage : localStorage. Le serveur ne voit jamais un brouillon — c'est
   ce qui rend impossible de le confondre avec un enregistrement reel.
   ------------------------------------------------------------------ */
var dfmBrouillon = (function(){
  var CLE = null, SERIALISER = null, RESTAURER = null;
  var REF = null, TOUCHE = false, ARME = false, IGNORER = false;
  var JOURS = 7;

  function _cle(){ return "dfm_brouillon:" + CLE; }
  function _etat(){
    try{ return JSON.stringify(SERIALISER()); }catch(e){ return null; }
  }
  function modifie(){
    if(!ARME || IGNORER || !TOUCHE) return false;
    var e = _etat();
    return e !== null && e !== REF;
  }
  function armer(){
    REF = _etat(); TOUCHE = false; ARME = true;
  }
  function ecrire(){
    if(!modifie()) return false;
    try{
      localStorage.setItem(_cle(), JSON.stringify({quand: Date.now(), etat: _etat()}));
      return true;
    }catch(e){ return false; }
  }
  function effacer(){ try{ localStorage.removeItem(_cle()); }catch(e){} }
  function lire(){
    try{
      var b = localStorage.getItem(_cle());
      if(!b) return null;
      var d = JSON.parse(b);
      if(!d || !d.etat) return null;
      if(Date.now() - (d.quand || 0) > JOURS * 86400000){ effacer(); return null; }
      return d;
    }catch(e){ return null; }
  }
  function _quandTexte(t){
    var d = new Date(t), n = new Date();
    var h = (" " + d.getHours()).slice(-2) + "h" + ("0" + d.getMinutes()).slice(-2);
    if(d.toDateString() === n.toDateString()) return "aujourd'hui à " + h.trim();
    return "le " + d.getDate() + "/" + (d.getMonth() + 1) + " à " + h.trim();
  }
  function _bandeau(d){
    var z = document.createElement("div");
    z.className = "br-bandeau";
    z.innerHTML = '<i class="ti ti-file-pencil"></i>'
      + '<span>Un brouillon non enregistré vous attend, sauvegardé <b>'
      + _quandTexte(d.quand) + '</b>.</span>'
      + '<button type="button" class="br-b br-repr">Le reprendre</button>'
      + '<button type="button" class="br-b br-ecart">L\'écarter</button>';
    var zone = document.getElementById("dfm_brouillon_zone");
    if(zone){ zone.appendChild(z); }
    else { document.body.insertBefore(z, document.body.firstChild); }
    z.querySelector(".br-repr").onclick = function(){
      try{ RESTAURER(JSON.parse(d.etat)); }catch(e){}
      effacer(); z.remove(); TOUCHE = true;
    };
    z.querySelector(".br-ecart").onclick = function(){ effacer(); z.remove(); };
  }
  function _sortie(cible){
    // dfmFenetre et non dfmConfirmer : ce dernier impose ses deux boutons,
    // or il en faut trois — conserver, ecarter, rester.
    dfmFenetre({
      ton: "attention", titre: "Modifications non enregistrées",
      sous: "Vous quittez cette page sans avoir enregistré",
      corps: "<p>Votre travail peut être conservé en brouillon. Vous le retrouverez "
           + "en revenant sur cet écran, avec le choix de le reprendre ou de l'écarter.</p>"
           + "<p style=\"color:var(--muted);font-size:12px\">Un brouillon n'est pas un "
           + "enregistrement : il ne paraît ni dans la bibliothèque, ni dans le catalogue.</p>",
      boutons: [
        {libelle: "Rester sur la page", style: "neutre"},
        {libelle: "Écarter et quitter", style: "attention",
         action: function(){ effacer(); IGNORER = true; window.location = cible; }},
        {libelle: "Conserver en brouillon", style: "primaire", icone: "ti-file-pencil",
         action: function(){ ecrire(); IGNORER = true; window.location = cible; }}
      ]
    });
  }
  function installer(opt){
    CLE = opt.cle; SERIALISER = opt.serialiser; RESTAURER = opt.restaurer;
    document.addEventListener("input", function(){ TOUCHE = true; }, true);
    document.addEventListener("change", function(){ TOUCHE = true; }, true);
    document.addEventListener("click", function(e){
      var a = e.target.closest ? e.target.closest("a[href]") : null;
      if(!a) return;
      var h = a.getAttribute("href") || "";
      if(!h || h.charAt(0) === "#" || a.target === "_blank") return;
      if(/^(mailto:|tel:|javascript:)/.test(h)) return;
      if(!modifie()) return;
      e.preventDefault(); e.stopPropagation();
      _sortie(a.href);
    }, true);
    // Fermeture d'onglet, bouton retour, barre d'adresse : on ne peut pas
    // afficher de dialogue. On ecrit le brouillon en silence, et le navigateur
    // pose sa question generique. Rien n'est perdu, meme en repondant quitter.
    window.addEventListener("beforeunload", function(e){
      if(!modifie()) return;
      ecrire();
      e.preventDefault(); e.returnValue = "";
      return "";
    });
    var d = lire();
    if(d) _bandeau(d);
  }
  return {installer: installer, armer: armer, modifie: modifie,
          enregistre: function(){ effacer(); armer(); },
          // TERMINER, ET NON ENREGISTRER — 15/10/2026. Apres une creation
          // reussie il n'y a plus rien a conserver : on efface le brouillon ET
          // on desarme. « enregistre » re-armait, si bien qu'un clic dans un
          // champ apres coup rappelait « Modifications non enregistrees » —
          // titre qui, juste apres une creation, laisse croire que rien n'a
          // ete sauve. C'est exactement ce qui s'est produit.
          terminer: function(){ effacer(); IGNORER = true; },
          ecarter: effacer};
})();


// --- bloc 3 ---

async function lancer(btn){
  const c = document.getElementById("console");
  const avant = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader-2"></i>Traitement…';
  c.style.display = "block";
  c.textContent = "Traitement en cours…";
  try{
    const r = await fetch("/lancer", {method:"POST"});
    const d = await r.json();
    c.textContent = d.sortie.join("\n");
  }catch(e){ c.textContent = "Erreur : " + e.message; }
  btn.disabled = false;
  btn.innerHTML = avant;
}

// --- bloc 4 ---

function dfmInfobulles(){
  var el = document.querySelectorAll("[title]");
  for(var i = 0; i < el.length; i++){
    var t = (el[i].getAttribute("title") || "").trim();
    if(!t) continue;
    el[i].setAttribute("data-tip", t);
    el[i].removeAttribute("title");
  }
}
// LA PAGE DOIT EXISTER. Cet appel etait ecrit au milieu du corps, donc
// apres le contenu ; le fichier commun etant charge plus tot, il faut le
// dire explicitement. Les deux declencheurs ci-dessous ne changent pas.
document.addEventListener("DOMContentLoaded", dfmInfobulles);
document.addEventListener("click", function(){ setTimeout(dfmInfobulles, 400); });
setInterval(dfmInfobulles, 2500);

// --- bloc 5 ---

var DFM_ICONES = {info: "ti-info-circle", succes: "ti-circle-check",
                  attention: "ti-alert-triangle", danger: "ti-alert-octagon"};
function dfmFermer(){
  document.getElementById("dfm_voile").style.display = "none";
  document.getElementById("dfm_modale").innerHTML = "";
}
function dfmFenetre(o){
  var ton = o.ton || "info";
  var h = '<div class="dfm-tete"><div class="dfm-ic ' + ton + '"><i class="ti ' + (o.icone || DFM_ICONES[ton]) + '"></i></div>';
  h += '<div class="dfm-tx"><div class="dfm-t">' + (o.titre || "") + '</div>';
  if(o.sous){ h += '<div class="dfm-st">' + o.sous + '</div>'; }
  h += '</div></div><div class="dfm-corps">' + (o.corps || "") + '</div>';
  h += '<div class="dfm-pied">';
  (o.boutons || []).forEach(function(b, i){
    var style = b.style || "neutre";
    h += '<button class="dfm-btn dfm-btn-' + style + '" id="dfm_b' + i + '"' + (b.desactive ? " disabled" : "") + '>';
    if(b.icone){ h += '<i class="ti ' + b.icone + '"></i>'; }
    h += (b.libelle || "OK") + '</button>';
  });
  h += '</div>';
  document.getElementById("dfm_modale").innerHTML = h;
  document.getElementById("dfm_voile").style.display = "flex";
  (o.boutons || []).forEach(function(b, i){
    var el = document.getElementById("dfm_b" + i);
    if(!el) return;
    // « garder » se lit SUR LE BOUTON, et aussi SUR LA FENETRE — mais au niveau
    // de la fenetre il ne vaut que pour les boutons QUI AGISSENT. Un bouton sans
    // action est un bouton de fermeture : il doit fermer, toujours.
    //
    // POURQUOI CETTE SOUPLESSE. Constate le 20/08/2026. Quatre appels passaient
    // « garder » au niveau de la fenetre, ou personne ne le lisait : dfmFermer()
    // vidait la fenetre AVANT l'action, les champs saisis disparaissaient du
    // DOM, l'action lisait du vide, puis ressortait en silence sur son propre
    // controle « si la date est absente ». « Enregistrer le reglement »
    // n'enregistrait rien ET n'affichait aucune erreur — la pire des pannes,
    // celle qui ressemble a un clic qui n'a pas pris.
    var garder = (b.garder === true)
              || (o.garder === true && typeof b.action === "function");
    el.onclick = function(){
      if(!garder){ dfmFermer(); }
      if(typeof b.action === "function"){ b.action(el); }
    };
  });
  if(o.apres){ o.apres(); }
}
function dfmInfo(titre, corps, ton){
  dfmFenetre({ton: ton || "info", titre: titre, corps: corps,
              boutons: [{libelle: "Fermer", style: "primaire"}]});
}
function dfmConfirmer(o){
  dfmFenetre({ton: o.ton || "attention", titre: o.titre, sous: o.sous, corps: o.corps,
    boutons: [{libelle: o.annuler || "Annuler", style: "neutre"},
              {libelle: o.valider || "Confirmer", style: o.styleValider || "attention",
               icone: o.iconeValider, action: o.action}]});
}
function dfmRisque(o){
  var corps = (o.corps || "");
  corps += '<div class="dfm-bloc dfm-b-dan"><b>Pour confirmer, recopiez exactement :</b> <code style="font-size:13px">' + o.motCle + '</code>';
  corps += '<input type="text" class="dfm-saisie" id="dfm_cle" autocomplete="off" spellcheck="false" placeholder="' + o.motCle + '"></div>';
  dfmFenetre({ton: "danger", titre: o.titre, sous: o.sous, corps: corps,
    boutons: [{libelle: "Annuler", style: "neutre"},
              {libelle: o.valider || "Confirmer", style: "danger", icone: o.iconeValider,
               desactive: true, action: o.action}],
    apres: function(){
      var champ = document.getElementById("dfm_cle");
      var bouton = document.getElementById("dfm_b1");
      if(!champ || !bouton) return;
      champ.focus();
      champ.addEventListener("input", function(){
        bouton.disabled = (champ.value.trim() !== o.motCle);
      });
    }});
}
function dfmEtapes(titre, sous, etapes, resume, ton){
  var corps = "";
  if(resume){ corps += '<div class="dfm-bloc dfm-b-' + (ton === "danger" ? "dan" : (ton === "attention" ? "att" : "ok")) + '">' + resume + '</div>'; }
  if(etapes && etapes.length){
    corps += '<div class="dfm-liste">';
    etapes.forEach(function(e){
      var ok = (e.ok !== false);
      corps += '<div class="dfm-liste-l"><i class="ti ' + (ok ? "ti-circle-check" : "ti-alert-circle") + '" style="color:' + (ok ? "var(--success)" : "var(--warn)") + '"></i><span>' + (e.texte || e) + '</span></div>';
    });
    corps += '</div>';
  }
  dfmFenetre({ton: ton || "succes", titre: titre, sous: sous, corps: corps,
              boutons: [{libelle: "Fermer", style: "primaire"}]});
}
document.addEventListener("click", function(e){ if(e.target && e.target.id === "dfm_voile") dfmFermer(); });
document.addEventListener("keydown", function(e){ if(e.key === "Escape") dfmFermer(); });

// --- bloc 6 ---

(function(){
  var natif = window.alert;
  window.alert = function(message){
    if(typeof dfmFenetre !== "function"){ return natif(message); }
    var texte = String(message === null || message === undefined ? "" : message);
    var ton = "info", titre = "Information";
    if(/erreur|impossible|échec|echec|non envoy/i.test(texte)){ ton = "danger"; titre = "Erreur"; }
    else if(/attention|manque|obligatoire|d'abord|deja|déjà/i.test(texte)){ ton = "attention"; titre = "Attention"; }
    else if(/envoy|enregistr|alignée|alignee|traitée|traitee|copié|copie/i.test(texte)){ ton = "succes"; titre = "C'est fait"; }
    var brutes = texte.split("\n");
    var lignes = [];
    for(var i = 0; i < brutes.length; i++){
      if(brutes[i].trim()){ lignes.push(brutes[i]); }
    }
    var corps = "";
    if(lignes.length > 2){
      var premiere = lignes.shift();
      corps = '<div class="dfm-bloc dfm-b-neutre">' + premiere + '</div><div class="dfm-liste">';
      for(var j = 0; j < lignes.length; j++){
        var l = lignes[j].trim();
        var ok = !/^(--|KO|ERREUR)/i.test(l);
        var propre = l.replace(/^(OK|--)\s+/i, "");
        corps += '<div class="dfm-liste-l"><i class="ti ' + (ok ? "ti-circle-check" : "ti-alert-circle")
               + '" style="color:' + (ok ? "var(--success)" : "var(--warn)") + '"></i><span>' + propre + '</span></div>';
      }
      corps += '</div>';
    } else {
      corps = '<p>' + texte.replace(/\n/g, "<br>") + '</p>';
    }
    dfmFenetre({ton: ton, titre: titre, corps: corps,
                boutons: [{libelle: "Fermer", style: "primaire"}]});
  };
})();
