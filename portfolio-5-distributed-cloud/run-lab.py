"""P5: isolated PostgreSQL physical streaming replication lab.
Python standard library + Docker. Creates new resources; never deletes old ones.
Run from the repo root: python portfolio-5-distributed-cloud/run-lab.py
"""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix',default='markethub-p5')
args=parser.parse_args()
prefix=args.prefix
primary=prefix+'-primary'
standby=prefix+'-standby'
network=prefix+'-network'
volumes=[prefix+'-primary-data',prefix+'-standby-data']
IMAGE='postgres:18-alpine'
PGDATA='/var/lib/postgresql/18/docker'
DATABASE='markethub_portfolio'
OUT.mkdir(exist_ok=True)
transcript=[]
checks=[]

def docker(*parts,stdin=None,expect_success=True,timeout=90):
    result=subprocess.run(['docker',*parts],input=stdin,text=True,encoding='utf-8',
                          capture_output=True,timeout=timeout)
    transcript.append('$ docker '+' '.join(parts)+'\n'+
                      (('STDIN>\n'+stdin+'\n') if stdin is not None else '')+
                      result.stdout+result.stderr)
    if expect_success and result.returncode:
        raise RuntimeError(result.stderr+result.stdout)
    return result

def sql(container,statement,allow_failure=False):
    return docker('exec','-i',container,'psql','-XAt','-v','ON_ERROR_STOP=1',
                  '-v','VERBOSITY=verbose','-U','postgres','-d',DATABASE,
                  stdin=statement,expect_success=not allow_failure)
def scalar(container,statement):
    return sql(container,statement).stdout.strip()
def save(name,value):
    (OUT/name).write_text(value,encoding='utf-8')
def check(condition,message):
    if not condition: raise AssertionError(message)
    checks.append('PASS: '+message)
    print(checks[-1],flush=True)
def wait_for(probe,message,timeout=45):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if probe(): return
        time.sleep(.3)
    raise TimeoutError(message)
def ready(container):
    # Image initialization starts a temporary Unix-socket-only server. TCP
    # readiness waits for normal startup, avoiding its intentional shutdown.
    return docker('exec',container,'pg_isready','-h','127.0.0.1','-U','postgres','-d',DATABASE,
                  expect_success=False).returncode==0

# Protect all earlier lab resources, including completed runs of this activity.
for kind,name in [('container',primary),('container',standby),('network',network),
                  *[('volume',v) for v in volumes]]:
    if docker(kind,'inspect',name,expect_success=False).returncode==0:
        raise RuntimeError('Resource already exists; use a new --prefix: '+name)

