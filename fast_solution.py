"""
5G Network Optimization - Fast Algorithm
=========================================

Optimized for large datasets using spatial indexing.

Algorithm: Grid-based Greedy with Priority Queue

Time Complexity: O(n * k * log(n)) where n = buildings, k = avg buildings per cell
Space Complexity: O(n)
"""

import json
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import heapq

# Antenna specifications
ANTENNA_TYPES = {
    'Nano': {'range': 50, 'capacity': 200, 'cost_on': 5_000, 'cost_off': 6_000},
    'Spot': {'range': 100, 'capacity': 800, 'cost_on': 15_000, 'cost_off': 20_000},
    'Density': {'range': 150, 'capacity': 5_000, 'cost_on': 30_000, 'cost_off': 50_000},
    'MaxRange': {'range': 400, 'capacity': 3_500, 'cost_on': 40_000, 'cost_off': 50_000}
}

# Ordered by cost-efficiency (best to worst for general use)
ANTENNA_ORDER = ['Density', 'MaxRange', 'Spot', 'Nano']


class SpatialIndex:
    """Grid-based spatial index for fast neighbor queries."""

    def __init__(self, buildings: List[dict], cell_size: int = 400):
        self.cell_size = cell_size
        self.grid = defaultdict(list)
        self.building_map = {}

        for b in buildings:
            self.building_map[b['id']] = b
            cell = (b['x'] // cell_size, b['y'] // cell_size)
            self.grid[cell].append(b['id'])

    def get_nearby_buildings(self, x: int, y: int, radius: int) -> List[int]:
        """Get buildings within radius of a point."""
        cells_to_check = int(math.ceil(radius / self.cell_size)) + 1
        center_cell = (x // self.cell_size, y // self.cell_size)

        nearby = []
        for dx in range(-cells_to_check, cells_to_check + 1):
            for dy in range(-cells_to_check, cells_to_check + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                for bid in self.grid[cell]:
                    b = self.building_map[bid]
                    dist_sq = (b['x'] - x) ** 2 + (b['y'] - y) ** 2
                    if dist_sq <= radius ** 2:
                        nearby.append(bid)

        return nearby


def get_max_population(building: dict) -> int:
    """Get maximum population across all time periods."""
    return max(
        building['populationPeakHours'],
        building['populationOffPeakHours'],
        building['populationNight']
    )


def solve_fast(dataset: dict) -> dict:
    """
    Fast greedy algorithm using spatial indexing.

    Strategy:
    1. Use spatial index for O(1) neighbor lookups
    2. Process buildings in order of decreasing population
    3. For each uncovered building, find best antenna placement
    4. Prioritize Density antennas (best cost/capacity ratio)
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}
    building_positions = {(b['x'], b['y']): b['id'] for b in buildings}

    # Create spatial index
    spatial = SpatialIndex(buildings, cell_size=200)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Sort buildings by max population (descending) - handle high-pop first
    sorted_buildings = sorted(buildings, key=lambda b: -get_max_population(b))

    # Phase 1: Handle buildings with population > 3500 (only Density can handle)
    for b in sorted_buildings:
        if b['id'] not in uncovered:
            continue

        pop = get_max_population(b)
        if pop > 3500:
            # Must use Density, can only cover this building
            antennas.append({
                'type': 'Density',
                'x': b['x'],
                'y': b['y'],
                'buildings': [b['id']]
            })
            uncovered.discard(b['id'])

    # Phase 2: Greedy covering with spatial optimization
    while uncovered:
        best_option = None
        best_score = -1

        # Sample buildings to consider as antenna positions
        # For efficiency, only consider uncovered buildings
        candidates = list(uncovered)
        if len(candidates) > 500:
            # Sample for very large datasets
            import random
            candidates = random.sample(candidates, 500)

        for bid in candidates:
            b = building_map[bid]
            pos_x, pos_y = b['x'], b['y']

            for atype in ANTENNA_ORDER:
                specs = ANTENNA_TYPES[atype]

                # Get uncovered buildings in range using spatial index
                in_range_ids = spatial.get_nearby_buildings(pos_x, pos_y, specs['range'])
                in_range_uncovered = [i for i in in_range_ids if i in uncovered]

                if not in_range_uncovered:
                    continue

                # Sort by population and pack greedily
                in_range_buildings = [(i, get_max_population(building_map[i])) for i in in_range_uncovered]
                in_range_buildings.sort(key=lambda x: x[1])

                selected = []
                total_pop = 0
                for i, pop in in_range_buildings:
                    if total_pop + pop <= specs['capacity']:
                        selected.append(i)
                        total_pop += pop

                if not selected:
                    continue

                cost = specs['cost_on']  # Always place on building

                # Score: buildings covered per unit cost
                score = len(selected) * 10000 / cost + total_pop / cost

                if score > best_score:
                    best_score = score
                    best_option = {
                        'type': atype,
                        'x': pos_x,
                        'y': pos_y,
                        'buildings': selected
                    }

        if best_option is None:
            # Fallback: cover one building
            bid = next(iter(uncovered))
            b = building_map[bid]
            pop = get_max_population(b)

            for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                if ANTENNA_TYPES[atype]['capacity'] >= pop:
                    best_option = {
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': [bid]
                    }
                    break

        antennas.append(best_option)
        for bid in best_option['buildings']:
            uncovered.discard(bid)

        # Progress indicator for large datasets
        if len(buildings) > 1000 and len(antennas) % 100 == 0:
            print(f"  Progress: {len(buildings) - len(uncovered)}/{len(buildings)} buildings covered")

    return {'antennas': antennas}


def local_optimization(solution: dict, dataset: dict) -> dict:
    """
    Quick local search to optimize antenna types.
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}

    antennas = [a.copy() for a in solution['antennas']]

    for i, antenna in enumerate(antennas):
        buildings_obj = [building_map[bid] for bid in antenna['buildings']]
        total_pop = sum(get_max_population(b) for b in buildings_obj)

        # Find cheapest antenna type that works
        best_type = antenna['type']
        best_cost = ANTENNA_TYPES[antenna['type']]['cost_on']

        for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            # Check all buildings in range
            all_in_range = all(
                math.sqrt((antenna['x'] - b['x'])**2 + (antenna['y'] - b['y'])**2) <= specs['range']
                for b in buildings_obj
            )

            if all_in_range and specs['cost_on'] < best_cost:
                best_type = atype
                best_cost = specs['cost_on']

        antennas[i]['type'] = best_type

    return {'antennas': antennas}


def main():
    """Solve all datasets."""
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

    for dataset_name in datasets:
        print(f"\n{'='*60}")
        print(f"Processing: {dataset_name}")
        print('='*60)

        input_file = f'./datasets/{dataset_name}.json'
        with open(input_file) as f:
            dataset = json.load(f)

        n_buildings = len(dataset['buildings'])
        print(f"Buildings: {n_buildings}")

        # Solve
        print("Running fast greedy algorithm...")
        solution = solve_fast(dataset)

        print("Applying local optimization...")
        solution = local_optimization(solution, dataset)

        # Validate
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))
        print(f"Result: {msg}")

        if valid:
            output_file = f'./solutions/solution_{dataset_name}_{cost}.json'
            with open(output_file, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output_file}")
            results.append((dataset_name, cost, len(solution['antennas'])))
        else:
            print("ERROR: Invalid solution!")
            results.append((dataset_name, None, None))

    # Summary
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print('='*60)
    total_cost = 0
    for name, cost, n_antennas in results:
        if cost:
            print(f"{name}: {cost:,} EUR ({n_antennas} antennas)")
            total_cost += cost
        else:
            print(f"{name}: FAILED")

    print(f"\nTotal cost: {total_cost:,} EUR")


if __name__ == "__main__":
    main()
