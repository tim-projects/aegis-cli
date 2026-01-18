import curses

def run_help_mode(stdscr, colors):
    """Displays a help screen with keybindings."""
    
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    
    max_rows, max_cols = stdscr.getmaxyx()
    
    # Help Content
    keybindings = [
        ("General", ""),
        ("  Ctrl+Q", "Exit Application"),
        ("  ?", "Show this Help Screen"),
        ("", ""),
        ("Search / Navigation Mode", ""),
        ("  j / Down", "Move Selection Down"),
        ("  k / Up", "Move Selection Up"),
        ("  /", "Enter Search Mode"),
        ("  Esc", "Clear Search / Filter"),
        ("  l / Enter", "Reveal Selected OTP"),
        ("  h", "Clear Search (if active)"),
        ("  Ctrl+C", "Copy Selected OTP (if available)"),
        ("  Ctrl+G", "Toggle Group Selection Mode"),
        ("", ""),
        ("Search Input Mode", ""),
        ("  Type...", "Filter Entries"),
        ("  Enter", "Reveal Selected OTP"),
        ("  Esc", "Exit Search Input Mode"),
        ("", ""),
        ("Group Selection Mode", ""),
        ("  j / k", "Navigate Groups"),
        ("  / ", "Search Groups"),
        ("  Enter", "Select Group"),
        ("  Esc", "Cancel Group Selection"),
        ("", ""),
        ("Reveal Mode", ""),
        ("  Esc", "Return to Search"),
        ("  Ctrl+C", "Copy Revealed OTP"),
        ("  Ctrl+Q", "Exit Application")
    ]

    # Calculate box dimensions
    box_height = min(len(keybindings) + 4, max_rows - 2)
    box_width = min(60, max_cols - 4)
    start_row = (max_rows - box_height) // 2
    start_col = (max_cols - box_width) // 2
    
    # Ensure dimensions
    if box_height < 5: box_height = 5
    if box_width < 20: box_width = 20
    if start_row < 0: start_row = 0
    if start_col < 0: start_col = 0

    while True:
        stdscr.clear()
        
        # Draw Box
        stdscr.attron(NORMAL_TEXT_COLOR)
        stdscr.addch(start_row, start_col, curses.ACS_ULCORNER)
        stdscr.hline(start_row, start_col + 1, curses.ACS_HLINE, box_width - 2)
        stdscr.addch(start_row, start_col + box_width - 1, curses.ACS_URCORNER)
        
        for r in range(start_row + 1, start_row + box_height - 1):
            stdscr.addch(r, start_col, curses.ACS_VLINE)
            stdscr.addch(r, start_col + box_width - 1, curses.ACS_VLINE)
            
        stdscr.addch(start_row + box_height - 1, start_col, curses.ACS_LLCORNER)
        stdscr.hline(start_row + box_height - 1, start_col + 1, curses.ACS_HLINE, box_width - 2)
        stdscr.addch(start_row + box_height - 1, start_col + box_width - 1, curses.ACS_LRCORNER)
        
        # Title
        title = " Help / Keybindings "
        stdscr.addstr(start_row, start_col + (box_width - len(title)) // 2, title, BOLD_WHITE_COLOR)
        
        # Content
        content_row = start_row + 1
        for key, desc in keybindings:
            if content_row >= start_row + box_height - 2: break
            
            if not desc: # Section Header
                stdscr.addstr(content_row, start_col + 2, key, BOLD_WHITE_COLOR)
            else:
                key_str = f"{key:<15}"
                stdscr.addstr(content_row, start_col + 4, key_str, NORMAL_TEXT_COLOR)
                stdscr.addstr(content_row, start_col + 20, desc, curses.A_DIM)
            content_row += 1
            
        # Footer
        footer = "Press any key to close"
        stdscr.addstr(start_row + box_height - 1, start_col + (box_width - len(footer)) // 2, footer, NORMAL_TEXT_COLOR)

        stdscr.refresh()
        
        key = stdscr.getch()
        if key != curses.ERR:
            break
            
