"""
5G Network Optimization - Best Combined Solution
=================================================

Combines multiple strategies and picks the best result for each dataset.
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


# Strategy 1: Efficient sweep
def solve_sweep(dataset, prefer_type='Density'):
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    sorted_b = sorted(buildings, key=lambda b: (b['x'], b['y']))

    antennas = []
    covered = set()

    for b in sorted_b:
        if b['id'] in covered:
            continue

        pop = get_max_pop(b)
        added = False

        for i in range(max(0, len(antennas) - 100), len(antennas)):
            ant, cur_pop = antennas[i]
            specs = ANTENNA_TYPES[ant['type']]

            if dist_sq(ant['x'], ant['y'], b['x'], b['y']) > specs['range'] ** 2:
                continue
            if cur_pop + pop > specs['capacity']:
                continue

            ant['buildings'].append(b['id'])
            antennas[i] = (ant, cur_pop + pop)
            covered.add(b['id'])
            added = True
            break

        if not added:
            if pop > 3500:
                atype = 'Density'
            elif pop > 800:
                atype = 'MaxRange'
            else:
                atype = prefer_type

            new_ant = {'type': atype, 'x': b['x'], 'y': b['y'], 'buildings': [b['id']]}
            antennas.append((new_ant, pop))
            covered.add(b['id'])

    return {'antennas': [a[0] for a in antennas]}


# Strategy 2: Grid clustering
def solve_grid(dataset, cell_size=300):
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}

    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    for cell in sorted(grid.keys()):
        cell_buildings = [b for b in grid[cell] if b['id'] in uncovered]

        while cell_buildings:
            anchor = cell_buildings[0]
            ax, ay = anchor['x'], anchor['y']

            best = None
            best_efficiency = -1

            for atype in ['MaxRange', 'Density', 'Spot', 'Nano']:
                specs = ANTENNA_TYPES[atype]
                r2 = specs['range'] ** 2

                in_range = []
                # Check current and adjacent cells
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        adj = (cell[0] + dx, cell[1] + dy)
                        for b in grid[adj]:
                            if b['id'] in uncovered and dist_sq(ax, ay, b['x'], b['y']) <= r2:
                                in_range.append(b)

                if not in_range:
                    continue

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

                efficiency = len(selected) / specs['cost_on']
                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best = {'type': atype, 'x': ax, 'y': ay, 'buildings': selected}

            if best:
                antennas.append(best)
                for bid in best['buildings']:
                    uncovered.discard(bid)
                cell_buildings = [b for b in cell_buildings if b['id'] in uncovered]
            else:
                b = cell_buildings[0]
                pop = get_max_pop(b)
                for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                    if ANTENNA_TYPES[atype]['capacity'] >= pop:
                        antennas.append({'type': atype, 'x': b['x'], 'y': b['y'], 'buildings': [b['id']]})
                        uncovered.discard(b['id'])
                        break
                cell_buildings = [bb for bb in cell_buildings if bb['id'] in uncovered]

    return {'antennas': antennas}


# Strategy 3: MaxRange first (for sparse datasets)
def solve_maxrange_first(dataset):
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}

    # Build grid for fast lookup
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // 200, b['y'] // 200)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Sort by total potential coverage
    building_priority = []
    for b in buildings:
        # Count neighbors
        cx, cy = b['x'] // 200, b['y'] // 200
        neighbors = 0
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                neighbors += len(grid[(cx+dx, cy+dy)])
        building_priority.append((b, neighbors))

    building_priority.sort(key=lambda x: -x[1])

    for b, _ in building_priority:
        if b['id'] not in uncovered:
            continue

        best = None
        best_count = 0

        for atype in ['MaxRange', 'Density', 'Spot', 'Nano']:
            specs = ANTENNA_TYPES[atype]
            r2 = specs['range'] ** 2

            in_range = []
            cx, cy = b['x'] // 200, b['y'] // 200
            cells_check = int(specs['range'] / 200) + 1

            for dx in range(-cells_check, cells_check + 1):
                for dy in range(-cells_check, cells_check + 1):
                    for bb in grid[(cx+dx, cy+dy)]:
                        if bb['id'] in uncovered and dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= r2:
                            in_range.append(bb)

            if not in_range:
                continue

            in_range.sort(key=get_max_pop)
            selected = []
            total_pop = 0

            for bb in in_range:
                p = get_max_pop(bb)
                if total_pop + p <= specs['capacity']:
                    selected.append(bb['id'])
                    total_pop += p

            if len(selected) > best_count:
                best_count = len(selected)
                best = {'type': atype, 'x': b['x'], 'y': b['y'], 'buildings': selected}

        if best:
            antennas.append(best)
            for bid in best['buildings']:
                uncovered.discard(bid)

    return {'antennas': antennas}


# Strategy 4: Density-focused (best cost/capacity)
def solve_density_focused(dataset):
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}

    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // 150, b['y'] // 150)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    for cell in sorted(grid.keys()):
        cell_buildings = [b for b in grid[cell] if b['id'] in uncovered]

        while cell_buildings:
            anchor = cell_buildings[0]

            # First try Density (best cost/capacity)
            specs = ANTENNA_TYPES['Density']
            r2 = specs['range'] ** 2

            in_range = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    adj = (cell[0] + dx, cell[1] + dy)
                    for b in grid[adj]:
                        if b['id'] in uncovered and dist_sq(anchor['x'], anchor['y'], b['x'], b['y']) <= r2:
                            in_range.append(b)

            in_range.sort(key=get_max_pop)
            selected = []
            total_pop = 0

            for b in in_range:
                p = get_max_pop(b)
                if total_pop + p <= specs['capacity']:
                    selected.append(b['id'])
                    total_pop += p

            if selected:
                antennas.append({'type': 'Density', 'x': anchor['x'], 'y': anchor['y'], 'buildings': selected})
                for bid in selected:
                    uncovered.discard(bid)
            else:
                # Fallback to any type
                b = cell_buildings[0]
                pop = get_max_pop(b)
                for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                    if ANTENNA_TYPES[atype]['capacity'] >= pop:
                        antennas.append({'type': atype, 'x': b['x'], 'y': b['y'], 'buildings': [b['id']]})
                        uncovered.discard(b['id'])
                        break

            cell_buildings = [b for b in cell_buildings if b['id'] in uncovered]

    return {'antennas': antennas}


def optimize_types(solution, dataset):
    """Downgrade antenna types to save cost."""
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

        result.append({'type': best_type, 'x': ant['x'], 'y': ant['y'], 'buildings': ant['buildings']})

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
        print(f"\n{'='*60}")
        print(f"Dataset: {name}")
        print('='*60)

        with open(f'./datasets/{name}.json') as f:
            dataset = json.load(f)

        n = len(dataset['buildings'])
        print(f"Buildings: {n}")

        # Try all strategies
        strategies = [
            ('Sweep (Density)', lambda d: optimize_types(solve_sweep(d, 'Density'), d)),
            ('Sweep (MaxRange)', lambda d: optimize_types(solve_sweep(d, 'MaxRange'), d)),
            ('Grid 300', lambda d: optimize_types(solve_grid(d, 300), d)),
            ('Grid 200', lambda d: optimize_types(solve_grid(d, 200), d)),
            ('Grid 400', lambda d: optimize_types(solve_grid(d, 400), d)),
            ('MaxRange first', lambda d: optimize_types(solve_maxrange_first(d), d)),
            ('Density focused', lambda d: optimize_types(solve_density_focused(d), d)),
        ]

        best_solution = None
        best_cost = float('inf')
        best_name = None

        for strat_name, strat_func in strategies:
            try:
                sol = strat_func(dataset)
                cost, valid, _ = getSolutionScore(json.dumps(sol), json.dumps(dataset))
                if valid and cost < best_cost:
                    best_cost = cost
                    best_solution = sol
                    best_name = strat_name
                print(f"  {strat_name}: {cost:,} EUR {'*' if cost == best_cost else ''}")
            except Exception as e:
                print(f"  {strat_name}: ERROR - {e}")

        if best_solution:
            print(f"\nBest: {best_name} = {best_cost:,} EUR ({len(best_solution['antennas'])} antennas)")

            output = f'./solutions/solution_{name}_{best_cost}.json'
            with open(output, 'w') as f:
                json.dump(best_solution, f, indent=2)
            print(f"Saved: {output}")
            results.append((name, best_cost, len(best_solution['antennas'])))
        else:
            print("ALL STRATEGIES FAILED!")
            results.append((name, None, None))

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
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
