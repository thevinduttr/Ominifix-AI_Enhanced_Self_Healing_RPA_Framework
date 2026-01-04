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
now = time.time()

rows = []
for bid, info in bots.items():
    last_seen = info.get('last_seen')
    if last_seen:
        age = now - float(last_seen)
    else:
        age = None
    rows.append((bid, age, info))

# categorize
miss_1 = [r for r in rows if (r[1] is None or r[1] > 60)]
miss_5 = [r for r in rows if (r[1] is None or r[1] > 300)]
miss_10 = [r for r in rows if (r[1] is None or r[1] > 600)]

print('Heartbeat missing summary (as of', datetime.fromtimestamp(now).isoformat(),')')
print(f'Total bots: {len(rows)}')
print(f'Bots missing (>1 min): {len(miss_1)}')
print(f'Bots missing (>5 min): {len(miss_5)}')
print(f'Bots missing (>10 min): {len(miss_10)}')
print('\nDetails (sorted by age desc; age None means never seen):')
for bid, age, info in sorted(rows, key=lambda x: (x[1] if x[1] is not None else 10**12), reverse=True):
    if age is None:
        age_s = 'never'
        age_h = 'never'
    else:
        age_s = f'{int(age)}s'
        age_h = f'{age/60:.1f}m'
    status = info.get('status')
    print(f'- {bid}: last_seen_age={age_s} ({age_h}), status={status}')

print('\nInterpretation:')
print('- If a bot is missing heartbeat for >1min, it is likely stopped or network issue.')
print('- >5min suggests persistent outage; >10min indicates longer downtime.')
print('- "never" means monitor never recorded a heartbeat for that bot.')
