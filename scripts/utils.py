# Copyright 2026 Vinay Williams

import os
import subprocess
import tempfile

import kisexp
from kisexp import Str

SYMBOL_SUFFIX = ".kicad_sym"
UNCATEGORISED = "uncategorised"

LIB_VERSION = "20231120"
LIB_GENERATOR = "kicad_symbol_editor"
LIB_GENERATOR_VERSION = "8.0"


class GitError(RuntimeError):
    """
    Git is missing, or could not report the state of the working tree
    """


def symbol_files(root):
    """
    Find every symbol file under a directory

    Arguments

    root - str
        Directory to search, recursively

    Returns

    paths - list
        Full paths of the .kicad_sym files, sorted
    """

    found = []
    for folder, _, names in os.walk(root):
        found.extend(
            os.path.join(folder, n) for n in names if n.endswith(SYMBOL_SUFFIX)
        )
    return sorted(found)


def symbol_name(path):
    """
    Name the symbol a source file holds

    Arguments

    path - str
        Path of a .kicad_sym file

    Returns

    name - str
        The file name without the .kicad_sym suffix
    """

    return os.path.basename(path)[: -len(SYMBOL_SUFFIX)]


def library_tree(symbols, quote_generator=True):
    """
    Build a library tree around some symbol nodes

    Arguments

    symbols - list
        Symbol nodes to place in the library
    quote_generator - bool
        Quote the generator fields as KiCad writes them. The per-symbol
        source files keep the bare generator name they have always had.

    Returns

    tree - list
        The kicad_symbol_lib tree
    """

    text = Str if quote_generator else str
    return [
        "kicad_symbol_lib",
        ["version", LIB_VERSION],
        ["generator", text(LIB_GENERATOR)],
        ["generator_version", Str(LIB_GENERATOR_VERSION)],
        *symbols,
    ]


def library_text(tree):
    """
    Serialise a library tree in the form KiCad writes

    Arguments

    tree - list
        The kicad_symbol_lib tree

    Returns

    text - str
        Library text, starting at the opening parenthesis
    """

    return kisexp.dump(tree).lstrip("\n") + "\n"


def write_text(path, text):
    """
    Write a file through a temporary file, so a failure leaves no half file

    Arguments

    path - str
        File to write
    text - str
        Content to write
    """

    folder = os.path.dirname(os.path.abspath(path))
    handle, temp = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.remove(temp)
        raise


def run_git(cwd, *args):
    """
    Run a git command

    Arguments

    cwd - str
        Directory to run it in
    args - str
        The git sub-command and its options

    Returns

    output - str
        What git printed on stdout
    """

    try:
        done = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        raise GitError("git is not installed or not on PATH") from None
    if done.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def changed_paths(target):
    """
    List what git reports as changed at or under a path

    Staged, unstaged, untracked, deleted and renamed entries all count, and
    both ends of a rename. Raises GitError if the state cannot be read.

    Arguments

    target - str
        A file or a directory

    Returns

    changed - set
        Real paths of the changed files
    """

    if os.path.isdir(target):
        cwd, spec = target, "."
    else:
        cwd, spec = os.path.dirname(os.path.abspath(target)), os.path.basename(target)
    top = run_git(cwd, "rev-parse", "--show-toplevel").strip()
    out = run_git(
        cwd, "status", "--porcelain", "-z", "--untracked-files=all", "--", spec
    )
    fields = out.split("\0")
    changed = set()
    i = 0
    while i < len(fields) and len(fields[i]) > 3:
        status, name = fields[i][:2], fields[i][3:]
        changed.add(os.path.realpath(os.path.join(top, name)))
        i += 1
        # a rename or copy is followed by a second field naming the origin
        if "R" in status or "C" in status:
            changed.add(os.path.realpath(os.path.join(top, fields[i])))
            i += 1
    return changed


def file_changed(path, changed):
    """
    Test one file against the output of changed_paths

    Arguments

    path - str
        File to look for
    changed - set
        Real paths returned by changed_paths

    Returns

    result - bool
        True if the file is among them
    """

    return os.path.realpath(path) in changed
