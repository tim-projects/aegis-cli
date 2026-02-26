# Current Task: Decouple TUI from CLI

## Objective
Separate the CLI functionality from the TUI to create two distinct applications:
1. **aegis-cli** - A fully functioning CLI tool with no TUI dependencies
2. **aegis-tui** - A TUI that interacts with aegis-cli via `--json` mode

## Plan

### Phase 1: Create aegis-cli (COMPLETED)
- Created `aegis-cli` executable with full CLI functionality
- `--json` mode outputs all info as JSON objects
- UUID and group filtering
- Password via argument, env var, or prompt

### Phase 2: Update aegis-tui (COMPLETED)

#### Architecture
The TUI has 3 views that interact with aegis-cli:

1. **Password Screen**
   - Display vault selection (if needed)
   - Password entry field
   - Call `aegis-cli --json` to validate password
   - On success: proceed to OTP selection screen

2. **OTP Selection Screen (Search Mode)**
   - Call `aegis-cli --json` to get all entries
   - Display searchable list
   - Type to filter entries
   - Arrow keys to navigate
   - Enter to select and reveal OTP
   - Support group filtering via CLI arg

3. **Reveal OTP Screen**
   - Call `aegis-cli -u <uuid> --json` to get current OTP
   - Display OTP with countdown timer
   - Auto-refresh OTP every period
   - Copy to clipboard option

#### Implementation
1. Created `cli_backend.py` - wrapper module to spawn aegis-cli processes
2. Updated `aegis_main.py` to use cli_backend instead of aegis_core
3. Updated `search_mode.py` to fetch data via aegis-cli
4. Updated `tui_ui.py` (reveal mode) to fetch OTP via aegis-cli
5. Removed direct imports of aegis_core from TUI files (keep for aegis-cli)

#### cli_backend.py Functions
- `get_entries(vault_path, password)` - returns list of entry dicts
- `get_entry(uuid, vault_path, password)` - returns single entry dict
- `get_otp(uuid, vault_path, password)` - returns current OTP string

### Phase 3: Testing
- Integration testing: Pending
