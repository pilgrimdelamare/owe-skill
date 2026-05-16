# OWE — Once Was Enough

> The AI coding agent knows everything. It remembers nothing. OWE fixes that.

**Zero token cost · Persists across sessions · Agent-agnostic**

---

It's 4am. The token counter is spinning like a slot machine and Claude is failing on a problem you've solved a hundred times across a hundred projects. OWE is the fix: a local database that grows with every session, every repo, every agent — turning a perpetual junior into something that actually remembers.

**English** | [Italiano](#italiano)

---

## How it works

```
Task → OWE search (zero tokens) → GitPilfer → Write from scratch
```

Before touching a single file, the agent queries a local SQLite index. If a tested solution exists, it reuses it. If not, it falls through to GitHub search, then writes from scratch. The database grows silently in the background. The more sessions it accumulates, the less the agent has to reinvent.

---

## What gets stored

| Layer | Contents |
|---|---|
| **Code** | Functions indexed by name, docstring, parameters, call graph, and exact line coordinates |
| **Knowledge** | API quirks, dead ends, unexpected behaviors — organized by domain |
| **Preferences** | How you want the agent to behave — loaded into context every session, automatically |

---

## Stack

- **Storage** — SQLite + FTS5 (`~/.owe/owe.db`) — BM25 full-text ranking, zero latency
- **Parsing** — tree-sitter (Python, JS, TS) — exact AST coordinates, not regex guesses
- **Sync** — watchdog file watcher — incremental SQLite updates on every file change
- **Dependencies** — tree-sitter and watchdog auto-install via pip on first run
- **Portability** — Unix and Windows (Git Bash / WSL) — one database, any machine

---

## Installation

### Claude Code

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cp -r owe-skill/owe-skill ~/.claude/skills/
rm -rf owe-skill
```

Add to `~/.claude/CLAUDE.md`:

```
# OWE — Once Was Enough

At the start of every session, before responding:

1. Check if $HOME/.owe/owe.db exists:
   - Not found → tell the user: "[OWE] Database not found. Run: python $HOME/.claude/skills/owe-skill/scripts/census.py"
   - Found → run python $HOME/.claude/skills/owe-skill/scripts/verify.py --status and report as [OWE] <output>

2. Run python $HOME/.claude/skills/owe-skill/scripts/prefs.py --load and keep preferences in context.

Before writing any code: python $HOME/.claude/skills/owe-skill/scripts/search.py keyword1 keyword2
```

OWE activates automatically in every Claude Code session, on every project.

### Windsurf — global

Open **Settings → Cascade → Global Rules** and paste the contents of `owe-skill/SKILL.md`.

### Windsurf — single project

```bash
cat owe-skill/SKILL.md > /path/to/your-project/.windsurfrules
```

### First run

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
```

It asks which folders to scan. From that point on, OWE manages everything automatically.

---

## Census levels

OWE indexes code in three passes. Each pass is additive — run them once after the initial setup.

| Level | Command | What it adds |
|---|---|---|
| **Light** (0) | `census.py` | Function names, docstrings, auto-tags, exact line range |
| **Medium** (1) | `census.py --medium` | Parameters, call graph — what calls what |
| **Heavy** (2) | `census.py --heavy` | File mtime snapshot for coordinate staleness detection |

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
python ~/.claude/skills/owe-skill/scripts/census.py --medium
python ~/.claude/skills/owe-skill/scripts/census.py --heavy
```

> **No file copying.** Heavy census stores only a mtime timestamp in SQLite. Function bodies are read on demand via exact line coordinates (`path:start-end`). Zero disk overhead.

`verify.py --status` shows the breakdown per level at any time.

---

## What the agent does

**At startup — automatically:**

1. Checks `~/.owe/owe.db` exists
2. Runs `verify.py --status` and reports the dashboard
3. Runs `prefs.py --load` and injects preferences into context

**Before every task — automatically:**

1. Searches the local index: `search.py keyword1 keyword2`
2. Reuses what it finds — or falls through to GitPilfer, then scratch

You never run these commands manually.

---

## Scripts

| Script | Purpose |
|---|---|
| `_db.py` | Shared SQLite module — schema, FTS5 triggers, migration |
| `census.py` | Scan and manage components (`--medium`, `--heavy`, `--add`, `--remove`) |
| `search.py` | FTS5 BM25 search — returns `FOUND:N` + ranked results |
| `verify.py` | Check stale paths, stale knowledge, census level breakdown |
| `prefs.py` | User preference CRUD (`--add`, `--list`, `--remove`, `--load`) |
| `export_import.py` | Vault backup and restore via zip |
| `watcher.py` | File watcher — incremental sync on every save |

---

## Slash commands

| Command | Action |
|---|---|
| `/owe-sync` | Re-scan configured folders |
| `/owe-setup` | Reconfigure folders and extensions |
| `/owe-status` | Dashboard: components, knowledge, preferences, census levels, stale entries |
| `/owe-pref` | Add a user preference |
| `/owe-autosync-on` | Add new components without confirmation |
| `/owe-autosync-off` | Revert to asking before adding |
| `/owe-export` | Zip `~/.owe/` to Desktop |
| `/owe-import` | Restore from Desktop zip |

---

## Database structure

```
~/.owe/
├── owe.db          # Everything — components, knowledge, preferences, config
└── knowledge/
    └── <domain>/
        └── notes.json
```

### components table

| Column | Description |
|---|---|
| `path` | Absolute path to the source file |
| `name` | Function or method name |
| `line` / `end_line` | Exact line range — body readable on demand without loading the full file |
| `file_mtime` | Mtime at last heavy census — used to detect stale coordinates |
| `docstring` | First docstring line, truncated to 120 chars |
| `tags` | Auto-generated from name, filename, and parent folder |
| `params` / `calls` | Parameters string and call graph (medium census) |
| `census_level` | 0 = light · 1 = medium · 2 = heavy |

---

## Rules

- **Components** — added with confirmation (silent if `autosync: true`)
- **Knowledge notes** — never added without confirmation
- **Preferences** — never added without confirmation
- **Stale entries** — flagged by `verify.py`, never silently ignored (default threshold: 30 days)

---

## Portability

```bash
python export_import.py --export   # zips ~/.owe/ to Desktop
python export_import.py --import   # restores from Desktop zip (backs up current to ~/.owe.bak/)
```

Transfer via USB or any manual method. No cloud, no sync, no account.

---

## Multi-agent

OWE is agent-agnostic. The same database works on Claude Code, Windsurf, or any agent running on the same machine. The watcher picks up changes from any of them. With `autosync: off` (default), new components are proposed, not silently added.

---

---

## Italiano

> L'agente AI sa tutto. Non ricorda niente. OWE risolve questo.

**Zero token · Persiste tra sessioni · Funziona su qualsiasi agente**

---

Sono le 4 del mattino. Il contatore dei token gira come una slot machine e Claude sta fallendo su un problema che hai risolto cento volte in cento progetti diversi. OWE è la soluzione: un database locale che cresce a ogni sessione, ogni repo, ogni agente — trasformando un eterno junior in qualcosa che finalmente si ricorda.

[English](#owe--once-was-enough) | **Italiano**

---

## Come funziona

```
Task → Ricerca OWE (zero token) → GitPilfer → Scrivi da zero
```

Prima di toccare un singolo file, l'agente interroga un indice SQLite locale. Se esiste una soluzione già testata, la riusa. Se no, passa alla ricerca su GitHub, poi scrive da zero. Il database cresce silenziosamente in background. Più sessioni accumula, meno l'agente deve reinventare.

---

## Cosa viene salvato

| Layer | Contenuto |
|---|---|
| **Codice** | Funzioni indicizzate per nome, docstring, parametri, call graph e coordinate di riga esatte |
| **Conoscenza** | Quirk di API, vicoli ciechi, comportamenti inattesi — organizzati per dominio |
| **Preferenze** | Come vuoi che l'agente si comporti — caricate in context a ogni sessione, in automatico |

---

## Stack

- **Storage** — SQLite + FTS5 (`~/.owe/owe.db`) — ranking BM25, zero latenza
- **Parsing** — tree-sitter (Python, JS, TS) — coordinate AST esatte, non regex
- **Sync** — file watcher watchdog — aggiornamento incrementale SQLite a ogni salvataggio
- **Dipendenze** — tree-sitter e watchdog si auto-installano via pip al primo avvio
- **Portabilita'** — Unix e Windows (Git Bash / WSL) — un database, qualsiasi macchina

---

## Installazione

### Claude Code

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cp -r owe-skill/owe-skill ~/.claude/skills/
rm -rf owe-skill
```

Aggiungi in `~/.claude/CLAUDE.md`:

```
# OWE — Once Was Enough

All'inizio di ogni sessione, prima di rispondere:

1. Controlla se $HOME/.owe/owe.db esiste:
   - Non esiste → di' all'utente: "[OWE] Database non trovato. Esegui: python $HOME/.claude/skills/owe-skill/scripts/census.py"
   - Esiste → esegui python $HOME/.claude/skills/owe-skill/scripts/verify.py --status e riporta come [OWE] <output>

2. Esegui python $HOME/.claude/skills/owe-skill/scripts/prefs.py --load e tieni le preferenze in context.

Prima di scrivere codice: python $HOME/.claude/skills/owe-skill/scripts/search.py keyword1 keyword2
```

OWE si attiva automaticamente in ogni sessione di Claude Code, su qualsiasi progetto.

### Windsurf — globale

Apri **Settings → Cascade → Global Rules** e incolla il contenuto di `owe-skill/SKILL.md`.

### Windsurf — singolo progetto

```bash
cat owe-skill/SKILL.md > /percorso/tuo-progetto/.windsurfrules
```

### Primo avvio

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
```

Chiede quali cartelle scansionare. Da quel momento OWE gestisce tutto in automatico.

---

## Livelli di censimento

OWE indicizza il codice in tre passaggi. Ogni passaggio e' additivo — eseguili una volta dopo il setup iniziale.

| Livello | Comando | Cosa aggiunge |
|---|---|---|
| **Light** (0) | `census.py` | Nomi funzione, docstring, tag automatici, range di riga esatto |
| **Medio** (1) | `census.py --medium` | Parametri, call graph — cosa chiama cosa |
| **Pesante** (2) | `census.py --heavy` | Snapshot mtime per rilevamento staleness delle coordinate |

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
python ~/.claude/skills/owe-skill/scripts/census.py --medium
python ~/.claude/skills/owe-skill/scripts/census.py --heavy
```

> **Nessuna copia di file.** Il censimento pesante salva solo un timestamp mtime in SQLite. I corpi delle funzioni vengono letti su richiesta tramite coordinate di riga esatte (`path:start-end`). Zero overhead su disco.

`verify.py --status` mostra la suddivisione per livello in qualsiasi momento.

---

## Cosa fa l'agente

**All'avvio — in automatico:**

1. Controlla che `~/.owe/owe.db` esista
2. Esegue `verify.py --status` e riporta il dashboard
3. Esegue `prefs.py --load` e inietta le preferenze in context

**Prima di ogni task — in automatico:**

1. Cerca nell'indice locale: `search.py keyword1 keyword2`
2. Riusa quello che trova — o passa a GitPilfer, poi scrive da zero

Non lanci mai questi comandi manualmente.

---

## Script

| Script | Funzione |
|---|---|
| `_db.py` | Modulo SQLite condiviso — schema, trigger FTS5, migrazione |
| `census.py` | Scansione e gestione componenti (`--medium`, `--heavy`, `--add`, `--remove`) |
| `search.py` | Ricerca FTS5 BM25 — restituisce `FOUND:N` + risultati ordinati |
| `verify.py` | Controlla path stale, conoscenza stale, breakdown livelli censimento |
| `prefs.py` | CRUD preferenze utente (`--add`, `--list`, `--remove`, `--load`) |
| `export_import.py` | Backup e ripristino vault via zip |
| `watcher.py` | File watcher — sync incrementale a ogni salvataggio |

---

## Comandi slash

| Comando | Azione |
|---|---|
| `/owe-sync` | Riscansiona le cartelle configurate |
| `/owe-setup` | Riconfigura cartelle ed estensioni |
| `/owe-status` | Dashboard: componenti, conoscenza, preferenze, livelli censimento, entry stale |
| `/owe-pref` | Aggiunge una preferenza utente |
| `/owe-autosync-on` | Aggiunge nuovi componenti senza chiedere conferma |
| `/owe-autosync-off` | Torna a chiedere conferma prima di aggiungere |
| `/owe-export` | Comprime `~/.owe/` sul Desktop |
| `/owe-import` | Ripristina dal zip sul Desktop |

---

## Struttura del database

```
~/.owe/
├── owe.db          # Tutto — componenti, conoscenza, preferenze, config
└── knowledge/
    └── <dominio>/
        └── notes.json
```

### Tabella components

| Colonna | Descrizione |
|---|---|
| `path` | Path assoluto al file sorgente |
| `name` | Nome della funzione o metodo |
| `line` / `end_line` | Range di riga esatto — corpo leggibile su richiesta senza caricare il file intero |
| `file_mtime` | Mtime all'ultimo censimento pesante — usato per rilevare coordinate stale |
| `docstring` | Prima riga di docstring, troncata a 120 char |
| `tags` | Generati automaticamente da nome, filename e cartella padre |
| `params` / `calls` | Stringa parametri e call graph (censimento medio) |
| `census_level` | 0 = light · 1 = medio · 2 = pesante |

---

## Regole

- **Componenti** — aggiunti con conferma (silenzioso se `autosync: true`)
- **Note di conoscenza** — mai aggiunte senza conferma
- **Preferenze** — mai aggiunte senza conferma
- **Entry stale** — segnalate da `verify.py`, mai ignorate silenziosamente (soglia default: 30 giorni)

---

## Portabilita'

```bash
python export_import.py --export   # comprime ~/.owe/ sul Desktop
python export_import.py --import   # ripristina dal zip (backup corrente in ~/.owe.bak/)
```

Trasferimento via USB o metodo manuale a scelta. Niente cloud, niente sync, niente account.

---

## Multi-agente

OWE e' agnostico rispetto all'agente. Lo stesso database funziona su Claude Code, Windsurf o qualsiasi altro agente sulla stessa macchina. Il watcher rileva le modifiche da chiunque. Con `autosync: off` (default), i nuovi componenti vengono proposti, non aggiunti silenziosamente.
