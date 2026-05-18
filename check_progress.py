import sys
sys.path.insert(0, '.')
from src.db.supabase_client import get_supabase_client
client = get_supabase_client()
# Get total count of domains
total = client.table('domains').select('id', count='exact').execute().count

# Count domains with a non‑null opportunity_score using pagination to avoid the 1000‑row limit
BATCH_SIZE = 1000
offset = 0
scored = 0
while True:
    batch = client.table('domains') \
        .select('opportunity_score') \
        .range(offset, offset + BATCH_SIZE - 1) \
        .execute()
    rows = batch.data or []
    if not rows:
        break
    scored += sum(1 for row in rows if row.get('opportunity_score') is not None)
    if len(rows) < BATCH_SIZE:
        break
    offset += BATCH_SIZE

print(f'Total domains scored: {scored} out of {total}')
