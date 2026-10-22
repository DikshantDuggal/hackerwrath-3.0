"""
Test paraphrase-multilingual-MiniLM-L12-v2 embedding quality and cross-lingual alignment.
Uses D:\huggingface_cache to utilize the 87+ GB of free disk space on D: drive.
"""
import os
import sys

# Route Hugging Face cache to D: drive
os.environ["HF_HOME"] = r"D:\huggingface_cache"
os.environ["TRANSFORMERS_CACHE"] = r"D:\huggingface_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = r"D:\huggingface_cache"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import time
import numpy as np
from sentence_transformers import SentenceTransformer

def test_multilingual():
    print("Testing sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2...")
    t0 = time.time()
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print(f"Model loaded in {time.time()-t0:.2f}s")
    
    texts = [
        "Your bank account has been blocked immediately. Share your OTP to verify.",
        "आपका बैंक खाता तुरंत ब्लॉक कर दिया गया है। सत्यापित करने के लिए अपना ओटीपी साझा करें।",
        "Never share your OTP with anyone. Bank officials will never ask for it.",
        "किसी के साथ भी अपना ओटीपी साझा न करें। बैंक अधिकारी कभी भी यह नहीं मांगते।",
        "Aapka account freeze ho gaya hai, abhi OTP batao turant."
    ]
    
    t1 = time.time()
    embs = model.encode(texts, convert_to_numpy=True)
    latency = (time.time() - t1) / len(texts) * 1000
    print(f"Embedding shape: {embs.shape}, Average CPU latency: {latency:.2f}ms/sentence")
    
    norms = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    
    sim_eng_hin_scam = float(np.dot(norms[0], norms[1]))
    sim_eng_hing_scam = float(np.dot(norms[0], norms[4]))
    sim_eng_hin_legit = float(np.dot(norms[2], norms[3]))
    sim_scam_vs_legit = float(np.dot(norms[0], norms[2]))
    sim_hin_scam_vs_legit = float(np.dot(norms[1], norms[3]))
    
    print("\n--- Cross-Lingual Alignment Scores ---")
    print(f"English Scam vs Hindi Scam (Devanagari):  {sim_eng_hin_scam:.4f} (Expected > 0.85)")
    print(f"English Scam vs Hinglish Scam (Romanized): {sim_eng_hing_scam:.4f} (Expected > 0.80)")
    print(f"English Legit vs Hindi Legit (Devanagari): {sim_eng_hin_legit:.4f} (Expected > 0.85)")
    print(f"English Scam vs English Legit:             {sim_scam_vs_legit:.4f} (Separation: {sim_eng_hin_scam - sim_scam_vs_legit:+.4f})")
    print(f"Hindi Scam vs Hindi Legit:                 {sim_hin_scam_vs_legit:.4f} (Separation: {sim_eng_hin_scam - sim_hin_scam_vs_legit:+.4f})")

if __name__ == "__main__":
    test_multilingual()
