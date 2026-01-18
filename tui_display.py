import curses

def _calculate_column_widths(stdscr, max_cols, display_list, group_selection_mode):
    """Calculates optimal column widths for TUI display."""
    max_rows, max_cols = stdscr.getmaxyx()

    # Define box dimensions. Leave 1 line for top/bottom borders + 1 for input prompt.
    # We use max_rows - 1 for input prompt, so actual content height is max_rows - row - 1.
    # These are defined early as they are needed for content width calculations.
    # Initial row for calculations starts at 0, will be adjusted later for display.
    temp_row_for_box_calc = 0 # Temporary row to calculate initial box dimensions
    box_start_row = temp_row_for_box_calc
    box_start_col = 0
    box_height = max(2, max_rows - box_start_row - 1) # Ensure min height of 2
    box_width = max(2, max_cols) # Ensure min width of 2

    # Initialize max lengths with header lengths
    max_name_len = len("Name")
    max_issuer_len = len("Issuer")
    max_group_len = len("Group")
    max_note_len = len("Note")

    # Calculate actual max content lengths from display_list
    if not group_selection_mode: # Only for OTP entries
        for item in display_list:
            if len(item["name"]) > max_name_len: max_name_len = len(item["name"])
            if len(item["issuer"]) > max_issuer_len: max_issuer_len = len(item["issuer"])
            if len(item["groups"]) > max_group_len: max_group_len = len(item["groups"])
            if len(item["note"]) > max_note_len: max_note_len = len(item["note"])
    else: # For group names
        for item in display_list:
            if len(item["name"]) > max_name_len: max_name_len = len(item["name"])

    # Re-adjust max_len for headers to ensure they fit, using the capped values
    max_name_len = max(len("Name"), max_name_len)
    max_issuer_len = max(len("Issuer"), max_issuer_len)
    max_group_len = max(len("Group"), max_group_len)
    max_note_len = max(len("Note"), max_note_len)

    # Now, calculate available content width inside the box
    inner_box_content_width = max(0, box_width - 2) # Account for left and right borders

    # Define minimum widths for fixed elements in OTP display mode (e.g., '#', 'Code', spaces)
    fixed_otp_display_width = 1 + 3 + 3 + 3 + 1 # Space before name, '|' separators, space after note
    # Remaining width for dynamic fields (issuer, name, group, note)
    remaining_dynamic_width = max(0, inner_box_content_width - fixed_otp_display_width)

    # Define minimum widths for fixed elements in Group display mode
    fixed_group_display_width = 3 + 1 # # + space

    # Cap max lengths based on available width, prioritizing some fields over others
    # This is a heuristic to prevent overflow. Adjust ratios as needed.
    if not group_selection_mode:
        # Distribute remaining_dynamic_width. Example: Name (40%), Issuer (30%), Group (20%), Note (10%)
        # Distribute remaining_dynamic_width proportionally as a starting point
        # These are ideal maximums, actual will depend on content and final adjustment
        ideal_max_name_len = int(remaining_dynamic_width * 0.35)
        ideal_max_issuer_len = int(remaining_dynamic_width * 0.25)
        ideal_max_group_len = int(remaining_dynamic_width * 0.2)
        # Note column will take remaining space, no ideal_max_note_len needed initially

        # Cap max lengths based on ideal maximums or actual content length, whichever is smaller
        final_name_len = min(max_name_len, ideal_max_name_len)
        final_issuer_len = min(max_issuer_len, ideal_max_issuer_len)
        final_group_len = min(max_group_len, ideal_max_group_len)

        # Calculate width used by Name, Issuer, Group, and their separators
        # 1 initial space + final_name_len + 3 (' | ') + final_issuer_len + 3 (' | ') + final_group_len + 3 (' | ')
        consumed_dynamic_width = final_name_len + final_issuer_len + final_group_len + 1 + 3 + 3 + 3

        # Allocate all remaining dynamic width to the Note column
        # Ensure it doesn't go below its header length if possible, but also doesn't exceed available space
        # The remaining_dynamic_width here is the total space left for the 'note' column after others are drawn
        final_note_len = max(len("Note"), inner_box_content_width - consumed_dynamic_width - 1) # -1 for the final space after note_str

        # Update the max_len variables used for ljust
        max_name_len = final_name_len
        max_issuer_len = final_issuer_len
        max_group_len = final_group_len
        max_note_len = final_note_len
    else:
        # For group selection, the entire remaining width is for the group name
        max_name_len = min(max_name_len, max(0, inner_box_content_width - fixed_group_display_width))

    return max_name_len, max_issuer_len, max_group_len, max_note_len, inner_box_content_width, fixed_group_display_width

