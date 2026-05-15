"""
OWE search.py — Ricerca nell'indice locale (zero token per l'agente)
Usage: python search.py <keyword1> [keyword2] ...

Output:
  FOUND:0  → nessun risultato
  FOUND:N  → N risultati (segue elenco)
"""
import json, sys
from pathlib import Path

OWE_DIR = Path.home() / ".owe"
INDEX_PATH = OWE_DIR / "index.json"
KNOWLEDGE_DIR = OWE_DIR / "knowledge"


def load_index():
    if not INDEX_PATH.exists():
        print("FOUND:0")
        print("OWE non inizializzato. Lancia prima: python census.py")
        sys.exit(0)
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def score_code(component, keywords):
    score = 0
    name = component.get("name", "").lower()
    doc = component.get("docstring", "").lower()
    tags = " ".join(component.get("tags", [])).lower()
    for kw in keywords:
        if kw in name:
            score += 3
        if kw in doc:
            score += 2
        if kw in tags:
            score += 1
    return score


def score_note(domain, note, keywords):
    score = 0
    title = note.get("title", "").lower()
    content = note.get("content", "").lower()
    dom = domain.lower()
    for kw in keywords:
        if kw in dom:
            score += 2
        if kw in title:
            score += 3
        if kw in content:
            score += 1
    return score


def search_code(components, keywords):
    results = []
    for c in components:
        s = score_code(c, keywords)
        if s > 0:
            results.append((s, c))
    results.sort(key=lambda x: -x[0])
    return results


def search_knowledge(domains, keywords):
    results = []
    for domain in domains:
        notes_path = KNOWLEDGE_DIR / domain / "notes.json"
        if not notes_path.exists():
            continue
        try:
            with open(notes_path, encoding="utf-8") as f:
                notes = json.load(f)
        except Exception:
            continue
        for n in notes:
            s = score_note(domain, n, keywords)
            if s > 0:
                results.append((s, domain, n))
    results.sort(key=lambda x: -x[0])
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py <keyword1> [keyword2] ...")
        sys.exit(1)

    keywords = [k.lower() for k in sys.argv[1:]]
    idx = load_index()

    code_results = search_code(idx["code"]["components"], keywords)
    knowledge_results = search_knowledge(idx["knowledge"]["domains"], keywords)

    total = len(code_results) + len(knowledge_results)
    print(f"FOUND:{total}")

    if total == 0:
        print(f"Nessun risultato per: {' '.join(sys.argv[1:])}")
        return

    if code_results:
        print(f"\n--- CODICE ({len(code_results)}) ---")
        for score, c in code_results[:10]:
            doc = c.get("docstring", "")
            doc_str = f" — {doc[:60]}" if doc else ""
            print(f"  [{score}] {c['name']}{doc_str}")
            print(f"       {c['path']}:{c['line']}")

    if knowledge_results:
        print(f"\n--- CONOSCENZA ({len(knowledge_results)}) ---")
        for score, domain, n in knowledge_results[:10]:
            print(f"  [{score}] [{domain}] {n.get('title', '?')}")
            preview = n.get("content", "")[:80]
            if preview:
                print(f"       {preview}{'...' if len(n.get('content','')) > 80 else ''}")


if __name__ == "__main__":
    main()
