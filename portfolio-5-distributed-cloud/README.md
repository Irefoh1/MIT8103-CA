# Portfolio 5: Distributed and Cloud Database Exercise

## Case study and objective

Continue the MarketHub e-commerce case study with a practical **PostgreSQL physical streaming replication lab**. A primary accepts writes; a hot standby replays its write-ahead log (WAL) and serves read-only queries. Test replication, deliberate stale reads, and read/write availability during a planned primary outage.

This is a local distributed-database exercise across two PostgreSQL servers in Docker. It is **not a cloud deployment**, automatic failover system, multi-host disaster-recovery installation, or sharded database. The assignment permits distributed/cloud discussion or setup; actual replication evidence is accompanied by cloud, consistency, availability, and sharding analysis.

## Files

| File | Purpose |
|---|---|
| [run-lab.py](run-lab.py) | Complete reproducible provisioning and test runner, using Python standard library and Docker |
| [architecture-and-analysis.md](architecture-and-analysis.md) | Topology, replication, consistency, availability, cloud mapping, and sharding tradeoffs |
| [manual-inspection.md](manual-inspection.md) | Read-only commands to inspect the completed lab |
| [evidence/](evidence/) | Actual settings, replication status, stale reads, rejected writes, outage/recovery, and final comparisons |

## Reproduce

Requirements: Python 3, running Docker engine, Docker access, and the existing `postgres:18-alpine` image (or pull it first). No Python database driver is needed. From the repository root:

```powershell
python portfolio-5-distributed-cloud/run-lab.py
```

The runner creates these **new** resources:

- Containers: `markethub-p5-primary`, `markethub-p5-standby`.
- Internal network: `markethub-p5-network`, without published host ports.
- Named volumes: `markethub-p5-primary-data`, `markethub-p5-standby-data`.
- Database: `markethub_portfolio`, with the unchanged P1 schema and seed loaded into the new primary.

No earlier portfolio database is reused, reset, or modified. The standby receives a physical base backup of this new primary. A dedicated LOGIN REPLICATION role and physical replication slot support streaming.

Existing resource names cause the runner to stop, rather than deleting or overwriting them. To repeat:

```powershell
python portfolio-5-distributed-cloud/run-lab.py --prefix markethub-p5-repeat
```

The repeat replaces this activity's local evidence files; preserve them first if you want both runs. Container/volume data stays in Docker, not GitHub. The containers are left running after success for inspection. Earlier failed/partial runs are also preserved for diagnosis, not silently deleted. Nothing is committed or pushed automatically.

## Replication configuration

The primary is started with `wal_level=replica`, `max_wal_senders=5`, `max_replication_slots=5`, and `max_slot_wal_keep_size=128MB`. A physical base backup uses `-R -X stream -C -S p5_standby_slot`; `-R` writes standby configuration and the signal file, `-X stream` includes required WAL, and the slot helps retain WAL needed by the standby. See the runner for exact commands and the evidence folder for observed settings/status.

This is asynchronous replication: `synchronous_standby_names` is empty, and the primary's COMMIT does not wait for standby replay. `synchronous_commit=on` alone does not make a standby synchronous when none is configured as a synchronous standby.

For this isolated exercise, database connections use trust authentication on a dedicated internal Docker network. Do not copy that authentication setup into a public or production deployment. A real deployment needs restricted network rules, credentials/certificates, TLS where appropriate, monitoring, and a tested recovery plan. Both containers share the same computer, so they do not provide independent host failure protection.

## Demonstrations

1. Confirm the primary is not in recovery, the standby is in recovery, and the primary reports asynchronous streaming.
2. Verify the standby contains three products and the original NGN 35,000 order.
3. Attempt a standby write and record SQLSTATE `25006` (read-only transaction).
4. Pause standby WAL replay, then commit a keyboard price change on the primary from NGN 15,000 to NGN 18,000.
5. Observe the old NGN 15,000 on the standby while the primary has committed NGN 18,000. This is a deliberately created stale read, not a measurement of ordinary replication latency or a simulated network partition.
6. Resume replay, wait for convergence, and verify the historical order total remains NGN 35,000.
7. Stop the original primary. Confirm its endpoint is unavailable while the standby still serves reads and rejects writes. No promotion or automatic failover occurs.
8. Restart the original primary, observe reconnection, commit a mouse price change to NGN 5,500, and confirm final catalogue equality.

## Evidence and submission

**Verified run:** All **19 checks passed** on 12 November 2026 (Africa/Lagos). Successful-run resources use prefix **`markethub-p5-verified`**, so the active servers are `markethub-p5-verified-primary` and `markethub-p5-verified-standby`. The original default-prefix resources belong to the initial startup-readiness development attempt; they are not the verified replication pair. The corrected runner checks TCP readiness to exclude PostgreSQL's temporary setup server. Use the successful prefix when inspecting the saved experiment.

`verification.txt` records the pass summary; `environment.json` identifies the actual server/image; `docker-topology.json` records separate resources and ports. Saved settings, replication status, rejected-write errors, stale and converged reads, and final results provide genuine technical evidence. Read the analysis and use the manual inspection guide to understand the outputs. Screenshots can supplement these files.

The exercise completes the practical fifth activity; the final 2–3 page LMS documentation is a separate remaining task. The final submission should include your individual reflection and references/AI-use declaration. A separate personal reflection per activity is not imposed here.

## Sources and AI-use record

Assessment source: MIT 8103 assignment brief, Portfolio 5 expected deliverables. Data/model source: existing MarketHub P1 SQL schema and synthetic sample. OpenAI Codex assisted with the lab runner, initial execution, analysis, and documentation. The student must review and understand the results and record personal verification/corrections honestly in the final declaration.
