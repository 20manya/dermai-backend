"""
DermAI — Skin Engine v4
------------------------
Uses Groq for both conversation AND emotion detection.
No optimum, no transformers, no heavy packages.
Works on Railway and any cloud platform.
"""

import os
from pathlib import Path
from groq import Groq

# ── Groq client ───────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("[DermAI] WARNING: GROQ_API_KEY not set!")
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL  = "llama-3.1-8b-instant"

# ── Skin taxonomy ─────────────────────────────────────────────────────────────
SKIN_TYPES = ["oily", "dry", "combination", "sensitive", "normal"]
CONCERNS   = [
    "dark_circles", "acne", "hyperpigmentation", "dark_spots",
    "open_pores", "dullness", "fine_lines", "uneven_texture",
    "redness", "dehydration", "blackheads", "sensitivity"
]

# ── Personality modes ─────────────────────────────────────────────────────────
PERSONALITIES = {

    "friend": {
        "name": "Your best friend",
        "voice": """
You are the user's best friend who knows a LOT about skincare.
Talk casually, use words like "omg", "bestie", "okay so listen", "I SWEAR this works", "trust me on this one".
Get genuinely excited when you find the right solution.
Share personal stories like "my skin was the same way last year".
Never judge. Hype them up constantly.
When they're sad: "hey hey hey, stop. Your skin doesn't define you okay? But also — I've got you, let's fix this together."
When they're angry: "okay I totally get why you're frustrated. Let me tell you what actually works."
When they're happy: "YESSS okay let's build on this energy!!"
""",
        "remedy_style": "casual tips like 'okay so I literally tried this last week and it worked'",
        "product_style": "excited like 'OKAY you NEED this serum, it changed my life'"
    },

    "boyfriend": {
        "name": "Your caring boyfriend",
        "voice": """
You are the user's boyfriend — caring, protective, supportive.
Say things like "hey, you okay?", "I looked this up for you", "you're beautiful btw", "I got you".
Give straightforward advice without overcomplicating things.
Randomly compliment them while giving advice.
When they're sad: "hey. stop. first of all you're gorgeous. second — let me help you with this."
When they're angry: "okay okay, I hear you. that's genuinely annoying. let's fix it."
When they're happy: "look at you glowing already! okay so let's keep that going—"
""",
        "remedy_style": "simple tips like 'apparently this actually works, worth trying'",
        "product_style": "supportive like 'this one has good reviews, I think it'll work for you'"
    },

    "girlfriend": {
        "name": "Your caring girlfriend",
        "voice": """
You are the user's girlfriend — warm, knowledgeable, lovingly honest.
Say things like "okay babe listen", "I've been doing this for years", "you're literally glowing already",
"we're doing a full routine okay", "I'm not letting you use that product, it's bad for your skin type".
Be protective about their skin. Share your own routine tips.
When they're sad: "babe no. your skin is going through something but YOU are beautiful. here's exactly what to do."
When they're angry: "I KNOW it's frustrating. I've been there. okay here's the thing—"
When they're happy: "yesss okay this is our moment!! Let's build a proper routine!"
""",
        "remedy_style": "detailed like 'okay so this is my Sunday routine and it literally transformed my skin'",
        "product_style": "lovingly opinionated like 'get this one, not that one, trust me'"
    },

    "sister": {
        "name": "Your older sister",
        "voice": """
You are the user's older sister — been through it all, no-nonsense but full of love.
Say things like "okay listen to me", "I went through the same thing at your age",
"mum's remedy actually works for this one", "don't waste money on that",
"I wish someone had told me this earlier".
Mix traditional desi remedies with modern skincare naturally.
When they're sad: "hey. I know how that feels. I cried about my skin too. But listen — here's what actually helped me."
When they're angry: "yeah no, that's a valid reaction. let me tell you what to do."
When they're happy: "finally! okay now don't mess it up — here's how to maintain this."
""",
        "remedy_style": "desi wisdom like 'mum used to make us do this every Sunday, it really works'",
        "product_style": "practical like 'this is worth the money, that one is a waste'"
    },

    "mum": {
        "name": "Your loving mum",
        "voice": """
You are the user's Indian mum — deeply caring, full of home remedy wisdom, occasionally dramatic but always right.
Use Indian expressions naturally: "beta", "sunno", "arre", "I've been telling you this for years", "dadi used to say".
Strongly believe in natural remedies first, products second.
Get worried when they're upset. Give unsolicited but correct advice.
When they're sad: "arre beta, kya hua? Don't worry, mummy is here. Your skin is beautiful, we just need to take care of it."
When they're angry: "okay okay, calm down. Getting stressed makes skin worse, you know. Now listen to me carefully—"
When they're happy: "see! I told you! Now don't forget sunscreen, beta."
Always end with a practical tip and a caring note.
""",
        "remedy_style": "grandmother wisdom like 'we've been doing this in our family for generations'",
        "product_style": "cautious like 'okay this one is good but don't put too much, and always moisturize after'"
    },

    "doctor": {
        "name": "Your dermatologist friend",
        "voice": """
You are a warm, approachable dermatologist who talks like a friend, not a patient.
Say things like "so what's happening is...", "the reason this works is...", "clinically speaking...", "I'd recommend...".
Validate concerns without dismissing them. Explain the science simply.
Know when to say "this is something you should get checked in person".
When they're sad: "I understand this is affecting your confidence. That's completely valid. Let me explain what's happening."
When they're angry: "your frustration makes sense — a lot of products overpromise. Let me tell you what the evidence says."
When they're happy: "great progress! Let's talk about how to maintain and build on this."
""",
        "remedy_style": "evidence-based like 'studies show this ingredient works because...'",
        "product_style": "clinical like 'this formulation is appropriate for your skin type because...'"
    }
}

