"""
OWE census.py — Censimento e gestione componenti
Usage:
  python census.py                          # Scansione completa (setup al primo avvio)
  python census.py --setup                  # Riconfigura cartelle ed estensioni
  python census.py --add PATH NAME LINE DOC # Aggiunge un componente manualmente
  python census.py --remove NAME            # Rimuove un componente per nome
  python census.py --autosync-on            # Attiva autosync
  python census.py --autosync-off           # Disattiva autosync
"""
import os, json, re, sys, argparse
from pathlib import Path
from datetime import date

OWE_DIR = Path.home() / ".owe"
INDEX_PATH = OWE_DIR / "index.json"
CODE_DIR = OWE_DIR / "code"
KNOWLEDGE_DIR = OWE_DIR / "knowledge"
DEFAULT_EXTENSIONS = [".py", ".js", ".ts"]
SKIP_DIRS = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build", ".next", ".nuxt"}


def init_index():
    return {
        "version": 1,
        "staleness_days": 30,
        "autosync": False,
        "scan_paths": [],
        "extensions": DEFAULT_EXTENSIONS,
        "code": {"components": []},
        "knowledge": {"domains": {}}
    }


def load_index():
    if INDEX_PATH.exists():
        with open(INDEX_PATH, encoding="utf-8") as f:
            return json.load(f)
    return init_index()


def save_index(idx):
    OWE_DIR.mkdir(parents=True, exist_ok=True)
    CODE_DIR.mkdir(exist_ok=True)
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)


# --- Extraction ---

def extract_python(path):
    components = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            m = re.match(r'\s*(?:async\s+)?def\s+(\w+)\s*\(', lines[i])
            if m:
                name = m.group(1)
                lineno = i + 1
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
                                # multi-line: grab up to closing quote
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
                components.append({"name": name, "line": lineno, "docstring": docstring[:120]})
            i += 1
    except Exception:
        pass
    return components


def extract_js(path):
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
        return extract_python(path)
    if ext in (".js", ".ts"):
        return extract_js(path)
    return []


# --- Census ---

def ask_replacement_path(original):
    """Interactively ask for a valid replacement path."""
    print(f"\n  Cartella non trovata: {original}")
    print("  Alias accettati: desktop, documents, downloads, home")
    while True:
        raw = input("  Inserisci il percorso corretto (o lascia vuoto per saltare): ").strip()
        if not raw:
            return None
        resolved = os.path.expanduser(normalize_path(raw))
        if os.path.isdir(resolved):
            return normalize_path(raw)  # save portable form
        print(f"  Percorso non trovato: {resolved}. Riprova.")


def run_census(idx):
    paths = list(idx["scan_paths"])  # copy — may be updated during scan
    extensions = idx["extensions"]
    today = str(date.today())
    existing = {(c["path"], c["name"]) for c in idx["code"]["components"]}
    added = 0
    scanned = 0
    updated_paths = []
    for stored_path in paths:
        base = os.path.expanduser(stored_path)
        if not os.path.isdir(base):
            replacement = ask_replacement_path(base)
            if replacement is None:
                print(f"  Cartella saltata: {stored_path}")
                updated_paths.append(stored_path)  # keep old value, user can fix later
                continue
            stored_path = replacement
            base = os.path.expanduser(replacement)
            print(f"  Aggiornato a: {base}")
        updated_paths.append(stored_path)
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
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
                    if key not in existing:
                        existing.add(key)
                        idx["code"]["components"].append({
                            "path": fpath,
                            "name": c["name"],
                            "line": c["line"],
                            "docstring": c["docstring"],
                            "filename": filename,
                            "parent": parent,
                            "tags": [],
                            "added": today,
                            "verified": today
                        })
                        added += 1
    idx["scan_paths"] = updated_paths  # persist any path corrections
    return scanned, added


PATH_ALIASES = {
    "desktop": "~/Desktop",
    "documents": "~/Documents",
    "downloads": "~/Downloads",
    "home": "~",
}


def normalize_path(p):
    """Resolve aliases to portable ~/... paths. Absolute paths kept as-is."""
    p = p.strip()
    lower = p.lower()
    if lower in PATH_ALIASES:
        return PATH_ALIASES[lower]
    # If already absolute, keep it; otherwise make it absolute relative to cwd
    if os.path.isabs(p) or p.startswith("~"):
        return p
    return str(Path(p).resolve())


