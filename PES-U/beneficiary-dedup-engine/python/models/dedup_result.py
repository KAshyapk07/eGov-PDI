"""
models/dedup_result.py   <->   lib/src/models/dedup_result.dart

The result of scoring one candidate pair.

Verdict is one of: "DUPLICATE", "REVIEW", "CLEAR".
feature_scores carries every individual algorithm score for transparency and
for the in-app warning UX ("matched on: name 0.94, dob 1.0, gps 0.97").

Dart port note: class with final fields; verdict as a String or a Dart enum.
feature_scores -> Map<String,double>. flags -> List<String>.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# Verdict constants — mirror as an enum in Dart.
DUPLICATE = "DUPLICATE"
REVIEW = "REVIEW"
CLEAR = "CLEAR"


@dataclass
class DedupResult:
    id_a: str
    id_b: str
    score: float
    verdict: str
    feature_scores: Dict[str, float] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)

    def is_duplicate(self) -> bool:
        return self.verdict == DUPLICATE

    def needs_review(self) -> bool:
        return self.verdict == REVIEW

    def is_possible_sibling(self) -> bool:
        return "POSSIBLE_SIBLING" in self.flags

    def top_signals(self, k: int = 3):
        """Highest-scoring features — drives the warning UX explanation."""
        items = sorted(self.feature_scores.items(), key=lambda kv: kv[1], reverse=True)
        return items[:k]
