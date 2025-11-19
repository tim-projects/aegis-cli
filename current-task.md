# Current Task: Implement "Search as you type" for OTP entries

## Objective
Rework the interactive OTP selection in `aegis-cli.py` to use a "search as you type" filtering mechanism, revealing codes only when a single match is found.

## Plan
1.  **Refactor the interactive OTP display loop in `aegis-cli.py` to incorporate `readchar` for "search as you type", dynamic filtering, and conditional OTP revelation.**
    *   **Status:** COMPLETED. The `aegis-cli.py` file has been updated with the `readchar`-based search and filter logic, including conditional OTP revelation.
2.  **Refine input prompts for search and selection.**
    *   **Status:** COMPLETED. The prompt `Search (Ctrl+C to exit): {search_term}` is implemented.
3.  **Implement error handling for no matches, backspace, etc.**
    *   **Status:** COMPLETED. Backspace, Ctrl+C, and EOFError are handled.
4.  **Add/Update Unit Tests for new filtering and display logic.**
    *   **Status:** PENDING. This is the next step.
