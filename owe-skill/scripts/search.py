"""
OWE search.py — Ricerca FTS5 sull'indice SQLite (zero token per l'agente)
Usage: python search.py <keyword1> [keyword2] ...

Output:
  FOUND:0  → nessun risultato
  FOUND:N  → N risultati (segue elenco)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _db import get_conn, init_db


def search_code(conn, keywords):
    # FTS5 OR query — keyword1 OR keyword2
    # Column weights: name(3) docstring(2) tags(2) filename(2) parent(1)
    match = " OR ".join(f'"{kw}"' for kw in keywords)
    try:
        rows = conn.execute("""
            SELECT c.path, c.name, c.line, c.end_line, c.docstring,
                   bm25(components_fts, 3.0, 2.0, 2.0, 2.0, 1.0) AS score
            FROM components_fts
            JOIN components c ON c.id = components_fts.rowid
            WHERE components_fts MATCH ?
            ORDER BY score
            LIMIT 50
        """, (match,)).fetchall()
        # bm25 returns negative values: negate for display (higher = better)
        return [(-r['score'], dict(r)) for r in rows]
    except Exception:
        return []


def search_knowledge(conn, keywords):
    # Column weights: domain(2) title(3) content(1)
    match = " OR ".join(f'"{kw}"' for kw in keywords)
    try:
        rows = conn.execute("""
            SELECT k.domain, k.title, k.content,
                   bm25(knowledge_fts, 2.0, 3.0, 1.0) AS score
            FROM knowledge_fts
            JOIN knowledge k ON k.id = knowledge_fts.rowid
            WHERE knowledge_fts MATCH ?
            ORDER BY score
            LIMIT 20
        """, (match,)).fetchall()
        return [(-r['score'], dict(r)) for r in rows]
    except Exception:
        return []


def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py <keyword1> [keyword2] ...")
        sys.exit(1)

    keywords = [k.lower() for k in sys.argv[1:] if len(k) > 1]
    if not keywords:
        print("FOUND:0")
        return

    conn = get_conn()
    init_db(conn)

    code_results      = search_code(conn, keywords)
    knowledge_results = search_knowledge(conn, keywords)

    total = len(code_results) + len(knowledge_results)
    print(f"FOUND:{total}")

    if total == 0:
        print(f"Nessun risultato per: {' '.join(sys.argv[1:])}")
        return

    if code_results:
        print(f"\n--- CODICE ({len(code_results)}) ---")
        for score, c in code_results[:10]:
            doc = c.get("docstring") or ""
            doc_str = f" — {doc[:60]}" if doc else ""
            end = c.get("end_line") or 0
            loc = f"{c['path']}:{c['line']}-{end}" if end > c['line'] else f"{c['path']}:{c['line']}"
            print(f"  [{score:.0f}] {c['name']}{doc_str}")
            print(f"       {loc}")

    if knowledge_results:
        print(f"\n--- CONOSCENZA ({len(knowledge_results)}) ---")
        for score, k in knowledge_results[:10]:
            print(f"  [{score:.0f}] [{k['domain']}] {k['title']}")
            content = k.get("content") or ""
            preview = content[:80]
            if preview:
                print(f"       {preview}{'...' if len(content) > 80 else ''}")


if __name__ == "__main__":
    main()
