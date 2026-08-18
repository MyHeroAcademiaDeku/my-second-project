import sys  
import os  
import json  
import shutil  
import traceback  
import urllib.request  
import urllib.parse  
import urllib.error  
  
TARGET = "geo_core.py"  
BACKUP = "geo_core.py.bak"  
MAX_ATTEMPTS = 4  
  
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "  
              "AppleWebKit/537.36 (KHTML, like Gecko) "  
              "Chrome/125.0.0.0 Safari/537.36")  
  
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  
  
  
def request_ai_fix(source_code, error_text):  
    """Sends broken source + traceback to OpenRouter, returns corrected code or None."""  
    key = os.environ.get("OPENROUTER_API_KEY", "")  
    if not key:  
        print("   [Repair debug] No OPENROUTER_API_KEY set; cannot auto-repair.")  
        return None  
  
    prompt = (  
        "The following Python file failed to run. Fix the bug and return ONLY the "  
        "complete corrected file with no explanation and no markdown fences.\n\n"  
        f"--- ERROR ---\n{error_text}\n\n--- SOURCE ---\n{source_code}"  
    )  
    payload = json.dumps({  
        "model": OPENROUTER_MODEL,  
        "messages": [{"role": "user", "content": prompt}],  
    }).encode("utf-8")  
  
    req = urllib.request.Request(  
        "https://openrouter.ai/api/v1/chat/completions",  
        data=payload, method="POST"  
    )  
    req.add_header("Authorization", f"Bearer {key}")  
    req.add_header("Content-Type", "application/json")  
    req.add_header("User-Agent", BROWSER_UA)          # <-- added  
    req.add_header("Accept", "application/json")  
  
    try:  
        with urllib.request.urlopen(req, timeout=60) as response:  
            data = json.loads(response.read().decode("utf-8"))  
            fixed = data["choices"][0]["message"]["content"].strip()  
            # Strip accidental markdown fences if the model adds them.  
            if fixed.startswith("```"):  
                fixed = fixed.split("```", 2)[1]  
                if fixed.lower().startswith("python"):  
                    fixed = fixed[len("python"):]  
            return fixed.strip()  
    except urllib.error.HTTPError as e:  
        try:  
            body = e.read().decode("utf-8")  
        except Exception:  
            body = ""  
        print(f"   [Repair debug] HTTP {e.code}: {body}")  
        return None  
    except Exception as e:  
        print(f"   [Repair debug] {type(e).__name__}: {e}")  
        return None  
  
  
def master_fail_safe_boot():  
    print("=" * 60)  
    print("🛡️  AI SELF-REPAIR SHIELD: INITIALIZING BOOT LOAD")  
    print("=" * 60)  
  
    if not os.path.exists(TARGET):  
        print(f"💥 Error: '{TARGET}' was not found.")  
        return  
  
    shutil.copyfile(TARGET, BACKUP)  
    print(f"💾 Backup saved to '{BACKUP}'.")  
  
    for attempt in range(1, MAX_ATTEMPTS + 1):  
        print(f"\n🕵️  Attempt {attempt}/{MAX_ATTEMPTS}: validating and launching core...")  
        try:  
            with open(TARGET, "r", encoding="utf-8") as f:  
                code_content = f.read()  
            compiled = compile(code_content, TARGET, "exec")  
            exec(compiled, {"__name__": "__main__"})  
            return  # clean exit once the core runs  
        except Exception:  
            error_text = traceback.format_exc()  
            print(f"\n💥 [CRASH INTERCEPTED]:\n{error_text}")  
            if attempt == MAX_ATTEMPTS:  
                print("🛑 Attempts exhausted. Restoring backup.")  
                shutil.copyfile(BACKUP, TARGET)  
                return  
            print("🤖 Requesting an AI fix...")  
            fixed = request_ai_fix(code_content, error_text)  
            if not fixed:  
                print("🛑 No usable fix returned. Restoring backup.")  
                shutil.copyfile(BACKUP, TARGET)  
                return  
            with open(TARGET, "w", encoding="utf-8") as f:  
                f.write(fixed)  
            print("🩹 Wrote AI-patched core. Retrying...")  
  
  
if __name__ == "__main__":  
    master_fail_safe_boot()
