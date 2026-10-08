const { createClient } = require("@supabase/supabase-js");

// Connexion a Supabase avec les cles rangees dans Netlify
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ message: "Methode non autorisee" }) };
  }

  try {
    const data = JSON.parse(event.body);
    const signature = data.signature;
    const praticien = data.praticien || "Inconnu";
    const formation = data.formation || "Inconnue";
    // LE CODE DE SESSION. Le nom de formation ne suffit pas a
    // identifier une signature : deux organismes peuvent dispenser la
    // meme formation, et un meme organisme la donner deux fois dans
    // l'annee. Sans ce code, la relevee prend la signature la plus
    // recente portant le bon nom — pas forcement la bonne.
    const session = data.session || "";

    if (!signature) {
      return { statusCode: 400, body: JSON.stringify({ message: "Aucune signature recue" }) };
    }

    // Ecriture dans la table "Signatures" de Supabase
    // On tente AVEC la colonne « session ». Si elle n'existe pas encore dans
    // la base, PostgREST refuse tout l'enregistrement : on reessaie alors sans
    // elle. Une signature perdue serait bien pire qu'une signature imprecise,
    // et cela permet de deployer le site avant d'ajouter la colonne.
    const base = {
      praticien: praticien,
      formation: formation,
      signature_images: signature,
      statut: "signee",
    };
    let { error } = await supabase
      .from("Signatures")
      .insert(Object.assign({ session: session }, base));
    if (error && /session/i.test(error.message || "")) {
      ({ error } = await supabase.from("Signatures").insert(base));
    }

    if (error) {
      return { statusCode: 500, body: JSON.stringify({ message: "Erreur Supabase : " + error.message }) };
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ message: "Signature enregistree avec succes !" }),
    };
  } catch (erreur) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur : " + erreur.message }) };
  }
};