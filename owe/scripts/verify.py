"""
OWE verify.py — Controlla path stale e conoscenza scaduta
Usage:
  python verify.py           # Report completo
  python verify.py --clean   # Rimuove automaticamente i path non validi
  python verify.py --status  # Dashboard sintetico (per /owe-status)
"""
import json, os, sys
from pathlib import Path
from datetime import date

OWE_DIR = Path.home() / ".owe"
INDEX_PATH = OWE_DIR / "index.json"
KNOWLEDGE_DIR = OWE_DIR / "knowledge"
PREFS_PATH = OWE_DIR / "prefs.json"


def load_index():
    if not INDEX_PATH.exists():
        print("OWE non inizializzato. Lancia prima: python census.py")
        sys.exit(0)
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_index(idx):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)


def verify_code_paths(components):
    stale = [c for c in components if not os.path.exists(c["path"])]
    return stale


def verify_knowledge_staleness(domains, staleness_days):
    today = date.today()
    stale = []
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
            verified_str = n.get("verified") or n.get("added", "")
            if not verified_str:
                continue
            try:
                delta = (today - date.fromisoformat(verified_str)).days
            except ValueError:
                continue
            if delta > staleness_days:
                stale.append((domain, n, delta))
    return stale


def load_prefs():
    if PREFS_PATH.exists():
        try:
            with open(PREFS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"preferences": []}


def main():
    clean = "--clean" in sys.argv
    status_only = "--status" in sys.argv

    idx = load_index()
    staleness_days = idx.get("staleness_days", 30)

    stale_code = verify_code_paths(idx["code"]["components"])
    stale_knowledge = verify_knowledge_staleness(idx["knowledge"]["domains"], staleness_days)
    prefs = load_prefs()

    total_code = len(idx["code"]["components"])
    total_domains = len(idx["knowledge"]["domains"])
    total_prefs = len(prefs.get("preferences", []))
    autosync = idx.get("autosync", False)

    if status_only:
        print("=== OWE STATUS ===")
        print(f"Componenti codice : {total_code}  (path stale: {len(stale_code)})")
        print(f"Domini conoscenza : {total_domains}  (note stale: {len(stale_knowledge)})")
        print(f"Preferenze utente : {total_prefs}")
        print(f"Autosync          : {'ON' if autosync else 'OFF'}")
        print(f"Staleness timeout : {staleness_days} giorni")
        if idx.get("scan_paths"):
            print(f"Cartelle scansionate: {len(idx['scan_paths'])}")
        return

    print("=== OWE — Verifica ===\n")

    # Code paths
    if stale_code:
        print(f"PATH NON PIU' VALIDI ({len(stale_code)}):")
        for c in stale_code:
            print(f"  {c['name']} — {c['path']}")
        if clean:
            invalid = {c["path"] for c in stale_code}
            before = len(idx["code"]["components"])
            idx["code"]["components"] = [c for c in idx["code"]["components"] if c["path"] not in invalid]
            after = len(idx["code"]["components"])
            save_index(idx)
            print(f"  → Rimossi {before - after} componenti con path non validi\n")
        else:
            print("  → Usa --clean per rimuoverli automaticamente\n")
    else:
        print("Tutti i path del codice sono validi.\n")

    # Knowledge staleness
    if stale_knowledge:
        print(f"CONOSCENZA STALE (>{staleness_days} giorni) ({len(stale_knowledge)}):")
        for domain, n, delta in stale_knowledge:
            print(f"  [{domain}] {n.get('title', '?')} — ultima verifica: {delta} giorni fa")
        print("  → Verifica manualmente e aggiorna il campo 'verified' nelle note.\n")
    else:
        print("Tutta la conoscenza e' aggiornata.\n")

    # Summary
    print(f"Totale: {total_code} componenti | {total_domains} domini | {total_prefs} preferenze")
    print(f"Autosync: {'ON' if autosync else 'OFF'} | Staleness: {staleness_days}g")


if __name__ == "__main__":
    main()
