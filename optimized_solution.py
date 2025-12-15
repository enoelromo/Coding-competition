"""
5G Network Optimization Solution
================================

Algorithm: Greedy Set Cover with Clustering Optimization

Approach:
1. Pre-process buildings by their maximum population requirement
2. Identify "forced" assignments (buildings that can only be covered by specific antenna types)
3. Use spatial clustering to group nearby buildings
4. Apply greedy selection prioritizing cost-efficiency
5. Local search optimization to improve initial solution

Complexity Analysis:
- Time: O(n^2 * m) where n = buildings, m = potential antenna positions
- Space: O(n + m)
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

def distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def get_max_population(building: dict) -> int:
    """Get maximum population across all time periods for a building."""
    return max(
        building['populationPeakHours'],
        building['populationOffPeakHours'],
        building['populationNight']
    )

def get_buildings_in_range(x: int, y: int, antenna_range: int, buildings: List[dict]) -> List[int]:
    """Get all building IDs within range of a position."""
    result = []
    for b in buildings:
        if distance(x, y, b['x'], b['y']) <= antenna_range:
            result.append(b['id'])
    return result

def can_antenna_cover(antenna_type: str, buildings_to_cover: List[dict]) -> bool:
    """Check if an antenna type can cover a set of buildings (capacity constraint)."""
    total_pop = sum(get_max_population(b) for b in buildings_to_cover)
    return total_pop <= ANTENNA_TYPES[antenna_type]['capacity']

def find_best_antenna_for_buildings(buildings_subset: List[dict], on_building: bool) -> Tuple[str, int]:
    """Find the cheapest antenna type that can cover a set of buildings."""
    total_pop = sum(get_max_population(b) for b in buildings_subset)

    best_type = None
    best_cost = float('inf')

    for atype, specs in ANTENNA_TYPES.items():
        if specs['capacity'] >= total_pop:
            cost = specs['cost_on'] if on_building else specs['cost_off']
            if cost < best_cost:
                best_cost = cost
                best_type = atype

    return best_type, best_cost

def greedy_solution(dataset: dict) -> dict:
    """
    Greedy algorithm with cost-efficiency optimization.

    Strategy:
    1. For each building position, evaluate all antenna types
    2. Score each option by: (buildings_covered * avg_population) / cost
    3. Select the best option, mark buildings as covered, repeat
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}
    building_positions = {(b['x'], b['y']): b['id'] for b in buildings}

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    while uncovered:
        best_option = None
        best_score = -1

        # Try placing antenna on each building position
        for b in buildings:
            if b['id'] not in uncovered:
                continue

            pos_x, pos_y = b['x'], b['y']
            is_on_building = True

            # Try each antenna type
            for atype, specs in ANTENNA_TYPES.items():
                # Get buildings in range that are still uncovered
                in_range = get_buildings_in_range(pos_x, pos_y, specs['range'], buildings)
                coverable = [bid for bid in in_range if bid in uncovered]

                if not coverable:
                    continue

                # Try to maximize coverage within capacity
                coverable_buildings = [building_map[bid] for bid in coverable]
                coverable_buildings.sort(key=lambda x: get_max_population(x))

                # Greedily add buildings until capacity is reached
                selected = []
                total_pop = 0
                for cb in coverable_buildings:
                    pop = get_max_population(cb)
                    if total_pop + pop <= specs['capacity']:
                        selected.append(cb['id'])
                        total_pop += pop

                if not selected:
                    continue

                cost = specs['cost_on'] if is_on_building else specs['cost_off']

                # Score: prioritize covering more buildings cheaply
                # Higher score = better option
                score = len(selected) * 1000 / cost + total_pop / cost

                if score > best_score:
                    best_score = score
                    best_option = {
                        'type': atype,
                        'x': pos_x,
                        'y': pos_y,
                        'buildings': selected
                    }

        if best_option is None:
            # Fallback: cover one building with smallest antenna possible
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

        # Add the antenna and mark buildings as covered
        antennas.append(best_option)
        for bid in best_option['buildings']:
            uncovered.discard(bid)

    return {'antennas': antennas}


