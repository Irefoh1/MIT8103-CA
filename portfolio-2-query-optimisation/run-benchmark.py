"""Python standard library + Docker CLI. Creates a new DB; never resets one.
Run from any directory: python portfolio-2-query-optimisation/run-benchmark.py
Use --database NEW_NAME to repeat without overwriting a previous database.
Evidence files in this folder are replaced by the new run.
"""
import argparse
import csv
import io
import json
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--container', default='markethub-p1-validation')
parser.add_argument('--database', default='markethub_p2')
args = parser.parse_args()
OUT = ROOT / 'evidence'
OUT.mkdir(exist_ok=True)

def docker(*parts, stdin=None):
    result = subprocess.run(['docker', 'exec', '-i', args.container, *parts],
                            input=stdin, text=True, encoding='utf-8', capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

def sql(statement, csv_mode=False):
    flags = ['--csv'] if csv_mode else ['-A', '-t']
    return docker('psql','-X','-v','ON_ERROR_STOP=1','-U','postgres',
                  '-d',args.database,*flags,
                  stdin="SET timezone='UTC'; SET jit=off; SET max_parallel_workers_per_gather=0;\n"+statement)

def clean(output):
    # psql prints a command tag for each session SET before query data.
    return '\n'.join(line for line in output.splitlines() if line != 'SET')+'\n'

# createdb fails if the database exists; intentional protection of prior work.
docker('createdb','-U','postgres',args.database)
for path in [ROOT.parent/'portfolio-1-database-design'/'schema.sql', ROOT/'seed.sql']:
    (OUT/(path.stem+'-execution.txt')).write_text(sql(path.read_text()), encoding='utf-8')
metadata = clean(sql("SELECT version(); SHOW shared_buffers; SHOW work_mem; SHOW effective_cache_size;"))
metadata += clean(sql("SELECT 'customers',count(*) FROM markethub.customers UNION ALL SELECT 'products',count(*) FROM markethub.products UNION ALL SELECT 'orders',count(*) FROM markethub.orders UNION ALL SELECT 'order_items',count(*) FROM markethub.order_items UNION ALL SELECT 'payment_attempts',count(*) FROM markethub.payment_attempts;"))
metadata += docker('sh','-c','cat /sys/fs/cgroup/cpu.max; cat /sys/fs/cgroup/memory.max')
(OUT/'environment.txt').write_text(datetime.now(timezone.utc).isoformat()+'\n'+metadata,encoding='utf-8')
queries = {p.stem:p.read_text() for p in sorted((ROOT/'queries').glob('*.sql'))}
measurements = {}
results = {}
for phase in ['before','after']:
    if phase == 'after':
        (OUT/'index-creation.txt').write_text(sql((ROOT/'optimise.sql').read_text()),encoding='utf-8')
    for name, query in queries.items():
        result = clean(sql(query, csv_mode=True))
        (OUT/f'{phase}-{name}-results.csv').write_text(result,encoding='utf-8')
        if phase == 'after' and result != results[name]:
            raise AssertionError(f'Results changed for {name}')
        results[name] = result
        explain = 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+query
        sql(explain)  # One discarded warm-up per phase and query.
        runs = [json.loads(clean(sql(explain)))[0] for _ in range(5)]
        (OUT/f'{phase}-{name}-plans.json').write_text(json.dumps(runs,indent=2),encoding='utf-8')
        (OUT/f'{phase}-{name}-plan.txt').write_text(clean(sql('EXPLAIN (ANALYZE, BUFFERS) '+query)),encoding='utf-8')
        measurements[phase,name] = runs
        print(phase,name,'median ms',statistics.median(r['Execution Time'] for r in runs),flush=True)
rows=[]
for name in queries:
    b,a = [statistics.median(r['Execution Time'] for r in measurements[phase,name]) for phase in ['before','after']]
    rows.append([name,b,a,round(b/a,2),round((b-a)/b*100,2)])
with (OUT/'timing-summary.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['query','before_median_ms','after_median_ms','speedup','reduction_percent']); w.writerows(rows)
(OUT/'index-sizes.csv').write_text(clean(sql("SELECT indexrelname,pg_relation_size(indexrelid) AS bytes FROM pg_stat_user_indexes WHERE schemaname='markethub' ORDER BY indexrelname;",csv_mode=True)),encoding='utf-8')
(OUT/'verification.txt').write_text('PASS: all four ordered result sets identical before and after indexing.\nPASS: schema, seed, queries, index creation, and measured plans executed without SQL errors.\n',encoding='utf-8')
print('Completed; evidence:',OUT)
