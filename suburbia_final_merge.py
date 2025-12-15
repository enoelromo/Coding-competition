"""
Suburbia Final Merge - All single-building antennas
====================================================
"""

import json
import math

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


def find_best_merge_type(d, pop):
    """Find cheapest antenna type that can cover both buildings."""
    for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
        specs = ANTENNA_TYPES[atype]
        if d <= specs['range'] and pop <= specs['capacity']:
            return atype, specs['cost_on']
    return None, None


def main():
    from score_function import getSolutionScore

    print("Loading data...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    bmap = {b['id']: b for b in dataset['buildings']}
    antennas = [dict(a) for a in sol['antennas']]

    old_cost = sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)
    print(f"Starting: {old_cost:,} EUR ({len(antennas)} antennas)")

    # Find single-building antennas
    single_indices = [i for i, a in enumerate(antennas) if len(a['buildings']) == 1]
    print(f"Single-building antennas: {len(single_indices)}")

    # Build list of all mergeable pairs with savings
    edges = []
    for idx1, i in enumerate(single_indices):
        a1 = antennas[i]
        b1 = bmap[a1['buildings'][0]]
        p1 = get_max_pop(b1)

        for idx2, j in enumerate(single_indices):
            if idx2 <= idx1:
                continue

            a2 = antennas[j]
            b2 = bmap[a2['buildings'][0]]
            p2 = get_max_pop(b2)

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])
            combined_pop = p1 + p2

            # Find best merge type
            merge_type, merge_cost = find_best_merge_type(d, combined_pop)

            if merge_type:
                old_cost_pair = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
                savings = old_cost_pair - merge_cost

                if savings > 0:
                    # Determine position (use position of building that's at center)
                    # For simplicity, use b1's position and verify both are in range
                    for pos in [(b1['x'], b1['y']), (b2['x'], b2['y'])]:
                        d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                        d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                        if d1 <= ANTENNA_TYPES[merge_type]['range'] and d2 <= ANTENNA_TYPES[merge_type]['range']:
                            edges.append((savings, i, j, merge_type, pos))
                            break

    print(f"Mergeable pairs: {len(edges)}")

    # Sort by savings (descending) for greedy matching
    edges.sort(reverse=True)

    # Greedy matching
    matched = set()
    merges = []

    for savings, i, j, atype, pos in edges:
        if i in matched or j in matched:
            continue

        matched.add(i)
        matched.add(j)
        merges.append((i, j, atype, pos, savings))

    print(f"Matches found: {len(merges)}")
    total_savings = sum(m[4] for m in merges)
    print(f"Total savings: {total_savings:,} EUR")

    # Apply merges
    merged_indices = set()
    new_antennas = []

    for i, j, atype, pos, _ in merges:
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

    if valid and cost < old_cost:
        print(f"IMPROVED! Savings: {old_cost - cost:,} EUR")
        output = f'./solutions/solution_3_suburbia_{cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    else:
        print("No improvement or invalid!")


if __name__ == "__main__":
    main()