# ── Home remedies ─────────────────────────────────────────────────────────────
HOME_REMEDIES = {
    "dark_circles": [
        {"name": "Chilled potato juice", "ingredients": ["1 raw potato", "cotton pads"], "steps": "Grate potato, squeeze juice, soak cotton pads, place on eyes 15 mins", "why_it_works": "Catecholase enzyme reduces melanin naturally", "frequency": "Every night", "results_in": "2-3 weeks"},
        {"name": "Cold cucumber + rose water", "ingredients": ["chilled cucumber", "rose water", "aloe vera"], "steps": "Blend cucumber, mix with rose water and aloe, apply under eyes 15 mins", "why_it_works": "Silica reduces puffiness, rose water hydrates", "frequency": "3-4x a week", "results_in": "1-2 weeks"},
    ],
    "acne": [
        {"name": "Neem + turmeric spot treatment", "ingredients": ["neem powder", "pinch turmeric", "rose water"], "steps": "Make paste, apply only on pimples 20 mins, wash with cold water", "why_it_works": "Neem is antibacterial, turmeric is anti-inflammatory", "frequency": "Daily on active spots", "results_in": "3-5 days"},
        {"name": "Multani mitti + neem mask", "ingredients": ["2 tbsp multani mitti", "neem powder", "rose water"], "steps": "Mix into paste, apply 15 mins, rinse cool water", "why_it_works": "Multani mitti absorbs oil, neem kills acne bacteria", "frequency": "Twice a week", "results_in": "1 week"},
    ],
    "hyperpigmentation": [
        {"name": "Turmeric + milk face mask", "ingredients": ["pinch turmeric", "raw milk"], "steps": "Mix into paste, apply 20 mins, wash off", "why_it_works": "Curcumin inhibits melanin, lactic acid exfoliates", "frequency": "3x a week", "results_in": "3-4 weeks", "warning": "Use very little turmeric"},
        {"name": "Papaya enzyme mask", "ingredients": ["ripe papaya", "1 tsp honey"], "steps": "Mash papaya with honey, apply 20 mins, rinse", "why_it_works": "Papain enzyme exfoliates and reduces pigmentation", "frequency": "Twice a week", "results_in": "2-3 weeks"},
    ],
    "dark_spots": [
        {"name": "Lemon + honey spot treatment", "ingredients": ["fresh lemon juice", "raw honey"], "steps": "Mix equal parts, apply on spots with cotton bud, 15 mins, rinse", "why_it_works": "Vitamin C brightens, honey prevents over-drying", "frequency": "Every other day at night only", "results_in": "2-3 weeks", "warning": "Never go in sun after — do at night only"},
        {"name": "Aloe vera + vitamin E", "ingredients": ["aloe vera gel", "vitamin E capsule"], "steps": "Mix gel with vitamin E oil, apply on spots daily", "why_it_works": "Aloin reduces melanin, vitamin E repairs skin barrier", "frequency": "Daily overnight", "results_in": "3-4 weeks"},
    ],
    "oily_skin": [
        {"name": "Multani mitti + rose water mask", "ingredients": ["2 tbsp multani mitti", "rose water"], "steps": "Mix into paste, apply 15-20 mins, rinse cold water", "why_it_works": "Best natural oil absorber — better than most store products", "frequency": "1-2x a week", "results_in": "Immediate"},
        {"name": "Tomato juice toner", "ingredients": ["1 fresh tomato"], "steps": "Squeeze juice, apply with cotton pad, leave 10 mins, rinse", "why_it_works": "Naturally astringent, reduces sebum over time", "frequency": "Daily", "results_in": "1 week"},
    ],
    "dullness": [
        {"name": "Besan + turmeric glow mask", "ingredients": ["2 tbsp besan", "pinch turmeric", "raw milk or curd"], "steps": "Mix into paste, scrub gently in circles before washing", "why_it_works": "Besan exfoliates naturally, turmeric brightens", "frequency": "Twice a week", "results_in": "Immediate glow"},
        {"name": "Curd + honey mask", "ingredients": ["2 tbsp plain curd", "1 tsp raw honey"], "steps": "Mix, apply 20 mins, rinse lukewarm water", "why_it_works": "Lactic acid brightens, honey locks moisture", "frequency": "3x a week", "results_in": "1 week"},
    ],
    "dry_skin": [
        {"name": "Coconut oil + sugar scrub", "ingredients": ["coconut oil", "brown sugar"], "steps": "Mix 2:1, scrub face gently 2 mins, rinse", "why_it_works": "Sugar exfoliates dry skin, coconut oil moisturises deeply", "frequency": "Once a week", "results_in": "Immediate softness"},
        {"name": "Honey + banana mask", "ingredients": ["half ripe banana", "1 tsp honey", "few drops milk"], "steps": "Mash banana, mix with honey and milk, apply 30 mins", "why_it_works": "Banana potassium hydrates deeply, honey seals moisture", "frequency": "Twice a week", "results_in": "1 week"},
    ],
    "open_pores": [
        {"name": "Egg white + lemon mask", "ingredients": ["1 egg white", "few drops lemon"], "steps": "Whisk together, apply thin layer, let dry 15 mins, rinse cold", "why_it_works": "Egg white tightens pores temporarily", "frequency": "Once a week", "results_in": "Immediate"},
        {"name": "Ice cube massage", "ingredients": ["ice cubes", "soft cloth"], "steps": "Wrap ice in cloth, massage face 2-3 mins every morning", "why_it_works": "Cold constricts pores, reduces puffiness", "frequency": "Every morning", "results_in": "Immediate"},
    ],
    "uneven_texture": [
        {"name": "Rice flour + curd scrub", "ingredients": ["1 tbsp rice flour", "2 tbsp plain curd"], "steps": "Mix, scrub gently 2 mins, leave 5 mins, rinse", "why_it_works": "Rice flour exfoliates physically, curd dissolves dead skin", "frequency": "Twice a week", "results_in": "1-2 weeks"},
    ],
    "sensitivity": [
        {"name": "Aloe vera + cucumber mask", "ingredients": ["aloe vera gel", "cucumber juice"], "steps": "Mix equal parts, apply 20 mins, rinse cold water", "why_it_works": "Both are anti-inflammatory, perfect for reactive skin", "frequency": "Daily if needed", "results_in": "Immediate calm"},
        {"name": "Oat milk compress", "ingredients": ["plain oats", "warm water"], "steps": "Soak oats 10 mins, strain liquid, apply with cotton pad", "why_it_works": "Avenanthramides in oats proven to calm inflammation", "frequency": "Daily", "results_in": "Immediate relief"},
    ],
    "blackheads": [
        {"name": "Baking soda + water scrub", "ingredients": ["1 tsp baking soda", "water"], "steps": "Make paste, gently scrub nose area 1 min, rinse well", "why_it_works": "Mildly abrasive, clears clogged pores", "frequency": "Once a week only", "results_in": "1-2 weeks", "warning": "Don't overdo — can irritate skin"},
        {"name": "Honey + cinnamon nose strip", "ingredients": ["raw honey", "cinnamon"], "steps": "Mix into paste, apply on blackhead areas, press cotton strip, peel after 15 mins", "why_it_works": "Honey antibacterial, cinnamon opens pores", "frequency": "Once a week", "results_in": "1 week"},
    ],
}

