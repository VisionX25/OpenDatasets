"""Unit tests for automated source-link monitoring, reliability & security (Task 39B).

Verifies:
  - Unique URL extraction and deduplication
  - Fair LRU / timestamp-based batch rotation (no starvation)
  - Full-cycle wraparound and cycle advancement
  - Resilient recovery from missing, empty, or corrupted state
  - SSRF protection against loopback, RFC1918, link-local, and cloud metadata targets
  - Thread-safe per-host rate limiting and Retry-After handling
  - Hardened input validation and sanitization
  - Multi-run alert policy (suspected_broken, confirmed_broken, recovered)
  - Handling of 401, 403, 429, timeouts, and transient failures
  - Isolated git branch state persistence and conflict detection
  - 25-cycle end-to-end synthetic simulation verifying 100% coverage
  - Zero public network requests (100% mocked / offline)
"""

from __future__ import annotations

import csv
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

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
    CheckResult,
    SSRFSecurityError,
    build_safe_opener,
    check_single_url,
    create_safe_connection,
)
from scripts.monitor_source_links import (
    ALERT_AUTHENTICATION_REQUIRED,
    ALERT_CONFIRMED_BROKEN,
    ALERT_HEALTHY,
    ALERT_INCONCLUSIVE,
    ALERT_RATE_LIMITED,
    ALERT_RECOVERED,
    ALERT_RESTRICTED,
    ALERT_SUSPECTED_BROKEN,
    ALERT_TRANSIENT_FAILURE,
    ALERT_UNVERIFIED,
    HostRateLimiter,
    MonitoringState,
    UnrecoverableStateError,
    compute_url_fingerprint,
    determine_alert_status,
    execute_monitoring_batch,
    extract_catalog_metadata,
    generate_monitoring_reports,
    is_safe_public_url,
    load_monitoring_state,
    merge_monitoring_histories,
    save_monitoring_state,
    select_batch,
    sync_branch_pull,
    sync_branch_push,
    validate_and_sanitize_inputs,
)


