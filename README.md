# OWE — Once Was Enough

> A local knowledge and code cache for AI coding agents. What the agent learns once, it remembers forever.

It's 4am, the world is asleep and someone is banging their head against the wall. That's you, while the token counter spins like a slot machine and Claude keeps failing on a problem you've solved 1000 times across 1000 projects. He knows everything, but remembers nothing. OWE fixes this: it creates a local database where the agent accumulates tested code, acquired knowledge and your preferences, session after session, repo after repo. And the more experience it accumulates, the more performant it becomes — going from junior to finally senior developer.

**English** | [Italiano](#italiano)

---

## What is OWE?

OWE is a global skill for AI coding agents (Claude Code, Windsurf, and others) that builds and queries a local database of:

- **Tested code** — functions and components indexed by name, docstring, parameters and call graph
- **Acquired knowledge** — API quirks, dead ends, unexpected behaviors, organized by domain
- **User preferences** — how you want the agent to behave, loaded into context on every session

The agent consults the database automatically before writing any code. You do nothing manually.

## How it works

**Task → OWE search (automatic) → [GitPilfer](https://github.com/pilgrimdelamare/GitPilfer) → Write from scratch**

Before writing any code, the agent searches the local SQLite index at zero token cost. If something useful exists, it reuses it. If not, it falls through to GitHub search or writes from scratch.

The database grows over time. The more sessions it accumulates, the more efficient the agent becomes.

## Stack

- **Language:** Python 3
- **Storage:** SQLite + FTS5 (`~/.owe/owe.db`) — full-text search with BM25 ranking
- **File cache:** `~/.owe/code/` — full file content, indexed by path hash
- **Code parsing:** tree-sitter (auto-installed via pip on first run)
- **File watcher:** watchdog (auto-installed via pip on first run)
- **Compatible with:** Unix, Windows (Git Bash / WSL)

## Installation

### Claude Code

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cp -r owe-skill/owe-skill ~/.claude/skills/
rm -rf owe-skill
```

Then add the following to `~/.claude/CLAUDE.md`:

```
# OWE — Once Was Enough

All'inizio di ogni sessione, prima di rispondere:

1. Controlla se $HOME/.owe/owe.db esiste:
   - Non esiste → di' all'utente: "[OWE] Database non trovato. Esegui: python $HOME/.claude/skills/owe-skill/scripts/census.py"
   - Esiste → esegui python $HOME/.claude/skills/owe-skill/scripts/verify.py --status e riporta come [OWE] <output>

2. Esegui python $HOME/.claude/skills/owe-skill/scripts/prefs.py --load e tieni le preferenze in context.

Prima di scrivere codice: python $HOME/.claude/skills/owe-skill/scripts/search.py keyword1 keyword2
```

OWE activates automatically in every Claude Code session on any project.

### Windsurf — global (all projects)

Open **Settings → Cascade → Global Rules** and paste the contents of `owe-skill/SKILL.md`.

### Windsurf — single project

```bash
cat owe-skill/SKILL.md > /path/to/your-project/.windsurfrules
```

### First run

After installing, run the initial census once:

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
```

It will ask which folders to scan. From that point on, OWE manages everything automatically.

## Census levels

OWE analyzes code at three levels of depth:

| Level | Command | What it extracts |
|---|---|---|
| **Light** (0) | `census.py` (default) | Function names, docstrings, auto-tags |
| **Medium** (1) | `census.py --medium` | Parameters, call graph (what calls what) |
| **Heavy** (2) | `census.py --heavy` | Full file content cached to `~/.owe/code/` |

Run all three after the initial census to fully populate the database:

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
python ~/.claude/skills/owe-skill/scripts/census.py --medium
python ~/.claude/skills/owe-skill/scripts/census.py --heavy
```

`verify.py --status` shows how many components are at each level.

## What the agent does automatically

**At startup:**

1. Checks that `~/.owe/owe.db` exists
2. Runs `verify.py --status` and reports the dashboard
3. Runs `prefs.py --load` and loads preferences into context

**Before each task:**

1. Searches the local index: `search.py keyword1 keyword2`
2. Reuses what it finds, or falls through to GitPilfer, then writes from scratch

You never run search commands manually.

## Scripts

| Script | Purpose |
|---|---|
| `_db.py` | Shared SQLite module (schema, FTS5, migration) |
| `census.py` | Scan + component management (`--medium`, `--heavy`, `--add`, `--remove`) |
| `search.py` | FTS5 search with BM25 ranking (zero agent tokens) |
| `verify.py` | Check stale paths, outdated knowledge, census levels |
| `prefs.py` | User preference CRUD (`--add`, `--list`, `--remove`, `--load`) |
| `export_import.py` | Vault backup/restore via zip |
| `watcher.py` | File watcher for incremental auto-sync |

## Slash commands

| Command | Action |
|---|---|
| `/owe-sync` | Re-scan configured folders |
| `/owe-setup` | Reconfigure folders and extensions |
| `/owe-status` | Dashboard: components, domains, preferences, census levels, stale entries |
| `/owe-pref` | Add a user preference |
| `/owe-autosync-on` | Auto-add new components without confirmation |
| `/owe-autosync-off` | Revert to asking before adding |
| `/owe-export` | Zip `~/.owe/` to Desktop |
| `/owe-import` | Restore from Desktop zip |

## Database structure

```
~/.owe/
├── owe.db              # SQLite database (components + knowledge + prefs + config)
│                       # FTS5 indexes on components and knowledge
├── code/               # Heavy cache: one JSON per file, named by path hash
│   └── <sha256>.json   # { path, content, indexed_at } — never overwritten
└── knowledge/
    └── <domain>/
        └── notes.json  # Notes per domain (redis, firebase, etc.)
```

### SQLite tables

| Table | Contents |
|---|---|
| `components` | path, name, line, docstring, filename, parent, tags, params, calls, census_level |
| `components_fts` | FTS5 virtual table (content mirror of components) |
| `knowledge` | domain, title, content, added, verified |
| `knowledge_fts` | FTS5 virtual table (content mirror of knowledge) |
| `preferences` | id, text, added |
| `config` | key/value: autosync, scan_paths, extensions, staleness_days |

## Portability

The database lives at `~/.owe/` — local, hidden, no remote sync.

```bash
python export_import.py --export   # zips ~/.owe/ to Desktop
python export_import.py --import   # restores from Desktop zip (backs up current to ~/.owe.bak/)
```

Transfer via USB or any manual method.

## Multi-agent

OWE is agent-agnostic. It works the same on Claude Code, Windsurf, or any agent on the same machine. When an agent finds new unregistered components, it proposes adding them. With `autosync: true`, this happens silently.

## Rules

- Components: added with user confirmation (silent if `autosync: true`)
- Knowledge notes: **never** added without confirmation
- User preferences: **never** added without confirmation
- Stale entries (default threshold: 30 days): flagged, not ignored

---

## Italiano

> Un database locale di codice e conoscenza per agenti AI. Quello che l'agente impara una volta, lo ricorda per sempre.

Sono le 4 am, il mondo dorme e una persona sbatte la testa contro il muro. Sei tu, mentre il contatore dei token gira come una slot machine e Claude continua a fallire su un problema che avete risolto 1000 volte su 1000 progetti. Lui sa tutto, ma non si ricorda niente. OWE risolve questo: crea un database locale dove l'agente accumula codice testato, conoscenza acquisita e le tue preferenze, sessione dopo sessione, repo dopo repo. E più accumula esperienza più diventa performante, passando da junior a finalmente senior developer.

[English](#owe--once-was-enough) | **Italiano**

---

## Cos'è OWE?

OWE è una skill globale per agenti AI (Claude Code, Windsurf e altri) che costruisce e consulta un database locale di:

- **Codice testato** — funzioni e componenti indicizzati per nome, docstring, parametri e call graph
- **Conoscenza acquisita** — quirk di API, vicoli ciechi, comportamenti inattesi, organizzati per dominio
- **Preferenze utente** — come vuoi che l'agente si comporti, caricate in context ad ogni sessione

L'agente consulta il database automaticamente prima di scrivere qualsiasi codice. L'utente non fa nulla manualmente.

## Come funziona

**Task → Ricerca OWE (automatica) → [GitPilfer](https://github.com/pilgrimdelamare/GitPilfer) → Scrivi da zero**

Prima di scrivere qualsiasi codice, l'agente cerca nell'indice SQLite locale a costo zero di token. Se trova qualcosa di utile lo riusa, altrimenti passa al livello successivo.

Il database cresce nel tempo. Più sessioni accumula, più l'agente diventa efficiente.

## Stack

- **Linguaggio:** Python 3
- **Storage:** SQLite + FTS5 (`~/.owe/owe.db`) — ricerca full-text con ranking BM25
- **Cache file:** `~/.owe/code/` — contenuto completo dei file, indicizzato per hash del path
- **Parsing codice:** tree-sitter (auto-installato via pip al primo avvio)
- **File watcher:** watchdog (auto-installato via pip al primo avvio)
- **Compatibile con:** Unix, Windows (Git Bash / WSL)

## Installazione

### Claude Code

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cp -r owe-skill/owe-skill ~/.claude/skills/
rm -rf owe-skill
```

Poi aggiungi in `~/.claude/CLAUDE.md`:

```
# OWE — Once Was Enough

All'inizio di ogni sessione, prima di rispondere:

1. Controlla se $HOME/.owe/owe.db esiste:
   - Non esiste → di' all'utente: "[OWE] Database non trovato. Esegui: python $HOME/.claude/skills/owe-skill/scripts/census.py"
   - Esiste → esegui python $HOME/.claude/skills/owe-skill/scripts/verify.py --status e riporta come [OWE] <output>

2. Esegui python $HOME/.claude/skills/owe-skill/scripts/prefs.py --load e tieni le preferenze in context.

Prima di scrivere codice: python $HOME/.claude/skills/owe-skill/scripts/search.py keyword1 keyword2
```

OWE si attiva automaticamente in ogni sessione di Claude Code su qualsiasi progetto.

### Windsurf — globale (tutti i progetti)

Apri **Settings → Cascade → Global Rules** e incolla il contenuto di `owe-skill/SKILL.md`.

### Windsurf — singolo progetto

```bash
cat owe-skill/SKILL.md > /percorso/tuo-progetto/.windsurfrules
```

### Primo avvio

Dopo l'installazione, esegui il censimento iniziale una volta sola:

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
```

Chiederà quali cartelle scansionare. Da quel momento OWE gestisce tutto automaticamente.

## Livelli di censimento

OWE analizza il codice a tre livelli di profondita':

| Livello | Comando | Cosa estrae |
|---|---|---|
| **Light** (0) | `census.py` (default) | Nomi funzione, docstring, tag automatici |
| **Medio** (1) | `census.py --medium` | Parametri, call graph (cosa chiama cosa) |
| **Pesante** (2) | `census.py --heavy` | Contenuto completo del file in `~/.owe/code/` |

Esegui tutti e tre dopo il primo censimento per popolare completamente il database:

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
python ~/.claude/skills/owe-skill/scripts/census.py --medium
python ~/.claude/skills/owe-skill/scripts/census.py --heavy
```

`verify.py --status` mostra quanti componenti sono a ciascun livello.

## Cosa fa l'agente automaticamente

**All'avvio:**

1. Controlla che `~/.owe/owe.db` esista
2. Esegue `verify.py --status` e riporta il dashboard
3. Esegue `prefs.py --load` e carica le preferenze in context

**Prima di ogni task:**

1. Cerca nell'indice locale: `search.py keyword1 keyword2`
2. Riusa quello che trova, o passa a GitPilfer, poi scrive da zero

Non lanci mai comandi di ricerca manualmente.

## Script

| Script | Funzione |
|---|---|
| `_db.py` | Modulo SQLite condiviso (schema, FTS5, migrazione) |
| `census.py` | Scansione + gestione componenti (`--medium`, `--heavy`, `--add`, `--remove`) |
| `search.py` | Ricerca FTS5 con ranking BM25 (zero token per l'agente) |
| `verify.py` | Controlla path stale, conoscenza scaduta, livelli censimento |
| `prefs.py` | Gestione preferenze (`--add`, `--list`, `--remove`, `--load`) |
| `export_import.py` | Backup/ripristino vault via zip |
| `watcher.py` | File watcher per auto-sync incrementale |

## Comandi slash

| Comando | Azione |
|---|---|
| `/owe-sync` | Riscansiona le cartelle configurate |
| `/owe-setup` | Riconfigura cartelle ed estensioni |
| `/owe-status` | Dashboard: componenti, domini, preferenze, livelli censimento, entry stale |
| `/owe-pref` | Aggiunge una preferenza utente |
| `/owe-autosync-on` | Aggiunge nuovi componenti senza chiedere conferma |
| `/owe-autosync-off` | Torna a chiedere conferma prima di aggiungere |
| `/owe-export` | Comprime `~/.owe/` sul Desktop |
| `/owe-import` | Ripristina dal zip sul Desktop |

## Struttura del database

```
~/.owe/
├── owe.db              # Database SQLite (componenti + conoscenza + preferenze + config)
│                       # Indici FTS5 su componenti e conoscenza
├── code/               # Cache pesante: un JSON per file, nominato con hash del path
│   └── <sha256>.json   # { path, content, indexed_at } — mai sovrascritto
└── knowledge/
    └── <dominio>/
        └── notes.json  # Note per dominio (redis, firebase, ecc.)
```

### Tabelle SQLite

| Tabella | Contenuto |
|---|---|
| `components` | path, name, line, docstring, filename, parent, tags, params, calls, census_level |
| `components_fts` | Tabella virtuale FTS5 (mirror di components) |
| `knowledge` | domain, title, content, added, verified |
| `knowledge_fts` | Tabella virtuale FTS5 (mirror di knowledge) |
| `preferences` | id, text, added |
| `config` | key/value: autosync, scan_paths, extensions, staleness_days |

## Portabilita'

Il database vive in `~/.owe/` — locale, nascosto, nessuna sincronizzazione remota.

```bash
python export_import.py --export   # comprime ~/.owe/ sul Desktop
python export_import.py --import   # ripristina dal zip (backup corrente in ~/.owe.bak/)
```

Trasferimento via chiavetta USB o metodo manuale a scelta.

## Multi-agente

OWE e' agnostico all'agente. Funziona uguale su Claude Code, Windsurf o qualsiasi altro agente sulla stessa macchina. Quando un agente trova nuovi componenti non registrati, propone di aggiungerli. Con `autosync: true`, questo avviene silenziosamente.

## Regole

- Componenti: aggiunti con conferma utente (silenzioso se `autosync: true`)
- Note di conoscenza: **mai** aggiunte senza conferma
- Preferenze utente: **mai** aggiunte senza conferma
- Entry stale (soglia configurabile, default 30 giorni): segnalate, non ignorate
