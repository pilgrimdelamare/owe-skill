# OWE — Once Was Enough

> A local knowledge and code cache for AI agents. What the agent learns once, it remembers forever.

**English** | [Italiano](#italiano)

---

## What is OWE?

OWE is a global skill for AI coding agents (Claude Code, Windsurf, and others) that builds and queries a local database of:

- **Tested code** — functions and components already written and confirmed working, indexed by name and docstring
- **Acquired knowledge** — API quirks, dead ends, unexpected service behaviors, organized by domain
- **User preferences** — how you want the agent to behave, loaded into context on every session

The goal: reduce repeated token usage and repeated mistakes across sessions and across agents.

## How it works

Before writing any code, the agent runs a zero-token search against the local index. If something useful is found, it reuses it. If not, it falls through to GitHub search (GitPilfer) or writes from scratch.

```
Task → OWE search → GitPilfer → Write from scratch
```

The database grows over time. The more sessions it accumulates, the more efficient the agent becomes.

## Stack

- **Language:** Python 3 (stdlib only, zero external dependencies)
- **Storage:** JSON (`~/.owe/`)
- **Shell:** bash
- **Compatible with:** Unix, Windows (Git Bash / WSL)

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/owe
cd owe

# 2. Run initial census (one-time setup)
python owe/scripts/census.py
```

You will be prompted to select which folders to scan and which file extensions to include (default: `.py`, `.js`, `.ts`).

**Accepted path aliases:** `desktop`, `documents`, `downloads`, `home`

The database lives at `~/.owe/` — hidden, local, portable.

## Agent setup

Add the following to your agent's system prompt or CLAUDE.md:

1. Load `~/.owe/prefs.json` into context at session start
2. Before any task, run: `python owe/scripts/search.py <keywords>`
3. If `FOUND:0` → proceed to next level; if `FOUND:N` → use the results

See [`owe/SKILL.md`](owe/SKILL.md) for complete agent instructions.

## Scripts

| Script | Purpose |
|---|---|
| `owe/scripts/census.py` | Initial scan + component management |
| `owe/scripts/search.py` | Search the index (zero agent tokens) |
| `owe/scripts/verify.py` | Check stale paths and outdated knowledge |

## Slash commands

| Command | Action |
|---|---|
| `/owe-sync` | Re-scan configured folders |
| `/owe-setup` | Reconfigure folders and extensions |
| `/owe-status` | Dashboard: components, domains, preferences, stale entries |
| `/owe-pref` | Add a user preference manually |
| `/owe-autosync-on` | Auto-add new components without confirmation |
| `/owe-autosync-off` | Revert to asking before adding |
| `/owe-export` | Copy `~/.owe/` to Desktop as a zip archive |
| `/owe-import` | Load a zip archive into `~/.owe/` |

## Database structure

```
~/.owe/
├── index.json          # Global index (code + knowledge + config)
├── prefs.json          # User preferences (always loaded)
├── code/               # Reserved for component detail files
└── knowledge/
    └── <domain>/
        └── notes.json  # Notes per domain (redis, firebase, etc.)
```

## Portability

No remote repository is used to avoid exposing secrets or sensitive data.

- `/owe-export` → zips `~/.owe/` to the Desktop
- `/owe-import` → loads the archive from the Desktop
- Transfer via USB drive or any manual method

## Multi-agent

OWE is agent-agnostic. It works the same on Claude Code, Windsurf, or any other agent on the same machine. When an agent finds new unregistered components (written by another agent or by the user), it proposes adding them. With `autosync: true`, this happens automatically.

## Rules

- Components are added only with user confirmation (unless `autosync: true`)
- Knowledge notes are **never** added without confirmation
- User preferences are **never** added without confirmation
- Stale knowledge (configurable threshold, default 30 days) is flagged but not ignored

---

## Italiano

OWE è una skill globale per agenti AI (Claude Code, Windsurf e altri) che costruisce e consulta un database locale di:

- **Codice testato** — funzioni e componenti già scritti e confermati funzionanti, indicizzati per nome e docstring
- **Conoscenza acquisita** — quirk di API, vicoli ciechi, comportamenti inattesi di servizi esterni, organizzati per dominio
- **Preferenze utente** — come vuoi che l'agente si comporti, caricate in context ad ogni sessione

### Obiettivo

Ridurre token ripetuti ed errori ripetuti nel tempo e tra agenti diversi. Il database cresce con le sessioni: più accumula, più l'agente diventa efficiente.

### Come funziona

Prima di scrivere qualsiasi codice, l'agente lancia una ricerca zero-token sull'indice locale. Se trova qualcosa di utile, lo riusa. Se non trova niente, passa al livello successivo (ricerca su GitHub o scrittura da zero).

### Installazione

```bash
git clone https://github.com/YOUR_USERNAME/owe
cd owe
python owe/scripts/census.py
```

Al primo avvio viene chiesto quali cartelle scansionare e quali estensioni includere.
**Alias accettati:** `desktop`, `documents`, `downloads`, `home`

Il database vive in `~/.owe/` — nascosto, locale, portabile.

### Configurazione agente

Aggiungi al system prompt o al CLAUDE.md del tuo agente:

1. Carica `~/.owe/prefs.json` in context all'avvio
2. Prima di ogni task, lancia: `python owe/scripts/search.py <keyword>`
3. Se `FOUND:0` → passa al livello successivo; se `FOUND:N` → usa i risultati

Vedi [`owe/SKILL.md`](owe/SKILL.md) per le istruzioni complete per l'agente.

### Regole

- I componenti si aggiungono solo con conferma utente (salvo `autosync: true`)
- Le note di conoscenza non si aggiungono mai senza conferma
- Le preferenze non si aggiungono mai senza conferma
- La conoscenza stale (soglia configurabile, default 30 giorni) viene segnalata ma non ignorata
