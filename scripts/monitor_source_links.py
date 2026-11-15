#!/usr/bin/env python3
"""OpenDatasets Automated Source-Link Monitoring Script.

Executes deterministic, rotating, safe batch monitoring of external metadata URLs
referenced in dataset records (data/datasets/*.json) for GitHub Actions and local audits.

Key Capabilities:
  - Fair LRU / timestamp-based batch rotation (no starvation, resilient to catalog changes)
  - SSRF protection against loopback, RFC1918, link-local, and cloud metadata targets
  - Thread-safe per-host rate limiting and Retry-After handling
  - Dedicated isolated monitoring-state branch sync via git plumbing with conflict detection
  - Conservative multi-run alerting policy (suspected_broken vs confirmed_broken)
  - Safe HTTP checking: bounded concurrency, HEAD-first, streaming GET fallback (<= 2KB),
    zero raw dataset binary downloads
  - Multi-format reporting: machine-readable JSON, CSV inventory, and Markdown summary
    for GitHub Actions GITHUB_STEP_SUMMARY
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Re-use proven link checking and classification logic from Task 38
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_source_links import (
    CLASSIFICATION_AUTH_REQUIRED,
    CLASSIFICATION_DNS_ERROR,
    CLASSIFICATION_FORBIDDEN,
    CLASSIFICATION_INCONCLUSIVE,
    CLASSIFICATION_NOT_CHECKED,
    CLASSIFICATION_NOT_FOUND,
    CLASSIFICATION_RATE_LIMITED,
    CLASSIFICATION_REACHABLE,
    CLASSIFICATION_REDIRECTED,
    CLASSIFICATION_SERVER_ERROR,
    CLASSIFICATION_SSL_ERROR,
    CLASSIFICATION_TIMEOUT,
    DEFAULT_CONCURRENCY,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    MAX_STREAM_BYTES,
    CheckResult,
    SSRFSecurityError,
    build_safe_opener,
    check_single_url,
    classify_http_status,
    extract_dataset_urls,
    is_ip_restricted,
)

DEFAULT_BATCH_SIZE = 50
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 250
DEFAULT_MAX_RUNTIME = 600.0  # 10 minutes maximum runtime
MIN_MAX_RUNTIME = 10.0
MAX_MAX_RUNTIME = 1800.0
DEFAULT_HOST_DELAY = 0.25  # Minimum seconds between requests to the same host

# Alert Status Values
ALERT_HEALTHY = "healthy"
ALERT_SUSPECTED_BROKEN = "suspected_broken"
ALERT_CONFIRMED_BROKEN = "confirmed_broken"
ALERT_AUTHENTICATION_REQUIRED = "authentication_required"
ALERT_RESTRICTED = "restricted"
ALERT_RATE_LIMITED = "rate_limited"
ALERT_TRANSIENT_FAILURE = "transient_failure"
ALERT_RECOVERED = "recovered"
ALERT_INCONCLUSIVE = "inconclusive"
ALERT_UNVERIFIED = "unverified"

VALID_ALERTS = {
    ALERT_HEALTHY,
    ALERT_SUSPECTED_BROKEN,
    ALERT_CONFIRMED_BROKEN,
    ALERT_AUTHENTICATION_REQUIRED,
    ALERT_RESTRICTED,
    ALERT_RATE_LIMITED,
    ALERT_TRANSIENT_FAILURE,
    ALERT_RECOVERED,
    ALERT_INCONCLUSIVE,
    ALERT_UNVERIFIED,
}

RESTRICTED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata.azure.com",
    "169.254.169.254",
}


def compute_url_fingerprint(url: str) -> str:
    """Generate a stable 16-character hexadecimal fingerprint for a URL."""
    norm = url.strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def is_safe_public_url(url: str) -> tuple[bool, str]:
    """Audit URL against loopback, private RFC1918, link-local, cloud metadata, and restricted IPs.

    Returns:
      (is_safe, failure_reason)
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{scheme}'"

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing or invalid hostname"

    hostname_lower = hostname.lower().strip(".")

    # Direct restricted names check
    if hostname_lower in RESTRICTED_HOSTNAMES or hostname_lower.endswith(".localhost"):
        return False, f"Restricted hostname '{hostname}'"

    # Check IP address literal
    try:
        ip = ipaddress.ip_address(hostname_lower)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False, f"Restricted IP literal: {ip}"
        return True, ""
    except ValueError:
        pass  # Hostname is a domain name

    # Resolve hostname via DNS and check all returned IP addresses
    try:
        addr_infos = socket.getaddrinfo(hostname_lower, None)
        if not addr_infos:
            return False, f"Could not resolve hostname '{hostname_lower}'"

        for _, _, _, _, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_reserved
                    or ip.is_multicast
                    or ip.is_unspecified
                ):
                    return False, f"Hostname '{hostname_lower}' resolves to restricted IP: {ip_str}"
            except ValueError:
                return False, f"Invalid resolved IP format: '{ip_str}'"

        return True, ""
    except socket.gaierror as exc:
        # Note: In test environments or offline mode, mock DNS should be provided
        return False, f"DNS resolution failed for '{hostname_lower}': {exc}"
    except Exception as exc:
        return False, f"Validation error for '{hostname_lower}': {exc}"


class HostRateLimiter:
    """Thread-safe rate limiter and throttle manager per hostname."""

    def __init__(self, delay_seconds: float = DEFAULT_HOST_DELAY):
        self.delay_seconds = delay_seconds
        self._global_lock = threading.Lock()
        self._host_locks: dict[str, threading.Lock] = {}
        self._last_access: dict[str, float] = {}
        self._retry_after_until: dict[str, float] = {}

    def get_host_lock(self, host: str) -> threading.Lock:
        with self._global_lock:
            if host not in self._host_locks:
                self._host_locks[host] = threading.Lock()
            return self._host_locks[host]

    def acquire(self, host: str, max_wait: float = 10.0) -> None:
        """Serialize access to the same host and enforce minimum inter-request delay."""
        h_lock = self.get_host_lock(host)
        h_lock.acquire()
        try:
            now = time.monotonic()
            # 1. Respect 429 Retry-After backoff if active
            with self._global_lock:
                backoff_until = self._retry_after_until.get(host, 0.0)
            if backoff_until > now:
                wait_needed = min(backoff_until - now, max_wait)
                time.sleep(wait_needed)
                now = time.monotonic()

            # 2. Enforce inter-request spacing
            with self._global_lock:
                last = self._last_access.get(host, 0.0)
            elapsed = now - last
            if elapsed < self.delay_seconds:
                sleep_needed = self.delay_seconds - elapsed
                time.sleep(sleep_needed)

            with self._global_lock:
                self._last_access[host] = time.monotonic()
        finally:
            h_lock.release()

    def record_retry_after(self, host: str, retry_after_header: str | None) -> None:
        """Parse HTTP Retry-After header (seconds) and apply bounded backoff."""
        if not retry_after_header:
            return
        try:
            seconds = float(retry_after_header.strip())
            # Cap backoff between 0.5s and 10.0s to avoid stalled workers
            capped = max(0.5, min(seconds, 10.0))
            with self._global_lock:
                self._retry_after_until[host] = time.monotonic() + capped
        except (ValueError, TypeError):
            pass


