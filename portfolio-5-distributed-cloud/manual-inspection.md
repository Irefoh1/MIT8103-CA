# Inspect the completed replication lab

These commands use the successful recorded run prefix, markethub-p5-verified. Substitute your prefix for another run. They inspect the lab without changing product data or replication configuration.

## Roles of the two servers

```powershell
docker exec markethub-p5-verified-primary psql -X -U postgres -d markethub_portfolio -c 'SELECT pg_is_in_recovery();'
docker exec markethub-p5-verified-standby psql -X -U postgres -d markethub_portfolio -c 'SELECT pg_is_in_recovery();'
```

The primary returns false; the standby returns true.

## Streaming status and slot

```powershell
docker exec markethub-p5-verified-primary psql -X -U postgres -d markethub_portfolio -c 'SELECT application_name,state,sync_state,sent_lsn,replay_lsn FROM pg_stat_replication;'
docker exec markethub-p5-verified-primary psql -X -U postgres -d markethub_portfolio -c 'SELECT slot_name,active,restart_lsn FROM pg_replication_slots;'
```

Look for streaming, async, and an active physical slot. LSNs change as WAL advances; do not expect the exact same values as the saved evidence.

## Compare the data

```powershell
docker exec markethub-p5-verified-primary psql -X -U postgres -d markethub_portfolio -c 'SELECT sku,current_price FROM markethub.products ORDER BY sku;'
docker exec markethub-p5-verified-standby psql -X -U postgres -d markethub_portfolio -c 'SELECT sku,current_price FROM markethub.products ORDER BY sku;'
```

After the successful run: keyboard NGN 18,000; mouse NGN 5,500; notebook NGN 2,000. The original order still totals NGN 35,000 because its purchase prices are independent historical facts.

## Inspect actual stale-read and outage evidence

Open `evidence/stale-standby-read.txt` next to `evidence/committed-primary-update.txt`: the former shows the old keyboard price while replay was paused; the latter shows the new committed price. Review `standby-write-rejected.txt` and `outage-standby-write-rejected.txt` for read-only errors. `primary-outage.txt` records the stopped endpoint, and `replication-final.txt` records the restored streaming connection.

Use the runner with a **new prefix** to reproduce the complete changing-state experiment. Do not pause replay or stop either server during another run. The lab leaves its resources running for inspection; stopping a container preserves its volume but affects the availability observations.
