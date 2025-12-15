"""
Suburbia Simulated Annealing
============================

Use simulated annealing to escape local optima and find better solutions.
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


def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def is_valid_antenna(ant, bmap):
    """Check if antenna configuration is valid."""
    if not ant['buildings']:
        return False

    blds = [bmap[bid] for bid in ant['buildings']]
    total_pop = sum(get_max_pop(b) for b in blds)
    specs = ANTENNA_TYPES[ant['type']]

    if total_pop > specs['capacity']:
        return False

    r2 = specs['range'] ** 2
    for b in blds:
        if dist_sq(ant['x'], ant['y'], b['x'], b['y']) > r2:
            return False

    return True


def get_cheapest_valid_type(ant, bmap):
    """Find the cheapest antenna type that can cover the buildings."""
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


def optimize_antenna_type(ant, bmap):
    """Optimize a single antenna's type to cheapest valid option."""
    best_type = get_cheapest_valid_type(ant, bmap)
    if best_type:
        ant['type'] = best_type
    return ant


def move_building(antennas, bmap, buildings):
    """Move a random building from one antenna to another."""
    if len(antennas) < 2:
        return None

    # Pick source antenna with at least 2 buildings
    multi_indices = [i for i, a in enumerate(antennas) if len(a['buildings']) > 1]
    if not multi_indices:
        return None

    src_idx = random.choice(multi_indices)
    src_ant = antennas[src_idx]

    # Pick random building to move
    bid = random.choice(src_ant['buildings'])
    b = bmap[bid]

    # Try to find a target antenna that can accept this building
    indices = list(range(len(antennas)))
    random.shuffle(indices)

    for tgt_idx in indices:
        if tgt_idx == src_idx:
            continue

        tgt_ant = antennas[tgt_idx]

        # Check if building is within MaxRange of target
        if dist(tgt_ant['x'], tgt_ant['y'], b['x'], b['y']) > 400:
            continue

        # Try to add building to target
        new_tgt = copy.deepcopy(tgt_ant)
        new_tgt['buildings'].append(bid)

        # Find valid type for new configuration
        new_type = get_cheapest_valid_type(new_tgt, bmap)
        if not new_type:
            continue

        new_tgt['type'] = new_type

        # Create new source without the building
        new_src = copy.deepcopy(src_ant)
        new_src['buildings'].remove(bid)
        new_src_type = get_cheapest_valid_type(new_src, bmap)
        if not new_src_type:
            continue
        new_src['type'] = new_src_type

        # Apply changes
        new_antennas = copy.deepcopy(antennas)
        new_antennas[src_idx] = new_src
        new_antennas[tgt_idx] = new_tgt

        return new_antennas

    return None


