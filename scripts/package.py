# Copyright 2026 Vinay Williams

import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LIBRARY = "pid_kicad.kicad_sym"
REGISTRY = "pid_registry.pdf"
ICON = os.path.join("pcm", "icon.png")
PREFIX = "kicad_pid"
SCHEMA = "https://go.kicad.org/pcm/schemas/v1"
IDENTIFIER = "com.github.v-i-n-a-y.kicad-pid"
HOMEPAGE = "https://github.com/v-i-n-a-y/kicad_pid"
RELEASES = HOMEPAGE + "/releases/latest"

# Fixed, so building twice gives byte-identical archives
STAMP = (2026, 1, 1, 0, 0, 0)

PLAIN = 0o644
EXECUTABLE = 0o755

DESCRIPTION = (
    "{count} P&ID symbols for rocketry: valves, instruments, tanks, bottles, "
    "engines and fittings, on a 1 mm connection grid"
)
DESCRIPTION_FULL = (
    "A library of P&ID symbols for rocketry, created for UK university "
    "rocketry teams. It covers valves, regulators, relief devices, "
    "instruments, tanks, gas bottles, engines and fittings. Every symbol has "
    "numbered pins, an ISA style reference prefix, a description and search "
    "keywords, and every pin sits on a whole millimetre so wires always land "
    "on it. The package installs one symbol library, pid_kicad."
)

LAUNCHERS = {
    "windows": ("install.bat", "install.bat"),
    "macos": ("install.sh", "install.command"),
    "linux": ("install.sh", "install.sh"),
}

RUN_STEPS = {
    "windows": (
        "1. Unzip this folder anywhere.\n"
        "2. Close KiCad.\n"
        "3. Double-click install.bat. If Windows warns that it is from an\n"
        "   unknown publisher, choose More info, then Run anyway.\n"
        "4. Start KiCad. The library is called pid_kicad."
    ),
    "macos": (
        "1. Unzip this folder anywhere.\n"
        "2. Close KiCad.\n"
        "3. Double-click install.command. If macOS refuses to open it, open\n"
        "   Terminal, type sh followed by a space, drag install.command into\n"
        "   the window and press Enter.\n"
        "4. Start KiCad. The library is called pid_kicad."
    ),
    "linux": (
        "1. Unpack the archive with tar xzf kicad_pid-*-linux.tar.gz\n"
        "2. Close KiCad.\n"
        "3. Run ./install.sh from the unpacked folder.\n"
        "4. Start KiCad. The library is called pid_kicad."
    ),
}

NEEDS = {
    "windows": "Python 3 from https://www.python.org/downloads/ (tick Add python.exe to PATH)",
    "macos": "Python 3, which comes with the Xcode command line tools (xcode-select --install)",
    "linux": "Python 3, which most distributions include",
}


def read_version(root):
    """
    Read the package version

    Arguments

    root - str
        Repository root, holding the VERSION file

    Returns

    version - str
        The version, such as 1.0.0
    """

    with open(os.path.join(root, "VERSION"), encoding="utf-8") as handle:
        version = handle.read().strip()
    parts = version.split(".")
    if not 1 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"VERSION: '{version}' is not major.minor.patch")
    return version


def read_bytes(root, name):
    """
    Read a repository file

    Arguments

    root - str
        Repository root
    name - str
        Path of the file relative to the root

    Returns

    data - bytes
        The content
    """

    path = os.path.join(root, name)
    if not os.path.isfile(path):
        raise ValueError(f"{name}: not found")
    with open(path, "rb") as handle:
        return handle.read()


def line_endings(data, ending):
    """
    Give a text file one kind of line ending

    Arguments

    data - bytes
        Text content
    ending - bytes
        b"\\n" or b"\\r\\n"

    Returns

    data - bytes
        The content with every line ending replaced
    """

    return data.replace(b"\r\n", b"\n").replace(b"\n", ending)


def metadata(version, count):
    """
    Build the PCM metadata.json text

    Arguments

    version - str
        Package version
    count - int
        Number of symbols in the library

    Returns

    text - str
        The JSON document
    """

    document = {
        "$schema": SCHEMA,
        "name": "Rocketry P&ID Symbols",
        "description": DESCRIPTION.format(count=count),
        "description_full": DESCRIPTION_FULL,
        "identifier": IDENTIFIER,
        "type": "library",
        "author": {
            "name": "Vinay Williams",
            "contact": {"web": "https://github.com/v-i-n-a-y"},
        },
        "license": "MIT",
        "resources": {
            "homepage": HOMEPAGE,
            "issues": HOMEPAGE + "/issues",
        },
        "tags": ["pid", "rocketry", "symbols"],
        "versions": [
            {
                "version": version,
                "status": "stable",
                "kicad_version": "8.0",
            }
        ],
    }
    return json.dumps(document, indent=4, ensure_ascii=False) + "\n"


def pcm_files(root, version, library):
    """
    List the files of the PCM package

    Arguments

    root - str
        Repository root
    version - str
        Package version
    library - bytes
        The compiled symbol library

    Returns

    files - list
        (archive path, content, mode) for each file
    """

    count = library.count(b"\n  (symbol ")
    return [
        ("metadata.json", metadata(version, count).encode("utf-8"), PLAIN),
        (f"symbols/{LIBRARY}", library, PLAIN),
        ("resources/icon.png", read_bytes(root, ICON), PLAIN),
    ]


