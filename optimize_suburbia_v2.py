"""
Suburbia Optimization V2 - More aggressive approach
====================================================

Key insight: Need to maximize buildings per antenna
- Density: range 150, capacity 5000 -> 30,000 EUR
- If we can fit 3+ buildings per Density antenna, it's efficient

Strategy:
1. Pre-compute all possible antenna placements
2. Select greedily by coverage/cost ratio
3. Use iterative improvement
"""

import json
import math
from collections import defaultdict
import random
import heapq

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


class SpatialIndex:
    def __init__(self, buildings, cell_size=100):
        self.cell_size = cell_size
        self.grid = defaultdict(list)
        self.bmap = {b['id']: b for b in buildings}

        for b in buildings:
            cell = (b['x'] // cell_size, b['y'] // cell_size)
            self.grid[cell].append(b['id'])

    def get_in_range(self, x, y, radius):
        cells = int(radius / self.cell_size) + 1
        cx, cy = x // self.cell_size, y // self.cell_size
        r2 = radius * radius
        result = []

        for dx in range(-cells, cells + 1):
            for dy in range(-cells, cells + 1):
                for bid in self.grid[(cx + dx, cy + dy)]:
                    b = self.bmap[bid]
                    if dist_sq(x, y, b['x'], b['y']) <= r2:
                        result.append(bid)
        return result


def find_best_coverage(x, y, uncovered, spatial, bmap, atype):
    """Find best building set to cover from position (x,y) with given antenna type."""
    specs = ANTENNA_TYPES[atype]

    in_range = spatial.get_in_range(x, y, specs['range'])
    in_range = [bid for bid in in_range if bid in uncovered]

    if not in_range:
        return None, 0

    # Sort by population (smallest first)
    in_range_pop = [(bid, get_max_pop(bmap[bid])) for bid in in_range]
    in_range_pop.sort(key=lambda x: x[1])

    selected = []
    total_pop = 0

    for bid, pop in in_range_pop:
        if total_pop + pop <= specs['capacity']:
            selected.append(bid)
            total_pop += pop

    return selected, len(selected)


def solve_greedy_best(buildings, seed=0):
    """
    Greedy algorithm that always picks the best option.
    """
    random.seed(seed)

    bmap = {b['id']: b for b in buildings}
    spatial = SpatialIndex(buildings, cell_size=75)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    while uncovered:
        best_antenna = None
        best_score = -1

        # Try each uncovered building as position
        candidates = list(uncovered)
        if len(candidates) > 500:
            candidates = random.sample(candidates, 500)

        for bid in candidates:
            b = bmap[bid]

            for atype in ['Density', 'Spot', 'Nano']:  # Skip MaxRange (worse cost/capacity)
                selected, count = find_best_coverage(b['x'], b['y'], uncovered, spatial, bmap, atype)

                if not selected:
                    continue

                cost = ANTENNA_TYPES[atype]['cost_on']
                score = count / cost * 1000000

                if score > best_score:
                    best_score = score
                    best_antenna = {
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': selected
                    }

        if best_antenna is None:
            bid = next(iter(uncovered))
            b = bmap[bid]
            pop = get_max_pop(b)
            for atype in ['Nano', 'Spot', 'Density']:
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


def solve_priority_queue(buildings):
    """
    Use priority queue to always select best option efficiently.
    """
    bmap = {b['id']: b for b in buildings}
    spatial = SpatialIndex(buildings, cell_size=75)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Pre-compute initial scores for all positions
    pq = []  # (-score, bid, atype)

    for b in buildings:
        for atype in ['Density', 'Spot', 'Nano']:
            selected, count = find_best_coverage(b['x'], b['y'], uncovered, spatial, bmap, atype)
            if selected:
                cost = ANTENNA_TYPES[atype]['cost_on']
                score = count / cost * 1000000
                heapq.heappush(pq, (-score, b['id'], atype, tuple(selected)))

    while uncovered and pq:
        neg_score, bid, atype, selected_tuple = heapq.heappop(pq)

        # Check if still valid
        selected = [b for b in selected_tuple if b in uncovered]
        if not selected:
            continue

        b = bmap[bid]

        # Recompute best coverage
        new_selected, count = find_best_coverage(b['x'], b['y'], uncovered, spatial, bmap, atype)

        if not new_selected:
            continue

        # Check if score changed significantly
        cost = ANTENNA_TYPES[atype]['cost_on']
        new_score = count / cost * 1000000

        if new_score < -neg_score * 0.8:  # Score dropped too much, reinsert
            heapq.heappush(pq, (-new_score, bid, atype, tuple(new_selected)))
            continue

        antennas.append({
            'type': atype,
            'x': b['x'],
            'y': b['y'],
            'buildings': new_selected
        })

        for bid in new_selected:
            uncovered.discard(bid)

    # Handle remaining
    for bid in uncovered:
        b = bmap[bid]
        pop = get_max_pop(b)
        for atype in ['Nano', 'Spot', 'Density']:
            if ANTENNA_TYPES[atype]['capacity'] >= pop:
                antennas.append({
                    'type': atype,
                    'x': b['x'],
                    'y': b['y'],
                    'buildings': [bid]
                })
                break

    return antennas


def solve_cluster_merge(buildings):
    """
    Start with one antenna per building, then merge aggressively.
    """
    bmap = {b['id']: b for b in buildings}

    # Start with Density on each building
    antennas = []
    for b in buildings:
        pop = get_max_pop(b)
        if pop <= 200:
            atype = 'Nano'
        elif pop <= 800:
            atype = 'Spot'
        else:
            atype = 'Density'

        antennas.append({
            'type': atype,
            'x': b['x'],
            'y': b['y'],
            'buildings': [b['id']],
            'pop': pop
        })

    # Merge pass
    merged = True
    iterations = 0
    max_iterations = 5000

    while merged and iterations < max_iterations:
        merged = False
        iterations += 1

        for i in range(len(antennas)):
            if merged:
                break

            a1 = antennas[i]
            if a1 is None:
                continue

            for j in range(i + 1, len(antennas)):
                a2 = antennas[j]
                if a2 is None:
                    continue

                # Check if can merge
                combined_pop = a1['pop'] + a2['pop']

                # Find best antenna type for combined
                for atype in ['Nano', 'Spot', 'Density']:
                    specs = ANTENNA_TYPES[atype]
                    if specs['capacity'] < combined_pop:
                        continue

                    # Check if all buildings fit in range from either position
                    for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
                        all_bids = a1['buildings'] + a2['buildings']
                        all_ok = all(
                            dist_sq(pos[0], pos[1], bmap[bid]['x'], bmap[bid]['y']) <= specs['range'] ** 2
                            for bid in all_bids
                        )

                        if all_ok:
                            old_cost = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
                            new_cost = specs['cost_on']

                            if new_cost < old_cost:
                                # Merge
                                antennas[i] = {
                                    'type': atype,
                                    'x': pos[0],
                                    'y': pos[1],
                                    'buildings': all_bids,
                                    'pop': combined_pop
                                }
                                antennas[j] = None
                                merged = True
                                break
                    if merged:
                        break
                if merged:
                    break

        # Clean up None entries periodically
        if iterations % 100 == 0:
            antennas = [a for a in antennas if a is not None]

    antennas = [a for a in antennas if a is not None]

    # Remove 'pop' field
    for a in antennas:
        del a['pop']

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

    # Strategy 1: Greedy best with many seeds
    print("\nTrying greedy best with multiple seeds...")
    for seed in range(20):
        antennas = solve_greedy_best(buildings, seed=seed)
        antennas = optimize_types(antennas, bmap)
        cost = calculate_cost(antennas)
        if cost < best_cost:
            best_cost = cost
            best_solution = antennas
            print(f"  Seed {seed}: {cost:,} EUR * NEW BEST")
        else:
            print(f"  Seed {seed}: {cost:,} EUR")

    # Strategy 2: Priority queue
    print("\nTrying priority queue algorithm...")
    antennas = solve_priority_queue(buildings)
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas
        print(f"  Priority queue: {cost:,} EUR * NEW BEST")
    else:
        print(f"  Priority queue: {cost:,} EUR")

    # Strategy 3: Cluster merge
    print("\nTrying cluster merge algorithm...")
    antennas = solve_cluster_merge(buildings)
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas
        print(f"  Cluster merge: {cost:,} EUR * NEW BEST")
    else:
        print(f"  Cluster merge: {cost:,} EUR")

    # Validate
    solution = {'antennas': best_solution}
    score, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\n{'='*60}")
    print(f"BEST: {best_cost:,} EUR ({len(best_solution)} antennas)")
    print(f"Validation: {msg}")
    print('='*60)

    if valid:
        output = f'./solutions/solution_3_suburbia_{score}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")


if __name__ == "__main__":
    main()
