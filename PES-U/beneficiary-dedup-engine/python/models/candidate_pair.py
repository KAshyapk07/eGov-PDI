"""
models/candidate_pair.py   <->   lib/src/models/candidate_pair.dart

Data models: the canonical Beneficiary record and a CandidatePair produced by
blocking. Kept dependency-free so they port straight to Dart data classes.

Dart port note:
  - Beneficiary -> a class with final fields + a fromCsvRow factory.
  - normGiven/normFamily/normFather/normFull/dobYear are computed once in
    normalize() (Dart: a method that returns a new instance or sets late finals).
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date

from utils.string_utils import normalize_name, token_sort


@dataclass
class Beneficiary:
    """One flat individual record. Mirrors the dedup_test_records.csv schema."""
    individual_id: str
    given_name:    Optional[str] = None
    family_name:   Optional[str] = None
    father_name:   Optional[str] = None
    husband_name:  Optional[str] = None
    gender:        Optional[str] = None
    date_of_birth: Optional[date] = None
    boundary_code: Optional[str] = None
    locality_name: Optional[str] = None
    latitude:      Optional[float] = None
    longitude:     Optional[float] = None
    location_accuracy: Optional[float] = None
    mobile_number: Optional[str] = None
    cycle:         Optional[str] = None

    # Computed by normalize()
    norm_given:  str = field(default="", init=False)
    norm_family: str = field(default="", init=False)
    norm_father: str = field(default="", init=False)
    norm_full:   str = field(default="", init=False)
    dob_year:    Optional[int] = field(default=None, init=False)

    def normalize(self) -> "Beneficiary":
        """Populate all norm_* fields in place; returns self."""
        self.norm_given = normalize_name(self.given_name)
        self.norm_family = normalize_name(self.family_name)
        self.norm_father = normalize_name(self.father_name)
        raw_full = (self.norm_given + " " + self.norm_family).strip()
        self.norm_full = token_sort(raw_full)
        self.dob_year = self.date_of_birth.year if self.date_of_birth else None
        return self


@dataclass
class CandidatePair:
    """A pair of record indices surfaced by the blocking stage."""
    index_a: int
    index_b: int

    def normalized(self) -> "CandidatePair":
        """Ensure index_a < index_b for stable dedup of the pair set."""
        if self.index_a > self.index_b:
            return CandidatePair(self.index_b, self.index_a)
        return self

    def key(self) -> tuple:
        lo = min(self.index_a, self.index_b)
        hi = max(self.index_a, self.index_b)
        return (lo, hi)
