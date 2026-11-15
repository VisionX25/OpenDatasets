# Automated Source-Link Health Monitoring

OpenDatasets implements a reproducible, zero-cost, serverless source-link monitoring system powered by GitHub Actions. The system continuously audits external dataset URLs across the catalog, detects broken links and domain migrations, maintains persistent rotation state across runs, and surfaces transparent, actionable health reports.

---

## 1. Architecture Overview

The monitoring subsystem is composed of decoupled components operating entirely within GitHub Actions and local execution environments:

```
+-------------------------------------------------------------+
|                     OpenDatasets Catalog                    |
|                   (data/datasets/*.json)                    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|             Extraction & Deduplication Engine               |
|            - 1,832 unique canonical URLs extracted         |
|            - Stable URL fingerprinting (SHA-256 / 16 hex)   |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|          Fair LRU Rotation & Batch Selection Engine         |
|            - Priority: Unchecked first, then oldest checked |
|            - Starvation-free, resilient to catalog changes  |
|            - Automatically prioritizes newly added URLs     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|            Persistent State Synchronization Engine          |
|        (monitoring-state branch via Git Plumbing)           |
|            - Isolated from main; zero code/metadata churn   |
|            - Atomic blob & tree creation (git hash-object)  |
|            - Conflict detection & retry with backoff        |
|            - 90-day workflow artifact archival fallback     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|       Hardened HTTP Probing Engine (SSRF Protected)         |
|            - SSRF Guard: loopback, RFC1918, metadata block  |
|            - Revalidates redirect destinations              |
|            - Thread-safe per-host rate limiter (locks)      |
|            - Respects HTTP 429 Retry-After header           |
|            - Bounded concurrency (5 worker threads)         |
|            - HEAD first -> Streaming GET fallback (<= 2KB)  |
|            - ZERO dataset binaries or raw files downloaded  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|           Conservative Multi-Run Alerting Policy            |
|            - 1st 404/410 -> suspected_broken                |
|            - 2nd 404/410 -> confirmed_broken (multi-run)    |
|            - 401 -> authentication_required (never dead)    |
|            - 403 / 429 / 5xx / Timeout -> transient/restr.  |
|            - Revival 200 -> recovered                       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                    Artifacts & Summaries                    |
|            - monitoring-report.json                         |
|            - monitoring-report.csv                          |
|            - monitoring-summary.md -> $GITHUB_STEP_SUMMARY  |
+-------------------------------------------------------------+
```

---

## 2. Weekly Monitoring Schedule

* **Workflow File:** [`.github/workflows/source-link-monitor.yml`](../.github/workflows/source-link-monitor.yml)
* **Schedule:** Every Sunday at `03:00 UTC` (`cron: '0 3 * * 0'`).
* **Trigger Support:** Manual execution via `workflow_dispatch`.

> [!NOTE]
> **Best-Effort Scheduling:**  
> GitHub Actions scheduled workflows run on a best-effort basis. During high-demand periods across GitHub-hosted runners, execution may experience queuing delays or occasional skipped intervals. The fair LRU rotation algorithm resumes from the exact least-recently-checked URLs regardless of when the next run executes.

---

## 3. Persistent State Architecture & Branch Isolation

To guarantee durable rotation continuity across weekly runs without risking eviction:

### Isolated `monitoring-state` Branch
State is stored on a dedicated orphan Git branch named `monitoring-state`, completely isolated from `main`.
* **Zero Catalog Pollution:** The working tree on `main` is never switched or dirtied. The workflow uses low-level git plumbing (`git hash-object`, `git mktree`, `git commit-tree`) to create commits containing only `state.json`.
* **Deterministic 3-Way History Reconciliation:** Before pushing, the sync utility checks `git ls-remote` and fetches `origin/monitoring-state`. If remote commits advanced concurrently, the sync engine fetches remote `state.json`, performs a 3-way merge of URL histories (`merge_monitoring_histories`) taking the newest `last_checked_at` timestamps and unioning dataset IDs, sets the new parent commit, and pushes forward. Zero history is lost.
* **Never Force-Push:** All push operations use standard forward updates (`git push origin <commit>:refs/heads/monitoring-state`). Force-pushing is strictly forbidden.
* **Dual-Tier Resilience:** In addition to the branch push, every workflow run uploads `.monitoring_state/state.json` and reports as a GitHub Actions artifact with 90-day retention.
* **Durable Persistence Guarantee:** Push failures (e.g. branch protection, token constraints, or exhausted retries) fail the persistence step with explicit diagnostics. Successful workflow runs guarantee durable persistence.