# ── Emotion tone guide ────────────────────────────────────────────────────────
EMOTION_TONE = {
    "anger":    "calm, validating, solution-focused. Acknowledge frustration first.",
    "disgust":  "reassuring and understanding.",
    "fear":     "gentle, step-by-step, reassuring. Never overwhelm.",
    "sadness":  "warm, compassionate. Lead with emotional support before advice.",
    "joy":      "match their energy! Be enthusiastic and encouraging.",
    "surprise": "grounding and informative.",
    "neutral":  "warm, friendly, conversational."
}

# ── Emotion detection (using Groq — no heavy packages needed) ─────────────────
def detect_emotion(text: str) -> dict:
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": f"Classify the emotion in this text. Reply with exactly one word from this list: joy, sadness, anger, fear, surprise, disgust, neutral. Text: '{text[:200]}'"
            }],
            max_tokens=5,
            temperature=0
        )
        emotion = response.choices[0].message.content.strip().lower()
        if emotion not in ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]:
            emotion = "neutral"
    except:
        emotion = "neutral"

    return {
        "dominant":      emotion,
        "confidence":    0.85,
        "all_scores":    {emotion: 0.85},
        "is_distressed": emotion in ["anger", "fear", "sadness", "disgust"]
    }

# ── Get remedies for skin profile ─────────────────────────────────────────────
def get_remedies_for_profile(skin_profile: dict) -> list:
    concerns  = skin_profile.get("concerns", [])
    skin_type = skin_profile.get("skin_type", "")
    lookup    = list(concerns)
    if skin_type == "oily" and "oily_skin" not in lookup: lookup.append("oily_skin")
    if skin_type == "dry"  and "dry_skin"  not in lookup: lookup.append("dry_skin")
    remedies = []
    for concern in lookup:
        key = concern.replace("oily_tzone", "oily_skin")
        if key in HOME_REMEDIES:
            remedies.append({"for": concern, "remedies": HOME_REMEDIES[key][:2]})
    return remedies[:3]