def optimized_greedy_solution(dataset: dict) -> dict:
    """
    Enhanced greedy algorithm with multiple strategies.

    Improvements over basic greedy:
    1. Pre-identify high-population buildings (need Density)
    2. Use MaxRange for sparse areas
    3. Cluster nearby small buildings for Spot/Nano
    4. Always place on buildings to save cost
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}
    building_positions = {(b['x'], b['y']): b['id'] for b in buildings}

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Phase 1: Handle high-population buildings first (>3500, only Density works)
    high_pop_buildings = [b for b in buildings if get_max_population(b) > 3500]
    for b in high_pop_buildings:
        if b['id'] not in uncovered:
            continue
        antennas.append({
            'type': 'Density',
            'x': b['x'],
            'y': b['y'],
            'buildings': [b['id']]
        })
        uncovered.discard(b['id'])

    # Phase 2: Try to use Density antennas efficiently (best cost/capacity ratio)
    while uncovered:
        best_option = None
        best_efficiency = -1

        for b in buildings:
            pos_x, pos_y = b['x'], b['y']

            for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                specs = ANTENNA_TYPES[atype]

                # Get uncovered buildings in range
                in_range = []
                for bid in uncovered:
                    bb = building_map[bid]
                    if distance(pos_x, pos_y, bb['x'], bb['y']) <= specs['range']:
                        in_range.append(bb)

                if not in_range:
                    continue

                # Sort by population (smallest first for bin packing)
                in_range.sort(key=lambda x: get_max_population(x))

                # Pack buildings into antenna capacity
                selected = []
                total_pop = 0
                for bb in in_range:
                    pop = get_max_population(bb)
                    if total_pop + pop <= specs['capacity']:
                        selected.append(bb['id'])
                        total_pop += pop

                if not selected:
                    continue

                is_on_building = (pos_x, pos_y) in building_positions
                cost = specs['cost_on'] if is_on_building else specs['cost_off']

                # Efficiency metric: maximize coverage, minimize cost
                efficiency = (len(selected) * 100 + total_pop) / cost

                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_option = {
                        'type': atype,
                        'x': pos_x,
                        'y': pos_y,
                        'buildings': selected
                    }

        if best_option is None:
            # Fallback for isolated buildings
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

    return {'antennas': antennas}


def cluster_based_solution(dataset: dict) -> dict:
    """
    Clustering-based approach using spatial proximity.

    Strategy:
    1. Build a graph of buildings within MaxRange distance
    2. Find connected components
    3. For each component, find optimal antenna placement
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}
    n = len(buildings)

    # Build adjacency based on MaxRange (400)
    max_range = 400
    adj = defaultdict(set)

    for i, b1 in enumerate(buildings):
        for j, b2 in enumerate(buildings):
            if i < j:
                d = distance(b1['x'], b1['y'], b2['x'], b2['y'])
                if d <= max_range:
                    adj[b1['id']].add(b2['id'])
                    adj[b2['id']].add(b1['id'])

    # Find connected components using BFS
    visited = set()
    components = []

    for b in buildings:
        if b['id'] in visited:
            continue

        component = []
        queue = [b['id']]
        while queue:
            bid = queue.pop(0)
            if bid in visited:
                continue
            visited.add(bid)
            component.append(bid)
            for neighbor in adj[bid]:
                if neighbor not in visited:
                    queue.append(neighbor)

        components.append(component)

    # Process each component
    antennas = []

    for component in components:
        comp_buildings = [building_map[bid] for bid in component]
        uncovered = set(component)

        while uncovered:
            best_option = None
            best_score = -1

            for b in comp_buildings:
                pos_x, pos_y = b['x'], b['y']

                for atype, specs in ANTENNA_TYPES.items():
                    in_range = []
                    for bid in uncovered:
                        bb = building_map[bid]
                        if distance(pos_x, pos_y, bb['x'], bb['y']) <= specs['range']:
                            in_range.append(bb)

                    if not in_range:
                        continue

                    in_range.sort(key=lambda x: get_max_population(x))

                    selected = []
                    total_pop = 0
                    for bb in in_range:
                        pop = get_max_population(bb)
                        if total_pop + pop <= specs['capacity']:
                            selected.append(bb['id'])
                            total_pop += pop

                    if not selected:
                        continue

                    cost = specs['cost_on']  # Always on building
                    score = len(selected) / cost * 10000 + total_pop / cost

                    if score > best_score:
                        best_score = score
                        best_option = {
                            'type': atype,
                            'x': pos_x,
                            'y': pos_y,
                            'buildings': selected
                        }

            if best_option:
                antennas.append(best_option)
                for bid in best_option['buildings']:
                    uncovered.discard(bid)
            else:
                bid = next(iter(uncovered))
                b = building_map[bid]
                pop = get_max_population(b)
                for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                    if ANTENNA_TYPES[atype]['capacity'] >= pop:
                        antennas.append({
                            'type': atype,
                            'x': b['x'],
                            'y': b['y'],
                            'buildings': [bid]
                        })
                        uncovered.discard(bid)
                        break

    return {'antennas': antennas}


