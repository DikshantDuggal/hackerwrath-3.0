"""
Quick Interactive & CLI Tester for EdgeRunners Scam Detection Model.
Usage:
  python scripts/test_query.py "Your custom text to test here"
  python scripts/test_query.py (interactive mode)
"""
import os
import sys

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.rag.classifier import RAGScamClassifier
from app.rag.retriever import get_retriever
from app.rag.schemas import RAGClassificationRequest


def safe_print(text: str):
    """Prints text safely without crashing on Windows cp1252 console."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "backslashreplace").decode("ascii"))


def test_text(classifier: RAGScamClassifier, text: str):
    safe_print("\n" + "=" * 60)
    safe_print(f"INPUT TEXT: \"{text}\"")
    safe_print("=" * 60)
    req = RAGClassificationRequest(text=text, top_k=3, include_retrieved_examples=True)
    res = classifier.classify(req)
    
    safe_print(f"CLASSIFICATION:       {res.classification}")
    safe_print(f"RISK SCORE:           {res.risk_score:.1f} / 100.0")
    safe_print(f"CONFIDENCE:           {res.confidence * 100:.1f}%")
    safe_print(f"FRAUD INDICATORS:     {res.indicators if res.indicators else 'None detected'}")
    safe_print(f"EXPLANATION:          {res.explanation}")
    safe_print(f"INFERENCE LATENCY:    {res.classification_latency_ms:.2f} ms (Retrieval: {res.retrieval_latency_ms:.2f} ms)")
    
    if res.retrieved_examples:
        safe_print("\nTOP SIMILAR MATCHES IN REFERENCE DATABASE:")
        for i, ex in enumerate(res.retrieved_examples, 1):
            safe_print(f"  [{i}] ({ex.label}) Cosine Similarity: {ex.similarity:.4f}")
            safe_print(f"      Text: \"{ex.text[:120]}...\"")
    safe_print("=" * 60)


def main():
    retriever = get_retriever()
    if not retriever.is_ready:
        print("Loading vector index and semantic model...")
        retriever.load()
    classifier = RAGScamClassifier(retriever=retriever)
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        test_text(classifier, query)
    else:
        print("\n=== EdgeRunners Model Interactive Tester ===")
        print("Enter any text or call dialogue to test (type 'exit' or 'quit' to stop):\n")
        while True:
            try:
                user_input = input("Enter text > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    break
                test_text(classifier, user_input)
            except (KeyboardInterrupt, EOFError):
                break
        print("\nExiting.")


if __name__ == "__main__":
    main()
