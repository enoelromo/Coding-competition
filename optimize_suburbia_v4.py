"""
Suburbia V4 - Use MaxRange for isolated buildings
==================================================

327 buildings are isolated (>150m from neighbors).
MaxRange has 400m range - can potentially cover multiple isolated buildings!
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


def dist(x1, y1, x2, y2):
    return math.sqrt(dist_sq(x1, y1, x2, y2))


def solve_hybrid(buildings):
    """
    Hybrid approach:
    1. Use Density for dense clusters
    2. Use MaxRange for isolated buildings (can cover more area)
    """
    bmap = {b['id']: b for b in buildings}
    n = len(buildings)

    # Classify buildings by isolation
    isolated = set()  # Buildings where nearest neighbor > 150
    clustered = set()

    for b in buildings:
        min_dist = float('inf')
        for other in buildings:
            if other['id'] == b['id']:
                continue
            d = dist(b['x'], b['y'], other['x'], other['y'])
            if d < min_dist:
                min_dist = d

        if min_dist > 150:
            isolated.add(b['id'])
        else:
            clustered.add(b['id'])

    print(f"  Isolated buildings: {len(isolated)}")
    print(f"  Clustered buildings: {len(clustered)}")

    # Build grid
    cell_size = 200
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Phase 1: Handle high-population buildings (>3500) with Density
    for b in buildings:
        if b['id'] not in uncovered:
            continue
        pop = get_max_pop(b)
        if pop > 3500:
            antennas.append({
                'type': 'Density',
                'x': b['x'],
                'y': b['y'],
                'buildings': [b['id']]
            })
            uncovered.discard(b['id'])

    # Phase 2: Use MaxRange for isolated buildings
    isolated_uncovered = [bmap[bid] for bid in isolated if bid in uncovered]
    isolated_uncovered.sort(key=lambda b: (b['x'], b['y']))

    for b in isolated_uncovered:
        if b['id'] not in uncovered:
            continue

        # Try MaxRange first for isolated
        specs = ANTENNA_TYPES['MaxRange']
        r2 = specs['range'] ** 2

        cx, cy = b['x'] // cell_size, b['y'] // cell_size
        cells_check = 2

        in_range = []
        for dx in range(-cells_check, cells_check + 1):
            for dy in range(-cells_check, cells_check + 1):
                for bb in grid[(cx + dx, cy + dy)]:
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

        if len(selected) >= 2:  # Only use MaxRange if covering 2+
            antennas.append({
                'type': 'MaxRange',
                'x': b['x'],
                'y': b['y'],
                'buildings': selected
            })
            for bid in selected:
                uncovered.discard(bid)

    # Phase 3: Use Density for clustered buildings
    clustered_uncovered = [bmap[bid] for bid in clustered if bid in uncovered]

    for b in clustered_uncovered:
        if b['id'] not in uncovered:
            continue

        specs = ANTENNA_TYPES['Density']
        r2 = specs['range'] ** 2

        cx, cy = b['x'] // cell_size, b['y'] // cell_size

        in_range = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for bb in grid[(cx + dx, cy + dy)]:
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

        if selected:
            antennas.append({
                'type': 'Density',
                'x': b['x'],
                'y': b['y'],
                'buildings': selected
            })
            for bid in selected:
                uncovered.discard(bid)

    # Phase 4: Handle remaining with any antenna type
    remaining = list(uncovered)
    for bid in remaining:
        if bid not in uncovered:
            continue

        b = bmap[bid]
        pop = get_max_pop(b)

        # Find best option
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
                    for bb in grid[(cx + dx, cy + dy)]:
                        if bb['id'] in uncovered:
                            if dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= r2:
                                in_range.append((bb['id'], get_max_pop(bb)))

            in_range.sort(key=lambda x: x[1])
            selected = []
            total_pop = 0

            for obid, p in in_range:
                if total_pop + p <= specs['capacity']:
                    selected.append(obid)
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
            for obid in best['buildings']:
                uncovered.discard(obid)

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

    print("\nTrying hybrid algorithm (MaxRange for isolated)...")
    antennas = solve_hybrid(buildings)
    antennas = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    print(f"Result: {cost:,} EUR ({len(antennas)} antennas)")

    # Count antenna types
    from collections import Counter
    types = Counter(a['type'] for a in antennas)
    for t, c in types.items():
        print(f"  {t}: {c}")

    # Validate
    solution = {'antennas': antennas}
    score, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\nValidation: {msg}")

    if valid:
        output = f'./solutions/solution_3_suburbia_{score}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")


if __name__ == "__main__":
    main()