def draw_main_screen(
    stdscr, max_rows, max_cols, display_list, selected_row, search_term,
    current_mode, group_selection_mode, current_group_filter,
    cli_args_group, colors, curses_colors_enabled
):
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]

    stdscr.clear()  # Clear screen for each refresh

    row = 0  # Reset row for each refresh
    header_row_offset = 0  # Offset for content after headers

    # Print main header based on mode, search, and group filter
    if group_selection_mode:
        stdscr.addstr(row, 0, "--- Select Group (Ctrl+G/Esc to cancel) ---")
    elif current_mode == "search":
        if current_group_filter:
            stdscr.addstr(row, 0, f"--- Group: {current_group_filter} (Ctrl+G to clear) ---")
        elif search_term:
            stdscr.addstr(row, 0, f"--- Search: {search_term} ---")
        elif cli_args_group:
            stdscr.addstr(row, 0, f"--- Group: {cli_args_group} ---")
        else:
            stdscr.addstr(row, 0, "--- All OTPs ---")  # This will be the main header if no filters
    row += 1
    header_row_offset = row  # Remember where content starts after header

    # Draw border box for the main display area
    box_height = max_rows - header_row_offset - 2  # Account for header, prompt, and bottom border
    box_width = max_cols

    # Ensure minimum dimensions for the box
    if box_height < 2: box_height = 2
    if box_width < 2: box_width = 2

    # Top line
    stdscr.addch(row, 0, curses.ACS_ULCORNER)
    stdscr.hline(row, 1, curses.ACS_HLINE, box_width - 2)
    stdscr.addch(row, box_width - 1, curses.ACS_URCORNER)
    row += 1  # Move past the top border

    # Middle lines
    for r in range(row, row + box_height - 1):
        stdscr.addch(r, 0, curses.ACS_VLINE)
        stdscr.addch(r, box_width - 1, curses.ACS_VLINE)

    # Bottom line
    stdscr.addch(row + box_height - 1, 0, curses.ACS_LLCORNER)
    stdscr.hline(row + box_height - 1, 1, curses.ACS_HLINE, box_width - 2)
    stdscr.addch(row + box_height - 1, box_width - 1, curses.ACS_LRCORNER)

    # Reset row to start of content area, inside the box
    row = header_row_offset + 1  # Start after the top border of the box

    # Calculate column widths inside the draw_main_screen function
    max_name_len, max_issuer_len, max_group_len, max_note_len, inner_box_content_width, fixed_group_display_width = \
        _calculate_column_widths(stdscr, max_cols, display_list, group_selection_mode)

    # Display "All OTPs" in group selection mode if there are no groups, or if it's the first option
    if group_selection_mode:
        # Always show "All OTPs" as the first selectable item
        all_otps_text = "-- All OTPs --"
        display_attr = HIGHLIGHT_COLOR if selected_row == -1 else NORMAL_TEXT_COLOR
        stdscr.addstr(row, 2, all_otps_text[:inner_box_content_width - fixed_group_display_width], display_attr)
        row += 1

    # Display OTPs or Groups
    for i, item in enumerate(display_list):
        if row >= max_rows - 2:  # Leave room for prompt and bottom border
            break

        display_attr = HIGHLIGHT_COLOR if i == selected_row else NORMAL_TEXT_COLOR

        # Dynamic width adjustment for printing OTP entries or groups
        if not group_selection_mode:
            # OTP entries
            name_str = item["name"][:max_name_len].ljust(max_name_len)
            issuer_str = item["issuer"][:max_issuer_len].ljust(max_issuer_len)
            group_str = item["groups"][:max_group_len].ljust(max_group_len)
            note_str = item["note"][:max_note_len].ljust(max_note_len)

            # Construct the display line
            line = f" {name_str} | {issuer_str} | {group_str} | {note_str} "
            stdscr.addstr(row, 2, line[:inner_box_content_width], display_attr)
        else:
            # Group names
            group_name_str = item["name"][:max_name_len].ljust(max_name_len)
            line = f" {group_name_str} "
            stdscr.addstr(row, 2, line[:inner_box_content_width], display_attr)

        row += 1

    # Display search prompt/input line
    prompt_string_prefix = "Search: " if current_mode == "search" else "Group Filter: "

    # If in group selection mode, allow user to type a search term to filter groups
    current_input_text = search_term if current_mode == "search" else (search_term if group_selection_mode else "")

    # Ensure the prompt fits on the last line
    prompt_row = max_rows - 1
    if prompt_row < 0: prompt_row = 0  # Safety check for very small terminals

    stdscr.addstr(prompt_row, 0, (prompt_string_prefix + current_input_text)[:max_cols], NORMAL_TEXT_COLOR)

    # Instructions
    stdscr.addstr(max_rows - 2, 0, "Ctrl+G: Toggle Groups | ESC: Clear Search/Exit Group Select | Enter: Reveal", curses.A_DIM)

    stdscr.refresh()
