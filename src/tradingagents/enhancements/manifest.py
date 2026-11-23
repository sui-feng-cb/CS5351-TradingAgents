"""Versioned run manifest and read-only local query (FR-C, NFR-C, ADR-001).

Every analysis execution attempt writes one ``run_manifest.json`` into its own
run directory under the results root. A read-only scan of the results root can
then find runs by ticker and/or date. Unknowns are explicit (``null``), never
guessed; the query never modifies or deletes a report.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1

# Frozen v1 top-level field whitelist (docs/architecture/interface-contracts.md).
REQUIRED_FIELDS = (
    "schema_version",
    "run_id",
    "ticker",
    "asset_type",
    "trade_date",
    "as_of",
    "started_at",
    "finished_at",
    "code_version",
    "analysts",
    "models",
    "configured_data_vendors",
    "status",
    "reports",
    "error",
    "unknown_fields",
)

ALLOWED_STATUS = ("running", "succeeded", "failed")

# The report keys a manifest may carry, each a results-root-relative path or null.
_REPORT_KEYS = ("complete_report_md", "complete_report_html")

MANIFEST_FILENAME = "run_manifest.json"

# A run attempt lives at <ticker>/<YYYY-MM-DD>/runs/<UUID>/ under the results root.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class ManifestError(ValueError):
    """Raised when a manifest violates the v1 contract."""


def _parse_date(value: object, field_name: str) -> None:
    """Require a canonical ``YYYY-MM-DD`` calendar date."""

    if not isinstance(value, str):
        raise ManifestError(f"{field_name} must be a YYYY-MM-DD string, got {value!r}")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ManifestError(f"{field_name} is not a valid date: {value!r}") from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise ManifestError(f"{field_name} is not a canonical date: {value!r}")


def _parse_utc(value: object, field_name: str) -> None:
    """Require a timezone-aware ISO-8601 timestamp (``...Z`` or an offset)."""

    if not isinstance(value, str):
        raise ManifestError(f"{field_name} must be an ISO-8601 string, got {value!r}")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ManifestError(f"{field_name} is not ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ManifestError(f"{field_name} must be timezone-aware: {value!r}")


def _validate_reports(reports: object) -> None:
    if not isinstance(reports, dict):
        raise ManifestError("reports must be an object mapping report keys to paths or null")
    extra = set(reports) - set(_REPORT_KEYS)
    if extra:
        raise ManifestError(f"reports has unknown keys: {sorted(extra)}")
    for key, value in reports.items():
        if value is None:
            continue
        if not isinstance(value, str):
            raise ManifestError(f"reports[{key!r}] must be a string path or null, got {value!r}")
        # Report references are results-root-relative; an absolute path is invalid.
        if Path(value).is_absolute():
            raise ManifestError(f"reports[{key!r}] must be relative to the results root: {value!r}")


def _validate_error(error: object) -> None:
    if error is None:
        return
    if not isinstance(error, dict):
        raise ManifestError("error must be an object or null")
    extra = set(error) - {"code", "message"}
    if extra:
        raise ManifestError(f"error has unknown keys: {sorted(extra)}")
    for key in ("code", "message"):
        if not isinstance(error.get(key), str):
            raise ManifestError(f"error[{key!r}] must be a string")


def _validate_models(models: object) -> None:
    if models is None:
        # Provider/model metadata may be genuinely unknown; that is an explicit null.
        return
    if not isinstance(models, dict):
        raise ManifestError("models must be an object")
    for tier, spec in models.items():
        if not isinstance(spec, dict):
            raise ManifestError(f"models[{tier!r}] must be an object")
        # Keep only provider/model: any extra key could carry a secret or a
        # credential-bearing endpoint and must not be serialized.
        extra = set(spec) - {"provider", "model"}
        if extra:
            raise ManifestError(f"models[{tier!r}] has unknown keys: {sorted(extra)}")
        for key in ("provider", "model"):
            if not isinstance(spec.get(key), str):
                raise ManifestError(f"models[{tier!r}][{key!r}] must be a string")


def _validate_vendors(vendors: object) -> None:
    if not isinstance(vendors, dict):
        raise ManifestError("configured_data_vendors must be an object")
    for key, value in vendors.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ManifestError("configured_data_vendors must map strings to strings")


def _validate_analysts(analysts: object) -> None:
    if not isinstance(analysts, list) or not all(isinstance(a, str) for a in analysts):
        raise ManifestError("analysts must be a list of strings")


@dataclass(frozen=True)
class ManifestRecord:
    """One run's manifest, as a validated or to-be-validated field mapping."""

    data: dict

    @classmethod
    def from_dict(cls, data: dict) -> ManifestRecord:
        """Build a record from a parsed mapping without validating yet.

        Structural validation happens in :func:`validate_manifest`, so a caller
        can persist only after it passes and a mutation surfaces as a clear error.
        """

        if not isinstance(data, dict):
            raise ManifestError(f"manifest must be a JSON object, got {type(data).__name__}")
        return cls(data=dict(data))

    @property
    def ticker(self) -> str:
        return self.data["ticker"]

    @property
    def trade_date(self) -> str:
        return self.data["trade_date"]

    @property
    def run_id(self) -> str:
        return self.data["run_id"]

    @property
    def status(self) -> str:
        return self.data["status"]

    @property
    def reports(self) -> dict:
        return self.data.get("reports") or {}


