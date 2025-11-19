import argparse
import getpass
import os
import time
import json
from pathlib import Path

from aegis_core import find_vault_path, read_and_decrypt_vault_file, get_otps, get_ttn

# ANSI escape codes for colors
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_BOLD_WHITE = "\033[1;97m"

DEFAULT_AEGIS_VAULT_DIR = os.path.expanduser("~/.config/aegis-cli")
CONFIG_FILE_PATH = Path(DEFAULT_AEGIS_VAULT_DIR) / "config.json"

def load_config():
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                config = json.load(f)
                # Provide default values for new config keys if they don't exist
                if "last_opened_vault" not in config: config["last_opened_vault"] = None
                if "last_vault_dir" not in config: config["last_vault_dir"] = None
                if "default_color_mode" not in config: config["default_color_mode"] = True # Default to color enabled
                return config
        except json.JSONDecodeError:
            print(f"Warning: Could not parse config file {CONFIG_FILE_PATH}. Using default config.")
    return {"last_opened_vault": None, "last_vault_dir": None, "default_color_mode": True}

def save_config(config):
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def apply_color(text, color_code, no_color_flag):
    if no_color_flag:
        return text
    return f"{color_code}{text}{COLOR_RESET}"

def main():
    parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.", prog="aegis-cli")
    parser.add_argument("-v", "--vault-path", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.")
    parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument("-g", "--group", help="Filter OTP entries by a specific group name.")
    parser.add_argument("positional_vault_path", nargs="?", help=argparse.SUPPRESS, default=None)
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")

    args = parser.parse_args()

    config = load_config()
    
    # Override args.no_color if default_color_mode is false and --no-color is not explicitly set
    if not config["default_color_mode"] and not args.no_color:
        args.no_color = True

    vault_path = args.vault_path
    if not vault_path and args.positional_vault_path and args.positional_vault_path.endswith(".json"):
        vault_path = args.positional_vault_path

    if not vault_path and config["last_opened_vault"]:
        vault_path = config["last_opened_vault"]
        print(f"No vault path provided. Opening previously used vault: {vault_path}")

    if not vault_path:
        # First, try to find in the explicitly provided or default vault_dir
        print(f"Searching for vault in {os.path.abspath(args.vault_dir)}...")
        vault_path = find_vault_path(args.vault_dir)

        if not vault_path and args.vault_dir != DEFAULT_AEGIS_VAULT_DIR:
            # If not found in vault_dir, try the default Aegis config directory
            print(f"Vault not found in {os.path.abspath(args.vault_dir)}. Searching in {DEFAULT_AEGIS_VAULT_DIR}...")
            vault_path = find_vault_path(DEFAULT_AEGIS_VAULT_DIR)
            args.vault_dir = DEFAULT_AEGIS_VAULT_DIR # Update for consistent messaging

        if not vault_path:
            print("Error: No vault file found.")
            parser.print_help()
            return
        print(f"Found vault: {vault_path}")

    password = os.getenv("AEGIS_CLI_PASSWORD")
    if not password:
        try:
            try:
                password = getpass.getpass("Enter vault password: ")
            except Exception:
                print("Warning: getpass failed. Falling back to insecure password input.")
                password = input("Enter vault password (will be echoed): ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            os.system('clear')
            return

    try:
        vault_data = read_and_decrypt_vault_file(vault_path, password)
        print("Vault decrypted successfully.")
        # Save the successfully opened vault path to config
        config["last_opened_vault"] = vault_path
        config["last_vault_dir"] = os.path.dirname(vault_path)
        save_config(config)
    except ValueError as e:
        print(f"Error decrypting vault: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    if args.uuid:
        otps = get_otps(vault_data)
        if args.uuid in otps:
            otp_entry = otps[args.uuid]
            print(f"OTP for {args.uuid}: {otp_entry.string()}")
        else:
            print(f"Error: No entry found with UUID {args.uuid}.")
    else:
        try:
            revealed_otps = set() # Keep track of which OTPs are revealed
            while True:
                revealed_otps.clear() # Clear previously revealed OTPs on each refresh
                os.system('clear') # Clear the screen for each refresh
                print("--- All OTPs ---")
                
                # Recalculate OTPs for the current time, as they might change during the countdown
                otps = get_otps(vault_data)

                # Collect data and calculate max widths
                display_data = []
                max_name_len = 0
                max_issuer_len = 0
                max_group_len = 0
                max_note_len = 0

                # Create a mapping of group UUIDs to group names
                group_names = {group.uuid: group.name for group in vault_data.db.groups}

                for entry in vault_data.db.entries:
                    # Resolve group UUIDs to names
                    resolved_groups = []
                    for group_uuid in entry.groups:
                        resolved_groups.append(group_names.get(group_uuid, group_uuid)) # Fallback to UUID if name not found
                    
                    # Apply group filter if provided
                    if args.group and args.group not in resolved_groups:
                        continue

                    name = entry.name
                    issuer = entry.issuer if entry.issuer else ""
                    groups = ", ".join(resolved_groups) if resolved_groups else ""
                    note = entry.note if entry.note else ""
                    uuid = entry.uuid

                    display_data.append({
                        "name": name,
                        "issuer": issuer,
                        "groups": groups,
                        "note": note,
                        "uuid": uuid
                    })

                    if len(name) > max_name_len:
                        max_name_len = len(name)
                    if len(issuer) > max_issuer_len:
                        max_issuer_len = len(issuer)
                    if len(groups) > max_group_len:
                        max_group_len = len(groups)
                    if len(note) > max_note_len:
                        max_note_len = len(note)
                
                # Sort alphabetically by issuer
                display_data.sort(key=lambda x: x["issuer"].lower())

                # Assign 1-based index after sorting
                for i, item in enumerate(display_data):
                    item["index"] = i + 1

                # If only one item, instantly reveal it
                if len(display_data) == 1:
                    revealed_otps.add(display_data[0]["uuid"])

                # Print header
                print(f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
                print(f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")

                # Print formatted output
                for item in display_data:
                    index = item["index"]
                    name = item["name"]
                    issuer = item["issuer"]
                    groups = item["groups"]
                    note = item["note"]
                    uuid = item["uuid"]

                    otp_value = "******" # Obscure by default
                    if uuid in otps and uuid in revealed_otps:
                        otp_value = otps[uuid].string()
                    
                    # Apply coloring
                    if uuid in revealed_otps:
                        line = f"{str(index).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"
                        print(apply_color(line, COLOR_BOLD_WHITE, args.no_color))
                    else:
                        line = f"{str(index).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"
                        print(apply_color(line, COLOR_DIM, args.no_color))
                
                # Only prompt for input if there's more than one item
                if len(display_data) > 1:
                    prompt_text = "\nMake a selection to reveal the OTP code (or press Ctrl+C to exit): "
                    print(apply_color(prompt_text, COLOR_DIM, args.no_color), end='')
                    try:
                        selection = input()
                        if selection.isdigit():
                            selected_index = int(selection)
                            # Clear previously revealed OTPs and add the new one
                            revealed_otps.clear()
                            for item in display_data:
                                if item["index"] == selected_index:
                                    revealed_otps.add(item["uuid"])
                                    break
                    except KeyboardInterrupt:
                        raise # Re-raise to be caught by the outer KeyboardInterrupt handler
                    except EOFError: # Handle cases where input stream might close (e.g., non-interactive shell)
                        print(apply_color("\nNon-interactive session detected. Exiting.", COLOR_DIM, args.no_color))
                        os.system('clear')
                        return
                # If only one item and it's already revealed, just wait for countdown (no prompt needed)
                # The 'revealed_otps.add(display_data[0]["uuid"])' line above already handles revealing it.

                ttn = get_ttn()
                initial_ttn_seconds = int(ttn / 1000)

                # Countdown loop
                for remaining_seconds in range(initial_ttn_seconds, 0, -1):
                    countdown_text = f"\n\rTime until next refresh: {remaining_seconds:.1f} seconds"
                    print(apply_color(countdown_text, COLOR_DIM, args.no_color), end='')
                    time.sleep(1)
                    os.system('clear') # Clear for next second of countdown
                    print("--- All OTPs ---")
                    # Re-print header and OTPs (they don't change during the 1-second countdown)
                    print(f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
                    print(f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")
                    for item in display_data:
                        index = item["index"]
                        name = item["name"]
                        issuer = item["issuer"]
                        groups = item["groups"]
                        note = item["note"]
                        uuid = item["uuid"]

                        otp_value = "******"
                        if uuid in otps and uuid in revealed_otps:
                            otp_value = otps[uuid].string()
                        
                        # Apply coloring
                        if uuid in revealed_otps:
                            line = f"{str(index).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"
                            print(apply_color(line, COLOR_BOLD_WHITE, args.no_color))
                        else:
                            line = f"{str(index).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"
                            print(apply_color(line, COLOR_DIM, args.no_color))
        
        # This is the new block that fixes the error
        except KeyboardInterrupt:
            print("\nExiting.")
            os.system('clear')
            return

if __name__ == "__main__":
    main()
