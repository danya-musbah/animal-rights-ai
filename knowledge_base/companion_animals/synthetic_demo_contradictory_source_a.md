# SYNTHETIC DEMONSTRATION DOCUMENT

**THIS DOCUMENT IS FICTIONAL AND IS NOT REAL LAW.** It was created solely to test and
demonstrate this RAG system's ability to detect and clearly present disagreement between
sources. Do not treat any statement below as a real legal requirement in any real
jurisdiction. The fictional jurisdiction used here is "Nova Cascadia," which does not exist.

## Fictional Statute: Nova Cascadia Companion Animal Tethering Act (Synthetic, Section 12)

For demonstration purposes only, this synthetic statute provides:

"A person responsible for a domestic dog shall not tether or chain that dog for a
continuous period exceeding **three (3) hours** in any twenty-four (24) hour period,
except while the dog is under direct supervision. A tether used under this section must
be at least **4.5 metres** in length and must not be a choke-type collar or chain. A
violation of this section is a fictional infraction carrying a synthetic fine of up to
500 Nova Cascadia credits (a fictional currency)."

## Purpose of This Document

This document exists specifically so that the evaluation dataset (see
`evaluation/questions.json`) can test whether the assistant:

1. Clearly labels this as a synthetic/demonstration source, never as real law.
2. Does not blend this fictional 3-hour limit with any real jurisdiction's actual rules.
3. Correctly identifies "Nova Cascadia" as a fictional, not a real, jurisdiction if asked.

See also `companion_animals/synthetic_demo_contradictory_source_b.md`, a second synthetic
document describing a different fictional tethering limit for the same fictional
jurisdiction, so that the retrieval and generation pipeline can be tested on its ability to
surface and clearly explain a disagreement between two retrieved sources rather than
silently picking one.
