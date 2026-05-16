"""
OWE census.py — Censimento e gestione componenti
Usage:
  python census.py                          # Scansione completa (setup al primo avvio)
  python census.py --setup                  # Riconfigura cartelle ed estensioni
  python census.py --add PATH NAME LINE DOC # Aggiunge un componente manualmente
  python census.py --remove NAME            # Rimuove un componente per nome
  python census.py --autosync-on            # Attiva autosync
  python census.py --autosync-off           # Disattiva autosync
  python census.py --enrich                 # Aggiunge tag ai componenti senza tag
"""
import os, json, re, sys, argparse
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from _db import get_conn, init_db, cfg_get, cfg_set, cfg_get_json, cfg_set_json

DEFAULT_EXTENSIONS = [".py", ".js", ".ts"]

SKIP_DIRS = {
    # dipendenze e build
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    "dist", "build", ".next", ".nuxt", ".output", ".cache",
    "vendor", "bower_components", ".turbo", ".vercel",
    # browser / Chrome
    "Default", "Guest Profile", "System Profile",
    "chrome_extensions", "Extensions", "Temp",
    # sistema Windows
    "$RECYCLE.BIN", "System Volume Information",
    "AppData", "ProgramData",
}

SKIP_PATTERNS = [
    re.compile(r'^[a-z0-9]{32}$'),        # Chrome extension IDs
    re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'),  # UUID
]


def should_skip(dirname):
    if dirname in SKIP_DIRS or dirname.startswith("."):
        return True
    return any(p.match(dirname) for p in SKIP_PATTERNS)


# --- Auto-tagging ---

NOISE_WORDS = {
    "get", "set", "is", "has", "on", "do", "run", "use", "new", "old",
    "add", "init", "main", "test", "data", "item", "list", "obj", "val",
    "tmp", "temp", "index", "default", "base", "common", "util", "helper",
    "handler", "manager", "service", "component", "module", "class", "type",
    "fn", "cb", "id", "key", "map", "res", "req", "err", "ctx", "ref",
    "the", "and", "for", "from", "with", "that", "this", "not", "are",
}


def split_name(name):
    """Split camelCase, PascalCase, snake_case, kebab-case into words."""
    words = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    words = re.sub(r'[_\-]', ' ', words)
    return [w.lower() for w in words.split() if len(w) > 2 and w.lower() not in NOISE_WORDS]


def auto_tags(name, filename, parent):
    words = set()
    words.update(split_name(name))
    words.update(split_name(filename))
    words.update(split_name(parent))
    return sorted(w for w in words if not w.isdigit())


# --- Tree-sitter extraction ---

def _ensure_treesitter():
    """Auto-install tree-sitter packages via pip if missing."""
    try:
        import tree_sitter  # noqa
        return True
    except ImportError:
        pass
    import subprocess
    pkgs = ["tree-sitter", "tree-sitter-python", "tree-sitter-javascript"]
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + pkgs)
        print("[OWE] tree-sitter installato automaticamente.")
        return True
    except Exception as e:
        print(f"[OWE] Impossibile installare tree-sitter: {e}. Uso regex come fallback.")
        return False


_parsers = {}


def _get_parser(lang):
    if lang in _parsers:
        return _parsers[lang]
    try:
        from tree_sitter import Language, Parser
        if lang == "python":
            import tree_sitter_python as tsl
        else:  # javascript / typescript
            import tree_sitter_javascript as tsl
        p = Parser(Language(tsl.language()))
        _parsers[lang] = p
        return p
    except Exception:
        return None


def _walk(root):
    """Iterative tree walk — avoids recursion limit on deep ASTs."""
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        for child in reversed(node.children):
            stack.append(child)


def _node_text(node, source_bytes):
    """Extract node text by slicing raw bytes — correct even with multi-byte UTF-8 chars."""
    return source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')