def local_search_improvement(solution: dict, dataset: dict, iterations: int = 100) -> dict:
    """
    Local search to improve an existing solution.

    Moves:
    1. Try to merge two nearby antennas into one
    2. Try to change antenna type to a cheaper one
    3. Try to reassign buildings between antennas
    """
    buildings = dataset['buildings']
    building_map = {b['id']: b for b in buildings}

    antennas = solution['antennas'].copy()

    for _ in range(iterations):
        improved = False

        # Try to merge antennas
        for i in range(len(antennas)):
            if improved:
                break
            for j in range(i + 1, len(antennas)):
                a1, a2 = antennas[i], antennas[j]

                # Check if one antenna could cover both sets
                all_buildings = a1['buildings'] + a2['buildings']
                all_building_objs = [building_map[bid] for bid in all_buildings]
                total_pop = sum(get_max_population(b) for b in all_building_objs)

                # Try each position
                for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
                    for atype, specs in ANTENNA_TYPES.items():
                        if specs['capacity'] < total_pop:
                            continue

                        # Check all buildings in range
                        all_in_range = all(
                            distance(pos[0], pos[1], building_map[bid]['x'], building_map[bid]['y']) <= specs['range']
                            for bid in all_buildings
                        )

                        if not all_in_range:
                            continue

                        # Calculate costs
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
                                'buildings': all_buildings
                            }
                            antennas.pop(j)
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break

        # Try to downgrade antenna types
        if not improved:
            for i, antenna in enumerate(antennas):
                buildings_obj = [building_map[bid] for bid in antenna['buildings']]
                total_pop = sum(get_max_population(b) for b in buildings_obj)

                current_cost = ANTENNA_TYPES[antenna['type']]['cost_on']

                for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                    specs = ANTENNA_TYPES[atype]
                    if specs['capacity'] < total_pop:
                        continue

                    # Check range
                    all_in_range = all(
                        distance(antenna['x'], antenna['y'], b['x'], b['y']) <= specs['range']
                        for b in buildings_obj
                    )

                    if not all_in_range:
                        continue

                    new_cost = specs['cost_on']
                    if new_cost < current_cost:
                        antennas[i]['type'] = atype
                        improved = True
                        break

    return {'antennas': antennas}


def solve_dataset(dataset: dict, method: str = 'optimized') -> dict:
    """
    Solve a dataset using the specified method.

    Methods:
    - 'greedy': Basic greedy algorithm
    - 'optimized': Optimized greedy with phases
    - 'cluster': Clustering-based approach
    - 'best': Try all methods and return the best
    """
    if method == 'greedy':
        return greedy_solution(dataset)
    elif method == 'optimized':
        solution = optimized_greedy_solution(dataset)
        return local_search_improvement(solution, dataset)
    elif method == 'cluster':
        solution = cluster_based_solution(dataset)
        return local_search_improvement(solution, dataset)
    elif method == 'best':
        from score_function import getSolutionScore

        solutions = [
            ('greedy', greedy_solution(dataset)),
            ('optimized', local_search_improvement(optimized_greedy_solution(dataset), dataset)),
            ('cluster', local_search_improvement(cluster_based_solution(dataset), dataset))
        ]

        best_solution = None
        best_cost = float('inf')
        best_method = None

        for name, sol in solutions:
            cost, valid, msg = getSolutionScore(json.dumps(sol), json.dumps(dataset))
            if valid and cost < best_cost:
                best_cost = cost
                best_solution = sol
                best_method = name

        print(f"Best method: {best_method} with cost {best_cost:,}")
        return best_solution

    return optimized_greedy_solution(dataset)


def main():
    """Main function to solve all datasets."""
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

        print(f"Buildings: {len(dataset['buildings'])}")

        # Solve using best method
        solution = solve_dataset(dataset, method='best')

        # Validate and get score
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))
        print(f"Result: {msg}")

        if valid:
            output_file = f'./solutions/solution_{dataset_name}_{cost}.json'
            with open(output_file, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved to: {output_file}")
            results.append((dataset_name, cost, len(solution['antennas'])))
        else:
            print("ERROR: Invalid solution!")
            results.append((dataset_name, None, None))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for name, cost, antennas in results:
        if cost:
            print(f"{name}: {cost:,} EUR ({antennas} antennas)")
        else:
            print(f"{name}: FAILED")


if __name__ == "__main__":
    main()