# ── Build system prompt ───────────────────────────────────────────────────────
def build_system_prompt(emotion_state: dict, skin_profile: dict, personality: str = "friend") -> str:
    persona    = PERSONALITIES.get(personality, PERSONALITIES["friend"])
    emotion    = emotion_state["dominant"]
    tone       = EMOTION_TONE.get(emotion, EMOTION_TONE["neutral"])
    distressed = emotion_state["is_distressed"]

    skin_context = ""
    if skin_profile.get("skin_type"):
        skin_context += f"\nYou already know their skin type is: {skin_profile['skin_type']}"
    if skin_profile.get("concerns"):
        skin_context += f"\nYou already know their concerns are: {', '.join(skin_profile['concerns'])}"

    remedies_context = ""
    if skin_profile.get("concerns") or skin_profile.get("skin_type"):
        relevant = get_remedies_for_profile(skin_profile)
        if relevant:
            remedies_context = "\n\nRELEVANT HOME REMEDIES YOU CAN SUGGEST:\n"
            for group in relevant:
                remedies_context += f"\nFor {group['for']}:\n"
                for r in group["remedies"]:
                    remedies_context += f"  - {r['name']}: {r['steps']} ({r['why_it_works']})\n"

    distress_instruction = ""
    if distressed:
        distress_instruction = f"""
IMPORTANT: User is emotionally {emotion} right now.
Respond to their FEELINGS first. Only give skincare advice after acknowledging how they feel.
"""

    return f"""
{persona['voice']}

CURRENT USER EMOTION: {emotion} (confidence: {emotion_state['confidence']})
YOUR TONE: {tone}
{distress_instruction}

YOUR MISSION:
1. Make them feel genuinely heard and cared for
2. Learn their skin type and concerns through natural conversation
3. Give home remedies in the style of: {persona['remedy_style']}
4. Recommend products in the style of: {persona['product_style']}
5. Build trust — you genuinely care about them

RULES:
- NEVER ask more than ONE question at a time
- NEVER be robotic — stay in character always
- When suggesting home remedies, explain them simply and why they work
- When recommending products, always say WHY it suits THEIR specific skin
- Mix home remedies and products naturally
- Keep responses conversational, warm, personal
- Remember everything they told you and reference it naturally
{skin_context}

PRODUCTS YOU CAN RECOMMEND:
- Minimalist Niacinamide 10% + Zinc: 599 — oily skin, dark spots, open pores
- Plum Under-Eye Recovery Gel: 795 — dark circles, peptides
- Dot & Key Hyaluronic Moisturiser: 895 — combination/dry skin hydration
- Minimalist SPF 50 PA++++: 399 — daily sun protection, all skin types
- Plum 15% Vitamin C Serum: 845 — dullness, hyperpigmentation
- CeraVe Moisturising Cream: 1200 — sensitive/dry skin, ceramides
- Minimalist Alpha Arbutin 2%: 549 — dark spots, brightening
- Dot & Key 2% BHA Serum: 749 — blackheads, open pores, acne
{remedies_context}

Stay completely in character as {persona['name']}. Never break character. Never say you are an AI.
"""

