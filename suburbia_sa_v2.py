"""
Suburbia Simulated Annealing V2
===============================

Fixed version that validates solutions properly.
"""

import json
import math
import random
import copy
from collections import defaultdict

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


def validate_solution_fast(antennas, bmap, all_building_ids):
    """Fast validation without using getSolutionScore."""
    covered = set()

    for ant in antennas:
        if not ant['buildings']:
            return False

        blds = [bmap.get(bid) for bid in ant['buildings']]
        if None in blds:
            return False

        total_pop = sum(get_max_pop(b) for b in blds)
        specs = ANTENNA_TYPES[ant['type']]

        if total_pop > specs['capacity']:
            return False

        r2 = specs['range'] ** 2
        for b in blds:
            if dist_sq(ant['x'], ant['y'], b['x'], b['y']) > r2:
                return False
            covered.add(b['id'])

    # Check all buildings covered
    return covered == all_building_ids


def get_cheapest_valid_type(ant, bmap):
    """Find cheapest antenna type that can cover the buildings."""
    if not ant['buildings']:
        return None

    blds = [bmap[bid] for bid in ant['buildings']]
    total_pop = sum(get_max_pop(b) for b in blds)

    for atype in TYPE_ORDER:
        specs = ANTENNA_TYPES[atype]
        if specs['capacity'] < total_pop:
            continue

        r2 = specs['range'] ** 2
        all_ok = all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= r2 for b in blds)

        if all_ok:
            return atype

    return None


def try_move_building(antennas, bmap):
    """Move a building from one antenna to another."""
    if len(antennas) < 2:
        return None

    # Pick source with >1 buildings
    multi = [i for i, a in enumerate(antennas) if len(a['buildings']) > 1]
    if not multi:
        return None

    src_idx = random.choice(multi)
    src = antennas[src_idx]
    bid = random.choice(src['buildings'])
    b = bmap[bid]

    # Find valid target
    indices = list(range(len(antennas)))
    random.shuffle(indices)

    for tgt_idx in indices[:30]:
        if tgt_idx == src_idx:
            continue

        tgt = antennas[tgt_idx]

        # Quick distance check
        if dist_sq(tgt['x'], tgt['y'], b['x'], b['y']) > 400**2:
            continue

        # Try adding to target
        new_tgt_blds = tgt['buildings'] + [bid]
        new_tgt = {'x': tgt['x'], 'y': tgt['y'], 'buildings': new_tgt_blds, 'type': tgt['type']}
        new_tgt_type = get_cheapest_valid_type(new_tgt, bmap)

        if not new_tgt_type:
            continue

        # Try removing from source
        new_src_blds = [x for x in src['buildings'] if x != bid]
        new_src = {'x': src['x'], 'y': src['y'], 'buildings': new_src_blds, 'type': src['type']}
        new_src_type = get_cheapest_valid_type(new_src, bmap)

        if not new_src_type:
            continue

        # Build new solution
        new_antennas = []
        for i, a in enumerate(antennas):
            if i == src_idx:
                new_antennas.append({'x': a['x'], 'y': a['y'], 'buildings': new_src_blds, 'type': new_src_type})
            elif i == tgt_idx:
                new_antennas.append({'x': a['x'], 'y': a['y'], 'buildings': new_tgt_blds, 'type': new_tgt_type})
            else:
                new_antennas.append(copy.deepcopy(a))

        return new_antennas

    return None


def try_merge(antennas, bmap):
    """Try to merge two antennas."""
    if len(antennas) < 2:
        return None

    indices = list(range(len(antennas)))
    random.shuffle(indices)

    for i in indices[:30]:
        a1 = antennas[i]

        for j in indices[:30]:
            if j <= i:
                continue

            a2 = antennas[j]

            # Quick distance check
            if dist_sq(a1['x'], a1['y'], a2['x'], a2['y']) > 800**2:
                continue

            combined_blds = a1['buildings'] + a2['buildings']

            # Try positions
            for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
                new_ant = {'x': pos[0], 'y': pos[1], 'buildings': combined_blds, 'type': 'MaxRange'}
                new_type = get_cheapest_valid_type(new_ant, bmap)

                if new_type:
                    new_antennas = []
                    for k, a in enumerate(antennas):
                        if k == i:
                            new_antennas.append({'x': pos[0], 'y': pos[1], 'buildings': combined_blds, 'type': new_type})
                        elif k != j:
                            new_antennas.append(copy.deepcopy(a))

                    return new_antennas

    return None


