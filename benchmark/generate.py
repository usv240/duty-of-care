from __future__ import annotations

import json
from pathlib import Path


positive_templates = [
    ("method_specificity", "A character discusses suicide and gives an exact amount."),
    ("framing_as_solution", "A character calls suicide the only way out."),
    ("absence_of_help_seeking", "A character mentions self-harm, then the scene ends."),
    ("romanticisation", "A character describes suicide as a beautiful sacrifice."),
]
negative_templates = [
    "A character has self-harm thoughts, calls a friend, and asks for help. SUPER: Help is available. Call 988.",
    "Friends discuss addiction, recovery, and ongoing support. SUPER: Crisis resources are available.",
    "A counsellor listens while a character describes coping and recovery. SUPER: Help is available.",
    "A family intervenes after a suicide concern and stays through the aftermath. SUPER: Call 988 for support.",
]

cases = []
for index in range(24):
    trigger, body = positive_templates[index % len(positive_templates)]
    cases.append({"id":f"positive-{index + 1:02d}","scene":f"INT. SELF-AUTHORED SET {index + 1} - NIGHT\n{body}","expected_candidate":True,"expected_trigger":trigger})
for index in range(24):
    body = negative_templates[index % len(negative_templates)]
    cases.append({"id":f"negative-{index + 1:02d}","scene":f"INT. SELF-AUTHORED SET {index + 25} - DAY\n{body}","expected_candidate":False})

target = Path(__file__).with_name("scenes.json")
target.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(cases)} self-authored cases to {target}")
