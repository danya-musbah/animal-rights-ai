# SYNTHETIC DEMONSTRATION DOCUMENT

**THIS DOCUMENT IS FICTIONAL AND IS NOT REAL LAW.** It was created solely to test and
demonstrate this RAG system's ability to detect and clearly present disagreement between
sources. Do not treat any statement below as a real legal requirement in any real
jurisdiction. The fictional jurisdiction used here is "Nova Cascadia," which does not exist.

## Fictional Municipal Ordinance: Riverbend City Animal Control Code (Synthetic, Rule 8)

For demonstration purposes only, this synthetic municipal ordinance (fictionally located
within the fictional jurisdiction of "Nova Cascadia") provides:

"Within the fictional municipality of Riverbend City, no dog shall be left tethered
unsupervised for more than **one (1) hour** in any twenty-four (24) hour period, regardless
of tether length. This local rule is fictionally stricter than the general Nova Cascadia
Companion Animal Tethering Act and, under this synthetic scenario's fictional legal
hierarchy, the stricter local rule fictionally governs within Riverbend City."

## Purpose of This Document

This document intentionally conflicts with `companion_animals/synthetic_demo_contradictory_
source_a.md` (which describes a fictional 3-hour statewide/regional limit) to create a
realistic demonstration of how real law often works: a general regional/state-level rule
plus a stricter local/municipal rule that overrides it in a specific area. A well-built RAG
system should:

1. Retrieve both fictional sources when relevant.
2. Explicitly explain that they differ (a 3-hour general fictional rule vs. a 1-hour
   fictional local rule in a specific fictional city) rather than silently reporting only
   one.
3. Never present either number as reflecting real law anywhere.
