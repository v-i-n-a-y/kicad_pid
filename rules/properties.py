# Copyright 2026 Vinay Williams

"""
Property and flag rules: Reference prefix, Description, keywords, on_board.
"""

import kisexp


def check_reference(symbol, allowed_prefixes):
    """
    Check the Reference property against the allowed prefixes

    Arguments

    symbol - list
        A symbol node
    allowed_prefixes - set
        Reference prefixes the library permits

    Returns

    messages - list
        One message if the Reference is missing, empty or not allowed
    """

    reference = kisexp.properties(symbol).get("Reference")
    if not reference:
        return ["Reference property is missing or empty"]
    if reference not in allowed_prefixes:
        message = (
            f"Reference {reference!r} is not an allowed prefix "
            f"({', '.join(sorted(allowed_prefixes))})"
        )
        return [message]
    return []


def check_text_properties(symbol):
    """
    Check that the Description and ki_keywords properties are present

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message for each of the two properties that is missing or blank
    """

    props = kisexp.properties(symbol)
    return [
        f"{key} property is missing or empty"
        for key in ("Description", "ki_keywords")
        if not str(props.get(key, "")).strip()
    ]


def check_on_board(symbol):
    """
    Check that the symbol is flagged on_board no

    Arguments

    symbol - list
        A symbol node

    Returns

    messages - list
        One message if the flag is missing or not set to no
    """

    node = kisexp.child(symbol, "on_board")
    if node is None or len(node) < 2 or node[1] != "no":
        return ["on_board must be no"]
    return []


def check(symbol, allowed_prefixes):
    """
    Run every property rule against one symbol

    Arguments

    symbol - list
        A symbol node
    allowed_prefixes - set
        Reference prefixes the library permits

    Returns

    messages - list
        All violation messages from the property rules
    """

    return (
        check_reference(symbol, allowed_prefixes)
        + check_text_properties(symbol)
        + check_on_board(symbol)
    )