### Durable State Recovery Hierarchy & Versioning
To prevent silent data loss or history destruction:
1. **Primary State Loading:** Inspects `.monitoring_state/state.json`.
2. **Automatic Trusted Backup (`.bak`):** Every successful state save creates an atomic `.monitoring_state/state.bak` file. If `state.json` is missing or corrupted, the system automatically restores from `.bak` and continues without data loss.
3. **Corrupted State Evidence Preservation:** Any corrupted or unparseable state file is renamed to `state.corrupt.<timestamp>.json` as audit evidence.
4. **Explicit Operator Reset Gate:** If state is corrupted and no valid `.bak` backup exists, the system refuses to silently reset history. It aborts execution with `UnrecoverableStateError`. A human maintainer must inspect the preserved corrupt file or explicitly pass `--reset-state` (`INPUT_RESET_STATE=true`) to reinitialize.
5. **Schema Versioning:** The state file records `"version": "1.0"`. Only supported versions are loaded. Known legacy formats (`0.9`) are safely migrated. Unknown future versions (`2.0+`) are rejected with `UnrecoverableStateError` rather than silently overwritten.

### State Schema (`state.json`)
```json
{
  "version": "1.0",
  "updated_at": "2026-11-15T03:00:00Z",
  "current_cycle": 1,
  "total_catalog_urls": 1832,
  "batch_size_last_run": 100,
  "history": {
    "https://doi.org/10.1000/182": {
      "url": "https://doi.org/10.1000/182",
      "fingerprint": "a1b2c3d4e5f60718",
      "dataset_ids": ["example-dataset"],
      "field_paths": ["citation.paper_url"],
      "first_checked_at": "2026-11-15T03:00:00Z",
      "last_checked_at": "2026-11-15T03:00:00Z",
      "last_http_status": 200,
      "last_classification": "reachable",
      "final_redirect_target": "https://publisher.com/paper",
      "consecutive_failures": 0,
      "last_successful_check": "2026-11-15T03:00:00Z",
      "alert_status": "healthy",
      "cycle_last_checked": 1
    }
  }
}
```

### GitHub Token Permissions & Branch Protection Considerations
* **Workflow Permissions:** The workflow job declares `permissions: contents: write`, which is scoped exclusively to pushing updates to the `monitoring-state` branch.
* **Branch Protection Rulesets:** If repository settings enforce strict branch protection or require PR reviews on all branches, `github-actions[bot]` cannot push directly to `monitoring-state`.
  * *Recommended Configuration:* Maintain `main` as a protected branch, but exclude `monitoring-state` from branch protection rulesets, treating it as an automated machine-state storage ref.
  * *Fallback Behavior:* If branch push is blocked by repository policy, the workflow emits a clear warning annotation and preserves state in the 90-day workflow artifacts without crashing.

---

## 4. Fair LRU Batch Rotation & Starvation Prevention

The monitoring system rejects naive numeric indexing in favor of an **authenticated Least-Recently-Used (LRU) priority queue**:

$$\text{Priority Key}(u) = \begin{cases} (0,\, "",\, \text{fingerprint}(u)) & \text{if } u \text{ has never been checked} \\ (1,\, \text{last\_checked\_at}(u),\, \text{fingerprint}(u)) & \text{if } u \text{ has a check timestamp} \end{cases}$$