def validate_manifest(record: ManifestRecord) -> dict:
    """Validate a record against the v1 contract; return its canonical dict.

    Raises :class:`ManifestError` (a ``ValueError``) on the first violation.
    """

    data = record.data
    keys = set(data)
    missing = set(REQUIRED_FIELDS) - keys
    if missing:
        raise ManifestError(f"manifest is missing required fields: {sorted(missing)}")
    extra = keys - set(REQUIRED_FIELDS)
    if extra:
        raise ManifestError(f"manifest has unknown fields: {sorted(extra)}")

    version = data["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise ManifestError(
            f"unsupported schema_version: {version!r} (expected the integer {SCHEMA_VERSION})")

    run_id = data["run_id"]
    if not isinstance(run_id, str):
        raise ManifestError("run_id must be a UUID string")
    try:
        uuid.UUID(run_id)
    except (ValueError, TypeError) as exc:
        raise ManifestError(f"run_id is not a UUID: {run_id!r}") from exc

    for key in ("ticker", "asset_type"):
        if not isinstance(data[key], str) or not data[key]:
            raise ManifestError(f"{key} must be a non-empty string")

    # code_version is best-effort: the running code version may be unavailable.
    if data["code_version"] is not None and (
            not isinstance(data["code_version"], str) or not data["code_version"]):
        raise ManifestError("code_version must be a non-empty string or null")

    _parse_date(data["trade_date"], "trade_date")
    _parse_date(data["as_of"], "as_of")
    _parse_utc(data["started_at"], "started_at")
    if data["finished_at"] is not None:
        _parse_utc(data["finished_at"], "finished_at")

    if data["status"] not in ALLOWED_STATUS:
        raise ManifestError(f"status must be one of {ALLOWED_STATUS}, got {data['status']!r}")

    _validate_analysts(data["analysts"])
    _validate_models(data["models"])
    _validate_vendors(data["configured_data_vendors"])
    _validate_reports(data["reports"])
    _validate_error(data["error"])

    if not isinstance(data["unknown_fields"], list):
        raise ManifestError("unknown_fields must be a list")

    return data


def write_manifest(path: str | Path, record: ManifestRecord) -> Path:
    """Validate then atomically write ``record`` as UTF-8 JSON to ``path``.

    The bytes are written to a temporary file in the same directory and then
    renamed into place, so a crash never leaves a half-written manifest. Any
    validation or I/O failure propagates to the caller.
    """

    data = validate_manifest(record)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    return target


