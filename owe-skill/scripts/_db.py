"""OWE shared database — SQLite + FTS5.
Schema patterns adapted from github.com/colbymchenry/codegraph (MIT license).
"""
import json, sqlite3
from pathlib import Path

OWE_DIR       = Path.home() / ".owe"
DB_PATH       = OWE_DIR / "owe.db"
INDEX_PATH    = OWE_DIR / "index.json"   # legacy
KNOWLEDGE_DIR = OWE_DIR / "knowledge"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS components (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT    NOT NULL,
    name         TEXT    NOT NULL,
    line         INTEGER DEFAULT 0,
    docstring    TEXT    DEFAULT '',
    filename     TEXT    DEFAULT '',
    parent       TEXT    DEFAULT '',
    tags         TEXT    DEFAULT '[]',
    added        TEXT    DEFAULT '',
    verified     TEXT    DEFAULT '',
    census_level INTEGER DEFAULT 0,
    params       TEXT    DEFAULT '[]',
    calls        TEXT    DEFAULT '[]',
    UNIQUE(path, name)
);

CREATE VIRTUAL TABLE IF NOT EXISTS components_fts USING fts5(
    name, docstring, tags, filename, parent,
    content='components', content_rowid='id',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS comp_ai AFTER INSERT ON components BEGIN
    INSERT INTO components_fts(rowid, name, docstring, tags, filename, parent)
    VALUES (NEW.id, NEW.name, NEW.docstring, NEW.tags, NEW.filename, NEW.parent);
END;
CREATE TRIGGER IF NOT EXISTS comp_ad AFTER DELETE ON components BEGIN
    INSERT INTO components_fts(components_fts, rowid, name, docstring, tags, filename, parent)
    VALUES ('delete', OLD.id, OLD.name, OLD.docstring, OLD.tags, OLD.filename, OLD.parent);
END;
CREATE TRIGGER IF NOT EXISTS comp_au AFTER UPDATE ON components BEGIN
    INSERT INTO components_fts(components_fts, rowid, name, docstring, tags, filename, parent)
    VALUES ('delete', OLD.id, OLD.name, OLD.docstring, OLD.tags, OLD.filename, OLD.parent);
    INSERT INTO components_fts(rowid, name, docstring, tags, filename, parent)
    VALUES (NEW.id, NEW.name, NEW.docstring, NEW.tags, NEW.filename, NEW.parent);
END;

CREATE TABLE IF NOT EXISTS knowledge (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    domain   TEXT DEFAULT '',
    title    TEXT DEFAULT '',
    content  TEXT DEFAULT '',
    added    TEXT DEFAULT '',
    verified TEXT DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    domain, title, content,
    content='knowledge', content_rowid='id',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS know_ai AFTER INSERT ON knowledge BEGIN
    INSERT INTO knowledge_fts(rowid, domain, title, content)
    VALUES (NEW.id, NEW.domain, NEW.title, NEW.content);
END;
CREATE TRIGGER IF NOT EXISTS know_ad AFTER DELETE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, domain, title, content)
    VALUES ('delete', OLD.id, OLD.domain, OLD.title, OLD.content);
END;
CREATE TRIGGER IF NOT EXISTS know_au AFTER UPDATE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, domain, title, content)
    VALUES ('delete', OLD.id, OLD.domain, OLD.title, OLD.content);
    INSERT INTO knowledge_fts(rowid, domain, title, content)
    VALUES (NEW.id, NEW.domain, NEW.title, NEW.content);
END;

CREATE TABLE IF NOT EXISTS preferences (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    text  TEXT,
    added TEXT DEFAULT ''
);
"""

_DEFAULT_CFG = {
    "version":        "2",
    "staleness_days": "30",
    "autosync":       "false",
    "scan_paths":     "[]",
    "extensions":     '[".py", ".js", ".ts"]',
}


def get_conn():
    OWE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn):
    conn.executescript(_SCHEMA)
    for k, v in _DEFAULT_CFG.items():
        conn.execute("INSERT OR IGNORE INTO config(key,value) VALUES (?,?)", (k, v))
    conn.commit()
    _migrate_schema(conn)
    _maybe_migrate(conn)


def _migrate_schema(conn):
    """Add new columns to existing DB if missing (schema evolution)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(components)")}
    added = False
    for col, typedef in [("params", "TEXT DEFAULT '[]'"), ("calls", "TEXT DEFAULT '[]'")]:
        if col not in existing:
            conn.execute(f"ALTER TABLE components ADD COLUMN {col} {typedef}")
            added = True
    if added:
        conn.commit()


# --- Config helpers ---

def cfg_get(conn, key, default=None):
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def cfg_set(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO config(key,value) VALUES (?,?)", (key, str(value)))
    conn.commit()


def cfg_get_json(conn, key, default=None):
    v = cfg_get(conn, key)
    return json.loads(v) if v is not None else default


def cfg_set_json(conn, key, value):
    cfg_set(conn, key, json.dumps(value, ensure_ascii=False))


# --- Migration from index.json ---

def _maybe_migrate(conn):
    """Import index.json into SQLite on first run (runs once)."""
    if not INDEX_PATH.exists():
        return
    count = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    if count > 0:
        return
    try:
        _migrate_json(conn)
    except Exception as e:
        print(f"[OWE] Migrazione fallita: {e}")


def _migrate_json(conn):
    with open(INDEX_PATH, encoding="utf-8") as f:
        idx = json.load(f)

    # Config
    cfg_set(conn, "autosync",       str(idx.get("autosync", False)).lower())
    cfg_set(conn, "staleness_days", str(idx.get("staleness_days", 30)))
    cfg_set_json(conn, "scan_paths",  idx.get("scan_paths", []))
    cfg_set_json(conn, "extensions",  idx.get("extensions", [".py", ".js", ".ts"]))

    # Components — triggers handle FTS sync automatically
    components = idx.get("code", {}).get("components", [])
    imported = 0
    for c in components:
        tags_json = json.dumps(c.get("tags", []), ensure_ascii=False)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO components
                   (path, name, line, docstring, filename, parent, tags, added, verified, census_level)
                   VALUES (?,?,?,?,?,?,?,?,?,0)""",
                (c.get("path", ""), c.get("name", ""), c.get("line", 0),
                 c.get("docstring", "")[:120], c.get("filename", ""),
                 c.get("parent", ""), tags_json,
                 c.get("added", ""), c.get("verified", ""))
            )
            imported += conn.execute("SELECT changes()").fetchone()[0]
        except Exception:
            pass

    # Knowledge from domain note files
    for domain in idx.get("knowledge", {}).get("domains", {}):
        notes_path = KNOWLEDGE_DIR / domain / "notes.json"
        if not notes_path.exists():
            continue
        try:
            with open(notes_path, encoding="utf-8") as f:
                notes = json.load(f)
            for n in notes:
                conn.execute(
                    "INSERT OR IGNORE INTO knowledge(domain,title,content,added,verified) VALUES (?,?,?,?,?)",
                    (domain, n.get("title", ""), n.get("content", ""),
                     n.get("added", ""), n.get("verified", ""))
                )
        except Exception:
            pass

    conn.commit()
    print(f"[OWE] Migrazione index.json -> SQLite: {imported} componenti importati.")
