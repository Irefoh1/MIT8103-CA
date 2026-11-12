"""Reproducible P3 lab: Python standard library, Docker CLI, PostgreSQL.
Creates a new database, never resets an existing one. Evidence is overwritten.
"""
import argparse
import queue
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--container', default='markethub-p1-validation')
parser.add_argument('--database', default='markethub_p3')
args = parser.parse_args()
OUT = ROOT/'evidence'
OUT.mkdir(exist_ok=True)

def docker(*parts, stdin=None):
    r = subprocess.run(['docker','exec','-i',args.container,*parts],input=stdin,
                       text=True,encoding='utf-8',capture_output=True,timeout=90)
    if r.returncode:
        raise RuntimeError(r.stderr+r.stdout)
    return r.stdout+r.stderr

class Session:
    """A live psql backend; one execute call at a time on each session."""
    def __init__(self,name):
        self.name=name
        self.log=[]
        self.seq=0
        self.lines=queue.Queue()
        self.proc=subprocess.Popen(['docker','exec','-i',args.container,'psql',
            '-X','-qAt','-v','ON_ERROR_STOP=1','-U','postgres','-d',args.database],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',bufsize=1)
        def read():
            for line in self.proc.stdout:
                self.lines.put(line.rstrip('\n'))
            self.lines.put(None)
        threading.Thread(target=read,daemon=True).start()
        self.execute("SET application_name='"+name+"'; SET timezone='UTC'; "
                     "SET statement_timeout='20s'; SET lock_timeout='15s';")
    def execute(self,sql):
        self.seq+=1
        marker=f'__P3_END_{self.seq}__'
        self.log.append('\nSQL> '+sql)
        self.proc.stdin.write(sql+'\n\\echo '+marker+'\n')
        self.proc.stdin.flush()
        result=[]
        deadline=time.monotonic()+30
        while True:
            line=self.lines.get(timeout=max(.01,deadline-time.monotonic()))
            if line is None:
                raise RuntimeError(self.name+' ended: '+'\n'.join(result))
            if line==marker:
                break
            result.append(line)
        output='\n'.join(result)
        self.log.append(output)
        return output
    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.write('\\q\n')
            self.proc.stdin.flush()
            self.proc.wait(timeout=25)
        (OUT/(self.name+'.txt')).write_text('\n'.join(self.log),encoding='utf-8')

sessions=[]
checks=[]
def session(name):
    s=Session(name); sessions.append(s); return s
def check(condition,message):
    if not condition:
        raise AssertionError(message)
    checks.append('PASS: '+message)
    print(checks[-1],flush=True)
def scalar(s,sql):
    return s.execute(sql).strip()
def order_count(s):
    return int(scalar(s,'SELECT count(*) FROM markethub.orders;'))
def stock(s,p=1):
    return int(scalar(s,f'SELECT quantity_on_hand FROM markethub.inventory WHERE product_id={p};'))
def reset(s,quantity=1):
    # Restricted to this newly created P3 lab DB. Keep logs from prior cases.
    s.execute('BEGIN; DELETE FROM markethub.order_items; DELETE FROM markethub.orders; '
              f'UPDATE markethub.inventory SET quantity_on_hand={quantity}; COMMIT;')
def unsafe_order(customer):
    # Deliberately broken: stale absolute stock write, followed by an order.
    return f"""UPDATE markethub.inventory SET quantity_on_hand=0 WHERE product_id=1;
    WITH o AS (INSERT INTO markethub.orders(customer_id,status,delivery_recipient,
      delivery_address_line,delivery_city,delivery_state)
      VALUES({customer},'placed','Demo','1 Synthetic Street','Ikeja','Lagos') RETURNING order_id)
    INSERT INTO markethub.order_items(order_id,product_id,quantity,unit_price)
    SELECT order_id,1,1,15000 FROM o; COMMIT;"""
def async_execute(s,sql):
    result={}
    def run():
        try: result['output']=s.execute(sql)
        except BaseException as e: result['error']=e
    t=threading.Thread(target=run,daemon=True); t.start()
    return t,result
def wait_for_block(observer,blocked,blocker):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        evidence=observer.execute(f"""SELECT b.application_name,b.wait_event_type,
         a.application_name FROM pg_stat_activity b
         JOIN pg_stat_activity a ON a.pid=ANY(pg_blocking_pids(b.pid))
         WHERE b.application_name='{blocked}' AND a.application_name='{blocker}';""")
        # Activity and lock-manager observations can straddle a transition;
        # wait for both to report the blocked state, not a transient null event.
        if evidence.strip()==f'{blocked}|Lock|{blocker}':
            check(True,
                  'PostgreSQL reports the competing checkout blocked by the first transaction')
            return
        time.sleep(.1)
    raise AssertionError('Did not observe the expected row-lock wait')

docker('createdb','-U','postgres',args.database)
try:
    for path in [ROOT.parent/'portfolio-1-database-design'/'schema.sql',ROOT/'setup.sql',ROOT/'checkout.sql']:
        output=docker('psql','-X','-v','ON_ERROR_STOP=1','-U','postgres','-d',args.database,
                      stdin=path.read_text(encoding='utf-8'))
        (OUT/(path.stem+'-execution.txt')).write_text(output,encoding='utf-8')
    admin=session('p3-observer')
    (OUT/'environment.txt').write_text(datetime.now(timezone.utc).isoformat()+'\n'+
        admin.execute('SELECT version(); SHOW default_transaction_isolation;')+
        '\ncontainer='+args.container+'\ndatabase='+args.database+'\n',encoding='utf-8')

    # Commit and durability across a separate connection.
    a=session('p3-commit')
    a.execute('BEGIN ISOLATION LEVEL READ COMMITTED; SELECT markethub.checkout_one(1,1,2); COMMIT;')
    check(stock(admin)==8 and order_count(admin)==1,
          'COMMIT persists stock reduction and order across connections')
    check(scalar(admin,'SELECT quantity||\'|\'||unit_price FROM markethub.order_items;')=='2|15000.00',
          'Committed item records correct quantity and purchase price')

    # Explicit rollback after all checkout statements have succeeded.
    a.execute('BEGIN; SELECT markethub.checkout_one(2,2,3);')
    check(stock(a,2)==7 and order_count(a)==2,'Uncommitted checkout is visible to its own transaction')
    check(stock(admin,2)==10 and order_count(admin)==1,'Other connection cannot see uncommitted changes')
    a.execute('ROLLBACK;')
    check(stock(admin,2)==10 and order_count(admin)==1,'ROLLBACK removes order and restores stock')

    # Genuine error and transaction rollback, with psql verbose SQLSTATE.
    # exit on SQL error closes the connection and aborts its open transaction.
    cmd=['docker','exec','-i',args.container,'psql','-X','-v','ON_ERROR_STOP=1',
         '-v','VERBOSITY=verbose','-U','postgres','-d',args.database]
    failed=subprocess.run(cmd,input='BEGIN; SELECT markethub.checkout_one(2,2,3); '
        'UPDATE markethub.inventory SET quantity_on_hand=-1 WHERE product_id=2; COMMIT;',
        text=True,encoding='utf-8',capture_output=True,timeout=30)
    (OUT/'error-rollback.txt').write_text(failed.stdout+failed.stderr,encoding='utf-8')
    check(failed.returncode!=0 and '23514' in failed.stderr,'Invalid negative stock raises CHECK violation SQLSTATE 23514')
    check(stock(admin,2)==10 and order_count(admin)==1,'Disconnect after SQL error rolls back the entire uncommitted checkout')

    # Nonrepeatable read versus stable snapshot, with explicit scheduling.
    reader=session('p3-isolation-reader'); writer=session('p3-isolation-writer')
    for level in ['READ COMMITTED','REPEATABLE READ']:
        reset(admin,10)
        reader.execute(f'BEGIN ISOLATION LEVEL {level}; SHOW transaction_isolation;')
        first=stock(reader)
        writer.execute('BEGIN; UPDATE markethub.inventory SET quantity_on_hand=9 WHERE product_id=1; COMMIT;')
        second=stock(reader)
        check((first,second)==((10,9) if level=='READ COMMITTED' else (10,10)),
              level+f' sees stock {first} then {second} across another session commit')
        reader.execute('COMMIT;')
        check(stock(reader)==9,level+' sees latest committed value in the next transaction')

    # Both sessions read 1 before either writes; no timing-only assumptions.
    reset(admin)
    u=session('p3-unsafe-a'); v=session('p3-unsafe-b')
    u.execute('BEGIN ISOLATION LEVEL READ COMMITTED;')
    v.execute('BEGIN ISOLATION LEVEL READ COMMITTED;')
    check(stock(u)==1 and stock(v)==1,'Unsafe sessions both read the same final unit')
    u.execute(unsafe_order(1)); v.execute(unsafe_order(2))
    units=int(scalar(admin,'SELECT sum(quantity) FROM markethub.order_items;'))
    check(stock(admin)==0 and order_count(admin)==2 and units==2,
          'Unsafe stale writes create two orders for one unit while nonnegative-stock CHECK still passes')

    # Protected checkout: B actually blocks, then rechecks stock after A commits.
    reset(admin)
    x=session('p3-safe-a'); y=session('p3-safe-b')
    x.execute('BEGIN ISOLATION LEVEL READ COMMITTED; SELECT markethub.checkout_one(1,1,1);')
    t,result=async_execute(y,"""BEGIN ISOLATION LEVEL READ COMMITTED;
    DO $$ BEGIN
      PERFORM markethub.checkout_one(2,1,1);
      RAISE EXCEPTION 'Unexpected second purchase succeeded' USING ERRCODE='XX000';
    EXCEPTION WHEN SQLSTATE 'P0001' THEN
      RAISE NOTICE 'EXPECTED: Insufficient stock; no second order created';
    END $$; COMMIT;""")
    wait_for_block(admin,'p3-safe-b','p3-safe-a')
    x.execute('COMMIT;')
    t.join(timeout=25)
    if t.is_alive(): raise TimeoutError('Competing checkout did not finish')
    if 'error' in result: raise result['error']
    check('EXPECTED: Insufficient stock' in result['output'],'Second safe checkout rejects insufficient stock after waiting')
    check(stock(admin)==0 and order_count(admin)==1 and
          scalar(admin,'SELECT sum(quantity) FROM markethub.order_items;')=='1',
          'Protected race ends with exactly one sold unit, one order, and zero stock')
    # Check function guard without committing any experimental changes.
    guard=admin.execute("""DO $$ BEGIN
      PERFORM markethub.checkout_one(1,1,0);
      RAISE EXCEPTION 'Guard failed';
    EXCEPTION WHEN SQLSTATE '22023' THEN RAISE NOTICE 'EXPECTED: positive quantity required'; END $$;""")
    check('EXPECTED: positive quantity required' in guard,'Checkout rejects zero quantity')
    (OUT/'verification.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
    print('All checks passed. Evidence:',OUT,flush=True)
finally:
    for s in reversed(sessions):
        try: s.close()
        except Exception as exc: print('Session cleanup:',exc,flush=True)
