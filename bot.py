import os
import sqlite3
import logging
import requests
from flask import Flask, request, jsonify

# Required Render environment variables:
# BOT_TOKEN, BOT_USERNAME (without @), CHANNEL_ID (e.g. @Svsi70),
# ADMIN_IDS (comma-separated Telegram numeric user IDs)
TOKEN = os.environ["BOT_TOKEN"]
BOT_USERNAME = os.environ["BOT_USERNAME"].lstrip("@")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@Svsi70")
ADMIN_IDS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
DB = os.environ.get("DB_PATH", "/tmp/quiz.sqlite3")
API = f"https://api.telegram.org/bot{TOKEN}"
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Question bank: 70 NCERT/Bihar Board-style Class 12 Chemistry MCQs.
# Each item: (question, [four options], zero-based correct option)
Q = [
("The SI unit of molality is:", ["mol kg⁻¹", "mol L⁻¹", "kg mol⁻¹", "mol m⁻³"], 0),
("Which concentration term is independent of temperature?", ["Molarity", "Molality", "Normality", "Volume percent"], 1),
("For an ideal solution, Raoult's law is obeyed:", ["At all compositions", "Only at low concentration", "Only at high temperature", "Only by electrolytes"], 0),
("The van't Hoff factor for complete dissociation of NaCl is approximately:", ["1", "2", "3", "0.5"], 1),
("Osmotic pressure is a:", ["Colligative property", "Chemical property", "Surface property", "Magnetic property"], 0),
("The standard electrode potential of the standard hydrogen electrode is:", ["1.00 V", "−1.00 V", "0.00 V", "0.76 V"], 2),
("The SI unit of conductivity is:", ["S m⁻¹", "S m² mol⁻¹", "ohm m", "ohm⁻¹ cm²"], 0),
("At the cathode, the reaction is:", ["Oxidation", "Reduction", "Neutralisation", "Hydrolysis"], 1),
("In a galvanic cell, electrons flow through the external circuit from:", ["Cathode to anode", "Anode to cathode", "Salt bridge to anode", "Electrolyte to cathode"], 1),
("The Nernst equation relates electrode potential to:", ["Only pressure", "Concentration and temperature", "Only mass", "Only volume"], 1),
("The unit of molar conductivity is:", ["S m² mol⁻¹", "S m⁻¹", "mol S⁻¹", "ohm m⁻¹"], 0),
("Faraday's first law is based on the amount of substance deposited being proportional to:", ["Resistance", "Charge passed", "Voltage only", "Temperature"], 1),
("The rate of a chemical reaction is generally expressed as change in:", ["Concentration per unit time", "Mass per unit volume", "Pressure per unit mass", "Temperature per unit time"], 0),
("For a first-order reaction, the unit of rate constant is:", ["mol L⁻¹ s⁻¹", "s⁻¹", "L mol⁻¹ s⁻¹", "mol⁻¹ L s⁻¹"], 1),
("The half-life of a first-order reaction is:", ["Directly proportional to initial concentration", "Independent of initial concentration", "Inversely proportional to rate", "Always zero"], 1),
("The slope of a plot of ln[A] versus time for a first-order reaction is:", ["k", "−k", "1/k", "−1/k"], 1),
("A catalyst changes the reaction rate by changing the:", ["Enthalpy", "Activation energy", "Equilibrium constant", "Overall energy change"], 1),
("Molecularity is always:", ["Zero or fractional", "A positive integer", "Negative", "A measured concentration"], 1),
("The order of a reaction is determined:", ["From balanced equation only", "Experimentally", "From molecular mass", "From colour"], 1),
("Adsorption is generally a:", ["Bulk phenomenon", "Surface phenomenon", "Nuclear phenomenon", "Optical phenomenon"], 1),
("The substance on whose surface adsorption occurs is called:", ["Adsorbate", "Adsorbent", "Solute", "Solvent"], 1),
("Physisorption is generally favoured by:", ["High temperature", "Low temperature", "Very high activation energy", "Strong ionic bonding"], 1),
("A catalyst increases the rate by providing a pathway with:", ["Higher activation energy", "Lower activation energy", "Higher enthalpy", "No intermediates"], 1),
("Tyndall effect is shown by:", ["True solutions", "Colloids", "Pure solvents only", "Crystals only"], 1),
("The movement of colloidal particles under an electric field is:", ["Dialysis", "Electrophoresis", "Peptisation", "Coagulation"], 1),
("The coagulating power of an ion generally increases with its:", ["Lower charge", "Higher charge", "Larger volume only", "Lower mass"], 1),
("Which is an example of a lyophilic sol?", ["Starch in water", "Gold sol", "Sulphur sol", "Arsenic sulphide sol"], 0),
("The IUPAC name of CH3CH2CHO is:", ["Propanone", "Propanal", "Ethanol", "Propanoic acid"], 1),
("The functional group of aldehydes is:", ["−COOH", "−CHO", "−OH", "−CO−"], 1),
("Tollens' reagent gives a silver mirror with:", ["Most aldehydes", "Most ketones", "Alkanes", "Ethers"], 0),
("The product of oxidation of a primary alcohol is generally first:", ["Ketone", "Aldehyde", "Ether", "Alkene"], 1),
("Which compound gives the iodoform test?", ["Methanol", "Ethanol", "Benzene", "Methanoic acid"], 1),
("Phenol is more acidic than ethanol because:", ["Phenoxide ion is resonance-stabilised", "Ethanol is aromatic", "Phenol has no oxygen", "Phenol is a stronger base"], 0),
("Williamson synthesis is used to prepare:", ["Ethers", "Aldehydes", "Amines", "Carboxylic acids"], 0),
("The major product of dehydration of ethanol at about 443 K with concentrated H2SO4 is:", ["Ethene", "Ethane", "Ethanal", "Ethanoic acid"], 0),
("Aniline is less basic than ammonia mainly due to:", ["Resonance delocalisation of the nitrogen lone pair", "Higher molecular mass", "Absence of nitrogen", "Ionic bonding"], 0),
("The carbylamine test is given by:", ["Primary amines", "Secondary amines", "Tertiary amines", "Amides"], 0),
("Diazotisation of aniline is usually carried out at:", ["273–278 K", "323–333 K", "373 K", "Room temperature only"], 0),
("The linkage present in proteins is:", ["Glycosidic", "Peptide", "Phosphodiester", "Ester"], 1),
("Glucose is classified as:", ["A ketohexose", "An aldohexose", "An aldopentose", "A ketopentose"], 1),
("The sugar present in DNA is:", ["Ribose", "2-deoxyribose", "Glucose", "Fructose"], 1),
("The monomers of proteins are:", ["Nucleotides", "Amino acids", "Fatty acids", "Monosaccharides"], 1),
("Which vitamin is water-soluble?", ["Vitamin A", "Vitamin D", "Vitamin E", "Vitamin C"], 3),
("The coordination number of cobalt in [Co(NH3)6]Cl3 is:", ["3", "4", "6", "9"], 2),
("The oxidation state of Co in [Co(NH3)6]Cl3 is:", ["0", "+2", "+3", "+6"], 2),
("A ligand that binds through two donor atoms is called:", ["Monodentate", "Bidentate", "Ambidentate", "Unidentate"], 1),
("The shape of [Ni(CO)4] is:", ["Square planar", "Tetrahedral", "Octahedral", "Linear"], 1),
("The IUPAC name of K4[Fe(CN)6] is:", ["Potassium hexacyanidoferrate(II)", "Potassium hexacyanidoferrate(III)", "Potassium ferrocyanide(III)", "Potassium tetracyan iron"], 0),
("Transition elements generally show variable oxidation states due to participation of:", ["Only s electrons", "Both (n−1)d and ns electrons", "Only p electrons", "Core electrons"], 1),
("The colour of many transition-metal ions is due to:", ["d–d transitions", "Nuclear transitions", "Only s–s transitions", "Hydrogen bonding"], 0),
("Which is not generally a transition element?", ["Fe", "Cu", "Zn", "Cr"], 2),
("The lanthanoid contraction is due to poor shielding by:", ["4f electrons", "3d electrons", "2p electrons", "6s electrons"], 0),
("The most common oxidation state of lanthanoids is:", ["+1", "+2", "+3", "+5"], 2),
("The geometry of methane is:", ["Linear", "Trigonal planar", "Tetrahedral", "Square planar"], 2),
("The hybridisation of carbon in ethyne is:", ["sp", "sp2", "sp3", "dsp2"], 0),
("The strongest intermolecular force among the following is generally:", ["London dispersion", "Dipole-induced dipole", "Hydrogen bonding", "Weak dispersion only"], 2),
("Which has the highest boiling point among hydrogen halides (excluding HF)?", ["HCl", "HBr", "HI", "All equal"], 2),
("The shape of NH3 is:", ["Trigonal planar", "Trigonal pyramidal", "Tetrahedral", "Linear"], 1),
("The bond angle in water is approximately:", ["180°", "120°", "104.5°", "90°"], 2),
("Which is a strong field ligand?", ["I⁻", "Br⁻", "CN⁻", "F⁻"], 2),
("The unit of rate constant for a zero-order reaction is:", ["s⁻¹", "mol L⁻¹ s⁻¹", "L mol⁻¹ s⁻¹", "mol² L⁻² s⁻¹"], 1),
("For a zero-order reaction, the half-life is proportional to:", ["Initial concentration", "Square of initial concentration", "Inverse of initial concentration", "Independent of initial concentration"], 0),
("The electrolyte used in a lead storage battery is:", ["Dilute H2SO4", "NaCl solution", "KOH solution", "HNO3"], 0),
("Rust is mainly:", ["FeO", "Fe2O3·xH2O", "Fe3O4 only", "FeCO3"], 1),
("The process of coating iron with zinc is:", ["Tinning", "Galvanisation", "Anodising", "Electrolysis"], 1),
("Which polymer is formed from tetrafluoroethene?", ["PVC", "Teflon", "Bakelite", "Nylon-6"], 1),
("Nylon-6,6 is a:", ["Addition polymer", "Condensation polymer", "Natural polymer", "Inorganic polymer"], 1),
("The monomer of PVC is:", ["Ethene", "Vinyl chloride", "Styrene", "Tetrafluoroethene"], 1),
("A biodegradable polymer is:", ["PHBV", "PVC", "Polystyrene", "Teflon"], 0),
("The antiseptic commonly used in dilute solution for wounds is:", ["Iodoform", "Chloramphenicol", "Aspirin", "Paracetamol"], 0),
("A broad-spectrum antibiotic is one that:", ["Acts against a wide range of bacteria", "Kills all viruses", "Acts only on fungi", "Has no side effects"], 0),
]

