"""Deterministic evidence registry for a single merge run (FR-B-2 / NFR-B-1).

:class:`EvidenceRegistry` is the sole authority on which evidence IDs belong to
the current run and how they map back to their :class:`NewsRecord`
(INV-B-3). It is deliberately run-scoped and stateless across runs: a fresh
``run_id`` is generated per instance, so IDs never collide across runs
(NFR-B-2).
"""

from __future__ import annotations

import uuid

from .schemas import NewsRecord


class EvidenceRegistry:
    """Issues, registers and resolves evidence IDs for one merge run."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id if run_id is not None else uuid.uuid4().hex[:8]
        self._records: dict[str, NewsRecord] = {}
        self._issued: set[str] = set()
        self._seq: dict[str, int] = {}

    @property
    def issued_ids(self) -> set[str]:
        """Evidence IDs issued/registered during this run (authoritative set)."""
        return set(self._issued)

    def records(self) -> dict[str, NewsRecord]:
        """A snapshot of ``evidence_id -> NewsRecord`` for this run."""
        return dict(self._records)

    def issue(
        self,
        ticker: str,
        date: str,
        source: str,
        title: str,
        snippet: str = "",
        link: str = "",
        pub_date: str = "",
    ) -> NewsRecord:
        """Issue a new record with a run-unique ``ev-{run_id}-{ticker}-{seq}`` ID.

        The sequence is per-ticker and 0-based. If an ID would collide (e.g.
        after :meth:`register` injected a record), the sequence is advanced until
        unique, guaranteeing ``issued_ids`` uniqueness within the run.
        """
        seq = self._seq.get(ticker, 0)
        while True:
            evidence_id = f"ev-{self.run_id}-{ticker}-{seq}"
            if evidence_id not in self._records:
                break
            seq += 1
        self._seq[ticker] = seq + 1

        record = NewsRecord(
            evidence_id=evidence_id,
            ticker=ticker,
            date=date,
            source=source,
            title=title,
            snippet=snippet,
            link=link,
            pub_date=pub_date,
        )
        self._records[evidence_id] = record
        self._issued.add(evidence_id)
        return record

    def register(self, record: NewsRecord) -> NewsRecord:
        """Register a pre-built record (used by fixtures/tests)."""
        self._records[record.evidence_id] = record
        self._issued.add(record.evidence_id)
        return record

    def resolve(self, evidence_id: str) -> NewsRecord | None:
        """Return the authoritative record for ``evidence_id``, or ``None``."""
        return self._records.get(evidence_id)
