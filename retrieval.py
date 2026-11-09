import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
TOP_K = 3  

SKIP_HEADINGS = ["gaps and conflicts", "when cleansite should send"]

#synonym map to match close related words
SYNONYMS = {
    "rag": "solvent contaminated wipes",
    "wipe": "solvent contaminated wipes",
    "towel": "solvent contaminated wipes",
    "spray paint": "aerosol",
    "spray can": "aerosol",
    "oil paint": "oil-based",
    "oil based": "oil-based",
    "stain": "oil-based",
    "varnish": "oil-based",
    "enamel": "oil-based",
    "water based": "latex",
    "acrylic": "latex",
    "thinner": "solvents hhw collection event",
    "mineral spirits": "thinner solvents hhw collection event",
    "turpentine": "thinner solvents hhw collection event",
    "acetone": "solvents",
    "dump": "transfer station",
    "drop off": "transfer station",
    "hours": "transfer station",
    "open": "transfer station hours",
}

#common words that don't help find the right chunk
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for", "from",
    "with", "by", "is", "are", "was", "it", "its", "this", "that", "these",
    "i", "me", "my", "we", "our", "you", "your", "do", "does", "can", "could",
    "should", "would", "what", "how", "where", "when", "which", "who", "if",
    "some", "any", "about", "get", "rid", "have", "has", "had", "be", "not",
    "no", "yes", "up", "out", "into", "off", "so", "just", "like", "there",
    "old", "leftover", "left", "over", "half", "full", "bit", "lot", "bunch",
    "few", "several", "gallon", "gallons", "quart", "quarts", "bucket",
    "box", "bag", "label", "torn", "kind", "sort", "stuff", "thing", "things",
}


def normalize(word):
    """Crude plural removal so 'rags' matches 'rag' and 'cans' matches 'can'."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text):
    """Lowercase, split into words, drop stopwords, strip plurals.
    Returns a set, so each keyword is only counted once."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {normalize(w) for w in words if w not in STOPWORDS}


def expand_query(text):
    """Keywords from the user's text, plus extra keywords from SYNONYMS."""
    # Check synonyms against the plural-stripped text so "rags" matches "rag".
    lowered = " ".join(normalize(w) for w in re.findall(r"[a-z0-9]+", text.lower()))
    terms = tokenize(text)
    for phrase, extra in SYNONYMS.items():
        if phrase in lowered:
            terms |= tokenize(extra)
    return terms


def read_header_sources(header):
    """Pull the source lines out of a kb file's header (the part above the
    first ## heading). We show these on the source card exactly as written."""
    lines = []
    for line in header.splitlines():
        line = line.strip()
        is_source_field = line.startswith(("**Primary source:**", "**Sources:**", "**Also drawn from:**"))
        is_numbered_source = re.match(r"^\d+\. ", line)  # kb02 lists sources as "1. ..."
        if is_source_field or is_numbered_source:
            lines.append(line.replace("**", ""))
    return "\n".join(lines)


def load_chunks():
    """Read every .md file in knowledge/ and split it into chunks by '## ' heading.

    Each chunk is a plain dict:
      file     - e.g. "kb02.md"
      title    - the file's "# " title
      sources  - source lines from the file header (for the source card)
      heading  - the "## " heading text
      text     - the section body, word for word from the file
    """
    chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")

        # Split right before each line that starts with "## ".
        # parts[0] is the header (title + sources); the rest are sections.
        parts = re.split(r"\n(?=## )", content)
        header = parts[0]
        title = header.splitlines()[0].lstrip("# ").strip()
        sources = read_header_sources(header)

        for part in parts[1:]:
            heading_line, _, body = part.partition("\n")
            chunks.append({
                "file": path.name,
                "title": title,
                "sources": sources,
                "heading": heading_line.lstrip("# ").strip(),
                "text": body.strip(),
            })
    return chunks


def score_chunk(query_terms, chunk):
    """+1 for each query keyword found in the chunk body,
    +2 extra if it's also in the heading (headings say what a section is about)."""
    body_words = tokenize(chunk["text"])
    heading_words = tokenize(chunk["heading"])
    score = 0
    for term in query_terms:
        if term in body_words:
            score += 1
        if term in heading_words:
            score += 2
    return score


def search(user_text, chunks=None, top_k=TOP_K):
    """Return up to top_k (score, chunk) pairs, best first.
    Returns [] if no chunk matches at all -> caller shows "I don't know"."""
    if chunks is None:
        chunks = load_chunks()
    query_terms = expand_query(user_text)

    scored = []
    for chunk in chunks:
        if any(skip in chunk["heading"].lower() for skip in SKIP_HEADINGS):
            continue
        score = score_chunk(query_terms, chunk)
        if score > 0:
            scored.append((score, chunk))

    # Highest score first. Python's sort is stable, so ties keep file order.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    # Quick check: run `python retrieval.py` and eyeball the results.
    all_chunks = load_chunks()
    print(f"Loaded {len(all_chunks)} chunks from {KNOWLEDGE_DIR.name}/\n")

    sample_queries = [
        "3 gallons of leftover latex paint from my house",
        "half a can of old oil paint",
        "a bucket of rags soaked in thinner from a job",
        "some solvent",
        "old gasoline",
    ]
    for query in sample_queries:
        print("=" * 70)
        print(f"QUERY: {query}")
        print(f"keywords: {sorted(expand_query(query))}")
        results = search(query, all_chunks)
        if not results:
            print("  -> no match (score 0) -> 'I don't know' screen")
        for score, chunk in results:
            print(f"  [{score:>2}] {chunk['file']}  ## {chunk['heading']}")
        print()
