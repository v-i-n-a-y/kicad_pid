# Copyright 2026 Vinay Williams

import argparse
import datetime
import os
import re
import shutil
import sys

LIBRARY = "pid_kicad.kicad_sym"
DATA_NAME = "kicad_pid"
NICKNAME = "pid_kicad"
DESCRIPTION = "Rocketry P&ID symbols"
TABLE = "sym-lib-table"
FLATPAK = os.path.join(".var", "app", "org.kicad.KiCad")
VERSION_DIR = re.compile(r"^\d+(\.\d+)*$")
TABLE_VERSION = 7

HERE = os.path.dirname(os.path.abspath(__file__))


def system_name():
    """
    Name the operating system

    Returns

    system - str
        One of windows, macos or linux
    """

    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def data_dir(system, env, home):
    """
    Work out the per-user directory the library is copied to

    Arguments

    system - str
        windows, macos or linux
    env - dict
        Environment variables
    home - str
        The user's home directory

    Returns

    path - str
        The kicad_pid data directory
    """

    if system == "windows":
        base = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif system == "macos":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, DATA_NAME)


def config_roots(system, env, home):
    """
    List the directories that hold one folder per KiCad version

    Flatpak KiCad keeps its configuration, and a data directory the sandbox can
    always see, under ~/.var/app/org.kicad.KiCad, so its root is paired with
    that data directory.

    Arguments

    system - str
        windows, macos or linux
    env - dict
        Environment variables
    home - str
        The user's home directory

    Returns

    roots - list
        (config root, data directory) pairs
    """

    own = data_dir(system, env, home)
    if system == "windows":
        base = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return [(os.path.join(base, "kicad"), own)]
    if system == "macos":
        return [(os.path.join(home, "Library", "Preferences", "kicad"), own)]
    base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    flatpak = os.path.join(home, FLATPAK)
    return [
        (os.path.join(base, "kicad"), own),
        (
            os.path.join(flatpak, "config", "kicad"),
            os.path.join(flatpak, "data", DATA_NAME),
        ),
    ]


def find_targets(roots, version):
    """
    Find every KiCad configuration directory

    Arguments

    roots - list
        (config root, data directory) pairs
    version - str
        Only this KiCad version, or an empty string for every version

    Returns

    targets - list
        (version directory, data directory) pairs, in version order
    """

    found = []
    for root, data in roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if not VERSION_DIR.match(name) or not os.path.isdir(path):
                continue
            if version and name != version:
                continue
            key = tuple(int(part) for part in name.split("."))
            found.append((key, path, data))
    found.sort()
    return [(path, data) for _, path, data in found]


def library_source():
    """
    Locate the library to install

    Returns

    path - str
        The library next to this script (a release bundle) or one level up
        (a repository checkout), or an empty string if neither exists
    """

    for folder in (HERE, os.path.dirname(HERE)):
        path = os.path.join(folder, LIBRARY)
        if os.path.isfile(path):
            return path
    return ""


