#!/usr/bin/env python3
"""Prompt pin for #1149 — Tier 2 takes mandatory references before sampling.

The old instructions drew 50% of sources and could skip a reference that
Tier 0 had already required to proceed. Selection order is now:

1. Every reference Tier 0 requires to proceed to Tier 2, every tier_3 and
   tier_4 source, and any other flagged reference. A reference selected by
   more than one of those rules is verified once.
2. A random draw from the remaining eligible tier_1 and tier_2 sources until
   the selection includes at least half of all bibliography references,
   rounding a fraction up. A tier_1 or tier_2 reference that passed Tier 0
   and is not flagged is not eligible. If the mandatory set already meets
   that half, verify the entire mandatory set. If too few eligible
   references remain, verify every remaining eligible reference and do not
   add an unflagged Tier 0 pass to fill the half.

Actual coverage is the number of distinct references a WebSearch check was
performed on, divided by all bibliography references. A selected reference
that was not checked adds nothing.

Worked cases, with the other references unflagged tier_1 or tier_2 passes
unless noted:

- Six Tier 0 referrals out of ten: 6 checks. Half of 10 is 5, so the
  mandatory set already meets the minimum.
- One of those referrals is also tier_3: still 6 checks, not 7.
- Semantic Scholar unavailable, 10 references, 3 of them tier_3 or tier_4:
  the outage is not a per-reference Tier 0 failure. Mandatory set is 3,
  then 2 draws from the 7 eligible sources, 5 checks in total.

The ethics reviewer keeps its own minimum of at least 50% of all cited
references. This file pins the prompt text. It does not sample.

Run:
    PYTHONPATH=. python -m pytest scripts/test_tier2_sampling_prompt_sync.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT = REPO_ROOT / "deep-research" / "agents" / "source_verification_agent.md"
PROTOCOL = (
    REPO_ROOT / "deep-research" / "references" / "semantic_scholar_api_protocol.md"
)
QUALITY = (
    REPO_ROOT / "deep-research" / "references" / "cross_agent_quality_definitions.md"
)

MANDATORY = (
    "First include every reference that Tier 0 requires to proceed to Tier 2 "
    "and every tier_3 and tier_4 source."
)
DRAW = (
    "Then randomly select from the remaining eligible tier_1 and tier_2 "
    "sources until the selection includes at least half of all bibliography "
    "references, rounding a fraction up."
)
COVERAGE = (
    "Actual coverage is the number of distinct references a WebSearch check "
    "was performed on, divided by all bibliography references."
)


def _between(text: str, start: str, end: str) -> str:
    start_at = text.index(start)
    end_at = text.index(end, start_at + len(start))
    return text[start_at:end_at]


def _tier2_section() -> str:
    return _between(
        AGENT.read_text(encoding="utf-8"),
        "#### Tier 2:",
        "#### Red Flags",
    )


def test_tier2_includes_mandatory_references_before_the_sample() -> None:
    """Tier 0 referrals and tier_3/tier_4 sources come before the random draw."""
    section = _tier2_section()
    assert MANDATORY in section
    assert section.startswith("#### Tier 2: WebSearch Spot-Check\n")
    assert "(50% coverage)" not in section
    assert "Randomly select 50% of sources" not in section
    assert "Priority sampling" not in section
    assert "Verify each selected reference once, including when both rules select it." in section
    assert DRAW in section
    assert section.index(MANDATORY) < section.index(DRAW)
    assert "is not eligible and skips Tier 2" in section
    assert "verify the entire mandatory set" in section
    assert "do not add an unflagged Tier 0 pass" in section
    assert "no per-reference Tier 0 failure" in section
    assert COVERAGE in section
    assert "adds nothing to actual coverage" in section
    assert section.index(DRAW) < section.index("- Search:")
    assert section.index("- Search:") < section.index("- Verify:")
    assert '"{exact title}" {first author last name} {year}' in section


def test_protocol_pins_the_same_mandatory_set_and_denominator() -> None:
    """The Tier 2 table cell and the execution-order paragraph match the agent."""
    protocol = PROTOCOL.read_text(encoding="utf-8")
    row = next(line for line in protocol.splitlines() if line.startswith("| Tier 2 |"))
    assert (
        "Every reference Tier 0 requires to proceed to Tier 2 and every "
        "tier_3 and tier_4 source"
    ) in row
    assert "50% of sources" not in row
    assert "remaining eligible tier_1 and tier_2 sources" in row
    assert "at least half of all bibliography references, rounding a fraction up" in row

    paragraph = next(
        line for line in protocol.splitlines() if line.startswith("**Execution order**:")
    )
    assert "Tier 0 first (batch, 1 req/sec)." in paragraph
    assert "tier_3 or tier_4" in paragraph
    assert "A tier_1 or tier_2 pass is not eligible" in paragraph
    assert (
        "References that FAIL Tier 0 proceed to Tier 1 + Tier 2 for manual investigation."
        in paragraph
    )
    assert COVERAGE in paragraph
    assert paragraph.index("Tier 0 first") < paragraph.index("not eligible")
    assert paragraph.index("not eligible") < paragraph.index("References that FAIL Tier 0")


def test_quality_definition_keeps_the_ethics_minimum_separate() -> None:
    """One row: source-verifier denominator, ethics reviewer's own 50% minimum."""
    row = next(
        line
        for line in QUALITY.read_text(encoding="utf-8").splitlines()
        if line.startswith("| **Verification Threshold** |")
    )
    assert row.endswith("| source_verification_agent, ethics_review_agent |")
    assert "100% DOI check" in row
    assert (
        "every reference Tier 0 requires to proceed to Tier 2 and every "
        "tier_3 and tier_4 source"
    ) in row
    assert "rounding a fraction up" in row
    assert COVERAGE in row
    assert row.count("at least 50% of all cited references") == 1


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
