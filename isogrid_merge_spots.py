"""
Isogrid Merge Analysis
======================

Try to merge Spot antennas or find other merge opportunities.
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


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def main():
    from score_function import getSolutionScore

    print("Loading isogrid dataset...")
    with open('./datasets/5_isogrid.json') as f:
        dataset = json.load(f)

    print("Loading solution...")
    with open('./solutions/solution_5_isogrid_195565000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {calculate_cost(antennas):,} EUR")

    # Analyze single-building antennas
    single_spot = []
    single_nano = []
    single_density = []

    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1:
            bid = ant['buildings'][0]
            b = bmap[bid]
            pop = get_max_pop(b)

            if ant['type'] == 'Spot':
                single_spot.append((i, bid, b, pop))
            elif ant['type'] == 'Nano':
                single_nano.append((i, bid, b, pop))
            elif ant['type'] == 'Density':
                single_density.append((i, bid, b, pop))

    print(f"\nSingle-building antennas:")
    print(f"  Nano: {len(single_nano)}")
    print(f"  Spot: {len(single_spot)}")
    print(f"  Density: {len(single_density)}")

    # Check if Spot pairs can be merged into Density
    # 2 Spots = 30,000 EUR, 1 Density = 30,000 EUR (no savings!)
    # But 2 Spots into 1 Spot would save 15,000 if possible
    print("\n=== SPOT MERGE ANALYSIS ===")

    spot_merges_spot = []  # Merge 2 Spots into 1 Spot
    spot_merges_density = []  # Merge 2 Spots into 1 Density

    for idx1, (i, bid1, b1, pop1) in enumerate(single_spot):
        for idx2, (j, bid2, b2, pop2) in enumerate(single_spot):
            if idx2 <= idx1:
                continue

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])
            combined_pop = pop1 + pop2

            # Try Spot (range 100, capacity 800)
            if d <= 100 and combined_pop <= 800:
                for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                    d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                    d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                    if d1 <= 100 and d2 <= 100:
                        spot_merges_spot.append((i, j, pos, 15_000))  # Save 15,000
                        break

            # Try Density (range 150, capacity 5000) - only if Spot didn't work
            elif d <= 150 and combined_pop <= 5000:
                for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                    d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                    d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                    if d1 <= 150 and d2 <= 150:
                        spot_merges_density.append((i, j, pos, 0))  # No savings
                        break

    print(f"Spot pairs mergeable into Spot: {len(spot_merges_spot)} (saves {len(spot_merges_spot) * 15_000:,} EUR)")
    print(f"Spot pairs mergeable into Density: {len(spot_merges_density)} (no savings)")

    # Check Nano merges
    print("\n=== NANO MERGE ANALYSIS ===")

    nano_merges_nano = []  # 2 Nano -> 1 Nano
    nano_merges_spot = []  # 2 Nano -> 1 Spot

    for idx1, (i, bid1, b1, pop1) in enumerate(single_nano):
        for idx2, (j, bid2, b2, pop2) in enumerate(single_nano):
            if idx2 <= idx1:
                continue

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])
            combined_pop = pop1 + pop2

            # Try Nano (range 50, capacity 200)
            if d <= 50 and combined_pop <= 200:
                for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                    d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                    d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                    if d1 <= 50 and d2 <= 50:
                        nano_merges_nano.append((i, j, pos, 5_000))  # Save 5,000
                        break

    print(f"Nano pairs mergeable into Nano: {len(nano_merges_nano)} (saves {len(nano_merges_nano) * 5_000:,} EUR)")

    # Check if single Density can be merged with another single Density using MaxRange
    print("\n=== DENSITY MERGE WITH MAXRANGE ===")

    density_merges = []

    for idx1, (i, bid1, b1, pop1) in enumerate(single_density):
        for idx2, (j, bid2, b2, pop2) in enumerate(single_density):
            if idx2 <= idx1:
                continue

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])
            combined_pop = pop1 + pop2

            # MaxRange: range 400, capacity 3500
            if d <= 400 and combined_pop <= 3500:
                for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                    d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                    d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                    if d1 <= 400 and d2 <= 400:
                        # 2 Density = 60,000, 1 MaxRange = 40,000 => Save 20,000
                        density_merges.append((i, j, pos, 20_000))
                        break

    print(f"Density pairs mergeable into MaxRange: {len(density_merges)} (saves up to {len(density_merges) * 20_000:,} EUR)")

    # Apply merges greedily
    all_merges = spot_merges_spot + nano_merges_nano + density_merges
    all_merges.sort(key=lambda x: -x[3])

    print(f"\n=== APPLYING MERGES ===")
    print(f"Total potential merges: {len(all_merges)}")

    merged = set()
    applied_merges = []

    for i, j, pos, savings in all_merges:
        if i in merged or j in merged:
            continue

        merged.add(i)
        merged.add(j)
        applied_merges.append((i, j, pos, savings))

    print(f"Applied merges: {len(applied_merges)}")
    total_savings = sum(m[3] for m in applied_merges)
    print(f"Total savings: {total_savings:,} EUR")

    if applied_merges:
        # Build new antenna list
        new_antennas = []

        for i, j, pos, savings in applied_merges:
            a1 = antennas[i]
            a2 = antennas[j]
            combined_bids = a1['buildings'] + a2['buildings']
            combined_blds = [bmap[bid] for bid in combined_bids]
            combined_pop = sum(get_max_pop(b) for b in combined_blds)

            # Determine type
            if combined_pop <= 200 and all(dist_sq(pos[0], pos[1], b['x'], b['y']) <= 50**2 for b in combined_blds):
                new_type = 'Nano'
            elif combined_pop <= 800 and all(dist_sq(pos[0], pos[1], b['x'], b['y']) <= 100**2 for b in combined_blds):
                new_type = 'Spot'
            elif combined_pop <= 5000 and all(dist_sq(pos[0], pos[1], b['x'], b['y']) <= 150**2 for b in combined_blds):
                new_type = 'Density'
            else:
                new_type = 'MaxRange'

            new_antennas.append({
                'type': new_type,
                'x': pos[0],
                'y': pos[1],
                'buildings': combined_bids
            })

        # Add unmerged antennas
        for i, ant in enumerate(antennas):
            if i not in merged:
                new_antennas.append(ant)

        # Validate
        solution = {'antennas': new_antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"\n{msg}")
        print(f"New cost: {cost:,} EUR ({len(new_antennas)} antennas)")

        if valid and cost < calculate_cost(antennas):
            output = f'./solutions/solution_5_isogrid_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
    else:
        print("No merges to apply")


if __name__ == "__main__":
    main()
