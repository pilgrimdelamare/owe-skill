# OWE — Once Was Enough

> A local knowledge and code cache for AI coding agents. What the agent learns once, it remembers forever.

It's 4am, the world is asleep and someone is banging their head against the wall. That's you, while the token counter spins like a slot machine and Claude keeps failing on a problem you've solved 1000 times across 1000 projects. He knows everything, but remembers nothing. OWE fixes this: it creates a local database where the agent accumulates tested code, acquired knowledge and your preferences, session after session, repo after repo. And the more experience it accumulates, the more performant it becomes — going from junior to finally senior developer.

**English** | [Italiano](#italiano)

---

## What is OWE?

OWE is a global skill for AI coding agents (Claude Code, Windsurf, and others) that builds and queries a local database of:

- **Tested code** — functions and components already confirmed working, indexed by name and docstring
- **Acquired knowledge** — API quirks, dead ends, unexpected behaviors, organized by domain
- **User preferences** — how you want the agent to behave, loaded into context on every session

The agent consults the database automatically before writing any code. You do nothing manually.

## How it works

**Task → OWE search (automatic) → [GitPilfer](https://github.com/pilgrimdelamare/GitPilfer) → Write from scratch**

Before writing any code, the agent searches the local index at zero token cost. If something useful exists, it reuses it. If not, it falls through to GitHub search or writes from scratch.

The database grows over time. The more sessions it accumulates, the more efficient the agent becomes.

## Stack

- **Language:** Python 3 (stdlib only, zero external dependencies)
- **Storage:** JSON (`~/.owe/`)
- **Compatible with:** Unix, Windows (Git Bash / WSL)

## Installation

### Claude Code

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cp -r owe-skill/owe-skill ~/.claude/skills/
```

OWE activates automatically in every Claude Code session on any project.

### Windsurf — global (all projects)

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
```

Open **Settings → Cascade → Global Rules** and paste the contents of `owe-skill/owe-skill/SKILL.md`.

### Windsurf — single project

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cat owe-skill/owe-skill/SKILL.md > /path/to/your-project/.windsurfrules
```

### First run

After installing, run the initial census once:

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
```

It will ask which folders to scan. From that point on, OWE manages everything automatically.

## What the agent does automatically

**First launch:** if no database exists yet, the agent runs the initial census. It asks which folders to scan and which file extensions to include (default: `.py`, `.js`, `.ts`), then indexes all functions and components it finds.

Accepted path aliases: `desktop`, `documents`, `downloads`, `home` — these resolve to the correct path on any machine regardless of username.

**Every session after that:**

1. Loads `~/.owe/prefs.json` into context
2. Before each task, searches the local index for relevant code and knowledge
3. Reuses what it finds, or falls through to the next level
4. After confirmed steps, proposes saving new components to the database

You never run search commands manually.

## Scripts

| Script | Purpose |
|---|---|
| `~/.owe/scripts/census.py` | Initial scan + component management |
| `~/.owe/scripts/search.py` | Search the index (zero agent tokens) |
| `~/.owe/scripts/verify.py` | Check stale paths and outdated knowledge |

## Slash commands

| Command | Action |
|---|---|
| `/owe-sync` | Re-scan configured folders |
| `/owe-setup` | Reconfigure folders and extensions |
| `/owe-status` | Dashboard: components, domains, preferences, stale entries |
| `/owe-pref` | Add a user preference |
| `/owe-autosync-on` | Auto-add new components without confirmation |
| `/owe-autosync-off` | Revert to asking before adding |
| `/owe-export` | Copy `~/.owe/` to Desktop as a zip archive |
| `/owe-import` | Load a zip archive into `~/.owe/` |

## Database structure

```
~/.owe/
├── index.json          # Global index (code + knowledge + config)
├── prefs.json          # User preferences (always loaded)
├── scripts/            # OWE scripts (installed here)
└── knowledge/
    └── <domain>/
        └── notes.json  # Notes per domain (redis, firebase, etc.)
```

## Portability

The database lives at `~/.owe/` — local, hidden, no remote sync.

- `/owe-export` → zips `~/.owe/` to the Desktop
- `/owe-import` → loads the archive from the Desktop
- Transfer via USB or any manual method

## Multi-agent

OWE is agent-agnostic. It works the same on Claude Code, Windsurf, or any agent on the same machine. When an agent finds new unregistered components, it proposes adding them. With `autosync: true`, this happens silently.

## Rules

- Components: added with user confirmation (silent if `autosync: true`)
- Knowledge notes: **never** added without confirmation
- User preferences: **never** added without confirmation
- Stale entries (default threshold: 30 days) are flagged, not ignored

---

## Italiano

> Un database locale di codice e conoscenza per agenti AI. Quello che l'agente impara una volta, lo ricorda per sempre.

Sono le 4 am, il mondo dorme e una persona sbatte la testa contro il muro. Sei tu, mentre il contatore dei token gira come una slot machine e Claude continua a fallire su un problema che avete risolto 1000 volte su 1000 progetti. Lui sa tutto, ma non si ricorda niente. OWE risolve questo: crea un database locale dove l'agente accumula codice testato, conoscenza acquisita e le tue preferenze, sessione dopo sessione, repo dopo repo. E più accumula esperienza più diventa performante, passando da junior a finalmente senior developer.

[English](#owe--once-was-enough) | **Italiano**

---

## Cos'è OWE?

OWE è una skill globale per agenti AI (Claude Code, Windsurf e altri) che costruisce e consulta un database locale di:

- **Codice testato** — funzioni e componenti già confermati funzionanti, indicizzati per nome e docstring
- **Conoscenza acquisita** — quirk di API, vicoli ciechi, comportamenti inattesi, organizzati per dominio
- **Preferenze utente** — come vuoi che l'agente si comporti, caricate in context ad ogni sessione

L'agente consulta il database automaticamente prima di scrivere qualsiasi codice. L'utente non fa nulla manualmente.

## Come funziona

**Task → Ricerca OWE (automatica) → [GitPilfer](https://github.com/pilgrimdelamare/GitPilfer) → Scrivi da zero**

Prima di scrivere qualsiasi codice, l'agente cerca nell'indice locale a costo zero di token. Se trova qualcosa di utile lo riusa, altrimenti passa al livello successivo.

Il database cresce nel tempo. Più sessioni accumula, più l'agente diventa efficiente.

## Stack

- **Linguaggio:** Python 3 (stdlib only, zero dipendenze esterne)
- **Storage:** JSON (`~/.owe/`)
- **Compatibile con:** Unix, Windows (Git Bash / WSL)

## Installazione

### Claude Code

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cp -r owe-skill/owe-skill ~/.claude/skills/
```

OWE si attiva automaticamente in ogni sessione di Claude Code su qualsiasi progetto.

### Windsurf — globale (tutti i progetti)

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
```

Apri **Settings → Cascade → Global Rules** e incolla il contenuto di `owe-skill/owe-skill/SKILL.md`.

### Windsurf — singolo progetto

```bash
git clone https://github.com/pilgrimdelamare/owe-skill.git
cat owe-skill/owe-skill/SKILL.md > /percorso/tuo-progetto/.windsurfrules
```

### Primo avvio

Dopo l'installazione, esegui il censimento iniziale una volta sola:

```bash
python ~/.claude/skills/owe-skill/scripts/census.py
```

Chiederà quali cartelle scansionare. Da quel momento OWE gestisce tutto automaticamente.

## Cosa fa l'agente automaticamente

**Al primo avvio:** se non esiste ancora un database, l'agente avvia il censimento iniziale. Chiede quali cartelle scansionare e quali estensioni includere (default: `.py`, `.js`, `.ts`), poi indicizza tutte le funzioni e i componenti trovati.

Alias accettati: `desktop`, `documents`, `downloads`, `home` — si risolvono al percorso corretto su qualsiasi macchina, indipendentemente dal nome utente.

**Da ogni sessione successiva:**

1. Carica `~/.owe/prefs.json` in context
2. Prima di ogni task, cerca nell'indice locale codice e conoscenza rilevanti
3. Riusa quello che trova, o passa al livello successivo
4. Dopo step confermati, propone di salvare nuovi componenti nel database

Non lanci mai comandi di ricerca manualmente.

## Script

| Script | Funzione |
|---|---|
| `~/.owe/scripts/census.py` | Scansione iniziale + gestione componenti |
| `~/.owe/scripts/search.py` | Ricerca nell'indice (zero token per l'agente) |
| `~/.owe/scripts/verify.py` | Controlla path stale e conoscenza scaduta |

## Comandi slash

| Comando | Azione |
|---|---|
| `/owe-sync` | Riscansiona le cartelle configurate |
| `/owe-setup` | Riconfigura cartelle ed estensioni |
| `/owe-status` | Dashboard: componenti, domini, preferenze, entry stale |
| `/owe-pref` | Aggiunge una preferenza utente |
| `/owe-autosync-on` | Aggiunge nuovi componenti senza chiedere conferma |
| `/owe-autosync-off` | Torna a chiedere conferma prima di aggiungere |
| `/owe-export` | Copia `~/.owe/` sul Desktop come archivio zip |
| `/owe-import` | Carica un archivio zip in `~/.owe/` |

## Struttura del database

```
~/.owe/
├── index.json          # Indice globale (codice + conoscenza + config)
├── prefs.json          # Preferenze utente (sempre caricate)
├── scripts/            # Script OWE (installati qui)
└── knowledge/
    └── <dominio>/
        └── notes.json  # Note per dominio (redis, firebase, ecc.)
```

## Portabilità

Il database vive in `~/.owe/` — locale, nascosto, nessuna sincronizzazione remota.

- `/owe-export` → comprime `~/.owe/` sul Desktop
- `/owe-import` → carica l'archivio dal Desktop
- Trasferimento via chiavetta USB o metodo manuale a scelta

## Multi-agente

OWE è agnostico all'agente. Funziona uguale su Claude Code, Windsurf o qualsiasi altro agente sulla stessa macchina. Quando un agente trova nuovi componenti non registrati, propone di aggiungerli. Con `autosync: true`, questo avviene silenziosamente.

## Regole

- Componenti: aggiunti con conferma utente (silenzioso se `autosync: true`)
- Note di conoscenza: **mai** aggiunte senza conferma
- Preferenze utente: **mai** aggiunte senza conferma
- Entry stale (soglia configurabile, default 30 giorni): segnalate, non ignorate
