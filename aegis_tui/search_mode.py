import curses

try:
    import pyperclip
except ImportError:
    pass

from . import cli_backend
from .tui_display import draw_main_screen
from .help_mode import run_help_mode


def run_search_mode(
    stdscr,
    entries,
    args,
    colors,
    curses_colors_enabled,
    vault_path,
    password,
    pyperclip_available,
):
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    search_term = ""
    current_mode = "search"
    in_search_mode = False
    status_message = ""

    selected_row = -1
    char = curses.ERR
    previous_search_term = ""
    current_group_filter = args.group
    group_selection_mode = False
    entry_to_reveal_uuid = None
    needs_redraw = True

    last_esc_time = 0

    all_groups = []
    group_name_map = {}
    for entry in entries:
        for g in entry.get("groups", []):
            if g not in group_name_map:
                group_name_map[g] = g

    all_entries = []
    for i, entry in enumerate(entries):
        all_entries.append(
            {
                "index": i,
                "name": entry.get("name", ""),
                "issuer": entry.get("issuer", ""),
                "groups": ", ".join(entry.get("groups", [])),
                "note": entry.get("note", ""),
                "uuid": entry.get("uuid", ""),
            }
        )
    all_entries.sort(key=lambda x: x["name"].lower())

    if current_group_filter:
        display_list_for_selection = [
            entry for entry in all_entries if current_group_filter in entry["groups"]
        ]
    else:
        display_list_for_selection = all_entries

    if len(display_list_for_selection) > 0:
        selected_row = 0
    else:
        selected_row = -1

    scroll_offset = 0
    items_per_page = 10

    while True:
        if current_mode == "search" and not group_selection_mode:
            term = search_term.lower()
            if current_group_filter:
                display_list = [
                    entry
                    for entry in all_entries
                    if current_group_filter in entry["groups"]
                    and (
                        term in entry["name"].lower() or term in entry["issuer"].lower()
                    )
                ]
            else:
                display_list = [
                    entry
                    for entry in all_entries
                    if term in entry["name"].lower() or term in entry["issuer"].lower()
                ]
        elif group_selection_mode:
            groups_list = [
                {"name": g, "uuid": g} for g in sorted(group_name_map.keys())
            ]
            if search_term:
                display_list = [
                    group
                    for group in groups_list
                    if search_term.lower() in group["name"].lower()
                ]
            else:
                display_list = groups_list
        else:
            display_list = all_entries

        if len(display_list) == 0:
            if not group_selection_mode:
                selected_row = -1
            else:
                if selected_row != -1:
                    selected_row = -1
        else:
            selected_row = max(
                -1 if group_selection_mode else 0,
                min(selected_row, len(display_list) - 1),
            )

        if needs_redraw:
            max_rows, max_cols = stdscr.getmaxyx()
            items_per_page = draw_main_screen(
                stdscr,
                max_rows,
                max_cols,
                display_list,
                selected_row,
                search_term,
                current_mode,
                group_selection_mode,
                current_group_filter,
                args.group,
                colors,
                curses_colors_enabled,
                scroll_offset,
                in_search_mode,
                status_message,
            )
            needs_redraw = False
            status_message = ""

        char = stdscr.getch()

        if char != curses.ERR:
            needs_redraw = True
            status_message = ""

            if char == curses.KEY_RESIZE:
                max_rows, max_cols = stdscr.getmaxyx()
                continue

            if char == 27:
                import time

                current_time = time.time()
                if current_time - last_esc_time < 0.5:
                    return None
                last_esc_time = current_time
                status_message = "Press ESC again to quit"
                needs_redraw = True
                continue

            if char == ord("?"):
                run_help_mode(stdscr, colors)
                needs_redraw = True
                continue

            move_down = False
            move_up = False

            if char == curses.KEY_DOWN:
                move_down = True
            elif char == curses.KEY_UP:
                move_up = True
            elif not in_search_mode:
                if char == ord("j"):
                    move_down = True
                elif char == ord("k"):
                    move_up = True

            if move_down:
                if group_selection_mode:
                    current_v_idx = selected_row + 1
                    total_virtual_items = len(display_list) + 1
                    if current_v_idx < total_virtual_items - 1:
                        selected_row = current_v_idx
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
                        selected_row = current_v_idx - 2
                        if selected_row + 1 < scroll_offset:
                            scroll_offset = selected_row + 1
                else:
                    if len(display_list) > 0:
                        selected_row = max(0, selected_row - 1)
                        if selected_row < scroll_offset:
                            scroll_offset = selected_row
                continue

            if group_selection_mode:
                if char == 27 or char == 7 or (not in_search_mode and char == ord("h")):
                    group_selection_mode = False
                    current_group_filter = None
                    search_term = ""
                    selected_row = 0 if len(all_entries) > 0 else -1
                    scroll_offset = 0
                    in_search_mode = False
                elif char == ord("/") and not in_search_mode:
                    in_search_mode = True
                elif (
                    char == curses.KEY_ENTER
                    or char in [10, 13]
                    or (not in_search_mode and char == ord("l"))
                ):
                    if selected_row == -1:
                        current_group_filter = None
                    elif selected_row != -1 and len(display_list) > 0:
                        selected_group = display_list[selected_row]
                        current_group_filter = selected_group["name"]
                    group_selection_mode = False
                    current_mode = "search"
                    initial_filtered_entries = (
                        [
                            entry
                            for entry in all_entries
                            if current_group_filter in entry["groups"]
                        ]
                        if current_group_filter
                        else all_entries
                    )
                    selected_row = 0 if len(initial_filtered_entries) > 0 else -1
                    scroll_offset = 0
                    search_term = ""
                    in_search_mode = False
                elif in_search_mode:
                    if char in [curses.KEY_BACKSPACE, 127, 8]:
                        if search_term:
                            search_term = search_term[:-1]
                            scroll_offset = 0
                    elif 32 <= char < 127:
                        search_term += chr(char)
                        scroll_offset = 0
                    elif char == 27:
                        in_search_mode = False

            else:
                if char == ord("/") and not in_search_mode:
                    in_search_mode = True
                elif char == 27:
                    if in_search_mode:
                        in_search_mode = False
                    else:
                        search_term = ""
                        current_group_filter = None
                        selected_row = 0 if len(all_entries) > 0 else -1
                        scroll_offset = 0
                elif not in_search_mode and char == ord("h"):
                    if search_term:
                        search_term = ""
                        scroll_offset = 0
                elif char == 7:
                    group_selection_mode = not group_selection_mode
                    if group_selection_mode:
                        selected_row = -1
                        search_term = ""
                        scroll_offset = 0
                        in_search_mode = False
                elif (
                    char == curses.KEY_ENTER
                    or char in [10, 13]
                    or (not in_search_mode and char == ord("l"))
                ):
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

            time.sleep(0.01)

    return entry_to_reveal_uuid
