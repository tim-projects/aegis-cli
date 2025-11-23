# Current Task: Implement "Search as you type" for OTP entries

## Objective
Rework the interactive OTP selection in `aegis-cli.py` to use a "search as you type" filtering mechanism, revealing codes only when a single match is found.

## Plan
1.  **Refactor the interactive OTP display loop in `aegis-cli.py` to incorporate `readchar` for "search as you type", dynamic filtering, and conditional OTP revelation.**
    *   **Status:** COMPLETED. The `aegis-cli.py` file has been updated with the `readchar`-based search and filter logic, including conditional OTP revelation. Indentation errors were corrected, debug prints removed, `os.system('clear')` was re-enabled, and the countdown loop was reactivated with all `print` statements now having `flush=True`.
2.  **Refine input prompts for search and selection.**
    *   **Status:** COMPLETED. The prompt `Search (Ctrl+C to exit): {search_term}` is implemented.
3.  **Implement error handling for no matches, backspace, etc.**
    *   **Status:** COMPLETED. Backspace, Ctrl+C, and EOFError are handled.
4.  **Add/Update Unit Tests for new filtering and display logic.**
    *   **Status:** COMPLETED.
    *   **Findings & Mitigations:**
        *   **Issue:** `ModuleNotFoundError: No module named 'readchar'` in tests.
            *   **Mitigation:** User installed `python-readchar`.
        *   **Issue:** `AttributeError` for various patched functions (e.g., `aegis_cli.read_and_decrypt_vault_file`, `aegis_cli.get_otps`, `aegis_cli.os.system`, `aegis_cli.readchar.readkey`, `aegis_cli.load_config`, `aegis_cli.save_config`).
            *   **Mitigation:** Corrected patching targets to point to the correct modules (`aegis_core`, `os`, `readchar`, `getpass`, `builtins`) or used `patch.object` for functions within the dynamically loaded `aegis_cli` module (`load_config`, `save_config`).
        *   **Issue:** `TypeError: Protocols cannot be instantiated` when creating `OTP` objects in tests.
            *   **Mitigation:** Replaced direct `OTP` instantiation with `MagicMock(spec=aegis_core.OTP, ...)`. Added `import aegis_core` to the top of the test file.
        *   **Issue:** `ImportError: cannot import name 'main' from 'aegis_cli'` and `AttributeError: module 'aegis_cli' has no attribute 'main'`.
            *   **Mitigation:** Implemented `importlib.util` to correctly load `aegis-cli.py` as a module for testing.
        *   **Issue:** `IndentationError` in test methods.
            *   **Mitigation:** Corrected indentation of `aegis_cli.main()` calls within `try` blocks.
        *   **Issue:** `AttributeError: <module 'aegis_cli' ...> does not have the attribute 'find_vault_path'`.
            *   **Mitigation:** Removed `@patch` decorator for `find_vault_path` from all test cases.
        *   **Issue:** Tests failing with "An unexpected error occurred: [Errno 2] No such file or directory: '/mock/vault/path.json'". This indicates `read_and_decrypt_vault_file` is not being mocked correctly.
            *   **Mitigation:** All `@patch` decorators for `read_and_decrypt_vault_file` and `get_otps` now target `aegis_cli` instead of `aegis_core`. The `sys.argv` patching is correctly inside the `with patch` block for each test. Syntax errors in `with` statements have been corrected using a temporary script.
        *   **Issue:** Tests failing because OTP entry names/issuers are displayed as `MagicMock` objects, e.g., `<MagicMock name='Test OTP 1.name.ljust()' id='...'>`.
            *   **Mitigation:** The `mock_vault_data.db.entries` now use `MagicMock(spec=Entry)` and have their attributes (`name`, `issuer`, `groups`, `note`, `uuid`) explicitly set to string values.
        *   **Issue:** `test_search_as_you_type_no_match` is failing because the assertion for the search prompt does not match the actual output of `aegis-cli.py`.
            *   **Mitigation:** The assertion in `test_search_as_you_type_no_match` has been updated to match the new prompt string.
        *   **Issue:** `test_search_as_you_type_no_match` is failing because `os.system('clear')` was not effectively clearing the `StringIO` buffer in the test environment, causing old output to accumulate.
            *   **Mitigation:** Reverted `patch('os.system')` in all test methods to simply return `None`, allowing all output to accumulate in `mock_stdout`. The assertions were then refined to inspect only the relevant final segment of the accumulated output to determine the displayed state after filtering.
        *   **Issue:** `SyntaxError: unexpected character after line continuation character` at line 21, and similar issues throughout the `with` statements.
            *   **Finding:** This is caused by an extra space after the backslash in line continuation characters (e.g., `\ ` instead of `\`).
            *   **Mitigation:** Manually removing all instances of `\ ` (backslash-space) and replacing them with `\` (single backslash followed by a newline) in `tests/test_aegis_cli.py` via `read_file` and `write_file` operations.
        *   **Issue:** The 'search as you type' functionality is not working when running `aegis-cli.py` directly, even though unit tests are passing.
            *   **Mitigation:** Debug prints for `key` and `search_term` were added to the interactive loop of `aegis-cli.py`, and `os.system('clear')` and the countdown loop (including `time.sleep(1)`) were temporarily commented out to observe input capture and search term updates. **This issue was later identified as a `SyntaxError` due to an unescaped newline within an f-string at line 254. This has been corrected by explicitly escaping the newline with `\n`.**
        *   **Issue:** `ModuleNotFoundError: No module named 'aegis_core'` during test execution.
            *   **Mitigation:** The `PYTHONPATH` environment variable was set to include the current directory (`.`) when running `pytest`, allowing Python to locate the `aegis_core` module.

## New Requirements
1.  **Conditional Refresh Loop:** If the filtered list (`display_data`) has exactly one item, that OTP should be revealed, and the refresh loop (countdown) should begin. If the filtered list has more than one item, OTP codes should remain hidden, and the refresh loop should not run.
    *   **Status:** COMPLETED. The countdown loop now only executes if `len(display_data) == 1` and the corresponding OTP is in `revealed_otps`. The conditional revelation of OTPs based on `len(display_data)` and clearing of `revealed_otps` if `len(display_data) != 1` is also correctly implemented.
2.  **Reset Filter with Esc key:** Tapping the Esc key should clear the typing filter (`search_term = ""`) and also clear any currently `revealed_otps`.
    *   **Status:** COMPLETED (in tests). **Finding:** User reports this is *not working* in the live application.

## Next Steps
1.  **Diagnose and fix Esc and Backspace functionality in live application:** Investigate why `readchar.key.ESC` and `readchar.key.BACKSPACE` are not being recognized or handled correctly in the live terminal environment, despite passing tests.
2.  **Commit and push changes:** Perform `git add .`, `git commit`, and `git push` as requested by the user.