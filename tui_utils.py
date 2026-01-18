import curses

def init_colors(stdscr, no_color_arg):
    """
    Initializes curses color pairs and returns them along with a flag indicating
    if colors are enabled.
    """
    curses_colors_enabled = False
    NORMAL_TEXT_COLOR = curses.A_NORMAL
    HIGHLIGHT_COLOR = curses.A_REVERSE
    REVEAL_HIGHLIGHT_COLOR = curses.A_NORMAL # Default in case colors are off
    RED_TEXT_COLOR = curses.A_NORMAL       # Default in case colors are off
    BOLD_WHITE_COLOR = curses.A_NORMAL     # Default in case colors are off

    if curses.has_colors() and not no_color_arg:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1) # Normal text, default background
        curses.init_pair(2, curses.COLOR_CYAN, -1)  # Highlight, default background
        curses.init_pair(3, curses.COLOR_GREEN, -1) # OTP green
        curses.init_pair(4, curses.COLOR_YELLOW, -1) # REVEAL_HIGHLIGHT_COLOR
        curses.init_pair(5, curses.COLOR_RED, -1)    # RED_TEXT_COLOR

        NORMAL_TEXT_COLOR = curses.color_pair(1)
        HIGHLIGHT_COLOR = curses.color_pair(2)
        OTP_GREEN_COLOR = curses.color_pair(3)
        REVEAL_HIGHLIGHT_COLOR = curses.color_pair(4)
        RED_TEXT_COLOR = curses.color_pair(5)
        BOLD_WHITE_COLOR = curses.A_BOLD | NORMAL_TEXT_COLOR
        curses_colors_enabled = True
    else:
        OTP_GREEN_COLOR = curses.A_NORMAL # Default in case colors are off

    return {
        "NORMAL_TEXT_COLOR": NORMAL_TEXT_COLOR,
        "HIGHLIGHT_COLOR": HIGHLIGHT_COLOR,
        "OTP_GREEN_COLOR": OTP_GREEN_COLOR,
        "REVEAL_HIGHLIGHT_COLOR": REVEAL_HIGHLIGHT_COLOR,
        "RED_TEXT_COLOR": RED_TEXT_COLOR,
        "BOLD_WHITE_COLOR": BOLD_WHITE_COLOR
    }, curses_colors_enabled
