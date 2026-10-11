# AGENTS.md

## Panoramica

`tpfireman` è un piccolo client HTTP da terminale per Windows, scritto in Python. L'installer PowerShell copia l'app in `%LOCALAPPDATA%\Programs\tpfireman`, aggiunge `bin` al PATH dell'utente e mantiene i dati separati in `%LOCALAPPDATA%\tpfireman`. La versione è definita nel file `VERSION`; all'avvio il client verifica in modo best-effort l'ultima release GitHub e suggerisce `tpfireman update` se disponibile. Senza argomenti avvia una sessione interattiva; `exit` e `quit` chiudono la sessione da qualsiasi prompt interattivo, solo se costituiscono l'intera risposta (ignorando maiuscole/minuscole e spazi esterni). Il wrapper batch gestisce versione, aggiornamento e disinstallazione.

## Struttura del progetto

- `main.py` — punto d'ingresso e implementazione: parsing degli argomenti, controllo best-effort della release all'avvio, richiesta HTTP, stampa della risposta ed esportazione facoltativa; mostra anche i profili auth salvati e accetta `--auth`, `--payload` e `--export`.
- `auth_store.py` — gestione profili auth; `tpfireman auth` e `tpfireman auth list` mostrano elenco e help.
- `history_store.py` — archivio per utente delle richieste HTTP riutilizzabili, con etichetta distinta dall'URL, deduplicazione per metodo e URL e help esplicito senza prompt di selezione.
- `install.ps1` / `uninstall.ps1` — installazione e disinstallazione per l'utente corrente; installer e updater devono distribuire tutti i moduli Python, incluso `history_store.py`.
- `VERSION` — versione SemVer copiata nell'installazione.
- `update.ps1` — updater per release GitHub, che scarica l'asset ZIP `tpfireman-source.zip`, ripara anche moduli mancanti reinstallando la release corrente, chiede conferma (`YES`, `yes`, `Y` o `y`) e preserva i dati utente.
- `bin/tpfireman.bat` — wrapper che gestisce `version`, `update`, `uninstall` e inoltra gli altri argomenti a `main.py`.
- `README.md` — documentazione d'uso e installazione.

Il progetto include test d'integrazione online in `tests/test_jsonplaceholder.py`, che richiedono Internet e usano JSONPlaceholder. Non dichiara dipendenze esterne né configurazione di build. La logica usa la libreria standard Python (`urllib`, `json`, `os`, `datetime`, `unittest`).

## TODO / prossimi step

### Completati
- [x] Aggiunta history locale delle richieste HTTP con selezione per ID/URL, revisione dei campi e salvataggio automatico delle modifiche.
- [x] Aggiunti `history edit` per ID/label/URL e `history delete` per una o più voci tramite ID/label, con conferma.
- [x] I comandi `history` e `auth` (alias `auth list`) mostrano l'elenco e l'help senza richiedere input di selezione.
- [x] Mostrare i profili auth all'avvio della sessione e supportare la selezione esplicita con `--auth NAME_OR_ID`.
- [x] Aggiungere test d'integrazione online per GET, POST, PUT, PATCH e DELETE contro JSONPlaceholder.
- [x] Correggere il controllo elevazione Windows in `main.py` impostando firme e tipi WinAPI per evitare WinError 6.
- [x] Verificare e correggere il controllo amministratore in `main.py` usando il token Windows.
- [x] Sistemare la formattazione Markdown del README, sostituendo le tabulazioni nei comandi con code span o blocchi di codice.
- [x] Correggere nel README il nome del file esportato (`api_response.txt`).
- [x] Correggere l'errore di sintassi in `main.py` e rendere le f-string compatibili con versioni Python precedenti a 3.12.
- [x] Correggere il controllo amministratore e la risoluzione dei percorsi in `install.ps1`.
- [x] Uniformare il nome del comando a `tpfireman` in README e wrapper.
- [x] Correggere la sintassi d'uso nel README: il payload è interattivo e non è un argomento CLI.
- [x] Rimuovere `QUERY` dall'elenco dei metodi supportati, essendo un errore.

### Da fare, in ordine
1. [x] Migliorare la validazione di metodo, URL e payload JSON, con messaggi d'errore chiari.
2. [x] Aggiungere il supporto per header HTTP personalizzati, inclusa l'autenticazione, senza esporre credenziali nei log.
- [x] Gestire profili auth riutilizzabili in `%LOCALAPPDATA%\\tpfireman`, cifrando i segreti con DPAPI e supportando Bearer, Basic, API key e OAuth2 (Client Credentials e Authorization Code con PKCE), senza mostrare i valori.
3. [x] Gestire timeout configurabile e risposte HTTP d'errore mostrando in modo coerente status code, header e corpo.
4. [x] Rafforzare l'esportazione: consentire la scelta del percorso e chiedere conferma prima di sovrascrivere file.
5. [x] Aggiungere verifiche dell'installazione e del wrapper, inclusa una prova in ambiente Windows non amministratore.

Aggiornare questa lista man mano che le voci vengono completate e non ripristinare i difetti già corretti.

## Convenzioni per le modifiche

- Mantenere il progetto semplice e basato sulla libreria standard, salvo una necessità concreta che giustifichi dipendenze aggiuntive.
- Preservare la compatibilità Windows: i percorsi usati dall'installer e dal wrapper devono funzionare indipendentemente dalla directory corrente.
- Mantenere README, messaggi CLI, installer e nome del wrapper coerenti tra loro.
- Ogni modifica al README deve preservare o migliorare una presentazione estetica, moderna e coerente: struttura scansionabile, sezioni concise, esempi separati dai commenti del codice, callout Markdown e tabelle quando aiutano la leggibilità; evitare paragrafi molto densi e contenuti fuori dai blocchi di codice in sezioni di comandi.
- Validare input e argomenti CLI con messaggi d'errore chiari; non ignorare silenziosamente valori non validi.
- Non includere credenziali o dati sensibili negli esempi, nei log o nei file di risposta.
- Le risposte HTTP possono contenere dati non JSON: mantenere la gestione del testo non JSON oltre al pretty-print JSON.
- Evitare di sovrascrivere file dell'utente senza una scelta esplicita o una documentazione chiara del comportamento.
- La disinstallazione deve chiedere conferma e rimuovere applicazione, entry PATH e tutti i dati utente di tpfireman, inclusi i profili auth.

## Verifica

Dopo modifiche a `main.py`, verificare almeno la sintassi con:

```powershell
python -m py_compile main.py
```

Dopo modifiche all'installer o all'updater, controllare la sintassi PowerShell e, quando possibile, provarli in un ambiente Windows non amministratore. Per la logica HTTP, preferire test con un server locale o mock, senza dipendere da servizi esterni.

I test d'integrazione online si eseguono con `python -m unittest discover -s tests -v` e richiedono una connessione Internet.
