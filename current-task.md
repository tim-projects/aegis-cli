# Current Task: Implement Arrow Key Navigation for OTP entries and Refactor Search Mode

- IMPORTANT: can you break up the aegis-tui.py file into seperate files because I am repeatedely getting indent errors when using an agent to edit the file.


## Objective
Enhance the interactive OTP selection in `aegis-tui.py` by implementing a Text User Interface (TUI) with arrow key navigation for selecting entries. The user will be able to move a cursor up and down the full list, type characters to move the cursor to the first matching item, and press Enter to reveal the OTP for the selected entry. Search functionality should be encapsulated in its own function that returns the selected OTP's UUID.

## Status
We are now implementing a `ncurses`-based TUI to provide a more intuitive selection mechanism. Vault generation and decryption are successful, and the `aegis-tui.py` application runs without runtime errors (aside from the expected `termios.error` in this environment).

## Findings & Mitigations
*   **`_curses.error: cbreak() returned ERR` and `_curses.error: nocbreak() returned ERR`:**
    *   **Finding:** These errors occurred during automated execution of `aegis-tui.py`, indicating issues with `cbreak` mode setup and teardown within `curses.wrapper`.
    *   **Mitigation:** This is an environmental limitation of the non-interactive shell used for automated execution, as `curses` applications require a fully interactive terminal. This issue cannot be resolved by code changes within the application or tests.
*   **`termios.error: (25, 'Inappropriate ioctl for device')`:**
    *   **Finding:** Occurred in non-interactive environments when `aegis-tui.py` attempted interactive terminal operations.
    *   **Mitigation:** Acknowledged as an expected environmental limitation; no code changes were made.
*   **`Killed` error during `pytest` execution:**
    *   **Finding:** Tests were crashing due to excessive memory usage with `MagicMock(spec=...)`.
    *   **Mitigation:** Removed `spec=Entry` and `spec=OTP` from `MagicMock` instances in unit tests.
*   **`io.UnsupportedOperation: redirected stdin is pseudofile, has no fileno()` in unit tests:**
    *   **Finding:** `select.select` calls failed when `sys.stdin` was mocked as `StringIO`.
    *   **Mitigation:** Patched `select.select` in unit tests to simulate input availability.
*   **OTP entry list overlapping top border in search mode:**
    *   **Finding:** The list of TOTP entries in search mode was not correctly positioned within the display box and overlapped the top border.
    *   **Mitigation:** Adjusted the starting `row` for content display within the main box to `header_row_offset + 1`, ensuring the content starts one row below the top border of the box. **(Resolved)**
*   **Excessive screen redraws:**
    *   **Finding:** The entire screen was being redrawn continuously in both search and reveal modes, leading to potential performance issues or visual artifacts.
    *   **Mitigation:**
        *   **Search Mode (`cli_main`):** Implemented a `needs_redraw` boolean flag. This flag is set to `True` initially and whenever an input event (key press, search term change, selection change, group mode toggle) occurs or a terminal resize is detected (`curses.KEY_RESIZE`). The entire display logic (from `stdscr.clear()` to `stdscr.refresh()`) is now wrapped in an `if needs_redraw:` block, ensuring redrawing only happens when necessary. After `stdscr.refresh()`, `needs_redraw` is reset to `False`.
        *   **Reveal Mode (`_run_reveal_mode`):** Optimized redraws to only update the "Time to Next" countdown. Instead of `stdscr.clear()` in every loop iteration, the function now performs an initial full redraw of the reveal box and static content. Subsequent iterations only clear and redraw the specific line where the countdown timer is displayed. A full redraw of the reveal mode is triggered only on `curses.KEY_RESIZE`. **(Resolved)**
*   **Unexpected Reveal Mode Entry After Password (Initial Attempt to fix):**
    *   **Finding:** The application sometimes enters reveal mode immediately after the password is entered, instead of displaying the search interface. This indicates an unintended "Enter" key event being registered by `curses.getch()` at the start of the main loop, despite attempts to flush the input buffer.
    *   **Mitigation:**
        1.  Ensure `char` variable is explicitly reset to `curses.ERR` before the main loop.
        2.  Modify the `--uuid` CLI argument handling to directly call `run_reveal_mode` for the specified OTP, then exit the application upon its completion, preventing it from falling into the main interactive loop unintentionally.
*   **Blank Screen and Unintended Reveal After Password Entry (Current Issue):**
    *   **Finding:** After successfully entering the password, the screen remains blank. Pressing `Enter` then incorrectly shows the reveal mode for a random OTP, rather than the expected search interface. This indicates: 
        1.  The initial rendering of the search UI is not occurring or is being immediately cleared.
        2.  A spurious `Enter` key event is still being processed at the beginning of the main loop, leading to an unintended and uncommanded entry into reveal mode.
        3.  The `run_reveal_mode` function is being invoked without a valid, user-selected `entry_to_reveal` from the search list, contradicting the design intent that `run_reveal_mode` should only run when an ID is explicitly supplied (either via CLI or user selection).
    *   **Mitigation:**
        1.  **Guaranteed Initial Redraw:** Explicitly ensure `needs_redraw = True` at the start of the main `while True` loop and confirm that `draw_main_screen` is called within the `if needs_redraw:` block *before* any input processing in each iteration.
        2.  **Enhanced Input Flushing:** Implement a more robust mechanism to clear the input buffer immediately after `getpass` returns, preventing any residual `Enter` key events from affecting the `curses` loop.
        3.  **Strict Reveal Mode Invocation:** Modify the `curses.KEY_ENTER` handling to only trigger `run_reveal_mode` if a valid `selected_row` exists in the `display_list`. If `selected_row` is `-1` or `display_list` is empty, an `Enter` press should do nothing or provide a hint, not trigger a reveal.
*   **Refactoring Search Mode into a Separate Function:**
    *   **Finding:** The main loop in `cli_main` was becoming too large and complex, mixing input handling, display logic, and state management. This made it harder to debug and maintain.
    *   **Mitigation:** Extracted the core search and selection logic into a new function, `run_search_mode`, in `search_mode.py`. This function will now handle the TUI display, user input for navigation and searching, and return the UUID of the selected OTP. This function will be called from `cli_main`, and its return value will be used to decide whether to enter reveal mode.