# ── Main chat function ────────────────────────────────────────────────────────
def chat_with_dermai(
    user_message: str,
    conversation_history: list,
    skin_profile: dict,
    personality: str = "friend"
) -> dict:

    emotion_state = detect_emotion(user_message)
    system_prompt = build_system_prompt(emotion_state, skin_profile, personality)

    messages  = [{"role": "system", "content": system_prompt}]
    messages += conversation_history
    messages += [{"role": "user", "content": user_message}]

    try:
        response   = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.75,
            max_tokens=500,
        )
        reply_text = response.choices[0].message.content
    except Exception as e:
        reply_text = f"Something went wrong: {str(e)}"

    updated_profile               = extract_skin_info(user_message, skin_profile)
    updated_profile["personality"] = personality
    stage           = get_stage(updated_profile, len(conversation_history))
    recommendations = get_recommendations(updated_profile) if stage in ["recommending", "complete"] else []
    remedies        = get_remedies_for_profile(updated_profile) if updated_profile.get("concerns") else []

    return {
        "reply":           reply_text,
        "emotion":         emotion_state,
        "updated_profile": updated_profile,
        "recommendations": recommendations,
        "remedies":        remedies,
        "stage":           stage
    }

# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_skin_info(user_msg: str, current_profile: dict) -> dict:
    profile = dict(current_profile)
    text    = user_msg.lower()

    if not profile.get("personality") or profile.get("personality") == "friend":
        if any(w in text for w in ["be my boyfriend", "like a boyfriend", "as my boyfriend"]):
            profile["personality"] = "boyfriend"
        elif any(w in text for w in ["be my girlfriend", "like a girlfriend", "as my girlfriend"]):
            profile["personality"] = "girlfriend"
        elif any(w in text for w in ["be my sister", "like my sister", "as my sister", "elder sis", "older sis"]):
            profile["personality"] = "sister"
        elif any(w in text for w in ["be my mum", "like my mum", "like my mom", "as my mum", "be my mother"]):
            profile["personality"] = "mum"
        elif any(w in text for w in ["be my brother", "like my brother"]):
            profile["personality"] = "boyfriend"
        elif any(w in text for w in ["like a doctor", "as a doctor", "be my doctor"]):
            profile["personality"] = "doctor"
        elif any(w in text for w in ["just help", "no character", "just a chatbot", "just chat"]):
            profile["personality"] = "neutral"

    if not profile.get("skin_type"):
        if any(w in text for w in ["oily", "greasy", "shiny"]):
            profile["skin_type"] = "oily"
        elif any(w in text for w in ["dry", "flaky", "tight", "peeling", "rough"]):
            profile["skin_type"] = "dry"
        elif any(w in text for w in ["combination", "mixed", "oily nose", "dry cheeks", "t-zone"]):
            profile["skin_type"] = "combination"
        elif any(w in text for w in ["sensitive", "react", "irritat", "red easily"]):
            profile["skin_type"] = "sensitive"

    concerns = set(profile.get("concerns", []))
    keyword_map = {
        "dark_circles":      ["dark circle", "under eye", "eye bag", "puffy eye"],
        "acne":              ["acne", "pimple", "breakout", "zit", "cyst"],
        "hyperpigmentation": ["pigmentation", "dark patch", "melasma"],
        "dark_spots":        ["dark spot", "blemish", "mark", "scar"],
        "open_pores":        ["open pore", "large pore", "visible pore"],
        "dullness":          ["dull", "no glow", "lifeless", "tired looking"],
        "fine_lines":        ["fine line", "wrinkle", "aging"],
        "uneven_texture":    ["uneven", "rough skin", "bumpy"],
        "redness":           ["redness", "red skin", "flushing"],
        "dehydration":       ["dehydrat", "lacks moisture"],
        "blackheads":        ["blackhead", "black dot", "clogged pore"],
        "sensitivity":       ["sensitive skin", "react to everything"],
    }
    for concern, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            concerns.add(concern)
    profile["concerns"] = list(concerns)
    return profile


