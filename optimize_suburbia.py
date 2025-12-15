"""
Optimized solution for Dataset 3: Suburbia
===========================================

Strategy:
1. Use Density antennas (best cost/capacity ratio)
2. Aggressive clustering to maximize buildings per antenna
3. Multiple passes with different starting points
4. Local search optimization
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


def solve_aggressive(buildings, seed=42):
    """
    Aggressive greedy with randomization for different starting points.
    """
    random.seed(seed)

    bmap = {b['id']: b for b in buildings}
    n = len(buildings)

    # Build spatial grid
    cell_size = 150  # Density range
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Shuffle order for randomization
    all_buildings = buildings[:]
    random.shuffle(all_buildings)

    while uncovered:
        best_antenna = None
        best_score = -1

        # Try each uncovered building as potential position
        candidates = [b for b in all_buildings if b['id'] in uncovered]

        # Sample if too many
        if len(candidates) > 300:
            candidates = random.sample(candidates, 300)

        for b in candidates:
            cx, cy = b['x'] // cell_size, b['y'] // cell_size

            # Try Density first (best cost/capacity)
            for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                specs = ANTENNA_TYPES[atype]
                r2 = specs['range'] ** 2
                cells_check = int(specs['range'] / cell_size) + 1

                # Get all uncovered buildings in range
                in_range = []
                for dx in range(-cells_check, cells_check + 1):
                    for dy in range(-cells_check, cells_check + 1):
                        for bb in grid[(cx + dx, cy + dy)]:
                            if bb['id'] in uncovered:
                                d2 = dist_sq(b['x'], b['y'], bb['x'], bb['y'])
                                if d2 <= r2:
                                    in_range.append((bb, get_max_pop(bb)))

                if not in_range:
                    continue

                # Sort by population (smallest first for better packing)
                in_range.sort(key=lambda x: x[1])

                # Pack as many as possible
                selected = []
                total_pop = 0
                for bb, pop in in_range:
                    if total_pop + pop <= specs['capacity']:
                        selected.append(bb['id'])
                        total_pop += pop

                if not selected:
                    continue

                # Score: maximize coverage per cost
                score = len(selected) * 10000 / specs['cost_on']

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

    return antennas


def solve_density_grid(buildings):
    """
    Grid-based approach optimized for Density antennas.
    """
    bmap = {b['id']: b for b in buildings}

    # Use Density range as cell size
    cell_size = 150
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Process cells in order
    cells = sorted(grid.keys())

    for cell in cells:
        while True:
            cell_uncovered = [b for b in grid[cell] if b['id'] in uncovered]
            if not cell_uncovered:
                break

            # Find best position in this cell
            best = None
            best_count = 0

            for anchor in cell_uncovered:
                # Check Density coverage
                specs = ANTENNA_TYPES['Density']
                r2 = specs['range'] ** 2

                in_range = []
                # Check this cell and neighbors
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
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

                if len(selected) > best_count:
                    best_count = len(selected)
                    best = {
                        'type': 'Density',
                        'x': anchor['x'],
                        'y': anchor['y'],
                        'buildings': selected
                    }

            if best:
                antennas.append(best)
                for bid in best['buildings']:
                    uncovered.discard(bid)
            else:
                # Use smallest antenna for remaining
                b = cell_uncovered[0]
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


def solve_maxrange_sparse(buildings):
    """
    Use MaxRange for better coverage in sparse areas.
    """
    bmap = {b['id']: b for b in buildings}

    cell_size = 200
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Sort buildings by number of neighbors (sparse first)
    building_neighbors = []
    for b in buildings:
        cx, cy = b['x'] // cell_size, b['y'] // cell_size
        neighbors = 0
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                neighbors += len(grid[(cx+dx, cy+dy)])
        building_neighbors.append((b, neighbors))

    building_neighbors.sort(key=lambda x: x[1])  # Sparse first

    for b, _ in building_neighbors:
        if b['id'] not in uncovered:
            continue

        best = None
        best_score = -1

        cx, cy = b['x'] // cell_size, b['y'] // cell_size

        for atype in ['MaxRange', 'Density', 'Spot', 'Nano']:
            specs = ANTENNA_TYPES[atype]
            r2 = specs['range'] ** 2
            cells_check = int(specs['range'] / cell_size) + 1

            in_range = []
            for dx in range(-cells_check, cells_check + 1):
                for dy in range(-cells_check, cells_check + 1):
                    for bb in grid[(cx+dx, cy+dy)]:
                        if bb['id'] in uncovered:
                            if dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= r2:
                                in_range.append((bb['id'], get_max_pop(bb)))

            if not in_range:
                continue

            in_range.sort(key=lambda x: x[1])
            selected = []
            total_pop = 0

            for bid, pop in in_range:
                if total_pop + pop <= specs['capacity']:
                    selected.append(bid)
                    total_pop += pop

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

    best_solution = None
    best_cost = float('inf')

    # Try multiple strategies
    strategies = []

    # Strategy 1: Aggressive with different seeds
    print("\nTrying aggressive algorithm with different seeds...")
    for seed in range(10):
        antennas = solve_aggressive(buildings, seed=seed)
        antennas = optimize_types(antennas, bmap)
        cost = calculate_cost(antennas)
        strategies.append(('aggressive_' + str(seed), antennas, cost))
        if cost < best_cost:
            best_cost = cost
            best_solution = antennas
        print(f"  Seed {seed}: {cost:,} EUR ({len(antennas)} antennas)")

    # Strategy 2: Density grid
    print("\nTrying density grid algorithm...")
    antennas = solve_density_grid(buildings)
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    strategies.append(('density_grid', antennas, cost))
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas
    print(f"  Density grid: {cost:,} EUR ({len(antennas)} antennas)")

    # Strategy 3: MaxRange for sparse areas
    print("\nTrying maxrange sparse algorithm...")
    antennas = solve_maxrange_sparse(buildings)
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    strategies.append(('maxrange_sparse', antennas, cost))
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas
    print(f"  MaxRange sparse: {cost:,} EUR ({len(antennas)} antennas)")

    # Validate best solution
    solution = {'antennas': best_solution}
    score, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\n{'='*60}")
    print(f"BEST RESULT: {best_cost:,} EUR ({len(best_solution)} antennas)")
    print(f"Validation: {msg}")
    print('='*60)

    if valid:
        output = f'./solutions/solution_3_suburbia_{score}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")

    return best_cost


if __name__ == "__main__":
    main()
