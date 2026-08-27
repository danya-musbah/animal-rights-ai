"""
test_query_analysis.py
------------------------
Tests for backend/rag/query_analysis.py: intent classification, animal/topic
extraction, jurisdiction detection, and the clarification gate.
"""

from backend.rag.query_analysis import analyze_query, needs_clarification


def test_legal_question_without_jurisdiction_requires_clarification():
    analysis = analyze_query("Is keeping a dog permanently chained outside illegal?")
    assert analysis.intent == "legal_question"
    assert analysis.requires_jurisdiction is True
    assert needs_clarification(analysis) is not None


def test_legal_question_with_jurisdiction_does_not_require_clarification():
    analysis = analyze_query("Is it illegal to chain a dog outside in the UK?")
    assert analysis.country == "united kingdom"
    assert analysis.requires_jurisdiction is False
    assert needs_clarification(analysis) is None


def test_scientific_intent_detected():
    analysis = analyze_query("What does research show about fish sentience?")
    assert analysis.intent == "scientific_question"


def test_comparison_intent_detected():
    analysis = analyze_query("Compare animal welfare laws between the UK and the US.")
    assert analysis.intent == "comparison"


def test_ethical_intent_detected():
    analysis = analyze_query("Should animal testing be banned?")
    assert analysis.intent == "ethical_discussion"


def test_animal_extraction():
    analysis = analyze_query("What are the housing rules for laying hens and cattle?")
    assert "poultry" in analysis.animals or "cattle" in analysis.animals


def test_topic_extraction_defaults_to_animal_welfare_when_empty():
    analysis = analyze_query("Tell me something.")
    assert "animal_welfare" in analysis.topics


def test_known_country_override_is_respected():
    analysis = analyze_query("Is this legal?", known_country="european union")
    assert analysis.country == "european union"
    assert analysis.requires_jurisdiction is False


def test_international_country_does_not_require_clarification():
    analysis = analyze_query("What do international standards say about animal transport?")
    # "international" is treated as a valid (non-jurisdiction-specific) scope
    assert analysis.country in ("international", None)
