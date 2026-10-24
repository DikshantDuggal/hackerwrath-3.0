import urllib.request
import json
import os

datasets = [
    "vikrant-vikram/INDICA",
    "rishia2220/icfd-31k",
    "karanverma19/trilingual_fraud_consumer_protection_v2",
    "anmolshrivastav/scam_ham_india_14_languages",
    "bolewara/hinglish-scam-text-dataset",
    "sarvamai/samvaad-hi-v1",
    "Horizon-Labs/phishing-scam-detector-base"
]

os.makedirs("D:/edgerunner_datasets/cards", exist_ok=True)

for ds in datasets:
    is_model = "Horizon-Labs" in ds
    base_url = "https://huggingface.co/" if not is_model else "https://huggingface.co/"
    readme_url = f"https://huggingface.co/{'datasets/' if not is_model else ''}{ds}/raw/main/README.md"
    safe_name = ds.replace("/", "__")
    card_path = f"D:/edgerunner_datasets/cards/{safe_name}_README.md"
    
    try:
        req = urllib.request.Request(readme_url, headers={"User-Agent": "EdgeRunner-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[FETCHED] README for {ds} ({len(content)} chars)")
    except Exception as e:
        print(f"[FAIL] README for {ds}: {e}")
