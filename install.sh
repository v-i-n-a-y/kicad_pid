#!/bin/sh
# Copyright 2026 Vinay Williams
#
# Installs the Rocketry P&ID symbol library into KiCad (macOS and Linux).
# Run it from a terminal, or double-click the .command copy on macOS.
# Arguments are passed on to install.py, for example --dry-run or --uninstall.

here=$(cd "$(dirname "$0")" && pwd)
script="$here/install.py"
[ -f "$script" ] || script="$here/scripts/install.py"

# A .command file is opened in a Terminal window that closes when the script ends
finish() {
    case "$0" in
    *.command)
        printf '\nPress Enter to close this window. '
        read -r _
        ;;
    esac
    exit "$1"
}

for python in python3 python; do
    # Skips the macOS stub that only offers to install the developer tools
    if "$python" -c 'import sys; sys.exit(sys.version_info < (3, 6))' >/dev/null 2>&1; then
        "$python" "$script" "$@"
        finish $?
    fi
done

echo "Rocketry P&ID KiCAD - Install"
echo
echo "Python 3 was not found, and the installer needs it."
echo "Either install Python 3 from https://www.python.org/downloads/ and run this again,"
echo "or skip Python: in KiCad open Plugin and Content Manager, choose"
echo "Install from File and pick the kicad_pid-*.zip file from the release page."
finish 1
