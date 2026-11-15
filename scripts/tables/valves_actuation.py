# Copyright 2026 Vinay Williams

"""
Table entries for the solenoid actuated valves and for the actuated
three-way and angle valves.
"""

ENTRIES = []

for _body in ("Ball", "Butterfly", "Diaphragm", "Gate", "Globe", "Needle"):
    ENTRIES.append(
        (
            f"Valve - {_body} Solenoid",
            "XV",
            f"{_body} valve, solenoid actuated",
            f"valve {_body.lower()} solenoid actuated xv",
        )
    )

_ACTUATORS = (
    ("Pneumatic", "pneumatically actuated", "pneumatic"),
    ("Solenoid", "solenoid actuated", "solenoid"),
    ("Servo", "servo actuated", "servo"),
)

for _base, _label, _words in (
    ("3 Way Ball", "Three-way ball valve", "valve three way 3 ball"),
    ("3 Way Globe", "Three-way globe valve", "valve three way 3 globe"),
    ("Angle Ball", "Angle ball valve", "valve angle right-angle ball"),
    ("Angle Globe", "Angle globe valve", "valve angle right-angle globe"),
):
    for _variant, _text, _key in _ACTUATORS:
        ENTRIES.append(
            (
                f"Valve - {_base} {_variant}",
                "XV",
                f"{_label}, {_text}",
                f"{_words} {_key} actuated xv",
            )
        )