def install_text(system, version):
    """
    Write the INSTALL.txt of an operating system bundle

    Arguments

    system - str
        windows, macos or linux
    version - str
        Package version

    Returns

    text - str
        The instructions
    """

    names = {"windows": "Windows", "macos": "macOS", "linux": "Linux"}
    return (
        f"Rocketry P&ID Symbols {version} for {names[system]}\n"
        "\n"
        "This installs the pid_kicad symbol library for your user account and\n"
        "adds it to the global symbol library table of every KiCad version it\n"
        "finds (8.0 and later). A copy of the table is saved beside it first.\n"
        "\n"
        f"You need {NEEDS[system]}.\n"
        "\n"
        f"{RUN_STEPS[system]}\n"
        "\n"
        "Options, given to the launcher on the command line\n"
        "\n"
        "  --dry-run               show what would change and change nothing\n"
        "  --uninstall             remove the library and its table entries\n"
        "  --kicad-version 9.0     only touch one KiCad version\n"
        "  --nickname NAME         use another library name instead of pid_kicad\n"
        "\n"
        "No Python? Use the package for KiCad instead. Download\n"
        f"kicad_pid-{version}.zip from {RELEASES}\n"
        "then in KiCad choose Plugin and Content Manager, Install from File.\n"
        "\n"
        "pid_registry.pdf is a to-scale reference of every symbol.\n"
        f"Source and issues: {HOMEPAGE}\n"
        "Licence: MIT, see LICENSE.\n"
    )


def bundle_files(root, system, version, library):
    """
    List the files of an operating system bundle

    Arguments

    root - str
        Repository root
    system - str
        windows, macos or linux
    version - str
        Package version
    library - bytes
        The compiled symbol library

    Returns

    files - list
        (archive path, content, mode) for each file, inside the top folder
    """

    source, name = LAUNCHERS[system]
    ending = b"\r\n" if system == "windows" else b"\n"
    launcher = line_endings(read_bytes(root, source), ending)
    mode = PLAIN if system == "windows" else EXECUTABLE
    text = install_text(system, version).encode("utf-8")
    top = f"{PREFIX}-{version}-{system}"
    files = [
        (name, launcher, mode),
        ("install.py", read_bytes(root, "scripts/install.py"), PLAIN),
        (LIBRARY, library, PLAIN),
        ("LICENSE", read_bytes(root, "LICENSE"), PLAIN),
        ("INSTALL.txt", line_endings(text, ending), PLAIN),
        (REGISTRY, read_bytes(root, REGISTRY), PLAIN),
    ]
    return [(f"{top}/{path}", data, mode) for path, data, mode in files]


def write_zip(path, files):
    """
    Write a zip archive that is the same every time it is built

    Arguments

    path - str
        Archive to write
    files - list
        (archive path, content, mode) for each file
    """

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data, mode in files:
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, data)


def write_tar(path, files):
    """
    Write a gzipped tar archive that is the same every time it is built

    Arguments

    path - str
        Archive to write
    files - list
        (archive path, content, mode) for each file
    """

    with (
        open(path, "wb") as out,
        gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0) as packed,
        tarfile.open(fileobj=packed, mode="w") as archive,
    ):
        for name, data, mode in files:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = mode
            info.mtime = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))


def checksums(folder, names):
    """
    Write SHA256SUMS.txt for the built files

    Arguments

    folder - str
        Directory holding the files
    names - list
        File names to cover

    Returns

    path - str
        The checksum file
    """

    lines = []
    for name in sorted(names):
        with open(os.path.join(folder, name), "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        lines.append(f"{digest}  {name}")
    path = os.path.join(folder, "SHA256SUMS.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def build(root, outdir):
    """
    Build the PCM package, the operating system bundles and the checksums

    Arguments

    root - str
        Repository root
    outdir - str
        Directory to write into, created if missing

    Returns

    names - list
        File names written, checksum file last
    """

    version = read_version(root)
    library = read_bytes(root, LIBRARY)
    if not library.startswith(b"(kicad_symbol_lib"):
        raise ValueError(f"{LIBRARY}: not a KiCad symbol library")
    os.makedirs(outdir, exist_ok=True)

    names = []
    name = f"{PREFIX}-{version}.zip"
    write_zip(os.path.join(outdir, name), pcm_files(root, version, library))
    names.append(name)
    for system in ("windows", "macos"):
        name = f"{PREFIX}-{version}-{system}.zip"
        files = bundle_files(root, system, version, library)
        write_zip(os.path.join(outdir, name), files)
        names.append(name)
    name = f"{PREFIX}-{version}-linux.tar.gz"
    write_tar(os.path.join(outdir, name), bundle_files(root, "linux", version, library))
    names.append(name)

    checksums(outdir, names)
    return names + ["SHA256SUMS.txt"]


def usage():
    """
    Usage

    Prints the script's usage
    """

    print(f"Usage: {sys.argv[0]} <output directory>")
    sys.exit(2)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Package\n")

    if len(sys.argv) != 2:
        usage()
    outdir = sys.argv[1]

    try:
        written = build(ROOT, outdir)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    for written_name in written:
        size = os.path.getsize(os.path.join(outdir, written_name))
        print(f"{written_name}  {size} bytes")
    print(f"\nWrote {len(written)} files to {outdir}")