def _py_docstring(func_node, source_bytes):
    body = func_node.child_by_field_name('body')
    if not body:
        return ''
    for stmt in body.children:
        if stmt.type == 'expression_statement':
            for child in stmt.children:
                if child.type == 'string':
                    raw = _node_text(child, source_bytes)
                    for q in ('"""', "'''", '"', "'"):
                        if raw.startswith(q) and raw.endswith(q) and len(raw) > len(q) * 2:
                            return raw[len(q):-len(q)].strip()[:120]
                    return ''
            break
    return ''


def extract_python_ts(path):
    parser = _get_parser("python")
    if parser is None:
        return _extract_python_regex(path)
    try:
        source_bytes = Path(path).read_bytes()
        tree = parser.parse(source_bytes)
        out = []
        for node in _walk(tree.root_node):
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    out.append({
                        'name':      _node_text(name_node, source_bytes),
                        'line':      node.start_point[0] + 1,
                        'docstring': _py_docstring(node, source_bytes),
                    })
        return out
    except Exception:
        return _extract_python_regex(path)


def extract_js_ts(path):
    parser = _get_parser("javascript")
    if parser is None:
        return _extract_js_regex(path)
    try:
        source_bytes = Path(path).read_bytes()
        tree = parser.parse(source_bytes)
        out = []
        seen = set()
        for node in _walk(tree.root_node):
            name = line = None
            if node.type in ('function_declaration', 'generator_function_declaration'):
                n = node.child_by_field_name('name')
                if n:
                    name = _node_text(n, source_bytes)
                    line = node.start_point[0] + 1
            elif node.type == 'variable_declarator':
                val = node.child_by_field_name('value')
                if val and val.type in ('arrow_function', 'function_expression',
                                        'generator_function_expression'):
                    n = node.child_by_field_name('name')
                    if n:
                        name = _node_text(n, source_bytes)
                        line = n.start_point[0] + 1
            elif node.type == 'method_definition':
                n = node.child_by_field_name('name')
                if n:
                    name = _node_text(n, source_bytes)
                    line = node.start_point[0] + 1
            if name and line and name not in ('if', 'for', 'while', 'switch') and name not in seen:
                seen.add(name)
                out.append({'name': name, 'line': line, 'docstring': ''})
        return out
    except Exception:
        return _extract_js_regex(path)


# --- Medium census: params + calls ---

NOISE_CALLS = {
    'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
    'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
    'sum', 'min', 'max', 'abs', 'round', 'open', 'type', 'isinstance',
    'hasattr', 'getattr', 'setattr', 'super', 'repr', 'format', 'vars',
    'dir', 'next', 'iter', 'any', 'all', 'bool', 'bytes', 'chr', 'ord',
    'hex', 'oct', 'bin', 'hash', 'id', 'input', 'exit', 'quit',
    'append', 'extend', 'update', 'get', 'items', 'keys', 'values',
    'join', 'split', 'strip', 'replace', 'format', 'encode', 'decode',
}

JS_NOISE_CALLS = {
    'console', 'log', 'error', 'warn', 'info', 'debug',
    'parseInt', 'parseFloat', 'isNaN', 'isFinite',
    'JSON', 'Math', 'Array', 'Object', 'String', 'Number', 'Boolean',
    'Promise', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval',
    'fetch', 'require', 'exports', 'push', 'pop', 'shift', 'unshift',
    'map', 'filter', 'reduce', 'forEach', 'find', 'findIndex', 'includes',
    'slice', 'splice', 'concat', 'join', 'split', 'trim', 'replace',
    'toString', 'valueOf', 'hasOwnProperty', 'keys', 'values', 'entries',
    'assign', 'freeze', 'resolve', 'reject', 'then', 'catch', 'finally',
}


