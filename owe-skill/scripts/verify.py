"""
OWE verify.py — Verifica path stale e conoscenza scaduta
Usage:
  python verify.py           # Report completo
  python verify.py --clean   # Rimuove automaticamente i path non validi
  python verify.py --status  # Dashboard sintetico (per /owe-status)
"""
import json, os, sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from _db import get_conn, init_db, cfg_get, cfg_get_json

PREFS_PATH = Path.home() / ".owe" / "prefs.json"


def _prefs_count(conn):
    """Count preferences: DB first, fallback to legacy prefs.json."""
    count = conn.execute("SELECT COUNT(*) FROM preferences").fetchone()[0]
    if count > 0:
        return count
    if PREFS_PATH.exists():
        try:
            with open(PREFS_PATH, encoding="utf-8") as f:
                return len(json.load(f).get("preferences", []))
        except Exception:
            pass
    return 0


def verify_code_paths(conn):
    stale = []
    for row in conn.execute("SELECT id, path, name FROM components"):
        if not os.path.exists(row['path']):
            stale.append(dict(row))
    return stale


def verify_knowledge_staleness(conn, staleness_days):
    today = date.today()
    stale = []
    for row in conn.execute("SELECT domain, title, verified FROM knowledge"):
        verified_str = row['verified'] or ''
        if not verified_str:
            continue
        try:
            delta = (today - date.fromisoformat(verified_str)).days
        except ValueError:
            continue
        if delta > staleness_days:
            stale.append((row['domain'], row['title'], delta))
    return stale


def main():
    clean       = "--clean"  in sys.argv
    status_only = "--status" in sys.argv

    conn = get_conn()
    init_db(conn)

    staleness_days = int(cfg_get(conn, "staleness_days", "30"))
    autosync       = cfg_get(conn, "autosync", "false").lower() == "true"
    scan_paths     = cfg_get_json(conn, "scan_paths", [])

    total_code    = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    total_domains = conn.execute("SELECT COUNT(DISTINCT domain) FROM knowledge WHERE domain != ''").fetchone()[0]
    total_prefs   = _prefs_count(conn)

    stale_code      = verify_code_paths(conn)
    stale_knowledge = verify_knowledge_staleness(conn, staleness_days)

    if status_only:
        print("=== OWE STATUS ===")
        print(f"Componenti codice : {total_code}  (path stale: {len(stale_code)})")
        print(f"Domini conoscenza : {total_domains}  (note stale: {len(stale_knowledge)})")
        print(f"Preferenze utente : {total_prefs}")
        print(f"Autosync          : {'ON' if autosync else 'OFF'}")
        print(f"Staleness timeout : {staleness_days} giorni")
        if scan_paths:
            print(f"Cartelle scansionate: {len(scan_paths)}")
        l0 = conn.execute("SELECT COUNT(*) FROM components WHERE census_level=0").fetchone()[0]
        l1 = conn.execute("SELECT COUNT(*) FROM components WHERE census_level=1").fetchone()[0]
        l2 = conn.execute("SELECT COUNT(*) FROM components WHERE census_level=2").fetchone()[0]
        print(f"Livello censimento: light={l0}  medio={l1}  pesante={l2}")
        return

    print("=== OWE - Verifica ===\n")

    if stale_code:
        print(f"PATH NON PIU' VALIDI ({len(stale_code)}):")
        for c in stale_code:
            print(f"  {c['name']} — {c['path']}")
        if clean:
            for c in stale_code:
                conn.execute("DELETE FROM components WHERE id=?", (c['id'],))
            conn.commit()
            print(f"  → Rimossi {len(stale_code)} componenti con path non validi\n")
        else:
            print("  → Usa --clean per rimuoverli automaticamente\n")
    else:
        print("Tutti i path del codice sono validi.\n")

    if stale_knowledge:
        print(f"CONOSCENZA STALE (>{staleness_days} giorni) ({len(stale_knowledge)}):")
        for domain, title, delta in stale_knowledge:
            print(f"  [{domain}] {title} — ultima verifica: {delta} giorni fa")
        print("  → Verifica manualmente e aggiorna il campo 'verified' nelle note.\n")
    else:
        print("Tutta la conoscenza e' aggiornata.\n")

    print(f"Totale: {total_code} componenti | {total_domains} domini | {total_prefs} preferenze")
    print(f"Autosync: {'ON' if autosync else 'OFF'} | Staleness: {staleness_days}g")


if __name__ == "__main__":
    main()