def normalize_ext(e):
    """Ensure extension starts with dot and has no trailing dots."""
    e = e.strip().rstrip(".")
    return e if e.startswith(".") else "." + e


def setup(idx):
    current_paths = idx.get("scan_paths", [])
    current_exts = idx.get("extensions", DEFAULT_EXTENSIONS)

    print("=== OWE — Configurazione cartelle ===\n")
    print("Alias accettati: desktop, documents, downloads, home")
    if current_paths:
        print(f"Cartelle attuali: {', '.join(current_paths)}")
    raw = input("Cartelle da scansionare (separate da virgola, lascia vuoto per non cambiare): ").strip()
    if raw:
        idx["scan_paths"] = [normalize_path(p) for p in raw.split(",") if p.strip()]

    print(f"Estensioni attuali: {', '.join(current_exts)}")
    ext_raw = input(f"Estensioni (lascia vuoto per non cambiare): ").strip()
    if ext_raw:
        idx["extensions"] = [normalize_ext(e) for e in ext_raw.split(",") if e.strip()]

    return idx["scan_paths"]


# --- CLI ---

def cmd_add(idx, args):
    if len(args) < 4:
        print("Usage: census.py --add PATH NAME LINE DOC")
        sys.exit(1)
    path, name, line, doc = args[0], args[1], int(args[2]), args[3]
    today = str(date.today())
    for c in idx["code"]["components"]:
        if c["path"] == path and c["name"] == name:
            print(f"Componente gia' presente: {name} in {path}")
            return
    idx["code"]["components"].append({
        "path": path, "name": name, "line": line,
        "docstring": doc[:120], "tags": [], "added": today, "verified": today
    })
    save_index(idx)
    print(f"Aggiunto: {name} ({path}:{line})")


def cmd_remove(idx, name):
    before = len(idx["code"]["components"])
    idx["code"]["components"] = [c for c in idx["code"]["components"] if c["name"] != name]
    after = len(idx["code"]["components"])
    removed = before - after
    save_index(idx)
    if removed:
        print(f"Rimossi {removed} componente/i con nome '{name}'")
    else:
        print(f"Nessun componente trovato con nome '{name}'")


def cmd_enrich(idx):
    """Add filename and parent fields to existing components that lack them."""
    enriched = 0
    for c in idx["code"]["components"]:
        if "filename" not in c or "parent" not in c:
            p = c.get("path", "")
            c["filename"] = os.path.splitext(os.path.basename(p))[0]
            c["parent"] = os.path.basename(os.path.dirname(p))
            enriched += 1
    save_index(idx)
    print(f"Arricchiti {enriched} componenti con filename e parent.")


def main():
    parser = argparse.ArgumentParser(description="OWE Census")
    parser.add_argument("--setup", action="store_true", help="Riconfigura cartelle ed estensioni")
    parser.add_argument("--enrich", action="store_true", help="Aggiunge filename/parent ai componenti esistenti")
    parser.add_argument("--add", nargs="+", metavar=("PATH", "NAME"), help="Aggiunge componente")
    parser.add_argument("--remove", metavar="NAME", help="Rimuove componente per nome")
    parser.add_argument("--autosync-on", action="store_true")
    parser.add_argument("--autosync-off", action="store_true")
    args = parser.parse_args()

    idx = load_index()

    if args.autosync_on:
        idx["autosync"] = True
        save_index(idx)
        print("Autosync: ON")
        return

    if args.autosync_off:
        idx["autosync"] = False
        save_index(idx)
        print("Autosync: OFF")
        return

    if args.enrich:
        cmd_enrich(idx)
        return

    if args.add:
        cmd_add(idx, args.add)
        return

    if args.remove:
        cmd_remove(idx, args.remove)
        return

    # Default: full census
    if args.setup or not idx.get("scan_paths"):
        paths = setup(idx)
        if not paths:
            save_index(idx)
            print("Nessuna cartella configurata. Usa: python census.py --setup")
            return

    print(f"Scansione di {len(idx['scan_paths'])} cartelle...")
    scanned, added = run_census(idx)
    save_index(idx)
    total = len(idx["code"]["components"])
    print(f"File scansionati: {scanned} | Nuovi componenti: {added} | Totale: {total}")


if __name__ == "__main__":
    main()
