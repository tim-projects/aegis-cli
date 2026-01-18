import curses
try:
    import pyperclip
except ImportError:
    pass

import time
import sys
from typing import Set, Dict, List, Any

# Define color attributes (these will be passed as arguments, no module-level definition)

def display_field(stdscr, label: str, value: Any, row_num: int, col_num: int, max_w: int, attr_to_use: int) -> int:
    line = f"{label}: {value}"
    # Pad with spaces to clear previous content, but clip to max_w to protect borders
    display_line = line.ljust(max_w)[:max_w]
    
    stdscr.addstr(row_num, col_num, display_line, attr_to_use)
    return row_num + 1 # Return the next row to use

def run_reveal_mode(stdscr, entry_to_reveal: Dict[str, Any], otps: Dict[str, Any], revealed_otps: Set[str], get_ttn_func, current_config: Dict[str, Any], initial_max_rows: int, initial_max_cols: int, curses_colors_enabled: bool, display_list: List[Dict[str, Any]], vault_data, colors: Dict[str, int], pyperclip_available=False) -> tuple[str, bool, int]:
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
    
    feedback_msg = ""
    feedback_expiry = 0
    
    last_activity_time = time.time()
    TIMEOUT_SECONDS = 60
    WARNING_SECONDS = 10

    stdscr.nodelay(True) # Make getch non-blocking

    # Initial full redraw for reveal mode
    # This will draw the box and all static content once.
    stdscr.clear()

    # ... (Keep existing layout logic) ...

    while current_mode == "reveal" and running:
        current_time = time.time()
        
        # Check Inactivity Timeout
        elapsed_idle = current_time - last_activity_time
        remaining_idle = TIMEOUT_SECONDS - elapsed_idle
        
        if remaining_idle <= 0:
            current_mode = "search"
            revealed_otps.clear()
            break

        # Check if OTP needs to be refreshed
        time_to_next_ms = get_ttn_func()
        if time_to_next_ms <= 0: # OTP has expired or is about to expire
            # ... (Keep existing OTP refresh logic) ...
            if new_otp_code != otp_to_reveal_string: # Only redraw if the code has actually changed
                otp_to_reveal_string = new_otp_code
                # Clear the old OTP Code line before redrawing
                otp_code_display_row_current = ttn_display_row - 1 # Recalculate based on current ttn_display_row
                # Removed clrtoeol to protect border
                display_field(stdscr, "OTP Code", otp_to_reveal_string, otp_code_display_row_current, field_col, inner_width, REVEAL_HIGHLIGHT_COLOR)

        # Only update the "Time to Next" field
        current_ttn_value_seconds = time_to_next_ms / 1000
        ttn_attr = RED_TEXT_COLOR if current_ttn_value_seconds < 10 else NORMAL_TEXT_COLOR
        current_ttn_value = f"{current_ttn_value_seconds:.0f}s" # Format to 0 decimal places
        # Clear the old "Time to Next" line before redrawing
        # Removed clrtoeol to protect border. display_field now handles padding.
        display_field(stdscr, "Next code refresh in", current_ttn_value, ttn_display_row, field_col, inner_width, ttn_attr)
        
        # Display Controls or Feedback
        ctrl_msg = "Ctrl+C: Copy | Ctrl+Q: Exit | ESC: Return"
        
        # Append warning if timeout is imminent
        if remaining_idle <= WARNING_SECONDS:
            ctrl_msg += f" | Timeout in {int(remaining_idle)}s"

        if feedback_expiry > current_time:
             ctrl_msg = feedback_msg
        
        ctrl_row = reveal_start_row + reveal_box_height
        # Clear line before printing control message to handle varying lengths
        if ctrl_row < max_rows:
            stdscr.move(ctrl_row, 0)
            stdscr.clrtoeol()
            stdscr.addstr(ctrl_row, reveal_start_col, ctrl_msg, NORMAL_TEXT_COLOR if remaining_idle > WARNING_SECONDS else RED_TEXT_COLOR)
        else:
             # Inside box fallback
            stdscr.move(reveal_start_row + reveal_box_height - 2, reveal_start_col + 2)
            # Need to clear strictly inside
            blank = " " * (reveal_box_width - 4)
            stdscr.addstr(reveal_start_row + reveal_box_height - 2, reveal_start_col + 2, blank, NORMAL_TEXT_COLOR)
            stdscr.addstr(reveal_start_row + reveal_box_height - 2, reveal_start_col + 2, ctrl_msg[:reveal_box_width-4], NORMAL_TEXT_COLOR if remaining_idle > WARNING_SECONDS else RED_TEXT_COLOR)

        stdscr.refresh() # Only refresh the updated portion

        reveal_char = stdscr.getch()
        
        if reveal_char != curses.ERR:
            last_activity_time = time.time() # Reset inactivity timer on any input

        if reveal_char == 27: # ESC key
            current_mode = "search"
            revealed_otps.clear()
            # Do not reset selected_row here, maintain selection from search mode
            break # Exit reveal loop
        elif reveal_char == 17: # Ctrl+Q
            running = False
            break
        elif reveal_char == 3: # Ctrl+C
             # Copy Logic
             if pyperclip_available:
                 try:
                     pyperclip.copy(otp_to_reveal_string)
                     feedback_msg = "Copied to clipboard!"
                     feedback_expiry = time.time() + 2
                 except Exception:
                     feedback_msg = "Copy failed."
                     feedback_expiry = time.time() + 2
             else:
                 feedback_msg = "Clipboard unavailable."
                 feedback_expiry = time.time() + 2
        
        elif reveal_char == curses.KEY_RESIZE: # Handle terminal resize event
            # ... (Rest of resize logic is implicit, but I need to make sure I don't cut off the function)
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
            
            # Note: Control message is handled in the loop logic now

            stdscr.refresh()

        elif reveal_char != curses.ERR: # Any other key press, clear revealed OTP and return to search
            # Optional: Allow j/k to scroll if we implemented scrolling, but for now just exit on other keys or ignore?
            # Original logic was: any key exits.
            # New logic: Only Esc exits? Or any key?
            # User wants j/k nav in search mode. In reveal mode, usually static.
            # Let's keep "Esc to return" strict? Or any key?
            # Ctrl+C/Q are handled.
            # Let's default to: Esc returns. Other keys ignored?
            # The prompt says "Press ESC to return".
            # If I make *any* key return, Ctrl+C handling might be tricky if not prioritized.
            # I handled Ctrl+C/Q specifically.
            # Let's ignore other keys to prevent accidental exit when trying to copy.
            pass
        
        # Add a small delay if no key was pressed to prevent CPU from spinning
        if reveal_char == curses.ERR:
            time.sleep(0.01) # Shorter sleep for reveal mode responsiveness

    return current_mode, running, selected_row # Return selected_row as well
