"""
Suburbia Rebuild - Multiple strategies from scratch
====================================================
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


def build_solution(buildings, bmap, strategy='density_first', seed=0):
    """Build a solution using the specified strategy."""
    random.seed(seed)

    # Build spatial grid
    cell_size = 100
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Order buildings based on strategy
    if strategy == 'density_first':
        # Process densest areas first
        cell_order = sorted(grid.keys(), key=lambda c: -len(grid[c]))
        ordered_buildings = []
        for cell in cell_order:
            ordered_buildings.extend(grid[cell])
    elif strategy == 'sparse_first':
        # Process sparse areas first
        cell_order = sorted(grid.keys(), key=lambda c: len(grid[c]))
        ordered_buildings = []
        for cell in cell_order:
            ordered_buildings.extend(grid[cell])
    elif strategy == 'high_pop_first':
        # Process high population buildings first
        ordered_buildings = sorted(buildings, key=lambda b: -get_max_pop(b))
    elif strategy == 'low_pop_first':
        # Process low population buildings first
        ordered_buildings = sorted(buildings, key=lambda b: get_max_pop(b))
    elif strategy == 'random':
        ordered_buildings = buildings[:]
        random.shuffle(ordered_buildings)
    else:
        ordered_buildings = buildings

    for b in ordered_buildings:
        if b['id'] not in uncovered:
            continue

        cx, cy = b['x'] // cell_size, b['y'] // cell_size

        # Try to find best antenna placement
        best = None
        best_score = -1

        # Try Density first (best cost/capacity)
        for atype in ['Density', 'Spot', 'Nano', 'MaxRange']:
            specs = ANTENNA_TYPES[atype]
            r2 = specs['range'] ** 2
            cells_check = int(specs['range'] / cell_size) + 1

            # Get buildings in range
            in_range = []
            for dx in range(-cells_check, cells_check + 1):
                for dy in range(-cells_check, cells_check + 1):
                    for bb in grid[(cx + dx, cy + dy)]:
                        if bb['id'] in uncovered:
                            if dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= r2:
                                in_range.append((bb['id'], get_max_pop(bb)))

            if not in_range:
                continue

            # Sort by population and pack
            in_range.sort(key=lambda x: x[1])
            selected = []
            total_pop = 0

            for bid, pop in in_range:
                if total_pop + pop <= specs['capacity']:
                    selected.append(bid)
                    total_pop += pop

            if not selected:
                continue

            # Score: buildings per cost
            score = len(selected) * 1000000 / specs['cost_on']

            if score > best_score:
                best_score = score
                best = {
                    'type': atype,
                    'x': b['x'],
                    'y': b['y'],
                    'buildings': selected
                }

        if best:
            antennas.append(best)
            for bid in best['buildings']:
                uncovered.discard(bid)
        else:
            # Fallback
            pop = get_max_pop(b)
            for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                if ANTENNA_TYPES[atype]['capacity'] >= pop:
                    antennas.append({
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': [b['id']]
                    })
                    uncovered.discard(b['id'])
                    break

    return antennas


def optimize_types(antennas, bmap):
    """Downgrade antenna types where possible."""
    result = []

    for ant in antennas:
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)

        best_type = ant['type']
        best_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            r2 = specs['range'] ** 2
            all_ok = all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= r2 for b in blds)

            if all_ok and specs['cost_on'] < best_cost:
                best_type = atype
                best_cost = specs['cost_on']

        result.append({
            'type': best_type,
            'x': ant['x'],
            'y': ant['y'],
            'buildings': ant['buildings']
        })

    return result


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def main():
    from score_function import getSolutionScore

    print("Loading data...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    print(f"Buildings: {len(buildings)}")

    # Load current best
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        best_sol = json.load(f)

    best_antennas = best_sol['antennas']
    best_cost = calculate_cost(best_antennas)
    print(f"Current best: {best_cost:,} EUR")

    # Try different strategies
    strategies = ['density_first', 'sparse_first', 'high_pop_first', 'low_pop_first', 'random']

    for strategy in strategies:
        print(f"\nStrategy: {strategy}")

        for seed in range(10):
            antennas = build_solution(buildings, bmap, strategy, seed)
            antennas = optimize_types(antennas, bmap)

            # Validate
            solution = {'antennas': antennas}
            cost, valid, _ = getSolutionScore(json.dumps(solution), json.dumps(dataset))

            if valid and cost < best_cost:
                print(f"  Seed {seed}: {cost:,} EUR * NEW BEST!")
                best_cost = cost
                best_antennas = antennas

                output = f'./solutions/solution_3_suburbia_{cost}.json'
                with open(output, 'w') as f:
                    json.dump(solution, f, indent=2)
            elif seed == 0:
                print(f"  Seed {seed}: {cost:,} EUR")

    print(f"\n{'='*60}")
    print(f"FINAL BEST: {best_cost:,} EUR ({len(best_antennas)} antennas)")


if __name__ == "__main__":
    main()