def lib_entry(nickname, uri):
    """
    Format a symbol library table entry

    Arguments

    nickname - str
        Library nickname
    uri - str
        Library location, written with forward slashes as KiCad does

    Returns

    entry - str
        The (lib ...) form
    """

    def quote(text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'

    return (
        f'(lib (name {quote(nickname)})(type "KiCad")(uri {quote(uri)})'
        f'(options "")(descr {quote(DESCRIPTION)}))'
    )


def lib_spans(text):
    """
    Find the (lib ...) forms of a library table

    Arguments

    text - str
        Content of a sym-lib-table

    Returns

    spans - list
        (start, end) offsets of each top-level (lib ...) form
    """

    spans = []
    depth = 0
    start = 0
    quoted = False
    escaped = False
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
            if depth == 2:
                start = index
        elif char == ")":
            if depth == 2 and text.startswith("(lib", start):
                spans.append((start, index + 1))
            depth -= 1
    return spans


def field(form, name):
    """
    Read one field of a (lib ...) form

    Arguments

    form - str
        The (lib ...) text
    name - str
        Field name, such as name or uri

    Returns

    value - str
        The field value, or an empty string if it is missing
    """

    match = re.search(rf'\({name}\s+(?:"((?:[^"\\]|\\.)*)"|([^\s()]+))', form)
    if not match:
        return ""
    value = match.group(1) if match.group(1) is not None else match.group(2)
    return re.sub(r"\\(.)", r"\1", value)


def ours(form, nickname):
    """
    Decide whether a table entry is this library

    An entry counts as ours if it has the nickname, or if it points at the
    kicad_pid data directory under another nickname.

    Arguments

    form - str
        The (lib ...) text
    nickname - str
        Library nickname

    Returns

    match - bool
        True if the entry is ours
    """

    if field(form, "name") == nickname:
        return True
    uri = field(form, "uri").replace("\\", "/").lower()
    return uri.endswith(f"/{DATA_NAME}/{LIBRARY}".lower())


def edit_table(text, nickname, uri):
    """
    Add or update the library entry in a table's text

    Arguments

    text - str
        Content of a sym-lib-table, or an empty string for a new one
    nickname - str
        Library nickname
    uri - str
        Library location

    Returns

    result - tuple
        (new text, action) where action is added, updated or unchanged
    """

    newline = "\r\n" if "\r\n" in text else "\n"
    entry = lib_entry(nickname, uri)
    if not text.strip():
        body = f"(sym_lib_table{newline}  (version {TABLE_VERSION}){newline}"
        return f"{body}  {entry}{newline}){newline}", "added"
    spans = lib_spans(text)
    matches = [span for span in spans if ours(text[span[0] : span[1]], nickname)]
    if matches:
        first = matches[0]
        if len(matches) == 1 and text[first[0] : first[1]] == entry:
            return text, "unchanged"
        # Remove the duplicates from the end, then rewrite the first in place
        for start, end in reversed(matches[1:]):
            text = remove_span(text, start, end)
        return text[: first[0]] + entry + text[first[1] :], "updated"
    close = text.rstrip().rfind(")")
    if close < 0:
        raise ValueError("not a library table (no closing parenthesis)")
    head = text[:close].rstrip()
    return f"{head}{newline}  {entry}{newline}{text[close:]}", "added"


def remove_span(text, start, end):
    """
    Delete a form and the whole line it occupies

    Arguments

    text - str
        Table text
    start - int
        Offset of the form's first character
    end - int
        Offset just past the form's last character

    Returns

    text - str
        The text without the form
    """

    line = text.rfind("\n", 0, start) + 1
    if text[line:start].strip() == "":
        start = line
        stop = text.find("\n", end)
        if text[end : stop if stop >= 0 else len(text)].strip() == "":
            end = len(text) if stop < 0 else stop + 1
    return text[:start] + text[end:]


def drop_entries(text, nickname):
    """
    Remove every entry of this library from a table's text

    Arguments

    text - str
        Content of a sym-lib-table
    nickname - str
        Library nickname

    Returns

    result - tuple
        (new text, count removed)
    """

    matches = [s for s in lib_spans(text) if ours(text[s[0] : s[1]], nickname)]
    for start, end in reversed(matches):
        text = remove_span(text, start, end)
    return text, len(matches)


def template_table(system, env):
    """
    Find KiCad's default symbol library table

    A KiCad that has never written a table seeds it from this template, so a
    new table made here starts from it rather than hiding the standard
    libraries.

    Arguments

    system - str
        windows, macos or linux
    env - dict
        Environment variables

    Returns

    path - str
        The template sym-lib-table, or an empty string if none is found
    """

    folders = []
    if env.get("KICAD_TEMPLATE_DIR"):
        folders.append(env["KICAD_TEMPLATE_DIR"])
    if system == "windows":
        for key in ("ProgramFiles", "ProgramW6432"):
            root = os.path.join(env.get(key, ""), "KiCad")
            if env.get(key) and os.path.isdir(root):
                for name in sorted(os.listdir(root), reverse=True):
                    folders.append(
                        os.path.join(root, name, "share", "kicad", "template")
                    )
    elif system == "macos":
        folders.append("/Applications/KiCad/KiCad.app/Contents/SharedSupport/template")
    else:
        folders += [
            "/usr/share/kicad/template",
            "/usr/local/share/kicad/template",
            "/app/share/kicad/template",
        ]
    for folder in folders:
        path = os.path.join(folder, TABLE)
        if os.path.isfile(path):
            return path
    return ""


def same_major(text, version):
    """
    Check a template belongs to the same KiCad major version

    The template names the standard libraries through a KICADn_SYMBOL_DIR
    variable, which only resolves in KiCad n.

    Arguments

    text - str
        Content of the template table
    version - str
        KiCad version of the configuration directory, such as 9.0

    Returns

    match - bool
        True if every variable in the template is the one for this version
    """

    majors = set(re.findall(r"KICAD(\d+)_SYMBOL_DIR", text))
    return majors == {version.split(".")[0]}


def read_text(path):
    """
    Read a file without translating its line endings

    Arguments

    path - str
        File to read

    Returns

    text - str
        The content
    """

    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path, text):
    """
    Write a file through a temporary file, without translating line endings

    Arguments

    path - str
        File to write
    text - str
        Content to write
    """

    temp = f"{path}.part"
    with open(temp, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    os.replace(temp, path)


def backup(path):
    """
    Copy a table aside before it is changed

    Arguments

    path - str
        File to back up

    Returns

    name - str
        Path of the backup
    """

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{path}.bak-{stamp}"
    count = 1
    while os.path.exists(name):
        count += 1
        name = f"{path}.bak-{stamp}-{count}"
    shutil.copy2(path, name)
    return name


def install_library(source, folder, dry):
    """
    Copy the library into a data directory

    Arguments

    source - str
        Library to copy
    folder - str
        Data directory
    dry - bool
        Report what would happen without doing it

    Returns

    target - str
        Path of the installed library
    """

    target = os.path.join(folder, LIBRARY)
    verb = "Would copy" if dry else "Copied"
    if not dry:
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"{verb} library to {target}")
    return target


