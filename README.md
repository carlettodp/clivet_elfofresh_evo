# Clivet ELFOFresh EVO - Integrazione Home Assistant

[![Aggiungi repository a Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=carlettodp&repository=clivet_elfofresh_evo&category=integration)

Integrazione personalizzata per monitorare e controllare le unità **Clivet CPAN-YIN (ELFOFresh EVO)** con Home Assistant Core **2026.11.0 o successivo**.

## Installazione tramite Home Assistant Marketplace

Puoi aggiungere direttamente questo repository al tuo Home Assistant facendo clic sul pulsante qui sotto:

[![Aggiungi repository a Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=carlettodp&repository=clivet_elfofresh_evo&category=integration)

Oppure manualmente dall'interfaccia:
1. In Home Assistant (Core 2026.11 o successivo), vai su **Impostazioni → Marketplace**.
2. Fai clic sul menu in alto a destra (**...**) e seleziona **Repository personalizzati**.
3. Inserisci l'URL del repository: `https://github.com/carlettodp/clivet_elfofresh_evo`
4. Seleziona la categoria **Integrazione** e premi **Aggiungi**.
5. Cerca **Clivet ELFOFresh EVO**, premi **Scarica** e riavvia Home Assistant.
6. Vai in **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** e seleziona **Clivet ELFOFresh EVO**.

## Installazione manuale

1. Apri la cartella di configurazione di Home Assistant, quella che contiene `configuration.yaml`.
2. Copia la cartella `custom_components/clivet_elfofresh_evo` del progetto nella sottocartella `custom_components` di Home Assistant. Al termine devi trovare `custom_components/clivet_elfofresh_evo/manifest.json` accanto agli altri file dell’integrazione.
3. Riavvia Home Assistant.
4. Alla prima installazione apri **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Clivet ELFOFresh EVO**. Seleziona il tipo di connessione e inserisci i dati del gateway o della porta seriale e l’indirizzo Modbus della VMC.

## Aggiornare un impianto già configurato

Per aggiornare il codice, sovrascrivi i file nella cartella `custom_components/clivet_elfofresh_evo` già installata e riavvia Home Assistant. Mantieni la voce Clivet ELFOFresh EVO esistente: è quella a cui sono associati dispositivo, entità, automazioni e contatore Energia.

Se cambia l’indirizzo del gateway, la porta o il tipo di collegamento della stessa VMC, apri il menu della **voce esistente → Riconfigura** in **Impostazioni → Dispositivi e servizi → Clivet ELFOFresh EVO**. Per cambiare la frequenza di lettura usa **Configura**.

## Caratteristiche

- **Configurazione grafica (Config Flow)**: Configura la connessione direttamente dall'interfaccia di Home Assistant senza dover modificare `configuration.yaml`.
- **Supporto Modbus flessibile**:
  - Modbus RTU over TCP (gateway Ethernet/Wi-Fi come Elfin EW11 o Waveshare)
  - Modbus TCP nativo
  - Modbus RTU seriale (tramite adattatore USB RS-485)
- **Lettura a blocchi ottimizzata**: I registri vengono letti in soli 3 blocchi sequenziali per garantire velocità ed evitare timeout sulla linea RS-485.
- **Risoluzione bitmask diagnostica**: I registri 124 e 125 vengono decodificati automaticamente in entità binarie native.

## Entità supportate

### Clima (`climate`)
- Modalità: Spento, Raffrescamento, Riscaldamento, Sola Ventilazione, Automatico
- Regolazione temperatura target (17 - 28 °C)
- Visualizzazione temperatura aria ambiente e stato operativo reale (riscaldamento, raffrescamento, sbrinamento, ventilazione)
- Modalità silenziose (Normale, Silenziosa, Super Silenziosa)

### Ventilazione (`fan`)
- Controllo percentuale di velocità (livelli 3..7)
- Feedback in tempo reale su velocità effettiva mandata ed estrazione

### Sensori (`sensor`)
- Temperature: ambiente (T1), esterna (T4), mandata (T2, T2B), evaporazione (T3), condensazione (Tc), scarico (Tp), aspirazione (Th)
- Umidità aria di mandata (RHC)
- Dati elettrici: tensione (V), corrente assorbita (A) e potenza stimata del compressore (W), calcolata come tensione × corrente × 0,96.
- Energia stimata compressore (kWh), selezionabile nella dashboard Energia tra i singoli dispositivi. Il contatore accumula la potenza stimata tra letture valide e riprende dal totale salvato dopo un riavvio.
- Frequenza compressore (Hz), apertura valvola EXV, tempi di funzionamento
- Codici errore attivo e storico allarmi

### Sensori Binari (`binary_sensor`)
- Allarme livello acqua vaschetta condensa
- Allarme errore di sistema
- Stato sbrinamento attivo
- Stato serranda aria aperta/chiusa
- Stato pompa condensa, valvola a 4 vie e ventilatori

### Selettori e Interruttori (`select` / `switch`)
- Selezione modalità di deumidificazione (Standard, Bassa, Eco)
- Selezione modalità silenziosa
- Selettore diretto livello velocità
- Interruttore accensione generale, filtro elettrostatico e umidificatore

