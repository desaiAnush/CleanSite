# CleanSite

Plain-English disposal steps for leftover paint, solvents, and rags in Centre County, PA, with the source shown under every answer.

I co-run a small painting business (Brush Bros), and at the end of jobs we always had leftover paint, thinner rags, and spray cans. The county and state rules exist, but they're spread across DEP FAQs, EPA fact sheets, and county flyers. Chatbots answer confidently with nothing to back it up. CleanSite only answers from sources I collected, and says "I don't know" with a county phone number when those sources don't cover the question.

Built as my MVP for A-I 285 class at Penn State.

**Live app:** _add Streamlit Cloud link_

## How it works

1. **Rule checks (`gaps.py`)** - keyword rules, no AI. Risky questions (contractor waste at the county event, gasoline, Blair County, etc.) go straight to an "I don't know" screen with the right contact.
2. **Keyword search (`retrieval.py`)** - splits the knowledge files into sections by heading and picks the best 2-3 matches. No match = no AI call.
3. **LLM (`llm.py`)** - `gpt-oss-120b` on Groq sees only those sections and must reply with numbered steps, one follow-up question, or `NOT_COVERED`.

Phone numbers, hours, and fees are always copied from the source files, never written by the AI. `pipeline.py` ties the three steps together in one function used by both the app and the tests.

## Knowledge base

| File | Covers |
| --- | --- |
| `knowledge/kb01.md` | PA DEP hazardous waste generator rules |
| `knowledge/kb02.md` | Centre County / CCRRA household options |
| `knowledge/kb03.md` | Job waste for painters and small businesses (EPA VSQG, DEP universal waste) |

Each file lists its sources and retrieval dates at the top.

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env        # then add your Groq API key
streamlit run app.py
```

Run the test questions: `python test_questions.py`

## Limitations

- Centre County only (Blair County is next)
- Keyword search can miss phrasings that aren't in the synonym map
- Not legal advice - a plain-language summary of public sources
