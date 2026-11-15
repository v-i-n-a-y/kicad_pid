# Copyright 2026 Vinay Williams

"""Property and flag rules: Reference prefix, Description, keywords, on_board."""

import kisexp


def check_reference(symbol, allowed_prefixes):
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
    props = kisexp.properties(symbol)
    return [
        f"{key} property is missing or empty"
        for key in ("Description", "ki_keywords")
        if not str(props.get(key, "")).strip()
    ]


def check_on_board(symbol):
    node = kisexp.child(symbol, "on_board")
    if node is None or len(node) < 2 or node[1] != "no":
        return ["on_board must be no"]
    return []


def check(symbol, allowed_prefixes):
    return (
        check_reference(symbol, allowed_prefixes)
        + check_text_properties(symbol)
        + check_on_board(symbol)
    )
