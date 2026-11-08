const { createClient } = require("@supabase/supabase-js");

// LA CLE EST SECRETE (verifie le 17/08/2026 : « sb_secret_… » cote Netlify).
// Elle contourne les regles d'acces, ce qui permet de verrouiller entierement
// les tables : personne muni d'une cle publique ne peut lire une inscription.
// Toute verification doit donc etre faite ICI — la base ne protegera rien.
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

const reponse = (code, corps) => ({
  statusCode: code,
  headers: { "Content-Type": "application/json; charset=utf-8" },
  body: JSON.stringify(corps),
});

// Les champs recopies dans le suivi, et leur longueur admise. Un formulaire
// public recoit ce qu'on y met : sans borne, un seul envoi peut remplir la base.
const CHAMPS = {
  nom: 120, prenom: 120, mail: 200, telephone: 40, ville: 120,
  fonction: 80, demande: 200, connu_par: 120,
  dejeuner: 80, restrictions: 400, image: 200, pmr: 200,
};
const OBLIGATOIRES = ["nom", "prenom", "mail", "telephone", "ville", "fonction", "demande"];

function propre(v, max) {
  return String(v == null ? "" : v).replace(/\s+/g, " ").trim().slice(0, max);
}

// ------------------------------------------------------------------
// LES CODES PROMO — 08/11/2026. La liste est tenue par DFM (codes_promo.py) et
// recopiee dans « Codes_promo » ; cette fonction ne fait que la lire. Les
// regles de calcul sont LES MEMES que celles de DFM, a l'euro pres : la page
// annonce le prix que la convention ecrira.
// ------------------------------------------------------------------
function codePropre(v) {
  return String(v == null ? "" : v).replace(/\s+/g, "").toUpperCase().slice(0, 30);
}

function euros(v) {
  const n = parseFloat(String(v == null ? "" : v).replace(",", ".").replace(/[^0-9.]/g, ""));
  return isFinite(n) ? n : 0;
}

function aujourdhuiParis() {
  // « 2026-11-08 » : un code valable jusqu'au 30 l'est jusqu'a minuit a Paris.
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Paris" }).format(new Date());
}

