"""
5G Network Optimization - Efficient Algorithm
==============================================

Fast O(n log n) algorithm using sweep line + greedy.
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


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def solve_efficient(dataset):
    """
    Efficient algorithm:
    1. Sort buildings by (x, y)
    2. For each building, try to add to recent antennas
    3. If not possible, create new antenna with best type
    """
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}

    # Sort by x, then y
    sorted_b = sorted(buildings, key=lambda b: (b['x'], b['y']))

    antennas = []  # List of (antenna_dict, current_population)
    covered = set()

    for b in sorted_b:
        if b['id'] in covered:
            continue

        pop = get_max_pop(b)
        added = False

        # Try to add to recent antennas (last 50)
        for i in range(max(0, len(antennas) - 50), len(antennas)):
            ant, cur_pop = antennas[i]
            specs = ANTENNA_TYPES[ant['type']]

            # Check distance
            if dist_sq(ant['x'], ant['y'], b['x'], b['y']) > specs['range'] ** 2:
                continue

            # Check capacity
            if cur_pop + pop > specs['capacity']:
                continue

            # Add to this antenna
            ant['buildings'].append(b['id'])
            antennas[i] = (ant, cur_pop + pop)
            covered.add(b['id'])
            added = True
            break

        if not added:
            # Create new antenna - choose best type based on population
            if pop > 3500:
                atype = 'Density'
            elif pop > 800:
                atype = 'MaxRange'
            elif pop > 200:
                atype = 'Spot'
            else:
                atype = 'Density'  # Use Density for clustering potential

            new_ant = {
                'type': atype,
                'x': b['x'],
                'y': b['y'],
                'buildings': [b['id']]
            }
            antennas.append((new_ant, pop))
            covered.add(b['id'])

    return {'antennas': [a[0] for a in antennas]}


def solve_clustering(dataset):
    """
    Better clustering approach:
    - Use MaxRange (400) to find dense areas
    - Use Density for medium density
    - Use Spot/Nano for sparse areas
    """
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    n = len(buildings)

    # Build grid with MaxRange cells
    cell_size = 300  # Slightly less than MaxRange
    grid = defaultdict(list)

    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Process each cell
    cells = list(grid.keys())
    cells.sort()

    for cell in cells:
        cell_buildings = [b for b in grid[cell] if b['id'] in uncovered]

        while cell_buildings:
            # Take first uncovered as anchor
            anchor = cell_buildings[0]
            ax, ay = anchor['x'], anchor['y']

            # Try each antenna type, starting from best coverage
            best = None
            best_count = 0

            for atype in ['MaxRange', 'Density', 'Spot', 'Nano']:
                specs = ANTENNA_TYPES[atype]
                r2 = specs['range'] ** 2

                # Find all uncovered buildings in range
                in_range = []
                for b in cell_buildings:
                    if dist_sq(ax, ay, b['x'], b['y']) <= r2:
                        in_range.append(b)

                # Also check adjacent cells
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        adj_cell = (cell[0] + dx, cell[1] + dy)
                        for b in grid[adj_cell]:
                            if b['id'] in uncovered and dist_sq(ax, ay, b['x'], b['y']) <= r2:
                                if b not in in_range:
                                    in_range.append(b)

                if not in_range:
                    continue

                # Pack buildings by smallest population first
                in_range.sort(key=get_max_pop)
                selected = []
                total_pop = 0

                for b in in_range:
                    p = get_max_pop(b)
                    if total_pop + p <= specs['capacity']:
                        selected.append(b['id'])
                        total_pop += p

                if not selected:
                    continue

                # Score by cost efficiency: buildings covered per EUR
                efficiency = len(selected) / specs['cost_on']

                if len(selected) > best_count or (len(selected) == best_count and best and specs['cost_on'] < ANTENNA_TYPES[best['type']]['cost_on']):
                    best_count = len(selected)
                    best = {
                        'type': atype,
                        'x': ax,
                        'y': ay,
                        'buildings': selected
                    }

            if best:
                antennas.append(best)
                for bid in best['buildings']:
                    uncovered.discard(bid)
                cell_buildings = [b for b in cell_buildings if b['id'] in uncovered]
            else:
                # Fallback - shouldn't happen
                b = cell_buildings[0]
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
                cell_buildings = [bb for bb in cell_buildings if bb['id'] in uncovered]

    return {'antennas': antennas}


def optimize_types(solution, dataset):
    """Downgrade antenna types where possible to save cost."""
    bmap = {b['id']: b for b in dataset['buildings']}
    result = []

    for ant in solution['antennas']:
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)

        best_type = ant['type']
        best_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        # Try cheaper types
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

    return {'antennas': result}


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
        print(f"\n{'='*50}")
        print(f"Dataset: {name}")
        print('='*50)

        with open(f'./datasets/{name}.json') as f:
            dataset = json.load(f)

        n = len(dataset['buildings'])
        print(f"Buildings: {n}")

        # Try both methods
        sol1 = optimize_types(solve_efficient(dataset), dataset)
        sol2 = optimize_types(solve_clustering(dataset), dataset)

        cost1, valid1, _ = getSolutionScore(json.dumps(sol1), json.dumps(dataset))
        cost2, valid2, _ = getSolutionScore(json.dumps(sol2), json.dumps(dataset))

        if valid1 and valid2:
            if cost1 <= cost2:
                solution, cost = sol1, cost1
                print(f"  Efficient method: {cost1:,} EUR")
            else:
                solution, cost = sol2, cost2
                print(f"  Clustering method: {cost2:,} EUR")
        elif valid1:
            solution, cost = sol1, cost1
        elif valid2:
            solution, cost = sol2, cost2
        else:
            print("BOTH FAILED!")
            results.append((name, None, None))
            continue

        msg = f"Solution is valid! Total cost: {cost:,} EUR"
        print(f"Result: {msg}")

        output = f'./solutions/solution_{name}_{cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
        results.append((name, cost, len(solution['antennas'])))

    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
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