def merge_antennas(antennas, bmap, buildings):
    """Try to merge two random antennas."""
    if len(antennas) < 2:
        return None

    indices = list(range(len(antennas)))
    random.shuffle(indices)

    for i in indices[:20]:  # Limit attempts
        for j in indices[:20]:
            if j <= i:
                continue

            a1 = antennas[i]
            a2 = antennas[j]

            # Check distance
            if dist(a1['x'], a1['y'], a2['x'], a2['y']) > 800:
                continue

            combined_bids = a1['buildings'] + a2['buildings']
            combined_blds = [bmap[bid] for bid in combined_bids]
            combined_pop = sum(get_max_pop(b) for b in combined_blds)

            # Try positions
            positions = [
                (a1['x'], a1['y']),
                (a2['x'], a2['y']),
                ((a1['x'] + a2['x']) // 2, (a1['y'] + a2['y']) // 2)
            ]

            for px, py in positions:
                for atype in TYPE_ORDER:
                    specs = ANTENNA_TYPES[atype]

                    if combined_pop > specs['capacity']:
                        continue

                    r2 = specs['range'] ** 2
                    all_ok = all(dist_sq(px, py, b['x'], b['y']) <= r2 for b in combined_blds)

                    if all_ok:
                        new_antennas = [a for k, a in enumerate(antennas) if k != i and k != j]
                        new_antennas.append({
                            'type': atype,
                            'x': px,
                            'y': py,
                            'buildings': combined_bids
                        })
                        return new_antennas

    return None


def split_antenna(antennas, bmap, buildings):
    """Split a random antenna with multiple buildings into two."""
    multi_indices = [i for i, a in enumerate(antennas) if len(a['buildings']) >= 2]
    if not multi_indices:
        return None

    idx = random.choice(multi_indices)
    ant = antennas[idx]

    # Randomly split buildings
    bids = ant['buildings'][:]
    random.shuffle(bids)
    mid = len(bids) // 2
    if mid == 0:
        mid = 1

    bids1 = bids[:mid]
    bids2 = bids[mid:]

    # Create two new antennas
    blds1 = [bmap[bid] for bid in bids1]
    blds2 = [bmap[bid] for bid in bids2]

    # Position at centroid of buildings
    x1 = sum(b['x'] for b in blds1) // len(blds1)
    y1 = sum(b['y'] for b in blds1) // len(blds1)
    x2 = sum(b['x'] for b in blds2) // len(blds2)
    y2 = sum(b['y'] for b in blds2) // len(blds2)

    ant1 = {'x': x1, 'y': y1, 'buildings': bids1, 'type': 'Density'}
    ant2 = {'x': x2, 'y': y2, 'buildings': bids2, 'type': 'Density'}

    type1 = get_cheapest_valid_type(ant1, bmap)
    type2 = get_cheapest_valid_type(ant2, bmap)

    if not type1 or not type2:
        return None

    ant1['type'] = type1
    ant2['type'] = type2

    new_antennas = [a for k, a in enumerate(antennas) if k != idx]
    new_antennas.append(ant1)
    new_antennas.append(ant2)

    return new_antennas


def relocate_antenna(antennas, bmap, buildings):
    """Relocate a random antenna to a building position."""
    if not antennas:
        return None

    idx = random.randint(0, len(antennas) - 1)
    ant = antennas[idx]

    # Try moving to a random building position
    blds = [bmap[bid] for bid in ant['buildings']]
    target_b = random.choice(blds)

    new_ant = copy.deepcopy(ant)
    new_ant['x'] = target_b['x']
    new_ant['y'] = target_b['y']

    new_type = get_cheapest_valid_type(new_ant, bmap)
    if not new_type:
        return None

    new_ant['type'] = new_type

    new_antennas = copy.deepcopy(antennas)
    new_antennas[idx] = new_ant

    return new_antennas


def random_neighbor(antennas, bmap, buildings):
    """Generate a random neighboring solution."""
    moves = [
        (move_building, 0.4),
        (merge_antennas, 0.3),
        (split_antenna, 0.15),
        (relocate_antenna, 0.15)
    ]

    r = random.random()
    cumulative = 0

    for move_func, prob in moves:
        cumulative += prob
        if r < cumulative:
            result = move_func(antennas, bmap, buildings)
            if result:
                return result
            break

    # Fallback: try all moves
    for move_func, _ in moves:
        result = move_func(antennas, bmap, buildings)
        if result:
            return result

    return None


def simulated_annealing(antennas, bmap, buildings,
                        initial_temp=100000,
                        cooling_rate=0.9995,
                        min_temp=1,
                        max_iterations=100000):
    """Run simulated annealing optimization."""

    current = copy.deepcopy(antennas)
    current_cost = calculate_cost(current)

    best = copy.deepcopy(current)
    best_cost = current_cost

    temp = initial_temp
    iteration = 0
    accepted = 0
    improved = 0

    print(f"Starting SA: cost={current_cost:,}, temp={temp:.1f}")

    while temp > min_temp and iteration < max_iterations:
        # Generate neighbor
        neighbor = random_neighbor(current, bmap, buildings)

        if neighbor is None:
            iteration += 1
            temp *= cooling_rate
            continue

        neighbor_cost = calculate_cost(neighbor)
        delta = neighbor_cost - current_cost

        # Accept or reject
        if delta < 0:
            # Better solution - always accept
            current = neighbor
            current_cost = neighbor_cost
            accepted += 1

            if current_cost < best_cost:
                best = copy.deepcopy(current)
                best_cost = current_cost
                improved += 1
                print(f"  Iter {iteration}: NEW BEST {best_cost:,} EUR (temp={temp:.1f})")

        elif random.random() < math.exp(-delta / temp):
            # Worse solution - accept with probability
            current = neighbor
            current_cost = neighbor_cost
            accepted += 1

        iteration += 1
        temp *= cooling_rate

        # Progress report
        if iteration % 10000 == 0:
            print(f"  Iter {iteration}: current={current_cost:,}, best={best_cost:,}, "
                  f"temp={temp:.1f}, accepted={accepted}")

    print(f"\nSA finished: {iteration} iterations, {accepted} accepted, {improved} improvements")

    return best, best_cost


def main():
    from score_function import getSolutionScore

    print("="*60)
    print("SIMULATED ANNEALING FOR SUBURBIA")
    print("="*60)

    print("\nLoading data...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']
    original_cost = calculate_cost(antennas)

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {original_cost:,} EUR")

    # Run simulated annealing
    print("\n" + "="*60)
    print("Running Simulated Annealing...")
    print("="*60 + "\n")

    best_antennas, best_cost = simulated_annealing(
        antennas, bmap, buildings,
        initial_temp=50000,
        cooling_rate=0.99995,
        min_temp=0.1,
        max_iterations=200000
    )

    # Validate
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
    elif valid:
        print(f"\nNo improvement found (diff: {cost - original_cost:,} EUR)")
    else:
        print("\nINVALID SOLUTION - checking best known valid...")


if __name__ == "__main__":
    random.seed(42)
    main()
