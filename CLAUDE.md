# OWE — Once Was Enough

## Obiettivo
OWE è una skill globale per Claude Code e Windsurf che costruisce e consulta un database locale di codice testato, conoscenza acquisita e preferenze utente, riducendo token e errori ripetuti nel tempo e tra agenti diversi.

## Stack
- Linguaggio: Python 3 (stdlib only, zero dipendenze esterne)
- Storage: JSON (~/.owe/)
- Shell: bash
- Compatibilità: Unix, Windows (WSL)

## File chiave
- `~/.owe/index.json`: indice leggero globale (codice + conoscenza)
- `~/.owe/code/`: dettagli dei componenti cachati
- `~/.owe/knowledge/`: note per dominio (es. redis/, firebase/, openrouter/)
- `~/.owe/prefs.json`: preferenze utente, sempre caricate in context ad ogni avvio
- `owe/SKILL.md`: istruzioni per l'agente
- `owe/scripts/census.py`: censimento iniziale e sync
- `owe/scripts/search.py`: ricerca nell'indice via Python, zero token
- `owe/scripts/verify.py`: controllo path stale e staleness della conoscenza
- `README.md`: documentazione pubblica

## Codice stato
`ST:F1/0:done`

## Stato attuale
**Ultimo punto fermo:** Setup completo — script core scritti, `~/.owe/` inizializzato
**Prossimo task:** Censimento iniziale (eseguire `census.py` con le cartelle dell'utente)

## Gerarchia prima di scrivere codice
1. **OWE** → cerca nel database locale (codice già testato)
2. **GitPilfer** → cerca su GitHub (skill separata, livello 2)
3. **Scratch** → scrivi da zero solo se i primi due falliscono

OWE gestisce solo il livello 1. Se non trova niente, passa il controllo senza intervenire ulteriormente.

## Tre sezioni del database

### 1. Codice riutilizzabile
Componenti funzionanti con path assoluto su disco.
- Censimento **leggero** su tutti i file al primo avvio (nomi funzioni + docstring via Python)
- Censimento **medio** solo sui file interrogati per un task specifico
- Censimento **pesante** solo sui file effettivamente utili, poi cachato — mai riletto
- L'agente interviene con token solo su file senza docstring o con docstring ambigui
- Un componente viene aggiunto quando l'utente conferma che uno step è completato

### 2. Conoscenza acquisita
Scoperte, vicoli ciechi, quirk di API, comportamenti inattesi di servizi esterni.
- Organizzata per dominio (`~/.owe/knowledge/redis/`, `firebase/`, ecc.)
- L'indice leggero tiene una riga per dominio con il numero di note
- L'agente legge solo il dominio rilevante per il task corrente
- Ogni nota ha una data di **ultima verifica**
- Dopo un periodo configurabile diventa **stale** — l'agente la segnala ma non la ignora
- Se l'agente la usa e funziona ancora, aggiorna la data automaticamente
- Viene aggiunta quando l'agente scopre qualcosa di rilevante, previa conferma utente

### 3. Preferenze utente
Come l'utente vuole che l'agente si comporti.
- File piccolo, sempre interamente in context ad ogni avvio
- Si aggiunge via `/owe-pref` oppure quando l'agente intercetta frasi come "ogni volta", "da adesso in poi", "in futuro sempre" — in quel caso chiede conferma prima di salvare
- Nessuna aggiunta automatica senza conferma, nessuna eccezione

## Flusso su ogni task
1. Carica `~/.owe/prefs.json` in context
2. Comprendi il task
3. Lancia `search.py` con le keyword del task → zero token
4. Se 0 risultati → passa al livello successivo della gerarchia
5. Se ci sono risultati → leggi solo quelli e decidi se usarli

## Censimento iniziale
- **Setup una tantum**: chiedi all'utente le cartelle da scansionare e le estensioni da includere (default: `.py`, `.js`, `.ts`)
- `census.py` scansiona tutto, estrae nomi funzioni e docstring → quasi zero token
- L'agente interviene solo su file senza docstring o ambigui
- Dal secondo avvio in poi consulta e aggiunge, non rescansiona

## Multi-agente
OWE è agnostico all'agente — funziona uguale su Claude Code, Windsurf, o qualsiasi altro agente sullo stesso progetto.
- Quando un agente trova componenti nuovi non registrati (scritti da un altro agente o dall'utente), propone di aggiungerli
- Con `/owe-autosync-on` questo avviene automaticamente senza chiedere conferma
- Il permesso autosync è **revocabile** in qualsiasi momento con `/owe-autosync-off`
- Autosync vale solo per il sync del codice — conoscenza e preferenze chiedono sempre conferma

## Comandi slash
| Comando | Azione |
|---|---|
| `/owe-autosync-on` | Attiva sync automatico dei componenti nuovi |
| `/owe-autosync-off` | Revoca sync automatico, torna a chiedere conferma |
| `/owe-sync` | Aggiorna manualmente il censimento |
| `/owe-export` | Copia l'intero database sul Desktop |
| `/owe-import` | Carica il database dal Desktop |
| `/owe-pref` | Aggiunge una preferenza utente manualmente |
| `/owe-status` | Dashboard testuale: componenti, domini, preferenze, entry stale |

## Portabilità tra macchine
Non si usa una repo remota per evitare esposizione di segreti o dati sensibili.
- `/owe-export` → copia `~/.owe/` sul Desktop come archivio
- `/owe-import` → carica l'archivio dal Desktop nella posizione corretta
- Trasferimento via chiavetta USB o metodo manuale a scelta dell'utente

## Dove vive
`~/.owe/` — cartella nascosta, accessibile all'utente, universale su qualsiasi macchina Unix.

## Requisiti
- `bash`
- `python3` (stdlib only)
- Zero dipendenze npm/pip

## Note specifiche
- Autosync è **off** per default
- La staleness della conoscenza è configurabile in `~/.owe/index.json`
- Compatibile con GitPilfer: le due skill operano su livelli diversi e non si sovrappongono
- Il database cresce nel tempo — più sessioni accumula, più l'agente diventa efficiente
