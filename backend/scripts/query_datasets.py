import urllib.request
import json
import sys

datasets = [
    # Scam / Fraud datasets
    "vikrant-vikram/INDICA",
    "rishia2220/icfd-31k",
    "ggirishg/MultiFraudAlign",
    "karanverma19/trilingual_fraud_consumer_protection_v2",
    "anmolshrivastav/scam_ham_india_14_languages",
    "bolewara/hinglish-scam-text-dataset",
    
    # Speech / Audio datasets
    "ai4bharat/IndicVoices",
    "agarwalayushi/hinglish",
    "sarvamai/samvaad-hi-v1",
    
    # Voice authenticity / Deepfake
    "mueller91/MLAAD"
]

models = [
    "Horizon-Labs/phishing-scam-detector-base"
]

results = {}

print("=== DATASET METADATA QUERY ===")
for ds in datasets:
    url = f"https://huggingface.co/api/datasets/{ds}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EdgeRunner-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            card_data = data.get("cardData", {}) or {}
            siblings = [s.get("rfilename") for s in data.get("siblings", [])]
            info = {
                "id": ds,
                "status": "available",
                "author": data.get("author"),
                "private": data.get("private", False),
                "gated": data.get("gated", False),
                "downloads": data.get("downloads", 0),
                "likes": data.get("likes", 0),
                "license": card_data.get("license", data.get("license", "unspecified")),
                "tags": data.get("tags", []),
                "files_count": len(siblings),
                "sample_files": siblings[:8],
                "description": data.get("description", "")[:200]
            }
            results[ds] = info
            print(f"[OK] {ds}: files={len(siblings)}, license={info['license']}, gated={info['gated']}")
    except urllib.error.HTTPError as e:
        results[ds] = {"id": ds, "status": f"HTTPError {e.code}", "error": str(e)}
        print(f"[FAIL] {ds}: HTTP {e.code}")
    except Exception as e:
        results[ds] = {"id": ds, "status": "Error", "error": str(e)}
        print(f"[FAIL] {ds}: {e}")

print("\n=== MODEL METADATA QUERY ===")
for m in models:
    url = f"https://huggingface.co/api/models/{m}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EdgeRunner-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            card_data = data.get("cardData", {}) or {}
            siblings = [s.get("rfilename") for s in data.get("siblings", [])]
            info = {
                "id": m,
                "status": "available",
                "pipeline_tag": data.get("pipeline_tag"),
                "license": card_data.get("license", "unspecified"),
                "downloads": data.get("downloads", 0),
                "files_count": len(siblings),
                "sample_files": siblings[:8]
            }
            results[m] = info
            print(f"[OK] {m}: files={len(siblings)}, license={info['license']}, pipeline={info['pipeline_tag']}")
    except Exception as e:
        results[m] = {"id": m, "status": "Error", "error": str(e)}
        print(f"[FAIL] {m}: {e}")

with open("D:/edgerunner_datasets/hf_discovery_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print("\nSaved raw metadata to D:/edgerunner_datasets/hf_discovery_raw.json")
