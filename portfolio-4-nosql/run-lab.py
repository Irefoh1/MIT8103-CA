"""Export P1 products and execute the MongoDB P4 catalogue lab.
Requires Python 3, Docker, a running Postgres container and mongo:8.0 image.
Creates a new isolated Mongo container: no network, ports, or host mounts.
Existing containers/databases are never reset. Evidence files are replaced.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--postgres-container',default='markethub-p1-validation')
parser.add_argument('--postgres-database',default='markethub_portfolio')
parser.add_argument('--mongo-container',default='markethub-p4-mongo')
parser.add_argument('--database',default='markethub_p4')
args=parser.parse_args()
OUT.mkdir(exist_ok=True)
def docker(*parts,stdin=None,timeout=120):
    p=subprocess.run(['docker',*parts],input=stdin,text=True,encoding='utf-8',
                     capture_output=True,timeout=timeout)
    if p.returncode: raise RuntimeError(p.stderr+p.stdout)
    return p.stdout

query="""SELECT COALESCE(json_agg(p ORDER BY p.sku),'[]'::json) FROM
 (SELECT p.product_id::text,p.sku,p.product_name AS name,p.description,
 p.current_price::text AS price,p.is_active AS active,c.category_id::text,c.category_name
 FROM markethub.products p JOIN markethub.categories c USING(category_id)
 WHERE p.sku IN ('KB-001','MS-001','NB-001')) p;"""
source=docker('exec','-i',args.postgres_container,'psql','-XAt','-v','ON_ERROR_STOP=1',
              '-U','postgres','-d',args.postgres_database,stdin=query)
products=json.loads(source)
if {p['sku'] for p in products}!={'KB-001','MS-001','NB-001'}:
    raise RuntimeError('Expected the three original P1 products; check the source database')
source_path=OUT/'postgresql-source-snapshot.json'
source_path.write_text(json.dumps(products,indent=2)+'\n',encoding='utf-8')
(OUT/'source-query.sql').write_text(query+'\n',encoding='utf-8')
print('Exported three real P1 catalogue records (read only).',flush=True)
# Docker fails on an existing name: deliberate protection, no rm/drop command.
docker('run','--detach','--name',args.mongo_container,'--network','none','mongo:8.0')
deadline=time.monotonic()+60
while True:
    try:
        docker('exec',args.mongo_container,'mongosh','--quiet','--eval',
               'if (!db.adminCommand({ping:1}).ok) quit(1);',timeout=10)
        break
    except (RuntimeError,subprocess.TimeoutExpired):
        if time.monotonic()>deadline: raise
        time.sleep(.5)
docker('cp',str(source_path),args.mongo_container+':/tmp/p4-source.json')
docker('cp',str(ROOT/'catalogue-lab.js'),args.mongo_container+':/tmp/catalogue-lab.js')
try:
    output=docker('exec','-e','P4_DATABASE='+args.database,args.mongo_container,
                  'mongosh','--quiet','--file','/tmp/catalogue-lab.js')
    (OUT/'execution.txt').write_text(output,encoding='utf-8')
    print(output,flush=True)
finally:
    # Preserve partial evidence too if a check fails; never present it as a pass.
    docker('cp',args.mongo_container+':/tmp/p4-output/.',str(OUT))
inspection=json.loads(docker('inspect',args.mongo_container))[0]
image=json.loads(docker('image','inspect',inspection['Image']))[0]
metadata={'container':args.mongo_container,'image_id':inspection['Image'],
          'repo_digests':image.get('RepoDigests',[]),'network_mode':inspection['HostConfig']['NetworkMode'],
          'published_ports':inspection['NetworkSettings']['Ports'],
          'source_postgres_database':args.postgres_database,
          'snapshot_is_read_only_export':True}
(OUT/'docker-environment.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
print('Evidence saved:',OUT)