### Starvation Prevention & Edge Case Handling
1. **Newly Added URLs:** New URLs added to `data/datasets/*.json` have `last_checked_at = None`. They receive priority `0` and are automatically scheduled in the very next batch.
2. **Removed URLs:** If a dataset or reference is deleted from the catalog, its historical record is pruned from `state.history` during state loading, preventing memory accumulation.
3. **Interrupted or Skipped Runs:** If an execution reaches the maximum runtime limit (`--max-runtime-seconds`) or is executed in offline mode, unprobed URLs do **not** have their `last_checked_at` updated. They retain their high priority and are retried on the subsequent run.
4. **Cycle Advancement:** A monitoring cycle $C$ completes when **every** active catalog URL has been checked in cycle $\ge C$. The cycle counter then advances to $C + 1$.
5. **25-Cycle Simulation Verification:** Proven via `scripts/simulate_monitoring.py` and `tests/test_source_link_monitoring.py` with 100% catalog coverage across 25 cycles, zero starved URLs, and verified resilience during injected additions, deletions, and interrupted runs.

---

## 5. Security & Network Target Safety (SSRF & DNS Rebinding / TOCTOU Mitigation)

External dataset URLs are untrusted inputs that must be verified before connection attempts:

* **Restricted Target Filtering (`is_safe_public_url`):**
  * **Loopback:** `127.0.0.0/8`, `::1`, `localhost`, `*.localhost`.
  * **RFC 1918 Private Ranges:** `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
  * **Link-Local & Cloud Metadata:** `169.254.0.0/16` (`169.254.169.254`), `fe80::/10`, `metadata.google.internal`, `instance-data`.
  * **IPv6 Private:** Unique Local (`fc00::/7`).
  * **Multicast / Unspecified / Broadcast:** `224.0.0.0/4`, `ff00::/8`, `0.0.0.0/8`, `255.255.255.255`.
* **Connection-Time IP Validation (DNS Rebinding / TOCTOU Mitigation):**
  * Rather than relying solely on pre-check DNS queries that are decoupled from connection time (leaving a Time-Of-Check to Time-Of-Use window), the probing engine installs a custom connection factory (`create_safe_connection`) via `SafeHTTPConnection` and `SafeHTTPSConnection`.
  * The actual destination IP is resolved and verified immediately before `sock.connect()`. If an attacker-controlled domain rebinds from a public IP to an internal address (`127.0.0.1` or `169.254.169.254`), the socket connection is aborted with `SSRFSecurityError` before any TCP packet is transmitted.
* **Redirect Destination Revalidation:** When an HTTP 3xx redirect is observed, `NoRedirectHandler` prevents automatic following. The target `Location` header is resolved and re-audited against `is_safe_public_url` before issuing any follow-up request.
* **Credential Stripping:** Any URL embedding credentials (`http://user:pass@...`) has authentication information stripped to prevent credential leaks.

### Inherent Limitations of Standard Python `urllib` & Architecture Safeguards
1. **Coupled Resolution in Stock `urllib`:** By default, standard `urllib.request` couples DNS resolution directly to TCP connection creation without exposing an IP check hook. This is solved by subclassing `http.client.HTTPConnection` and `http.client.HTTPSConnection` to override `self._create_connection = create_safe_connection`.
2. **Redirect Autopilot in Stock Handlers:** Standard `urllib.request.HTTPRedirectHandler` automatically follows 3xx redirects across arbitrary domains and schemes. This is mitigated by `NoRedirectHandler`, which returns `None` to intercept the redirect and enforce destination validation.
3. **SNI and TLS Certificate Verification:** Standard TLS requires `server_hostname` to match the target certificate. By performing IP validation at the socket connection level, the original hostname is preserved in `HTTPSConnection.host`, ensuring full cryptographic TLS certificate and SAN/CN verification.
4. **Host OS Resolver Reliance:** Python `urllib` uses POSIX `getaddrinfo` via the host OS resolver (`/etc/resolv.conf`). It does not support native DNS-over-HTTPS (DoH) or DNSSEC out of the box. Bounded timeouts (`DEFAULT_TIMEOUT = 10.0s`) and strict IP validation minimize risks associated with compromised recursive resolvers.

