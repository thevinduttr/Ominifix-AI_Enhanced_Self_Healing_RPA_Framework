import sys, json, time
from datetime import datetime

p = 'status.json'
if len(sys.argv) > 1:
    p = sys.argv[1]

try:
    with open(p, 'r') as f:
        data = json.load(f)
except Exception as e:
    print('Failed to load', p, e)
    sys.exit(2)

bots = data.get('bots', {})
if not bots:
    print('No bots present in status.')
    sys.exit(0)

now = time.time()
running = 0
failed = 0
print('Bot heartbeat summary (now =', datetime.fromtimestamp(now).isoformat(), ')')
print('-' * 60)
for bid, info in sorted(bots.items()):
    last_seen = info.get('last_seen')
    failed_at = info.get('failed_at')
    status = info.get('status') or 'UNKNOWN'
    age = None
    if last_seen:
        age = int(now - float(last_seen))
        status_calc = 'FAILED' if age > 10 else 'RUNNING'
    else:
        status_calc = 'UNKNOWN'
    # prefer calculated status for heartbeat freshness
    effective = status_calc
    if effective == 'RUNNING':
        running += 1
    elif effective == 'FAILED':
        failed += 1

    last = datetime.fromtimestamp(last_seen).isoformat() if last_seen else 'never'
    fa = datetime.fromtimestamp(failed_at).isoformat() if failed_at else '-'
    le = info.get('last_error')
    le_summary = ''
    if le:
        err = le.get('error')
        le_summary = (err[:120] + '...') if err and len(err) > 120 else (err or '')
    print(f'{bid}\n  status: {effective} (reported status="{status}")\n  last_seen: {last}  age_s: {age}\n  failed_at: {fa}\n  last_error: {le_summary}\n')

print('-' * 60)
print(f'Total bots: {len(bots)}  Running: {running}  Failed: {failed}')