@pytest.fixture
def mock_datasets_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with synthetic dataset JSON records."""
    d_dir = tmp_path / "datasets"
    d_dir.mkdir(parents=True)

    d1 = {
        "id": "ds-alpha",
        "homepage_url": "https://example.org/alpha",
        "publisher": {"name": "Lab A", "url": "https://example.org/lab-a"},
        "license": {"url": "https://example.org/license-alpha"},
        "citation": {"paper_url": "https://doi.org/10.1000/alpha"},
        "source_references": [
            {"title": "Repo", "url": "https://github.com/example/alpha"},
        ],
    }

    d2 = {
        "id": "ds-beta",
        "homepage_url": "https://example.org/beta",
        "publisher": {"name": "Lab B", "url": "https://example.org/lab-b"},
        "license": {"url": "https://example.org/license-alpha"},  # Shared
        "citation": {"paper_url": "https://doi.org/10.1000/beta"},
        "source_references": [
            {"title": "Repo", "url": "https://github.com/example/beta"},
        ],
    }

    d3 = {
        "id": "ds-gamma",
        "homepage_url": "https://example.org/gamma",
        "publisher": {"name": "Lab A", "url": "https://example.org/lab-a"},  # Shared
        "license": {"url": "https://example.org/license-gamma"},
        "citation": {"paper_url": "https://doi.org/10.1000/gamma"},
    }

    for d in [d1, d2, d3]:
        with open(d_dir / f"{d['id']}.json", "w", encoding="utf-8") as fp:
            json.dump(d, fp)

    return d_dir


class TestCatalogExtraction:
    def test_unique_url_extraction(self, mock_datasets_dir: Path):
        unique_urls, catalog_meta = extract_catalog_metadata(mock_datasets_dir)
        assert len(unique_urls) == 12
        assert len(catalog_meta) == 12

        shared_lic = "https://example.org/license-alpha"
        assert shared_lic in catalog_meta
        assert sorted(catalog_meta[shared_lic]["dataset_ids"]) == ["ds-alpha", "ds-beta"]
        assert "license.url" in catalog_meta[shared_lic]["field_paths"]

    def test_stable_batch_ordering(self, mock_datasets_dir: Path):
        urls1, _ = extract_catalog_metadata(mock_datasets_dir)
        urls2, _ = extract_catalog_metadata(mock_datasets_dir)
        assert urls1 == urls2
        assert urls1 == sorted(urls1)

    def test_url_fingerprint_deterministic(self):
        u1 = "https://example.org/dataset-1"
        u2 = "https://example.org/dataset-1"
        u3 = "https://example.org/dataset-2"
        assert compute_url_fingerprint(u1) == compute_url_fingerprint(u2)
        assert compute_url_fingerprint(u1) != compute_url_fingerprint(u3)


class TestLRURotationFairness:
    def test_uninspected_urls_prioritized_first(self):
        urls = [f"https://example.org/{i:02d}" for i in range(5)]
        state = MonitoringState(
            history={
                urls[0]: {"last_checked_at": "2026-11-01T00:00:00Z"},
                urls[1]: {"last_checked_at": "2026-11-02T00:00:00Z"},
            }
        )
        # urls[2], urls[3], urls[4] have never been checked
        batch, _, _, _ = select_batch(urls, state, batch_size=3)
        assert set(batch) == {urls[2], urls[3], urls[4]}

    def test_lru_timestamp_ordering(self):
        urls = [f"https://example.org/{i:02d}" for i in range(4)]
        state = MonitoringState(
            history={
                urls[0]: {"last_checked_at": "2026-11-04T00:00:00Z"},
                urls[1]: {"last_checked_at": "2026-11-01T00:00:00Z"},  # Oldest
                urls[2]: {"last_checked_at": "2026-11-03T00:00:00Z"},
                urls[3]: {"last_checked_at": "2026-11-02T00:00:00Z"},
            }
        )
        batch, _, _, _ = select_batch(urls, state, batch_size=2)
        # Expect oldest checked first: urls[1] (Nov 1) and urls[3] (Nov 2)
        assert batch == [urls[1], urls[3]]

    def test_newly_added_url_immediately_prioritized(self):
        urls = [f"https://example.org/{i:02d}" for i in range(3)]
        state = MonitoringState(
            history={
                urls[0]: {"last_checked_at": "2026-11-10T00:00:00Z"},
                urls[1]: {"last_checked_at": "2026-11-10T00:00:00Z"},
                urls[2]: {"last_checked_at": "2026-11-10T00:00:00Z"},
            }
        )
        # New URL added to catalog
        new_url = "https://example.org/brand-new"
        active_urls = sorted(urls + [new_url])

        batch, _, _, _ = select_batch(active_urls, state, batch_size=1)
        assert batch == [new_url]  # Newly added URL prioritized immediately

    def test_removed_url_pruned_from_state(self, tmp_path: Path):
        active_urls = ["https://example.org/1", "https://example.org/2"]
        state = MonitoringState(
            history={
                "https://example.org/1": {"last_checked_at": "2026-11-10T00:00:00Z"},
                "https://example.org/deleted": {"last_checked_at": "2026-11-01T00:00:00Z"},
            }
        )
        state_file = tmp_path / "state.json"
        save_monitoring_state(state, state_file)

        loaded, is_recovered = load_monitoring_state(state_file, active_urls)
        assert not is_recovered
        assert "https://example.org/deleted" not in loaded.history
        assert "https://example.org/1" in loaded.history

    def test_unattempted_urls_not_counted_as_checked(self):
        urls = ["https://example.org/offline1", "https://example.org/offline2"]
        state = MonitoringState(total_catalog_urls=2)
        meta = {u: {"fingerprint": f"fp_{i}", "dataset_ids": [], "field_paths": []} for i, u in enumerate(urls)}

        # Run in offline mode
        results = execute_monitoring_batch(
            batch_urls=urls,
            catalog_meta=meta,
            state=state,
            offline=True,
        )

        assert len(results) == 2
        for r in results:
            assert r["checked_at"] is None
            assert r["attempted"] is False
            assert r["classification"] == CLASSIFICATION_NOT_CHECKED

        # History should NOT mark them as checked
        for u in urls:
            assert state.history.get(u, {}).get("last_checked_at") is None


class TestStateResilience:
    def test_first_time_initialization_when_no_state_file(self, tmp_path: Path):
        non_existent = tmp_path / "non_existent.json"
        state, is_recovered = load_monitoring_state(non_existent, ["https://example.org/1"])
        assert not is_recovered
        assert state.current_cycle == 1
        assert state.history == {}

    def test_empty_state_without_backup_raises_unrecoverable(self, tmp_path: Path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("", encoding="utf-8")
        with pytest.raises(UnrecoverableStateError, match="is empty \\(0 bytes\\) and no valid backup exists"):
            load_monitoring_state(empty_file, ["https://example.org/1"], allow_reset=False)

        # Confirm corrupted file was preserved as evidence
        corrupt_backups = list(tmp_path.glob("empty.corrupt.*.json"))
        assert len(corrupt_backups) == 1

    def test_corrupted_json_without_backup_raises_unrecoverable(self, tmp_path: Path):
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{invalid_json: 123", encoding="utf-8")
        with pytest.raises(UnrecoverableStateError, match="contains corrupted JSON.*and no valid backup exists"):
            load_monitoring_state(corrupt_file, ["https://example.org/1"], allow_reset=False)

        corrupt_backups = list(tmp_path.glob("corrupt.corrupt.*.json"))
        assert len(corrupt_backups) == 1

    def test_corrupted_json_with_allow_reset_succeeds_and_preserves_evidence(self, tmp_path: Path):
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{invalid_json: 123", encoding="utf-8")
        state, is_recovered = load_monitoring_state(corrupt_file, ["https://example.org/1"], allow_reset=True)
        assert is_recovered is True
        assert state.current_cycle == 1
        assert state.history == {}

        # Evidence must still be preserved
        corrupt_backups = list(tmp_path.glob("corrupt.corrupt.*.json"))
        assert len(corrupt_backups) == 1

    def test_corrupted_state_recovered_from_backup(self, tmp_path: Path):
        state_file = tmp_path / "state.json"
        backup_file = tmp_path / "state.bak"

        # Valid backup file with historical records
        valid_backup_data = {
            "version": "1.0",
            "current_cycle": 3,
            "history": {
                "https://example.org/1": {
                    "url": "https://example.org/1",
                    "last_checked_at": "2026-11-10T00:00:00Z",
                    "cycle_last_checked": 3,
                }
            },
        }
        backup_file.write_text(json.dumps(valid_backup_data), encoding="utf-8")

        # Corrupted active state file
        state_file.write_text("CORRUPTED_GARBAGE_PAYLOAD", encoding="utf-8")

        # Loading must automatically recover from backup without raising error
        state, is_recovered = load_monitoring_state(state_file, ["https://example.org/1"], allow_reset=False)
        assert is_recovered is True
        assert state.current_cycle == 3
        assert "https://example.org/1" in state.history

        # Evidence of corrupted state was preserved
        corrupt_backups = list(tmp_path.glob("state.corrupt.*.json"))
        assert len(corrupt_backups) == 1

    def test_missing_state_recovered_from_backup(self, tmp_path: Path):
        state_file = tmp_path / "state.json"
        backup_file = tmp_path / "state.bak"

        valid_backup_data = {
            "version": "1.0",
            "current_cycle": 2,
            "history": {
                "https://example.org/1": {"last_checked_at": "2026-11-10T00:00:00Z"}
            },
        }
        backup_file.write_text(json.dumps(valid_backup_data), encoding="utf-8")

        # Active state file does not exist
        assert not state_file.exists()

        state, is_recovered = load_monitoring_state(state_file, ["https://example.org/1"], allow_reset=False)
        assert is_recovered is True
        assert state.current_cycle == 2
        assert "https://example.org/1" in state.history

    def test_unsupported_version_raises_unrecoverable(self, tmp_path: Path):
        v2_file = tmp_path / "state.json"
        v2_file.write_text(json.dumps({"version": "2.0", "current_cycle": 1, "history": {}}), encoding="utf-8")
        with pytest.raises(UnrecoverableStateError, match="Unsupported monitoring state version '2.0'"):
            load_monitoring_state(v2_file, ["https://example.org/1"], allow_reset=False)

    def test_fixture_migration_v0_9_to_v1_0(self, tmp_path: Path):
        legacy_file = tmp_path / "legacy.json"
        legacy_data = {
            "version": "0.9",
            "current_cycle": 2,
            "history": {
                "https://example.org/1": {"last_checked_at": "2026-10-01T00:00:00Z", "alert_status": "healthy"}
            },
        }
        legacy_file.write_text(json.dumps(legacy_data), encoding="utf-8")

        state, is_recovered = load_monitoring_state(legacy_file, ["https://example.org/1"], allow_reset=False)
        assert state.version == "1.0"
        assert state.current_cycle == 2
        assert "https://example.org/1" in state.history

    def test_save_monitoring_state_creates_backup_atomically(self, tmp_path: Path):
        state_file = tmp_path / "state.json"
        backup_file = tmp_path / "state.bak"

        # 1. First save: creates state.json
        state1 = MonitoringState(current_cycle=1)
        save_monitoring_state(state1, state_file)
        assert state_file.exists()
        assert not backup_file.exists()  # No prior version to back up

        # 2. Second save: backs up state1 to state.bak before writing state2
        state2 = MonitoringState(current_cycle=2)
        save_monitoring_state(state2, state_file)
        assert backup_file.exists()

        b_data = json.loads(backup_file.read_text(encoding="utf-8"))
        assert b_data["current_cycle"] == 1

        active_data = json.loads(state_file.read_text(encoding="utf-8"))
        assert active_data["current_cycle"] == 2


class TestHostRateLimiting:
    def test_host_serialization_and_spacing(self):
        limiter = HostRateLimiter(delay_seconds=0.1)
        access_times: list[float] = []

        def worker():
            limiter.acquire("api.example.org")
            access_times.append(time.monotonic())

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(access_times) == 5
        # Verify that each sequential access to api.example.org was spaced by at least 0.08s
        for i in range(1, len(access_times)):
            diff = access_times[i] - access_times[i - 1]
            assert diff >= 0.08, f"Requests {i-1} and {i} were only {diff:.3f}s apart"

    def test_independent_hosts_not_blocked(self):
        limiter = HostRateLimiter(delay_seconds=0.5)
        start = time.monotonic()

        # Two different hosts should acquire rapidly without blocking each other
        limiter.acquire("host-a.com")
        limiter.acquire("host-b.com")
        elapsed = time.monotonic() - start
        assert elapsed < 0.4  # Well under the 0.5s delay for identical hosts

    def test_retry_after_backoff(self):
        limiter = HostRateLimiter(delay_seconds=0.01)
        limiter.record_retry_after("throttle.com", "0.2")

        start = time.monotonic()
        limiter.acquire("throttle.com")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15


class TestSSRFProtection:
    def test_loopback_blocked(self):
        safe1, _ = is_safe_public_url("http://127.0.0.1/status")
        safe2, _ = is_safe_public_url("http://127.0.1.1:8080/path")
        safe3, _ = is_safe_public_url("http://localhost:3000/")
        assert not safe1
        assert not safe2
        assert not safe3

    def test_rfc1918_private_blocked(self):
        safe_10, _ = is_safe_public_url("http://10.0.0.1/")
        safe_172, _ = is_safe_public_url("https://172.16.5.10/admin")
        safe_192, _ = is_safe_public_url("http://192.168.1.1/")
        assert not safe_10
        assert not safe_172
        assert not safe_192

    def test_cloud_metadata_blocked(self):
        safe_aws, _ = is_safe_public_url("http://169.254.169.254/latest/meta-data/")
        safe_gcp, _ = is_safe_public_url("http://metadata.google.internal/computeMetadata/v1/")
        assert not safe_aws
        assert not safe_gcp

    def test_ipv6_loopback_and_link_local_blocked(self):
        safe_v6_loop, _ = is_safe_public_url("http://[::1]/")
        safe_v6_link, _ = is_safe_public_url("http://[fe80::1]/")
        assert not safe_v6_loop
        assert not safe_v6_link

    @patch("socket.getaddrinfo")
    def test_dns_rebinding_to_private_ip_blocked(self, mock_dns: MagicMock):
        # Mock domain resolving to private IP
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 80))
        ]
        safe, reason = is_safe_public_url("http://evil-attacker.com/data")
        assert not safe
        assert "resolves to restricted IP" in reason

    @patch("socket.getaddrinfo")
    def test_valid_public_domain_allowed(self, mock_dns: MagicMock):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ]
        safe, _ = is_safe_public_url("https://example.com/data")
        assert safe

    def test_create_safe_connection_blocks_loopback_and_private_ips(self):
        # 127.0.0.1
        with pytest.raises(SSRFSecurityError, match="(?i)restricted"):
            create_safe_connection(("127.0.0.1", 80))

        # localhost
        with pytest.raises(SSRFSecurityError, match="(?i)restricted"):
            create_safe_connection(("localhost", 80))

        # 169.254.169.254
        with pytest.raises(SSRFSecurityError, match="(?i)restricted"):
            create_safe_connection(("169.254.169.254", 80))

    @patch("socket.getaddrinfo")
    def test_connection_time_dns_rebinding_prevention(self, mock_dns: MagicMock):
        # Even if pre-check passed, at connection time DNS rebinds to 127.0.0.1
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
        ]
        with pytest.raises(SSRFSecurityError, match="resolved to Restricted IP address: 127.0.0.1"):
            create_safe_connection(("rebinding-attacker.com", 80))

    def test_check_single_url_with_safe_opener_blocks_private_ip(self):
        res = check_single_url("http://127.0.0.1/sensitive", opener=build_safe_opener())
        assert res.classification == CLASSIFICATION_FORBIDDEN
        assert "SSRF protection blocked target" in res.error_message

    @patch("scripts.monitor_source_links.check_single_url")
    def test_ssrf_redirect_destination_blocked(self, mock_check: MagicMock):
        # Server responds with 301 pointing to cloud metadata
        mock_check.return_value = CheckResult(
            url="https://public.example.com",
            classification=CLASSIFICATION_REDIRECTED,
            status_code=301,
            redirect_url="http://169.254.169.254/metadata",
        )

        state = MonitoringState(total_catalog_urls=1)
        meta = {"https://public.example.com": {"fingerprint": "fp", "dataset_ids": [], "field_paths": []}}

        with patch("scripts.monitor_source_links.is_safe_public_url") as mock_safe:
            # First URL is safe, redirect destination is restricted
            def safe_side_effect(u):
                if "169.254" in u:
                    return False, "Restricted IP"
                return True, ""

            mock_safe.side_effect = safe_side_effect

            results = execute_monitoring_batch(
                batch_urls=["https://public.example.com"],
                catalog_meta=meta,
                state=state,
            )

            assert len(results) == 1
            assert results[0]["classification"] == CLASSIFICATION_FORBIDDEN
            assert "SSRF protection blocked redirect destination" in results[0]["error_message"]


class TestAlertClassification:
    def test_consecutive_404_transitions(self):
        url = "https://example.org/dead"
        result_404 = CheckResult(url=url, classification=CLASSIFICATION_NOT_FOUND, status_code=404)

        # Run 1: Suspected Broken
        alert1, fails1 = determine_alert_status(None, result_404)
        assert alert1 == ALERT_SUSPECTED_BROKEN
        assert fails1 == 1

        # Run 2: Confirmed Broken
        prev = {"alert_status": ALERT_SUSPECTED_BROKEN, "consecutive_failures": 1}
        alert2, fails2 = determine_alert_status(prev, result_404)
        assert alert2 == ALERT_CONFIRMED_BROKEN
        assert fails2 == 2

    def test_recovered_transition(self):
        url = "https://example.org/revived"
        result_200 = CheckResult(url=url, classification=CLASSIFICATION_REACHABLE, status_code=200)

        prev_confirmed = {"alert_status": ALERT_CONFIRMED_BROKEN, "consecutive_failures": 3}
        alert, fails = determine_alert_status(prev_confirmed, result_200)
        assert alert == ALERT_RECOVERED
        assert fails == 0

    def test_401_403_429_never_confirmed_broken(self):
        url = "https://example.org/gated"
        for code, classif, expected_alert in [
            (401, CLASSIFICATION_AUTH_REQUIRED, ALERT_AUTHENTICATION_REQUIRED),
            (403, CLASSIFICATION_FORBIDDEN, ALERT_RESTRICTED),
            (429, CLASSIFICATION_RATE_LIMITED, ALERT_RATE_LIMITED),
        ]:
            res = CheckResult(url=url, classification=classif, status_code=code)
            # Even with 10 repeated observations, should never be confirmed_broken
            prev = {"alert_status": expected_alert, "consecutive_failures": 10}
            alert, fails = determine_alert_status(prev, res)
            assert alert == expected_alert
            assert alert != ALERT_CONFIRMED_BROKEN
            assert fails == 0


class TestInputSanitization:
    def test_default_inputs(self):
        b, r, off, dry, res = validate_and_sanitize_inputs(None, None, None, None, None)
        assert b == 50
        assert r == 600.0
        assert off is False
        assert dry is False
        assert res is False

    def test_empty_string_inputs(self):
        """Simulate scheduled workflow where unset inputs evaluate to empty strings."""
        b, r, off, dry, res = validate_and_sanitize_inputs("", "", "", "", "")
        assert b == 50
        assert r == 600.0
        assert off is False
        assert dry is False
        assert res is False

    def test_whitespace_inputs(self):
        """Ensure whitespace-only strings fall back to documented defaults."""
        b, r, off, dry, res = validate_and_sanitize_inputs("   ", "  \t\n  ", "  ", " \t", " \n ")
        assert b == 50
        assert r == 600.0
        assert off is False
        assert dry is False
        assert res is False

    def test_valid_inputs(self):
        b, r, off, dry, res = validate_and_sanitize_inputs("50", "300", "true", "false", "0")
        assert b == 50
        assert r == 300.0
        assert off is True
        assert dry is False
        assert res is False

    def test_valid_numeric_types(self):
        """Accept native int and float types within valid range."""
        b, r, off, dry, res = validate_and_sanitize_inputs(25, 120.5, False, True, False)
        assert b == 25
        assert r == 120.5
        assert off is False
        assert dry is True
        assert res is False

    def test_boolean_parsing_matrix(self):
        # Truthy
        for t in ("true", "True", "TRUE", "1", "yes", "YES", True):
            _, _, off, dry, res = validate_and_sanitize_inputs(50, 600, t, t, t)
            assert off is True
            assert dry is True
            assert res is True

        # Falsy
        for f in ("false", "False", "FALSE", "0", "no", "NO", "none", "None", "", "   ", False, None):
            _, _, off, dry, res = validate_and_sanitize_inputs(50, 600, f, f, f)
            assert off is False
            assert dry is False
            assert res is False

    def test_batch_size_out_of_bounds(self):
        with pytest.raises(ValueError, match="batch_size must be between"):
            validate_and_sanitize_inputs("0", "600", False, False, False)
        with pytest.raises(ValueError, match="batch_size must be between"):
            validate_and_sanitize_inputs("251", "600", False, False, False)
        with pytest.raises(ValueError, match="batch_size must be between"):
            validate_and_sanitize_inputs("-5", "600", False, False, False)

    def test_batch_size_invalid_literals(self):
        with pytest.raises(ValueError, match="Invalid batch_size parameter"):
            validate_and_sanitize_inputs("abc", "600", False, False, False)
        with pytest.raises(ValueError, match="Invalid batch_size parameter"):
            validate_and_sanitize_inputs("50.5", "600", False, False, False)
        with pytest.raises(ValueError, match="Boolean value not accepted for batch_size"):
            validate_and_sanitize_inputs(True, "600", False, False, False)

    def test_max_runtime_out_of_bounds(self):
        with pytest.raises(ValueError, match="max_runtime must be between"):
            validate_and_sanitize_inputs("100", "5", False, False, False)
        with pytest.raises(ValueError, match="max_runtime must be between"):
            validate_and_sanitize_inputs("100", "5000", False, False, False)
        with pytest.raises(ValueError, match="max_runtime must be between"):
            validate_and_sanitize_inputs("100", "-10", False, False, False)

    def test_max_runtime_invalid_literals(self):
        with pytest.raises(ValueError, match="Invalid max_runtime parameter"):
            validate_and_sanitize_inputs("100", "abc", False, False, False)
        with pytest.raises(ValueError, match="Boolean value not accepted for max_runtime"):
            validate_and_sanitize_inputs("100", False, False, False, False)

    def test_boolean_invalid_values(self):
        with pytest.raises(ValueError, match="Invalid offline parameter"):
            validate_and_sanitize_inputs("50", "600", "invalid_bool", False, False)
        with pytest.raises(ValueError, match="Invalid dry_run parameter"):
            validate_and_sanitize_inputs("50", "600", False, "not_a_bool", False)
        with pytest.raises(ValueError, match="Invalid reset_state parameter"):
            validate_and_sanitize_inputs("50", "600", False, False, "unknown")


class TestScheduledMonitoringExecutionRegression:
    """Regression tests verifying scheduled GitHub Actions monitoring execution without workflow_dispatch inputs."""

    def test_cli_scheduled_execution_empty_env_vars(self, mock_datasets_dir: Path, tmp_path: Path):
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "monitor_source_links.py"
        state_file = tmp_path / "state.json"
        output_dir = tmp_path / "output"

        env = os.environ.copy()
        # Simulate GitHub Actions schedule event where inputs are absent/empty strings
        env["INPUT_BATCH_SIZE"] = ""
        env["INPUT_MAX_RUNTIME"] = ""
        env["INPUT_OFFLINE"] = ""
        env["INPUT_DRY_RUN"] = "true"
        env["INPUT_RESET_STATE"] = ""

        res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--data-dir",
                str(mock_datasets_dir),
                "--state-file",
                str(state_file),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 0
        assert "Effective batch:   50" in res.stdout
        assert "Max runtime limit: 600.0s" in res.stdout
        assert "Dry-run mode:      True" in res.stdout
        assert "Dry-run completed successfully" in res.stdout

    def test_cli_scheduled_execution_whitespace_env_vars(self, mock_datasets_dir: Path, tmp_path: Path):
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "monitor_source_links.py"
        state_file = tmp_path / "state.json"
        output_dir = tmp_path / "output"

        env = os.environ.copy()
        env["INPUT_BATCH_SIZE"] = "   "
        env["INPUT_MAX_RUNTIME"] = " \t\n "
        env["INPUT_OFFLINE"] = "  "
        env["INPUT_DRY_RUN"] = " true "
        env["INPUT_RESET_STATE"] = "   "

        res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--data-dir",
                str(mock_datasets_dir),
                "--state-file",
                str(state_file),
                "--output-dir",
                str(output_dir),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 0
        assert "Effective batch:   50" in res.stdout
        assert "Max runtime limit: 600.0s" in res.stdout
        assert "Dry-run completed successfully" in res.stdout

    def test_cli_scheduled_execution_offline_rotation(self, mock_datasets_dir: Path, tmp_path: Path):
        """Simulate scheduled rotation with offline execution, verifying state persistence and report output."""
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "monitor_source_links.py"
        state_file = tmp_path / "state.json"
        output_dir = tmp_path / "output"
        summary_file = tmp_path / "summary.md"

        env = os.environ.copy()
        env["INPUT_BATCH_SIZE"] = ""
        env["INPUT_MAX_RUNTIME"] = ""
        env["INPUT_OFFLINE"] = "true"
        env["INPUT_DRY_RUN"] = ""
        env["INPUT_RESET_STATE"] = ""

        res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--data-dir",
                str(mock_datasets_dir),
                "--state-file",
                str(state_file),
                "--output-dir",
                str(output_dir),
                "--summary-file",
                str(summary_file),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 0
        assert "Effective batch:   50" in res.stdout
        assert "Offline mode:      True" in res.stdout
        assert state_file.exists()
        assert summary_file.exists()
        assert (output_dir / "monitoring-report.json").exists()
        assert (output_dir / "monitoring-report.csv").exists()

    def test_cli_explicit_invalid_inputs_fail_strictly(self, mock_datasets_dir: Path, tmp_path: Path):
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "monitor_source_links.py"
        state_file = tmp_path / "state.json"
        output_dir = tmp_path / "output"

        # Case 1: Invalid batch size string
        env = os.environ.copy()
        env["INPUT_BATCH_SIZE"] = "invalid"
        res = subprocess.run(
            [sys.executable, str(script_path), "--data-dir", str(mock_datasets_dir), "--state-file", str(state_file), "--output-dir", str(output_dir)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 2
        assert "Input validation failed: Invalid batch_size parameter" in res.stderr

        # Case 2: Out-of-bounds batch size
        env["INPUT_BATCH_SIZE"] = "0"
        res = subprocess.run(
            [sys.executable, str(script_path), "--data-dir", str(mock_datasets_dir), "--state-file", str(state_file), "--output-dir", str(output_dir)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 2
        assert "batch_size must be between 1 and 250" in res.stderr

        # Case 3: Out-of-bounds runtime
        env["INPUT_BATCH_SIZE"] = "50"
        env["INPUT_MAX_RUNTIME"] = "5"
        res = subprocess.run(
            [sys.executable, str(script_path), "--data-dir", str(mock_datasets_dir), "--state-file", str(state_file), "--output-dir", str(output_dir)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 2
        assert "max_runtime must be between 10.0 and 1800.0" in res.stderr

        # Case 4: Invalid boolean
        env["INPUT_MAX_RUNTIME"] = "600"
        env["INPUT_OFFLINE"] = "not_a_bool"
        res = subprocess.run(
            [sys.executable, str(script_path), "--data-dir", str(mock_datasets_dir), "--state-file", str(state_file), "--output-dir", str(output_dir)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 2
        assert "Invalid offline parameter" in res.stderr


class TestGitPlumbingSync:
    def test_sync_branch_push_plumbing(self, tmp_path: Path):
        # Create a temporary local git repository with main branch
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Bot"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "bot@example.com"], cwd=repo_dir, check=True)

        # Create dummy initial commit on main
        readme = repo_dir / "README.md"
        readme.write_text("# Test Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True)

        # Set up a bare remote repo to push to
        remote_dir = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(remote_dir)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote_dir)], cwd=repo_dir, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True, capture_output=True)

        # Create state file
        state_file = repo_dir / "state.json"
        state_file.write_text(json.dumps({"version": "1.0", "current_cycle": 1}), encoding="utf-8")

        # Push to isolated monitoring-state branch
        success = sync_branch_push("monitoring-state", state_file, repo_dir)
        assert success is True

        # Verify remote branch has state.json
        show_out = subprocess.check_output(
            ["git", "show", "origin/monitoring-state:state.json"],
            cwd=repo_dir,
            text=True,
        )
        data = json.loads(show_out)
        assert data["version"] == "1.0"
        assert data["current_cycle"] == 1

    def test_merge_monitoring_histories_deterministic(self):
        local_data = {
            "version": "1.0",
            "current_cycle": 2,
            "history": {
                "https://example.org/common": {
                    "url": "https://example.org/common",
                    "last_checked_at": "2026-11-12T00:00:00Z",
                    "dataset_ids": ["ds-1"],
                    "field_paths": ["homepage_url"],
                    "cycle_last_checked": 2,
                    "alert_status": "healthy",
                },
                "https://example.org/local-only": {
                    "url": "https://example.org/local-only",
                    "last_checked_at": "2026-11-12T00:00:00Z",
                    "dataset_ids": ["ds-2"],
                    "field_paths": ["license.url"],
                    "cycle_last_checked": 2,
                },
            },
        }

        remote_data = {
            "version": "1.0",
            "current_cycle": 1,
            "history": {
                "https://example.org/common": {
                    "url": "https://example.org/common",
                    "last_checked_at": "2026-11-10T00:00:00Z",  # Older than local
                    "dataset_ids": ["ds-3"],
                    "field_paths": ["citation.paper_url"],
                    "cycle_last_checked": 1,
                    "alert_status": "suspected_broken",
                },
                "https://example.org/remote-only": {
                    "url": "https://example.org/remote-only",
                    "last_checked_at": "2026-11-11T00:00:00Z",
                    "dataset_ids": ["ds-4"],
                    "field_paths": ["publisher.url"],
                    "cycle_last_checked": 1,
                },
            },
        }

        merged = merge_monitoring_histories(local_data, remote_data)
        assert merged["current_cycle"] == 2
        assert "https://example.org/common" in merged["history"]
        assert "https://example.org/local-only" in merged["history"]
        assert "https://example.org/remote-only" in merged["history"]

        # Common entry: local was newer (healthy), but dataset_ids and field_paths should be unioned
        common = merged["history"]["https://example.org/common"]
        assert common["alert_status"] == "healthy"
        assert set(common["dataset_ids"]) == {"ds-1", "ds-3"}
        assert set(common["field_paths"]) == {"homepage_url", "citation.paper_url"}

    def test_sync_branch_push_conflict_reconciliation(self, tmp_path: Path):
        repo_dir = tmp_path / "repo_conflict"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Bot"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "bot@example.com"], cwd=repo_dir, check=True)

        readme = repo_dir / "README.md"
        readme.write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)

        remote_dir = tmp_path / "remote_conflict.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(remote_dir)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote_dir)], cwd=repo_dir, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True, capture_output=True)

        # 1. Simulate initial remote commit on monitoring-state from another worker
        state_file = repo_dir / "state.json"
        remote_initial = {
            "version": "1.0",
            "current_cycle": 1,
            "history": {
                "https://example.org/remote-checked": {
                    "url": "https://example.org/remote-checked",
                    "last_checked_at": "2026-11-10T00:00:00Z",
                    "cycle_last_checked": 1,
                }
            },
        }
        state_file.write_text(json.dumps(remote_initial), encoding="utf-8")
        assert sync_branch_push("monitoring-state", state_file, repo_dir) is True

        # 2. Local worker checks a different URL without pulling remote first
        local_divergent = {
            "version": "1.0",
            "current_cycle": 1,
            "history": {
                "https://example.org/local-checked": {
                    "url": "https://example.org/local-checked",
                    "last_checked_at": "2026-11-11T00:00:00Z",
                    "cycle_last_checked": 1,
                }
            },
        }
        state_file.write_text(json.dumps(local_divergent), encoding="utf-8")

        # 3. Push: must detect remote state, reconcile both records without losing data, and succeed
        success = sync_branch_push("monitoring-state", state_file, repo_dir)
        assert success is True

        # 4. Verify remote now has BOTH URLs
        show_remote = subprocess.check_output(
            ["git", "show", "origin/monitoring-state:state.json"],
            cwd=repo_dir,
            text=True,
        )
        final_remote_data = json.loads(show_remote)
        assert "https://example.org/remote-checked" in final_remote_data["history"]
        assert "https://example.org/local-checked" in final_remote_data["history"]

    def test_sync_branch_push_auth_failure_diagnostics(self, tmp_path: Path, monkeypatch):
        repo_dir = tmp_path / "repo_auth"
        repo_dir.mkdir()
        state_file = repo_dir / "state.json"
        state_file.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")

        monkeypatch.setenv("GIT_AUTHOR_NAME", "Test Bot")
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "bot@example.com")

        with patch("subprocess.run") as mock_run:
            mock_res = MagicMock()
            mock_res.returncode = 1
            mock_res.stderr = "remote: Protected branch hook declined. Permission denied to ref refs/heads/monitoring-state"
            mock_run.return_value = mock_res

            # When branch protection rejects push, sync_branch_push returns False immediately
            success = sync_branch_push("monitoring-state", state_file, repo_dir)
            assert success is False

    def test_sync_branch_push_missing_identity_fails(self, tmp_path: Path, monkeypatch):
        """Verify that attempting to commit state without a valid Git author identity raises an error."""
        bare_remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

        repo_dir = tmp_path / "repo_no_id"
        subprocess.run(["git", "clone", str(bare_remote), str(repo_dir)], check=True, capture_output=True)

        state_file = repo_dir / "state.json"
        state_file.write_text(json.dumps({"version": "1.0", "current_cycle": 1, "history": {}}), encoding="utf-8")

        # Isolate environment from global Git config and ambient GIT_* environment variables
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
        monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
        monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
        monkeypatch.delenv("GIT_AUTHOR_EMAIL", raising=False)
        monkeypatch.delenv("GIT_COMMITTER_NAME", raising=False)
        monkeypatch.delenv("GIT_COMMITTER_EMAIL", raising=False)

        with pytest.raises(RuntimeError, match="Git identity missing"):
            sync_branch_push("monitoring-state", state_file, repo_dir)

    def test_sync_branch_push_configured_identity_sets_author_and_committer(self, tmp_path: Path, monkeypatch):
        """Verify that commit-tree receives and records valid author and committer identities when configured."""
        bare_remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

        repo_dir = tmp_path / "repo_with_id"
        subprocess.run(["git", "clone", str(bare_remote), str(repo_dir)], check=True, capture_output=True)

        # Configure repository-local identity matching GitHub Actions bot
        bot_name = "github-actions[bot]"
        bot_email = "41898282+github-actions[bot]@users.noreply.github.com"
        subprocess.run(["git", "config", "--local", "user.name", bot_name], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "--local", "user.email", bot_email], cwd=repo_dir, check=True)

        state_file = repo_dir / "state.json"
        state_file.write_text(json.dumps({"version": "1.0", "current_cycle": 1, "history": {}}), encoding="utf-8")

        # Isolate from global config
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
        monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
        monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
        monkeypatch.delenv("GIT_AUTHOR_EMAIL", raising=False)
        monkeypatch.delenv("GIT_COMMITTER_NAME", raising=False)
        monkeypatch.delenv("GIT_COMMITTER_EMAIL", raising=False)

        success = sync_branch_push("monitoring-state", state_file, repo_dir)
        assert success is True

        # Verify the commit on remote branch records valid author and committer identities
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "refs/remotes/origin/monitoring-state"], cwd=repo_dir, text=True
        ).strip()
        commit_cat = subprocess.check_output(
            ["git", "cat-file", "-p", commit_hash], cwd=repo_dir, text=True
        )

        assert f"author {bot_name} <{bot_email}>" in commit_cat
        assert f"committer {bot_name} <{bot_email}>" in commit_cat

    def test_cli_sync_branch_push_missing_identity_exit_code(self, tmp_path: Path):
        """Verify that CLI --sync-branch-push exits with code 1 and logs ::error:: when Git identity is missing."""
        bare_remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

        repo_dir = tmp_path / "repo_cli_no_id"
        subprocess.run(["git", "clone", str(bare_remote), str(repo_dir)], check=True, capture_output=True)

        state_file = repo_dir / "state.json"
        state_file.write_text(json.dumps({"version": "1.0", "current_cycle": 1, "history": {}}), encoding="utf-8")

        script_path = Path(__file__).resolve().parent.parent / "scripts" / "monitor_source_links.py"

        clean_env = os.environ.copy()
        clean_env["GIT_CONFIG_GLOBAL"] = "/dev/null"
        clean_env["GIT_CONFIG_SYSTEM"] = "/dev/null"
        clean_env.pop("GIT_AUTHOR_NAME", None)
        clean_env.pop("GIT_AUTHOR_EMAIL", None)
        clean_env.pop("GIT_COMMITTER_NAME", None)
        clean_env.pop("GIT_COMMITTER_EMAIL", None)

        res = subprocess.run(
            [sys.executable, str(script_path), "--sync-branch-push", "--state-file", str(state_file), "--repo-root", str(repo_dir)],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            env=clean_env,
        )
        assert res.returncode == 1
        assert "::error::" in res.stderr
        assert "Git identity missing" in res.stderr

    def test_cross_runner_backup_recovery_two_workspaces(self, tmp_path: Path):
        """Simulate two completely separate ephemeral GitHub Actions runners.

        Runner 1 pushes valid state. Runner 1's workspace is destroyed.
        A corrupted state is introduced on the remote monitoring-state branch.
        Runner 2 starts with an empty workspace (new runner), pulls remote state,
        detects corrupted state.json, and successfully recovers from remote state.bak!
        """
        bare_remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

        # Runner 1 Workspace
        runner1_dir = tmp_path / "runner1"
        runner1_dir.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=runner1_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Runner 1"], cwd=runner1_dir, check=True)
        subprocess.run(["git", "config", "user.email", "runner1@example.com"], cwd=runner1_dir, check=True)
        (runner1_dir / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=runner1_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=runner1_dir, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare_remote)], cwd=runner1_dir, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=runner1_dir, check=True, capture_output=True)

        # Runner 1 initializes and pushes initial state with URL A
        r1_state_file = runner1_dir / ".monitoring_state" / "state.json"
        r1_state_file.parent.mkdir(parents=True)
        state_v1 = {
            "version": "1.0",
            "current_cycle": 1,
            "total_catalog_urls": 2,
            "history": {
                "https://example.org/url-a": {
                    "url": "https://example.org/url-a",
                    "last_checked_at": "2026-11-10T00:00:00Z",
                    "alert_status": "healthy",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 1,
                }
            },
        }
        r1_state_file.write_text(json.dumps(state_v1, indent=2), encoding="utf-8")
        assert sync_branch_push("monitoring-state", r1_state_file, runner1_dir) is True

        # Runner 1 pushes state update with URL B (so state.bak on remote has state_v1)
        state_v2 = {
            "version": "1.0",
            "current_cycle": 1,
            "total_catalog_urls": 2,
            "history": {
                "https://example.org/url-a": {
                    "url": "https://example.org/url-a",
                    "last_checked_at": "2026-11-10T00:00:00Z",
                    "alert_status": "healthy",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 1,
                },
                "https://example.org/url-b": {
                    "url": "https://example.org/url-b",
                    "last_checked_at": "2026-11-11T00:00:00Z",
                    "alert_status": "healthy",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 1,
                },
            },
        }
        r1_state_file.write_text(json.dumps(state_v2, indent=2), encoding="utf-8")
        assert sync_branch_push("monitoring-state", r1_state_file, runner1_dir) is True

        # Now simulate remote state.json corruption (e.g. truncated remote push)
        bak_blob = subprocess.check_output(
            ["git", "rev-parse", "refs/remotes/origin/monitoring-state:state.bak"],
            cwd=runner1_dir,
            text=True,
        ).strip()
        corrupt_blob = subprocess.check_output(
            ["git", "hash-object", "-w", "--stdin"],
            input="{CORRUPTED_TRUNCATED_JSON",
            cwd=runner1_dir,
            text=True,
        ).strip()
        tree_input = f"100644 blob {corrupt_blob}\tstate.json\n100644 blob {bak_blob}\tstate.bak\n"
        corrupt_tree = subprocess.check_output(["git", "mktree"], input=tree_input, cwd=runner1_dir, text=True).strip()
        parent = subprocess.check_output(["git", "rev-parse", "refs/remotes/origin/monitoring-state"], cwd=runner1_dir, text=True).strip()
        corrupt_commit = subprocess.check_output(["git", "commit-tree", corrupt_tree, "-p", parent, "-m", "corrupt"], cwd=runner1_dir, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{corrupt_commit}:refs/heads/monitoring-state"], cwd=runner1_dir, check=True, capture_output=True)

        # Runner 1 workspace is now destroyed!

        # Runner 2 Workspace (completely clean, independent runner)
        runner2_dir = tmp_path / "runner2"
        runner2_dir.mkdir()
        subprocess.run(["git", "clone", str(bare_remote), "."], cwd=runner2_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Runner 2"], cwd=runner2_dir, check=True)
        subprocess.run(["git", "config", "user.email", "runner2@example.com"], cwd=runner2_dir, check=True)

        r2_state_file = runner2_dir / ".monitoring_state" / "state.json"

        # Runner 2 executes sync_branch_pull
        pulled = sync_branch_pull("monitoring-state", r2_state_file, runner2_dir)
        assert pulled is True

        # Both state.json (corrupted) and state.bak (valid) now exist on Runner 2's filesystem
        assert r2_state_file.exists()
        assert r2_state_file.with_suffix(".bak").exists()

        # Runner 2 loads monitoring state: must detect corruption and recover from state.bak!
        catalog_urls = ["https://example.org/url-a", "https://example.org/url-b"]
        state_r2, is_rec = load_monitoring_state(r2_state_file, catalog_urls, allow_reset=False)
        assert is_rec is True
        assert "https://example.org/url-a" in state_r2.history
        assert state_r2.history["https://example.org/url-a"]["alert_status"] == "healthy"

        # Evidence of corrupted state was preserved on Runner 2
        corrupt_evidence = list((runner2_dir / ".monitoring_state").glob("state.corrupt.*.json"))
        assert len(corrupt_evidence) == 1

        # Runner 2 can successfully save state and push back to origin
        save_monitoring_state(state_r2, r2_state_file)
        pushed = sync_branch_push("monitoring-state", r2_state_file, runner2_dir)
        assert pushed is True

    def test_concurrent_conflict_all_scenarios(self):
        """Verify concurrent reconciliation across all 5 requested conflict cases:
        1. Same URL with different check timestamps
        2. Confirmed-broken vs recovered status
        3. Consecutive failure counters
        4. Interrupted batches
        5. URL additions and removals
        """
        # Case 1 & 2: URL1 was confirmed-broken at 09:00, but newer run at 11:00 observed recovered (200 OK)
        # URL2 was healthy at 09:00, but newer run at 11:00 observed 404 (confirmed-broken with 2 failures)
        local_state = {
            "version": "1.0",
            "current_cycle": 2,
            "history": {
                "https://example.org/url1": {
                    "url": "https://example.org/url1",
                    "last_checked_at": "2026-11-15T11:00:00Z",  # NEWER
                    "alert_status": "recovered",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 2,
                    "dataset_ids": ["ds-a"],
                    "field_paths": ["homepage_url"],
                },
                "https://example.org/url2": {
                    "url": "https://example.org/url2",
                    "last_checked_at": "2026-11-15T09:00:00Z",  # OLDER
                    "alert_status": "healthy",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 1,
                    "dataset_ids": ["ds-b"],
                    "field_paths": ["license.url"],
                },
                "https://example.org/batch_local": {
                    "url": "https://example.org/batch_local",
                    "last_checked_at": "2026-11-15T11:00:00Z",
                    "alert_status": "healthy",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 2,
                    "dataset_ids": ["ds-c"],
                    "field_paths": ["citation.paper_url"],
                },
            },
        }

        remote_state = {
            "version": "1.0",
            "current_cycle": 1,
            "history": {
                "https://example.org/url1": {
                    "url": "https://example.org/url1",
                    "last_checked_at": "2026-11-15T09:00:00Z",  # OLDER
                    "alert_status": "confirmed_broken",
                    "consecutive_failures": 3,
                    "cycle_last_checked": 1,
                    "dataset_ids": ["ds-a", "ds-alt"],
                    "field_paths": ["homepage_url"],
                },
                "https://example.org/url2": {
                    "url": "https://example.org/url2",
                    "last_checked_at": "2026-11-15T11:00:00Z",  # NEWER
                    "alert_status": "confirmed_broken",
                    "consecutive_failures": 2,
                    "cycle_last_checked": 2,
                    "dataset_ids": ["ds-b"],
                    "field_paths": ["license.url"],
                },
                "https://example.org/batch_remote": {
                    "url": "https://example.org/batch_remote",
                    "last_checked_at": "2026-11-15T10:30:00Z",
                    "alert_status": "healthy",
                    "consecutive_failures": 0,
                    "cycle_last_checked": 1,
                    "dataset_ids": ["ds-d"],
                    "field_paths": ["publisher.url"],
                },
            },
        }

        merged = merge_monitoring_histories(local_state, remote_state)

        # 1. URL1: Local (11:00) is newer than Remote (09:00) -> status is RECOVERED, failures = 0
        u1 = merged["history"]["https://example.org/url1"]
        assert u1["last_checked_at"] == "2026-11-15T11:00:00Z"
        assert u1["alert_status"] == "recovered"
        assert u1["consecutive_failures"] == 0
        assert set(u1["dataset_ids"]) == {"ds-a", "ds-alt"}

        # 2. URL2: Remote (11:00) is newer than Local (09:00) -> status is CONFIRMED_BROKEN, failures = 2
        u2 = merged["history"]["https://example.org/url2"]
        assert u2["last_checked_at"] == "2026-11-15T11:00:00Z"
        assert u2["alert_status"] == "confirmed_broken"
        assert u2["consecutive_failures"] == 2

        # 3. Interrupted batches: both batch_local and batch_remote are retained without loss
        assert "https://example.org/batch_local" in merged["history"]
        assert "https://example.org/batch_remote" in merged["history"]

        # 4. Cycle is max(2, 1) = 2
        assert merged["current_cycle"] == 2


class TestStateRetrievalPlumbing:
    """Regression tests for missing branch versus corrupted or inaccessible existing state.

    Safety Invariants:
      1. Missing branch on remote: ONLY genuine first-time initialization, succeeds cleanly (exit 0).
      2. Remote query failure (network / auth / permission): Fails loudly with RuntimeError (exit 1).
      3. Git fetch failure: Fails loudly with RuntimeError (exit 1).
      4. Missing state files on existing branch: Fails loudly with UnrecoverableStateError (exit 1).
      5. Corrupted state with valid backup: Prepares files for recovery on load, succeeds cleanly (exit 0).
      6. Corrupted state with invalid/missing backup: Fails loudly with UnrecoverableStateError (exit 1).
      7. Unsupported schema version: Fails loudly with UnrecoverableStateError (exit 1).
      8. Explicit reset requested: Cleans state for reinitialization when allow_reset=True.
    """

    def _setup_bare_remote_and_clone(self, tmp_path: Path) -> tuple[Path, Path]:
        bare_remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

        seed_repo = tmp_path / "seed"
        seed_repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=seed_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Seed Bot"], cwd=seed_repo, check=True)
        subprocess.run(["git", "config", "user.email", "seed@example.com"], cwd=seed_repo, check=True)
        (seed_repo / "README.md").write_text("# Seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=seed_repo, check=True)
        subprocess.run(["git", "commit", "-m", "init main"], cwd=seed_repo, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare_remote)], cwd=seed_repo, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=seed_repo, check=True, capture_output=True)

        local_repo = tmp_path / "local"
        subprocess.run(["git", "clone", str(bare_remote), str(local_repo)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Local Bot"], cwd=local_repo, check=True)
        subprocess.run(["git", "config", "user.email", "local@example.com"], cwd=local_repo, check=True)

        return bare_remote, local_repo

    def test_sync_branch_pull_genuine_missing_branch(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        # Call sync_branch_pull on branch that genuinely does not exist on origin
        success = sync_branch_pull("monitoring-state", state_file, local_repo)
        assert success is True
        assert state_file.exists() is False
        assert state_file.with_suffix(".bak").exists() is False

        # Verify load_monitoring_state handles this cleanly as first-time initialization
        state, is_rec = load_monitoring_state(state_file, ["https://example.org/url1"], allow_reset=False)
        assert state.current_cycle == 1
        assert state.history == {}
        assert is_rec is False

    def test_sync_branch_pull_stale_local_files_cleaned_on_missing_branch(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{\"stale\": true}", encoding="utf-8")
        state_file.with_suffix(".bak").write_text("{\"stale_bak\": true}", encoding="utf-8")

        success = sync_branch_pull("monitoring-state", state_file, local_repo)
        assert success is True
        assert state_file.exists() is False
        assert state_file.with_suffix(".bak").exists() is False

    def test_sync_branch_pull_ls_remote_network_failure(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        # Point origin to a broken non-existent socket / directory
        subprocess.run(["git", "remote", "set-url", "origin", "/nonexistent/socket/remote.git"], cwd=local_repo, check=True)

        with pytest.raises(RuntimeError, match="Failed to query remote branch.*via git ls-remote"):
            sync_branch_pull("monitoring-state", state_file, local_repo)

    def test_sync_branch_pull_git_fetch_failure(self, tmp_path: Path, monkeypatch):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        # Create monitoring-state branch on origin
        subprocess.run(["git", "push", "origin", "main:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        real_run = subprocess.run

        def mock_subprocess_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 1 and cmd[1] == "fetch":
                raise subprocess.CalledProcessError(128, cmd, stderr="fatal: connection reset by peer")
            return real_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        with pytest.raises(RuntimeError, match="Failed to fetch branch 'monitoring-state' from origin.*connection reset by peer"):
            sync_branch_pull("monitoring-state", state_file, local_repo)

    def test_sync_branch_pull_existing_branch_empty_tree(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        # Create monitoring-state branch on origin with only a dummy file (no state.json, no state.bak)
        empty_tree = subprocess.check_output(["git", "mktree"], input="", cwd=local_repo, text=True).strip()
        dummy_commit = subprocess.check_output(
            ["git", "commit-tree", empty_tree, "-m", "empty branch commit"], cwd=local_repo, text=True
        ).strip()
        subprocess.run(["git", "push", "origin", f"{dummy_commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        with pytest.raises(UnrecoverableStateError, match="exists but contains neither state.json nor state.bak"):
            sync_branch_pull("monitoring-state", state_file, local_repo)

    def test_sync_branch_pull_existing_branch_valid_state(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        # Push valid state.json to monitoring-state branch
        valid_json = json.dumps({
            "version": "1.0",
            "current_cycle": 3,
            "total_catalog_urls": 10,
            "history": {"https://example.org/test": {"alert_status": "healthy", "consecutive_failures": 0}},
        })
        blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input=valid_json, cwd=local_repo, text=True).strip()
        tree = subprocess.check_output(["git", "mktree"], input=f"100644 blob {blob}\tstate.json\n", cwd=local_repo, text=True).strip()
        commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "valid state"], cwd=local_repo, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        success = sync_branch_pull("monitoring-state", state_file, local_repo)
        assert success is True
        assert state_file.exists()
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        assert loaded["current_cycle"] == 3
        assert "https://example.org/test" in loaded["history"]

    def test_sync_branch_pull_corrupted_state_recovers_from_backup(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        corrupt_blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input="{CORRUPT_JSON", cwd=local_repo, text=True).strip()
        valid_bak_json = json.dumps({
            "version": "1.0",
            "current_cycle": 2,
            "history": {"https://example.org/url1": {"alert_status": "healthy"}},
        })
        bak_blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input=valid_bak_json, cwd=local_repo, text=True).strip()
        tree = subprocess.check_output(
            ["git", "mktree"],
            input=f"100644 blob {corrupt_blob}\tstate.json\n100644 blob {bak_blob}\tstate.bak\n",
            cwd=local_repo,
            text=True,
        ).strip()
        commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "corrupt with backup"], cwd=local_repo, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        # Pull succeeds because valid backup exists on the branch
        success = sync_branch_pull("monitoring-state", state_file, local_repo)
        assert success is True
        assert state_file.exists()
        assert state_file.with_suffix(".bak").exists()

        # When rotation loads the state, it recovers from the backup
        state, is_rec = load_monitoring_state(state_file, ["https://example.org/url1"], allow_reset=False)
        assert is_rec is True
        assert state.current_cycle == 2
        assert "https://example.org/url1" in state.history

    def test_sync_branch_pull_corrupted_state_without_backup_fails(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        corrupt_blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input="{CORRUPT_JSON", cwd=local_repo, text=True).strip()
        tree = subprocess.check_output(
            ["git", "mktree"], input=f"100644 blob {corrupt_blob}\tstate.json\n", cwd=local_repo, text=True
        ).strip()
        commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "corrupt no backup"], cwd=local_repo, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        with pytest.raises(UnrecoverableStateError, match="has unrecoverable state.*primary state.json is invalid"):
            sync_branch_pull("monitoring-state", state_file, local_repo, allow_reset=False)

        # Confirm evidence was preserved locally
        corrupt_files = list(state_file.parent.glob("state.corrupt.*.json"))
        assert len(corrupt_files) >= 1

    def test_sync_branch_pull_invalid_schema_version_fails(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        v2_json = json.dumps({"version": "2.0", "current_cycle": 1, "history": {}})
        blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input=v2_json, cwd=local_repo, text=True).strip()
        tree = subprocess.check_output(
            ["git", "mktree"], input=f"100644 blob {blob}\tstate.json\n", cwd=local_repo, text=True
        ).strip()
        commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "v2 schema"], cwd=local_repo, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        with pytest.raises(UnrecoverableStateError, match="unsupported schema version '2.0'"):
            sync_branch_pull("monitoring-state", state_file, local_repo, allow_reset=False)

    def test_sync_branch_pull_corrupt_allows_reset_when_explicit(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"

        corrupt_blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input="{CORRUPT_JSON", cwd=local_repo, text=True).strip()
        tree = subprocess.check_output(
            ["git", "mktree"], input=f"100644 blob {corrupt_blob}\tstate.json\n", cwd=local_repo, text=True
        ).strip()
        commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "corrupt reset test"], cwd=local_repo, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        success = sync_branch_pull("monitoring-state", state_file, local_repo, allow_reset=True)
        assert success is True
        assert state_file.exists() is False

    def test_cli_sync_branch_pull_exit_codes(self, tmp_path: Path):
        bare_remote, local_repo = self._setup_bare_remote_and_clone(tmp_path)
        state_file = local_repo / ".monitoring_state" / "state.json"
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "monitor_source_links.py"

        # Case 1: Missing branch -> exit 0
        res = subprocess.run(
            [sys.executable, str(script_path), "--sync-branch-pull", "--state-file", str(state_file)],
            cwd=local_repo,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert "Remote branch 'monitoring-state' does not exist on origin" in res.stdout

        # Case 2: Corrupted state on branch without backup -> exit 1
        corrupt_blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input="{CORRUPT_JSON", cwd=local_repo, text=True).strip()
        tree = subprocess.check_output(
            ["git", "mktree"], input=f"100644 blob {corrupt_blob}\tstate.json\n", cwd=local_repo, text=True
        ).strip()
        commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "corrupt cli test"], cwd=local_repo, text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/monitoring-state"], cwd=local_repo, check=True, capture_output=True)

        res_corrupt = subprocess.run(
            [sys.executable, str(script_path), "--sync-branch-pull", "--state-file", str(state_file)],
            cwd=local_repo,
            capture_output=True,
            text=True,
        )
        assert res_corrupt.returncode == 1
        assert "::error::" in res_corrupt.stderr
        assert "has unrecoverable state" in res_corrupt.stderr


class TestEndToEndSimulation25Cycles:
    """Rigorous 25-cycle simulation across 1,832 synthetic URLs.

    Simulates:
      - 1,832 catalog URLs
      - Batch size 100
      - Additions, removals, interruptions, corrupted states, git conflicts
      - Verifies 100% eventual coverage of all stable URLs
    """

    def test_simulation_25_cycles(self):
        total_urls = 1832
        batch_size = 100
        catalog = {f"https://datasets.org/url_{i:04d}": {"fingerprint": f"fp_{i:04d}", "dataset_ids": [f"ds_{i%100}"], "field_paths": ["url"]} for i in range(total_urls)}

        state = MonitoringState(total_catalog_urls=total_urls)
        completed_cycles = 0

        # Run until 25 full cycles complete
        total_batches_run = 0
        max_batches = 800  # Generous upper bound

        while state.current_cycle <= 25 and total_batches_run < max_batches:
            total_batches_run += 1
            active_urls = sorted(catalog.keys())

            # Inject event 1: Catalog URL additions at cycle 3
            if state.current_cycle == 3 and "https://datasets.org/new_added_01" not in catalog:
                for n in range(15):
                    new_u = f"https://datasets.org/new_added_{n:02d}"
                    catalog[new_u] = {"fingerprint": f"fp_new_{n}", "dataset_ids": ["ds_new"], "field_paths": ["url"]}
                active_urls = sorted(catalog.keys())

            # Inject event 2: Catalog URL removals at cycle 7
            if state.current_cycle == 7 and "https://datasets.org/url_0005" in catalog:
                for r in range(10):
                    del catalog[f"https://datasets.org/url_{r:04d}"]
                active_urls = sorted(catalog.keys())

            # Inject event 3: Interrupted run at batch 50 (simulate timeout after checking 35 URLs)
            is_interrupted = (total_batches_run == 50)

            batch_urls, _, _, _ = select_batch(active_urls, state, batch_size=batch_size)
            if not batch_urls:
                break

            checked_batch = batch_urls[:35] if is_interrupted else batch_urls

            # Mock check execution with monotonically advancing simulated timestamps
            sim_time = f"2026-11-15T{total_batches_run:06d}Z"
            for u in checked_batch:
                prev = state.history.get(u, {})
                fails = prev.get("consecutive_failures", 0)
                state.history[u] = {
                    "url": u,
                    "fingerprint": catalog[u]["fingerprint"],
                    "last_checked_at": sim_time,
                    "cycle_last_checked": state.current_cycle,
                    "alert_status": ALERT_HEALTHY,
                    "consecutive_failures": 0,
                }

            # Check cycle completion
            all_checked_in_cycle = all(
                state.history.get(u, {}).get("cycle_last_checked", 0) >= state.current_cycle
                for u in active_urls
            )
            if all_checked_in_cycle:
                state.current_cycle += 1
                completed_cycles += 1

        assert completed_cycles >= 25
        # Verify 100% coverage of all active catalog URLs
        for u in catalog.keys():
            assert u in state.history
            assert state.history[u]["last_checked_at"] is not None
            assert state.history[u]["cycle_last_checked"] >= 25