---

## 6. Thread-Safe Per-Host Rate Limiting

To prevent overwhelming academic repositories or triggering denial-of-service protections:

* **Host Locking (`HostRateLimiter`):** A global coordinator manages dedicated `threading.Lock` instances per hostname. Concurrent worker threads querying the same domain (e.g. `doi.org` or `github.com`) are serialized.
* **Enforced Spacing:** A minimum inter-request delay (`DEFAULT_HOST_DELAY = 0.25s`) is enforced between consecutive queries to the same host, regardless of worker concurrency.
* **HTTP 429 `Retry-After` Handling:** When an upstream server issues a 429 response, the limiter parses the `Retry-After` header and applies a bounded backoff (capped between 0.5s and 10.0s).

---

## 7. Multi-Run Alerting Policy

```
[ New URL Check ]
       |
       +--> 200 / 204 / 206 / 3xx (Valid) ------> healthy (consecutive_failures = 0)
       |
       +--> 404 / 410 (Not Found)
       |         |
       |         +--> 1st observation -----------> suspected_broken (failures = 1)
       |         |
       |         +--> >=2 consecutive ----------> confirmed_broken (multi-run evidence)
       |
       +--> 401 Unauthorized ------------------> authentication_required (gated)
       |
       +--> 403 Forbidden ----------------------> restricted (anti-bot / WAF)
       |
       +--> 429 Too Many Requests --------------> rate_limited
       |
       +--> 5xx / Timeout / DNS / SSL ----------> transient_failure (not dead)
       |
       +--> Previously broken returns 200/3xx --> recovered (alert cleared)
```

### Scientific Integrity Notice
> [!IMPORTANT]
> **Automated 404 Responses vs. Scientific Availability:**  
> Two automated 404 responses do **NOT** prove scientific dataset removal. Academic institutions frequently reorganize URL paths, migrate lab servers, or change web frameworks without setting up 301 redirects. Maintainers must verify author homepages, check research portals, or contact publishers before removing or modifying catalog metadata. Automated monitoring provides early warning signals, not destructive mandates.

---

## 8. Hardened GitHub Actions Execution & Manual Dispatch

All manual inputs in `.github/workflows/source-link-monitor.yml` are passed exclusively via environment variables (`INPUT_BATCH_SIZE`, `INPUT_MAX_RUNTIME`, `INPUT_OFFLINE`, `INPUT_DRY_RUN`, `INPUT_RESET_STATE`), completely eliminating shell expansion or command injection vulnerabilities.

### Input Bounds & Validation
* `batch_size`: Validated integer between `1` and `250` (default `100`).
* `max_runtime`: Validated positive float between `10` and `1800` seconds (default `600`).
* `offline`: Boolean flag (`true`/`false`).
* `dry_run`: Boolean flag (`true`/`false`).
* `reset_state`: Boolean flag (`true`/`false`).

### Manual Workflow Dispatch
Maintainers can trigger runs via GitHub Actions UI with custom settings:
* Use `dry_run: true` to preview the upcoming batch of URLs without executing network requests or advancing state.
* Use `offline: true` to verify catalog metadata extraction and local state synchronization.
* Use `reset_state: true` to restart monitoring from cycle 1.

---

## 9. Offline Simulation Utility

Maintainers can verify the reliability and fairness of the rotation algorithm locally at any time:

```bash
# Run 25-cycle offline simulation across 1,832 synthetic URLs
python3 scripts/simulate_monitoring.py --cycles 25 --catalog-size 1832 --batch-size 100
```
This utility simulates catalog URL additions, deletions, runtime cutoffs, state corruptions, and git conflict retries, reporting 100% coverage and zero starvation.
