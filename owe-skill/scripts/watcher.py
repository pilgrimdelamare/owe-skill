"""
OWE watcher.py — File watcher con auto-sync incrementale
Usage:
  python watcher.py          # Avvia il watcher in foreground
  python watcher.py --status # Mostra cartelle monitorate e stato autosync

Comportamento:
  - Monitora le cartelle in scan_paths per modifiche a file .py/.js/.ts
  - autosync ON : aggiunge nuovi componenti automaticamente
  - autosync OFF: logga le novita' ma non le aggiunge (propone all'utente)
  - Aggiorna/rimuove componenti per file modificati in ogni caso
"""
import os, sys, json, time, logging
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from _db import get_conn, init_db, cfg_get, cfg_get_json

# Auto-installa watchdog se mancante
def _ensure_watchdog():
    try:
        import watchdog  # noqa
        return True
    except ImportError:
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "watchdog"])
            print("[OWE] watchdog installato automaticamente.")
            return True
        except Exception as e:
            print(f"[OWE] Impossibile installare watchdog: {e}")
            return False

# Auto-installa tree-sitter (necessario per census)
def _ensure_treesitter():
    try:
        import tree_sitter  # noqa
        return True
    except ImportError:
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet",
                                   "tree-sitter", "tree-sitter-python", "tree-sitter-javascript"])
            return True
        except Exception:
            return False


logging.basicConfig(
    level=logging.INFO,
    format="[OWE %(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("owe-watcher")


def _scan_file_incremental(conn, fpath, autosync, today):
    """Re-scan a single file and update SQLite incrementally."""
    # Import extraction functions from census
    from census import scan_file, auto_tags

    ext = os.path.splitext(fpath)[1].lower()
    filename = os.path.splitext(os.path.basename(fpath))[0]
    parent   = os.path.basename(os.path.dirname(fpath))

    # Get current components for this file
    existing_rows = {
        row['name']: row['id']
        for row in conn.execute("SELECT id, name FROM components WHERE path=?", (fpath,))
    }

    # Re-scan
    try:
        fresh = {c['name']: c for c in scan_file(fpath, ext)}
    except Exception:
        return

    fresh_names   = set(fresh)
    existing_names = set(existing_rows)

    removed = existing_names - fresh_names
    added   = fresh_names - existing_names
    updated = fresh_names & existing_names

    # Remove stale components (deleted functions)
    for name in removed:
        conn.execute("DELETE FROM components WHERE id=?", (existing_rows[name],))
        log.info(f"REMOVE {name} <- {fpath}")

    # Update existing (line may have changed)
    for name in updated:
        c = fresh[name]
        conn.execute(
            "UPDATE components SET line=?, end_line=?, docstring=? WHERE id=?",
            (c['line'], c.get('end_line', 0), c.get('docstring', '')[:120], existing_rows[name])
        )

    # Add new components
    for name in added:
        c = fresh[name]
        tags = auto_tags(name, filename, parent)
        if autosync:
            conn.execute(
                """INSERT OR IGNORE INTO components
                   (path,name,line,end_line,docstring,filename,parent,tags,added,verified,census_level)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
                (fpath, name, c['line'], c.get('end_line', 0), c.get('docstring', '')[:120],
                 filename, parent, json.dumps(tags, ensure_ascii=False), today, today)
            )
            log.info(f"ADD    {name} -> {fpath}:{c['line']}")
        else:
            log.info(f"NUOVO  {name} @ {fpath}:{c['line']} (autosync OFF — usa 'census.py --add' per aggiungere)")

    conn.commit()


def build_handler(conn, extensions):
    from watchdog.events import FileSystemEventHandler

    class _Handler(FileSystemEventHandler):
        def _handle(self, fpath):
            ext = os.path.splitext(fpath)[1].lower()
            if ext not in extensions or not os.path.isfile(fpath):
                return
            autosync = cfg_get(conn, "autosync", "false").lower() == "true"
            today    = str(date.today())
            log.info(f"CHANGE {fpath}")
            _scan_file_incremental(conn, fpath, autosync, today)

        def on_modified(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_created(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_deleted(self, event):
            if not event.is_directory:
                ext = os.path.splitext(event.src_path)[1].lower()
                if ext not in extensions:
                    return
                conn.execute("DELETE FROM components WHERE path=?", (event.src_path,))
                conn.commit()
                log.info(f"DELETE {event.src_path}")

    return _Handler()


def cmd_status(conn):
    scan_paths = cfg_get_json(conn, "scan_paths", [])
    autosync   = cfg_get(conn, "autosync", "false").lower() == "true"
    extensions = cfg_get_json(conn, "extensions", [".py", ".js", ".ts"])
    print("=== OWE Watcher ===")
    print(f"Autosync  : {'ON' if autosync else 'OFF'}")
    print(f"Estensioni: {', '.join(extensions)}")
    print(f"Cartelle  : {len(scan_paths)}")
    for p in scan_paths:
        exists = os.path.isdir(os.path.expanduser(p))
        print(f"  {'OK' if exists else 'MANCANTE':8} {p}")


def main():
    if not _ensure_watchdog():
        sys.exit(1)
    _ensure_treesitter()

    from watchdog.observers import Observer

    conn = get_conn()
    init_db(conn)

    if "--status" in sys.argv:
        cmd_status(conn)
        return

    scan_paths = cfg_get_json(conn, "scan_paths", [])
    extensions = set(cfg_get_json(conn, "extensions", [".py", ".js", ".ts"]))
    autosync   = cfg_get(conn, "autosync", "false").lower() == "true"

    if not scan_paths:
        print("Nessuna cartella configurata. Usa: python census.py --setup")
        sys.exit(1)

    handler  = build_handler(conn, extensions)
    observer = Observer()

    watched = []
    for p in scan_paths:
        base = os.path.expanduser(p)
        if os.path.isdir(base):
            observer.schedule(handler, base, recursive=True)
            watched.append(base)
        else:
            log.warning(f"Cartella non trovata, saltata: {base}")

    if not watched:
        print("Nessuna cartella valida da monitorare.")
        sys.exit(1)

    observer.start()
    log.info(f"Watcher avviato — {len(watched)} cartelle | autosync={'ON' if autosync else 'OFF'}")
    for p in watched:
        log.info(f"  Monitorando: {p}")
    log.info("Ctrl+C per fermare.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log.info("Watcher fermato.")
    observer.join()


if __name__ == "__main__":
    main()