async function jugerCode(of, codeSession, saisi, mail) {
  const code = codePropre(saisi);
  if (!code) return { ok: false, message: "Aucun code saisi." };
  const { data: sess, error: e1 } = await supabase
    .from("Sessions_inscription").select("code_session,tarif")
    .eq("code_session", codeSession).eq("organisme", of).limit(1);
  if (e1) return { ok: false, message: "Base indisponible.", panne: true };
  if (!sess || !sess.length) return { ok: false, message: "Formation inconnue." };
  const tarif = euros(sess[0].tarif);

  // LE CLOISONNEMENT, ENCORE : on ne cherche que parmi les codes de CET organisme.
  const { data: codes, error: e2 } = await supabase
    .from("Codes_promo").select("*").eq("organisme", of).eq("code", code).limit(1);
  if (e2) return { ok: false, message: "Base indisponible.", panne: true };
  const r = codes && codes[0];
  if (!r) return { ok: false, message: "Ce code n'existe pas." };
  if (!r.actif) return { ok: false, message: "Ce code n'est plus valable." };
  const visees = r.sessions || [];
  if (visees.length && visees.indexOf(codeSession) < 0) {
    return { ok: false, message: "Ce code ne s'applique pas à cette formation." };
  }
  if (r.jusqu_au && aujourdhuiParis() > String(r.jusqu_au).slice(0, 10)) {
    return { ok: false, message: "Ce code a expiré." };
  }
  const plafond = Number(r.max_utilisations || 0);
  if (plafond > 0) {
    // Un renvoi corrige du formulaire ne consomme pas une seconde utilisation.
    let q = supabase.from("Inscriptions").select("id", { count: "exact", head: true })
      .eq("organisme", of).eq("code_promo", code);
    if (mail) q = q.neq("mail", String(mail).toLowerCase());
    const { count, error: e3 } = await q;
    if (e3) return { ok: false, message: "Base indisponible.", panne: true };
    if ((count || 0) >= plafond) {
      return { ok: false, message: "Ce code a déjà été utilisé le nombre de fois prévu." };
    }
  }
  const v = Number(r.valeur || 0);
  // Au centime, comme Stripe et comme DFM (codes_promo.remise) : 10 % de 975 =
  // 97,50. Calcule en centimes pour echapper aux arrondis binaires.
  let remise = r.type === "pourcentage" ? Math.round(tarif * v) / 100 : v;
  remise = Math.max(0, Math.min(remise, tarif));
  // Une formation offerte passe par l'invitation, pas par un code.
  if (remise <= 0 || remise >= tarif) {
    return { ok: false, message: "Ce code ne s'applique pas à cette formation." };
  }
  return {
    ok: true, code, tarif, remise, prix: tarif - remise,
    libelle: r.type === "pourcentage" ? v + " %" : v + " €",
  };
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return reponse(405, { ok: false, message: "Methode non autorisee" });
  }
  // Un corps demesure est rejete avant meme d'etre analyse.
  if ((event.body || "").length > 20000) {
    return reponse(413, { ok: false, message: "Requete trop volumineuse." });
  }

  let data;
  try {
    data = JSON.parse(event.body || "{}");
  } catch (e) {
    return reponse(400, { ok: false, message: "Requete illisible." });
  }

  const of = propre(data.of, 80);
  if (!of) return reponse(200, { ok: false, message: "Organisme non precise." });

  // ------------------------------------------------------------------
  // 1. CE QUE LA PAGE AFFICHE : l'organisme et ses sessions ouvertes.
  // ------------------------------------------------------------------
  if (data.action === "sessions") {
    const { data: orgs, error: e1 } = await supabase
      .from("Organismes_publics").select("*").eq("organisme", of).limit(1);
    if (e1) return reponse(500, { ok: false, message: "Base indisponible." });
    if (!orgs || !orgs.length) {
      return reponse(200, { ok: false, message: "Ce lien ne correspond a aucun organisme." });
    }

    // LE CLOISONNEMENT EST ICI. On ne rend QUE les sessions de cet organisme :
    // deux entites, deux Qualiopi, et un praticien ne doit jamais voir sur le
    // formulaire de l'une les formations de l'autre.
    const { data: sess, error: e2 } = await supabase
      .from("Sessions_inscription").select("*")
      .eq("organisme", of).eq("ouverte", true)
      .order("date_debut", { ascending: true });
    if (e2) return reponse(500, { ok: false, message: "Base indisponible." });

    const o = orgs[0];
    return reponse(200, {
      ok: true,
      organisme: {
        marque: o.marque || of, accroche: o.accroche || "",
        mail_contact: o.mail_contact || "", telephone_contact: o.telephone_contact || "",
        logo: o.logo || "",
      },
      sessions: (sess || []).map((s) => {
        const maxi = Number(s.places_max || 0);
        const prises = Number(s.occupees || 0);
        return {
          code: s.code_session, formation: s.formation || "", titre: s.titre || "",
          date_texte: s.date_texte || "", lieu: s.lieu || "", tarif: s.tarif || "",
          couleur: s.couleur || "#4f7ef8", descriptif: s.descriptif || "",
          restantes: Math.max(0, maxi - prises),
          complet: maxi > 0 && prises >= maxi,
          // POUR LE SITE DE L'ORGANISME, qui lit cette meme adresse depuis le
          // 16/10/2026 au lieu de recopier les sessions a la main. La page
          // d'inscription, elle, ignore ces champs : les ajouter ne lui coute
          // rien et evite une seconde adresse a maintenir.
          date_debut: s.date_debut || "", date_fin: s.date_fin || "",
          places_max: maxi, occupees: prises,
        };
      }),
    });
  }

  // ------------------------------------------------------------------
  // 2. UN CODE PROMO, JUGE AVANT L'ENVOI : la page montre le prix reduit.
  // ------------------------------------------------------------------
  if (data.action === "code") {
    const j = await jugerCode(of, propre(data.session, 120), data.code, propre(data.mail, 200));
    if (j.panne) return reponse(500, { ok: false, message: j.message });
    return reponse(200, j);
  }

  // ------------------------------------------------------------------
  // 3. LA DEMANDE D'INSCRIPTION.
  // ------------------------------------------------------------------
  if (data.action === "inscrire") {
    const d = data.donnees || {};
    const code = propre(d.session, 120);
    if (!code) return reponse(200, { ok: false, message: "Formation non precisee." });

    // ON NE FAIT PAS CONFIANCE AU CODE ENVOYE. Il vient du navigateur, donc de
    // n'importe qui : sans ce controle, une requete forgee inscrirait quelqu'un
    // dans la session d'un AUTRE organisme, ou dans une session fermee.
    const { data: sess, error: e3 } = await supabase
      .from("Sessions_inscription").select("code_session,organisme,ouverte,titre")
      .eq("code_session", code).eq("organisme", of).limit(1);
    if (e3) return reponse(500, { ok: false, message: "Base indisponible." });
    if (!sess || !sess.length) {
      return reponse(200, { ok: false, message: "Cette formation n'est pas proposee ici." });
    }
    if (!sess[0].ouverte) {
      return reponse(200, {
        ok: false,
        message: "Les inscriptions a cette formation viennent d'etre closes. "
               + "Ecrivez-nous, nous vous proposerons la prochaine date.",
      });
    }

    const ligne = { organisme: of, code_session: code };
    for (const [c, max] of Object.entries(CHAMPS)) ligne[c] = propre(d[c], max);
    for (const c of OBLIGATOIRES) {
      if (!ligne[c]) return reponse(200, { ok: false, message: "Formulaire incomplet." });
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(ligne.mail)) {
      return reponse(200, { ok: false, message: "Cette adresse mail ne semble pas valide." });
    }
    ligne.mail = ligne.mail.toLowerCase();
    ligne.nom = ligne.nom.toUpperCase();

    // LE CODE EST REJUGE ICI, au moment ou il compte. La page l'a deja verifie,
    // mais elle tourne chez le visiteur : on ne lui fait pas confiance. Un code
    // refuse arrete l'envoi avec son motif — la personne a vu un prix, elle ne
    // doit pas en recevoir un autre sans le savoir.
    ligne.code_promo = "";
    if (codePropre(d.code_promo)) {
      const j = await jugerCode(of, code, d.code_promo, ligne.mail);
      if (j.panne) return reponse(500, { ok: false, message: j.message });
      if (!j.ok) return reponse(200, { ok: false, champ: "code_promo", message: "Code promo : " + j.message });
      ligne.code_promo = j.code;
    }

    // UN RENVOI CORRIGE REMPLACE, il ne double pas. Quelqu'un qui se rend
    // compte d'une faute de frappe renvoie le formulaire ; deux lignes pour
    // une personne creeraient deux conventions.
    const { error } = await supabase
      .from("Inscriptions")
      .upsert(ligne, { onConflict: "code_session,mail" });
    if (error) {
      return reponse(500, { ok: false, message: "Enregistrement impossible : " + error.message });
    }
    return reponse(200, { ok: true, message: "Demande enregistree" });
  }

  return reponse(200, { ok: false, message: "Action inconnue" });
};
