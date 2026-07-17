from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple

ALLOWED_STATUSES = frozenset(("pass", "noop", "blocked", "failed"))
STAGE_IDS = tuple("N%d" % number for number in range(1, 10))
SIA_DISPOSITIONS = frozenset(("same", "revised", "stale", "conflict", "withdrawn"))
VALID_LIFECYCLES = SIA_DISPOSITIONS
CANONICAL_GRAPH_REF = "cps-memory-lifecycle-and-honcho-anchor/C2@ee8cb7cbd851ff2eee40b0f2556be5133fc7a2cd"
MAX_BUDGET_ENVELOPE_AGE_SECONDS = 300
MAX_BUDGET_AGE_RECEIPT_SECONDS = 86400
MAX_BUDGET_COUNTER = (1 << 63) - 1


@dataclass(frozen=True)
class PushedShaEvent:
    event_id: str
    pushed_sha: str
    source_ref: str
    source_revision: str
    content_hash: str
    lifecycle: str
    graph_ref: str
    prior_ref: Optional[str] = None
    attempt: int = 1
    first_anchor_initialization: bool = False


@dataclass(frozen=True)
class SiaComparison:
    disposition: str
    prior_ref: Optional[str] = None


@dataclass(frozen=True)
class BudgetDecision:
    schema: str
    version: int
    budget_source_ref: str
    token_estimate: Optional[int]
    token_budget_remaining_before: Optional[int]
    budget_age_seconds: Optional[int]
    actual_token_usage: Optional[int]
    context_remaining_pct: Any
    decision: str
    reason: str
    measurement_status: str

    def receipt_fields(self) -> Mapping[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "budget_source_ref": self.budget_source_ref,
            "token_estimate": self.token_estimate,
            "token_budget_remaining_before": self.token_budget_remaining_before,
            "budget_age_seconds": self.budget_age_seconds,
            "actual_token_usage": self.actual_token_usage,
            "context_remaining_pct": self.context_remaining_pct,
            "decision": self.decision,
            "reason": self.reason,
            "measurement_status": self.measurement_status,
        }


@dataclass(frozen=True)
class StageReceipt:
    event_id: str
    graph_ref: str
    stage_id: str
    attempt: int
    status: str
    reason: str
    refs: Mapping[str, Any] = field(default_factory=dict)
    depends_on: Tuple[str, ...] = ()


@dataclass(frozen=True)
class StageResult:
    receipts: Tuple[StageReceipt, ...]
    closure_candidate: bool


class StageAdapters(Protocol):
    writer_session_id: str
    readback_session_id: str

    def confirm_remote(self, event: PushedShaEvent) -> bool: ...
    def is_duplicate(self, event: PushedShaEvent) -> bool: ...
    def within_budget(self, event: PushedShaEvent) -> BudgetDecision: ...
    def import_source(self, event: PushedShaEvent) -> str: ...
    def read_source(self, import_ref: str) -> Mapping[str, Any]: ...
    def compare(self, event: PushedShaEvent, source: Mapping[str, Any]) -> SiaComparison: ...
    def deactivate(self, prior_ref: str, event: PushedShaEvent) -> bool: ...
    def claim_first_initialization(self, event: PushedShaEvent) -> bool: ...
    def write(
        self,
        event: PushedShaEvent,
        source: Mapping[str, Any],
        comparison: SiaComparison,
    ) -> str: ...
    def readback(self, conclusion_ref: str) -> Mapping[str, Any]: ...
    def persist_stage_receipt(self, receipt: StageReceipt) -> None: ...
    def reload_stage_receipts(self, event: PushedShaEvent) -> Sequence[StageReceipt]: ...


class HonchoAnchorPort(Protocol):
    identity: str

    def write_anchor(self, anchor: Mapping[str, str]) -> str: ...
    def read_anchor(self, anchor_ref: str) -> Mapping[str, str]: ...
    def deactivate_anchor(self, anchor_ref: str, superseded_by: str) -> bool: ...