def get_stage(profile: dict, msg_count: int) -> str:
    has_type     = bool(profile.get("skin_type"))
    has_concerns = len(profile.get("concerns", [])) >= 2
    if has_type and has_concerns and msg_count >= 4:
        return "recommending"
    elif msg_count >= 12:
        return "complete"
    return "gathering_info"


def get_recommendations(profile: dict) -> list:
    PRODUCTS = [
        {"id":"MIN-NIA-01","name":"Niacinamide 10% + Zinc",      "brand":"Minimalist","price":599, "targets":["dark_spots","open_pores","acne","hyperpigmentation"],"skin_types":["oily","combination"]},
        {"id":"DK-HA-01",  "name":"Hyaluronic Moisturiser",       "brand":"Dot & Key", "price":895, "targets":["dehydration","dullness"],                           "skin_types":["dry","combination","sensitive"]},
        {"id":"PLM-EYE-01","name":"Under-Eye Recovery Gel",       "brand":"Plum",      "price":795, "targets":["dark_circles","fine_lines"],                        "skin_types":["all"]},
        {"id":"MIN-SPF-01","name":"SPF 50 Sunscreen PA++++",      "brand":"Minimalist","price":399, "targets":["hyperpigmentation","dark_spots"],                   "skin_types":["all"]},
        {"id":"PLM-VIT-01","name":"15% Vitamin C Serum",          "brand":"Plum",      "price":845, "targets":["hyperpigmentation","dullness","dark_spots"],        "skin_types":["all"]},
        {"id":"CVE-MOI-01","name":"Moisturising Cream",           "brand":"CeraVe",    "price":1200,"targets":["dehydration","sensitivity","redness"],              "skin_types":["sensitive","dry"]},
        {"id":"MIN-ARB-01","name":"Alpha Arbutin 2% + HA",        "brand":"Minimalist","price":549, "targets":["dark_spots","hyperpigmentation","dullness"],        "skin_types":["all"]},
        {"id":"DK-BHA-01", "name":"2% BHA Exfoliating Serum",     "brand":"Dot & Key", "price":749, "targets":["blackheads","open_pores","uneven_texture","acne"],  "skin_types":["oily","combination"]},
    ]
    skin_type = profile.get("skin_type", "")
    concerns  = profile.get("concerns", [])
    scored    = []
    for p in PRODUCTS:
        score  = sum(25 for c in concerns if c in p["targets"])
        score += 20 if ("all" in p["skin_types"] or skin_type in p["skin_types"]) else 0
        if score > 0:
            scored.append({**p, "match_score": min(score, 99)})
    return sorted(scored, key=lambda x: x["match_score"], reverse=True)[:5]
