
import os
import re

from dotenv import load_dotenv
from groq import Groq

# Change the model here and nowhere else. List: https://console.groq.com/docs/models
MODEL = "openai/gpt-oss-120b"

# Reads GROQ_API_KEY from the .env file into os.environ (local runs only).
# On Streamlit Cloud, app.py copies st.secrets into os.environ instead.
load_dotenv()

SYSTEM_PROMPT = """You are CleanSite, a disposal guide for painters and small trade businesses in Centre County, Pennsylvania.

RULES - follow every one:
1. Use ONLY the text inside <sources>. Do not use any outside knowledge, even if you are sure it is true.
2. Every step must restate something the sources actually say. Never invent labels, container names, procedures, or safety tips that are not in the sources.
   Apply each rule only to the situation it describes. Example: "lids removed and interiors cleaned" is about EMPTY cans - never tell someone to empty or clean out a can that still has paint or solvent in it.
3. First decide which ONE kind of waste this is: latex paint; oil-based paint, stain, or varnish; spray paint / aerosol cans; rags or wipes soaked in solvent; or liquid solvent / paint thinner. Rules about rags and wipes apply ONLY to rags and wipes.
4. If the description doesn't tell you which kind it is, reply with exactly one line: FOLLOW_UP: <one short question>
   Examples: "some solvent" -> ask whether it is liquid or soaked into rags, and what kind. "old paint" -> ask whether it is latex (water-based) or oil-based.
5. If the sources do not clearly answer the question for that kind of waste, reply with exactly: NOT_COVERED
6. Otherwise reply with 3 to 5 numbered steps in plain English ("1. ...", "2. ..."). Short sentences. No intro or closing text.
7. Never put phone numbers, fees, prices, addresses, or hours in the steps. Leave them out completely - the app shows them separately, straight from the source.
8. Reply with ONLY one of: the numbered steps, NOT_COVERED, or a FOLLOW_UP line."""

# Safety net for rule 7: any step with a phone number or a $ amount gets dropped,
# because those must come straight from the source, never from the AI.
PHONE_OR_PRICE = re.compile(r"\d{3}[-.)\s]\d{3}[-.\s]\d{4}|\$\s?\d")


def get_client():
    """Create the Groq client. Fails with a clear message if the key is missing."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your-key-here":
        raise RuntimeError("GROQ_API_KEY is missing. Copy .env.example to .env and add your key.")
    return Groq(api_key=api_key)


def format_sources(chunks):
    """Turn the retrieved chunks into one block of text for the prompt.
    Each chunk is labeled so the model knows where it came from."""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[Source {i}: {chunk['title']} - {chunk['heading']}]\n{chunk['text']}")
    return "<sources>\n" + "\n\n".join(parts) + "\n</sources>"


def build_user_message(user_text, situation, chunks, follow_up_q=None, follow_up_a=None):
    """The message we send for this one question (the system prompt stays the same)."""
    where = "a job for a business/customer" if situation == "job" else "their own household"
    msg = (
        f"{format_sources(chunks)}\n\n"
        f"The waste came from: {where}\n"
        f"User's description: {user_text}"
    )
    if follow_up_q and follow_up_a:
        msg += f"\nYou asked: {follow_up_q}\nUser answered: {follow_up_a}"
    return msg


def parse_reply(reply):
    """Turn the model's raw text into a dict the app can use.

    Returns one of:
      {"type": "steps", "steps": [...]}
      {"type": "follow_up", "question": "..."}
      {"type": "not_covered"}
    Anything we can't understand is treated as not_covered - the safe choice.
    """
    reply = (reply or "").strip()

    if "NOT_COVERED" in reply:
        return {"type": "not_covered"}

    match = re.search(r"FOLLOW_UP:\s*(.+)", reply)
    if match:
        return {"type": "follow_up", "question": match.group(1).strip()}

    # Grab lines that start with "1." / "2)" etc. and keep just the text.
    steps = re.findall(r"^\s*\d+[.)]\s+(.+)$", reply, flags=re.MULTILINE)
    # The model sometimes uses odd Unicode spaces/hyphens; swap them for plain ones.
    steps = [s.replace("\u202f", " ").replace("\u2011", "-").strip() for s in steps]
    steps = [s for s in steps if not PHONE_OR_PRICE.search(s)]
    if steps:
        return {"type": "steps", "steps": steps[:5]}

    return {"type": "not_covered"}


def ask_model(user_text, situation, chunks, follow_up_q=None, follow_up_a=None):
    """Send one question to the model and return the parsed reply (see parse_reply)."""
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            # "system" = standing instructions; "user" = this specific question.
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(user_text, situation, chunks,
                                                           follow_up_q, follow_up_a)},
        ],
        # gpt-oss "thinks" before answering. We don't need to see that thinking.
        # "low" was too sloppy in testing (it invented steps), so we use "medium".
        reasoning_effort="medium",
        include_reasoning=False,
        max_completion_tokens=2000,
    )
    reply = response.choices[0].message.content or ""    
    result = parse_reply(reply)
    result["raw"] = reply  # keep the original text for debugging
    return result