def _walk_no_nested(node):
    """Walk subtree without entering nested function/class/lambda bodies."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        for child in reversed(n.children):
            if child.type not in ('function_definition', 'class_definition',
                                  'lambda', 'function_declaration',
                                  'arrow_function', 'function_expression'):
                stack.append(child)


def _py_params(func_node, source_bytes):
    """Return raw parameters string, e.g. '(self, name, value=None)'."""
    params_node = func_node.child_by_field_name('parameters')
    if not params_node:
        return '()'
    return _node_text(params_node, source_bytes)


def _py_calls(body_node, source_bytes):
    """Return sorted list of function names called in a Python function body."""
    if not body_node:
        return []
    calls = set()
    for node in _walk_no_nested(body_node):
        if node.type == 'call':
            func = node.child_by_field_name('function')
            if func:
                if func.type == 'identifier':
                    calls.add(_node_text(func, source_bytes))
                elif func.type == 'attribute':
                    attr = func.child_by_field_name('attribute')
                    if attr:
                        calls.add(_node_text(attr, source_bytes))
    return sorted(calls - NOISE_CALLS)


def _js_params(func_node, source_bytes):
    """Return raw parameters string for a JS function node."""
    params_node = func_node.child_by_field_name('parameters') or \
                  func_node.child_by_field_name('formal_parameters')
    if not params_node:
        return '()'
    return _node_text(params_node, source_bytes)


def _js_calls(body_node, source_bytes):
    """Return sorted list of function names called in a JS function body."""
    if not body_node:
        return []
    calls = set()
    for node in _walk_no_nested(body_node):
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func:
                if func.type == 'identifier':
                    calls.add(_node_text(func, source_bytes))
                elif func.type == 'member_expression':
                    prop = func.child_by_field_name('property')
                    if prop:
                        calls.add(_node_text(prop, source_bytes))
    return sorted(calls - JS_NOISE_CALLS)


def _medium_py(path):
    """Extract params + calls for all functions in a Python file.
    Returns dict: function_name -> (params_str, calls_list)"""
    parser = _get_parser("python")
    if parser is None:
        return {}
    try:
        source_bytes = Path(path).read_bytes()
        tree = parser.parse(source_bytes)
        result = {}
        for node in _walk(tree.root_node):
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name   = _node_text(name_node, source_bytes)
                    params = _py_params(node, source_bytes)
                    calls  = _py_calls(node.child_by_field_name('body'), source_bytes)
                    result[name] = (params, calls)
        return result
    except Exception:
        return {}


def _medium_js(path):
    """Extract params + calls for all functions in a JS/TS file.
    Returns dict: function_name -> (params_str, calls_list)"""
    parser = _get_parser("javascript")
    if parser is None:
        return {}
    try:
        source_bytes = Path(path).read_bytes()
        tree = parser.parse(source_bytes)
        result = {}
        for node in _walk(tree.root_node):
            name = body = None
            if node.type in ('function_declaration', 'generator_function_declaration'):
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = _node_text(name_node, source_bytes)
                    body = node.child_by_field_name('body')
                    params = _js_params(node, source_bytes)
            elif node.type == 'variable_declarator':
                val = node.child_by_field_name('value')
                if val and val.type in ('arrow_function', 'function_expression',
                                        'generator_function_expression'):
                    n = node.child_by_field_name('name')
                    if n:
                        name   = _node_text(n, source_bytes)
                        body   = val.child_by_field_name('body')
                        params = _js_params(val, source_bytes)
            elif node.type == 'method_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name   = _node_text(name_node, source_bytes)
                    body   = node.child_by_field_name('body')
                    params = _js_params(node, source_bytes)
            if name and name not in ('if', 'for', 'while', 'switch'):
                calls = _js_calls(body, source_bytes)
                result[name] = (params, calls)
        return result
    except Exception:
        return {}


def census_medium(conn):
    """Upgrade census_level 0 -> 1: add params + calls to each component."""
    import hashlib

    rows = conn.execute(
        "SELECT id, path, name FROM components WHERE census_level < 1"
    ).fetchall()

    # Group by file for efficiency — parse each file once
    by_file = {}
    for row in rows:
        by_file.setdefault(row['path'], []).append(dict(row))

    upgraded = 0
    for fpath, components in by_file.items():
        if not os.path.exists(fpath):
            continue
        ext = os.path.splitext(fpath)[1].lower()
        if ext == '.py':
            info = _medium_py(fpath)
        elif ext in ('.js', '.ts'):
            info = _medium_js(fpath)
        else:
            info = {}

        for comp in components:
            fi = info.get(comp['name'])
            params = json.dumps(fi[0] if fi else [], ensure_ascii=False)
            calls  = json.dumps(fi[1] if fi else [], ensure_ascii=False)
            conn.execute(
                "UPDATE components SET params=?, calls=?, census_level=1 WHERE id=?",
                (params, calls, comp['id'])
            )
            upgraded += 1

    conn.commit()
    return upgraded


def census_heavy(conn):
    """Upgrade census_level 1 -> 2: cache full file content in ~/.owe/code/."""
    import hashlib

    code_dir = Path.home() / ".owe" / "code"
    code_dir.mkdir(exist_ok=True)
    today = str(date.today())

    paths = set(
        row[0] for row in conn.execute(
            "SELECT DISTINCT path FROM components WHERE census_level < 2"
        )
    )

    cached = 0
    for fpath in paths:
        if not os.path.exists(fpath):
            continue
        path_hash  = hashlib.sha256(fpath.encode('utf-8')).hexdigest()
        cache_file = code_dir / f"{path_hash}.json"

        if not cache_file.exists():
            try:
                content = Path(fpath).read_text(encoding='utf-8', errors='ignore')
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({"path": fpath, "content": content,
                               "hash": path_hash, "indexed_at": today},
                              f, ensure_ascii=False)
                cached += 1
            except Exception:
                pass

        conn.execute(
            "UPDATE components SET census_level=2 WHERE path=? AND census_level < 2",
            (fpath,)
        )

    conn.commit()
    return cached, len(paths)


# --- Regex fallbacks ---

def _extract_python_regex(path):
    components = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            m = re.match(r'\s*(?:async\s+)?def\s+(\w+)\s*\(', lines[i])
            if m:
                name = m.group(1)
                docstring = ""
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines):
                    stripped = lines[j].strip()
                    for q in ('"""', "'''", '"', "'"):
                        if stripped.startswith(q):
                            body = stripped[len(q):]
                            if body.endswith(q) and len(body) > 0:
                                docstring = body[:-len(q)].strip()
                            else:
                                parts = [body]
                                j2 = j + 1
                                while j2 < len(lines):
                                    if q in lines[j2]:
                                        parts.append(lines[j2][:lines[j2].index(q)].strip())
                                        break
                                    parts.append(lines[j2].strip())
                                    j2 += 1
                                docstring = " ".join(p for p in parts if p).strip()
                            break
                components.append({"name": name, "line": i + 1, "docstring": docstring[:120]})
            i += 1
    except Exception:
        pass
    return components


