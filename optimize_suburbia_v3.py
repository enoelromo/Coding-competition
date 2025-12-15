"""
Suburbia V3 - Focus on reducing single-building antennas
=========================================================

Current best has 436 antennas covering only 1 building.
Goal: Reduce this number by better clustering.
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


def solve_maxrange_priority(buildings):
    """
    Prioritize MaxRange antennas to cover more buildings per antenna.
    MaxRange: range 400, capacity 3500
    Even though cost/capacity is worse, larger range means more buildings.
    """
    bmap = {b['id']: b for b in buildings}

    # Build grid with MaxRange cell size
    cell_size = 200
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # First pass: Use MaxRange for areas with many buildings
    cells_by_density = []
    for cell, blds in grid.items():
        cells_by_density.append((cell, len(blds)))
    cells_by_density.sort(key=lambda x: -x[1])  # Densest first

    for cell, _ in cells_by_density:
        while True:
            cell_uncovered = [b for b in grid[cell] if b['id'] in uncovered]
            if not cell_uncovered:
                break

            best = None
            best_count = 0

            for anchor in cell_uncovered:
                # Try MaxRange first
                for atype in ['MaxRange', 'Density']:
                    specs = ANTENNA_TYPES[atype]
                    r2 = specs['range'] ** 2

                    in_range = []
                    cells_check = int(specs['range'] / cell_size) + 1
                    for dx in range(-cells_check, cells_check + 1):
                        for dy in range(-cells_check, cells_check + 1):
                            adj = (cell[0] + dx, cell[1] + dy)
                            for b in grid[adj]:
                                if b['id'] in uncovered:
                                    if dist_sq(anchor['x'], anchor['y'], b['x'], b['y']) <= r2:
                                        in_range.append((b['id'], get_max_pop(b)))

                    if not in_range:
                        continue

                    in_range.sort(key=lambda x: x[1])
                    selected = []
                    total_pop = 0

                    for bid, pop in in_range:
                        if total_pop + pop <= specs['capacity']:
                            selected.append(bid)
                            total_pop += pop

                    # Only use if covering 2+ buildings
                    if len(selected) >= 2 and len(selected) > best_count:
                        best_count = len(selected)
                        best = {
                            'type': atype,
                            'x': anchor['x'],
                            'y': anchor['y'],
                            'buildings': selected
                        }

            if best:
                antennas.append(best)
                for bid in best['buildings']:
                    uncovered.discard(bid)
            else:
                break

    # Second pass: Handle remaining buildings with best fit
    remaining = [bmap[bid] for bid in uncovered]

    for b in remaining:
        if b['id'] not in uncovered:
            continue

        pop = get_max_pop(b)

        # Find best antenna
        best = None
        best_score = -1

        cx, cy = b['x'] // cell_size, b['y'] // cell_size

        for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < pop:
                continue

            r2 = specs['range'] ** 2
            cells_check = int(specs['range'] / cell_size) + 1

            in_range = []
            for dx in range(-cells_check, cells_check + 1):
                for dy in range(-cells_check, cells_check + 1):
                    adj = (cx + dx, cy + dy)
                    for bb in grid[adj]:
                        if bb['id'] in uncovered:
                            if dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= r2:
                                in_range.append((bb['id'], get_max_pop(bb)))

            in_range.sort(key=lambda x: x[1])
            selected = []
            total_pop = 0

            for bid, p in in_range:
                if total_pop + p <= specs['capacity']:
                    selected.append(bid)
                    total_pop += p

            if not selected:
                continue

            score = len(selected) / specs['cost_on'] * 1000000

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

    return antennas


def solve_iterative_improve(buildings, initial_antennas):
    """
    Start from existing solution and try to improve.
    """
    bmap = {b['id']: b for b in buildings}

    # Copy antennas
    antennas = [dict(a) for a in initial_antennas]

    # Build grid
    cell_size = 200
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    # Find single-building antennas
    single_antennas = [(i, a) for i, a in enumerate(antennas) if len(a['buildings']) == 1]

    print(f"  Found {len(single_antennas)} single-building antennas")

    improved = True
    iterations = 0

    while improved and iterations < 100:
        improved = False
        iterations += 1

        for idx, ant in single_antennas:
            if antennas[idx] is None:
                continue

            bid = ant['buildings'][0]
            b = bmap[bid]

            # Try to merge with nearby antenna
            cx, cy = b['x'] // cell_size, b['y'] // cell_size

            for i, other in enumerate(antennas):
                if other is None or i == idx:
                    continue

                # Check if we can add this building to other antenna
                specs = ANTENNA_TYPES[other['type']]
                if dist_sq(other['x'], other['y'], b['x'], b['y']) > specs['range'] ** 2:
                    continue

                other_pop = sum(get_max_pop(bmap[obid]) for obid in other['buildings'])
                my_pop = get_max_pop(b)

                if other_pop + my_pop <= specs['capacity']:
                    # Can merge!
                    old_cost = ANTENNA_TYPES[ant['type']]['cost_on']
                    # Adding to existing antenna is free
                    if old_cost > 0:  # Always saves money
                        other['buildings'].append(bid)
                        antennas[idx] = None
                        improved = True
                        break

        # Clean up
        antennas = [a for a in antennas if a is not None]
        single_antennas = [(i, a) for i, a in enumerate(antennas) if len(a['buildings']) == 1]

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

            all_ok = all(
                dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= specs['range'] ** 2
                for b in blds
            )

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

    print("Loading suburbia dataset...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    print(f"Buildings: {len(buildings)}")

    # Load existing best solution
    print("\nLoading existing best solution...")
    with open('./solutions/solution_3_suburbia_32145000.json') as f:
        existing = json.load(f)
    existing_cost = calculate_cost(existing['antennas'])
    print(f"Existing: {existing_cost:,} EUR ({len(existing['antennas'])} antennas)")

    best_solution = existing['antennas']
    best_cost = existing_cost

    # Try MaxRange priority
    print("\nTrying MaxRange priority algorithm...")
    antennas = solve_maxrange_priority(buildings)
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    print(f"  MaxRange priority: {cost:,} EUR ({len(antennas)} antennas)")
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas
        print("  * NEW BEST!")

    # Try iterative improvement on existing
    print("\nTrying iterative improvement on existing solution...")
    antennas = solve_iterative_improve(buildings, existing['antennas'])
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    print(f"  Iterative improve: {cost:,} EUR ({len(antennas)} antennas)")
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas
        print("  * NEW BEST!")

    # Validate
    solution = {'antennas': best_solution}
    score, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\n{'='*60}")
    print(f"BEST: {best_cost:,} EUR ({len(best_solution)} antennas)")
    print(f"Validation: {msg}")
    print('='*60)

    if valid and score < existing_cost:
        output = f'./solutions/solution_3_suburbia_{score}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    else:
        print("No improvement found, keeping existing solution.")


if __name__ == "__main__":
    main()
