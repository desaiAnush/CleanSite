from gaps import check_gaps, not_covered_gap
from llm import ask_model
from retrieval import load_chunks, search

CHUNKS = load_chunks()  


def get_answer(user_text, county="Centre", situation="household",
               follow_up_q=None, follow_up_a=None):
    """Run one question through CleanSite.

    situation:   "household" or "job"
    follow_up_q/a: pass these on the second try, after the user answered our
                   one follow-up question. We never ask a second follow-up.

    Returns a dict with a "screen" key telling the app what to show:
      "gap"         -> gap (the "I don't know" info)
      "follow_up"   -> question
      "answer"      -> steps + chunks (+ job_warning)
      "all_matches" -> chunks (still vague after the follow-up, so show them all)
    """
    
    full_text = user_text if not follow_up_a else f"{user_text} {follow_up_a}"
    job_warning = situation == "job"

    # Step 1: known gaps 
    gap = check_gaps(full_text, county)
    if gap:
        return {"screen": "gap", "gap": gap}

    # Step 2:  if nothing matches dont ask AI
    results = search(full_text, CHUNKS)
    if not results:
        return {"screen": "gap", "gap": not_covered_gap()}
    chunks = [chunk for score, chunk in results]

    # Step 3: ask the model only using those chunks
    reply = ask_model(user_text, situation, chunks, follow_up_q, follow_up_a)

    if reply["type"] == "not_covered":
        return {"screen": "gap", "gap": not_covered_gap(), "raw": reply["raw"]}

    if reply["type"] == "follow_up":
        if follow_up_a:
            # We already asked once. Don't ask again - show every matching source.
            return {"screen": "all_matches", "chunks": chunks, "job_warning": job_warning}
        return {"screen": "follow_up", "question": reply["question"]}

    return {"screen": "answer", "steps": reply["steps"], "chunks": chunks,
            "job_warning": job_warning, "raw": reply["raw"]}
