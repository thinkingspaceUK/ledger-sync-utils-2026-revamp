#!/usr/bin/env python3
"""
Bake maps ahead of time. Building a map is seconds of work, and on the small
shared-CPU machine the game runs on that is a stall for everyone playing (and
enough of them in a row gets the whole machine throttled). So the maps are
built here, once, and shipped as gzipped JSON in server/maps/<kind>/<seed>.json.gz;
the server loads one at random instead of building. Run it again whenever the
generators change:

    python3 tools/bake_maps.py            # every kind
    python3 tools/bake_maps.py tower 6    # one kind, six of them
"""

import gzip
import json
import os
import random
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import mapgen  # noqa: E402

OUT = os.path.join(ROOT, 'server', 'maps')
# how many of each: the random towns get a spread, the fixed ones need one
COUNTS = {'town': 6, 'dock': 4, 'alpine': 4, 'manor': 4, 'tower': 3, 'front': 1, 'royale': 3, 'derby': 2}


def bake(kind, n):
    d = os.path.join(OUT, kind)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    rng = random.Random(kind)
    for i in range(n):
        seed = 1 if kind in ('front', 'derby') and i == 0 else rng.randrange(1, 2 ** 31)
        t0 = time.time()
        m = mapgen.generate(seed, kind).to_json()
        raw = json.dumps(m, separators=(',', ':')).encode()
        path = os.path.join(d, '%d.json.gz' % seed)
        with gzip.open(path, 'wb', compresslevel=9) as f:
            f.write(raw)
        print('  %-7s seed %-11d %5d KB -> %4d KB gz  built in %.1fs' % (kind, seed, len(raw) // 1024, os.path.getsize(path) // 1024, time.time() - t0), flush=True)


def main():
    kinds = [sys.argv[1]] if len(sys.argv) > 1 else list(COUNTS)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    for k in kinds:
        bake(k, n or COUNTS[k])
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
    print('baked %d KB in all' % (total // 1024))


if __name__ == '__main__':
    main()
