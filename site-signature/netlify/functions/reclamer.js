// Depot d'une reclamation depuis la page publique.
//
// POURQUOI CETTE FONCTION. L'indicateur 31 demande que la procedure de
// reclamation soit PORTEE A LA CONNAISSANCE des beneficiaires. Une adresse
// mail inscrite dans un dossier interne ne l'est pas. Une page ou l'on depose
// sa reclamation, dont le lien figure dans la convocation, l'est.
//
// ELLE N'IMPOSE PAS D'ETRE INSCRIT. Un client, un formateur, un financeur
// peuvent reclamer ; exiger un identifiant de session fermerait le canal a
// ceux qui en ont le plus besoin. Seuls le nom, le contact et l'objet sont
// requis — de quoi repondre et de quoi savoir de quoi il s'agit.
const { createClient } = require("@supabase/supabase-js");
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ message: "Methode non autorisee" }) };
  }
  try {
    const d = JSON.parse(event.body || "{}");
    const qui = (d.qui || "").trim();
    const mail = (d.mail || "").trim();
    const objet = (d.objet || "").trim();
    const description = (d.description || "").trim();

    if (!qui) {
      return { statusCode: 400, body: JSON.stringify({ message: "Indiquez votre nom." }) };
    }
    if (!mail || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(mail)) {
      return { statusCode: 400,
               body: JSON.stringify({ message: "Indiquez une adresse mail valide : c'est par la que nous vous repondrons." }) };
    }
    if (!objet) {
      return { statusCode: 400, body: JSON.stringify({ message: "Resumez votre reclamation en une ligne." }) };
    }
    // Une reclamation sans contenu n'est pas exploitable, et la personne
    // croirait avoir ete entendue.
    if (description.length < 10) {
      return { statusCode: 400,
               body: JSON.stringify({ message: "Decrivez ce qui s'est passe : quelques mots suffisent, mais il en faut." }) };
    }

    const { error } = await supabase.from("Reclamations").insert({
      qui: qui.slice(0, 200),
      mail: mail.slice(0, 200),
      organisme: (d.organisme || "").trim().slice(0, 60),
      session: (d.session || "").trim().slice(0, 120),
      origine: (d.origine || "apprenant").trim().slice(0, 40),
      objet: objet.slice(0, 300),
      description: description.slice(0, 8000),
    });
    if (error) {
      return { statusCode: 500, body: JSON.stringify({ message: "Erreur Supabase : " + error.message }) };
    }
    return { statusCode: 200, body: JSON.stringify({ message: "Reclamation enregistree" }) };
  } catch (erreur) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur : " + erreur.message }) };
  }
};
