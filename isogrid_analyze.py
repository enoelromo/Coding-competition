"""
Isogrid Deep Analysis
=====================

Understand why no merges are possible.
"""

import json
import math
from collections import defaultdict

ANTENNA_TYPES = {
    'Nano': {'range': 50, 'capacity': 200, 'cost_on': 5_000},
    'Spot': {'range': 100, 'capacity': 800, 'cost_on': 15_000},
    'Density': {'range': 150, 'capacity': 5_000, 'cost_on': 30_000},
    'MaxRange': {'range': 400, 'capacity': 3_500, 'cost_on': 40_000}
}


def get_max_pop(b):
    return max(b['populationPeakHours'], b['populationOffPeakHours'], b['populationNight'])


def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def main():
    print("Loading isogrid dataset...")
    with open('./datasets/5_isogrid.json') as f:
        dataset = json.load(f)

    print("Loading solution...")
    with open('./solutions/solution_5_isogrid_195565000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    # Find single-building Density antennas
    single_density = []
    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1 and ant['type'] == 'Density':
            bid = ant['buildings'][0]
            b = bmap[bid]
            pop = get_max_pop(b)
            single_density.append((i, bid, b, pop))

    print(f"\nSingle-building Density antennas: {len(single_density)}")

    # Population distribution
    pops = [p for _, _, _, p in single_density]
    print(f"Population range: {min(pops)} - {max(pops)}")
    print(f"Average population: {sum(pops)/len(pops):.0f}")

    # Count by population buckets
    buckets = defaultdict(int)
    for pop in pops:
        if pop <= 800:
            buckets['<= 800'] += 1
        elif pop <= 1000:
            buckets['801-1000'] += 1
        elif pop <= 1500:
            buckets['1001-1500'] += 1
        elif pop <= 1750:
            buckets['1501-1750'] += 1
        elif pop <= 2000:
            buckets['1751-2000'] += 1
        elif pop <= 2500:
            buckets['2001-2500'] += 1
        elif pop <= 3000:
            buckets['2501-3000'] += 1
        elif pop <= 3500:
            buckets['3001-3500'] += 1
        else:
            buckets['> 3500'] += 1

    print("\nPopulation distribution:")
    for bucket in ['<= 800', '801-1000', '1001-1500', '1501-1750', '1751-2000', '2001-2500', '2501-3000', '3001-3500', '> 3500']:
        if buckets[bucket] > 0:
            print(f"  {bucket}: {buckets[bucket]}")

    # Find nearest neighbor distances for single-building Density
    print("\n=== NEAREST NEIGHBOR ANALYSIS ===")

    near_400 = 0  # Within MaxRange
    near_150 = 0  # Within Density range
    near_100 = 0  # Within Spot range
    isolated = 0  # More than 400m from any other

    combinable = []

    for idx1, (i, bid1, b1, pop1) in enumerate(single_density):
        nearest_dist = float('inf')
        nearest_info = None

        for idx2, (j, bid2, b2, pop2) in enumerate(single_density):
            if idx2 == idx1:
                continue

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])

            if d < nearest_dist:
                nearest_dist = d
                nearest_info = (j, pop2)

        if nearest_dist <= 100:
            near_100 += 1
        elif nearest_dist <= 150:
            near_150 += 1
        elif nearest_dist <= 400:
            near_400 += 1
        else:
            isolated += 1

        # Check if combinable with MaxRange
        if nearest_info and nearest_dist <= 400:
            combined = pop1 + nearest_info[1]
            if combined <= 3500:
                combinable.append((idx1, nearest_dist, pop1, nearest_info[1], combined))

    print(f"Within 100m (Spot range): {near_100}")
    print(f"Within 150m (Density range): {near_150}")
    print(f"Within 400m (MaxRange): {near_400}")
    print(f"Isolated (>400m): {isolated}")

    print(f"\nPairs with combined pop <= 3500 and d <= 400: {len(combinable)}")

    if combinable:
        print("\nSample combinable pairs:")
        for idx, d, p1, p2, combined in combinable[:10]:
            print(f"  Distance: {d:.1f}m, pop1: {p1}, pop2: {p2}, combined: {combined}")
    else:
        print("\nNo pairs found that can be merged with MaxRange!")
        print("This means all nearby pairs have combined population > 3500")

        # Let's verify
        print("\n=== VERIFICATION ===")
        examples = 0
        for idx1, (i, bid1, b1, pop1) in enumerate(single_density[:100]):
            for idx2, (j, bid2, b2, pop2) in enumerate(single_density):
                if idx2 <= idx1:
                    continue

                d = dist(b1['x'], b1['y'], b2['x'], b2['y'])

                if d <= 400:
                    combined = pop1 + pop2
                    if examples < 10:
                        print(f"  Pair: d={d:.1f}m, pop1={pop1}, pop2={pop2}, combined={combined}")
                        if combined <= 3500:
                            print("    ^ This should be mergeable!")
                        examples += 1


if __name__ == "__main__":
    main()
