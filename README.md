# Clivet ELFOFresh EVO - Home Assistant Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=carlettodp&repository=clivet_elfofresh_evo&category=integration)

Custom Home Assistant integration to monitor and control **Clivet CPAN-YIN (ELFOFresh EVO)** active thermodynamic mechanical ventilation (HRV/VMC) units with Home Assistant Core **2026.11.0 or newer**.

---

## Installation via Home Assistant Marketplace

You can add this repository to your Home Assistant instance with a single click:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=carlettodp&repository=clivet_elfofresh_evo&category=integration)

### Manual UI Method:
1. In Home Assistant (Core 2026.11 or newer), navigate to **Settings → Marketplace**.
2. Click the top-right menu (**...**) and select **Custom repositories**.
3. Enter the repository URL: `https://github.com/carlettodp/clivet_elfofresh_evo`
4. Select category **Integration** and click **Add**.
5. Find **Clivet ELFOFresh EVO**, click **Download**, and restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and select **Clivet ELFOFresh EVO**.

---

## Manual Installation

1. Open your Home Assistant configuration directory (where `configuration.yaml` is located).
2. Copy the `custom_components/clivet_elfofresh_evo` folder into your `custom_components` directory (so that `custom_components/clivet_elfofresh_evo/manifest.json` is present).
3. Restart Home Assistant.
4. Navigate to **Settings → Devices & Services → Add Integration → Clivet ELFOFresh EVO**. Select your connection type and enter your gateway IP or serial port along with the Modbus Slave ID.

---

## Updating an Existing Installation

To update the integration code, overwrite the files in your `custom_components/clivet_elfofresh_evo` directory and restart Home Assistant. Keep your existing Clivet ELFOFresh EVO config entry: your device, entities, automations, and Energy dashboard history are preserved.

If your gateway IP address, port, or serial adapter path changes, open the integration card in **Settings → Devices & Services → Clivet ELFOFresh EVO**, click the menu and choose **Reconfigure**. To change polling frequency, click **Configure**.

---

## Key Features

- **UI Config Flow**: Configure and reconfigure network and serial parameters directly from the Home Assistant interface without touching `configuration.yaml`.
- **Flexible Modbus Transports**:
  - Modbus RTU over TCP (Ethernet/Wi-Fi gateways such as Waveshare, Elfin EW11, USR-TCP232)
  - Native Modbus TCP
  - Modbus RTU Serial (USB RS-485 dongles)
- **Optimized Block Reading**: Reads all operational, diagnostic, and configuration registers in just 3 sequential blocks to minimize bus traffic and avoid RS-485 timeouts.
- **Diagnostic Bitmask Decoding**: Automatically decodes registers 124 and 125 into native binary sensors for alarms, dampers, and status indicators.
- **Calibrated Real-World Power Model**: Accurately estimates real power consumption (W) and accumulated energy (kWh) for both the EC ventilation fans and the DC inverter compressor.

---

## Supported Entities

### Climate (`climate`)
- Modes: Off, Cool, Heat, Fan Only, Auto
- Target temperature adjustment (17 °C – 28 °C)
- Current indoor air temperature and real operating action (Heating, Cooling, Defrosting, Fan, Idle)
- Silent mode presets: Normal, Silent, Super Silent

### Ventilation (`fan`)
- Percentage speed control (mapped across native speeds 3 to 7)
- Real-time feedback for supply and exhaust fan speeds and power status

### Sensors (`sensor`)
- **Temperatures**: Indoor Air (T1), Outdoor Air (T4), Supply Air (T2, T2B), Evaporation (T3), Condensation (Tc), Discharge (Tp), Suction (Th)
- **Air Quality & Humidity**: Supply Air Relative Humidity (RHC)
- **Electrical & Energy**:
  - Voltage (V) and Current (A)
  - **Estimated Total Power (W)**: Total instant power drawn by both EC fans, electronics, and the inverter compressor.
  - **Estimated Compressor Power (W)**: Separate power draw of the compressor stage.
  - **Estimated Total Energy (kWh)**: Continuous energy counter ready for individual device tracking in the **Home Assistant Energy Dashboard**.
  - **Estimated Compressor Energy (kWh)**: Dedicated energy counter for the compressor.
- **Operational & Diagnostics**: Compressor Frequency (Hz), EXV Valve Opening (steps), Compressor Runtime, Active Error Code, Error History (1–3), Software Versions (Main / HMI)

### Binary Sensors (`binary_sensor`)
- Condensate water level alarm
- System error status
- Active defrosting
- Fresh air motorized damper open/closed
- Condensate pump running
- 4-way reversing valve active
- Supply and exhaust fan power status
- Electrostatic filter active
- Auxiliary electric heater active

### Selectors & Switches (`select` / `switch`)
- Dehumidification mode selector (Standard, Low, Eco)
- Silent mode selector (Off, Silent, Super Silent)
- Target fan speed level selector (Levels 3–7)
- Main unit power switch
- Electrostatic filter enable switch
- Humidifier enable switch

---

## License

This project is licensed under the Apache 2.0 License.
