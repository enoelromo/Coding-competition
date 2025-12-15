"""
Suburbia Smart Merge
====================

Look for specific single-building Density antennas that could be merged
using MaxRange at an optimal position.
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

    print("Loading suburbia dataset...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    print("Loading current best solution...")
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {calculate_cost(antennas):,} EUR")

    # Find ALL single-building antennas (any type)
    single_antennas = []
    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1:
            bid = ant['buildings'][0]
            b = bmap[bid]
            pop = get_max_pop(b)
            cost = ANTENNA_TYPES[ant['type']]['cost_on']
            single_antennas.append({
                'index': i,
                'type': ant['type'],
                'bid': bid,
                'x': b['x'],
                'y': b['y'],
                'pop': pop,
                'cost': cost
            })

    print(f"\nSingle-building antennas: {len(single_antennas)}")

    # Count by type
    by_type = defaultdict(list)
    for sa in single_antennas:
        by_type[sa['type']].append(sa)

    for atype, items in by_type.items():
        print(f"  {atype}: {len(items)} (cost: {ANTENNA_TYPES[atype]['cost_on']:,} each)")

    # Find pairs that could be merged with MaxRange
    # Savings: old_cost1 + old_cost2 - 40,000 (MaxRange cost)
    print("\n=== LOOKING FOR MERGE OPPORTUNITIES ===")

    merge_opportunities = []

    for i, sa1 in enumerate(single_antennas):
        for j, sa2 in enumerate(single_antennas):
            if j <= i:
                continue

            d = dist(sa1['x'], sa1['y'], sa2['x'], sa2['y'])
            combined_pop = sa1['pop'] + sa2['pop']

            # Check if MaxRange can cover both
            if d <= 400 and combined_pop <= 3500:
                # Try building positions and midpoint
                positions = [
                    (sa1['x'], sa1['y']),
                    (sa2['x'], sa2['y']),
                    ((sa1['x'] + sa2['x']) // 2, (sa1['y'] + sa2['y']) // 2)
                ]

                for px, py in positions:
                    d1 = dist(px, py, sa1['x'], sa1['y'])
                    d2 = dist(px, py, sa2['x'], sa2['y'])

                    if d1 <= 400 and d2 <= 400:
                        old_cost = sa1['cost'] + sa2['cost']
                        new_cost = 40_000  # MaxRange
                        savings = old_cost - new_cost

                        if savings > 0:
                            merge_opportunities.append({
                                'i': sa1['index'],
                                'j': sa2['index'],
                                'pos': (px, py),
                                'savings': savings,
                                'sa1': sa1,
                                'sa2': sa2,
                                'distance': d
                            })
                        break

    print(f"Merge opportunities found: {len(merge_opportunities)}")

    if merge_opportunities:
        # Sort by savings (descending)
        merge_opportunities.sort(key=lambda x: -x['savings'])

        print("\nTop 10 opportunities:")
        for opp in merge_opportunities[:10]:
            print(f"  Antennas {opp['i']},{opp['j']}: "
                  f"{opp['sa1']['type']}+{opp['sa2']['type']} -> MaxRange, "
                  f"d={opp['distance']:.1f}m, pop={opp['sa1']['pop']}+{opp['sa2']['pop']}, "
                  f"savings={opp['savings']:,} EUR")

        # Apply merges greedily
        print("\n=== APPLYING MERGES ===")

        merged_indices = set()
        merges_to_apply = []

        for opp in merge_opportunities:
            if opp['i'] in merged_indices or opp['j'] in merged_indices:
                continue

            merged_indices.add(opp['i'])
            merged_indices.add(opp['j'])
            merges_to_apply.append(opp)

        print(f"Merges to apply: {len(merges_to_apply)}")
        total_savings = sum(m['savings'] for m in merges_to_apply)
        print(f"Expected total savings: {total_savings:,} EUR")

        # Build new antenna list
        new_antennas = []

        # Add merged antennas
        for opp in merges_to_apply:
            new_antennas.append({
                'type': 'MaxRange',
                'x': opp['pos'][0],
                'y': opp['pos'][1],
                'buildings': [opp['sa1']['bid'], opp['sa2']['bid']]
            })

        # Add non-merged antennas
        for i, ant in enumerate(antennas):
            if i not in merged_indices:
                new_antennas.append(ant)

        # Validate
        solution = {'antennas': new_antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"\n{'='*60}")
        print(f"RESULT: {msg}")
        print(f"New cost: {cost:,} EUR ({len(new_antennas)} antennas)")
        print(f"Original: {calculate_cost(antennas):,} EUR")
        print('='*60)

        if valid and cost < calculate_cost(antennas):
            print(f"\nIMPROVED! Actual savings: {calculate_cost(antennas) - cost:,} EUR")
            output = f'./solutions/solution_3_suburbia_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
        elif valid:
            print(f"\nNo improvement")
        else:
            print("\nINVALID SOLUTION!")
    else:
        print("\nNo merge opportunities found!")
        print("All single-building antennas either:")
        print("  - Are too far apart (>400m)")
        print("  - Have combined population >3500")


if __name__ == "__main__":
    main()
