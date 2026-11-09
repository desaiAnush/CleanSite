

import re

#Contacts from knowledge files
CCRRA = {
    "name": "Centre County Recycling and Refuse Authority (CCRRA)",
    "phone": "814-238-7005",          # kb02.md header ("from the flyer")
    "detail": "253 Transfer Road, Bellefonte, PA 16823",
}
DEP = {
    "name": "PA DEP Hazardous Waste Division",
    "phone": "717-787-6239",          # kb01.md section 9
    "detail": "RA-HazWaste@pa.gov",
}


#Words that mean this came from a business not a household
BUSINESS_WORDS = ["company", "contractor", "business", "job", "jobsite", "job site",
                  "crew", "client", "customer", "commercial", "my shop", "employer"]

#Words that mean the county's household drop-off programs
COUNTY_DROPOFF_WORDS = ["hhw", "household hazardous", "collection event", "event",
                        "transfer station", "ccrra", "county drop", "drop off", "drop-off"]

#Words that mean work done in someone else's home
CUSTOMER_WORDS = ["customer", "client", "homeowner"]
HOME_WORDS = ["home", "house", "household", "residence"]

#Items people may ask about that our sources don't cover at all
NOT_IN_SOURCES_WORDS = ["gasoline", "gas can", "motor oil", "used oil", "engine oil",
                        "antifreeze", "coolant", "battery", "batteries", "propane",
                        "pesticide", "herbicide", "fertilizer", "pool chemical",
                        "fluorescent", "mercury", "tire", "tires", "asbestos", "lead"]

#Things that clearly aren't paint/solvent waste at all
OFF_TOPIC_WORDS = ["soup", "food", "pizza", "meat", "vegetable", "fruit", "leftovers",
                   "yard waste", "grass", "leaves", "clothes", "clothing", "furniture",
                   "mattress", "couch", "electronics", "tv", "computer", "phone"]

#If any of these appear, the question is about paint/solvents, so never call it off-topic
ON_TOPIC_WORDS = ["paint", "stain", "varnish", "solvent", "thinner", "rag", "wipe",
                  "aerosol", "spray", "latex", "primer", "sealer", "stripper", "lacquer",
                  "spirits", "turpentine", "finish", "coating", "degreaser", "linseed"]


def has_any(text, words):
    """True if any word/phrase appears in text as a whole word.
    \\b = word boundary, so 'tire' doesn't match 'entire' and 'tv' doesn't match 'tvs'."""
    return any(re.search(r"\b" + re.escape(w) + r"s?\b", text) for w in words)


def check_gaps(user_text, county):
    """Return a gap dict if the question hits a known gap, otherwise None.

    A gap dict has:
      id       - short name, handy for tests
      headline - big text on the "I don't know" screen
      message  - one or two plain sentences explaining why
      contacts - list of contact dicts to show
    Order matters: the first rule that matches wins.
    """
    text = user_text.lower()

    
    if county.lower().startswith("blair") or "blair" in text:
        return {
            "id": "blair",
            "headline": "Blair County isn't covered yet",
            "message": "CleanSite only has Centre County sources right now. "
                       "Blair County support is coming soon.",
            "contacts": [DEP],
        }

    # 2. Contractor/business waste at the county HHW event or Transfer Station.
    #    kb02 section 5.1: no source says whether contractors qualify.
    if has_any(text, BUSINESS_WORDS) and has_any(text, COUNTY_DROPOFF_WORDS):
        return {
            "id": "contractor_eligibility",
            "headline": "I don't know - my sources don't answer this",
            "message": "CCRRA's paint guidance and HHW event are written for households. "
                       "None of my sources say whether a business or contractor's waste is "
                       "accepted. Please call before bringing it in.",
            "contacts": [CCRRA, DEP],
        }

   
    if has_any(text, CUSTOMER_WORDS) and has_any(text, HOME_WORDS):
        return {
            "id": "customer_home",
            "headline": "I don't know - this needs a DEP answer",
            "message": "PA DEP doesn't say whether leftover paint from a contractor working "
                       "in a customer's home counts as household waste. Ask DEP directly.",
            "contacts": [DEP],
        }

    # 4. Items that aren't in our sources at all (e.g. gasoline, motor oil).
    if has_any(text, NOT_IN_SOURCES_WORDS):
        return {
            "id": "not_in_sources",
            "headline": "Not covered by my sources",
            "message": "My sources don't cover this item. Keep it sealed in its original "
                       "container, away from heat, and call CCRRA to ask how to get rid of it.",
            "contacts": [CCRRA],
        }

    # 5. Off-topic (food, furniture, ...), but only if nothing paint-related is mentioned.
    if has_any(text, OFF_TOPIC_WORDS) and not has_any(text, ON_TOPIC_WORDS):
        return {
            "id": "off_topic",
            "headline": "That's outside what CleanSite covers",
            "message": "CleanSite only helps with leftover paint, stains, solvents, and "
                       "related painting waste. For general trash and recycling, ask CCRRA.",
            "contacts": [CCRRA],
        }

    return None  # no known gap -> go on to retrieval


# Used when retrieval finds nothing, or the AI says NOT_COVERED.
def not_covered_gap():
    return {
        "id": "not_covered",
        "headline": "I don't know - my sources don't cover this",
        "message": "I couldn't find this in my sources, and I won't guess. "
                   "Keep the item sealed and call one of these numbers.",
        "contacts": [CCRRA, DEP],
    }