try:
    docker('network','create','--internal',network)
    for volume in volumes: docker('volume','create',volume)
    docker('run','--detach','--name',primary,'--network',network,
           '-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_DB='+DATABASE,
           '-v',volumes[0]+':/var/lib/postgresql',IMAGE,
           '-c','wal_level=replica','-c','max_wal_senders=5',
           '-c','max_replication_slots=5','-c','max_slot_wal_keep_size=128MB')
    wait_for(lambda:ready(primary),'Primary did not become ready')
    for file in ['schema.sql','sample-data-and-checks.sql']:
        path=ROOT.parent/'portfolio-1-database-design'/file
        save(file+'.txt',sql(primary,path.read_text(encoding='utf-8')).stdout)
    sql(primary,'CREATE ROLE replicator WITH LOGIN REPLICATION;')
    # Lab-only trust access on a dedicated internal network, with no host ports.
    docker('exec',primary,'sh','-c',
           'echo "host replication replicator 0.0.0.0/0 trust" >> "$PGDATA/pg_hba.conf"')
    sql(primary,'SELECT pg_reload_conf();')
    # Seed a separate standby volume via base backup, then start it normally.
    backup_script='mkdir -p "$PGDATA" && chown postgres:postgres "$PGDATA" && chmod 700 "$PGDATA" && gosu postgres pg_basebackup -D "$PGDATA" -R -X stream -C -S p5_standby_slot --checkpoint=fast'
    docker('run','--rm','--network',network,'-e','PGDATA='+PGDATA,
           '-e','PGHOST='+primary,'-e','PGUSER=replicator',
           '-v',volumes[1]+':/var/lib/postgresql','--entrypoint','sh',IMAGE,'-c',backup_script)
    docker('run','--detach','--name',standby,'--network',network,
           '-v',volumes[1]+':/var/lib/postgresql',IMAGE)
    wait_for(lambda:ready(standby),'Standby did not become ready')
    check(scalar(primary,'SELECT pg_is_in_recovery();')=='f','Primary is writable and not in recovery')
    check(scalar(standby,'SELECT pg_is_in_recovery();')=='t','Standby is in recovery')
    wait_for(lambda:scalar(primary,"SELECT count(*) FROM pg_stat_replication WHERE state='streaming' AND sync_state='async';")=='1',
             'Asynchronous streaming connection not observed')
    check(True,'Primary reports one asynchronously streaming standby')
    check(scalar(standby,'SELECT count(*) FROM markethub.products;')=='3',
          'Base backup reproduces all three MarketHub products')
    check(scalar(standby,"SELECT sum(quantity*unit_price) FROM markethub.order_items;")=='35000.00',
          'Standby reproduces the original NGN 35000 order total')
    config="""SELECT name,setting,unit FROM pg_settings WHERE name IN
    ('wal_level','max_wal_senders','max_replication_slots','max_slot_wal_keep_size',
     'synchronous_commit','synchronous_standby_names','hot_standby') ORDER BY name;"""
    save('primary-settings.txt',sql(primary,config).stdout)
    save('standby-settings.txt',sql(standby,config).stdout)
    status="""SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn
    FROM pg_stat_replication; SELECT slot_name,slot_type,active,restart_lsn FROM pg_replication_slots;"""
    save('replication-before.txt',sql(primary,status).stdout)
    denied=sql(standby,"UPDATE markethub.products SET current_price=1 WHERE sku='KB-001';",allow_failure=True)
    save('standby-write-rejected.txt',denied.stdout+denied.stderr)
    check(denied.returncode!=0 and '25006' in denied.stderr,
          'Standby rejects writes with read-only SQLSTATE 25006')

    # Controlled replay pause shows a stale replica without pretending this is
    # a measured natural network lag or a full network partition.
    sql(standby,'SELECT pg_wal_replay_pause();')
    wait_for(lambda:scalar(standby,'SELECT pg_get_wal_replay_pause_state();')=='paused',
             'Replay did not pause')
    check(True,'Standby WAL replay is deliberately paused')
    old=scalar(standby,"SELECT current_price FROM markethub.products WHERE sku='KB-001';")
    check(old=='15000.00' and scalar(primary,"SELECT current_price FROM markethub.products WHERE sku='KB-001';")=='15000.00',
          'Before update, both copies have the original keyboard price')
    update="""BEGIN;
    UPDATE markethub.products SET current_price=18000 WHERE sku='KB-001';
    COMMIT;
    SELECT current_price FROM markethub.products WHERE sku='KB-001';
    SELECT pg_current_wal_lsn();"""
    save('committed-primary-update.txt',sql(primary,update).stdout)
    check(scalar(primary,"SELECT current_price FROM markethub.products WHERE sku='KB-001';")=='18000.00',
          'Primary commits NGN 18000 while standby replay is paused')
    stale=sql(standby,"""SELECT sku,current_price FROM markethub.products WHERE sku='KB-001';
    SELECT pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn(),pg_get_wal_replay_pause_state();""").stdout
    save('stale-standby-read.txt',stale)
    check('KB-001|15000.00' in stale,'Standby serves stale NGN 15000 after primary has committed NGN 18000')
    sql(standby,'SELECT pg_wal_replay_resume();')
    wait_for(lambda:scalar(standby,"SELECT current_price FROM markethub.products WHERE sku='KB-001';")=='18000.00',
             'Standby did not replay the committed change')
    check(True,'After replay resumes, standby converges to NGN 18000')
    check(scalar(standby,'SELECT sum(quantity*unit_price) FROM markethub.order_items;')=='35000.00',
          'Replicated catalogue price update preserves historical order total')
    save('replication-after-catchup.txt',sql(primary,status).stdout)
    save('standby-after-catchup.txt',sql(standby,"SELECT sku,current_price FROM markethub.products ORDER BY sku;").stdout)

    # Planned primary outage. No standby promotion is performed or claimed.
    docker('stop','--time','20',primary)
    stopped=docker('exec',primary,'pg_isready','-U','postgres',expect_success=False)
    save('primary-outage.txt',stopped.stdout+stopped.stderr)
    check(stopped.returncode!=0,'Original primary endpoint is unavailable while stopped')
    check(scalar(standby,"SELECT current_price FROM markethub.products WHERE sku='KB-001';")=='18000.00',
          'Standby continues serving the replicated catalogue during primary outage')
    check(scalar(standby,'SELECT pg_is_in_recovery();')=='t',
          'Standby remains read-only in recovery; no automatic failover occurs')
    denied=sql(standby,"UPDATE markethub.products SET current_price=19000 WHERE sku='KB-001';",allow_failure=True)
    save('outage-standby-write-rejected.txt',denied.stdout+denied.stderr)
    check(denied.returncode!=0 and '25006' in denied.stderr,
          'Primary outage does not make the standby accept checkout writes')
    docker('start',primary)
    wait_for(lambda:ready(primary),'Primary did not restart')
    wait_for(lambda:scalar(primary,"SELECT count(*) FROM pg_stat_replication WHERE state='streaming';")=='1',
             'Standby did not reconnect after restart')
    check(True,'Standby reconnects to the restarted original primary')
    sql(primary,"UPDATE markethub.products SET current_price=5500 WHERE sku='MS-001';")
    wait_for(lambda:scalar(standby,"SELECT current_price FROM markethub.products WHERE sku='MS-001';")=='5500.00',
             'Replication did not resume after primary restart')
    check(True,'Post-restart price change replicates to the standby')
    save('final-primary.txt',sql(primary,'SELECT sku,current_price FROM markethub.products ORDER BY sku;').stdout)
    save('final-standby.txt',sql(standby,'SELECT sku,current_price FROM markethub.products ORDER BY sku;').stdout)
    check((OUT/'final-primary.txt').read_text()==(OUT/'final-standby.txt').read_text(),
          'Final primary and standby catalogue results match exactly')
    save('replication-final.txt',sql(primary,status).stdout)
    metadata={'executed_at_utc':datetime.now(timezone.utc).isoformat(),
              'postgresql':scalar(primary,'SELECT version();'),
              'image':json.loads(docker('image','inspect',IMAGE).stdout)[0]['RepoDigests'],
              'primary':primary,'standby':standby,'network':network,'volumes':volumes,
              'local_lab_not_cloud_deployment':True}
    save('environment.json',json.dumps(metadata,indent=2)+'\n')
    resources=[json.loads(docker('container','inspect',c).stdout)[0] for c in [primary,standby]]
    save('docker-topology.json',json.dumps([{'name':r['Name'],
        'networks':list(r['NetworkSettings']['Networks']),
        'published_ports':r['NetworkSettings']['Ports'],
        'mounts':[{'name':m.get('Name'),'destination':m['Destination']} for m in r['Mounts']]}
        for r in resources],indent=2)+'\n')
    save('verification.txt','\n'.join(checks)+'\n')
    print('All',len(checks),'checks passed; evidence:',OUT,flush=True)
finally:
    save('execution-transcript.txt','\n\n'.join(transcript))
