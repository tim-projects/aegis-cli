import argparse
import os
import sys
import curses

try:
    import pyperclip

    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print(
        "Warning: pyperclip library not found. OTP copying to clipboard will not be available."
    )

import cli_backend
from tui_ui import run_reveal_mode
from config import load_config, save_config, DEFAULT_AEGIS_VAULT_DIR
from search_mode import run_search_mode
from tui_utils import init_colors
from aegis_core import find_vault_path


def cli_main(stdscr, args, password):
    stdscr.keypad(True)

    max_rows, max_cols = stdscr.getmaxyx()

    colors, curses_colors_enabled = init_colors(stdscr, args.no_color)
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    config = load_config()

    if not config["default_color_mode"] and not args.no_color:
        args.no_color = True

    vault_path = args.vault_path

    if not vault_path and config["last_opened_vault"]:
        vault_path = config["last_opened_vault"]

    if not vault_path:
        vault_path = find_vault_path(args.vault_dir)

        if not vault_path and args.vault_dir != DEFAULT_AEGIS_VAULT_DIR:
            vault_path = find_vault_path(DEFAULT_AEGIS_VAULT_DIR)
            args.vault_dir = DEFAULT_AEGIS_VAULT_DIR

        if not vault_path:
            stdscr.addstr(0, 0, "Error: No vault file found. Exiting.")
            stdscr.refresh()
            curses.napms(2000)
            return

    row = 0
    stdscr.clear()

    vault_name = os.path.basename(vault_path)
    pwd_input = []
    last_esc_time = 0

    while True:
        max_rows, max_cols = stdscr.getmaxyx()

        stdscr.clear()

        box_height = 9
        box_width = max(50, max_cols - 10)
        start_row = (max_rows - box_height) // 2
        start_col = (max_cols - box_width) // 2
        if start_row < 0:
            start_row = 0
        if start_col < 0:
            start_col = 0

        stdscr.addch(start_row, start_col, curses.ACS_ULCORNER)
        stdscr.hline(start_row, start_col + 1, curses.ACS_HLINE, box_width - 2)
        stdscr.addch(start_row, start_col + box_width - 1, curses.ACS_URCORNER)
        for r in range(start_row + 1, start_row + box_height - 1):
            stdscr.addch(r, start_col, curses.ACS_VLINE)
            stdscr.addch(r, start_col + box_width - 1, curses.ACS_VLINE)
        stdscr.addch(start_row + box_height - 1, start_col, curses.ACS_LLCORNER)
        stdscr.hline(
            start_row + box_height - 1, start_col + 1, curses.ACS_HLINE, box_width - 2
        )
        stdscr.addch(
            start_row + box_height - 1, start_col + box_width - 1, curses.ACS_LRCORNER
        )

        header = "Aegis Authenticator"
        stdscr.addstr(
            start_row + 1,
            start_col + (box_width - len(header)) // 2,
            header,
            BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_BOLD,
        )

        vault_label = f"Vault: {vault_name}"
        stdscr.addstr(start_row + 3, start_col + 2, vault_label, NORMAL_TEXT_COLOR)

        prompt = "Enter vault password: "
        stdscr.addstr(start_row + 4, start_col + 2, prompt, NORMAL_TEXT_COLOR)

        pwd_display = "*" * len(pwd_input)
        stdscr.addstr(
            start_row + 4, start_col + 2 + len(prompt), pwd_display, HIGHLIGHT_COLOR
        )

        stdscr.refresh()

        ch = stdscr.getch()

        if ch in [10, 13]:
            password = "".join(pwd_input)
            try:
                entries = cli_backend.get_entries(vault_path, password)
                break
            except cli_backend.CLIError as e:
                stdscr.addstr(
                    start_row + 6, start_col + 2, f"Error: {e}", RED_TEXT_COLOR
                )
                stdscr.refresh()
                curses.napms(1500)
                pwd_input = []
        elif ch in [8, 127, curses.KEY_BACKSPACE]:
            if pwd_input:
                pwd_input.pop()
        elif 32 <= ch <= 126:
            pwd_input.append(chr(ch))
        elif ch == 27:
            import time

            current_time = time.time()
            if current_time - last_esc_time < 0.5:
                return
            last_esc_time = current_time
            try:
                stdscr.addstr(
                    start_row + 6,
                    start_col + 2,
                    "Press ESC again to quit",
                    NORMAL_TEXT_COLOR,
                )
                stdscr.refresh()
                curses.napms(800)
            except:
                pass
            continue

    config["last_opened_vault"] = vault_path
    config["last_vault_dir"] = os.path.dirname(vault_path)
    save_config(config)

    stdscr.nodelay(True)
    while True:
        ch = stdscr.getch()
        if ch == curses.ERR:
            break
    stdscr.nodelay(False)
    stdscr.clear()
    stdscr.refresh()

    if args.uuid:
        try:
            entry = cli_backend.get_entry(args.uuid, vault_path, password)
            display_list = [
                {
                    "index": 0,
                    "name": entry["name"],
                    "issuer": entry.get("issuer", ""),
                    "groups": ", ".join(entry.get("groups", [])),
                    "note": entry.get("note", ""),
                    "uuid": entry["uuid"],
                }
            ]
            run_reveal_mode(
                stdscr,
                display_list[0],
                None,
                set(),
                lambda: 30000,
                config,
                max_rows,
                max_cols,
                curses_colors_enabled,
                display_list,
                vault_path,
                password,
                colors,
                PYPERCLIP_AVAILABLE,
            )
            if not args.group:
                return
        except cli_backend.CLIError as e:
            stdscr.addstr(0, 0, f"Error: {e}", RED_TEXT_COLOR)
            stdscr.refresh()
            curses.napms(2000)
            return

    while True:
        selected_otp_uuid = run_search_mode(
            stdscr,
            entries,
            args,
            colors,
            curses_colors_enabled,
            vault_path,
            password,
            PYPERCLIP_AVAILABLE,
        )

        if selected_otp_uuid:
            try:
                entry = cli_backend.get_entry(selected_otp_uuid, vault_path, password)
                display_list = [
                    {
                        "index": 0,
                        "name": entry["name"],
                        "issuer": entry.get("issuer", ""),
                        "groups": ", ".join(entry.get("groups", [])),
                        "note": entry.get("note", ""),
                        "uuid": entry["uuid"],
                    }
                ]
                run_reveal_mode(
                    stdscr,
                    display_list[0],
                    None,
                    set(),
                    lambda: 30000,
                    config,
                    max_rows,
                    max_cols,
                    curses_colors_enabled,
                    display_list,
                    vault_path,
                    password,
                    colors,
                    PYPERCLIP_AVAILABLE,
                )
            except cli_backend.CLIError as e:
                stdscr.addstr(max_rows - 1, 0, f"Error: {e}", RED_TEXT_COLOR)
                stdscr.refresh()
                curses.napms(2000)
        else:
            break


def main():
    parser = argparse.ArgumentParser(
        description="Aegis Authenticator TUI.", prog="aegis-tui"
    )
    parser.add_argument(
        "vault_path", nargs="?", help="Path to the Aegis vault file.", default=None
    )
    parser.add_argument(
        "-d", "--vault-dir", help="Directory to search for vault files.", default="."
    )
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument(
        "-g", "--group", help="Filter OTP entries by a specific group name."
    )
    parser.add_argument("-p", "--password", help="Vault password.")
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output."
    )

    args = parser.parse_args()

    password = args.password
    if not password:
        password = os.getenv("AEGIS_CLI_PASSWORD")

    curses.wrapper(cli_main, args, password)


if __name__ == "__main__":
    main()
