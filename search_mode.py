import curses
try:
    import pyperclip
except ImportError:
    pass

from tui_display import draw_main_screen
from help_mode import run_help_mode

def run_search_mode(
    stdscr, vault_data, group_names, args, colors, curses_colors_enabled, otps, pyperclip_available
):
    """Runs the interactive search mode for OTP entries."""

    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    # Initialize state variables
    search_term = ""
    current_mode = "search" # "search" or "group_select"
    in_search_mode = False # Start in navigation mode
    status_message = ""
    
    selected_row = -1 # Track the currently highlighted row for navigation (-1 for no selection)
    char = curses.ERR # Initialize char to prevent UnboundLocalError
    previous_search_term = ""
    current_group_filter = args.group # Use CLI group filter if provided
    group_selection_mode = False
    entry_to_reveal_uuid = None # Store the UUID of the selected entry
    needs_redraw = True # Initial redraw needed

    # Prepare initial data based on CLI arguments (group filter)
    all_entries = []
    for i, entry in enumerate(vault_data.db.entries):
        all_entries.append({
            "index": i,
            "name": entry.name,
            "issuer": entry.issuer if entry.issuer else "",
            "groups": ", ".join(group_names.get(g, g) for g in entry.groups) if entry.groups else "",
            "note": entry.note if entry.note else "",
            "uuid": entry.uuid
        })
    all_entries.sort(key=lambda x: x["name"].lower())

    if current_group_filter:
        # Apply initial group filter
        display_list_for_selection = [entry for entry in all_entries if current_group_filter in entry["groups"]]
    else:
        display_list_for_selection = all_entries

    # Ensure selected_row is valid for the initial display
    if len(display_list_for_selection) > 0:
        selected_row = 0
    else:
        selected_row = -1

    scroll_offset = 0
    items_per_page = 10 # Initial estimate, will be updated by draw_main_screen

    # --- Main Search Loop ---
    while True:
        # Prepare display list based on current mode and filters
        if current_mode == "search" and not group_selection_mode:
            term = search_term.lower()
            if current_group_filter:
                display_list = [
                    entry for entry in all_entries 
                    if current_group_filter in entry["groups"] and 
                    (term in entry["name"].lower() or term in entry["issuer"].lower())
                ]
            else:
                display_list = [
                    entry for entry in all_entries 
                    if term in entry["name"].lower() or term in entry["issuer"].lower()
                ]
        elif group_selection_mode:
            # In group selection mode, display available groups
            groups_list = [{"name": group.name, "uuid": group.uuid} for group in vault_data.db.groups]
            groups_list.sort(key=lambda x: x["name"].lower()) # Sort groups alphabetically

            # Filter groups by search_term if in group selection mode
            if search_term:
                display_list = [group for group in groups_list if search_term.lower() in group["name"].lower()]
            else:
                display_list = groups_list # No search term, show all groups

            # Adjust selected_row for group list
        else:
            display_list = all_entries # Use filtered entries for display

        # If no items are in display_list, reset selected_row
        if len(display_list) == 0:
            if not group_selection_mode:
                selected_row = -1
            else:
                if selected_row != -1:
                     selected_row = -1
        else:
            # Ensure selected_row is within bounds for the current display_list
            selected_row = max(-1 if group_selection_mode else 0, min(selected_row, len(display_list) - 1))

        if needs_redraw:
            max_rows, max_cols = stdscr.getmaxyx()
            items_per_page = draw_main_screen(
                stdscr, max_rows, max_cols, display_list, selected_row, search_term,
                current_mode, group_selection_mode, current_group_filter, args.group,
                colors, curses_colors_enabled, scroll_offset,
                in_search_mode, status_message
            )
            needs_redraw = False # Redraw completed
            status_message = "" # Clear status message after drawing once (or keep it? Flashing is better)
            # Actually, if we clear it here, it will be visible for one frame. We should clear it on NEXT input.
            # But draw_main_screen is called inside the loop.
            # Let's not clear it here. Clear it on keypress.

        # --- Input Handling ---
        char = stdscr.getch() # Get a single character

        if char != curses.ERR: # Only process if a key was actually pressed
            needs_redraw = True # Input occurred, so redraw the screen
            status_message = "" # Clear previous status message on new input
            
            if char == curses.KEY_RESIZE:
                # Terminal resized, re-get dimensions and force redraw
                max_rows, max_cols = stdscr.getmaxyx()
                continue
            
            # --- Global Hotkeys ---
            if char == 17: # Ctrl+Q to exit
                return None
            
            if char == ord('?'): # Help
                run_help_mode(stdscr, colors)
                needs_redraw = True
                continue
            
            if char == 3: # Ctrl+C to copy
                if pyperclip_available and selected_row != -1 and len(display_list) > 0:
                    try:
                        # Get UUID based on current selection
                        if group_selection_mode:
                             pass # No copy for groups
                        else:
                             uuid = display_list[selected_row]["uuid"]
                             otp = otps[uuid]
                             pyperclip.copy(otp.string())
                             status_message = "OTP copied to clipboard!"
                    except Exception as e:
                        status_message = f"Copy failed: {str(e)}"
                elif not pyperclip_available:
                     status_message = "Clipboard unavailable."
                continue

            # --- Navigation (Common logic for j/k/UP/DOWN) ---
            move_down = False
            move_up = False
            
            if char == curses.KEY_DOWN:
                move_down = True
            elif char == curses.KEY_UP:
                move_up = True
            elif not in_search_mode:
                if char == ord('j'): move_down = True
                elif char == ord('k'): move_up = True
            
            if move_down:
                if group_selection_mode:
                     current_v_idx = selected_row + 1
                     total_virtual_items = len(display_list) + 1
                     if current_v_idx < total_virtual_items - 1:
                         selected_row = current_v_idx # (v_idx + 1) - 1
                         if selected_row + 1 >= scroll_offset + items_per_page:
                             scroll_offset = selected_row + 1 - items_per_page + 1
                else:
                    if len(display_list) > 0:
                        selected_row = min(len(display_list) - 1, selected_row + 1)
                        if selected_row >= scroll_offset + items_per_page:
                            scroll_offset = selected_row - items_per_page + 1
                continue
                
            if move_up:
                if group_selection_mode:
                    current_v_idx = selected_row + 1
                    if current_v_idx > 0:
                        selected_row = current_v_idx - 2 # (v_idx - 1) - 1
                        if selected_row + 1 < scroll_offset:
                            scroll_offset = selected_row + 1
                else:
                    if len(display_list) > 0:
                        selected_row = max(0, selected_row - 1)
                        if selected_row < scroll_offset:
                            scroll_offset = selected_row
                continue

            # --- Mode Specific Handling ---
            if group_selection_mode:
                 if char == 27 or char == 7 or (not in_search_mode and char == ord('h')): # ESC/Ctrl+G/h
                    group_selection_mode = False
                    current_group_filter = None
                    search_term = ""
                    selected_row = 0 if len(all_entries) > 0 else -1
                    scroll_offset = 0
                    in_search_mode = False
                 elif char == ord('/') and not in_search_mode:
                    in_search_mode = True
                 elif char == curses.KEY_ENTER or char in [10, 13] or (not in_search_mode and char == ord('l')):
                    if selected_row == -1:
                        current_group_filter = None
                    elif selected_row != -1 and len(display_list) > 0:
                        selected_group = display_list[selected_row]
                        current_group_filter = selected_group["name"]
                    group_selection_mode = False
                    current_mode = "search"
                    initial_filtered_entries = [entry for entry in all_entries if current_group_filter in entry["groups"]] if current_group_filter else all_entries
                    selected_row = 0 if len(initial_filtered_entries) > 0 else -1
                    scroll_offset = 0
                    search_term = ""
                    in_search_mode = False
                 elif in_search_mode:
                     # Typing logic
                     if char in [curses.KEY_BACKSPACE, 127, 8]:
                        if search_term:
                            search_term = search_term[:-1]
                            scroll_offset = 0
                     elif 32 <= char < 127:
                        search_term += chr(char)
                        scroll_offset = 0
                     elif char == 27: # Esc exits search mode
                        in_search_mode = False

            else: # Normal OTP List Mode
                 if char == ord('/') and not in_search_mode:
                     in_search_mode = True
                 elif char == 27: # ESC
                     if in_search_mode:
                         in_search_mode = False
                     else:
                         search_term = ""
                         current_group_filter = None
                         selected_row = 0 if len(all_entries) > 0 else -1
                         scroll_offset = 0
                 elif not in_search_mode and char == ord('h'):
                     # Clear search if present
                     if search_term:
                         search_term = ""
                         scroll_offset = 0
                 elif char == 7: # Ctrl+G
                     group_selection_mode = not group_selection_mode
                     if group_selection_mode:
                         selected_row = -1
                         search_term = ""
                         scroll_offset = 0
                         in_search_mode = False
                 elif char == curses.KEY_ENTER or char in [10, 13] or (not in_search_mode and char == ord('l')):
                     if selected_row != -1 and len(display_list) > 0:
                         entry_to_reveal_uuid = display_list[selected_row]["uuid"]
                         break
                 elif in_search_mode:
                     if char in [curses.KEY_BACKSPACE, 127, 8]:
                        if search_term:
                            search_term = search_term[:-1]
                            scroll_offset = 0
                     elif 32 <= char < 127:
                        search_term += chr(char)
                        scroll_offset = 0

        else:
            import time
            time.sleep(0.01) # Small delay to prevent tight loop if no input

    # Return the selected UUID or None if user exited
    return entry_to_reveal_uuid
