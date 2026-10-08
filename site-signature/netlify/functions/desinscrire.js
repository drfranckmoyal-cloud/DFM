// Desinscription d'un contact — pose « ne plus contacter » sur sa fiche.
//
// LE JETON EST VERIFIE ICI, jamais fait confiance. Il porte le numero de fiche
// ET une signature calculee avec la cle Supabase, que seuls DFM et cette
// fonction connaissent. Sans cette verification, « ?c=42 » suffirait a
// desinscrire n'importe qui en changeant un chiffre.
//
// L'ACTION EST IDEMPOTENTE : se desinscrire deux fois donne le meme resultat.
// Quelqu'un qui reclique sur le lien de son mail doit voir une confirmation,
// pas une erreur.
const { createClient } = require("@supabase/supabase-js");
const crypto = require("crypto");

const LONGUEUR = 24;

function signature(identifiant) {
  return crypto
    .createHmac("sha256", process.env.SUPABASE_KEY || "")
    .update(String(identifiant))
    .digest("hex")
    .slice(0, LONGUEUR);
}

function verifier(jeton) {
  const brut = String(jeton || "").trim();
  const point = brut.indexOf(".");
  if (point < 1) return null;
  const identifiant = brut.slice(0, point);
  const sig = brut.slice(point + 1);
  if (!/^\d+$/.test(identifiant) || !sig) return null;
  const attendue = signature(identifiant);
  // Comparaison a duree constante : « === » s'arrete au premier caractere
  // different, et le temps de reponse renseignerait sur la signature attendue.
  const a = Buffer.from(sig);
  const b = Buffer.from(attendue);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  return identifiant;
}

exports.handler = async (event) => {
  const jeton = (event.queryStringParameters || {}).c || "";
  const identifiant = verifier(jeton);
  if (!identifiant) {
    return {
      statusCode: 400,
      body: JSON.stringify({ message: "Ce lien de désinscription n'est pas valable." }),
    };
  }
  try {
    const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
    const { error } = await supabase
      .from("Contacts")
      .update({ ne_plus_contacter: true })
      .eq("id", identifiant);
    if (error) {
      return { statusCode: 500, body: JSON.stringify({ message: "Erreur : " + error.message }) };
    }
    return { statusCode: 200, body: JSON.stringify({ message: "Désinscription enregistrée" }) };
  } catch (erreur) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur : " + erreur.message }) };
  }
};