def extract_catalog_metadata(data_dir: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Extract and deduplicate all URLs across dataset records.

    Returns:
      A tuple of:
        - Sorted list of unique URLs
        - Mapping from URL to its metadata (referencing dataset IDs, field paths, fingerprint)
    """
    references = extract_dataset_urls(data_dir)
    catalog_meta: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"dataset_ids": set(), "field_paths": set(), "fingerprint": ""}
    )

    for ref in references:
        url = ref.url.strip()
        if not url:
            continue
        entry = catalog_meta[url]
        entry["dataset_ids"].add(ref.dataset_id)
        entry["field_paths"].add(ref.field_name)
        if not entry["fingerprint"]:
            entry["fingerprint"] = compute_url_fingerprint(url)

    # Convert sets to sorted lists for deterministic serialization
    for url, meta in catalog_meta.items():
        meta["dataset_ids"] = sorted(meta["dataset_ids"])
        meta["field_paths"] = sorted(meta["field_paths"])

    unique_urls = sorted(catalog_meta.keys())
    return unique_urls, dict(catalog_meta)


class UnrecoverableStateError(RuntimeError):
    """Raised when persistent monitoring state cannot be safely loaded or recovered."""
    pass


CURRENT_STATE_VERSION = "1.0"
SUPPORTED_STATE_VERSIONS = {"1.0"}
MIGRATABLE_STATE_VERSIONS = {"0.9"}


def migrate_state_version(raw_data: dict[str, Any], from_version: str, to_version: str) -> dict[str, Any]:
    """Migrate monitoring state dictionary from an older schema version to the target version."""
    if from_version == "0.9" and to_version == "1.0":
        migrated = dict(raw_data)
        migrated["version"] = "1.0"
        if "current_cycle" not in migrated:
            migrated["current_cycle"] = 1
        if "history" not in migrated or not isinstance(migrated["history"], dict):
            migrated["history"] = {}
        return migrated
    raise UnrecoverableStateError(
        f"Unsupported state version migration from '{from_version}' to '{to_version}'. Operator intervention required."
    )


@dataclass
class MonitoringState:
    """Persistent state capturing monitoring rotation and historical URL statuses."""

    version: str = CURRENT_STATE_VERSION
    updated_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    current_cycle: int = 1
    total_catalog_urls: int = 0
    batch_size_last_run: int = 0
    history: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_monitoring_state(
    state_path: Path | None,
    current_catalog_urls: list[str],
    allow_reset: bool = False,
) -> tuple[MonitoringState, bool]:
    """Load monitoring state with resilient recovery from missing, empty, or corrupted files.

    Durable Recovery Policy:
      1. Genuine First-Time Init: Missing state file with no backup returns initial clean state (is_recovered=False).
      2. Corrupted State with Valid Backup: Restores state from trusted backup .bak (is_recovered=True).
      3. Corrupted State without Backup:
         - If allow_reset=True (--reset-state): Preserves corrupted file as evidence and reinitializes.
         - If allow_reset=False: Aborts execution with UnrecoverableStateError to prevent silent history loss.
      4. Unknown State Versions: Rejects unknown future schema versions unless explicit operator reset is requested.

    Returns:
      (state, is_recovered)
    """
    total_urls = len(current_catalog_urls)
    catalog_set = set(current_catalog_urls)
    default_state = MonitoringState(
        total_catalog_urls=total_urls,
    )

    if state_path is None:
        return default_state, False

    backup_path = state_path.with_suffix(".bak")

    def try_recover_from_backup() -> tuple[MonitoringState, bool] | None:
        if backup_path.exists():
            try:
                b_text = backup_path.read_text(encoding="utf-8").strip()
                if b_text:
                    b_data = json.loads(b_text)
                    if isinstance(b_data, dict) and str(b_data.get("version")) in SUPPORTED_STATE_VERSIONS:
                        b_hist = {
                            u: rec
                            for u, rec in b_data.get("history", {}).items()
                            if u in catalog_set and isinstance(rec, dict)
                        }
                        b_state = MonitoringState(
                            version=CURRENT_STATE_VERSION,
                            updated_at=str(b_data.get("updated_at", "")),
                            current_cycle=max(1, int(b_data.get("current_cycle", 1))),
                            total_catalog_urls=total_urls,
                            batch_size_last_run=int(b_data.get("batch_size_last_run", 0)),
                            history=b_hist,
                        )
                        logging.warning("Successfully recovered monitoring state from trusted backup %s", backup_path)
                        return b_state, True
            except Exception as b_exc:
                logging.warning("Trusted backup file %s is also corrupt or invalid: %s", backup_path, b_exc)
        return None

    def preserve_corrupt_file() -> Path | None:
        try:
            ts = int(time.time())
            corrupt_path = state_path.with_suffix(f".corrupt.{ts}.json")
            state_path.rename(corrupt_path)
            logging.error("Preserved corrupted state evidence to %s", corrupt_path)
            return corrupt_path
        except Exception as e:
            logging.error("Could not preserve corrupted state file: %s", e)
            return None

    # Handle missing state file
    if not state_path.exists():
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        # No state and no backup: Genuine first-time initialization
        logging.info("State file %s does not exist; performing first-time initialization.", state_path)
        return default_state, False

    # Read existing state file
    try:
        content = state_path.read_text(encoding="utf-8").strip()
    except Exception as read_exc:
        corrupt_ref = preserve_corrupt_file()
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        if allow_reset:
            logging.warning("State file %s could not be read (%s); explicit reset requested.", state_path, read_exc)
            return default_state, True
        raise UnrecoverableStateError(
            f"Monitoring state at '{state_path}' could not be read ({read_exc}) and no valid backup exists. "
            f"Preserved evidence to '{corrupt_ref}'. Re-run with --reset-state to explicitly reinitialize."
        )

    # Empty file check
    if not content:
        corrupt_ref = preserve_corrupt_file()
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        if allow_reset:
            logging.warning("State file %s is empty; explicit reset requested.", state_path)
            return default_state, True
        raise UnrecoverableStateError(
            f"Monitoring state at '{state_path}' is empty (0 bytes) and no valid backup exists. "
            f"Preserved evidence to '{corrupt_ref}'. Re-run with --reset-state to explicitly reinitialize."
        )

    # Parse JSON
    try:
        raw_data = json.loads(content)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        corrupt_ref = preserve_corrupt_file()
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        if allow_reset:
            logging.warning("State file %s contains invalid JSON (%s); explicit reset requested.", state_path, exc)
            return default_state, True
        raise UnrecoverableStateError(
            f"Monitoring state at '{state_path}' contains corrupted JSON ({exc}) and no valid backup exists. "
            f"Preserved evidence to '{corrupt_ref}'. Re-run with --reset-state to explicitly reinitialize."
        )

    if not isinstance(raw_data, dict):
        corrupt_ref = preserve_corrupt_file()
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        if allow_reset:
            logging.warning("State file %s is not a JSON object; explicit reset requested.", state_path)
            return default_state, True
        raise UnrecoverableStateError(
            f"Monitoring state at '{state_path}' is not a JSON object and no valid backup exists. "
            f"Preserved evidence to '{corrupt_ref}'. Re-run with --reset-state to explicitly reinitialize."
        )

    # Version validation and migration
    version = str(raw_data.get("version", ""))
    if version in MIGRATABLE_STATE_VERSIONS:
        logging.info("Migrating state file from version '%s' to '%s'.", version, CURRENT_STATE_VERSION)
        raw_data = migrate_state_version(raw_data, version, CURRENT_STATE_VERSION)
        version = CURRENT_STATE_VERSION
    elif version not in SUPPORTED_STATE_VERSIONS:
        corrupt_ref = preserve_corrupt_file()
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        if allow_reset:
            logging.warning("Unsupported state version '%s'; explicit reset requested.", version)
            return default_state, True
        raise UnrecoverableStateError(
            f"Unsupported monitoring state version '{version}' (supported: {sorted(SUPPORTED_STATE_VERSIONS)}). "
            f"Cannot safely auto-migrate unknown version. Preserved evidence to '{corrupt_ref}'. "
            "Operator intervention required or pass --reset-state to explicitly reinitialize."
        )

    # Validate required fields
    try:
        current_cycle = int(raw_data.get("current_cycle", 1))
        if current_cycle < 1:
            current_cycle = 1
    except (ValueError, TypeError):
        current_cycle = 1

    raw_history = raw_data.get("history", {})
    if not isinstance(raw_history, dict):
        corrupt_ref = preserve_corrupt_file()
        recovered = try_recover_from_backup()
        if recovered:
            return recovered
        if allow_reset:
            return default_state, True
        raise UnrecoverableStateError(
            f"Monitoring state history field is corrupted in '{state_path}'. "
            f"Preserved evidence to '{corrupt_ref}'. Re-run with --reset-state to explicitly reinitialize."
        )

    # Prune URLs that no longer exist in catalog to prevent memory bloat
    pruned_history = {u: rec for u, rec in raw_history.items() if u in catalog_set and isinstance(rec, dict)}

    state = MonitoringState(
        version=CURRENT_STATE_VERSION,
        updated_at=str(raw_data.get("updated_at", "")),
        current_cycle=current_cycle,
        total_catalog_urls=total_urls,
        batch_size_last_run=int(raw_data.get("batch_size_last_run", 0)),
        history=pruned_history,
    )
    return state, False


def save_monitoring_state(state: MonitoringState, state_path: Path) -> None:
    """Save monitoring state atomically to disk with durable .bak backup creation."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state.updated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Maintain trusted backup of previous valid state before replacing
    if state_path.exists():
        try:
            old_text = state_path.read_text(encoding="utf-8")
            if old_text.strip():
                json.loads(old_text)  # Verify valid JSON before promoting to backup
                backup_path = state_path.with_suffix(".bak")
                backup_path.write_text(old_text, encoding="utf-8")
        except Exception as b_exc:
            logging.warning("Could not create .bak backup of existing state: %s", b_exc)

    temp_path = state_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as fp:
        json.dump(state.to_dict(), fp, indent=2)
    temp_path.replace(state_path)


def url_priority_key(url: str, state: MonitoringState) -> tuple[int, str, str]:
    """Calculate sorting priority for batch selection (LRU with stable tie-breaking).

    Priority:
      0: Never checked (highest priority)
      1: Oldest checked first (ascending last_checked_at timestamp)
      Tie-breaker: URL fingerprint
    """
    rec = state.history.get(url)
    fp = rec.get("fingerprint") if rec else compute_url_fingerprint(url)
    if not rec or not rec.get("last_checked_at"):
        return (0, "", fp)
    return (1, str(rec["last_checked_at"]), fp)


def select_batch(
    catalog_urls: list[str],
    state: MonitoringState,
    batch_size: int,
) -> tuple[list[str], int, int, bool]:
    """Select next batch using LRU / timestamp priority rotation.

    Returns:
      (batch_urls, start_index, end_index, cycle_wrapped)
    """
    total = len(catalog_urls)
    if total == 0:
        return [], 0, 0, False

    effective_batch = max(MIN_BATCH_SIZE, min(batch_size, MAX_BATCH_SIZE))

    # Sort catalog URLs by LRU priority (uninspected first, then oldest last_checked_at)
    sorted_urls = sorted(catalog_urls, key=lambda u: url_priority_key(u, state))
    batch_urls = sorted_urls[:effective_batch]

    start_idx = 0
    end_idx = len(batch_urls)
    state.batch_size_last_run = len(batch_urls)
    state.total_catalog_urls = total

    # Check whether all URLs in the catalog have been checked in the active cycle
    cycle_wrapped = False
    return batch_urls, start_idx, end_idx, cycle_wrapped


def determine_alert_status(
    prev_record: dict[str, Any] | None,
    result: CheckResult,
) -> tuple[str, int]:
    """Determine alert classification according to conservative multi-run policy.

    Rules:
      - 200/204/206/3xx: healthy (or recovered if previously broken)
      - 404/410 (Not Found):
          1 failure: suspected_broken
          >= 2 failures: confirmed_broken (evidence across runs)
      - 401: authentication_required (never dead)
      - 403: restricted (WAF/Cloudflare/anti-bot, never confirmed_broken)
      - 429: rate_limited (never confirmed_broken)
      - 5xx / Timeout / DNS / SSL: transient_failure (never confirmed_broken)
      - Inconclusive: inconclusive

    Returns:
      (alert_status, consecutive_failures)
    """
    prev_alert = prev_record.get("alert_status") if prev_record else ALERT_UNVERIFIED
    prev_failures = int(prev_record.get("consecutive_failures", 0)) if prev_record else 0

    classification = result.classification

    if classification in (CLASSIFICATION_REACHABLE, CLASSIFICATION_REDIRECTED):
        consecutive_failures = 0
        if prev_alert in (ALERT_SUSPECTED_BROKEN, ALERT_CONFIRMED_BROKEN):
            return ALERT_RECOVERED, 0
        return ALERT_HEALTHY, 0

    if classification == CLASSIFICATION_NOT_FOUND:
        consecutive_failures = prev_failures + 1
        if consecutive_failures >= 2:
            return ALERT_CONFIRMED_BROKEN, consecutive_failures
        return ALERT_SUSPECTED_BROKEN, consecutive_failures

    if classification == CLASSIFICATION_AUTH_REQUIRED:
        return ALERT_AUTHENTICATION_REQUIRED, 0

    if classification == CLASSIFICATION_FORBIDDEN:
        return ALERT_RESTRICTED, 0

    if classification == CLASSIFICATION_RATE_LIMITED:
        return ALERT_RATE_LIMITED, 0

    if classification in (
        CLASSIFICATION_TIMEOUT,
        CLASSIFICATION_SERVER_ERROR,
        CLASSIFICATION_DNS_ERROR,
        CLASSIFICATION_SSL_ERROR,
    ):
        return ALERT_TRANSIENT_FAILURE, prev_failures + 1

    return ALERT_INCONCLUSIVE, prev_failures


def execute_monitoring_batch(
    batch_urls: list[str],
    catalog_meta: dict[str, dict[str, Any]],
    state: MonitoringState,
    timeout: float = DEFAULT_TIMEOUT,
    concurrency: int = 5,
    retries: int = DEFAULT_RETRIES,
    offline: bool = False,
    max_runtime_seconds: float = DEFAULT_MAX_RUNTIME,
    rate_limiter: HostRateLimiter | None = None,
) -> list[dict[str, Any]]:
    """Execute network checks for the batch with SSRF validation, host throttling, and runtime limits."""
    results: list[dict[str, Any]] = []
    start_time = time.monotonic()
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if rate_limiter is None:
        rate_limiter = HostRateLimiter(delay_seconds=DEFAULT_HOST_DELAY)

    if offline:
        for url in batch_urls:
            meta = catalog_meta.get(url, {})
            prev = state.history.get(url)
            rec = {
                "url": url,
                "fingerprint": meta.get("fingerprint", compute_url_fingerprint(url)),
                "dataset_ids": meta.get("dataset_ids", []),
                "field_paths": meta.get("field_paths", []),
                "status_code": None,
                "classification": CLASSIFICATION_NOT_CHECKED,
                "alert_status": prev.get("alert_status", ALERT_UNVERIFIED) if prev else ALERT_UNVERIFIED,
                "consecutive_failures": prev.get("consecutive_failures", 0) if prev else 0,
                "final_redirect_target": None,
                "elapsed_ms": 0,
                "checked_at": None,  # Not checked in offline mode; do not update last_checked_at
                "error_message": "Offline mode active",
                "attempted": False,
            }
            results.append(rec)
        return results

    safe_opener = build_safe_opener()

    def check_url_safely(target_url: str) -> CheckResult:
        # 1. Runtime guard
        if (time.monotonic() - start_time) > max_runtime_seconds:
            return CheckResult(
                url=target_url,
                classification=CLASSIFICATION_NOT_CHECKED,
                error_message="Batch execution exceeded maximum runtime limit",
            )

        # 2. SSRF Pre-Check Guard
        is_safe, reason = is_safe_public_url(target_url)
        if not is_safe:
            return CheckResult(
                url=target_url,
                classification=CLASSIFICATION_FORBIDDEN,
                error_message=f"SSRF protection blocked target: {reason}",
            )

        # 3. Host Throttling
        parsed = urllib.parse.urlparse(target_url)
        host = (parsed.hostname or "").lower()
        rate_limiter.acquire(host)

        # 4. Probe execution with connection-time IP validation (mitigating DNS rebinding / TOCTOU)
        try:
            res = check_single_url(
                url=target_url,
                timeout=timeout,
                user_agent=DEFAULT_USER_AGENT,
                retries=retries,
                offline=False,
                opener=safe_opener,
            )
        except SSRFSecurityError as ssrf_err:
            res = CheckResult(
                url=target_url,
                classification=CLASSIFICATION_FORBIDDEN,
                error_message=f"SSRF protection blocked target: {ssrf_err}",
            )

        # Record 429 Retry-After if applicable
        if res.status_code == 429:
            # Audit_source_links does not expose headers in CheckResult, so record default throttle
            rate_limiter.record_retry_after(host, "2.0")

        # 5. Redirect Destination SSRF Validation
        if res.classification == CLASSIFICATION_REDIRECTED and res.redirect_url:
            resolved_target = urllib.parse.urljoin(target_url, res.redirect_url)
            target_safe, target_reason = is_safe_public_url(resolved_target)
            if not target_safe:
                return CheckResult(
                    url=target_url,
                    classification=CLASSIFICATION_FORBIDDEN,
                    status_code=res.status_code,
                    error_message=f"SSRF protection blocked redirect destination: {target_reason}",
                )

        return res

    # Use bounded concurrency
    workers = max(1, min(concurrency, len(batch_urls)))
    url_to_result: dict[str, CheckResult] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {executor.submit(check_url_safely, url): url for url in batch_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                res = future.result()
                url_to_result[url] = res
            except Exception as exc:
                url_to_result[url] = CheckResult(
                    url=url,
                    classification=CLASSIFICATION_INCONCLUSIVE,
                    error_message=f"Executor task error: {exc}",
                )

    # Process results and update historical state deterministically
    for url in batch_urls:
        res = url_to_result.get(
            url,
            CheckResult(
                url=url,
                classification=CLASSIFICATION_NOT_CHECKED,
                error_message="Check skipped",
            ),
        )

        meta = catalog_meta.get(url, {})
        prev = state.history.get(url)
        alert_status, failures = determine_alert_status(prev, res)

        # Do NOT count as checked if network request was not attempted (e.g. skipped or not_checked)
        was_attempted = res.classification != CLASSIFICATION_NOT_CHECKED

        first_checked = prev.get("first_checked_at") if prev else None
        last_checked = prev.get("last_checked_at") if prev else None
        last_success = prev.get("last_successful_check") if prev else None

        if was_attempted:
            if not first_checked:
                first_checked = now_iso
            last_checked = now_iso
            if alert_status in (ALERT_HEALTHY, ALERT_RECOVERED):
                last_success = now_iso

        history_entry = {
            "url": url,
            "fingerprint": meta.get("fingerprint", compute_url_fingerprint(url)),
            "dataset_ids": meta.get("dataset_ids", []),
            "field_paths": meta.get("field_paths", []),
            "first_checked_at": first_checked,
            "last_checked_at": last_checked,
            "last_http_status": res.status_code,
            "last_classification": res.classification,
            "final_redirect_target": res.redirect_url,
            "consecutive_failures": failures,
            "last_successful_check": last_success,
            "alert_status": alert_status,
            "cycle_last_checked": state.current_cycle if was_attempted else prev.get("cycle_last_checked", 0) if prev else 0,
        }
        state.history[url] = history_entry

        record = {
            "url": url,
            "fingerprint": history_entry["fingerprint"],
            "dataset_ids": history_entry["dataset_ids"],
            "field_paths": history_entry["field_paths"],
            "status_code": res.status_code,
            "classification": res.classification,
            "alert_status": alert_status,
            "consecutive_failures": failures,
            "final_redirect_target": res.redirect_url,
            "elapsed_ms": res.elapsed_ms,
            "checked_at": last_checked,
            "error_message": (res.error_message or "")[:200],  # Bound error length
            "attempted": was_attempted,
        }
        results.append(record)

    # Re-evaluate cycle completion across entire catalog
    all_catalog_urls = list(catalog_meta.keys())
    if all_catalog_urls and all(
        state.history.get(u, {}).get("cycle_last_checked", 0) >= state.current_cycle
        for u in all_catalog_urls
    ):
        state.current_cycle += 1
        logging.info("Cycle complete! Advanced to cycle %d", state.current_cycle)

    return results


def generate_monitoring_reports(
    batch_results: list[dict[str, Any]],
    state: MonitoringState,
    start_idx: int,
    end_idx: int,
    total_urls: int,
    cycle_wrapped: bool,
    output_dir: Path,
    summary_file: Path | None = None,
) -> dict[str, Any]:
    """Generate machine-readable JSON, CSV inventory, and Markdown summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    counts = Counter(r["classification"] for r in batch_results)
    alert_counts = Counter(r["alert_status"] for r in batch_results)

    cycle_checked = len([rec for rec in state.history.values() if rec.get("cycle_last_checked") == state.current_cycle])
    cycle_progress_pct = round((cycle_checked / total_urls) * 100.0, 1) if total_urls else 0.0

    report_payload = {
        "monitoring_task": "Task 39B",
        "run_date": now_iso,
        "cycle_info": {
            "current_cycle": state.current_cycle,
            "batch_start_index": start_idx,
            "batch_end_index": end_idx,
            "batch_size_checked": len([r for r in batch_results if r.get("attempted", True)]),
            "total_catalog_urls": total_urls,
            "cycle_progress_pct": cycle_progress_pct,
            "cycle_wrapped": cycle_wrapped,
        },
        "classification_counts": {
            "reachable": counts[CLASSIFICATION_REACHABLE],
            "redirected": counts[CLASSIFICATION_REDIRECTED],
            "not_found": counts[CLASSIFICATION_NOT_FOUND],
            "forbidden": counts[CLASSIFICATION_FORBIDDEN],
            "rate_limited": counts[CLASSIFICATION_RATE_LIMITED],
            "authentication_required": counts[CLASSIFICATION_AUTH_REQUIRED],
            "server_error": counts[CLASSIFICATION_SERVER_ERROR],
            "timeout": counts[CLASSIFICATION_TIMEOUT],
            "dns_error": counts[CLASSIFICATION_DNS_ERROR],
            "ssl_error": counts[CLASSIFICATION_SSL_ERROR],
            "inconclusive": counts[CLASSIFICATION_INCONCLUSIVE],
            "not_checked": counts[CLASSIFICATION_NOT_CHECKED],
        },
        "alert_counts": {
            "healthy": alert_counts[ALERT_HEALTHY],
            "suspected_broken": alert_counts[ALERT_SUSPECTED_BROKEN],
            "confirmed_broken": alert_counts[ALERT_CONFIRMED_BROKEN],
            "transient_failure": alert_counts[ALERT_TRANSIENT_FAILURE],
            "restricted": alert_counts[ALERT_RESTRICTED],
            "rate_limited": alert_counts[ALERT_RATE_LIMITED],
            "authentication_required": alert_counts[ALERT_AUTHENTICATION_REQUIRED],
            "recovered": alert_counts[ALERT_RECOVERED],
            "inconclusive": alert_counts[ALERT_INCONCLUSIVE],
        },
        "active_alerts": [
            r
            for r in batch_results
            if r["alert_status"] in (ALERT_SUSPECTED_BROKEN, ALERT_CONFIRMED_BROKEN, ALERT_RECOVERED)
        ],
        "batch_results": batch_results,
    }

    # 1. JSON Report
    report_json_path = output_dir / "monitoring-report.json"
    with open(report_json_path, "w", encoding="utf-8") as fp:
        json.dump(report_payload, fp, indent=2)

    # 2. CSV Report
    report_csv_path = output_dir / "monitoring-report.csv"
    with open(report_csv_path, "w", encoding="utf-8", newline="") as fp:
        fieldnames = [
            "url",
            "fingerprint",
            "dataset_ids",
            "field_paths",
            "status_code",
            "classification",
            "alert_status",
            "consecutive_failures",
            "final_redirect_target",
            "elapsed_ms",
            "checked_at",
            "error_message",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for r in batch_results:
            row = dict(r)
            row.pop("attempted", None)
            row["dataset_ids"] = ";".join(row.get("dataset_ids", []))
            row["field_paths"] = ";".join(row.get("field_paths", []))
            writer.writerow(row)

    # 3. Markdown Summary Report (compatible with GITHUB_STEP_SUMMARY)
    md_doc = f"""# Source-Link Health Monitoring Report (Task 39B)

**Execution Date:** `{now_iso}`  
**Cycle Progress:** Cycle {state.current_cycle} ({cycle_checked} of {total_urls} URLs checked — **{cycle_progress_pct}%**)  
**Persistence Architecture:** Isolated `monitoring-state` branch + 90-day artifact archives

> [!IMPORTANT]
> **Verification Dimensions & Scientific Integrity:**  
> 1. **URL Syntax Validation:** Validates URI formats offline against schema patterns.  
> 2. **Live HTTP Health:** Probes external connectivity via safe HEAD / minimal streaming GET (<= 2KB). HTTP 200/300 confirms endpoint availability, but **does not** prove dataset correctness, scientific integrity, or licensing validity.  
> 3. **Scientific Metadata Accuracy:** Requires primary research reconciliation, author citations, and authentic publisher terms. **Two automated 404 responses do NOT prove scientific dataset removal.**

---

## Batch Summary

| Metric | Count | Description |
|---|---|---|
| **URLs in Current Batch** | `{len(batch_results)}` | Deterministic LRU rotation |
| **Healthy / Reachable** | `{alert_counts[ALERT_HEALTHY]}` | Direct 200/204/206 or clean redirect |
| **Recovered** | `{alert_counts[ALERT_RECOVERED]}` | Previously flagged broken URL now responsive |
| **Suspected Broken** | `{alert_counts[ALERT_SUSPECTED_BROKEN]}` | First 404/410 observation (provisional alert) |
| **Confirmed Broken** | `{alert_counts[ALERT_CONFIRMED_BROKEN]}` | Repeated 404/410 verified across separate runs |
| **Transient Failures** | `{alert_counts[ALERT_TRANSIENT_FAILURE]}` | 5xx, timeouts, connection resets (not dead) |
| **Restricted / WAF** | `{alert_counts[ALERT_RESTRICTED]}` | 403 Forbidden or anti-bot challenge |
| **Rate Limited** | `{alert_counts[ALERT_RATE_LIMITED]}` | 429 Too Many Requests |
| **Auth Required** | `{alert_counts[ALERT_AUTHENTICATION_REQUIRED]}` | 401 Unauthorized (session gate) |
| **Inconclusive** | `{alert_counts[ALERT_INCONCLUSIVE]}` | Non-standard responses |

---

## Actionable Alerts
"""
    alerts = report_payload["active_alerts"]
    if not alerts:
        md_doc += "\n*No confirmed broken URLs, suspected failures, or new alert transitions detected in this batch.*\n"
    else:
        md_doc += "\n| Alert Status | Status Code | Referencing Datasets | Target URL |\n|---|---|---|---|\n"
        for a in alerts:
            dids = ", ".join(f"`{d}`" for d in a.get("dataset_ids", []))
            md_doc += f"| `{a['alert_status']}` | `{a.get('status_code') or 'ERR'}` | {dids} | [{a['url']}]({a['url']}) |\n"

    summary_md_path = output_dir / "monitoring-summary.md"
    with open(summary_md_path, "w", encoding="utf-8") as fp:
        fp.write(md_doc)

    if summary_file is not None:
        try:
            with open(summary_file, "a", encoding="utf-8") as sfp:
                sfp.write("\n" + md_doc + "\n")
        except Exception as exc:
            logging.warning("Could not append to summary file %s: %s", summary_file, exc)

    return report_payload


def sync_branch_pull(
    state_branch: str,
    state_file: Path,
    repo_root: Path,
    allow_reset: bool = False,
) -> bool:
    """Fetch and validate state and durable backup from isolated git branch without checking out or dirtying main.

    Durable Safety Invariants:
      1. Missing branch on remote: ONLY this condition represents genuine first-time initialization.
         Returns True without error and guarantees clean slate for initial state creation.
      2. Remote query failure (network / auth / permission error): Raises RuntimeError and fails loudly.
      3. Git fetch failure: Raises RuntimeError and fails loudly.
      4. Missing state files on existing branch: Raises UnrecoverableStateError and fails loudly.
      5. Corrupted state with valid backup: Prepares state and backup on disk for transparent recovery on state load.
      6. Corrupted state with invalid/missing backup: Raises UnrecoverableStateError and fails loudly (unless allow_reset=True).
      7. Unsupported schema version: Raises UnrecoverableStateError and fails loudly (unless allow_reset=True).
    """
    backup_file = state_file.with_suffix(".bak")

    # 1. Query remote head for state_branch
    try:
        res = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", state_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        err_msg = (exc.stderr or "").strip() or str(exc)
        logging.error(
            "Failed to query remote branch '%s' via git ls-remote (network, auth, or permission error): %s",
            state_branch,
            err_msg,
        )
        raise RuntimeError(
            f"Failed to query remote branch '{state_branch}' via git ls-remote (network, auth, or permission error): {err_msg}"
        ) from exc

    # 2. Check if remote branch genuinely does not exist
    if not res.stdout.strip():
        # Remote branch genuinely does not exist yet on origin
        if state_file.exists():
            state_file.unlink()
        if backup_file.exists():
            backup_file.unlink()
        logging.info(
            "Remote branch '%s' does not exist yet on origin. Genuine first-time initialization; fresh state will be created on execution.",
            state_branch,
        )
        print(f"  ✓ Remote branch '{state_branch}' does not exist on origin. Genuine first-time initialization.")
        return True

    # 3. Branch exists on origin: Fetch refs
    try:
        subprocess.run(
            ["git", "fetch", "origin", f"{state_branch}:refs/remotes/origin/{state_branch}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        err_msg = (exc.stderr or "").strip() or str(exc)
        logging.error("Failed to fetch remote branch '%s' from origin: %s", state_branch, err_msg)
        raise RuntimeError(
            f"Failed to fetch branch '{state_branch}' from origin (network, permission, or fetch error): {err_msg}"
        ) from exc

    # 4. Extract state.json and state.bak from fetched tree
    state_file.parent.mkdir(parents=True, exist_ok=True)

    show_state = subprocess.run(
        ["git", "show", f"refs/remotes/origin/{state_branch}:state.json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    show_bak = subprocess.run(
        ["git", "show", f"refs/remotes/origin/{state_branch}:state.bak"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    state_content = show_state.stdout if show_state.returncode == 0 else None
    bak_content = show_bak.stdout if show_bak.returncode == 0 else None

    if state_content is None and bak_content is None:
        raise UnrecoverableStateError(
            f"Remote branch '{state_branch}' exists but contains neither state.json nor state.bak."
        )

    # Helper to validate a JSON string payload
    def _is_valid_payload(text: str | None) -> tuple[bool, str]:
        if text is None:
            return False, "file does not exist"
        if not text.strip():
            return False, "file is empty (0 bytes)"
        try:
            data = json.loads(text)
        except Exception as j_exc:
            return False, f"corrupted JSON ({j_exc})"
        if not isinstance(data, dict):
            return False, "root JSON entity is not an object"
        ver = str(data.get("version", ""))
        if ver not in SUPPORTED_STATE_VERSIONS:
            return False, f"unsupported schema version '{ver}' (supported: {SUPPORTED_STATE_VERSIONS})"
        if "history" not in data or not isinstance(data.get("history"), dict):
            return False, "missing or invalid 'history' mapping"
        return True, ""

    state_valid, state_reason = _is_valid_payload(state_content)
    bak_valid, bak_reason = _is_valid_payload(bak_content)

    # Write backup file to disk if present
    if bak_content is not None and bak_content.strip():
        backup_file.write_text(bak_content, encoding="utf-8")
    elif backup_file.exists():
        backup_file.unlink()

    # Write primary state file to disk if present
    if state_content is not None:
        state_file.write_text(state_content, encoding="utf-8")
    elif state_file.exists():
        state_file.unlink()

    if state_valid:
        logging.info("Successfully retrieved and validated state.json from remote branch '%s'", state_branch)
        print(f"  ✓ Successfully retrieved and validated state.json from remote branch '{state_branch}'.")
        return True

    # Primary state is invalid or corrupted, but valid backup is present
    if bak_valid:
        logging.warning(
            "Primary state.json on remote branch '%s' is invalid (%s), but valid backup state.bak is present. Recovery will occur on state load.",
            state_branch,
            state_reason,
        )
        print(f"  ⚠ Remote state.json is invalid ({state_reason}), but valid backup state.bak is present.")
        return True

    # Both primary and backup are invalid
    if allow_reset:
        logging.warning(
            "State on remote branch '%s' is unrecoverable (primary: %s, backup: %s); explicit reset requested.",
            state_branch,
            state_reason,
            bak_reason,
        )
        print(f"  ⚠ Remote state is unrecoverable; resetting state as explicitly requested.")
        if state_file.exists():
            state_file.unlink()
        if backup_file.exists():
            backup_file.unlink()
        return True

    # Preserve evidence locally if possible
    ts = int(time.time())
    corrupt_evidence = state_file.with_suffix(f".corrupt.{ts}.json")
    if state_content is not None:
        try:
            corrupt_evidence.write_text(state_content, encoding="utf-8")
            logging.error("Preserved corrupted remote state evidence to %s", corrupt_evidence)
        except Exception as e:
            logging.error("Could not preserve corrupted state file: %s", e)

    evidence_note = f" Preserved evidence to '{corrupt_evidence}'." if state_content is not None else ""
    raise UnrecoverableStateError(
        f"Remote branch '{state_branch}' has unrecoverable state: primary state.json is invalid ({state_reason}) "
        f"and backup state.bak is invalid or missing ({bak_reason}).{evidence_note} "
        f"Re-run with --reset-state to explicitly reinitialize."
    )


def merge_monitoring_histories(
    local_state: dict[str, Any],
    remote_state: dict[str, Any],
) -> dict[str, Any]:
    """Merge local and remote monitoring state histories deterministically without data loss."""
    merged = dict(local_state)
    merged["version"] = CURRENT_STATE_VERSION

    try:
        loc_cycle = int(local_state.get("current_cycle", 1))
    except (ValueError, TypeError):
        loc_cycle = 1

    try:
        rem_cycle = int(remote_state.get("current_cycle", 1))
    except (ValueError, TypeError):
        rem_cycle = 1

    merged["current_cycle"] = max(loc_cycle, rem_cycle)
    merged["total_catalog_urls"] = local_state.get("total_catalog_urls") or remote_state.get("total_catalog_urls", 0)

    local_hist = local_state.get("history", {}) if isinstance(local_state.get("history"), dict) else {}
    remote_hist = remote_state.get("history", {}) if isinstance(remote_state.get("history"), dict) else {}

    merged_hist: dict[str, Any] = {}
    all_urls = sorted(set(local_hist.keys()) | set(remote_hist.keys()))

    for url in all_urls:
        loc = local_hist.get(url)
        rem = remote_hist.get(url)
        if loc and rem and isinstance(loc, dict) and isinstance(rem, dict):
            loc_time = str(loc.get("last_checked_at") or "")
            rem_time = str(rem.get("last_checked_at") or "")
            if rem_time > loc_time:
                winner = dict(rem)
            elif loc_time > rem_time:
                winner = dict(loc)
            else:
                rem_cycle_u = int(rem.get("cycle_last_checked", 0))
                loc_cycle_u = int(loc.get("cycle_last_checked", 0))
                if rem_cycle_u > loc_cycle_u:
                    winner = dict(rem)
                else:
                    winner = dict(loc)

            # Union dataset IDs and field paths
            all_dids = sorted(set(loc.get("dataset_ids", [])) | set(rem.get("dataset_ids", [])))
            all_fpaths = sorted(set(loc.get("field_paths", [])) | set(rem.get("field_paths", [])))
            winner["dataset_ids"] = all_dids
            winner["field_paths"] = all_fpaths

            # Max cycle checked
            winner["cycle_last_checked"] = max(
                int(loc.get("cycle_last_checked", 0)),
                int(rem.get("cycle_last_checked", 0)),
            )

            # Earliest first checked at
            loc_first = str(loc.get("first_checked_at") or "")
            rem_first = str(rem.get("first_checked_at") or "")
            first_candidates = [t for t in (loc_first, rem_first) if t]
            if first_candidates:
                winner["first_checked_at"] = min(first_candidates)

            # Latest successful check
            loc_succ = str(loc.get("last_successful_check") or "")
            rem_succ = str(rem.get("last_successful_check") or "")
            succ_candidates = [t for t in (loc_succ, rem_succ) if t]
            if succ_candidates:
                winner["last_successful_check"] = max(succ_candidates)

            merged_hist[url] = winner
        elif loc and isinstance(loc, dict):
            merged_hist[url] = dict(loc)
        elif rem and isinstance(rem, dict):
            merged_hist[url] = dict(rem)

    merged["history"] = merged_hist
    return merged


def sync_branch_push(state_branch: str, state_file: Path, repo_root: Path, max_retries: int = 3) -> bool:
    """Commit state file to isolated git branch and push to origin with conflict detection, history reconciliation, and durable remote backup."""
    if not state_file.exists():
        logging.warning("State file %s does not exist; skipping branch push.", state_file)
        return False

    try:
        local_content = state_file.read_text(encoding="utf-8")
        local_dict = json.loads(local_content)
        if not isinstance(local_dict, dict):
            raise ValueError("State is not a valid JSON object")
    except Exception as exc:
        logging.error("State file %s contains invalid JSON (%s); refusing to commit corrupted state.", state_file, exc)
        print(f"::error::State file {state_file} contains invalid JSON: {exc}", file=sys.stderr)
        return False

    for attempt in range(1, max_retries + 1):
        try:
            parent_commit = None
            ls_remote = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", state_branch],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_payload = json.dumps(local_dict, indent=2)

            if ls_remote.stdout.strip():
                # Branch exists on remote: fetch latest commit
                subprocess.run(
                    ["git", "fetch", "origin", f"{state_branch}:refs/remotes/origin/{state_branch}"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                parent_commit = subprocess.check_output(
                    ["git", "rev-parse", f"refs/remotes/origin/{state_branch}"],
                    cwd=repo_root,
                    text=True,
                ).strip()

                # Reconcile local state with remote state
                try:
                    remote_raw = subprocess.check_output(
                        ["git", "show", f"refs/remotes/origin/{state_branch}:state.json"],
                        cwd=repo_root,
                        text=True,
                    )
                    remote_dict = json.loads(remote_raw)
                    if isinstance(remote_dict, dict):
                        merged_dict = merge_monitoring_histories(local_dict, remote_dict)
                        commit_payload = json.dumps(merged_dict, indent=2)
                        # Keep local working file updated with reconciled state
                        state_file.write_text(commit_payload, encoding="utf-8")
                        local_dict = merged_dict
                except Exception as merge_exc:
                    logging.warning("Could not reconcile remote state on attempt %d: %s", attempt, merge_exc)

            # 1. Create blob for state.json
            state_blob = subprocess.check_output(
                ["git", "hash-object", "-w", "--stdin"],
                input=commit_payload,
                cwd=repo_root,
                text=True,
            ).strip()

            # 2. Determine blob for durable state.bak
            bak_blob = None
            if parent_commit:
                try:
                    bak_blob = subprocess.check_output(
                        ["git", "rev-parse", f"refs/remotes/origin/{state_branch}:state.json"],
                        cwd=repo_root,
                        text=True,
                    ).strip()
                except Exception:
                    pass

            if not bak_blob:
                backup_file = state_file.with_suffix(".bak")
                if backup_file.exists():
                    try:
                        bak_content = backup_file.read_text(encoding="utf-8")
                        json.loads(bak_content)
                        bak_blob = subprocess.check_output(
                            ["git", "hash-object", "-w", "--stdin"],
                            input=bak_content,
                            cwd=repo_root,
                            text=True,
                        ).strip()
                    except Exception:
                        bak_blob = state_blob
                else:
                    bak_blob = state_blob

            # Build tree containing both primary state and durable backup
            tree_input = f"100644 blob {state_blob}\tstate.json\n100644 blob {bak_blob}\tstate.bak\n"
            tree_hash = subprocess.check_output(
                ["git", "mktree"],
                input=tree_input,
                cwd=repo_root,
                text=True,
            ).strip()

            commit_args = ["git", "commit-tree", tree_hash, "-m", "chore(monitoring): update source-link state [skip ci]"]
            if parent_commit:
                commit_args.extend(["-p", parent_commit])

            commit_hash = subprocess.check_output(
                commit_args,
                cwd=repo_root,
                text=True,
            ).strip()

            # Push commit explicitly without force-pushing
            push_res = subprocess.run(
                ["git", "push", "origin", f"{commit_hash}:refs/heads/{state_branch}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if push_res.returncode == 0:
                logging.info(
                    "Successfully pushed updated monitoring state to branch '%s' (commit %s)",
                    state_branch,
                    commit_hash[:8],
                )
                return True

            stderr = push_res.stderr.strip()
            # Check for fatal branch protection or authentication errors
            stderr_lower = stderr.lower()
            if any(term in stderr_lower for term in ("protected", "permission", "denied", "authentication", "forbidden")):
                logging.error("Push rejected due to permissions or branch protection: %s", stderr)
                print(f"::error::State branch push rejected (permissions/protection): {stderr}", file=sys.stderr)
                return False

            logging.warning("Push to '%s' rejected (attempt %d/%d): %s", state_branch, attempt, max_retries, stderr)
            time.sleep(1.0 * attempt)
        except Exception as exc:
            logging.warning("Error pushing state to branch '%s' (attempt %d/%d): %s", state_branch, attempt, max_retries, exc)
            time.sleep(1.0 * attempt)

    logging.error("Failed to push state to branch '%s' after %d attempts.", state_branch, max_retries)
    print(f"::error::Failed to persist monitoring state to branch '{state_branch}' after {max_retries} attempts.", file=sys.stderr)
    return False


def validate_and_sanitize_inputs(
    batch_size_raw: Any,
    max_runtime_raw: Any,
    offline_raw: Any,
    dry_run_raw: Any,
    reset_state_raw: Any,
) -> tuple[int, float, bool, bool, bool]:
    """Validate and sanitize inputs against injection, overflow, and out-of-range bounds."""
    # 1. batch_size
    try:
        batch_size = int(str(batch_size_raw).strip() if batch_size_raw is not None else DEFAULT_BATCH_SIZE)
        if not (MIN_BATCH_SIZE <= batch_size <= MAX_BATCH_SIZE):
            raise ValueError(f"batch_size must be between {MIN_BATCH_SIZE} and {MAX_BATCH_SIZE}, got {batch_size}")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid batch_size parameter: {exc}")

    # 2. max_runtime
    try:
        max_runtime = float(str(max_runtime_raw).strip() if max_runtime_raw is not None else DEFAULT_MAX_RUNTIME)
        if not (MIN_MAX_RUNTIME <= max_runtime <= MAX_MAX_RUNTIME):
            raise ValueError(f"max_runtime must be between {MIN_MAX_RUNTIME} and {MAX_MAX_RUNTIME} seconds, got {max_runtime}")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid max_runtime parameter: {exc}")

    # 3. Booleans
    def parse_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no", "", "none"):
            return False
        raise ValueError(f"Invalid boolean value: '{val}'")

    offline = parse_bool(offline_raw)
    dry_run = parse_bool(dry_run_raw)
    reset_state = parse_bool(reset_state_raw)

    return batch_size, max_runtime, offline, dry_run, reset_state


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenDatasets Automated Source-Link Monitoring.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=REPO_ROOT / "data" / "datasets",
        help="Path to datasets metadata directory.",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=REPO_ROOT / ".monitoring_state" / "state.json",
        help="Path to persistent state JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "monitoring_output",
        help="Directory to write monitoring reports.",
    )
    parser.add_argument(
        "--batch-size",
        type=str,
        default=None,
        help="Number of unique URLs to check in this run (1 to 250, default 50).",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        default=None,
        help="Optional path to append Markdown summary (e.g. $GITHUB_STEP_SUMMARY).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run offline without making live network requests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview batch selection without executing HTTP probes or updating state file.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset rotation pointer to start a fresh cycle.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Concurrency worker limit (default 5).",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=str,
        default=None,
        help="Maximum overall runtime limit in seconds (default 600).",
    )
    parser.add_argument(
        "--sync-branch-pull",
        action="store_true",
        help="Pull state file from git monitoring-state branch.",
    )
    parser.add_argument(
        "--sync-branch-push",
        action="store_true",
        help="Push state file to git monitoring-state branch with conflict detection.",
    )
    parser.add_argument(
        "--state-branch",
        type=str,
        default="monitoring-state",
        help="Git branch name for persistent monitoring state.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to git repository root (defaults to current working directory).",
    )

    args = parser.parse_args()

    # Parse inputs from CLI or environment variables
    raw_batch = args.batch_size if args.batch_size is not None else os.environ.get("INPUT_BATCH_SIZE")
    raw_runtime = args.max_runtime_seconds if args.max_runtime_seconds is not None else os.environ.get("INPUT_MAX_RUNTIME")
    raw_offline = args.offline or os.environ.get("INPUT_OFFLINE", "false")
    raw_dry_run = args.dry_run or os.environ.get("INPUT_DRY_RUN", "false")
    raw_reset = args.reset_state or os.environ.get("INPUT_RESET_STATE", "false")

    try:
        batch_size, max_runtime, offline, dry_run, reset_state = validate_and_sanitize_inputs(
            raw_batch, raw_runtime, raw_offline, raw_dry_run, raw_reset
        )
    except ValueError as val_err:
        print(f"::error::Input validation failed: {val_err}", file=sys.stderr)
        return 2

    repo_root = args.repo_root or Path.cwd()

    # Handle branch sync pull if requested
    if args.sync_branch_pull:
        try:
            success = sync_branch_pull(args.state_branch, args.state_file, repo_root, allow_reset=reset_state)
            return 0 if success else 1
        except Exception as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1

    # Handle branch sync push if requested
    if args.sync_branch_push:
        try:
            success = sync_branch_push(args.state_branch, args.state_file, repo_root)
            return 0 if success else 1
        except Exception as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1

    print("=======================================================")
    print(" [MONITOR] OpenDatasets Automated Source-Link Monitor  ")
    print("=======================================================")
    print(f"  • Data directory:    {args.data_dir}")
    print(f"  • State file:        {args.state_file}")
    print(f"  • Output directory:  {args.output_dir}")
    print(f"  • Effective batch:   {batch_size}")
    print(f"  • Max runtime limit: {max_runtime}s")
    print(f"  • Offline mode:      {offline}")
    print(f"  • Dry-run mode:      {dry_run}")
    print(f"  • Reset state:       {reset_state}")

    # 1. Extract catalog URLs
    unique_urls, catalog_meta = extract_catalog_metadata(args.data_dir)
    total_urls = len(unique_urls)
    print(f"  ✓ Discovered {total_urls} unique URLs across {len(list(args.data_dir.glob('*.json')))} datasets")

    # 2. Load monitoring state
    try:
        state, is_recovered = load_monitoring_state(args.state_file, unique_urls, allow_reset=reset_state)
        if is_recovered:
            print("  ⚠ State was recovered from backup or reinitialized.")
    except UnrecoverableStateError as err:
        print(f"::error::{err}", file=sys.stderr)
        return 1

    if reset_state:
        state.current_cycle = 1
        state.history = {}
        print("  ✓ State manually reset to cycle 1.")

    # 3. Select fair LRU batch
    batch_urls, start_idx, end_idx, cycle_wrapped = select_batch(
        catalog_urls=unique_urls,
        state=state,
        batch_size=batch_size,
    )
    print(f"  ✓ Selected batch: {len(batch_urls)} URLs (LRU priority)")
    if cycle_wrapped:
        print(f"  ↻ Cycle complete! Advanced to cycle {state.current_cycle}.")

    if dry_run:
        print("\n[DRY RUN] Preview of URLs selected for this batch:")
        for idx, u in enumerate(batch_urls[:10]):
            print(f"   [{idx:04d}] {u}")
        if len(batch_urls) > 10:
            print(f"   ... and {len(batch_urls) - 10} more URLs.")
        print("\nDry-run completed successfully without updating state or making network calls.")
        return 0

    # 4. Execute batch checks with SSRF and per-host rate limiting
    print(f"\nProbing {len(batch_urls)} URLs (concurrency={args.concurrency}, timeout={args.timeout}s)...")
    rate_limiter = HostRateLimiter(delay_seconds=DEFAULT_HOST_DELAY)
    results = execute_monitoring_batch(
        batch_urls=batch_urls,
        catalog_meta=catalog_meta,
        state=state,
        timeout=args.timeout,
        concurrency=args.concurrency,
        retries=DEFAULT_RETRIES,
        offline=offline,
        max_runtime_seconds=max_runtime,
        rate_limiter=rate_limiter,
    )

    # 5. Save state
    save_monitoring_state(state, args.state_file)
    print(f"  ✓ Updated persistent state at {args.state_file}")

    # 6. Generate reports
    summary_path = args.summary_file or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if "GITHUB_STEP_SUMMARY" in os.environ else None)
    report = generate_monitoring_reports(
        batch_results=results,
        state=state,
        start_idx=start_idx,
        end_idx=end_idx,
        total_urls=total_urls,
        cycle_wrapped=cycle_wrapped,
        output_dir=args.output_dir,
        summary_file=summary_path,
    )

    print(f"  ✓ Generated reports in {args.output_dir}")
    print(f"  • Healthy: {report['alert_counts']['healthy']}")
    print(f"  • Suspected Broken: {report['alert_counts']['suspected_broken']}")
    print(f"  • Confirmed Broken: {report['alert_counts']['confirmed_broken']}")
    print(f"  • Transient Failures: {report['alert_counts']['transient_failure']}")
    print(f"  • Recovered: {report['alert_counts']['recovered']}")
    print("=======================================================")
    print("[SUCCESS] Monitoring Run Completed Successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
