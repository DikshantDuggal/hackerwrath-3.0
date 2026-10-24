import urllib.request

candidates = [
    ("datasets", "agarwalayushi/hinglish"),
    ("datasets", "ggirishg/MultiFraudAlign"),
    ("datasets", "mueller91/MLAAD"),
    ("datasets", "ai4bharat/IndicVoices")
]

for kind, ds in candidates:
    url = f"https://huggingface.co/{kind}/{ds}/raw/main/README.md"
    safe_name = ds.replace("/", "__")
    card_path = f"D:/edgerunner_datasets/cards/{safe_name}_README.md"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EdgeRunner-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[FETCHED] README for {ds} ({len(content)} chars)")
    except Exception as e:
        print(f"[FAIL] README for {ds}: {e}")
