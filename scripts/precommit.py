# Copyright 2026 Vinay Williams

import os
import subprocess
import sys
import tempfile

import utils

HERE = os.path.dirname(os.path.abspath(__file__))


def run_script(name, *args, capture=False):
    """
    Run a sibling script with this interpreter

    Arguments

    name - str
        File name of the script
    args - str
        Command line arguments for it
    capture - bool
        Capture its output instead of showing it

    Returns

    done - CompletedProcess
        The finished process
    """

    sys.stdout.flush()
    return subprocess.run(
        [sys.executable, os.path.join(HERE, name), *args],
        capture_output=capture,
        text=capture,
        check=False,
    )


def sources_match_library(libpath, symbolsdir):
    """
    Check whether compiling the sources would reproduce the library

    Arguments

    libpath - str
        Path to the monolith library
    symbolsdir - str
        Directory containing the symbol sources

    Returns

    result - bool
        True if the compiled text equals the library on disk
    """

    with tempfile.TemporaryDirectory() as scratch:
        probe = os.path.join(scratch, "probe.kicad_sym")
        if run_script("compile.py", symbolsdir, probe, capture=True).returncode:
            return False
        with open(probe, "rb") as a, open(libpath, "rb") as b:
            return a.read() == b.read()


def step(label, name, *args):
    """
    Announce and run one build step

    Arguments

    label - str
        What is being done
    name - str
        File name of the script to run
    args - str
        Command line arguments for it

    Returns

    code - int
        The script's exit status
    """

    print(f"{label}\n")
    code = run_script(name, *args).returncode
    if code != 0:
        print(f"Error: {name} failed with exit status {code}", file=sys.stderr)
    return code


def main(libpath, symbolsdir):
    """
    Bring the monolith, the symbol sources and the plots into step

    Arguments

    libpath - str
        Path to the monolith library
    symbolsdir - str
        Directory containing the symbol sources

    Returns

    code - int
        Exit status, non-zero if a step failed or the two sides conflict
    """

    plotsdir = os.path.join(os.path.dirname(os.path.abspath(symbolsdir)), "plots")
    try:
        symbol_changes = any(
            p.endswith(utils.SYMBOL_SUFFIX) for p in utils.changed_paths(symbolsdir)
        )
        monolith_changes = bool(utils.changed_paths(libpath))
    except utils.GitError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if monolith_changes and symbol_changes:
        # after a hook run has compiled, both look changed; only a real difference is a conflict
        if not sources_match_library(libpath, symbolsdir):
            print(
                "Error: Both the monolithic library and the individual symbols "
                "changed, and they differ. Run `make compile` to keep the symbols "
                "or `make decompile` to keep the library.",
                file=sys.stderr,
            )
            return 1
        print("Library and symbols both changed but agree, plotting")
    elif symbol_changes:
        code = step(
            "Only symbol changes, compiling monolith and plotting",
            "compile.py",
            symbolsdir,
            libpath,
        )
        if code:
            return code
    elif monolith_changes:
        code = step(
            "Only monolith changes, decompiling and plotting",
            "decompile.py",
            libpath,
            symbolsdir,
        )
        if code:
            return code
    else:
        print("No changes")
        return 0
    return step("Plotting", "plot.py", symbolsdir, plotsdir)


def usage():
    """
    Usage

    Prints the script's usage
    """

    print(f"Usage: {sys.argv[0]} <monolith lib path> <symbols directory>")
    sys.exit(2)


if __name__ == "__main__":
    print("Rocketry P&ID KiCAD - Precommit\n")

    if len(sys.argv) != 3:
        usage()
    sys.exit(main(sys.argv[1], sys.argv[2]))