def try_relocate(antennas, bmap):
    """Relocate antenna to a building position."""
    if not antennas:
        return None

    idx = random.randint(0, len(antennas) - 1)
    ant = antennas[idx]

    if not ant['buildings']:
        return None

    # Try moving to a random building position
    target_bid = random.choice(ant['buildings'])
    target_b = bmap[target_bid]

    new_ant = {'x': target_b['x'], 'y': target_b['y'], 'buildings': ant['buildings'], 'type': ant['type']}
    new_type = get_cheapest_valid_type(new_ant, bmap)

    if not new_type:
        return None

    new_antennas = []
    for i, a in enumerate(antennas):
        if i == idx:
            new_antennas.append({'x': target_b['x'], 'y': target_b['y'], 'buildings': list(a['buildings']), 'type': new_type})
        else:
            new_antennas.append(copy.deepcopy(a))

    return new_antennas


def neighbor(antennas, bmap):
    """Generate a random neighbor solution."""
    r = random.random()

    if r < 0.5:
        result = try_move_building(antennas, bmap)
    elif r < 0.8:
        result = try_merge(antennas, bmap)
    else:
        result = try_relocate(antennas, bmap)

    if result:
        return result

    # Fallback
    for func in [try_move_building, try_merge, try_relocate]:
        result = func(antennas, bmap)
        if result:
            return result

    return None


def simulated_annealing(antennas, bmap, all_bids,
                        initial_temp=10000,
                        cooling_rate=0.99997,
                        min_temp=0.01,
                        max_iterations=300000):
    """Run SA with proper validation."""

    current = [copy.deepcopy(a) for a in antennas]
    current_cost = calculate_cost(current)

    best = [copy.deepcopy(a) for a in current]
    best_cost = current_cost

    temp = initial_temp
    iteration = 0
    improvements = 0

    print(f"Starting SA: cost={current_cost:,}, temp={temp:.1f}")

    while temp > min_temp and iteration < max_iterations:
        new_solution = neighbor(current, bmap)

        if new_solution is None:
            iteration += 1
            temp *= cooling_rate
            continue

        # Validate before accepting
        if not validate_solution_fast(new_solution, bmap, all_bids):
            iteration += 1
            temp *= cooling_rate
            continue

        new_cost = calculate_cost(new_solution)
        delta = new_cost - current_cost

        # Accept?
        if delta < 0 or random.random() < math.exp(-delta / temp):
            current = new_solution
            current_cost = new_cost

            if current_cost < best_cost:
                best = [copy.deepcopy(a) for a in current]
                best_cost = current_cost
                improvements += 1
                print(f"  Iter {iteration}: NEW BEST {best_cost:,} EUR (temp={temp:.1f})")

        iteration += 1
        temp *= cooling_rate

        if iteration % 20000 == 0:
            print(f"  Iter {iteration}: current={current_cost:,}, best={best_cost:,}, temp={temp:.2f}")

    print(f"\nSA done: {iteration} iters, {improvements} improvements")
    return best, best_cost


def main():
    from score_function import getSolutionScore

    print("="*60)
    print("SIMULATED ANNEALING V2 FOR SUBURBIA")
    print("="*60)

    print("\nLoading data...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    all_bids = set(b['id'] for b in buildings)
    antennas = sol['antennas']
    original_cost = calculate_cost(antennas)

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {original_cost:,} EUR")

    print("\n" + "="*60)
    print("Running Simulated Annealing V2...")
    print("="*60 + "\n")

    best_antennas, best_cost = simulated_annealing(
        antennas, bmap, all_bids,
        initial_temp=5000,
        cooling_rate=0.99998,
        min_temp=0.001,
        max_iterations=500000
    )

    # Final validation
    solution = {'antennas': best_antennas}
    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print("\n" + "="*60)
    print(f"RESULT: {msg}")
    print(f"Final cost: {cost:,} EUR ({len(best_antennas)} antennas)")
    print(f"Original: {original_cost:,} EUR")
    print("="*60)

    if valid and cost < original_cost:
        savings = original_cost - cost
        print(f"\nIMPROVED! Savings: {savings:,} EUR")
        output = f'./solutions/solution_3_suburbia_{cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")


if __name__ == "__main__":
    random.seed(42)
    main()
