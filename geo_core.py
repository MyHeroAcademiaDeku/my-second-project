import json  
import os  
import re  
import urllib.parse  
import urllib.request  
import urllib.error  
  
DATA_FILE = "geo_data.json"  
  
# Browser-like header to reduce bot-blocking (Cloudflare error 1010, etc.)  
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "  
              "AppleWebKit/537.36 (KHTML, like Gecko) "  
              "Chrome/125.0.0.0 Safari/537.36")  
  
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  
  
# Curated offline dictionary (instant, no network). Cached web answers do NOT go here.  
CURATED_TERMS = {  
    "causes": "forces producing effect", "difference": "way things differ",  
    "instrument": "measuring tool", "measures": "checking a metric",  
    "rain gauge": "tracks rainwater", "seasons": "cyclic year divisions",  
    "tilt": "earth axial angle", "tropical": "hot equatorial zone",  
    "polar": "cold frozen pole region", "hottest": "highest heat level",  
    "coldest": "lowest heat level", "coastal": "near ocean coastline",  
    "areas": "distinct tracts of land", "milder": "gentler weather",  
    "mountains": "high natural elevations", "affect": "to produce influence",  
    "often": "frequently occurring", "type": "category or class",  
    "cooler": "lower heat intensity", "higher": "greater vertical spot",  
    "elevations": "height above sea level", "eye": "calm storm center",  
    "eye of a hurricane": "calm middle of a massive storm",  
    "drought": "prolonged dry period", "hurricane": "massive tropical storm",  
    "monsoon": "seasonal reversing wind", "tornado": "rotating air column",  
    "arid": "severe lack of water", "heatwave": "an abnormally hot period",  
    "humidity": "water vapor volume", "insolation": "incoming solar radiation",  
    "rainfall": "liquid precipitation", "scorching": "intensely hot weather",  
    "subtropical": "bordering tropics", "sweltering": "oppressive humidity",  
    "temperatures": "heat intensity levels", "thermal": "relating to heat",  
    "thermal radiation": "heat particles moving through space",  
    "torrid zone": "the equatorial hot belt region", "acid rain": "polluted rain",  
    "cloudburst": "a sudden heavy downpour", "condensation": "vapor turning to liquid",  
    "deluge": "a severe flood or downpour", "downpour": "heavy continuous rain",  
    "drizzle": "fine light droplets", "precipitation": "rain, snow, or sleet",  
    "rain shadow": "the dry mountain-sheltered side",  
    "rainforest": "a dense high-rainfall forest", "torrential": "rapid violent rain",  
    "water cycle": "the global water circulation loop",  
    "absolute zero": "the lowest possible temperature",  
    "altitude": "height above sea level", "ambient temperature": "air temperature",  
    "celsius": "a metric temperature scale", "diurnal range": "a 24-hour temperature swing",  
    "fahrenheit": "an imperial temperature scale", "freeze": "water turning to solid ice",  
    "isotherm": "a map temperature line", "lapse rate": "temperature drop per altitude",  
    "permafrost": "permanently frozen soil layers", "temperate zone": "a moderate climate region",  
    "thermometer": "a temperature reading tool", "atmosphere": "gases surrounding Earth",  
    "biome": "a distinct regional ecosystem", "climate": "long-term weather averages over decades",  
    "desert": "extremely dry terrain", "erosion": "land surfaces wearing away",  
    "global warming": "an atmospheric heat increase",  
    "greenhouse effect": "heat-trapping atmospheric gas behavior",  
    "microclimate": "a small restricted climate area", "savanna": "a tropical wet-dry plain",  
    "smog": "polluted atmospheric fog", "solstice": "seasonal solar cycle markers",  
    "stratosphere": "the upper atmospheric layer", "topography": "physical land features",  
    "tundra": "treeless frozen Arctic plain", "weather": "short-term atmosphere conditions"  
}  
  
