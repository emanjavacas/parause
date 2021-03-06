
import math
import collections
import random
import json

random.seed(1001)

lines = []
with open('SCT1-5.json') as f:
    for l in f:
        obj = json.loads(l.strip())
        if obj['type'] == 'inexactQuotation-allusion':
            lines.append(obj)

NSPLITS = 4
RESERVE = 20
PROP = math.ceil(len(lines) / NSPLITS)
splits = collections.defaultdict(list)
random.shuffle(lines)

print(len(lines), len(set([i['id'] for i in lines])))

for split in range(NSPLITS):
    split_lines = lines[split*PROP:(split+1)*PROP]
    for i in split_lines:
        splits[split].append(i)
    reserve = split_lines[-RESERVE:]
    for splitb in range(NSPLITS):
        if split != splitb:
            splits[splitb].extend(reserve)
    print(split, len(split_lines))

for split in range(NSPLITS):
    print(len(splits[split]), len(set([i['id'] for i in splits[split]])))

# CHECKS
ids = [i['id'] for i in lines]
target_ids = []
for split in splits:
    target_ids.extend([i['id'] for i in splits[split]])

print("All targets are captured", set(ids) == set(target_ids))
for idx, split in enumerate(splits):
    with open("SCT1-5.split{}.json".format(idx+1), 'w') as f:
        for line in splits[split]:
            f.write('{}\n'.format(json.dumps(line)))
