# Operations

## Refresh and recovery

1. Obtain all source extracts and manifest as a consistent snapshot.
2. Run `python -m customer360 ingest <directory>` from the project environment.
3. Review row accounting, integration rejects and source fingerprints in Data quality.
4. Run `python -m customer360 report --cadence all` after successful publication.
5. Refresh the browser. The app queries the published warehouse on every interaction.

Do not run two writers concurrently. The CLI rebuilds in a new run directory and replaces the published warehouse only on success. Preserve the prior database via your storage snapshot/backup mechanism before production refresh. Failed staging runs remain available for inspection. A scheduled import should stop on nonzero exit status and never invoke reporting after failure.

For automation, configure Windows Task Scheduler or a deployment scheduler to run the above CLI under a service account with a fixed working directory and environment. Weekly reports end on the as-of day and include seven days; monthly/quarterly reports start at the calendar boundary. Pass `--as-of` explicitly for closed-period runs. Commands are provided; no recurring OS task has been installed. Default as-of is the source coverage end, so a stale source will produce a stale-period report rather than imply current data.

Keep raw and run directories according to your retention policy, and encrypt production backups. Log command exit status, run ID, source hashes, counts, build duration and coverage freshness. Restrict filesystem permissions to operators. Do not print accounts or passwords in logs.

## Access control

The demo is local-only and uses the admin role with authentication disabled. Real-data classification fails closed unless authentication is required. Enable it before any shared deployment:

```powershell
$env:C360_AUTH_REQUIRED = '1'
.\.venv\Scripts\python.exe -m customer360 password-hash
```

The password command prompts without echo and returns a salted PBKDF2-SHA256 hash with 600,000 iterations. Place that hash in a secret store as an account configuration:

```json
{"analyst-name":{"role":"analyst","password_hash":"<generated hash>"}}
```

Set `C360_USERS_JSON` from that secret store. Do not commit it. Accounts allow `viewer`, `analyst`, `admin`. Viewers browse analytic pages; analysts also export CSV/PDF; admins also inspect quality/provenance. Sessions expire after one hour. Five failed attempts trigger a 60-second session-level delay. This demo throttle can be reset by creating a new session and is **not** a production brute-force defense. Enforce rate limits and SSO at a trusted reverse proxy for deployment.

The app does not implement per-country row security, encryption at rest, MFA or a tamper-proof audit log. It should remain bound to `127.0.0.1` until a managed TLS/SSO gateway and role enforcement are configured and tested. UI gating does not restrict authorized filesystem users from reading DuckDB or the source files. Plotly and dataframe tools expose data already authorized for viewing; an export role gate is not a data-loss prevention boundary.

## Troubleshooting

- Missing warehouse: run `python -m customer360 demo` or import complete extracts.
- Missing columns: compare the file with `docs/DATA_DICTIONARY.md`; field names are exact.
- Conflicting source keys: resolve source versions upstream. The pipeline deliberately refuses to guess the latest row without an update timestamp.
- High orphan counts: verify identity crosswalks and coordinated snapshot timing.
- Database replacement denied: close long-lived readers or run the refresh in a controlled window, then retry.
- No forecast: choose at least 12 complete months.
- Empty marketing range: select a range containing at least one entire calendar month.
- Empty retention comparison: choose a later period with a full prior baseline.
- Blank charts: check date/country/channel filters and quarantined rows before treating this as a rendering error.

## Packaging

The submission archive excludes the local virtual environment, temporary renders and source-control internals. It includes source, documentation, generated fictional inputs, the demo warehouse and final reports/presentation. Rebuild from the seeded generator when transferring to another platform. No external service credentials are required.

