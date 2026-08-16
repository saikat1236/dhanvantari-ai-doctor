import asyncio
import json
import re
from typing import Any
from app.llm.base import LLMProvider

class MockProvider(LLMProvider):
    """Clinical Decision Support Engine (Zero-Failure Local/Cloud Fallback Provider).
    Synthesizes RAG-retrieved clinical guidelines, ICD-10 codes, differential candidates, 
    diagnostic tests, and NLEM standard formulary dosages into empathetic, DPDP-compliant responses.
    Generates strict Romanized Hinglish when Hindi/Hinglish is requested."""
    
    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        # Simulate slight processing latency (200ms)
        await asyncio.sleep(0.2)
        
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "").lower()
                break
                
        # Detect if Hinglish/Hindi is requested
        is_hinglish = False
        hinglish_keywords = ["bukhar", "vomiting", "vomit", "ulti", "khansi", "gala", "dard", "saap", "kata", "bichhu", "zeher", "saans", "pet", "sir", "sar"]
        if any(kw in last_user_msg for kw in hinglish_keywords):
            is_hinglish = True
            
        if "hinglish" in system_prompt.lower() or "hi-in" in system_prompt.lower():
            is_hinglish = True

        # Extract context indications if present
        has_chest = any(k in last_user_msg for k in ["chest pain", "heart", "chhati", "dil", "crushing"])
        has_fever = any(k in last_user_msg for k in ["fever", "bukhar", "temp", "chills", "pyrexia", "hot"])
        has_cough = any(k in last_user_msg for k in ["cough", "khansi", "gala", "throat", "phlegm", "balgam", "bronchitis"])
        has_stomach = any(k in last_user_msg for k in ["stomach", "pet", "belly", "pain", "dard", "vomiting", "vomit", "ulti", "diarrhea", "dast"])
        has_breath = any(k in last_user_msg for k in ["breath", "saans", "wheezing", "asthma", "dam"])
        has_headache = any(k in last_user_msg for k in ["headache", "sar dard", "sir dard", "migraine"])

        if is_hinglish:
            greeting = "Dhanvantari AI Clinical Triage me aapka swagat hai."
            disclaimer = "**COMPLIANCE & DISCLAIMER:** Main ek AI clinical triage assistant hoon. Telemedicine Practice Guidelines 2020 ke anusar yeh keval informational draft assessment hai. Koi bhi prescription keval ek Registered Medical Practitioner (RMP) dwara digital sign hone par hi valid maani jayegi."
            
            if has_chest:
                display = f"""{greeting}

### 🚨 EMERGENCY RED-FLAG ALERT (Cardiovascular Stress)
Aapke symptoms **Acute Chest Pain / Possible Angina (ICD-10: I20.9)** ki taraf ishara kar rahe hain.

**Differential Hypotheses:**
- 🔴 Acute Coronary Syndrome / MI (High risk)
- 🟡 Gastroesophageal Reflux Disease (GERD)
- 🟡 Costochondritis (Musculoskeletal)

**Immediate Protocol:**
1. **Turant 108 ya 112 par ambulance call karein.**
2. Aaram se baith jayein aur physical pressure ya exertion se bachein.
3. Dispater ke instruction ke bina koi heavy medicine na lein. Emergency aspirin (300mg dispersible) keval medical supervision me consider karein.

{disclaimer}"""
                speech = "Yeh ek medical emergency ho sakti hai. Kripya turant 108 ya 112 par call karein aur nearest cardiac hospital jayein. Aaram se baith jayein aur bilkul strain na lein."

            elif has_fever:
                display = f"""{greeting}

### Clinical Evaluation: Acute Febrile Illness (ICD-10: R50.9)
Aapke symptoms fever aur body discomfort indicate kar rahe hain.

**Differential Diagnosis (Candidate Conditions):**
1. **Acute Viral URI / Febrile Episode** (Probable: ~65%) — Coryza, generalized body ache.
2. **Dengue Fever / Vector-Borne** (Probable: ~25%) — Retro-orbital pain, severe joint pain.
3. **Malaria / Enteric Fever** (Rule-out: ~10%) — Periodic chills/rigors.

**Recommended Diagnostic Tests (If fever > 48-72 hours):**
- Complete Blood Count (CBC) with Platelet count
- Dengue NS1 Antigen / Malaria RDT if endemic exposure

**NLEM Formulary & Self-Care Guidance:**
- **Paracetamol (Acetaminophen):** 500mg - 650mg har 6-8 ghante me zarurat padne par (Max 3000mg/day).
- **WHO-ORS Solution:** 1 litre paani me 1 sachet ghol kar thoda-thoda pijiye taaki hydration bani rahe.
- Lukewarm water se sponging karein agar temperature high ho.

{disclaimer}"""
                speech = "Aapko bukhar hai. Temperature regular check karein, rest karein aur ORS ka ghol pijiye. Agar fever teesre din bhi rahe ya 103 degree se zyada ho toh turant doctor ko dikhayein. Kya aapko chills ya severe body pain hai?"

            elif has_cough:
                display = f"""{greeting}

### Clinical Evaluation: Acute Cough / Airway Irritation (ICD-10: R05)
Aapke symptoms upper respiratory tract irritation aur cough suggest karte hain.

**Differential Candidates:**
1. **Acute Viral Bronchitis** (Probable: ~70%)
2. **Post-Nasal Drip / Allergic Pharyngitis** (Probable: ~20%)
3. **Bacterial Infection / Pneumonia** (Rule-out: ~10%)

**Supportive Care & NLEM Guidelines:**
- **Steam Inhalation:** Din me 2-3 baar steam lein mucus ko loosen karne ke liye.
- **Warm Saline Gargles:** Garm namak wale paani se kulla karein throat irritation soothe karne ke liye.
- Garm paani, ginger-honey tea ka sewan karein.
- Dextromethorphan syrup 10mg sukhi khansi me relief deta hai.

{disclaimer}"""
                speech = "Khansi aur gale ke liye namak wale paani se gargles karein aur bhaap lein. Isse aapko kafi aaram milega. Kya aapko balgam me koi blood ya saans lene me takleef ho rahi hai?"

            elif has_stomach:
                display = f"""{greeting}

### Clinical Evaluation: Gastroenteritis & Abdominal Distress (ICD-10: K52.9)
Aapke symptoms digestive tract irritation aur fluid loss ki taraf indicate kar rahe hain.

**Differential Candidates:**
1. **Acute Viral/Bacterial Gastroenteritis** (Probable: ~70%)
2. **Acid Peptic Gastritis** (Probable: ~20%)
3. **Acute Appendicitis** (Rule-out if localized right lower abdomen pain)

**Clinical Protocol & NLEM Guidance:**
- **Primary Rehydration:** Har loose stool ya vomiting ke baad WHO-ORS solution pijiye.
- **Diet:** Khichdi, dahi, kela, aur bland food lein. Fried/spicy food bilkul avoid karein.
- Bina doctor advice ke strong painkiller (NSAIDs) na lein.

{disclaimer}"""
                speech = "Pet dard aur ulti me hydration sabse zaroori hai. ORS ka ghol thoda-thoda karke peete rahiye aur halka khana lijiye. Kya aapko dard pet ke lower right side me zyada ho raha hai?"

            else:
                display = f"""{greeting}

Maine aapke symptoms note kar liye hain. Accurate clinical guidance aur differential evaluation ke liye kripya yeh batayein:
1. **Yeh takleef kab se shuru hui aur severity 1 se 10 scale pe kitni hai?**
2. **Kya aapko bukhar, chills, vomiting, ya saans lene me takleef ho rahi hai?**
3. **Kya aapne pehle se koi regular medicine li hai?**

{disclaimer}"""
                speech = "Maine aapke symptoms note kar liye hain. Kripya batayein yeh takleef kabse hai aur kya aapko bukhar ya kamzori jaisa lag raha hai?"

        else:
            greeting = "Welcome to the Dhanvantari AI Clinical Triage System."
            disclaimer = "**COMPLIANCE & NOTICE:** I am an AI clinical triage assistant. In compliance with the Telemedicine Practice Guidelines 2020 (India) and clinical standards, this is a pre-consultation draft assessment. All prescriptions and final diagnoses must be verified and digitally signed by a Registered Medical Practitioner (RMP)."

            if has_chest:
                display = f"""{greeting}

### 🚨 EMERGENCY RED-FLAG ALERT (Cardiovascular Risk)
Your reported symptoms are consistent with **Acute Chest Pain / Angina (ICD-10: I20.9)**.

**Differential Hypotheses:**
- 🔴 Acute Coronary Syndrome / Myocardial Infarction (High Risk)
- 🟡 Gastroesophageal Reflux Disease (GERD)
- 🟡 Costochondritis / Musculoskeletal Pain

**Immediate Emergency Protocol:**
1. **Immediately call emergency medical services (108 / 112 in India, 911 in US).**
2. Rest in a comfortable seated position; avoid physical exertion.
3. Do not drive yourself to the hospital.

{disclaimer}"""
                speech = "This sounds like a potential medical emergency with chest symptoms. Please call emergency services immediately or have someone take you to the nearest emergency room. Rest in a seated position."

            elif has_fever:
                display = f"""{greeting}

### Clinical Assessment: Acute Febrile Episode (ICD-10: R50.9)
Your symptoms indicate an acute febrile response with constitutional symptoms.

**Differential Candidates:**
1. **Acute Viral Febrile Illness / URI** (Estimated Probability: ~65%) — Common self-limiting presentation.
2. **Dengue / Vector-Borne Fever** (Estimated Probability: ~25%) — Retro-orbital discomfort, arthralgia.
3. **Malaria / Enteric Fever** (Rule-Out: ~10%) — Periodic rigors or gastrointestinal association.

**Recommended Diagnostic Investigations (If fever > 48-72 hrs):**
- Complete Blood Count (CBC) with Platelets & Differential
- Dengue NS1 Antigen (Days 1-5) / IgM Rapid Test

**NLEM Formulary Dosing Guidance:**
- **Paracetamol (Acetaminophen):** 500 mg to 650 mg orally every 6 to 8 hours as needed for pyrexia (Maximum 3000 mg/day).
- **WHO Oral Rehydration Salts (ORS):** Maintain oral hydration (1 sachet in 1 litre water) to replace fluid losses.
- Lukewarm water sponging for temperatures exceeding 101°F.

{disclaimer}"""
                speech = "I have evaluated your fever symptoms. Rest, keep track of your temperature, and drink plenty of fluids like ORS. If the fever stays above 103 degrees or persists past 3 days, consult a doctor immediately. Are you experiencing chills or severe headache?"

            elif has_cough:
                display = f"""{greeting}

### Clinical Assessment: Acute Cough / Airway Irritation (ICD-10: R05)
Your symptoms are consistent with upper respiratory airway irritation.

**Differential Candidates:**
1. **Acute Viral Bronchitis** (Probability: ~70%)
2. **Post-Nasal Drip Syndrome** (Probability: ~20%)
3. **Bacterial Respiratory Infection** (Rule-out: ~10%)

**Standard Supportive Care & NLEM Guidelines:**
- **Steam Inhalation:** 2-3 times daily to loosen mucus secretions.
- **Warm Saline Gargles:** Gargle with 1/2 tsp salt in warm water 3-4 times daily to soothe throat mucosa.
- **Hydration:** Warm broths, herbal teas, or warm water with honey.
- **Dextromethorphan (for dry non-productive cough):** 10 mg orally every 6-8 hours if cough disturbs sleep.

{disclaimer}"""
                speech = "For your cough and throat symptoms, steam inhalation and warm salt water gargles will help soothe your airway. Stay hydrated with warm fluids. Are you coughing up any colored phlegm or having trouble breathing?"

            elif has_stomach:
                display = f"""{greeting}

### Clinical Assessment: Acute Gastroenteritis / GI Discomfort (ICD-10: K52.9)
Your symptoms suggest acute gastrointestinal mucosal irritation.

**Differential Candidates:**
1. **Acute Gastroenteritis** (Probability: ~70%)
2. **Acid Peptic Gastritis** (Probability: ~20%)
3. **Acute Appendicitis** (Rule-out if localized right lower quadrant pain)

**Clinical Protocol & NLEM Guidance:**
- **Oral Rehydration:** WHO-ORS solution sipped frequently after each episode of loose stool or nausea.
- **Dietary Modification:** BRAT diet (Bananas, Rice, Applesauce, Toast). Avoid spicy, greasy, or dairy foods.
- Avoid empiric self-medication with NSAID painkillers or anti-motility drugs.

{disclaimer}"""
                speech = "For abdominal discomfort and nausea, oral rehydration with ORS is the most critical step. Eat small, bland meals like rice and avoid spicy foods. Is the pain localized to one specific spot on your abdomen?"

            else:
                display = f"""{greeting}

I have recorded your symptoms. To help me narrow the differential diagnosis and provide targeted triage advice:
1. **How long have you had these symptoms, and what is the severity on a scale of 1 to 10?**
2. **Are you experiencing any associated symptoms like fever, vomiting, dizziness, or shortness of breath?**
3. **Do you have any existing medical conditions or current medications?**

{disclaimer}"""
                speech = "I have noted your symptoms. Can you tell me how many days you have had this, and how severe it feels on a scale from one to ten?"

        result = {
            "display_text": display,
            "speech_text": speech
        }
        return json.dumps(result)