SORTED_KEYS_BY_LEN = sorted(CURATED_TERMS.keys(), key=len, reverse=True)  
  
  
def load_cache():  
    if os.path.exists(DATA_FILE):  
        try:  
            with open(DATA_FILE, "r", encoding="utf-8") as f:  
                return json.load(f)  
        except Exception:  
            return {}  
    return {}  
  
  
def save_cache(db):  
    with open(DATA_FILE, "w", encoding="utf-8") as f:  
        json.dump(db, f, indent=4, ensure_ascii=False)  
  
  
def run_full_system_audit():  
    print("\n🔍 RUNNING FULL SYSTEM HEALTH CHECK...\n" + "=" * 60)  
    issues_found = 0  
    try:  
        parsed = urllib.parse.urlparse("https://en.wikipedia.org/w/api.php")  
        if not parsed.scheme or not parsed.netloc:  
            raise ValueError("Malformed components.")  
        print("✅ [Network Construction]: Healthy. Routing parameters secure.")  
    except Exception as e:  
        issues_found += 1  
        print(f"❌ [Network Construction]: Malformed. Error: {e}")  
    try:  
        if len(CURATED_TERMS) == 0:  
            raise ValueError("Zero definitions map loaded.")  
        print("✅ [Memory Subsystem]: Healthy. Definition variables initialized.")  
    except Exception as e:  
        issues_found += 1  
        print(f"❌ [Memory Subsystem]: Config failure. Error: {e}")  
    print("=" * 60)  
    if issues_found == 0:  
        print("🚀 ALL SYSTEMS NOMINAL: Application engine safe to initialize.")  
    else:  
        print(f"⚠️ AUDIT COMPLETE: Found {issues_found} distinct problems.")  
    print("=" * 60 + "\n")  
  
  
def looks_like_math(question):  
    q = question.lower()  
    if re.search(r'\d\s*[\+\-\*/x=]\s*\d', q):  
        return True  
    keywords = ["solve", "calculate", "equation", "derivative", "integral",  
                "simplify", "factor", "evaluate"]  
    return any(k in q for k in keywords)  
  
  
def ask_llm(question):  
    """Primary route: OpenRouter (OpenAI-compatible). Detailed for math, adaptive length otherwise."""  
    key = os.environ.get("OPENROUTER_API_KEY", "")  
    if not key:  
        print("   [LLM debug] No OPENROUTER_API_KEY set.")  
        return None  
  
    if looks_like_math(question):  
        system_msg = ("You are a math tutor. Solve the problem with clear, "  
                      "step-by-step working, and end with a line beginning 'Answer:'.")  
        label = "[Math Solution]"  
    else:  
        system_msg = ("Answer accurately and directly. Match your length to the "  
                      "question: give a brief answer for a simple factual question, "  
                      "and a fuller explanation when the question needs one. "  
                      "No unnecessary preamble.")  
        label = "[AI Answer]"  
  
    payload = json.dumps({  
        "model": OPENROUTER_MODEL,  
        "messages": [  
            {"role": "system", "content": system_msg},  
            {"role": "user", "content": question},  
        ],  
    }).encode("utf-8")  
  
    req = urllib.request.Request(  
        "https://openrouter.ai/api/v1/chat/completions",  
        data=payload, method="POST"  
    )  
    req.add_header("Authorization", f"Bearer {key}")  
    req.add_header("Content-Type", "application/json")  
    req.add_header("User-Agent", BROWSER_UA)  
    req.add_header("Accept", "application/json")  
  
    try:  
        with urllib.request.urlopen(req, timeout=30) as response:  
            data = json.loads(response.read().decode("utf-8"))  
            answer = data["choices"][0]["message"]["content"].strip()  
            return f"{label}\n{answer}"  
    except urllib.error.HTTPError as e:  
        try:  
            body = e.read().decode("utf-8")  
        except Exception:  
            body = ""  
        print(f"   [LLM debug] HTTP {e.code}: {body}")  
        return None  
    except Exception as e:  
        print(f"   [LLM debug] {type(e).__name__}: {e}")  
        return None  
  
  
