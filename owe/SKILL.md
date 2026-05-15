# OWE — Istruzioni per l'Agente

## Avvio sessione

1. Leggi `~/.owe/prefs.json` → carica le preferenze utente in context
2. Se `~/.owe/index.json` non esiste → esegui `python owe/scripts/census.py` per il setup iniziale

## Per ogni task

1. Estrai 2-5 keyword rilevanti dal task
2. Esegui: `python owe/scripts/search.py <keyword1> [keyword2] ...`
3. Leggi la prima riga dell'output:
   - `FOUND:0` → nessun risultato → passa al livello 2 (GitPilfer) o scrivi da zero
   - `FOUND:N` → N > 0 → leggi i risultati e usa i componenti/knowledge pertinenti

## Gerarchia prima di scrivere codice

1. OWE (questo livello) → database locale
2. GitPilfer → GitHub
3. Scratch → scrivi da zero

OWE gestisce solo il livello 1. Se FOUND:0, passa avanti senza intervenire.

---

## Aggiungere un componente

Quando l'utente conferma che uno step è completato e il codice funziona:

1. Chiedi: "Vuoi salvare `<nome_funzione>` in OWE?"
2. Se sì, esegui:
   ```
   python owe/scripts/census.py --add <path_assoluto> <nome> <linea> "<docstring>"
   ```

Oppure aggiungi direttamente in `~/.owe/index.json` → `code.components`:
```json
{
  "path": "/path/assoluto/file.py",
  "name": "nome_funzione",
  "line": 42,
  "docstring": "cosa fa in max 120 caratteri",
  "tags": ["tag1", "tag2"],
  "added": "YYYY-MM-DD",
  "verified": "YYYY-MM-DD"
}
```

Se `autosync: true` in index.json → aggiungi senza chiedere, ma segnalalo all'utente.

---

## Aggiungere conoscenza

Quando scopri qualcosa di rilevante (quirk API, vicolo cieco, comportamento inatteso):

1. Chiedi: "Vuoi salvare questa nota in OWE? Dominio: `<dominio>`"
2. Se sì:
   - Crea `~/.owe/knowledge/<dominio>/` se non esiste
   - Edita (o crea) `~/.owe/knowledge/<dominio>/notes.json`:

```json
[
  {
    "id": "YYYYMMDD-HHMMSS",
    "title": "titolo breve",
    "content": "spiegazione completa",
    "added": "YYYY-MM-DD",
    "verified": "YYYY-MM-DD"
  }
]
```

   - Aggiorna `~/.owe/index.json` → `knowledge.domains.<dominio>`:
```json
{
  "count": 1,
  "last_update": "YYYY-MM-DD"
}
```

Conoscenza e preferenze: **mai aggiungere senza conferma utente, nessuna eccezione**.

---

## Aggiornare una nota come verificata

Se usi una nota di knowledge e funziona ancora, aggiorna il campo `verified` con la data di oggi.

---

## Comandi slash

| Comando | Azione |
|---|---|
| `/owe-autosync-on` | `python owe/scripts/census.py --autosync-on` |
| `/owe-autosync-off` | `python owe/scripts/census.py --autosync-off` |
| `/owe-sync` | `python owe/scripts/census.py` |
| `/owe-status` | `python owe/scripts/verify.py --status` |
| `/owe-pref` | Chiedi la preferenza → aggiungi a `~/.owe/prefs.json` (con conferma) |
| `/owe-export` | Zip `~/.owe/` → Desktop come `owe-backup-<YYYY-MM-DD>.zip` |
| `/owe-import` | Chiedi file → decomprimi in `~/.owe/` (con conferma, sovrascrive) |

### Implementazione /owe-export (bash)
```bash
cd ~ && zip -r ~/Desktop/owe-backup-$(date +%F).zip .owe/
```

### Implementazione /owe-import (bash)
```bash
# Chiedi conferma prima — sovrascrive ~/.owe/
unzip -o <file> -d ~/
```

---

## Intercettare preferenze implicite

Se l'utente usa frasi come:
- "ogni volta", "sempre", "da adesso in poi", "in futuro"

→ Chiedi: "Vuoi che salvi questa preferenza in OWE per le sessioni future?"
→ Solo se conferma, aggiungi a `~/.owe/prefs.json`.

---

## Struttura ~/.owe/prefs.json

```json
{
  "preferences": [
    {
      "id": "20260515-120000",
      "text": "Usa sempre TypeScript, non JavaScript",
      "added": "2026-05-15"
    }
  ]
}
```

---

## Regole

- Non aggiungere componenti senza conferma (a meno che autosync=true)
- Non aggiungere knowledge senza conferma — MAI
- Non aggiungere preferenze senza conferma — MAI
- Usa OWE prima di qualsiasi ricerca esterna o scrittura da zero
- Se un path è stale ma il componente è logicamente ancora utile, segnalalo ma non ignorarlo
