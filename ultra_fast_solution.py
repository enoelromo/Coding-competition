"""
5G Network Optimization - Ultra Fast Algorithm
================================================

Simple but effective approach:
1. Sort buildings by position
2. Greedily assign buildings to antennas
3. Use Density (best cost/capacity) as primary type
"""

import json
import math
from collections import defaultdict

ANTENNA_TYPES = {
    'Nano': {'range': 50, 'capacity': 200, 'cost_on': 5_000, 'cost_off': 6_000},
    'Spot': {'range': 100, 'capacity': 800, 'cost_on': 15_000, 'cost_off': 20_000},
    'Density': {'range': 150, 'capacity': 5_000, 'cost_on': 30_000, 'cost_off': 50_000},
    'MaxRange': {'range': 400, 'capacity': 3_500, 'cost_on': 40_000, 'cost_off': 50_000}
}


def get_max_pop(b):
    return max(b['populationPeakHours'], b['populationOffPeakHours'], b['populationNight'])


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def solve_simple(dataset):
    """
    Simple greedy: for each building, try to add to existing antenna or create new one.
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}

    # Sort by x then y for spatial locality
    sorted_buildings = sorted(buildings, key=lambda b: (b['x'], b['y']))

    antennas = []
    covered = set()

    for b in sorted_buildings:
        if b['id'] in covered:
            continue

        pop = get_max_pop(b)

        # Try to add to existing antenna
        added = False
        for ant in antennas:
            specs = ANTENNA_TYPES[ant['type']]

            # Check distance
            d2 = dist_sq(ant['x'], ant['y'], b['x'], b['y'])
            if d2 > specs['range'] ** 2:
                continue

            # Check capacity
            current_pop = sum(get_max_pop(building_map[bid]) for bid in ant['buildings'])
            if current_pop + pop <= specs['capacity']:
                ant['buildings'].append(b['id'])
                covered.add(b['id'])
                added = True
                break

        if not added:
            # Create new antenna
            # Choose smallest antenna that fits
            for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
                if ANTENNA_TYPES[atype]['capacity'] >= pop:
                    antennas.append({
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': [b['id']]
                    })
                    covered.add(b['id'])
                    break

    return {'antennas': antennas}


def solve_density_first(dataset):
    """
    Prioritize Density antennas (best cost/capacity ratio).
    Group nearby buildings and assign to Density antennas.
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}

    # Grid-based grouping
    cell_size = 150  # Density range
    grid = defaultdict(list)

    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    antennas = []
    covered = set()

    # Process each cell
    for cell, cell_buildings in grid.items():
        cell_buildings = [b for b in cell_buildings if b['id'] not in covered]
        if not cell_buildings:
            continue

        # Sort by population
        cell_buildings.sort(key=lambda b: get_max_pop(b))

        while cell_buildings:
            # Find centroid of remaining buildings
            uncovered_here = [b for b in cell_buildings if b['id'] not in covered]
            if not uncovered_here:
                break

            # Use first uncovered building as anchor
            anchor = uncovered_here[0]

            # Try each antenna type, prefer Density
            best_antenna = None
            best_score = -1

            for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                specs = ANTENNA_TYPES[atype]

                # Find buildings in range from anchor
                in_range = []
                for b in uncovered_here:
                    if dist_sq(anchor['x'], anchor['y'], b['x'], b['y']) <= specs['range'] ** 2:
                        in_range.append(b)

                if not in_range:
                    continue

                # Pack buildings
                in_range.sort(key=lambda b: get_max_pop(b))
                selected = []
                total_pop = 0

                for b in in_range:
                    pop = get_max_pop(b)
                    if total_pop + pop <= specs['capacity']:
                        selected.append(b['id'])
                        total_pop += pop

                if not selected:
                    continue

                # Score by buildings covered per cost
                score = len(selected) / specs['cost_on'] * 1000000

                if score > best_score:
                    best_score = score
                    best_antenna = {
                        'type': atype,
                        'x': anchor['x'],
                        'y': anchor['y'],
                        'buildings': selected
                    }

            if best_antenna:
                antennas.append(best_antenna)
                for bid in best_antenna['buildings']:
                    covered.add(bid)
                cell_buildings = [b for b in cell_buildings if b['id'] not in covered]
            else:
                # Fallback
                b = uncovered_here[0]
                pop = get_max_pop(b)
                for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                    if ANTENNA_TYPES[atype]['capacity'] >= pop:
                        antennas.append({
                            'type': atype,
                            'x': b['x'],
                            'y': b['y'],
                            'buildings': [b['id']]
                        })
                        covered.add(b['id'])
                        break
                cell_buildings = [bb for bb in cell_buildings if bb['id'] not in covered]

    return {'antennas': antennas}


def optimize_antenna_types(solution, dataset):
    """Downgrade antenna types where possible."""
    building_map = {b['id']: b for b in dataset['buildings']}
    antennas = []

    for ant in solution['antennas']:
        buildings_obj = [building_map[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in buildings_obj)

        # Find cheapest type that works
        best_type = ant['type']
        best_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            # Check range for all buildings
            all_ok = all(
                dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= specs['range'] ** 2
                for b in buildings_obj
            )

            if all_ok and specs['cost_on'] < best_cost:
                best_type = atype
                best_cost = specs['cost_on']

        antennas.append({
            'type': best_type,
            'x': ant['x'],
            'y': ant['y'],
            'buildings': ant['buildings']
        })

    return {'antennas': antennas}


def solve_dataset(dataset):
    """Solve a single dataset."""
    # Try density-first approach
    solution = solve_density_first(dataset)
    solution = optimize_antenna_types(solution, dataset)
    return solution


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

        print(f"Buildings: {len(dataset['buildings'])}")

        solution = solve_dataset(dataset)

        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))
        print(f"Result: {msg}")

        if valid:
            output = f'./solutions/solution_{name}_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
            results.append((name, cost, len(solution['antennas'])))
        else:
            print("FAILED!")
            results.append((name, None, None))

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
