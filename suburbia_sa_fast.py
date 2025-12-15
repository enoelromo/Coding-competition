"""
Suburbia SA Fast - Optimized for speed
======================================
"""

import json
import math
import random
import copy

ANTENNA_TYPES = {
    'Nano': {'range': 50, 'capacity': 200, 'cost_on': 5_000},
    'Spot': {'range': 100, 'capacity': 800, 'cost_on': 15_000},
    'Density': {'range': 150, 'capacity': 5_000, 'cost_on': 30_000},
    'MaxRange': {'range': 400, 'capacity': 3_500, 'cost_on': 40_000}
}

TYPE_ORDER = ['Nano', 'Spot', 'Density', 'MaxRange']


def get_max_pop(b):
    return max(b['populationPeakHours'], b['populationOffPeakHours'], b['populationNight'])


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def get_cheapest_type(x, y, bids, bmap):
    """Find cheapest antenna type for given position and buildings."""
    blds = [bmap[bid] for bid in bids]
    total_pop = sum(get_max_pop(b) for b in blds)

    for atype in TYPE_ORDER:
        specs = ANTENNA_TYPES[atype]
        if specs['capacity'] < total_pop:
            continue

        r2 = specs['range'] ** 2
        if all(dist_sq(x, y, b['x'], b['y']) <= r2 for b in blds):
            return atype

    return None


def try_merge(antennas, bmap):
    """Try to merge two random antennas."""
    n = len(antennas)
    if n < 2:
        return None

    # Random selection
    i = random.randint(0, n - 1)
    j = random.randint(0, n - 1)
    if i == j:
        return None

    a1, a2 = antennas[i], antennas[j]

    # Quick check
    if dist_sq(a1['x'], a1['y'], a2['x'], a2['y']) > 640000:  # 800^2
        return None

    combined = a1['buildings'] + a2['buildings']

    # Try positions
    for px, py in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
        new_type = get_cheapest_type(px, py, combined, bmap)
        if new_type:
            # Check cost savings
            old_cost = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
            new_cost = ANTENNA_TYPES[new_type]['cost_on']

            if new_cost <= old_cost:  # Accept same cost (fewer antennas)
                new_antennas = [a for k, a in enumerate(antennas) if k not in (i, j)]
                new_antennas.append({
                    'type': new_type,
                    'x': px,
                    'y': py,
                    'buildings': combined
                })
                return new_antennas

    return None


def try_relocate(antennas, bmap):
    """Try to relocate an antenna to a better position."""
    if not antennas:
        return None

    idx = random.randint(0, len(antennas) - 1)
    ant = antennas[idx]

    if not ant['buildings']:
        return None

    # Pick random building as new position
    bid = random.choice(ant['buildings'])
    b = bmap[bid]

    new_type = get_cheapest_type(b['x'], b['y'], ant['buildings'], bmap)
    if not new_type:
        return None

    # Check improvement
    old_cost = ANTENNA_TYPES[ant['type']]['cost_on']
    new_cost = ANTENNA_TYPES[new_type]['cost_on']

    if new_cost < old_cost:
        new_antennas = [copy.deepcopy(a) for a in antennas]
        new_antennas[idx] = {
            'type': new_type,
            'x': b['x'],
            'y': b['y'],
            'buildings': list(ant['buildings'])
        }
        return new_antennas

    return None


def simulated_annealing(antennas, bmap, max_iter=100000, temp=1000, cooling=0.9999):
    """Fast SA focusing on merges."""
    current = [copy.deepcopy(a) for a in antennas]
    current_cost = calculate_cost(current)

    best = [copy.deepcopy(a) for a in current]
    best_cost = current_cost

    print(f"Start: {current_cost:,} EUR, {len(current)} antennas")

    for i in range(max_iter):
        # Try operations
        if random.random() < 0.7:
            new_sol = try_merge(current, bmap)
        else:
            new_sol = try_relocate(current, bmap)

        if new_sol is None:
            temp *= cooling
            continue

        new_cost = calculate_cost(new_sol)
        delta = new_cost - current_cost

        # Accept?
        if delta < 0 or (temp > 0.01 and random.random() < math.exp(-delta / temp)):
            current = new_sol
            current_cost = new_cost

            if current_cost < best_cost:
                best = [copy.deepcopy(a) for a in current]
                best_cost = current_cost
                print(f"  Iter {i}: NEW BEST {best_cost:,} EUR ({len(best)} antennas)")

        temp *= cooling

        if i % 20000 == 0 and i > 0:
            print(f"  Iter {i}: current={current_cost:,}, best={best_cost:,}, temp={temp:.2f}")

    return best, best_cost


def main():
    from score_function import getSolutionScore

    print("="*60)
    print("SUBURBIA SA FAST")
    print("="*60)

    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']
    original_cost = calculate_cost(antennas)

    print(f"Buildings: {len(buildings)}, Antennas: {len(antennas)}")
    print(f"Original: {original_cost:,} EUR\n")

    # Run SA
    best, best_cost = simulated_annealing(antennas, bmap, max_iter=100000)

    # Validate
    solution = {'antennas': best}
    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\n{'='*60}")
    print(f"RESULT: {msg}")
    print(f"Cost: {cost:,} EUR ({len(best)} antennas)")
    print(f"Original: {original_cost:,} EUR")

    if valid and cost < original_cost:
        print(f"\nSAVED: {original_cost - cost:,} EUR")
        with open(f'./solutions/solution_3_suburbia_{cost}.json', 'w') as f:
            json.dump(solution, f, indent=2)
    elif valid:
        print(f"\nNo improvement")


if __name__ == "__main__":
    random.seed(42)
    main()
