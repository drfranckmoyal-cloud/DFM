const { createClient } = require("@supabase/supabase-js");
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ message: "Methode non autorisee" }) };
  }
  try {
    const data = JSON.parse(event.body);
    const praticien = (data.praticien || "").trim();
    const formation = (data.formation || "").trim();
    const motif = (data.motif || "").trim();
    if (!praticien || praticien === "Inconnu") {
      return { statusCode: 400, body: JSON.stringify({ message: "Praticien non identifie" }) };
    }
    let { error } = await supabase
      .from("Annulations")
      .insert({ praticien: praticien, formation: formation, motif: motif,
                session: data.session || "" });
    if (error && /session/i.test(error.message || "")) {
      ({ error } = await supabase.from("Annulations")
        .insert({ praticien: praticien, formation: formation, motif: motif }));
    }
    if (error) {
      return { statusCode: 500, body: JSON.stringify({ message: "Erreur Supabase : " + error.message }) };
    }
    return { statusCode: 200, body: JSON.stringify({ message: "Demande enregistree" }) };
  } catch (erreur) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur : " + erreur.message }) };
  }
};
