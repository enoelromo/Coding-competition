"""
5G Network Optimization - Advanced Algorithm
=============================================

Enhanced greedy with better clustering and position optimization.

Key improvements:
1. Better neighbor search using spatial indexing
2. Smart antenna type selection based on building density
3. Iterative improvement phase
"""

import json
import math
from collections import defaultdict
from typing import List, Dict, Set, Tuple

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


def dist(x1, y1, x2, y2):
    return math.sqrt(dist_sq(x1, y1, x2, y2))


class SpatialGrid:
    """Efficient spatial indexing."""
    def __init__(self, buildings, cell_size=100):
        self.cell_size = cell_size
        self.grid = defaultdict(list)
        self.bmap = {b['id']: b for b in buildings}

        for b in buildings:
            cell = (b['x'] // cell_size, b['y'] // cell_size)
            self.grid[cell].append(b['id'])

    def get_in_range(self, x, y, radius, exclude=None):
        """Get building IDs within radius."""
        if exclude is None:
            exclude = set()

        cells = int(radius / self.cell_size) + 1
        cx, cy = x // self.cell_size, y // self.cell_size
        result = []
        r2 = radius * radius

        for dx in range(-cells, cells + 1):
            for dy in range(-cells, cells + 1):
                for bid in self.grid[(cx + dx, cy + dy)]:
                    if bid in exclude:
                        continue
                    b = self.bmap[bid]
                    if dist_sq(x, y, b['x'], b['y']) <= r2:
                        result.append(bid)
        return result


def find_best_antenna(x, y, uncovered_ids, bmap, prefer_capacity=False):
    """
    Find the best antenna configuration for a position.
    Returns (type, building_ids, score) or None.
    """
    best = None
    best_score = -1

    for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
        specs = ANTENNA_TYPES[atype]

        # Get buildings in range
        in_range = []
        for bid in uncovered_ids:
            b = bmap[bid]
            if dist_sq(x, y, b['x'], b['y']) <= specs['range'] ** 2:
                in_range.append((bid, get_max_pop(b)))

        if not in_range:
            continue

        # Sort by population ascending (pack small first)
        in_range.sort(key=lambda x: x[1])

        # Pack as many as possible
        selected = []
        total_pop = 0
        for bid, pop in in_range:
            if total_pop + pop <= specs['capacity']:
                selected.append(bid)
                total_pop += pop

        if not selected:
            continue

        cost = specs['cost_on']

        # Score: prioritize covering more buildings at lower cost
        if prefer_capacity:
            score = total_pop / cost * 1000
        else:
            score = len(selected) * 10000 / cost + total_pop / cost

        if score > best_score:
            best_score = score
            best = (atype, selected, score)

    return best


def solve_advanced(dataset):
    """
    Advanced greedy algorithm with better coverage.
    """
    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    bpos = {(b['x'], b['y']): b['id'] for b in buildings}

    # Build spatial index
    grid = SpatialGrid(buildings, cell_size=100)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Phase 1: Handle high-population buildings
    for b in buildings:
        if b['id'] not in uncovered:
            continue
        pop = get_max_pop(b)
        if pop > 3500:  # Only Density can handle
            antennas.append({
                'type': 'Density',
                'x': b['x'],
                'y': b['y'],
                'buildings': [b['id']]
            })
            uncovered.discard(b['id'])

    # Phase 2: Greedy covering
    iteration = 0
    while uncovered:
        iteration += 1

        best_antenna = None
        best_score = -1

        # Sample positions to try (all uncovered building positions)
        # For large datasets, sample
        candidates = list(uncovered)
        if len(candidates) > 1000:
            import random
            candidates = random.sample(candidates, min(1000, len(candidates)))

        for bid in candidates:
            b = bmap[bid]

            result = find_best_antenna(b['x'], b['y'], uncovered, bmap)
            if result and result[2] > best_score:
                best_score = result[2]
                best_antenna = {
                    'type': result[0],
                    'x': b['x'],
                    'y': b['y'],
                    'buildings': result[1]
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

        if len(buildings) > 1000 and iteration % 200 == 0:
            print(f"  Iteration {iteration}: {len(buildings) - len(uncovered)}/{len(buildings)} covered")

    return {'antennas': antennas}


def optimize_types(solution, dataset):
    """Optimize antenna types."""
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


def try_merge_antennas(solution, dataset):
    """Try to merge nearby antennas."""
    bmap = {b['id']: b for b in dataset['buildings']}
    antennas = solution['antennas'][:]
    improved = True

    while improved:
        improved = False
        i = 0
        while i < len(antennas):
            j = i + 1
            while j < len(antennas):
                a1, a2 = antennas[i], antennas[j]

                # Check if we can merge
                all_bids = a1['buildings'] + a2['buildings']
                all_blds = [bmap[bid] for bid in all_bids]
                total_pop = sum(get_max_pop(b) for b in all_blds)

                # Try each position and type
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

                        old_cost = (
                            ANTENNA_TYPES[a1['type']]['cost_on'] +
                            ANTENNA_TYPES[a2['type']]['cost_on']
                        )
                        new_cost = specs['cost_on']

                        if new_cost < old_cost:
                            # Merge!
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
                j += 1
            if improved:
                break
            i += 1

    return {'antennas': antennas}


def solve_dataset(dataset, name):
    """Solve a single dataset."""
    print(f"  Running advanced algorithm...")
    solution = solve_advanced(dataset)

    print(f"  Optimizing antenna types...")
    solution = optimize_types(solution, dataset)

    # Only merge for smaller datasets (expensive operation)
    if len(dataset['buildings']) <= 5000:
        print(f"  Trying to merge antennas...")
        solution = try_merge_antennas(solution, dataset)

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

        solution = solve_dataset(dataset, name)

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
