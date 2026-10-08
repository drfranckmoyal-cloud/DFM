const { createClient } = require("@supabase/supabase-js");
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
const reponse = (code, corps) => ({
  statusCode: code,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(corps),
});
exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return reponse(405, { ok: false, message: "Methode non autorisee" });
  }
  try {
    const data = JSON.parse(event.body || "{}");
    if (data.action === "charger") {
      if (!data.session) return reponse(200, { ok: false, message: "Session non precisee" });
      const { data: lignes, error } = await supabase
        .from("Sessions_publiques")
        .select("session_code, formation, titre, date_texte, participants, questions, satisfaction, ouvert")
        .eq("session_code", data.session)
        .limit(1);
      if (error) return reponse(500, { ok: false, message: "Erreur Supabase : " + error.message });
      if (!lignes || !lignes.length) {
        return reponse(200, { ok: false, message: "Cette session n'est pas ouverte aux questionnaires." });
      }
      return reponse(200, { ok: true, session: lignes[0] });
    }
    if (data.action === "repondre") {
      if (!data.session || !data.mail || !data.type) {
        return reponse(200, { ok: false, message: "Informations incompletes" });
      }
      const { error } = await supabase.from("Questionnaires").upsert({
        session_code: data.session,
        formation: data.formation || "",
        mail: String(data.mail).trim().toLowerCase(),
        nom: data.nom || "",
        type: data.type,
        reponses: data.reponses || {},
      }, { onConflict: "session_code,mail,type" });
      if (error) return reponse(500, { ok: false, message: "Erreur Supabase : " + error.message });
      return reponse(200, { ok: true, message: "Reponses enregistrees" });
    }
    return reponse(200, { ok: false, message: "Action inconnue" });
  } catch (erreur) {
    return reponse(500, { ok: false, message: "Erreur : " + erreur.message });
  }
};