@dataclass(frozen=True)
class Match:
    """One matching run found by a query."""

    run_id: str
    ticker: str
    trade_date: str
    status: str
    reports: dict
    manifest_path: Path


@dataclass
class QueryOutcome:
    """The matches a query found and the per-file warnings it raised."""

    matches: list[Match] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _within_root(path: Path, root: Path) -> bool:
    """True when ``path`` (symlinks resolved) is ``root`` or lives beneath it."""

    try:
        resolved = path.resolve()
        resolved_root = root.resolve()
    except (OSError, RuntimeError):
        return False
    return resolved == resolved_root or resolved_root in resolved.parents


def _check_report_paths(manifest_path: Path, root: Path, reports: dict,
                        warnings: list[str]) -> bool:
    """Warn about declared reports that escape the root or are missing.

    The manifest's own location is only inspected; report contents are never
    opened. Reports are resolved relative to the results root per the contract.
    Returns ``False`` when a declared report escapes the results root, so the
    caller drops that record entirely rather than returning it.
    """

    safe = True
    for key, value in reports.items():
        if value is None:
            continue
        candidate = Path(value)
        if candidate.is_absolute():
            # Keep the location and a fixed reason; never echo the path value.
            warnings.append(
                f"{manifest_path}: unsafe report path ({key}), must be relative to the "
                "results root")
            safe = False
            continue
        resolved = root / candidate
        if not _within_root(resolved, root):
            warnings.append(
                f"{manifest_path}: unsafe report path ({key}), escapes the results root")
            safe = False
            continue
        if not resolved.exists():
            warnings.append(f"{manifest_path}: declared report ({key}) is missing")
    return safe


def _load_one(manifest_path: Path, root: Path, warnings: list[str]) -> Match | None:
    """Parse and validate one manifest file; return a Match or None (with a warning)."""

    if not _within_root(manifest_path, root):
        warnings.append(f"{manifest_path}: manifest path escapes the results root")
        return None
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        # Keep the file and a fixed reason; never echo the file's bytes.
        warnings.append(f"{manifest_path}: not valid UTF-8, skipped")
        return None
    except ValueError:
        # JSONDecodeError and the int-conversion ValueError (huge integer) both
        # land here; report a fixed reason, never the parser/exception text.
        warnings.append(f"{manifest_path}: unreadable manifest, skipped")
        return None
    except OSError:
        warnings.append(f"{manifest_path}: unreadable manifest, skipped")
        return None

    if not isinstance(raw, dict):
        warnings.append(f"{manifest_path}: invalid manifest, skipped")
        return None
    version = raw.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        # Fixed reason; never echo the raw schema_version value.
        warnings.append(f"{manifest_path}: unknown schema_version, skipped")
        return None

    try:
        record = ManifestRecord.from_dict(raw)
        validate_manifest(record)
    except ManifestError:
        # Fixed reason; the exception text could echo field values.
        warnings.append(f"{manifest_path}: invalid manifest, skipped")
        return None

    reports = record.reports
    if not _check_report_paths(manifest_path, root, reports, warnings):
        return None
    # A succeeded analysis whose report save failed is still a valid record; flag
    # it with a fixed warning (no exception text) and keep it in the matches.
    error = record.data.get("error") if isinstance(record.data, dict) else None
    if isinstance(error, dict) and error.get("code") == "report_save_failed":
        warnings.append(f"{manifest_path}: report save failed for this run, kept")
    return Match(
        run_id=record.run_id,
        ticker=record.ticker,
        trade_date=record.trade_date,
        status=record.status,
        reports=dict(reports),
        manifest_path=manifest_path,
    )