def install_entry(vdir, target, nickname, dry, system, env):
    """
    Add or update the library entry in one KiCad version's table

    Arguments

    vdir - str
        KiCad configuration directory for one version
    target - str
        Installed library path
    nickname - str
        Library nickname
    dry - bool
        Report what would happen without doing it
    system - str
        windows, macos or linux
    env - dict
        Environment variables
    """

    table = os.path.join(vdir, TABLE)
    uri = target.replace("\\", "/")
    seeded = ""
    existed = os.path.isfile(table)
    if existed:
        text = read_text(table)
    else:
        seeded = template_table(system, env)
        text = read_text(seeded) if seeded else ""
        if seeded and not same_major(text, os.path.basename(vdir)):
            seeded, text = "", ""
    new, action = edit_table(text, nickname, uri)
    label = os.path.basename(vdir)
    if action == "unchanged":
        print(f"KiCad {label}: already up to date ({table})")
        return
    verb = {"added": "add", "updated": "update"}[action]
    if dry:
        print(f"KiCad {label}: would {verb} entry '{nickname}' in {table}")
        return
    if existed:
        print(f"KiCad {label}: backed up table to {backup(table)}")
    write_text(table, new)
    print(f"KiCad {label}: {action} entry '{nickname}' in {table}")
    if seeded:
        print(f"KiCad {label}: new table started from {seeded}")
    elif not text.strip():
        print(
            f"KiCad {label}: warning, KiCad had no table and no matching default template "
            "was found, so only this library is listed. Add the standard "
            "libraries again in Preferences > Manage Symbol Libraries."
        )