class ProductionStageAdapters:
    def __init__(
        self,
        repo: Path,
        database_path: Path,
        writer: HonchoAnchorPort,
        reader: HonchoAnchorPort,
        budget_decision: BudgetDecision,
    ):
        self.repo = Path(repo).resolve()
        self.database_path = Path(database_path)
        self.writer = writer
        self.reader = reader
        self.budget_decision = budget_decision
        self.writer_session_id = writer.identity
        self.readback_session_id = reader.identity
        if self.writer_session_id == self.readback_session_id:
            raise ValueError("Honcho writer and reader contexts must be distinct")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_store()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize_store(self):
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS gbrain_sources (
                    import_ref TEXT PRIMARY KEY, source_ref TEXT NOT NULL,
                    source_revision TEXT NOT NULL, content_hash TEXT NOT NULL,
                    graph_ref TEXT NOT NULL, pushed_sha TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS active_anchors (
                    anchor_ref TEXT PRIMARY KEY, anchor_key TEXT NOT NULL,
                    source_ref TEXT NOT NULL, source_revision TEXT NOT NULL,
                    content_hash TEXT NOT NULL, graph_ref TEXT NOT NULL,
                    active INTEGER NOT NULL, superseded_by TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_anchor
                    ON active_anchors(source_ref) WHERE active=1;
                CREATE TABLE IF NOT EXISTS anchor_supersessions (
                    prior_ref TEXT NOT NULL, superseded_by TEXT NOT NULL,
                    event_id TEXT NOT NULL, graph_ref TEXT NOT NULL,
                    PRIMARY KEY(prior_ref, superseded_by)
                );
                CREATE TABLE IF NOT EXISTS initialization_claims (
                    source_ref TEXT PRIMARY KEY, anchor_key TEXT NOT NULL UNIQUE,
                    event_id TEXT NOT NULL, graph_ref TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stage_receipts (
                    event_id TEXT NOT NULL, stage_id TEXT NOT NULL, attempt INTEGER NOT NULL,
                    graph_ref TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL,
                    refs_json TEXT NOT NULL, depends_json TEXT NOT NULL,
                    PRIMARY KEY(event_id, stage_id, attempt)
                );
            """)

    def _git(self, *args, text=True):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True,
            text=text, stdin=subprocess.DEVNULL,
        ).stdout

    def confirm_remote(self, event):
        refs = self._git("for-each-ref", "--format=%(refname)", "refs/remotes/origin/").splitlines()
        for ref in refs:
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", event.pushed_sha, ref],
                cwd=self.repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                return True
        return False

    def is_duplicate(self, event):
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM stage_receipts WHERE event_id=? AND attempt=? AND stage_id='N9'",
                (event.event_id, event.attempt),
            ).fetchone() is not None

    def within_budget(self, event):
        return self.budget_decision

    def import_source(self, event):
        blob = self._git("show", "%s:%s" % (event.pushed_sha, event.source_ref), text=False)
        content_hash = hashlib.sha256(blob).hexdigest()
        if content_hash != event.content_hash:
            raise ValueError("canonical blob content hash mismatch")
        import_ref = "gbrain:%s:%s:%s" % (
            event.pushed_sha,
            source_ref_digest(event.source_ref),
            content_hash,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO gbrain_sources VALUES (?, ?, ?, ?, ?, ?)",
                (import_ref, event.source_ref, event.source_revision, content_hash, event.graph_ref, event.pushed_sha),
            )
        return import_ref

    def read_source(self, import_ref):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT source_ref, source_revision, content_hash, graph_ref, pushed_sha "
                "FROM gbrain_sources WHERE import_ref=?", (import_ref,),
            ).fetchone()
        if row is None:
            raise KeyError(import_ref)
        return dict(zip(("source_ref", "source_revision", "content_hash", "graph_ref", "pushed_sha"), row))

    def compare(self, event, source):
        with self._connect() as connection:
            prior = connection.execute(
                "SELECT anchor_ref, source_revision, content_hash FROM active_anchors "
                "WHERE source_ref=? AND active=1", (event.source_ref,),
            ).fetchone()
        if event.lifecycle == "withdrawn":
            return SiaComparison("withdrawn", prior[0] if prior else event.prior_ref)
        if prior and prior[1] == event.source_revision:
            disposition = "same" if prior[2] == event.content_hash else "conflict"
        elif event.lifecycle in SIA_DISPOSITIONS:
            disposition = event.lifecycle
        else:
            disposition = "stale"
        return SiaComparison(disposition, prior[0] if prior else event.prior_ref)

    def deactivate(self, prior_ref, event):
        superseded_by = "%s@%s" % (event.source_ref, event.source_revision)
        if not self.writer.deactivate_anchor(prior_ref, superseded_by):
            return False
        with self._connect() as connection:
            connection.execute(
                "UPDATE active_anchors SET active=0, superseded_by=? WHERE anchor_ref=?",
                (superseded_by, prior_ref),
            )
            connection.execute(
                "INSERT OR REPLACE INTO anchor_supersessions VALUES (?, ?, ?, ?)",
                (prior_ref, superseded_by, event.event_id, event.graph_ref),
            )
        return True

    def claim_first_initialization(self, event):
        anchor_key = "%s@%s" % (event.source_ref, event.source_revision)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            historical = connection.execute(
                "SELECT 1 FROM active_anchors WHERE source_ref=? OR anchor_key=? LIMIT 1",
                (event.source_ref, anchor_key),
            ).fetchone()
            supersession = connection.execute(
                "SELECT 1 FROM anchor_supersessions WHERE (superseded_by=? OR superseded_by LIKE ? ESCAPE '\\') OR prior_ref IN "
                "(SELECT anchor_ref FROM active_anchors WHERE source_ref=?) LIMIT 1",
                (anchor_key, event.source_ref.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "@%", event.source_ref),
            ).fetchone()
            claimed = connection.execute(
                "SELECT 1 FROM initialization_claims WHERE source_ref=? OR anchor_key=? LIMIT 1",
                (event.source_ref, anchor_key),
            ).fetchone()
            if historical or supersession or claimed:
                connection.rollback()
                return False
            connection.execute(
                "INSERT INTO initialization_claims VALUES (?, ?, ?, ?)",
                (event.source_ref, anchor_key, event.event_id, event.graph_ref),
            )
            connection.commit()
            return True
        finally:
            connection.close()

    def _anchor(self, event):
        return {
            "anchor_key": "%s@%s" % (event.source_ref, event.source_revision),
            "source_ref": event.source_ref,
            "source_revision": event.source_revision,
            "content_hash": event.content_hash,
            "graph_ref": event.graph_ref,
            "lifecycle": event.lifecycle,
        }

    def write(self, event, source, comparison):
        anchor = self._anchor(event)
        anchor_ref = self.writer.write_anchor(anchor)
        if not isinstance(anchor_ref, str) or not anchor_ref.strip():
            raise RuntimeError("Honcho returned no real conclusion ID")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO active_anchors VALUES (?, ?, ?, ?, ?, ?, 1, NULL)",
                (anchor_ref, anchor["anchor_key"], event.source_ref, event.source_revision,
                 event.content_hash, event.graph_ref),
            )
        return anchor_ref

    def readback(self, conclusion_ref):
        expected = None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT anchor_key, source_ref, source_revision, content_hash, graph_ref, 'revised' "
                "FROM active_anchors WHERE anchor_ref=? AND active=1", (conclusion_ref,),
            ).fetchone()
        if row:
            expected = dict(zip(("anchor_key", "source_ref", "source_revision", "content_hash", "graph_ref", "lifecycle"), row))
        actual = dict(self.reader.read_anchor(conclusion_ref))
        if expected is None or actual != expected:
            raise ValueError("independent Honcho readback mismatch")
        return actual

    def persist_stage_receipt(self, receipt):
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO stage_receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (receipt.event_id, receipt.stage_id, receipt.attempt, receipt.graph_ref,
                 receipt.status, receipt.reason, json.dumps(dict(receipt.refs), sort_keys=True),
                 json.dumps(list(receipt.depends_on))),
            )

    def reload_stage_receipts(self, event):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id, graph_ref, stage_id, attempt, status, reason, refs_json, depends_json "
                "FROM stage_receipts WHERE event_id=? AND attempt=? ORDER BY CAST(SUBSTR(stage_id, 2) AS INTEGER)",
                (event.event_id, event.attempt),
            ).fetchall()
        return tuple(StageReceipt(
            event_id=row[0], graph_ref=row[1], stage_id=row[2], attempt=row[3],
            status=row[4], reason=row[5], refs=json.loads(row[6]),
            depends_on=tuple(json.loads(row[7])),
        ) for row in rows)


def _receipt(
    event: PushedShaEvent,
    stage_id: str,
    status: str,
    reason: str,
    refs: Optional[Mapping[str, Any]] = None,
    depends_on: Tuple[str, ...] = (),
) -> StageReceipt:
    if status not in ALLOWED_STATUSES:
        raise ValueError("invalid receipt status")
    return StageReceipt(
        event_id=event.event_id,
        graph_ref=event.graph_ref,
        stage_id=stage_id,
        attempt=event.attempt,
        status=status,
        reason=reason,
        refs={key: value for key, value in (refs or {}).items() if key != "graph_ref"},
        depends_on=depends_on,
    )


def source_ref_digest(source_ref: str) -> str:
    return hashlib.sha256(source_ref.encode("utf-8")).hexdigest()


def _nonnegative_int(value: Any, upper_bound: int = MAX_BUDGET_COUNTER) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= upper_bound else None


def _bounded_context_pct(value: Any) -> Any:
    return value if value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100) else None


def _bounded_budget_source_ref(value: Any) -> str:
    return value if isinstance(value, str) and value.strip() and len(value) <= 256 and "\n" not in value and "\r" not in value else "unavailable"


def build_budget_decision(
    budget_source_ref: Any,
    token_estimate: Any,
    token_budget_remaining: Any,
    context_remaining_pct: Any = None,
    budget_age_seconds: Any = None,
    actual_token_usage: Any = None,
) -> BudgetDecision:
    source_ref = _bounded_budget_source_ref(budget_source_ref)
    estimate = _nonnegative_int(token_estimate)
    remaining = _nonnegative_int(token_budget_remaining)
    age = _nonnegative_int(budget_age_seconds, MAX_BUDGET_AGE_RECEIPT_SECONDS)
    actual_usage = _nonnegative_int(actual_token_usage)
    measurement_status = "measured" if actual_usage is not None else "unavailable"
    if source_ref == "unavailable" or estimate is None or remaining is None or age is None:
        decision, reason = "blocked", "budget-check-unavailable"
    elif age > MAX_BUDGET_ENVELOPE_AGE_SECONDS:
        decision, reason = "blocked", "budget-envelope-stale"
    elif estimate > remaining:
        decision, reason = "blocked", "budget-breached"
    else:
        decision, reason = "admitted", "budget-admitted"
    return BudgetDecision(
        schema="harness.cps_budget_decision_receipt.v1",
        version=1,
        budget_source_ref=source_ref,
        token_estimate=estimate,
        token_budget_remaining_before=remaining,
        budget_age_seconds=age,
        actual_token_usage=actual_usage,
        context_remaining_pct=_bounded_context_pct(context_remaining_pct),
        decision=decision,
        reason=reason,
        measurement_status=measurement_status,
    )


def _validated_budget_decision(value: Any) -> BudgetDecision:
    if not isinstance(value, BudgetDecision):
        return build_budget_decision("unavailable", None, None)
    expected = build_budget_decision(
        value.budget_source_ref,
        value.token_estimate,
        value.token_budget_remaining_before,
        value.context_remaining_pct,
        value.budget_age_seconds,
        value.actual_token_usage,
    )
    return value if value == expected else build_budget_decision(
        value.budget_source_ref,
        None,
        None,
        value.context_remaining_pct,
        value.budget_age_seconds,
        value.actual_token_usage,
    )


def _valid_event(event: PushedShaEvent) -> bool:
    required = (
        event.event_id,
        event.pushed_sha,
        event.source_ref,
        event.source_revision,
        event.content_hash,
    )
    try:
        prefix, event_sha, digest = event.event_id.rsplit(":", 2)
    except ValueError:
        return False
    identity_matches = (
        prefix.startswith("push:")
        and event_sha == event.pushed_sha
        and digest == source_ref_digest(event.source_ref)
    )
    return identity_matches and all(isinstance(value, str) and bool(value.strip()) for value in required) and (
        event.lifecycle in VALID_LIFECYCLES and event.attempt > 0
        and isinstance(event.first_anchor_initialization, bool)
    )


def _source_matches_event(source: Mapping[str, Any], event: PushedShaEvent) -> bool:
    return all(
        source.get(key) == expected
        for key, expected in (
            ("source_ref", event.source_ref),
            ("source_revision", event.source_revision),
            ("content_hash", event.content_hash),
            ("graph_ref", event.graph_ref),
        )
    )


def evaluate_closure(receipts: Sequence[StageReceipt], event: PushedShaEvent) -> bool:
    identities = [(receipt.event_id, receipt.stage_id, receipt.attempt) for receipt in receipts]
    expected = [(event.event_id, stage_id, event.attempt) for stage_id in STAGE_IDS]
    if identities != expected:
        return False
    dependencies = [()] + [(STAGE_IDS[index - 1],) for index in range(1, len(STAGE_IDS))]
    return all(
        receipt.graph_ref == event.graph_ref
        and receipt.depends_on == dependencies[index]
        and receipt.status in ("pass", "noop")
        for index, receipt in enumerate(receipts)
    )


def _normalize_disposition(disposition: Any) -> Optional[str]:
    if not isinstance(disposition, str):
        return None
    normalized = disposition.strip().lower()
    return normalized if normalized in SIA_DISPOSITIONS else None


def run_stage_core(event: PushedShaEvent, adapters: StageAdapters) -> StageResult:
    if event.graph_ref != CANONICAL_GRAPH_REF:
        return StageResult((), False)

    receipts = []

    def add(stage_id: str, status: str, reason: str, refs=None) -> None:
        dependency = (receipts[-1].stage_id,) if receipts else ()
        receipt = _receipt(event, stage_id, status, reason, refs, dependency)
        receipts.append(receipt)
        adapters.persist_stage_receipt(receipt)

    def stop() -> StageResult:
        return StageResult(tuple(receipts), False)

    def finalize() -> StageResult:
        try:
            durable_prefix = tuple(adapters.reload_stage_receipts(event))
        except Exception:
            return StageResult((), False)
        if durable_prefix != tuple(receipts):
            return StageResult(durable_prefix, False)
        add("N9", "pass", "complete-durable-receipts-eligible")
        try:
            durable = tuple(adapters.reload_stage_receipts(event))
        except Exception:
            return StageResult((), False)
        return StageResult(durable, evaluate_closure(durable, event))

    try:
        remote_confirmed = adapters.confirm_remote(event)
    except Exception:
        add("N1", "blocked", "remote-confirm-unavailable")
        return stop()
    if not remote_confirmed:
        add("N1", "blocked", "pushed-sha-not-remote-confirmed")
        return stop()
    add("N1", "pass", "pushed-sha-remote-confirmed", {"pushed_sha": event.pushed_sha})

    if not _valid_event(event):
        add("N2", "blocked", "malformed-source-event")
        return stop()
    try:
        duplicate = adapters.is_duplicate(event)
    except Exception:
        add("N2", "blocked", "dedupe-filter-unavailable")
        return stop()
    if duplicate:
        add("N2", "noop", "duplicate-pushed-sha")
        return stop()
    add("N2", "pass", "event-admitted")

    try:
        budget_decision = _validated_budget_decision(adapters.within_budget(event))
    except Exception:
        budget_decision = build_budget_decision("unavailable", None, None)
    if budget_decision.decision != "admitted":
        add("N3", "blocked", budget_decision.reason, budget_decision.receipt_fields())
        return stop()
    add("N3", "pass", "budget-admitted", budget_decision.receipt_fields())

    try:
        import_ref = adapters.import_source(event)
        source = adapters.read_source(import_ref)
    except Exception:
        add("N4", "blocked", "gbrain-import-read-unavailable")
        return stop()
    if not import_ref or not _source_matches_event(source, event):
        add("N4", "blocked", "gbrain-source-mismatch")
        return stop()
    add("N4", "pass", "gbrain-source-read", {"import_ref": import_ref})

    try:
        comparison = adapters.compare(event, source)
    except Exception:
        add("N5", "blocked", "sia-compare-unavailable")
        return stop()
    disposition = _normalize_disposition(comparison.disposition)
    if disposition is None:
        add("N5", "blocked", "sia-disposition-ineligible")
        return stop()
    comparison = SiaComparison(disposition, comparison.prior_ref)
    add("N5", "pass", "sia-comparison-complete", {"disposition": disposition})

    prior_ref = comparison.prior_ref or event.prior_ref
    if event.first_anchor_initialization and prior_ref:
        add("N6", "blocked", "initialization-prohibits-prior-ref")
        return stop()

    if disposition == "same":
        add("N6", "noop", "same-needs-no-deactivation")
        add("N7", "noop", "same-excludes-write")
        add("N8", "noop", "no-write-to-read-back")
        return finalize()

    if disposition in ("stale", "conflict"):
        add("N6", "blocked", "%s-prohibits-write" % disposition)
        return stop()

    if event.first_anchor_initialization:
        if disposition != "revised":
            add("N6", "blocked", "initialization-requires-revised-disposition")
            return stop()
        try:
            admitted = adapters.claim_first_initialization(event)
        except Exception:
            admitted = False
        if not admitted:
            add("N6", "blocked", "first-anchor-initialization-ineligible")
            return stop()
        add("N6", "pass", "first-anchor-initialization-admitted")
    elif disposition == "revised" and not prior_ref:
        add("N6", "blocked", "revised-requires-prior-deactivation")
        return stop()

    if prior_ref and not event.first_anchor_initialization:
        try:
            deactivated = adapters.deactivate(prior_ref, event)
        except Exception:
            deactivated = False
        if not deactivated:
            add("N6", "blocked", "prior-deactivation-failed", {"prior_ref": prior_ref})
            return stop()
        add("N6", "pass", "prior-deactivated", {"prior_ref": prior_ref})
    elif not event.first_anchor_initialization:
        add("N6", "noop", "no-prior-active-conclusion")

    if disposition == "withdrawn":
        add("N7", "noop", "withdrawn-excludes-active-write")
        add("N8", "noop", "no-write-to-read-back")
        return finalize()

    try:
        conclusion_ref = adapters.write(event, source, comparison)
    except Exception:
        add("N7", "failed", "honcho-write-failed")
        return stop()
    if not conclusion_ref:
        add("N7", "failed", "honcho-write-missing-ref")
        return stop()
    add("N7", "pass", "honcho-write-complete", {"conclusion_ref": conclusion_ref})

    if adapters.writer_session_id == adapters.readback_session_id:
        add("N8", "failed", "readback-session-not-independent")
        return stop()
    try:
        readback = adapters.readback(conclusion_ref)
    except Exception:
        add("N8", "failed", "honcho-readback-failed")
        return stop()
    if not _source_matches_event(readback, event):
        add("N8", "failed", "honcho-readback-mismatch")
        return stop()
    add("N8", "pass", "honcho-readback-matched", {"conclusion_ref": conclusion_ref})

    return finalize()