def _iter_subdirs(directory: Path):
    """Yield real (non-symlink) subdirectories, skipping any unreadable branch.

    An ``OSError`` reading one directory is swallowed so the scan continues over
    other records. Symlinked directories are skipped: they may point outside the
    results root and are not genuine run structure.
    """

    try:
        entries = list(directory.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_symlink() or not entry.is_dir():
                continue
        except OSError:
            continue
        yield entry


def _is_real_calendar_date(name: str) -> bool:
    """True when ``name`` is a real ``YYYY-MM-DD`` calendar date (rejects 02-31)."""

    if not _DATE_RE.match(name):
        return False
    try:
        _parse_date(name, "date")
    except ManifestError:
        return False
    return True


def _warn_missing_run_manifests(root: Path, warnings: list[str]) -> None:
    """Warn once for each recognizable run dir that has no ``run_manifest.json``.

    A recognizable run dir is ``<root>/<ticker>/<YYYY-MM-DD>/runs/<UUID>/``.
    Unreadable branches and symlinked directories are skipped, the date must be a
    real calendar date, and unrelated directories are ignored. An existing (even
    corrupt) manifest is handled by the normal scan, so it is not re-warned here.
    """

    for ticker_dir in _iter_subdirs(root):
        for date_dir in _iter_subdirs(ticker_dir):
            if not _is_real_calendar_date(date_dir.name):
                continue
            try:
                if (date_dir / "runs").is_symlink():
                    continue
            except OSError:
                continue
            for attempt_dir in _iter_subdirs(date_dir / "runs"):
                if not _UUID_RE.match(attempt_dir.name):
                    continue
                try:
                    has_manifest = (attempt_dir / MANIFEST_FILENAME).exists()
                except OSError:
                    continue
                if not has_manifest:
                    warnings.append(
                        f"{attempt_dir / MANIFEST_FILENAME}: run manifest is missing")


def query_manifests(results_dir: str | Path, *, ticker: str | None = None,
                    date: str | None = None) -> QueryOutcome:
    """Read-only scan of ``results_dir`` for manifests, filtered by ticker and/or date.

    A bad JSON file, unknown schema version, invalid manifest, or out-of-root
    path contributes a warning and is skipped; the rest are returned unchanged.
    A declared-but-missing report warns but keeps its record. A recognizable run
    directory (``<ticker>/<date>/runs/<uuid>/``) with no manifest warns once.
    Null report paths are normal. No report is opened, modified or deleted.
    """

    root = Path(results_dir)
    outcome = QueryOutcome()
    if not root.exists():
        outcome.warnings.append(f"{root}: results directory does not exist")
        return outcome

    # Warn about recognizable run dirs that never wrote a manifest. Existing
    # (including corrupt) manifests are diagnosed by the scan below, not here.
    _warn_missing_run_manifests(root, outcome.warnings)

    for manifest_path in sorted(root.rglob(MANIFEST_FILENAME)):
        match = _load_one(manifest_path, root, outcome.warnings)
        if match is None:
            continue
        if ticker is not None and match.ticker != ticker:
            continue
        if date is not None and match.trade_date != date:
            continue
        outcome.matches.append(match)
    return outcome


# --------------------------------------------------------------------------- #
# Run-recording helpers used by the CLI. Only allowlisted metadata is read from
# the config so credentials, endpoints and the whole config never leak in.
# --------------------------------------------------------------------------- #

def new_run_id() -> str:
    """A fresh UUID4 string identifying one execution attempt."""

    return str(uuid.uuid4())


def utc_now_iso() -> str:
    """The current time as an ISO-8601 UTC string (``...Z``)."""

    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def attempt_manifest_path(results_root: str | Path, ticker: str, trade_date: str,
                          run_id: str) -> Path:
    """Where one attempt's manifest goes: a per-run-id directory under the root."""

    return Path(results_root) / ticker / trade_date / "runs" / run_id / MANIFEST_FILENAME


def _provider(config: dict, tier: str) -> str | None:
    """The provider of a model tier from the allowlisted config fields."""

    primary = config.get("llm_provider")
    if not primary:
        return None
    return (config.get(f"{tier}_think_provider") or primary).lower()


def _models_from_config(config: dict) -> dict | None:
    """Deep/quick provider+model from the config, or ``None`` when unknown.

    Only provider and model are copied; endpoints and keys are never read.
    """

    if not config.get("llm_provider"):
        return None
    return {
        "deep": {"provider": _provider(config, "deep"),
                 "model": config.get("deep_think_llm") or ""},
        "quick": {"provider": _provider(config, "quick"),
                  "model": config.get("quick_think_llm") or ""},
    }


def _vendor_routing():
    """The routing tables (categories, tool names, per-tool vendors).

    Imported lazily so the read-only query path never loads the vendor
    implementation modules; only the write path builds vendor metadata.
    """

    from tradingagents.dataflows.router import TOOLS_CATEGORIES, VENDOR_METHODS

    return TOOLS_CATEGORIES, VENDOR_METHODS


def _filter_chain(value: str, allowed: set[str]) -> str | None:
    """Keep only known provider identifiers from a comma-separated chain.

    Preserves the configured order (a legitimate fallback chain such as
    ``sec_edgar,yfinance``). The ``default`` sentinel is kept as-is. Any entry
    that is not a known provider (a credential URL, a typo, an unknown key) is
    dropped; an all-invalid chain becomes ``None``.
    """

    if value.strip() == "default":
        return "default"
    kept = [part.strip() for part in value.split(",") if part.strip() in allowed]
    return ",".join(kept) if kept else None


def _vendors_from_config(config: dict) -> dict:
    """Configured data vendors, filtered to the known routing definitions.

    Only valid categories (``data_vendors``), tool names (``tool_vendors``) and
    known provider identifiers (values, possibly a fallback chain) are kept;
    unknown keys and credential-bearing URLs are omitted. This shapes a newly
    written manifest only — reading existing manifests stays v1-compatible.
    """

    categories, vendor_methods = _vendor_routing()
    providers_by_category: dict[str, set[str]] = {}
    for category, info in categories.items():
        allowed: set[str] = set()
        for tool in info["tools"]:
            allowed |= set(vendor_methods.get(tool, {}).keys())
        providers_by_category[category] = allowed
    providers_by_tool: dict[str, set[str]] = {
        tool: set(impl.keys()) for tool, impl in vendor_methods.items()
    }

    vendors: dict[str, str] = {}
    for key, value in (config.get("data_vendors") or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        allowed = providers_by_category.get(key)
        if allowed is None:
            continue  # unknown category
        filtered = _filter_chain(value, allowed)
        if filtered is not None:
            vendors[key] = filtered
    for key, value in (config.get("tool_vendors") or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        allowed = providers_by_tool.get(key)
        if allowed is None:
            continue  # unknown tool name
        filtered = _filter_chain(value, allowed)
        if filtered is not None:
            vendors[key] = filtered
    return vendors


def build_record(*, run_id: str, ticker: str, trade_date: str, started_at: str,
                 finished_at: str | None, status: str, analysts, config: dict,
                 code_version: str | None, reports: dict, error: dict | None,
                 asset_type: str = "stock") -> ManifestRecord:
    """Assemble a manifest record from allowlisted fields (unknowns are null).

    ``config`` is only mined for provider/model/vendor identifiers; nothing else
    from it is copied, so keys, endpoints and the full config stay out.
    """

    if not isinstance(trade_date, str):
        trade_date = str(trade_date)
    return ManifestRecord.from_dict({
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "ticker": ticker,
        "asset_type": asset_type,
        "trade_date": trade_date,
        "as_of": trade_date,
        "started_at": started_at,
        "finished_at": finished_at,
        "code_version": code_version,
        "analysts": list(analysts or []),
        "models": _models_from_config(config),
        "configured_data_vendors": _vendors_from_config(config),
        "status": status,
        "reports": reports,
        "error": error,
        "unknown_fields": [],
    })