def uninstall_entry(vdir, nickname, dry):
    """
    Remove the library entry from one KiCad version's table

    A table left with no libraries is deleted (after a backup), so KiCad
    rebuilds the default one at its next start.

    Arguments

    vdir - str
        KiCad configuration directory for one version
    nickname - str
        Library nickname
    dry - bool
        Report what would happen without doing it
    """

    table = os.path.join(vdir, TABLE)
    label = os.path.basename(vdir)
    if not os.path.isfile(table):
        print(f"KiCad {label}: no {TABLE}, nothing to remove")
        return
    new, count = drop_entries(read_text(table), nickname)
    if not count:
        print(f"KiCad {label}: no '{nickname}' entry in {table}")
        return
    empty = not lib_spans(new)
    if dry:
        what = (
            "remove the entry and delete the then empty table"
            if empty
            else "remove the entry"
        )
        print(f"KiCad {label}: would {what} '{nickname}' in {table}")
        return
    print(f"KiCad {label}: backed up table to {backup(table)}")
    if empty:
        os.remove(table)
        print(f"KiCad {label}: removed '{nickname}' and deleted the empty {table}")
    else:
        write_text(table, new)
        print(f"KiCad {label}: removed '{nickname}' from {table}")


def uninstall_library(folder, dry):
    """
    Delete the installed library and its directory if that leaves it empty

    Arguments

    folder - str
        Data directory
    dry - bool
        Report what would happen without doing it
    """

    target = os.path.join(folder, LIBRARY)
    if not os.path.isfile(target):
        return
    if dry:
        print(f"Would delete {target}")
        return
    os.remove(target)
    print(f"Deleted {target}")
    if not os.listdir(folder):
        os.rmdir(folder)
        print(f"Deleted {folder}")


def run(args, system, env, home):
    """
    Install or uninstall the library

    Arguments

    args - Namespace
        Parsed command line
    system - str
        windows, macos or linux
    env - dict
        Environment variables
    home - str
        The user's home directory

    Returns

    status - int
        Process exit status
    """

    dry = args.dry_run
    if dry:
        print("Dry run: nothing will be changed\n")
    roots = config_roots(system, env, home)
    targets = find_targets(roots, args.kicad_version)
    folders = []
    for _, folder in targets or [("", roots[0][1])]:
        if folder not in folders:
            folders.append(folder)

    if args.uninstall:
        for vdir, _ in targets:
            uninstall_entry(vdir, args.nickname, dry)
        for folder in [data for _, data in roots]:
            uninstall_library(folder, dry)
        if not targets:
            print("No KiCad configuration found, so no tables were changed")
        print("\nRestart KiCad for the change to take effect")
        return 0

    source = library_source()
    if not source:
        print(f"Error: cannot find {LIBRARY} next to this script", file=sys.stderr)
        return 1
    installed = {}
    for folder in folders:
        installed[folder] = install_library(source, folder, dry)
    if not targets:
        where = args.kicad_version or "any version"
        print(
            f"\nNo KiCad configuration found for {where}. Run KiCad once, then "
            "run this installer again, or add the library by hand in "
            "Preferences > Manage Symbol Libraries."
        )
        return 1
    for vdir, folder in targets:
        install_entry(vdir, installed[folder], args.nickname, dry, system, env)
    print("\nClose and restart KiCad for the library to appear")
    return 0


def usage():
    """
    Usage

    Prints the script's usage
    """

    print(
        f"Usage: {sys.argv[0]} [--uninstall] [--dry-run] "
        "[--kicad-version VERSION] [--nickname NAME]"
    )
    sys.exit(2)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Install\n")

    parser = argparse.ArgumentParser(
        description="Install the P&ID symbol library into KiCad",
        add_help=False,
    )
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--kicad-version", default="")
    parser.add_argument("--nickname", default=NICKNAME)
    parser.add_argument("-h", "--help", action="store_true")
    options, extra = parser.parse_known_args()
    if options.help or extra:
        usage()
    if options.kicad_version and not VERSION_DIR.match(options.kicad_version):
        print(
            f"Error: '{options.kicad_version}' is not a version such as 8.0",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        status = run(
            options,
            system_name(),
            os.environ,
            os.path.expanduser("~"),
        )
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(status)
