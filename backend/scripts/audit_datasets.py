"""
Dataset and Environment Audit Script for EdgeRunners
Inspects D:\\Dataset for EdgeRunners\\Text_hindi and Text_english,
checks system resources, dependencies, script detection, duplicates, and model compatibility.
"""
import os
import sys
import glob
import json
import hashlib
import shutil
import platform
import unicodedata
from collections import Counter
from pathlib import Path

def audit_environment():
    print("=" * 60)
    print("1. ENVIRONMENT & SYSTEM AUDIT")
    print("=" * 60)
    print(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    
    # Check ML libraries
    ml_libs = [
        "torch", "sentence_transformers", "transformers", "chromadb", 
        "sklearn", "numpy", "scipy", "fastapi", "uvicorn", "pydantic"
    ]
    lib_status = {}
    for lib in ml_libs:
        try:
            mod = __import__(lib)
            ver = getattr(mod, "__version__", "installed")
            lib_status[lib] = ver
        except ImportError as e:
            lib_status[lib] = f"MISSING ({e})"
    print("Installed ML Dependencies:")
    for k, v in lib_status.items():
        print(f"  - {k}: {v}")
        
    # Check GPU / PyTorch
    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_avail else 0
        device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU Only"
        print(f"PyTorch CUDA Available: {cuda_avail} (Devices: {device_count}, Name: {device_name})")
    except Exception as e:
        print(f"PyTorch check error: {e}")
        
    # Check Disk Space
    for drive in ["C:\\", "D:\\"]:
        if os.path.exists(drive):
            total, used, free = shutil.disk_usage(drive)
            print(f"Disk {drive}: Total={total//(1024**3)} GB, Used={used//(1024**3)} GB, Free={free//(1024**3)} GB")

def inspect_directory_deep(dir_path, name):
    print("\n" + "=" * 60)
    print(f"2. DATASET DEEP AUDIT: {name} ({dir_path})")
    print("=" * 60)
    
    if not os.path.exists(dir_path):
        print(f"ERROR: Directory {dir_path} does not exist!")
        return None
        
    categories = ["legit", "scam"]
    results = {
        "name": name,
        "path": dir_path,
        "categories": {},
        "total_files": 0,
        "empty_files": 0,
        "extensions": Counter(),
        "scripts": Counter(),
        "file_sizes": [],
        "char_lengths": [],
        "hashes": {},
        "file_names": set(),
        "samples": []
    }
    
    # Also look for any non-category files directly in dir_path
    root_files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
    if root_files:
        print(f"Found {len(root_files)} files in dataset root directory: {root_files[:10]}")
        
    for cat in categories:
        cat_dir = os.path.join(dir_path, cat)
        if not os.path.isdir(cat_dir):
            print(f"Category folder missing: {cat_dir}")
            continue
            
        files = os.listdir(cat_dir)
        results["categories"][cat] = len(files)
        results["total_files"] += len(files)
        
        for idx, fname in enumerate(files):
            fpath = os.path.join(cat_dir, fname)
            ext = os.path.splitext(fname)[1].lower()
            results["extensions"][ext] += 1
            results["file_names"].add(fname)
            
            try:
                sz = os.path.getsize(fpath)
                results["file_sizes"].append(sz)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f_in:
                    content = f_in.read()
            except Exception as e:
                results["empty_files"] += 1
                continue
                
            stripped = content.strip()
            if not stripped:
                results["empty_files"] += 1
                continue
                
            results["char_lengths"].append(len(stripped))
            h = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
            results["hashes"].setdefault(h, []).append((cat, fname))
            
            # Detect script distribution
            devanagari_chars = sum(1 for c in stripped if 0x0900 <= ord(c) <= 0x097F)
            latin_chars = sum(1 for c in stripped if ("a" <= c <= "z" or "A" <= c <= "Z"))
            
            if devanagari_chars > 0 and latin_chars == 0:
                script_type = "Pure_Devanagari"
            elif devanagari_chars > 0 and latin_chars > 0:
                # If mostly Devanagari with a few English words vs mostly Latin
                ratio = devanagari_chars / (devanagari_chars + latin_chars)
                if ratio > 0.5:
                    script_type = "Mixed_Devanagari_Dominant"
                else:
                    script_type = "Mixed_Latin_Dominant"
            elif latin_chars > 0 and devanagari_chars == 0:
                script_type = "Pure_Latin_Script"
            else:
                script_type = "Other/Numeric"
                
            results["scripts"][script_type] += 1
            
            # Sample for inspection
            if len(results["samples"]) < 6 and idx % 200 == 0:
                clean_sample = " ".join(stripped.split())
                results["samples"].append({
                    "category": cat,
                    "filename": fname,
                    "script_type": script_type,
                    "length": len(stripped),
                    "preview": clean_sample[:150]
                })

    total = results["total_files"]
    unique_content = len(results["hashes"])
    dup_count = total - unique_content
    dup_pct = (dup_count / total * 100) if total > 0 else 0
    
    print(f"Total Files: {total}")
    print(f"Category Breakdown: {results['categories']}")
    print(f"Extensions: {dict(results['extensions'])}")
    print(f"Empty Files: {results['empty_files']}")
    print(f"Unique Content Records: {unique_content}")
    print(f"Duplicate Files: {dup_count} ({dup_pct:.2f}%)")
    print(f"Script Classification:")
    for s_type, cnt in results["scripts"].items():
        print(f"  - {s_type}: {cnt} ({cnt/total*100:.2f}%)")
        
    if results["char_lengths"]:
        avg_len = sum(results["char_lengths"]) / len(results["char_lengths"])
        min_len = min(results["char_lengths"])
        max_len = max(results["char_lengths"])
        print(f"Character Length: Min={min_len}, Avg={avg_len:.1f}, Max={max_len}")
        
    print("\nText Samples:")
    for s in results["samples"]:
        # Use ascii-safe repr for preview to prevent Windows console cp1252 crash
        preview_safe = s['preview'].encode('ascii', 'backslashreplace').decode('ascii')
        print(f"  [{s['category'].upper()}] ({s['script_type']}) {s['filename']}:\n    \"{preview_safe}\"")
        
    return results

def check_cross_dataset_overlap(hindi_res, eng_res):
    print("\n" + "=" * 60)
    print("3. CROSS-DATASET COMPARISON & OVERLAP AUDIT")
    print("=" * 60)
    if not hindi_res or not eng_res:
        print("Skipping cross comparison - missing dataset.")
        return
        
    common_filenames = hindi_res["file_names"].intersection(eng_res["file_names"])
    print(f"Total English Files: {eng_res['total_files']}")
    print(f"Total Hindi Files: {hindi_res['total_files']}")
    print(f"Identical Filenames in both datasets: {len(common_filenames)}")
    if common_filenames:
        pct = len(common_filenames) / max(len(hindi_res["file_names"]), 1) * 100
        print(f"Filename Overlap Rate: {pct:.2f}%")
        sample_common = list(common_filenames)[:5]
        print(f"Sample common filenames: {sample_common}")
        
    # Check if exact text matches between English and Hindi
    common_hashes = set(hindi_res["hashes"].keys()).intersection(set(eng_res["hashes"].keys()))
    print(f"Identical Text Content SHA-256 Hashes: {len(common_hashes)}")
    if common_hashes:
        print("WARNING: Some Hindi files contain exact English text (untranslated)!")

def test_multilingual_embedding_compatibility():
    print("\n" + "=" * 60)
    print("4. EMBEDDING MODEL COMPATIBILITY TEST")
    print("=" * 60)
    import time
    
    test_texts = [
        "Dear customer, your bank account has been blocked. Please verify your OTP immediately.",
        "प्रिय ग्राहक, आपका बैंक खाता ब्लॉक कर दिया गया है। कृपया तुरंत अपना ओटीपी सत्यापित करें।",
        "Aapka account freeze ho gaya hai. Abhi payment verify karein.",
        "Never share your OTP or CVV with anyone. Stay alert.",
        "kisi ke sath apna OTP share na karein, ye bank ki taraf se nahi hai."
    ]
    
    models_to_test = [
        ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2"),
        ("paraphrase-multilingual-MiniLM-L12-v2", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    ]
    
    for short_name, hf_name in models_to_test:
        print(f"\nTesting model: {short_name}")
        t0 = time.time()
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(hf_name)
            load_time = time.time() - t0
            print(f"  Model load time: {load_time:.2f}s")
            
            t1 = time.time()
            embeddings = model.encode(test_texts, convert_to_numpy=True)
            encode_time = (time.time() - t1) / len(test_texts) * 1000
            print(f"  Embedding shape: {embeddings.shape}")
            print(f"  Average inference latency per text (CPU): {encode_time:.2f}ms")
            
            # Compute cosine similarity between English scam and Hindi scam
            import numpy as np
            norm_emb = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            eng_scam = norm_emb[0]
            hin_scam = norm_emb[1]
            hing_scam = norm_emb[2]
            eng_legit = norm_emb[3]
            hin_legit = norm_emb[4]
            
            sim_eng_hin_scam = float(np.dot(eng_scam, hin_scam))
            sim_eng_hing_scam = float(np.dot(eng_scam, hing_scam))
            sim_scam_legit = float(np.dot(eng_scam, eng_legit))
            sim_hin_scam_legit = float(np.dot(hin_scam, hin_legit))
            
            print(f"  Similarity [Eng Scam <-> Hin Scam (Devanagari)]: {sim_eng_hin_scam:.4f}")
            print(f"  Similarity [Eng Scam <-> Hinglish Scam]:         {sim_eng_hing_scam:.4f}")
            print(f"  Similarity [Eng Scam <-> Eng Legit (Advisory)]:  {sim_scam_legit:.4f}")
            print(f"  Similarity [Hin Scam <-> Hin Legit (Advisory)]:  {sim_hin_scam_legit:.4f}")
        except Exception as e:
            print(f"  Error loading/testing {short_name}: {e}")

if __name__ == "__main__":
    audit_environment()
    hindi_res = inspect_directory_deep(r"D:\Dataset for EdgeRunners\Text_hindi", "Text_hindi")
    eng_res = inspect_directory_deep(r"D:\Dataset for EdgeRunners\Text_english", "Text_english")
    check_cross_dataset_overlap(hindi_res, eng_res)
    test_multilingual_embedding_compatibility()