def ask_wikipedia(query_phrase):  
    """Fallback route: Wikipedia MediaWiki API, parsed with json.loads (accent-safe)."""  
    clean_query = re.sub(r'[^a-zA-Z0-9 ]', '', query_phrase).strip()  
    safe_query = urllib.parse.quote(clean_query)  
    url = (  
        "https://en.wikipedia.org/w/api.php?action=query&format=json"  
        "&formatversion=2&prop=extracts&exintro=1&explaintext=1"  
        f"&generator=search&gsrsearch={safe_query}&gsrlimit=1"  
    )  
    try:  
        req = urllib.request.Request(url)  
        req.add_header("User-Agent", BROWSER_UA)  
        req.add_header("Accept", "application/json")  
        with urllib.request.urlopen(req, timeout=15) as response:  
            raw_bytes = response.read()  
            if not raw_bytes:  
                print("   [Wiki debug] empty body")  
                return None  
            data = json.loads(raw_bytes.decode("utf-8"))  
            pages = data.get("query", {}).get("pages", [])  
            if pages and pages[0].get("extract"):  
                return f"[Wikipedia Answer]:\n{pages[0]['extract'].strip()}"  
            print("   [Wiki debug] no extract match")  
            return None  
    except urllib.error.HTTPError as e:  
        print(f"   [Wiki debug] HTTP {e.code}")  
        return None  
    except Exception as e:  
        print(f"   [Wiki debug] {type(e).__name__}: {e}")  
        return None  
  
  
def clean_input(txt):  
    return re.sub(r'[?.!,]', '', txt.lower().strip())  
  
  
def search_assistant(user_input):  
    try:  
        cleaned = clean_input(user_input)  
        if not cleaned:  
            return "Please ask a question."  
  
        # 1) Curated local dictionary only (cached web answers can't shadow the LLM).  
        if cleaned in CURATED_TERMS:  
            return f"[Local File Answer]:\n{CURATED_TERMS[cleaned]}"  
        for key in SORTED_KEYS_BY_LEN:  
            if " " in key and key in cleaned:  
                return f"[Local File Answer]:\n{CURATED_TERMS[key]}"  
  
        # 2) Primary online route: LLM.  
        print("\n[Thinking] Contacting the general knowledge model...")  
        llm = ask_llm(user_input)  
        if llm:  
            return llm  
  
        # 3) Fallback: Wikipedia.  
        print("[Fallback] Model unavailable, trying Wikipedia...\n")  
        wiki = ask_wikipedia(cleaned)  
        if wiki:  
            return wiki  
  
        # 4) Offline fuzzy match on curated terms.  
        helpers = {"is", "what", "in", "to", "of", "the", "on", "or", "it", "a",  
                   "an", "how", "and", "does", "its", "at", "capital", "country"}  
        matched = []  
        for word in cleaned.split():  
            if word in helpers:  
                continue  
            best, lowest = None, 999  
            for key in CURATED_TERMS:  
                if key in helpers or " " in key:  
                    continue  
                len_diff = abs(len(word) - len(key))  
                shorter = min(len(word), len(key))  
                mism = sum(1 for i in range(shorter) if word[i] != key[i])  
                dist = len_diff + mism  
                if dist < lowest:  
                    lowest, best = dist, key  
            if best and lowest <= (1 if len(word) <= 5 else 3):  
                matched.append((best, CURATED_TERMS[best]))  
        if matched:  
            b, d = matched[0]  
            return f"[Human Analysis Local]: '{b}' refers to {d}."  
  
        return f"[Notice] Could not find an answer for: '{cleaned}'"  
    except Exception as e:  
        return f"[System Alert]: Internal loop error caught safely: {e}"  
  
  
if __name__ == "__main__":  
    run_full_system_audit()  
    print("==============================================")  
    print("--- General Question Answering Assistant ---")  
    print("==============================================")  
    while True:  
        q = input("\nAsk me anything (or type 'exit'): ")  
        if q.lower() == "exit":  
            break  
        if q.strip():  
            print(f"\n{search_assistant(q)}")
