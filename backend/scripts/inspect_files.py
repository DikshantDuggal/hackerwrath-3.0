import urllib.request
import json

targets = [
    "karanverma19/trilingual_fraud_consumer_protection_v2",
    "anmolshrivastav/scam_ham_india_14_languages",
    "bolewara/hinglish-scam-text-dataset",
    "vikrant-vikram/INDICA",
    "rishia2220/icfd-31k"
]

print("=== DETAILED FILE SIZES AND STRUCTURE ===")
for t in targets:
    url = f"https://huggingface.co/api/datasets/{t}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EdgeRunner-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            siblings = data.get("siblings", [])
            print(f"\n--- {t} ---")
            for s in siblings[:15]:
                print(f"  {s.get('rfilename')} (size: {s.get('size', 'N/A')})")
    except Exception as e:
        print(f"Error for {t}: {e}")
