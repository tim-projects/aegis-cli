# aegis-cli

### Example Output

When run without a group filter, OTP codes are obscured by default:

```
--- All OTPs ---
#   Issuer             Name               Code    Group              Note
--- ---                ----               ----    -----              ----
1   Bank of America    MyBank             ******  Finance            Checking Account
2   Facebook           MySocial           ******  Social             Personal Profile
3   Google             MyEmail            ******  Personal           Primary Email
4   Steam              MyGaming           ******  Gaming             Steam Account

Time until next refresh: 25.0 seconds

Make a selection to reveal the OTP code (or press Ctrl+C to exit): 
```

After entering '1' to reveal the first OTP:

```
--- All OTPs ---
#   Issuer             Name               Code    Group              Note
--- ---                ----               ----    -----              ----
1   Bank of America    MyBank             123456  Finance            Checking Account
2   Facebook           MySocial           ******  Social             Personal Profile
3   Google             MyEmail            ******  Personal           Primary Email
4   Steam              MyGaming           ******  Gaming             Steam Account

Time until next refresh: 25.0 seconds

Make a selection to reveal the OTP code (or press Ctrl+C to exit): 
```

When filtering by a specific group (e.g., `aegis-cli /path/to/your/aegis-backup.json --group Finance`):

```
--- All OTPs ---
#   Issuer             Name               Code    Group              Note
--- ---                ----               ----    -----              ----
1   Bank of America    MyBank             ******  Finance            Checking Account

Time until next refresh: 25.0 seconds

Make a selection to reveal the OTP code (or press Ctrl+C to exit): 
```

A command-line interface (CLI) tool for viewing Aegis Authenticator Time-based One-Time Passwords (TOTP).

**Note:** This tool is primarily a viewer and does not support editing or creating new OTP codes.

## Features

*   Decrypts Aegis Authenticator vault files using a provided password.
*   Continuously displays OTP codes for all entries in a real-time refreshing table.
*   Automatically refreshes OTPs based on their configured periods, with a live countdown that updates in place.
*   Outputs OTPs in a clear, sorted table format (by Issuer), including Issuer, Name, Code, Group, and Note.
*   Interactive mode to reveal obscured OTP codes on demand.
*   Supports filtering OTP entries by group name.
*   Purely command-line based, with no graphical interface.

## Usage

### Installation (Arch Linux AUR)

To install `aegis-cli` on Arch Linux, you can use an AUR helper like `yay` or `paru`:

```bash
yay -S aegis-cli
# or
paru -S aegis-cli
```

Alternatively, you can build it manually:

```bash
git clone https://aur.archlinux.org/aegis-cli.git
cd aegis-cli
makepkg -si
```

### Running the CLI

Once installed, you can run `aegis-cli` from any terminal with the path to your Aegis vault `.json` file:

```bash
aegis-cli /path/to/your/aegis-backup.json
```

If no vault path is provided, `aegis-cli` will automatically search for the most recently modified `aegis-backup-*.json` file in the current directory, and then in `~/.config/aegis`.

If your vault requires a password, you will be prompted securely. For non-interactive use (e.g., in scripts), you can provide the password via the `AEGIS_CLI_PASSWORD` environment variable:

```bash
export AEGIS_CLI_PASSWORD="YourVaultPassword"
aegis-cli /path/to/your/aegis-backup.json
```

## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.

This project is a complete rewrite in Python, originally inspired by the `avdu` project (https://github.com/Sammy-T/avdu). It provides CLI functionality for displaying OTP codes from an encrypted Aegis vault.
