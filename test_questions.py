"""
test_questions.py - run the 8 CleanSite test questions end to end in the terminal.

Run:  python test_questions.py
Each test prints what CleanSite decided, then PASS / FAIL on the screen type.
Read the steps yourself too - the script can't judge whether wording is right.
"""

import re

from pipeline import get_answer

# (question, county, situation, expected screen)
TESTS = [
    ("3 gallons of leftover latex paint from my house", "Centre", "household", "answer"),
    ("half a can of old oil paint", "Centre", "household", "answer"),
    ("a bucket of rags soaked in thinner from a job", "Centre", "job", "answer"),
    ("some solvent", "Centre", "household", "follow_up"),
    ("Can I bring my company's leftover paint to the county HHW event?", "Centre", "job", "gap"),
    ("old gasoline", "Centre", "household", "gap"),
    ("leftover tomato soup", "Centre", "household", "gap"),
    ("spray paint cans, Blair County", "Centre", "household", "gap"),
]

# Simulated answer for test 4's follow-up, to show the second (final) try.
FOLLOW_UP_ANSWER = "it's paint thinner"

PHONE_OR_MONEY = re.compile(r"\d{3}[-.)\s]\d{3}[-.\s]\d{4}|\$\d")


def show(result):
    """Print a result dict in a readable way."""
    screen = result["screen"]
    if screen == "gap":
        gap = result["gap"]
        print(f"  [{gap['id']}] {gap['headline']}")
        print(f"  {gap['message']}")
        for c in gap["contacts"]:
            print(f"    call: {c['name']} {c['phone']} ({c['detail']})")
    elif screen == "follow_up":
        print(f"  FOLLOW-UP: {result['question']}")
    elif screen in ("answer", "all_matches"):
        for i, step in enumerate(result.get("steps", []), start=1):
            print(f"  {i}. {step}")
            if PHONE_OR_MONEY.search(step):
                print("     ^ WARNING: step contains a phone number or price")
        for chunk in result["chunks"]:
            print(f"  source: {chunk['file']} ## {chunk['heading']}")
        if result.get("job_warning"):
            print("  JOB WARNING: county rules for contractors aren't confirmed - call CCRRA 814-238-7005")


passed = 0
for n, (question, county, situation, expected) in enumerate(TESTS, start=1):
    print("=" * 72)
    print(f"TEST {n}: {question!r}  ({county}, {situation})")
    try:
        result = get_answer(question, county, situation)
    except Exception as e:  # e.g. missing key, rate limit, no internet
        print(f"  ERROR: {e}")
        continue
    show(result)

    # Test 4: answer the follow-up once and show the second try.
    if result["screen"] == "follow_up":
        print(f"  ...user answers: {FOLLOW_UP_ANSWER!r}")
        second = get_answer(question, county, situation,
                            follow_up_q=result["question"], follow_up_a=FOLLOW_UP_ANSWER)
        print(f"  second try -> screen: {second['screen']}")
        show(second)

    ok = result["screen"] == expected
    passed += ok
    print(f"  {'PASS' if ok else 'FAIL'} (expected screen: {expected}, got: {result['screen']})")

print("=" * 72)
print(f"{passed}/{len(TESTS)} tests got the expected screen type.")
