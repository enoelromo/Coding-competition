"""
Fast merge algorithm using spatial indexing
============================================
"""

import json
import math
from collections import defaultdict
import sys

ANTENNA_TYPES = {
    'Nano': {'range': 50, 'capacity': 200, 'cost_on': 5_000},
    'Spot': {'range': 100, 'capacity': 800, 'cost_on': 15_000},
    'Density': {'range': 150, 'capacity': 5_000, 'cost_on': 30_000},
    'MaxRange': {'range': 400, 'capacity': 3_500, 'cost_on': 40_000}
}


def get_max_pop(b):
    return max(b['populationPeakHours'], b['populationOffPeakHours'], b['populationNight'])


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def fast_merge(antennas, bmap):
    """
    Fast merge using spatial grid to only check nearby antennas.
    """
    # Build grid of antennas
    cell_size = 200  # Half of MaxRange
    grid = defaultdict(list)

    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    merged = set()
    new_antennas = []
    merges = 0

    for i, ant in enumerate(antennas):
        if i in merged:
            continue

        a1 = ant
        cx, cy = a1['x'] // cell_size, a1['y'] // cell_size

        best_merge = None
        best_savings = 0

        # Check nearby cells
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                for j in grid[(cx + dx, cy + dy)]:
                    if j <= i or j in merged:
                        continue

                    a2 = antennas[j]

                    # Quick distance check
                    if dist_sq(a1['x'], a1['y'], a2['x'], a2['y']) > 800 ** 2:
                        continue

                    all_bids = a1['buildings'] + a2['buildings']
                    all_blds = [bmap[bid] for bid in all_bids]
                    total_pop = sum(get_max_pop(b) for b in all_blds)

                    for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
                        for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                            specs = ANTENNA_TYPES[atype]
                            if specs['capacity'] < total_pop:
                                continue

                            r2 = specs['range'] ** 2
                            all_ok = all(
                                dist_sq(pos[0], pos[1], b['x'], b['y']) <= r2
                                for b in all_blds
                            )

                            if not all_ok:
                                continue

                            old_cost = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
                            new_cost = specs['cost_on']
                            savings = old_cost - new_cost

                            if savings > best_savings:
                                best_savings = savings
                                best_merge = {
                                    'j': j,
                                    'type': atype,
                                    'x': pos[0],
                                    'y': pos[1],
                                    'buildings': all_bids
                                }
                            break  # Found valid type, no need to try more expensive ones

        if best_merge:
            merged.add(i)
            merged.add(best_merge['j'])
            new_antennas.append({
                'type': best_merge['type'],
                'x': best_merge['x'],
                'y': best_merge['y'],
                'buildings': best_merge['buildings']
            })
            merges += 1
        else:
            new_antennas.append(a1)

    # Add remaining unmerged antennas
    for i, ant in enumerate(antennas):
        if i not in merged:
            pass  # Already added

    return new_antennas, merges


def optimize_dataset(dataset_num, dataset_name):
    from score_function import getSolutionScore

    print(f'\n{"="*60}')
    print(f'Optimizing {dataset_name}...')
    print("="*60)

    with open(f'./datasets/{dataset_name}.json') as f:
        dataset = json.load(f)

    # Find best existing solution
    import os
    best_file = None
    best_cost = float('inf')

    for f in os.listdir('./solutions'):
        if dataset_name in f and f.endswith('.json'):
            cost = int(f.split('_')[-1].replace('.json', ''))
            if cost < best_cost:
                best_cost = cost
                best_file = f

    if not best_file:
        print(f"No existing solution found for {dataset_name}")
        return

    print(f"Starting from: {best_file} ({best_cost:,} EUR)")

    with open(f'./solutions/{best_file}') as f:
        sol = json.load(f)

    bmap = {b['id']: b for b in dataset['buildings']}
    antennas = sol['antennas']

    print(f"Antennas: {len(antennas)}")

    # Apply fast merge repeatedly
    total_merges = 0
    for iteration in range(10):
        antennas, merges = fast_merge(antennas, bmap)
        total_merges += merges
        if merges == 0:
            break
        print(f"  Iteration {iteration + 1}: {merges} merges")

    print(f"Total merges: {total_merges}")

    # Validate and save
    solution = {'antennas': antennas}
    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))
    print(f"Result: {msg}")

    if valid and cost < best_cost:
        output = f'./solutions/solution_{dataset_name}_{cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"IMPROVED! Saved: {output}")
        return cost
    else:
        print("No improvement")
        return best_cost


def main():
    datasets = [
        (3, '3_suburbia'),
        (4, '4_epitech'),
        (5, '5_isogrid'),
        (6, '6_manhattan')
    ]

    results = []
    for num, name in datasets:
        cost = optimize_dataset(num, name)
        results.append((name, cost))

    print(f'\n{"="*60}')
    print("SUMMARY")
    print("="*60)
    for name, cost in results:
        if cost:
            print(f"{name}: {cost:,} EUR")


if __name__ == "__main__":
    main()