def _extract_js_regex(path):
    components = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines()):
            m = re.match(r'\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*[(<]', line)
            if not m:
                m = re.match(r'\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(', line)
            if m:
                name = m.group(1)
                if name not in ("if", "for", "while", "switch"):
                    components.append({"name": name, "line": i + 1, "docstring": ""})
    except Exception:
        pass
    return components


def scan_file(path, ext):
    if ext == ".py":
        return extract_python_ts(path)
    if ext in (".js", ".ts"):
        return extract_js_ts(path)
    return []


# --- Census ---

PATH_ALIASES = {
    "desktop":   "~/Desktop",
    "documents": "~/Documents",
    "downloads": "~/Downloads",
    "home":      "~",
}


def normalize_path(p):
    p = p.strip()
    lower = p.lower()
    if lower in PATH_ALIASES:
        return PATH_ALIASES[lower]
    if os.path.isabs(p) or p.startswith("~"):
        return p
    return str(Path(p).resolve())


def normalize_ext(e):
    e = e.strip().rstrip(".")
    return e if e.startswith(".") else "." + e


def ask_replacement_path(original):
    print(f"\n  Cartella non trovata: {original}")
    print("  Alias accettati: desktop, documents, downloads, home")
    while True:
        raw = input("  Inserisci il percorso corretto (o lascia vuoto per saltare): ").strip()
        if not raw:
            return None
        resolved = os.path.expanduser(normalize_path(raw))
        if os.path.isdir(resolved):
            return normalize_path(raw)
        print(f"  Percorso non trovato: {resolved}. Riprova.")