def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS players( user_id INTEGER PRIMARY KEY, name TEXT, score INTEGER NOT NULL DEFAULT 0, answered INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 0)""")
    con.commit()
    return con

def tg(method, data):
    r = requests.post(f"{API}/{method}", json=data, timeout=25)
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(result)
    return result["result"]

def send(chat_id, text, **kwargs):
    return tg("sendMessage", {"chat_id": chat_id, "text": text, **kwargs})

def is_admin(user_id):
    return str(user_id) in ADMIN_IDS

def leaderboard():
    con = db()
    rows = con.execute(
        "SELECT name,score,answered FROM players WHERE answered > 0 ORDER BY score DESC, answered ASC, name ASC LIMIT 10"
    ).fetchall()
    con.close()
    if not rows:
        return "अभी किसी विद्यार्थी ने क्विज़ पूरा नहीं किया है।"
    lines = ["🏆 Chemistry Quiz – Top 10"]
    for i, (name, score, answered) in enumerate(rows, 1):
        lines.append(f"{i}. {name}: {score}/70")
    return "\n".join(lines)

def begin_quiz(user):
    uid = user["id"]
    name = user.get("first_name", "Student")
    con = db()
    con.execute("""INSERT INTO players(user_id,name,score,answered,active) VALUES(?,?,0,0,1) ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,score=0,answered=0,active=1""",
        (uid, name))
    con.commit()
    con.close()
    send(uid, f"नमस्ते {name}! 🧪\nClass 12 Chemistry Quiz शुरू हो गया है।\nकुल 70 प्रश्न; सही उत्तर +1, गलत उत्तर 0।")
    ask_question(uid, 0)

def ask_question(uid, idx):
    if idx >= len(Q):
        con = db()
        row = con.execute("SELECT name,score FROM players WHERE user_id=?", (uid,)).fetchone()
        con.execute("UPDATE players SET active=0 WHERE user_id=?", (uid,))
        con.commit()
        con.close()
        send(uid, f"🎉 क्विज़ पूरा हुआ!\nआपका स्कोर: {row[1]}/70\n\n" + leaderboard())
        try:
            send(CHANNEL_ID, f"एक विद्यार्थी ने Chemistry Quiz पूरा किया।\n\n{leaderboard()}")
        except Exception:
            logging.exception("Could not post leaderboard to channel")
        return
    question, opts, correct = Q[idx]
    buttons = [[{"text": f"{chr(65+j)}. {opt}", "callback_data": f"a:{idx}:{j}"}] for j, opt in enumerate(opts)]
    send(uid, f"प्रश्न {idx+1}/70\n\n{question}",
         reply_markup={"inline_keyboard": buttons})

@app.route("/", methods=["GET"])
def home():
    return "Chemistry quiz bot is running", 200

@app.route("/telegram", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    try:
        if "message" in update:
            m = update["message"]
            chat_id = m["chat"]["id"]
            user = m.get("from", {})
            text = m.get("text", "")
            if text.startswith("/start"):
                payload = text.partition(" ")[2].strip()
                if payload == "quiz":
                    begin_quiz(user)
                else:
                    send(chat_id, "स्वागत है! अपने चैनल @Svsi70 से Start Quiz बटन दबाकर क्विज़ शुरू करें।")
            elif text.startswith("/startquiz"):
                if is_admin(user.get("id")):
                    link = f"https://t.me/{BOT_USERNAME}?start=quiz"
                    send(CHANNEL_ID, "🧪 Swami Vivekanand Science Institute\nClass 12 Chemistry – 70 MCQ Quiz शुरू हो गया है!\nभाग लेने के लिए नीचे Start Quiz दबाएँ।",
                         reply_markup={"inline_keyboard": [[{"text": "▶️ Start Quiz", "url": link}]]})
                    send(chat_id, "क्विज़ का लिंक चैनल पर प्रकाशित कर दिया गया है।")
                else:
                    send(chat_id, "यह कमांड केवल अधिकृत एडमिन के लिए है।")
            elif text.startswith("/leaderboard"):
                send(chat_id, leaderboard())
            elif text.startswith("/myid"):
                send(chat_id, f"आपका Telegram ID: {user.get('id')}")
        elif "callback_query" in update:
            cq = update["callback_query"]
            data = cq.get("data", "")
            uid = cq["from"]["id"]
            tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
            if data.startswith("a:"):
                _, si, sj = data.split(":")
                idx, choice = int(si), int(sj)
                con = db()
                row = con.execute("SELECT active,answered,score FROM players WHERE user_id=?", (uid,)).fetchone()
                if not row or not row[0] or row[1] != idx:
                    con.close()
                    send(uid, "यह प्रश्न अब सक्रिय नहीं है। नया क्विज़ शुरू करने के लिए चैनल का बटन दबाएँ।")
                else:
                    correct = Q[idx][2]
                    score = row[2] + (1 if choice == correct else 0)
                    con.execute("UPDATE players SET score=?,answered=? WHERE user_id=?",
                                (score, idx+1, uid))
                    con.commit()
                    con.close()
                    send(uid, "✅ सही उत्तर!" if choice == correct else f"❌ गलत उत्तर। सही विकल्प: {chr(65+correct)}")
                    ask_question(uid, idx+1)
    except Exception:
        logging.exception("Update handling failed")
    return jsonify(ok=True)

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if PUBLIC_URL:
    try:
        tg("setWebhook", {"url": PUBLIC_URL + "/telegram"})
    except Exception:
        logging.exception("Webhook setup failed")
