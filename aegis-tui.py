import argparse
import getpass
import os
import time
import json
from pathlib import Path

import sys
import curses

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("Warning: pyperclip library not found. OTP copying to clipboard will not be available.")

from aegis_core import find_vault_path, read_and_decrypt_vault_file, get_otps, get_ttn



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


def cli_main(stdscr, args, password):
    stdscr.keypad(True) # Enable special keys like arrow keys
    curses.curs_set(0)  # Make the cursor invisible
    curses.noecho()     # Turn off automatic echoing of keys to the screen

    # Get terminal dimensions
    max_rows, max_cols = stdscr.getmaxyx()

    # Initialize colors
    curses_colors_enabled = False
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors() # Use default terminal background

        # Define color pairs
        # Pair 1: Default text (white on default background, but let terminal handle default foreground)
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        # Pair 2: Highlighted item (bold white text on a contrasting background, e.g., blue)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
        # Pair 3: Dim text (gray on default background, or just normal if gray isn't distinct)
        curses.init_pair(3, curses.COLOR_BLACK, -1) # Using black for 'dim' on light default backgrounds

        curses_colors_enabled = True

    # Define color attributes to be used with addstr
    DIM_COLOR = curses.color_pair(1) # Using white for 'dim' for better visibility
    BOLD_WHITE_COLOR = curses.A_BOLD | curses.color_pair(1) # For revealed OTP, bold white on default background
    HIGHLIGHT_COLOR = curses.color_pair(2) # For selected row in search mode

    config = load_config()

    
    # Override args.no_color if default_color_mode is false and --no-color is not explicitly set
    if not config["default_color_mode"] and not args.no_color:
        args.no_color = True

    vault_path = args.vault_path
    if not vault_path and args.positional_vault_path and args.positional_vault_path.endswith(".json"):
        vault_path = args.positional_vault_path

    row = 0
    if not vault_path and config["last_opened_vault"]:
        vault_path = config["last_opened_vault"]
        stdscr.addstr(row, 0, f"No vault path provided. Opening previously used vault: {vault_path}")
        row += 1
        stdscr.refresh()

    if not vault_path:
        stdscr.addstr(row, 0, f"Searching for vault in {os.path.abspath(args.vault_dir)}...")
        row += 1
        stdscr.refresh()
        vault_path = find_vault_path(args.vault_dir)

        if not vault_path and args.vault_dir != DEFAULT_AEGIS_VAULT_DIR:
            stdscr.addstr(row, 0, f"Vault not found in {os.path.abspath(args.vault_dir)}. Searching in {DEFAULT_AEGIS_VAULT_DIR}...")
            row += 1
            stdscr.refresh()
            vault_path = find_vault_path(DEFAULT_AEGIS_VAULT_DIR)
            args.vault_dir = DEFAULT_AEGIS_VAULT_DIR # Update for consistent messaging

        if not vault_path:
            stdscr.addstr(row, 0, "Error: No vault file found.")
            row += 1
            parser.print_help()
            stdscr.refresh()
            return
        stdscr.addstr(row, 0, f"Found vault: {vault_path}")
        row += 1
        stdscr.refresh()

    try:
        vault_data = read_and_decrypt_vault_file(vault_path, password)
        stdscr.addstr(row, 0, "Vault decrypted successfully.")
        row += 1
        stdscr.refresh()
        # Save the successfully opened vault path to config
        config["last_opened_vault"] = vault_path
        config["last_vault_dir"] = os.path.dirname(vault_path)
        save_config(config)
    except ValueError as e:
        stdscr.addstr(row, 0, f"Error decrypting vault: {e}")
        row += 1
        stdscr.refresh()
        time.sleep(3) # Display error message for 3 seconds before exiting
        return
    except Exception as e:
        import traceback
        stdscr.addstr(row, 0, f"An unexpected error occurred: {e}")
        row += 1
        stdscr.refresh()
        time.sleep(3) # Display error message for 3 seconds before exiting
        traceback.print_exc()
        return

    if args.uuid:
        otps = get_otps(vault_data)
        if args.uuid in otps:
            otp_entry = otps[args.uuid]
            stdscr.addstr(row, 0, f"OTP for {args.uuid}: {otp_entry.string()}")
            row += 1
            stdscr.refresh()
        else:
            stdscr.addstr(row, 0, f"Error: No entry found with UUID {args.uuid}.")
            row += 1
            stdscr.refresh()

    # Main interactive loop for search and reveal modes
    try:
        revealed_otps = set() # Keep track of which OTPs are revealed
        search_term = ""
        current_mode = "search" # Initialize mode: "search" or "reveal" or "group_select"
        selected_index_for_reveal = None # Initialize to None
        selected_row = -1 # Track the currently highlighted row for navigation (-1 for no selection)
        char = curses.ERR # Initialize char to prevent UnboundLocalError
        previous_search_term = "" # Track previous search term to detect changes
        current_group_filter = None # New: Store the currently active group filter UUID
        group_selection_mode = False # New: Flag to indicate if we are in group selection mode
        
        while True:
            stdscr.clear() # Clear the screen for each refresh
            
            otps = get_otps(vault_data)

            all_entries = []
            group_names = {group.uuid: group.name for group in vault_data.db.groups}

            # Prepare all_entries (filtered by current_group_filter if active)
            for idx, entry in enumerate(vault_data.db.entries):
                resolved_groups = []
                for group_uuid in entry.groups:
                    resolved_groups.append(group_names.get(group_uuid, group_uuid))

                # Apply group filter if active
                if current_group_filter and current_group_filter not in resolved_groups:
                    continue

                all_entries.append({
                    "index": idx,
                    "name": entry.name,
                    "issuer": entry.issuer if entry.issuer else "",
                    "groups": ", ".join(resolved_groups) if resolved_groups else "",
                    "note": entry.note if entry.note else "",
                    "uuid": entry.uuid
                })

            # Sort alphabetically by issuer
            all_entries.sort(key=lambda x: x["issuer"].lower())

            if group_selection_mode:
                # Only populate display_list with actual groups for scrolling within the box
                display_list = [{
                    "name": group.name,
                    "uuid": group.uuid
                } for group in vault_data.db.groups]
                display_list.sort(key=lambda x: x["name"].lower()) # Sort groups alphabetically

                # If "All OTPs" was previously selected, try to keep selection consistent.
                # Otherwise, reset to the first actual group.
                if current_group_filter == "-- All OTPs --":
                    selected_row = -1 # Indicate no specific group is selected from the list within the box
                elif len(display_list) > 0:
                    # Try to find the currently selected group in the new display_list
                    try:
                        selected_row = next(i for i, group in enumerate(display_list) if group["name"] == current_group_filter)
                    except StopIteration:
                        selected_row = 0 # Default to first group if not found
                else:
                    selected_row = -1

            else:
                display_list = all_entries # Use filtered entries for display

            # Adjust selected_row based on display_list (either groups or entries)
            if len(display_list) > 0:
                selected_row = max(0, min(selected_row, len(display_list) - 1))
            else:
                selected_row = -1

            # Update max lengths based on the content being displayed
            max_name_len = len("Name")
            max_issuer_len = len("Issuer")
            max_group_len = len("Group")
            max_note_len = len("Note")

            if not group_selection_mode:
                # Calculate max lengths for entries
                for item in display_list:
                    if len(item["name"]) > max_name_len: max_name_len = len(item["name"])
                    if len(item["issuer"]) > max_issuer_len: max_issuer_len = len(item["issuer"])
                    if len(item["groups"]) > max_group_len: max_group_len = len(item["groups"])
                    if len(item["note"]) > max_note_len: max_note_len = len(item["note"])
            else:
                # Calculate max lengths for groups
                for item in display_list:
                    if len(item["name"]) > max_name_len: max_name_len = len(item["name"])

            # --- Mode Management & Display ---
            entry_to_reveal = None
            group_to_filter = None

            if group_selection_mode and selected_row != -1 and (char == curses.KEY_ENTER or char in [10, 13]):
                group_to_filter = display_list[selected_row]
                current_group_filter = group_to_filter["name"]
                group_selection_mode = False # Exit group selection mode
                selected_row = 0 # Reset selection for filtered entries
            elif current_mode == "search" and selected_row != -1 and (char == curses.KEY_ENTER or char in [10, 13]):
                entry_to_reveal = all_entries[selected_row]


            if entry_to_reveal:
                if entry_to_reveal["uuid"] not in revealed_otps:
                    revealed_otps.add(entry_to_reveal["uuid"])
                current_mode = "reveal"
                # Auto-copy logic (already exists and uses PYPERCLIP_AVAILABLE)
                if PYPERCLIP_AVAILABLE:
                    otp_to_copy = otps[entry_to_reveal["uuid"]].string()
                    pyperclip.copy(otp_to_copy)
                # Reset selected_row after revealing
                selected_row = 0


            row = 0 # Reset row for each refresh
            header_row_offset = 0 # Offset for content after headers

            # Print main header based on mode, search, and group filter
            if group_selection_mode:
                stdscr.addstr(row, 0, "--- Select Group (Ctrl+G/Esc to cancel) ---")
            elif current_mode == "search":
                if current_group_filter:
                    stdscr.addstr(row, 0, f"--- Group: {current_group_filter} (Ctrl+G to clear) ---")
                elif search_term:
                    stdscr.addstr(row, 0, f"--- Search: {search_term} ---")
                elif args.group:
                    stdscr.addstr(row, 0, f"--- Group: {args.group} ---")
                else:
                    stdscr.addstr(row, 0, "--- All OTPs ---") # This will be the main header if no filters
            elif current_mode == "reveal" and len(display_list) == 1:
                 stdscr.addstr(row, 0, f"--- Revealed OTP: {display_list[0]['name']} ---")
            row += 1

            # Handle "-- All OTPs --" display in group selection mode, outside the box
            if group_selection_mode:
                all_otps_text = "-- All OTPs --"
                attribute = HIGHLIGHT_COLOR if current_group_filter is None else curses.A_NORMAL
                stdscr.addstr(row, 0, all_otps_text, attribute)
                row += 1 # Advance row after "All OTPs" line

            # Define box dimensions. Leave 1 line for top/bottom borders + 1 for input prompt.
            # We use max_rows - 1 for input prompt, so actual content height is max_rows - row - 1.
            box_start_row = row
            box_start_col = 0
            box_height = max(2, max_rows - box_start_row - 1) # Ensure min height of 2
            box_width = max(2, max_cols) # Ensure min width of 2

            # Draw the border box manually
            stdscr.attron(curses.A_NORMAL)
            stdscr.addch(box_start_row, box_start_col, curses.ACS_ULCORNER)
            stdscr.hline(box_start_row, box_start_col + 1, curses.ACS_HLINE, box_width - 2)
            stdscr.addch(box_start_row, box_start_col + box_width - 1, curses.ACS_URCORNER)

            stdscr.vline(box_start_row + 1, box_start_col, curses.ACS_VLINE, box_height - 2)
            stdscr.vline(box_start_row + 1, box_start_col + box_width - 1, curses.ACS_VLINE, box_height - 2)

            stdscr.addch(box_start_row + box_height - 1, box_start_col, curses.ACS_LLCORNER)
            stdscr.hline(box_start_row + box_height - 1, box_start_col + 1, curses.ACS_HLINE, box_width - 2)
            stdscr.addch(box_start_row + box_height - 1, box_start_col + box_width - 1, curses.ACS_LRCORNER)
            stdscr.attroff(curses.A_NORMAL)

            # Adjust row for content inside the box (after top border)
            row = box_start_row + 1 # Start printing content inside the box, below the top border

            # Print header for table (Groups or OTPs) - inside the box
            current_content_row = row # Track current row for content inside the box
            if group_selection_mode:
                stdscr.addstr(current_content_row, box_start_col + 1, f"{'#'.ljust(3)} {'Group Name'.ljust(max_name_len)}")
                current_content_row += 1
                stdscr.addstr(current_content_row, box_start_col + 1, f"{'---'.ljust(3)} {'-' * max_name_len}")
                current_content_row += 1
            else:
                stdscr.addstr(current_content_row, box_start_col + 1, f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
                current_content_row += 1
                stdscr.addstr(current_content_row, box_start_col + 1, f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")
                current_content_row += 1

            # Print formatted output - inside the box
            for i, item in enumerate(display_list): # Use enumerate to get the index for highlighting
                if current_content_row >= box_start_row + box_height - 1: # Leave space for the bottom border
                    break

                line = ""
                attribute = curses.A_NORMAL

                if group_selection_mode:
                    line = f"{str(i + 1).ljust(3)} {item['name'].ljust(max_name_len)}"
                    if curses_colors_enabled and i == selected_row:
                        attribute = HIGHLIGHT_COLOR
                else:
                    # OTP entry display logic
                    name = item["name"]
                    issuer = item["issuer"]
                    groups = item["groups"]
                    note = item["note"]
                    uuid = item["uuid"]

                    otp_value = "******" # Obscure by default
                    if uuid in otps and uuid in revealed_otps:
                        try:
                            otp_obj = otps[uuid]
                            otp_value = otp_obj.string()
                        except Exception as e:
                            otp_value = f"ERROR: {e}"
                    
                    line = f"{str(i + 1).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"

                    # Determine color attribute
                    if curses_colors_enabled:
                        if uuid in revealed_otps:
                            attribute = BOLD_WHITE_COLOR
                        elif i == selected_row and current_mode == "search": # Highlight if selected in search mode
                            attribute = HIGHLIGHT_COLOR
                        else:
                            attribute = curses.A_NORMAL
                
                stdscr.addstr(current_content_row, box_start_col + 1, line, attribute)
                current_content_row += 1
            stdscr.refresh()

            # --- Input Handling for "Search" Mode with Arrow Key Navigation ---
            ### START_INPUT_HANDLING_REFACTOR ###
            # --- Input Handling ---
            input_prompt_row = max_rows - 1
            if group_selection_mode:
                stdscr.addstr(input_prompt_row, 0, "Select a group (Enter to confirm, Ctrl+G/Esc to cancel): ")
            elif current_mode == "search":
                stdscr.addstr(input_prompt_row, 0, f"Type to filter, use arrows to select, Enter to reveal (Ctrl+G for groups, Ctrl+C to exit): {search_term}")
            stdscr.refresh()

            char = stdscr.getch() # Get a single character

            if char != curses.ERR: # Only process if a key was actually pressed
                if group_selection_mode:
                    if char == curses.KEY_UP:
                        if selected_row == 0: # If at the first group, move to "All OTPs"
                            selected_row = -1
                        elif len(display_list) > 0:
                            selected_row = max(0, selected_row - 1)
                    elif char == curses.KEY_DOWN:
                        if selected_row == -1: # If at "All OTPs", move to the first group
                            if len(display_list) > 0:
                                selected_row = 0
                        elif len(display_list) > 0:
                            selected_row = min(len(display_list) - 1, selected_row + 1)
                    elif char == 27 or char == 7: # ESC or Ctrl+G
                        group_selection_mode = False
                        current_group_filter = None
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for all entries
                        search_term = "" # Clear search term
                    elif char == curses.KEY_ENTER or char in [10, 13]:
                        if selected_row == -1: # "All OTPs" selected
                            current_group_filter = None # Clear filter
                        elif selected_row != -1 and len(display_list) > 0:
                            selected_group = display_list[selected_row]
                            current_group_filter = selected_group["name"]
                        revealed_otps.clear() # Clear revealed OTPs when a new group filter is applied or cleared
                        group_selection_mode = False
                        current_mode = "search" # Explicitly set mode to search after group selection
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for filtered entries
                        search_term = "" # Clear search term
                elif current_mode == "search": # Normal search mode
                    if char == curses.KEY_UP:
                        if len(all_entries) > 0:
                            selected_row = max(0, selected_row - 1)
                        else:
                            selected_row = -1
                    elif char == curses.KEY_DOWN:
                        if len(all_entries) > 0:
                            selected_row = min(len(all_entries) - 1, selected_row + 1)
                        else:
                            selected_row = -1
                    elif char == 27: # ESC key
                        search_term = ""
                        revealed_otps.clear()
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection
                        current_group_filter = None # Clear group filter on ESC
                    elif char in [curses.KEY_BACKSPACE, 127, 8]: # Backspace key
                        if search_term: # Only modify search_term if it's not empty
                            search_term = search_term[:-1]
                            selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for new search term evaluation
                    elif 32 <= char < 127: # Printable character
                        search_term += chr(char)
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for new search term evaluation
                    elif char == 7: # Ctrl+G
                        group_selection_mode = not group_selection_mode
                        revealed_otps.clear() # Clear revealed OTPs on mode change
                        if group_selection_mode:
                            selected_row = 0 # Reset selection for group list (first item is "All OTPs")
                        else:
                            current_group_filter = None # Clear filter if exiting group selection mode
                            selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for all entries
                        search_term = "" # Clear search term when entering/exiting group selection
                    elif char == 3: # Ctrl+C
                        raise KeyboardInterrupt
            row += 1 # Advance row after input prompt
            
            # Add a small delay if no key was pressed to prevent CPU from spinning
            if char == curses.ERR:
                time.sleep(0.1)
            ### END_INPUT_HANDLING_REFACTOR ###
            elif current_mode == "reveal": # Ensure we are still in a valid reveal state
                if not entry_to_reveal: # If we are in reveal mode but no entry was revealed, it's an error state
                    current_mode = "search"
                    continue # Go back to search
                otp_to_reveal = otps[entry_to_reveal["uuid"]].string() # Define otp_to_reveal here
                # Get the actual time to next refresh
                actual_ttn = get_ttn()

                # Loop to keep OTP revealed until ESC is pressed
                while True:
                    current_remaining_ttn = get_ttn() # Get updated ttn in each iteration
                    remaining_seconds_for_display = int(current_remaining_ttn / 1000)

                    if PYPERCLIP_AVAILABLE:
                        pyperclip.copy(otp_to_reveal)
                    stdscr.clear() # Clear for each countdown second
                    
                    countdown_row = 0 # Local row counter for reveal mode
                    stdscr.addstr(countdown_row, 0, f"--- Revealed OTP: {display_list[0]['name']} ---")
                    countdown_row += 1

                    # Define box dimensions for reveal mode. Similar logic to main loop.
                    reveal_box_start_row = countdown_row
                    reveal_box_start_col = 0
                    reveal_box_height = max(2, max_rows - reveal_box_start_row - 1) # 1 for input prompt row
                    reveal_box_width = max(2, max_cols)

                    # Draw the border box manually for reveal mode
                    stdscr.attron(curses.A_NORMAL)
                    stdscr.addch(reveal_box_start_row, reveal_box_start_col, curses.ACS_ULCORNER)
                    stdscr.hline(reveal_box_start_row, reveal_box_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
                    stdscr.addch(reveal_box_start_row, reveal_box_start_col + reveal_box_width - 1, curses.ACS_URCORNER)

                    stdscr.vline(reveal_box_start_row + 1, reveal_box_start_col, curses.ACS_VLINE, reveal_box_height - 2)
                    stdscr.vline(reveal_box_start_row + 1, reveal_box_start_col + reveal_box_width - 1, curses.ACS_VLINE, reveal_box_height - 2)

                    stdscr.addch(reveal_box_start_row + reveal_box_height - 1, reveal_box_start_col, curses.ACS_LLCORNER)
                    stdscr.hline(reveal_box_start_row + reveal_box_height - 1, reveal_box_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
                    stdscr.addch(reveal_box_start_row + reveal_box_height - 1, reveal_box_start_col + reveal_box_width - 1, curses.ACS_LRCORNER)
                    stdscr.attroff(curses.A_NORMAL)

                    # Adjust countdown_row for content inside the box
                    countdown_row = reveal_box_start_row + 1

                    stdscr.addstr(countdown_row, reveal_box_start_col + 1, f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
                    countdown_row += 1
                    stdscr.addstr(countdown_row, reveal_box_start_col + 1, f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")
                    countdown_row += 1
                    
                    # Print prefix before OTP
                    prefix = f"{str(item['index']).ljust(3)} {item['issuer'].ljust(max_issuer_len)}  {item['name'].ljust(max_name_len)}  "
                    stdscr.addstr(countdown_row, reveal_box_start_col + 1, prefix, BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_NORMAL)

                    # Print OTP with highlight
                    otp_start_col_in_box = len(prefix)
                    stdscr.addstr(countdown_row, reveal_box_start_col + 1 + otp_start_col_in_box, otp_to_reveal.ljust(6), HIGHLIGHT_COLOR if curses_colors_enabled else curses.A_NORMAL)

                    # Print suffix after OTP
                    suffix = f"  {item['groups'].ljust(max_group_len)}  {item['note'].ljust(max_note_len)}"
                    stdscr.addstr(countdown_row, reveal_box_start_col + 1 + otp_start_col_in_box + 6, suffix, BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_NORMAL)
                    countdown_row += 1

                    countdown_text = f"Time until next refresh: {remaining_seconds_for_display:.1f} seconds (Press ESC to go back)"
                    stdscr.addstr(max_rows - 1, 0, countdown_text, DIM_COLOR if curses_colors_enabled else curses.A_NORMAL) # Place at bottom
                    
                    stdscr.refresh() # Refresh screen after all updates

                    # Set timeout for getch to allow for responsive exit
                    stdscr.timeout(1000) # 1-second timeout for getch
                    char = stdscr.getch()

                    if char == 27 or char in [curses.KEY_BACKSPACE, 127, 8]: # ESC or Backspace key
                        current_mode = "search"
                        selected_index_for_reveal = None
                        break # Exit the reveal loop
                    elif char == 3: # Ctrl+C
                        raise KeyboardInterrupt
                    # If other keys are pressed, or no key, getch will return ERR after 1 second

                # After countdown finishes (either by ESC/Backspace or OTP expiration)
                stdscr.timeout(-1) # Reset timeout to blocking upon exiting reveal loop
                current_mode = "search"
                search_term = ""
                revealed_otps.clear()
                    
    except KeyboardInterrupt:
        print("\nExiting.")
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.", prog="aegis-cli")
    parser.add_argument("-v", "--vault-path", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.")
    parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument("-g", "--group", help="Filter OTP entries by a specific group name.")
    parser.add_argument("positional_vault_path", nargs="?", help=argparse.SUPPRESS, default=None)
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")

    args = parser.parse_args()

    password = os.getenv("AEGIS_CLI_PASSWORD")
    if not password:
        try:
            password = getpass.getpass("Enter vault password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0) # Exit cleanly

    curses.wrapper(cli_main, args, password)
