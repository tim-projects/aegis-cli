# Current Task: Decouple TUI from CLI

## Objective
Separate the CLI functionality from the TUI to create two distinct applications:
1. **aegis-cli** - A fully functioning CLI tool with no TUI dependencies
2. **aegis-tui** - A TUI that interacts with aegis-cli via `--json` mode

## Plan

### Phase 1: Create aegis-cli
Create `aegis_cli.py` with the following features:
- All core vault operations (decrypt, read entries, generate OTPs)
- `--json` mode that outputs all info as JSON objects
- Support for filtering by UUID, group
- Standard CLI output for human readability

### Phase 2: Update aegis-tui
Modify existing TUI code to:
- Spawn aegis-cli process with `--json` for data
- Parse JSON responses instead of directly calling aegis_core
- Keep TUI-specific code (curses, display, etc.) in TUI files

### Phase 3: Testing
- Verify aegis-cli works standalone
- Verify aegis-tui works via CLI backend

## Status
- **Plan creation:** Completed
- **aegis-cli creation:** Completed
- **aegis-cli testing:** Completed
- **aegis-tui update:** Pending
- **Testing:** Pending

## Completed Work
- Created `aegis-cli` (executable) with full CLI functionality:
  - Vault decryption and reading
  - `--json` mode for JSON output
  - UUID and group filtering
  - Standard CLI output for human readability
  - Password via argument, env var, or prompt
