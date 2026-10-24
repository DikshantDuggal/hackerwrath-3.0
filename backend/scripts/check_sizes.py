import urllib.request

urls = [
    ("trilingual_csv", "https://huggingface.co/datasets/karanverma19/trilingual_fraud_consumer_protection_v2/resolve/main/trilingual_fraud_consumer_protection_v2.csv"),
    ("scam_ham_14_csv", "https://huggingface.co/datasets/anmolshrivastav/scam_ham_india_14_languages/resolve/main/scam_ham_india_14_languages.csv"),
    ("bolewara_json", "https://huggingface.co/datasets/bolewara/hinglish-scam-text-dataset/resolve/main/data.json"),
    ("indica_text_tar", "https://huggingface.co/datasets/vikrant-vikram/INDICA/resolve/main/Text_samples.tar.gz"),
    ("icfd_manifest", "https://huggingface.co/datasets/rishia2220/icfd-31k/resolve/main/dataset_manifest.jsonl"),
    ("icfd_summary", "https://huggingface.co/datasets/rishia2220/icfd-31k/resolve/main/release_summary.json")
]

for label, url in urls:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "EdgeRunner-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            cl = resp.headers.get("Content-Length")
            cl_mb = f"{int(cl) / (1024*1024):.2f} MB" if cl else "Unknown"
            print(f"{label}: {cl_mb} ({resp.status})")
    except Exception as e:
        print(f"{label}: {e}")