def run_census(conn):
    scan_paths = cfg_get_json(conn, "scan_paths", [])
    extensions = cfg_get_json(conn, "extensions", DEFAULT_EXTENSIONS)
    today = str(date.today())

    existing = set(
        (row[0], row[1]) for row in conn.execute("SELECT path, name FROM components")
    )

    added = 0
    scanned = 0
    updated_paths = []

    for stored_path in scan_paths:
        base = os.path.expanduser(stored_path)
        if not os.path.isdir(base):
            replacement = ask_replacement_path(base)
            if replacement is None:
                print(f"  Cartella saltata: {stored_path}")
                updated_paths.append(stored_path)
                continue
            stored_path = replacement
            base = os.path.expanduser(replacement)
            print(f"  Aggiornato a: {base}")
        updated_paths.append(stored_path)

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not should_skip(d)]
            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext not in extensions:
                    continue
                fpath = os.path.join(root, fname)
                scanned += 1
                filename = os.path.splitext(fname)[0]
                parent = os.path.basename(root)

                for c in scan_file(fpath, ext):
                    key = (fpath, c["name"])
                    if key in existing:
                        continue
                    existing.add(key)
                    tags = auto_tags(c["name"], filename, parent)
                    conn.execute(
                        """INSERT OR IGNORE INTO components
                           (path,name,line,docstring,filename,parent,tags,added,verified,census_level)
                           VALUES (?,?,?,?,?,?,?,?,?,0)""",
                        (fpath, c["name"], c["line"], c.get("docstring", "")[:120],
                         filename, parent, json.dumps(tags, ensure_ascii=False), today, today)
                    )
                    if conn.execute("SELECT changes()").fetchone()[0]:
                        added += 1

    conn.commit()
    cfg_set_json(conn, "scan_paths", updated_paths)
    return scanned, added


def setup(conn):
    current_paths = cfg_get_json(conn, "scan_paths", [])
    current_exts  = cfg_get_json(conn, "extensions", DEFAULT_EXTENSIONS)

    print("=== OWE — Configurazione cartelle ===\n")
    print("Alias accettati: desktop, documents, downloads, home")
    if current_paths:
        print(f"Cartelle attuali: {', '.join(current_paths)}")
    raw = input("Cartelle da scansionare (separate da virgola, lascia vuoto per non cambiare): ").strip()
    if raw:
        cfg_set_json(conn, "scan_paths", [normalize_path(p) for p in raw.split(",") if p.strip()])

    print(f"Estensioni attuali: {', '.join(current_exts)}")
    ext_raw = input("Estensioni (lascia vuoto per non cambiare): ").strip()
    if ext_raw:
        cfg_set_json(conn, "extensions", [normalize_ext(e) for e in ext_raw.split(",") if e.strip()])


# --- CLI commands ---

def cmd_add(conn, args):
    if len(args) < 4:
        print("Usage: census.py --add PATH NAME LINE DOC")
        sys.exit(1)
    path, name, line, doc = args[0], args[1], int(args[2]), args[3]
    today = str(date.today())
    filename = os.path.splitext(os.path.basename(path))[0]
    parent   = os.path.basename(os.path.dirname(path))
    tags     = auto_tags(name, filename, parent)
    conn.execute(
        """INSERT OR IGNORE INTO components
           (path,name,line,docstring,filename,parent,tags,added,verified,census_level)
           VALUES (?,?,?,?,?,?,?,?,?,0)""",
        (path, name, line, doc[:120], filename, parent,
         json.dumps(tags, ensure_ascii=False), today, today)
    )
    if conn.execute("SELECT changes()").fetchone()[0]:
        conn.commit()
        print(f"Aggiunto: {name} ({path}:{line})")
    else:
        print(f"Componente gia' presente: {name} in {path}")


