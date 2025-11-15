# aegis-cli

A command-line interface (CLI) tool for viewing Aegis Authenticator Time-based One-Time Passwords (TOTP).

This project is a fork of the original `avdu` project (https://github.com/Sammy-T/avdu), stripped down to provide only CLI functionality for displaying TOTP codes from an encrypted Aegis vault.

**Note:** There are currently no plans for this tool to support editing or creating new TOTP codes; its sole purpose is to be a viewer.

## Features

*   Decrypts Aegis Authenticator vault files.
*   Continuously displays TOTP codes for all entries.
*   Automatically refreshes OTPs based on their configured periods.
*   Outputs OTPs in a neat, sorted table format (by Issuer).
*   Purely command-line based, no graphical interface.

## Usage

To run the `aegis-cli` tool, navigate to the `cmd/aegis-cli` directory and execute it with the path to your Aegis vault `.json` file as an argument.

```bash
./cmd/aegis-cli/aegis-cli /path/to/your/aegis-backup.json
```

## Building from Source (for AUR)

To build the `aegis-cli` tool from source, ensure you have Go installed (version 1.16 or higher is recommended).

For AUR packages, the build process is typically handled by `makepkg`. You would usually place the source in a `PKGBUILD` file that includes a `build()` function similar to this:

```bash
build() {
  cd "${srcdir}"
  go build -o "${pkgdir}/usr/bin/aegis-cli" ./cmd/aegis-cli/main.go
}
```

## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.
