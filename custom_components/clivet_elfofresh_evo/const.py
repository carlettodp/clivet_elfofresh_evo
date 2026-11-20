"""Constants for the Clivet ELFOFresh EVO integration."""

DOMAIN = "clivet_elfofresh_evo"

# Configuration options
CONF_CONNECTION_TYPE = "connection_type"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

# Connection types
CONN_TYPE_RTUOVERTCP = "rtuovertcp"
CONN_TYPE_TCP = "tcp"
CONN_TYPE_SERIAL = "serial"

# Defaults
DEFAULT_NAME = "Clivet ELFOFresh EVO"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_BAUDRATE = 9600
DEFAULT_SCAN_INTERVAL = 15  # seconds

# Modbus Registers (Holding Registers)

# --- Block 1: Basic Control (0..3) ---
REG_POWER = 0           # BIT0: 0: OFF, 1: ON
REG_MODE_SET = 1        # 1: Cool, 2: Heat, 3: Fan, 4: Auto
REG_TARGET_TEMP = 2     # T1s: 17..28 °C
REG_FUNCTIONS_SET = 3   # BIT0: Silent mode, BIT1: 0=normal/1=super silent, BIT2: Auto T1s

# --- Block 2: Read-Only Measurements & Diagnostics (100..128) ---
REG_COMPRESSOR_RPS = 100       # Compressor Hz
REG_OPERATING_MODE = 101       # 0: off, 1: cool, 2: heat, 3: fan
REG_SUPPLY_FAN_SPEED_RAW = 102 # 0..9
REG_EXHAUST_FAN_SPEED = 103    # 0..9
REG_EXV_OPENING = 104          # 0..480 steps (P)
REG_CONDENSATION_TEMP = 105    # Tc: -25..70 °C (S16)
REG_SUPPLY_AIR_HUMIDITY = 106  # RHC: 0..100 %
REG_EVAPORATION_TEMP = 107     # T3: -25..70 °C (S16)
REG_OUTDOOR_AIR_TEMP = 108     # T4: -25..70 °C (S16)
REG_DISCHARGE_TEMP = 109       # TP: -25..70 °C (S16)
REG_SUCTION_TEMP = 110         # TH: -25..70 °C (S16)
REG_INDOOR_AIR_TEMP = 111      # T1: -25..70 °C (S16)
REG_SUPPLY_AIR_TEMP = 112      # T2: -25..70 °C (S16)
REG_SECOND_SUPPLY_TEMP = 113   # T2B: -25..70 °C (S16)
REG_CURRENT = 116              # 0.1 A
REG_VOLTAGE = 117              # V
REG_COMPRESSOR_TIME = 118      # Stop / run time (seconds)
REG_CURRENT_ERROR = 119        # Error code
REG_HISTORY_ERROR_1 = 120
REG_HISTORY_ERROR_2 = 121
REG_HISTORY_ERROR_3 = 122
REG_UNIT_SIZE = 123            # 1: Size 1, 2: Size 2, 3: Size 3
REG_OP_MODE_BITMASK = 124      # Operating mode bitmask
REG_OUTPUT_STATUS_BITMASK = 125# Output status bitmask
REG_EHEATER_OUTPUT = 126       # 0..100% (0..10V)
REG_MAIN_SW_VERSION = 127
REG_HMI_SW_VERSION = 128
REG_TARGET_TEMP_READ = 129     # T1s setting temp readback

# --- Block 3: Settings Parameters (210..225) ---
REG_TARGET_FAN_SPEED = 210     # SupFanSet: 3..7 (default 6)
REG_SILENT_MODE_SET = 217      # 0: Off/Normal, 1: Silent, 2: Super Silent
REG_DEHUM_MODE_SET = 222       # 0: Standard, 1: Low, 2: Eco
REG_ENABLE_E_FILTER = 224      # 0: Disable, 1: Enable electrostatic filter
REG_ENABLE_HUMIDIFIER = 225    # 0: Disable, 1: Enable humidifier

# Bitmask Register 124 (Operating mode)
BIT_124_DEFROST = 1            # BIT1
BIT_124_SILENT = 2             # BIT2
BIT_124_OIL_RETURN = 3         # BIT3
BIT_124_REMOTE_ON_OFF = 4      # BIT4
BIT_124_WATER_LEVEL_ALARM = 8  # BIT8 - Water level switch alarm ON
BIT_124_DAMPER_OPEN = 11       # BIT11 - Damper ON (1: open, 0: closed)
BIT_124_HUMIDIFIER_ON = 12     # BIT12 - Humidifier ON

# Bitmask Register 125 (Output status)
BIT_125_ELECTRICAL_FILTER = 0  # BIT0
BIT_125_GAS_DEFROST = 1        # BIT1 (reserved)
BIT_125_WATER_PUMP = 2         # BIT2
BIT_125_HUMIDIFIER = 3         # BIT3
BIT_125_4WAY_VALVE = 4         # BIT4 (heating valve active)
BIT_125_EXHAUST_FAN_POWER = 5  # BIT5
BIT_125_SUPPLY_FAN_POWER = 6   # BIT6
BIT_125_SYSTEM_ERROR = 7       # BIT7 - System error active
BIT_125_UNIT_ON_INDEX = 8      # BIT8 - Unit running
BIT_125_ELECTRICAL_HEATER = 9  # BIT9 - Auxiliary heater active
BIT_125_DEFROST_INDEX = 10     # BIT10 - Defrost active

# Clivet HVAC Modes (Register 1)
CLIVET_MODE_COOL = 1
CLIVET_MODE_HEAT = 2
CLIVET_MODE_FAN = 3
CLIVET_MODE_AUTO = 4

# Clivet Silent Modes (Register 217)
SILENT_MODE_OFF = 0
SILENT_MODE_NORMAL = 1
SILENT_MODE_SUPER = 2

# Clivet Dehumidification Modes (Register 222)
DEHUM_MODE_STD = 0
DEHUM_MODE_LOW = 1
DEHUM_MODE_ECO = 2