def cmd_remove(conn, name):
    conn.execute("DELETE FROM components WHERE name=?", (name,))
    removed = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    if removed:
        print(f"Rimossi {removed} componente/i con nome '{name}'")
    else:
        print(f"Nessun componente trovato con nome '{name}'")


def cmd_enrich(conn):
    rows = conn.execute(
        "SELECT id, path, name FROM components WHERE tags='[]' OR tags=''"
    ).fetchall()
    enriched = 0
    for row in rows:
        p = row['path']
        filename = os.path.splitext(os.path.basename(p))[0]
        parent   = os.path.basename(os.path.dirname(p))
        tags     = auto_tags(row['name'], filename, parent)
        conn.execute(
            "UPDATE components SET filename=?, parent=?, tags=? WHERE id=?",
            (filename, parent, json.dumps(tags, ensure_ascii=False), row['id'])
        )
        enriched += 1
    conn.commit()
    print(f"Arricchiti {enriched} componenti con tag automatici.")


def main():
    parser = argparse.ArgumentParser(description="OWE Census")
    parser.add_argument("--setup",        action="store_true")
    parser.add_argument("--enrich",       action="store_true")
    parser.add_argument("--medium",       action="store_true",
                        help="Censimento medio: aggiunge params+calls (livello 0->1)")
    parser.add_argument("--heavy",        action="store_true",
                        help="Censimento pesante: copia file completo in ~/.owe/code/ (livello ->2)")
    parser.add_argument("--add",          nargs="+", metavar=("PATH", "NAME"))
    parser.add_argument("--remove",       metavar="NAME")
    parser.add_argument("--autosync-on",  action="store_true")
    parser.add_argument("--autosync-off", action="store_true")
    args = parser.parse_args()

    _ensure_treesitter()

    conn = get_conn()
    init_db(conn)

    if args.autosync_on:
        cfg_set(conn, "autosync", "true")
        print("Autosync: ON")
        return

    if args.autosync_off:
        cfg_set(conn, "autosync", "false")
        print("Autosync: OFF")
        return

    if args.enrich:
        cmd_enrich(conn)
        return

    if args.medium:
        total = conn.execute("SELECT COUNT(*) FROM components WHERE census_level < 1").fetchone()[0]
        print(f"Censimento medio: {total} componenti da aggiornare...")
        upgraded = census_medium(conn)
        print(f"Aggiornati: {upgraded} componenti al livello 1 (params+calls)")
        return

    if args.heavy:
        total = conn.execute("SELECT COUNT(DISTINCT path) FROM components WHERE census_level < 2").fetchone()[0]
        print(f"Censimento pesante: {total} file da cachare...")
        cached, processed = census_heavy(conn)
        print(f"File cachati: {cached}/{processed} in ~/.owe/code/")
        return

    if args.add:
        cmd_add(conn, args.add)
        return

    if args.remove:
        cmd_remove(conn, args.remove)
        return

    # Default: full census
    scan_paths = cfg_get_json(conn, "scan_paths", [])
    if args.setup or not scan_paths:
        setup(conn)
        scan_paths = cfg_get_json(conn, "scan_paths", [])
        if not scan_paths:
            print("Nessuna cartella configurata. Usa: python census.py --setup")
            return

    print(f"Scansione di {len(scan_paths)} cartelle...")
    scanned, added = run_census(conn)
    total = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    print(f"File scansionati: {scanned} | Nuovi componenti: {added} | Totale: {total}")


if __name__ == "__main__":
    main()
