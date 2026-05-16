"""
OWE prefs.py — Gestione preferenze utente
Usage:
  python prefs.py --add "testo preferenza"   # Aggiunge una preferenza
  python prefs.py --list                      # Lista tutte le preferenze con ID
  python prefs.py --remove <id>              # Rimuove per ID
  python prefs.py --load                     # Stampa le preferenze (usato dall'agente all'avvio)
"""
import sys, argparse
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from _db import get_conn, init_db


def cmd_add(conn, text):
    text = text.strip()
    if not text:
        print("Errore: il testo della preferenza non puo' essere vuoto.")
        sys.exit(1)
    conn.execute(
        "INSERT INTO preferences(text, added) VALUES (?,?)",
        (text, str(date.today()))
    )
    conn.commit()
    row = conn.execute("SELECT last_insert_rowid()").fetchone()
    print(f"Preferenza aggiunta (ID {row[0]}): {text}")


def cmd_list(conn):
    rows = conn.execute("SELECT id, text, added FROM preferences ORDER BY id").fetchall()
    if not rows:
        print("Nessuna preferenza salvata.")
        return
    print("=== Preferenze OWE ===")
    for r in rows:
        print(f"  [{r['id']}] ({r['added']}) {r['text']}")


def cmd_remove(conn, pref_id):
    conn.execute("DELETE FROM preferences WHERE id=?", (pref_id,))
    removed = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    if removed:
        print(f"Preferenza {pref_id} rimossa.")
    else:
        print(f"Nessuna preferenza trovata con ID {pref_id}.")


def cmd_load(conn):
    """Print all preferences — called by the agent at startup."""
    rows = conn.execute("SELECT text FROM preferences ORDER BY id").fetchall()
    if not rows:
        return
    for r in rows:
        print(r['text'])


def main():
    parser = argparse.ArgumentParser(description="OWE Preferences")
    parser.add_argument("--add",    metavar="TESTO", help="Aggiunge una preferenza")
    parser.add_argument("--list",   action="store_true", help="Lista tutte le preferenze")
    parser.add_argument("--remove", metavar="ID", type=int, help="Rimuove per ID")
    parser.add_argument("--load",   action="store_true",
                        help="Stampa preferenze (per l'agente all'avvio)")
    args = parser.parse_args()

    conn = get_conn()
    init_db(conn)

    if args.add:
        cmd_add(conn, args.add)
    elif args.list:
        cmd_list(conn)
    elif args.remove is not None:
        cmd_remove(conn, args.remove)
    elif args.load:
        cmd_load(conn)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
