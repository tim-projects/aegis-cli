import curses

try:
    import pyperclip
except ImportError:
    pass

import time
import sys
from typing import Set, Dict, List, Any

import cli_backend


def display_field(
    stdscr,
    label: str,
    value: Any,
    row_num: int,
    col_num: int,
    max_w: int,
    attr_to_use: int,
) -> int:
    line = f"{label}: {value}"
    display_line = line.ljust(max_w)[:max_w]
    stdscr.addstr(row_num, col_num, display_line, attr_to_use)
    return row_num + 1


def run_reveal_mode(
    stdscr,
    entry_to_reveal: Dict[str, Any],
    otps: Dict[str, Any],
    revealed_otps: Set[str],
    get_ttn_func,
    current_config: Dict[str, Any],
    initial_max_rows: int,
    initial_max_cols: int,
    curses_colors_enabled: bool,
    display_list: List[Dict[str, Any]],
    vault_path: str,
    password: str,
    colors: Dict[str, int],
    pyperclip_available=False,
) -> tuple[str, bool, int]:
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    current_mode = "reveal"
    running = True
    max_rows, max_cols = initial_max_rows, initial_max_cols
    selected_row = 0

    feedback_msg = ""
    feedback_expiry = 0

    last_activity_time = time.time()
    TIMEOUT_SECONDS = 60
    WARNING_SECONDS = 10

    stdscr.nodelay(True)

    stdscr.clear()

    try:
        current_entry = cli_backend.get_entry(
            entry_to_reveal["uuid"], vault_path, password
        )
        otp_to_reveal_string = current_entry.get("otp", "N/A")
        period = current_entry.get("period", 30)
        entry_timestamp_ms = current_entry.get("timestamp_ms", int(time.time() * 1000))
    except cli_backend.CLIError as e:
        otp_to_reveal_string = f"Error: {e}"
        period = 30
        entry_timestamp_ms = int(time.time() * 1000)

    last_fetch_time = entry_timestamp_ms
    last_otp = otp_to_reveal_string

    next_refresh_time = entry_timestamp_ms + (period * 1000)

    reveal_box_height = max(12, max_rows - 4)
    reveal_box_width = max(40, max_cols - 10)
    reveal_start_row = (max_rows - reveal_box_height) // 2
    reveal_start_col = (max_cols - reveal_box_width) // 2
    if reveal_start_row < 0:
        reveal_start_row = 0
    if reveal_start_col < 0:
        reveal_start_col = 0
    if reveal_box_height > max_rows:
        reveal_box_height = max_rows
    if reveal_box_width > max_cols:
        reveal_box_width = max_cols

    field_col = reveal_start_col + 2
    inner_width = reveal_box_width - 4

    stdscr.addch(reveal_start_row, reveal_start_col, curses.ACS_ULCORNER)
    stdscr.hline(
        reveal_start_row, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2
    )
    stdscr.addch(
        reveal_start_row, reveal_start_col + reveal_box_width - 1, curses.ACS_URCORNER
    )
    for r in range(reveal_start_row + 1, reveal_start_row + reveal_box_height - 1):
        stdscr.addch(r, reveal_start_col, curses.ACS_VLINE)
        stdscr.addch(r, reveal_start_col + reveal_box_width - 1, curses.ACS_VLINE)
    stdscr.addch(
        reveal_start_row + reveal_box_height - 1, reveal_start_col, curses.ACS_LLCORNER
    )
    stdscr.hline(
        reveal_start_row + reveal_box_height - 1,
        reveal_start_col + 1,
        curses.ACS_HLINE,
        reveal_box_width - 2,
    )
    stdscr.addch(
        reveal_start_row + reveal_box_height - 1,
        reveal_start_col + reveal_box_width - 1,
        curses.ACS_LRCORNER,
    )

    header_text = f"--- Revealed OTP: {entry_to_reveal['name']} ---"
    stdscr.addstr(
        reveal_start_row + 1,
        reveal_start_col + (reveal_box_width - len(header_text)) // 2,
        header_text,
        BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_BOLD,
    )

    display_row = reveal_start_row + 3
    display_row = display_field(
        stdscr,
        "Issuer",
        entry_to_reveal["issuer"],
        display_row,
        field_col,
        inner_width,
        NORMAL_TEXT_COLOR,
    )
    display_row = display_field(
        stdscr,
        "Name",
        entry_to_reveal["name"],
        display_row,
        field_col,
        inner_width,
        NORMAL_TEXT_COLOR,
    )
    display_row = display_field(
        stdscr,
        "Group",
        entry_to_reveal["groups"],
        display_row,
        field_col,
        inner_width,
        NORMAL_TEXT_COLOR,
    )
    display_row = display_field(
        stdscr,
        "Note",
        entry_to_reveal["note"],
        display_row,
        field_col,
        inner_width,
        NORMAL_TEXT_COLOR,
    )

    display_row += 1

    otp_code_display_row = display_row
    display_row = display_field(
        stdscr,
        "OTP Code",
        otp_to_reveal_string,
        otp_code_display_row,
        field_col,
        inner_width,
        REVEAL_HIGHLIGHT_COLOR,
    )

    display_row += 1

    ttn_display_row = display_row

    stdscr.refresh()

    while current_mode == "reveal" and running:
        current_time = time.time()
        current_time_ms = int(current_time * 1000)

        elapsed_idle = current_time - last_activity_time
        remaining_idle = TIMEOUT_SECONDS - elapsed_idle

        if remaining_idle <= 0:
            current_mode = "search"
            revealed_otps.clear()
            break

        p = period * 1000
        seconds_remaining = (next_refresh_time - current_time_ms) // 1000

        if current_time_ms >= next_refresh_time:
            next_refresh_time = current_time_ms + p
            try:
                current_entry = cli_backend.get_entry(
                    entry_to_reveal["uuid"], vault_path, password
                )
                new_otp_code = current_entry.get("otp", "N/A")
                period = current_entry.get("period", 30)
                last_fetch_time = current_entry.get("timestamp_ms", current_time_ms)
                next_refresh_time = last_fetch_time + (period * 1000)
                if new_otp_code != otp_to_reveal_string:
                    otp_to_reveal_string = new_otp_code
                    display_field(
                        stdscr,
                        "OTP Code",
                        otp_to_reveal_string,
                        otp_code_display_row,
                        field_col,
                        inner_width,
                        REVEAL_HIGHLIGHT_COLOR,
                    )
            except cli_backend.CLIError:
                pass

        current_ttn_value_seconds = seconds_remaining
        ttn_attr = (
            RED_TEXT_COLOR if current_ttn_value_seconds < 10 else NORMAL_TEXT_COLOR
        )
        current_ttn_value = f"{current_ttn_value_seconds:.0f}s"

        display_field(
            stdscr,
            "Next code refresh in",
            current_ttn_value,
            ttn_display_row,
            field_col,
            inner_width,
            ttn_attr,
        )

        ctrl_msg = "Enter: Copy | ESC: Return"

        if remaining_idle <= WARNING_SECONDS:
            ctrl_msg += f" | Timeout in {int(remaining_idle)}s"

        if feedback_expiry > current_time:
            ctrl_msg = feedback_msg

        ctrl_row = reveal_start_row + reveal_box_height
        if ctrl_row < max_rows:
            stdscr.move(ctrl_row, 0)
            stdscr.clrtoeol()
            stdscr.addstr(
                ctrl_row,
                reveal_start_col,
                ctrl_msg,
                NORMAL_TEXT_COLOR
                if remaining_idle > WARNING_SECONDS
                else RED_TEXT_COLOR,
            )
        else:
            stdscr.addstr(
                reveal_start_row + reveal_box_height - 2,
                reveal_start_col + 2,
                ctrl_msg[: reveal_box_width - 4],
                NORMAL_TEXT_COLOR
                if remaining_idle > WARNING_SECONDS
                else RED_TEXT_COLOR,
            )

        stdscr.refresh()

        reveal_char = stdscr.getch()

        if reveal_char != curses.ERR:
            last_activity_time = time.time()

        if reveal_char == 27:
            current_mode = "search"
            revealed_otps.clear()
            break
        elif reveal_char in [10, 13]:
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

        elif reveal_char == curses.KEY_RESIZE:
            max_rows, max_cols = stdscr.getmaxyx()
            stdscr.clear()

            reveal_box_height = max(7, max_rows - 2)
            reveal_box_width = max(30, max_cols)
            reveal_start_row = (max_rows - reveal_box_height) // 2
            reveal_start_col = (max_cols - reveal_box_width) // 2
            if reveal_start_row < 0:
                reveal_start_row = 0
            if reveal_start_col < 0:
                reveal_start_col = 0

            field_col = reveal_start_col + 2
            inner_width = reveal_box_width - 4

            stdscr.addch(reveal_start_row, reveal_start_col, curses.ACS_ULCORNER)
            stdscr.hline(
                reveal_start_row,
                reveal_start_col + 1,
                curses.ACS_HLINE,
                reveal_box_width - 2,
            )
            stdscr.addch(
                reveal_start_row,
                reveal_start_col + reveal_box_width - 1,
                curses.ACS_URCORNER,
            )
            for r in range(
                reveal_start_row + 1, reveal_start_row + reveal_box_height - 1
            ):
                stdscr.addch(r, reveal_start_col, curses.ACS_VLINE)
                stdscr.addch(
                    r, reveal_start_col + reveal_box_width - 1, curses.ACS_VLINE
                )
            stdscr.addch(
                reveal_start_row + reveal_box_height - 1,
                reveal_start_col,
                curses.ACS_LLCORNER,
            )
            stdscr.hline(
                reveal_start_row + reveal_box_height - 1,
                reveal_start_col + 1,
                curses.ACS_HLINE,
                reveal_box_width - 2,
            )
            stdscr.addch(
                reveal_start_row + reveal_box_height - 1,
                reveal_start_col + reveal_box_width - 1,
                curses.ACS_LRCORNER,
            )

            header_text = f"--- Revealed OTP: {entry_to_reveal['name']} ---"
            stdscr.addstr(
                reveal_start_row + 1,
                reveal_start_col + (reveal_box_width - len(header_text)) // 2,
                header_text,
                BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_BOLD,
            )

            display_row = reveal_start_row + 3
            display_row = display_field(
                stdscr,
                "Issuer",
                entry_to_reveal["issuer"],
                display_row,
                field_col,
                inner_width,
                NORMAL_TEXT_COLOR,
            )
            display_row = display_field(
                stdscr,
                "Name",
                entry_to_reveal["name"],
                display_row,
                field_col,
                inner_width,
                NORMAL_TEXT_COLOR,
            )
            display_row = display_field(
                stdscr,
                "Group",
                entry_to_reveal["groups"],
                display_row,
                field_col,
                inner_width,
                NORMAL_TEXT_COLOR,
            )
            display_row = display_field(
                stdscr,
                "Note",
                entry_to_reveal["note"],
                display_row,
                field_col,
                inner_width,
                NORMAL_TEXT_COLOR,
            )
            otp_code_display_row = display_row
            display_row = display_field(
                stdscr,
                "OTP Code",
                otp_to_reveal_string,
                otp_code_display_row,
                field_col,
                inner_width,
                REVEAL_HIGHLIGHT_COLOR,
            )
            ttn_display_row = display_row

            stdscr.refresh()

        elif reveal_char != curses.ERR:
            pass

        if reveal_char == curses.ERR:
            time.sleep(0.01)

    return current_mode, running, selected_row
