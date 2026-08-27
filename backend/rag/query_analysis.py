"""
query_analysis.py
------------------
Query understanding stage of the RAG pipeline.

Before any retrieval happens, the raw user question is analysed to
extract:

  - intent (legal_question, scientific_question, comparison,
    definition, ethical_discussion, factual, general)
  - animal(s) mentioned
  - topic(s)
  - country / jurisdiction (if stated)
  - document_type hint
  - whether the question is a legal/regulatory question that
    critically depends on an unknown jurisdiction (in which case the
    pipeline should ask a clarifying question rather than guessing)

This is implemented with transparent, inspectable rule-based NLP
(keyword/pattern matching) so behaviour is deterministic and free to
run. It can be upgraded to an LLM-based classifier by replacing the
body of `analyze_query` while keeping the same `QueryAnalysis`
contract used by the rest of the pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ANIMALS = {
    "dog": ["dog", "dogs", "puppy", "puppies", "canine"],
    "cat": ["cat", "cats", "kitten", "kittens", "feline"],
    "horse": ["horse", "horses", "equine"],
    "cattle": ["cattle", "cow", "cows", "bovine", "calf", "calves"],
    "pig": ["pig", "pigs", "swine", "hog", "hogs"],
    "poultry": ["chicken", "chickens", "poultry", "hen", "hens", "broiler", "layer hens"],
    "wildlife": ["wildlife", "wild animal", "wild animals"],
    "primate": ["primate", "primates", "monkey", "chimpanzee"],
    "marine": ["whale", "dolphin", "marine mammal", "fish welfare", "aquaculture"],
    "laboratory_animal": ["laboratory animal", "lab animal", "test animal", "research animal"],
    "endangered_species": ["endangered species", "endangered animal", "extinction"],
    "zoo_animal": ["zoo animal", "zoo", "captive wildlife"],
}

TOPICS = {
    "animal_welfare": ["welfare", "wellbeing", "five freedoms", "sentience"],
    "animal_cruelty": ["cruelty", "abuse", "neglect", "mistreatment"],
    "animal_testing": ["testing", "vivisection", "experimentation", "3rs", "replacement reduction refinement"],
    "farming": ["farming", "livestock", "slaughter", "factory farm", "intensive farming"],
    "transport": ["transport", "transportation", "journey time", "live export"],
    "wildlife_protection": ["wildlife protection", "conservation", "poaching", "habitat"],
    "legislation": ["law", "act", "statute", "regulation", "legal", "legislation", "illegal", "penalty"],
    "international_standards": ["international standard", "who", "woah", "oie", "treaty", "convention"],
    "companion_animals": ["pet", "companion animal", "shelter", "adoption"],
    "organizations": ["organization", "organisation", "charity", "ngo"],
}

COUNTRIES = {
    "united kingdom": ["uk", "united kingdom", "england", "wales", "scotland", "northern ireland", "britain"],
    "united states": ["us", "usa", "united states", "america"],
    "european union": ["eu", "european union", "europe"],
    "germany": ["germany", "german"],
    "france": ["france", "french"],
    "australia": ["australia", "australian"],
    "canada": ["canada", "canadian"],
    "india": ["india", "indian"],
    "international": ["international", "global", "worldwide"],
}

LEGAL_TRIGGER_WORDS = ["illegal", "legal", "law", "allowed", "banned", "prohibited", "penalty", "fine", "offence", "offense", "crime"]
SCIENTIFIC_TRIGGERS = ["research shows", "study", "evidence suggests", "scientific", "sentience", "cognition", "peer-reviewed"]
COMPARISON_TRIGGERS = ["compare", "versus", " vs ", "difference between", "which country", "differ"]
DEFINITION_TRIGGERS = ["what is", "what are", "define", "meaning of", "difference between animal rights and animal welfare"]
ETHICAL_TRIGGERS = ["should", "ethical", "moral", "right or wrong", "justify", "argument for", "argument against"]


@dataclass
class QueryAnalysis:
    raw_query: str
    intent: str = "general"
    animals: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    country: str | None = None
    jurisdiction: str | None = None
    document_type_hint: str | None = None
    requires_jurisdiction: bool = False
    is_out_of_scope: bool = False


def _match_any(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def analyze_query(query: str, known_country: str | None = None) -> QueryAnalysis:
    text = f" {query.lower()} "

    animals = [key for key, kws in ANIMALS.items() if _match_any(text, kws)]
    topics = [key for key, kws in TOPICS.items() if _match_any(text, kws)]

    country = known_country
    if not country:
        for key, kws in COUNTRIES.items():
            if _match_any(text, kws):
                country = key
                break

    is_scientific = _match_any(text, SCIENTIFIC_TRIGGERS)
    is_comparison = _match_any(text, COMPARISON_TRIGGERS)
    is_definition = _match_any(text, DEFINITION_TRIGGERS)
    # Normative framing ("should X be banned") is ethical even if it shares
    # vocabulary (e.g. "banned") with factual legal-status questions
    # ("is X banned/illegal"), so ethical framing is detected first and
    # takes precedence over the overlapping legal keywords.
    is_ethical = _match_any(text, ETHICAL_TRIGGERS)
    is_legal = (_match_any(text, LEGAL_TRIGGER_WORDS) or "legislation" in topics) and not is_ethical

    if is_comparison:
        intent = "comparison"
    elif is_legal:
        intent = "legal_question"
    elif is_scientific:
        intent = "scientific_question"
    elif is_definition:
        intent = "definition"
    elif is_ethical:
        intent = "ethical_discussion"
    else:
        intent = "general"

    document_type_hint = None
    if is_legal:
        document_type_hint = "legislation"
    elif is_scientific:
        document_type_hint = "scientific_research"
    elif "organizations" in topics:
        document_type_hint = "organization_report"

    requires_jurisdiction = is_legal and country is None and country != "international"

    return QueryAnalysis(
        raw_query=query,
        intent=intent,
        animals=animals,
        topics=topics or (["animal_welfare"] if not topics else topics),
        country=country,
        jurisdiction=country,
        document_type_hint=document_type_hint,
        requires_jurisdiction=requires_jurisdiction,
    )


def needs_clarification(analysis: QueryAnalysis) -> str | None:
    """
    Returns a clarification question string if the pipeline should
    pause and ask the user something before retrieving/answering, or
    None if it's safe to proceed.
    """
    if analysis.requires_jurisdiction:
        return (
            "This looks like a legal or regulatory question, and animal protection "
            "law varies significantly between countries. Which country or jurisdiction "
            "are you asking about? (e.g. United Kingdom, European Union, United States)"
        )
    return None
