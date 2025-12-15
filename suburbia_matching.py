"""
Suburbia Matching Optimization
==============================

Use graph matching to merge single-building Density antennas.
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

    print("Loading data...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    bmap = {b['id']: b for b in dataset['buildings']}
    antennas = sol['antennas']

    print(f"Starting: {calculate_cost(antennas):,} EUR ({len(antennas)} antennas)")

    # Find single-building Density antennas
    single_density_indices = []
    for i, a in enumerate(antennas):
        if len(a['buildings']) == 1 and a['type'] == 'Density':
            single_density_indices.append(i)

    print(f"Single-building Density antennas: {len(single_density_indices)}")

    # Build graph of mergeable pairs
    # Edge: (i, j, savings, merged_type, merged_pos)
    edges = []

    for idx1, i in enumerate(single_density_indices):
        a1 = antennas[i]
        b1 = bmap[a1['buildings'][0]]
        p1 = get_max_pop(b1)

        for idx2, j in enumerate(single_density_indices):
            if idx2 <= idx1:
                continue

            a2 = antennas[j]
            b2 = bmap[a2['buildings'][0]]
            p2 = get_max_pop(b2)

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])

            # Check if mergeable
            combined_pop = p1 + p2

            # Try Density (range 150)
            if d <= 150 and combined_pop <= 5000:
                # Both buildings within 150 of one position
                # Check which position works
                for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                    d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                    d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                    if d1 <= 150 and d2 <= 150:
                        # Old: 2 * 30000 = 60000, New: 30000, Savings: 30000
                        edges.append((i, j, 30000, 'Density', pos))
                        break

            # Try MaxRange (range 400) - but only if Density doesn't work
            elif d <= 400 and combined_pop <= 3500:
                for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                    d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                    d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                    if d1 <= 400 and d2 <= 400:
                        # Old: 2 * 30000 = 60000, New: 40000, Savings: 20000
                        edges.append((i, j, 20000, 'MaxRange', pos))
                        break

    print(f"Mergeable edges: {len(edges)}")

    # Greedy matching: sort by savings (descending), then greedily select
    edges.sort(key=lambda e: -e[2])

    matched = set()
    merges = []

    for i, j, savings, atype, pos in edges:
        if i in matched or j in matched:
            continue

        matched.add(i)
        matched.add(j)
        merges.append((i, j, atype, pos))

    print(f"Matches found: {len(merges)}")
    print(f"Expected savings: {len(merges) * 30000:,} EUR (if all Density)")

    # Apply merges
    merged_indices = set()
    new_antennas = []

    for i, j, atype, pos in merges:
        a1 = antennas[i]
        a2 = antennas[j]
        new_antennas.append({
            'type': atype,
            'x': pos[0],
            'y': pos[1],
            'buildings': a1['buildings'] + a2['buildings']
        })
        merged_indices.add(i)
        merged_indices.add(j)

    # Add non-merged antennas
    for i, a in enumerate(antennas):
        if i not in merged_indices:
            new_antennas.append(a)

    # Validate
    solution = {'antennas': new_antennas}
    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\nResult: {msg}")
    print(f"New cost: {cost:,} EUR ({len(new_antennas)} antennas)")

    if valid:
        old_cost = calculate_cost(antennas)
        savings = old_cost - cost
        print(f"Savings: {savings:,} EUR")

        if cost < old_cost:
            output = f'./solutions/solution_3_suburbia_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
        else:
            print("No improvement!")
    else:
        print("INVALID SOLUTION!")


if __name__ == "__main__":
    main()
