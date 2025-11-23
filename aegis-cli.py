import argparse
import getpass
import os
import time
import json
from pathlib import Path
import readchar

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
            os.system("clear")
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
            search_term = ""
            while True:
                os.system("clear") # Clear the screen for each refresh
                print("--- All OTPs ---")
                
                otps = get_otps(vault_data)

                display_data = []
                max_name_len = len("Name")
                max_issuer_len = len("Issuer")
                max_group_len = len("Group")
                max_note_len = len("Note")

                group_names = {group.uuid: group.name for group in vault_data.db.groups}

                all_entries = []
                for entry in vault_data.db.entries:
                    resolved_groups = []
                    for group_uuid in entry.groups:
                        resolved_groups.append(group_names.get(group_uuid, group_uuid))
                    
                    if args.group and args.group not in resolved_groups:
                        continue

                    all_entries.append({
                        "name": entry.name,
                        "issuer": entry.issuer if entry.issuer else "",
                        "groups": ", ".join(resolved_groups) if resolved_groups else "",
                        "note": entry.note if entry.note else "",
                        "uuid": entry.uuid
                    })
                
                # Sort alphabetically by issuer
                all_entries.sort(key=lambda x: x["issuer"].lower())

                # Apply search filter
                filtered_entries = []
                for i, item in enumerate(all_entries):
                    item["index"] = i + 1 # Assign 1-based index
                    search_string_match = (
                        search_term.lower() in item["name"].lower() or
                        search_term.lower() in item["issuer"].lower() or
                        search_term.lower() in item["groups"].lower() or
                        search_term.lower() in item["note"].lower()
                    )
                    # Also allow searching by index number
                    if search_term.isdigit() and int(search_term) == item["index"]:
                        search_string_match = True

                    if not search_term or search_string_match:
                        filtered_entries.append(item)
                
                display_data = filtered_entries

                for item in display_data:
                    if len(item["name"]) > max_name_len:
                        max_name_len = len(item["name"])
                    if len(item["issuer"]) > max_issuer_len:
                        max_issuer_len = len(item["issuer"])
                    if len(item["groups"]) > max_group_len:
                        max_group_len = len(item["groups"])
                    if len(item["note"]) > max_note_len:
                        max_note_len = len(item["note"])

                # Conditional OTP revelation and clearing based on filtered results
                if len(display_data) == 1:
                    if display_data[0]["uuid"] not in revealed_otps:
                        revealed_otps.add(display_data[0]["uuid"])
                elif len(display_data) != 1 and len(revealed_otps) > 0:
                    revealed_otps.clear()

                # Print header
                print(f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}", flush=True)
                print(f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}", flush=True)

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
                        print(apply_color(line, COLOR_BOLD_WHITE, args.no_color), flush=True) # Added flush=True
                    else:
                        line = f"{str(index).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"
                        print(apply_color(line, COLOR_DIM, args.no_color), flush=True) # Added flush=True

                print(f"\nType the name or line number to reveal OTP code (Ctrl+C to exit): {search_term}", end='', flush=True)
                
                try:
                    key = readchar.readkey()
                    if key == readchar.key.BACKSPACE:
                        search_term = search_term[:-1]
                    elif key == readchar.key.CTRL_C:
                        raise KeyboardInterrupt
                    elif key == readchar.key.ESC: # Handle Esc key to clear search term
                        search_term = ""
                        revealed_otps.clear() # Clear revealed OTPs on filter reset
                    elif key == readchar.key.ENTER:
                        # If enter is pressed and there is exactly one filtered entry, reveal it
                        if len(filtered_entries) == 1 and filtered_entries[0]["uuid"] not in revealed_otps:
                            revealed_otps.add(filtered_entries[0]["uuid"])
                        # If enter is pressed and there is more than one entry, or no entry, or already revealed, do nothing.
                    else:
                        search_term += key

                except KeyboardInterrupt:
                    raise # Re-raise to be caught by the outer KeyboardInterrupt handler
                except EOFError: # Handle cases where input stream might close (e.g., non-interactive shell)
                    print(apply_color("\nNon-interactive session detected. Exiting.", COLOR_DIM, args.no_color), flush=True)
                    os.system('clear')
                    return

                # Conditional Countdown loop
                if len(display_data) == 1 and display_data[0]["uuid"] in revealed_otps:
                    ttn = get_ttn()
                    initial_ttn_seconds = int(ttn / 1000)

                    for remaining_seconds in range(initial_ttn_seconds, 0, -1):
                        countdown_text = f"\n\rTime until next refresh: {remaining_seconds:.1f} seconds"
                        print(apply_color(countdown_text, COLOR_DIM, args.no_color), end='', flush=True) # Added flush=True
                        time.sleep(1)
                        os.system('clear') # Clear for next second of countdown
                        print("--- All OTPs ---", flush=True) # Added flush=True
                        # Recalculate OTPs for the current time, as they might change during the countdown
                        otps = get_otps(vault_data)
                        # Re-print header and OTPs (logic for re-printing header and OTPs already exists in the main loop)
                        print(f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}", flush=True)
                        print(f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}", flush=True)
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
                                print(apply_color(line, COLOR_BOLD_WHITE, args.no_color), flush=True)
                            else:
                                line = f"{str(index).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"
                                print(apply_color(line, COLOR_DIM, args.no_color), flush=True)
        
        except KeyboardInterrupt:
            print("\nExiting.")
            os.system('clear')
            return

if __name__ == "__main__":
    main()