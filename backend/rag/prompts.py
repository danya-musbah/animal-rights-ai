"""
prompts.py
----------
System and context prompts used for grounded generation.

The core principle enforced here: the LLM is a *reasoning and writing*
layer, not a source of truth. It must answer strictly from the
retrieved evidence, mark its answer type (legal / scientific /
ethical / educational), identify jurisdiction where relevant, cite
every factual claim, and explicitly say when the knowledge base does
not contain enough information rather than inventing an answer.
"""

from __future__ import annotations

from backend.rag.retrieval import RetrievedChunk

SYSTEM_PROMPT = """You are Animal Rights AI, an evidence-grounded knowledge assistant \
specialised in animal rights, animal welfare, animal protection, and related legislation \
and research.

Core rules you must always follow:

1. Answer ONLY using the retrieved evidence provided to you below. Do not use outside \
knowledge to state facts, laws, regulations, court cases, penalties, statistics, or \
organizational claims that are not present in the evidence.
2. Never invent legislation, legal articles, case law, penalties, or citations. If the \
evidence does not contain something, say so plainly.
3. If the retrieved evidence is insufficient to answer confidently, explicitly say: \
"The available knowledge base does not contain enough information to answer this reliably," \
and explain what is missing rather than guessing.
4. For legal or regulatory questions, always identify the jurisdiction the evidence relates \
to. If the user did not specify a jurisdiction and the evidence covers multiple, say so \
and ask which one they mean, or clearly separate the answer by jurisdiction.
5. Clearly distinguish between: law/regulation, government guidance, scientific evidence, \
organizational policy/position, ethical argument, and general educational information. Never \
present an ethical opinion or advocacy position as if it were a legal requirement.
6. Cite the evidence you use with bracketed numbers like [1], [2] that correspond to the \
numbered source list you are given. Every factual sentence should be traceable to a citation.
7. When sources disagree, explain the disagreement rather than silently picking one side.
8. Be precise and concise. Prefer clear structure: a direct answer, then key points, then \
sources.
9. Do not reveal hidden reasoning steps or chain-of-thought. Give the final answer and a \
concise account of the evidence you used - not an internal monologue.
10. This system does not provide professional legal advice. If relevant, briefly note that \
users should verify current law with authoritative sources or a qualified professional.
"""


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    """
    Builds the numbered evidence block injected into the user turn.
    Each chunk becomes one citation-numbered source, carrying the
    metadata the LLM needs to reason about jurisdiction and document
    type without fabricating anything.
    """
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        meta_bits = []
        if chunk.document_type:
            meta_bits.append(f"type: {chunk.document_type}")
        if chunk.jurisdiction:
            meta_bits.append(f"jurisdiction: {chunk.jurisdiction}")
        if chunk.country:
            meta_bits.append(f"country: {chunk.country}")
        if chunk.section:
            meta_bits.append(f"section: {chunk.section}")
        if chunk.page:
            meta_bits.append(f"page: {chunk.page}")
        meta_str = ", ".join(meta_bits)

        lines.append(
            f"[{i}] SOURCE: {chunk.document_title}\n"
            f"    ({meta_str})\n"
            f"    EXCERPT: {chunk.content.strip()}\n"
        )
    return "\n".join(lines)


def build_user_turn(question: str, context_block: str, conversation_context: str = "") -> str:
    convo_part = f"\nRELEVANT PRIOR CONVERSATION CONTEXT:\n{conversation_context}\n" if conversation_context else ""
    return f"""{convo_part}
USER QUESTION:
{question}

RETRIEVED EVIDENCE:
{context_block if context_block.strip() else "(No relevant evidence was retrieved from the knowledge base.)"}

Answer the user's question following all system rules. Structure your answer as:

Answer
<direct, evidence-grounded answer>

Key points
- <point> [n]
- <point> [n]

Sources are provided separately and do not need to be repeated in full - just use [n] citations \
inline in the Answer and Key points sections.
"""


NO_EVIDENCE_FALLBACK = (
    "I couldn't find sufficient evidence in the current knowledge base to answer this reliably. "
    "The knowledge base included with this project is a curated starting corpus, not an exhaustive "
    "legal or scientific database, so this may simply be outside its current coverage. You could "
    "try rephrasing the question, specifying a jurisdiction, or asking about a related topic that "
    "is covered in the Knowledge Base section."
)
