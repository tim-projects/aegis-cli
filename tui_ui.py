import curses
import time
import sys
from typing import Set, Dict, List, Any

# Define color attributes (these will be passed as arguments, no module-level definition)

def display_field(stdscr, label: str, value: Any, row_num: int, col_num: int, max_w: int, attr_to_use: int) -> int:
    line = f"{label}: {value}"
    display_line = line[:max_w] # Truncate if too long
    
    stdscr.addstr(row_num, col_num, display_line, attr_to_use)
    return row_num + 1 # Return the next row to use

def run_reveal_mode(stdscr, entry_to_reveal: Dict[str, Any], otps: Dict[str, Any], revealed_otps: Set[str], get_ttn_func, current_config: Dict[str, Any], initial_max_rows: int, initial_max_cols: int, curses_colors_enabled: bool, display_list: List[Dict[str, Any]], vault_data, colors: Dict[str, int]) -> tuple[str, bool, int]:
    # Need to import get_otp here as it's used to regenerate the OTP object
    from aegis_core import get_otp 

    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    current_mode = "reveal"
    running = True
    max_rows, max_cols = initial_max_rows, initial_max_cols # Initial dimensions
    selected_row = 0 # Default to first item in reveal display

    stdscr.nodelay(True) # Make getch non-blocking

    # Initial full redraw for reveal mode
    # This will draw the box and all static content once.
    stdscr.clear()

    # Dynamic box dimensions for reveal mode
    reveal_box_height = max(7, max_rows - 2) # At least 7 lines for content + borders
    reveal_box_width = max(30, max_cols) # At least 30 cols

    reveal_start_row = (max_rows - reveal_box_height) // 2
    reveal_start_col = (max_cols - reveal_box_width) // 2
    
    # Ensure box dimensions are within screen limits
    if reveal_start_row < 0: reveal_start_row = 0
    if reveal_start_col < 0: reveal_start_col = 0
    if reveal_box_height > max_rows: reveal_box_height = max_rows
    if reveal_box_width > max_cols: reveal_box_width = max_cols

    # Draw border box for reveal mode
    # Top line
    stdscr.addch(reveal_start_row, reveal_start_col, curses.ACS_ULCORNER)
    stdscr.hline(reveal_start_row, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
    stdscr.addch(reveal_start_row, reveal_start_col + reveal_box_width - 1, curses.ACS_URCORNER)

    # Middle lines
    for r in range(reveal_start_row + 1, reveal_start_row + reveal_box_height - 1):
        stdscr.addch(r, reveal_start_col, curses.ACS_VLINE)
        stdscr.addch(r, reveal_start_col + reveal_box_width - 1, curses.ACS_VLINE)

    # Bottom line
    stdscr.addch(reveal_start_row + reveal_box_height - 1, reveal_start_col, curses.ACS_LLCORNER)
    stdscr.hline(reveal_start_row + reveal_box_height - 1, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
    stdscr.addch(reveal_start_row + reveal_box_height - 1, reveal_start_col + reveal_box_width - 1, curses.ACS_LRCORNER)

    # Find the original Entry object from vault_data.db.entries
    original_entry = next((entry for entry in vault_data.db.entries if entry.uuid == entry_to_reveal["uuid"]), None)
    if original_entry is None:
        # Handle error: original entry not found (should not happen if entry_to_reveal is valid)
        return "search", False, selected_row # Exit reveal mode and terminate application

    otp_object = otps[entry_to_reveal["uuid"]] # Get the actual OTP object
    otp_to_reveal_string = otp_object.string() # Initial OTP code

    # Header and OTP display (static content)
    header_text = f"--- Revealed OTP: {entry_to_reveal['name']} ---"
    stdscr.addstr(reveal_start_row + 1, reveal_start_col + (reveal_box_width - len(header_text)) // 2, header_text, BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_BOLD)

    # Display fields (static content, except for Time to Next)
    display_row = reveal_start_row + 3
    inner_width = reveal_box_width - 4 # Account for box borders and padding
    field_col = reveal_start_col + 2

    display_row = display_field(stdscr, "Issuer", entry_to_reveal["issuer"], display_row, field_col, inner_width, NORMAL_TEXT_COLOR)
    display_row = display_field(stdscr, "Name", entry_to_reveal["name"], display_row, field_col, inner_width, NORMAL_TEXT_COLOR)
    display_row = display_field(stdscr, "Group", entry_to_reveal["groups"], display_row, field_col, inner_width, NORMAL_TEXT_COLOR)
    display_row = display_field(stdscr, "Note", entry_to_reveal["note"], display_row, field_col, inner_width, NORMAL_TEXT_COLOR)
    otp_code_display_row = display_row # Store the row for OTP Code for selective updates
    display_row = display_field(stdscr, "OTP Code", otp_to_reveal_string, otp_code_display_row, field_col, inner_width, REVEAL_HIGHLIGHT_COLOR)
    # Store the row for Time to Next for selective updates
    ttn_display_row = display_row 

    # Controls (static content)
    stdscr.addstr(reveal_start_row + reveal_box_height - 2, reveal_start_col + 2, "Press ESC to return to search, Ctrl+C to exit.", NORMAL_TEXT_COLOR)
    
    # Initial refresh after drawing all static content
    stdscr.refresh()

    while current_mode == "reveal" and running:
        # Check if OTP needs to be refreshed
        time_to_next_ms = get_ttn_func()
        if time_to_next_ms <= 0: # OTP has expired or is about to expire
            # Regenerate the otp_object to ensure a fresh OTP for the new time window
            otp_object = get_otp(original_entry) 
            new_otp_code = otp_object.string() # Regenerate OTP
            if new_otp_code != otp_to_reveal_string: # Only redraw if the code has actually changed
                otp_to_reveal_string = new_otp_code
                # Clear the old OTP Code line before redrawing
                otp_code_display_row_current = ttn_display_row - 1 # Recalculate based on current ttn_display_row
                stdscr.move(otp_code_display_row_current, field_col)
                stdscr.clrtoeol()
                display_field(stdscr, "OTP Code", otp_to_reveal_string, otp_code_display_row_current, field_col, inner_width, REVEAL_HIGHLIGHT_COLOR)

        # Only update the "Time to Next" field
        current_ttn_value_seconds = time_to_next_ms / 1000
        ttn_attr = RED_TEXT_COLOR if current_ttn_value_seconds < 10 else NORMAL_TEXT_COLOR
        current_ttn_value = f"{current_ttn_value_seconds:.0f}s" # Format to 0 decimal places
        # Clear the old "Time to Next" line before redrawing
        stdscr.move(ttn_display_row, field_col)
        stdscr.clrtoeol()
        display_field(stdscr, "Time to Next", current_ttn_value, ttn_display_row, field_col, inner_width, ttn_attr)

        stdscr.refresh() # Only refresh the updated portion

        reveal_char = stdscr.getch()
        if reveal_char == 27: # ESC key
            current_mode = "search"
            revealed_otps.clear()
            # Do not reset selected_row here, maintain selection from search mode
            break # Exit reveal loop
        elif reveal_char == 3: # Ctrl+C
            running = False
            break # Exit reveal loop and signal main loop to exit
        elif reveal_char == curses.KEY_RESIZE: # Handle terminal resize event
            max_rows, max_cols = stdscr.getmaxyx() # Update dimensions
            # Trigger a full redraw for reveal mode by clearing and redrawing all static and dynamic elements
            stdscr.clear()
            # Re-calculate and redraw static elements of the box and fields
            reveal_box_height = max(7, max_rows - 2)
            reveal_box_width = max(30, max_cols)
            reveal_start_row = (max_rows - reveal_box_height) // 2
            reveal_start_col = (max_cols - reveal_box_width) // 2
            if reveal_start_row < 0: reveal_start_row = 0
            if reveal_start_col < 0: reveal_start_col = 0
            if reveal_box_height > max_rows: reveal_box_height = max_rows
            if reveal_box_width > max_cols: reveal_box_width = max_cols

            stdscr.addch(reveal_start_row, reveal_start_col, curses.ACS_ULCORNER)
            stdscr.hline(reveal_start_row, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
            stdscr.addch(reveal_start_row, reveal_start_col + reveal_box_width - 1, curses.ACS_URCORNER)
            for r in range(reveal_start_row + 1, reveal_start_row + reveal_box_height - 1):
                stdscr.addch(r, reveal_start_col, curses.ACS_VLINE)
                stdscr.addch(r, reveal_start_col + reveal_box_width - 1, curses.ACS_VLINE)
            stdscr.addch(reveal_start_row + reveal_box_height - 1, reveal_start_col, curses.ACS_LLCORNER)
            stdscr.hline(reveal_start_row + reveal_box_height - 1, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
            stdscr.addch(reveal_start_row + reveal_box_height - 1, reveal_start_col + reveal_box_width - 1, curses.ACS_LRCORNER)

            header_text = f"--- Revealed OTP: {entry_to_reveal['name']} ---"
            stdscr.addstr(reveal_start_row + 1, reveal_start_col + (reveal_box_width - len(header_text)) // 2, header_text, BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_BOLD)
            
            display_row_static = reveal_start_row + 3
            display_row_static = display_field(stdscr, "Issuer", entry_to_reveal["issuer"], display_row_static, field_col, inner_width, NORMAL_TEXT_COLOR)
            display_row_static = display_field(stdscr, "Name", entry_to_reveal["name"], display_row_static, field_col, inner_width, NORMAL_TEXT_COLOR)
            display_row_static = display_field(stdscr, "Group", entry_to_reveal["groups"], display_row_static, field_col, inner_width, NORMAL_TEXT_COLOR)
            display_row_static = display_field(stdscr, "Note", entry_to_reveal["note"], display_row_static, field_col, inner_width, NORMAL_TEXT_COLOR)
            otp_code_display_row_static = display_row_static # Store the row for OTP Code for selective updates on resize
            display_row_static = display_field(stdscr, "OTP Code", otp_to_reveal_string, otp_code_display_row_static, field_col, inner_width, REVEAL_HIGHLIGHT_COLOR)
            ttn_display_row = display_row_static # Update ttn_display_row after redraw
            stdscr.addstr(reveal_start_row + reveal_box_height - 2, reveal_start_col + 2, "Press ESC to return to search, Ctrl+C to exit.", NORMAL_TEXT_COLOR)

            stdscr.refresh()

        elif reveal_char != curses.ERR: # Any other key press, clear revealed OTP and return to search
            current_mode = "search"
            revealed_otps.clear()
            break # Exit reveal loop
        
        # Add a small delay if no key was pressed to prevent CPU from spinning
        if reveal_char == curses.ERR:
            time.sleep(0.01) # Shorter sleep for reveal mode responsiveness

    return current_mode, running, selected_row # Return selected_row as well
