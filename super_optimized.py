"""
5G Network - Super Optimized Solution
======================================

More aggressive optimization with:
1. Better packing algorithms
2. Position optimization within buildings
3. Multiple passes to maximize coverage per antenna
"""

import json
import math
from collections import defaultdict
import random

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


def find_best_position(target_buildings, all_buildings, bmap, atype):
    """
    Find the best position to place an antenna to cover target buildings.
    Returns (x, y, buildings_covered) or None.
    """
    specs = ANTENNA_TYPES[atype]
    r2 = specs['range'] ** 2

    best_pos = None
    best_coverage = []

    # Try each target building as position
    for anchor_id in target_buildings:
        anchor = bmap[anchor_id]
        ax, ay = anchor['x'], anchor['y']

        # Find all buildings in range
        in_range = []
        for b in all_buildings:
            if dist_sq(ax, ay, b['x'], b['y']) <= r2:
                in_range.append(b)

        # Pack buildings (smallest first)
        in_range.sort(key=get_max_pop)
        selected = []
        total_pop = 0

        for b in in_range:
            if b['id'] not in target_buildings:
                continue
            p = get_max_pop(b)
            if total_pop + p <= specs['capacity']:
                selected.append(b['id'])
                total_pop += p

        if len(selected) > len(best_coverage):
            best_coverage = selected
            best_pos = (ax, ay)

    return best_pos, best_coverage


def solve_super_optimized(dataset):
    """
    Super optimized algorithm.

    Strategy:
    1. For each uncovered area, find the antenna that covers the most buildings
    2. Prioritize Density (best cost/capacity) for high-density areas
    3. Use MaxRange for sparse areas
    """
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    n = len(buildings)

    # Build spatial grid for fast lookup
    cell_size = 100
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Process until all covered
    iteration = 0
    while uncovered:
        iteration += 1

        best_antenna = None
        best_score = -1  # Score = buildings covered / cost

        # Sample positions
        candidates = list(uncovered)
        if len(candidates) > 500:
            candidates = random.sample(candidates, 500)

        for bid in candidates:
            b = bmap[bid]
            cx, cy = b['x'] // cell_size, b['y'] // cell_size

            for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                specs = ANTENNA_TYPES[atype]
                r2 = specs['range'] ** 2
                cells_check = int(specs['range'] / cell_size) + 1

                # Get buildings in range
                in_range = []
                for dx in range(-cells_check, cells_check + 1):
                    for dy in range(-cells_check, cells_check + 1):
                        for bb in grid[(cx + dx, cy + dy)]:
                            if bb['id'] in uncovered and dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= r2:
                                in_range.append(bb)

                if not in_range:
                    continue

                # Pack buildings
                in_range.sort(key=get_max_pop)
                selected = []
                total_pop = 0

                for bb in in_range:
                    p = get_max_pop(bb)
                    if total_pop + p <= specs['capacity']:
                        selected.append(bb['id'])
                        total_pop += p

                if not selected:
                    continue

                # Score: maximize coverage efficiency
                score = len(selected) * 1000000 / specs['cost_on']

                if score > best_score:
                    best_score = score
                    best_antenna = {
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': selected
                    }

        if best_antenna is None:
            # Fallback
            bid = next(iter(uncovered))
            b = bmap[bid]
            pop = get_max_pop(b)
            for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                if ANTENNA_TYPES[atype]['capacity'] >= pop:
                    best_antenna = {
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': [bid]
                    }
                    break

        antennas.append(best_antenna)
        for bid in best_antenna['buildings']:
            uncovered.discard(bid)

        if n > 1000 and iteration % 100 == 0:
            pct = (n - len(uncovered)) / n * 100
            print(f"  Progress: {pct:.1f}% ({n - len(uncovered)}/{n} buildings)")

    return {'antennas': antennas}


def optimize_types(solution, dataset):
    """Downgrade antenna types where possible."""
    bmap = {b['id']: b for b in dataset['buildings']}
    result = []

    for ant in solution['antennas']:
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)

        best_type = ant['type']
        best_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            all_ok = all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= specs['range'] ** 2 for b in blds)

            if all_ok and specs['cost_on'] < best_cost:
                best_type = atype
                best_cost = specs['cost_on']

        result.append({
            'type': best_type,
            'x': ant['x'],
            'y': ant['y'],
            'buildings': ant['buildings']
        })

    return {'antennas': result}


def merge_antennas(solution, dataset, max_iterations=1000):
    """Try to merge antennas to reduce count."""
    bmap = {b['id']: b for b in dataset['buildings']}
    antennas = [a.copy() for a in solution['antennas']]

    improved = True
    iterations = 0

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1

        for i in range(len(antennas)):
            if improved:
                break
            for j in range(i + 1, len(antennas)):
                a1, a2 = antennas[i], antennas[j]

                all_bids = a1['buildings'] + a2['buildings']
                all_blds = [bmap[bid] for bid in all_bids]
                total_pop = sum(get_max_pop(b) for b in all_blds)

                # Try to merge
                for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
                    for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                        specs = ANTENNA_TYPES[atype]
                        if specs['capacity'] < total_pop:
                            continue

                        all_ok = all(
                            dist_sq(pos[0], pos[1], b['x'], b['y']) <= specs['range'] ** 2
                            for b in all_blds
                        )

                        if not all_ok:
                            continue

                        old_cost = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
                        new_cost = specs['cost_on']

                        if new_cost < old_cost:
                            antennas[i] = {
                                'type': atype,
                                'x': pos[0],
                                'y': pos[1],
                                'buildings': all_bids
                            }
                            antennas.pop(j)
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break

    return {'antennas': antennas}


def main():
    from score_function import getSolutionScore

    datasets = [
        "1_peaceful_village",
        "2_small_town",
        "3_suburbia",
        "4_epitech",
        "5_isogrid",
        "6_manhattan"
    ]

    results = []

    for name in datasets:
        print(f"\n{'='*60}")
        print(f"Dataset: {name}")
        print('='*60)

        with open(f'./datasets/{name}.json') as f:
            dataset = json.load(f)

        n = len(dataset['buildings'])
        print(f"Buildings: {n}")

        # Run multiple times and keep best
        best_solution = None
        best_cost = float('inf')

        for run in range(3):  # 3 runs with randomization
            print(f"  Run {run + 1}/3...")

            sol = solve_super_optimized(dataset)
            sol = optimize_types(sol, dataset)

            if n <= 5000:
                sol = merge_antennas(sol, dataset)

            cost, valid, _ = getSolutionScore(json.dumps(sol), json.dumps(dataset))

            if valid and cost < best_cost:
                best_cost = cost
                best_solution = sol

        if best_solution:
            print(f"\nBest: {best_cost:,} EUR ({len(best_solution['antennas'])} antennas)")

            output = f'./solutions/solution_{name}_{best_cost}.json'
            with open(output, 'w') as f:
                json.dump(best_solution, f, indent=2)
            print(f"Saved: {output}")
            results.append((name, best_cost, len(best_solution['antennas'])))
        else:
            print("FAILED!")
            results.append((name, None, None))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    total = 0
    for name, cost, n in results:
        if cost:
            print(f"{name}: {cost:,} EUR ({n} antennas)")
            total += cost
        else:
            print(f"{name}: FAILED")
    print(f"\nTotal: {total:,} EUR")


if __name__ == "__main__":
    main()
