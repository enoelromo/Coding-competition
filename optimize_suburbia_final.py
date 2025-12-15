"""
Suburbia Final Optimization
============================

Aggressive optimization focusing on:
1. Reassigning buildings between antennas
2. Downgrading antenna types
3. Using MaxRange to connect isolated buildings
4. Merging under-utilized antennas
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


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def optimize_types(antennas, bmap):
    """Downgrade antenna types where possible."""
    result = []
    savings = 0

    for ant in antennas:
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)

        best_type = ant['type']
        best_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            r2 = specs['range'] ** 2
            all_ok = all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= r2 for b in blds)

            if all_ok and specs['cost_on'] < best_cost:
                best_type = atype
                best_cost = specs['cost_on']

        if best_type != ant['type']:
            savings += ANTENNA_TYPES[ant['type']]['cost_on'] - best_cost

        result.append({
            'type': best_type,
            'x': ant['x'],
            'y': ant['y'],
            'buildings': ant['buildings']
        })

    return result, savings


def try_reassign_buildings(antennas, bmap):
    """
    Try to reassign buildings from single-building antennas to nearby multi-building antennas.
    """
    # Build spatial index of antennas
    cell_size = 200
    grid = defaultdict(list)
    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    # Find single-building antennas
    single_indices = [i for i, a in enumerate(antennas) if len(a['buildings']) == 1]

    reassignments = 0
    removed = set()

    for si in single_indices:
        if si in removed:
            continue

        sant = antennas[si]
        sbid = sant['buildings'][0]
        sb = bmap[sbid]
        spop = get_max_pop(sb)

        cx, cy = sant['x'] // cell_size, sant['y'] // cell_size

        # Look for nearby antennas that could absorb this building
        best_target = None
        best_savings = 0

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for ti in grid[(cx + dx, cy + dy)]:
                    if ti == si or ti in removed:
                        continue

                    tant = antennas[ti]

                    # Check if building is in range of target antenna
                    for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                        specs = ANTENNA_TYPES[atype]

                        # Check range
                        if dist_sq(tant['x'], tant['y'], sb['x'], sb['y']) > specs['range'] ** 2:
                            continue

                        # Check if all current buildings + new one fit
                        current_pop = sum(get_max_pop(bmap[bid]) for bid in tant['buildings'])
                        if current_pop + spop > specs['capacity']:
                            continue

                        # Check if current buildings still in range
                        all_ok = all(
                            dist_sq(tant['x'], tant['y'], bmap[bid]['x'], bmap[bid]['y']) <= specs['range'] ** 2
                            for bid in tant['buildings']
                        )
                        if not all_ok:
                            continue

                        # Calculate savings
                        old_target_cost = ANTENNA_TYPES[tant['type']]['cost_on']
                        new_target_cost = ANTENNA_TYPES[atype]['cost_on']
                        source_cost = ANTENNA_TYPES[sant['type']]['cost_on']

                        savings = source_cost + old_target_cost - new_target_cost

                        if savings > best_savings:
                            best_savings = savings
                            best_target = (ti, atype)

                        break  # Found valid type

        if best_target:
            ti, new_type = best_target
            antennas[ti]['buildings'].append(sbid)
            antennas[ti]['type'] = new_type
            removed.add(si)
            reassignments += 1

    # Remove reassigned antennas
    result = [a for i, a in enumerate(antennas) if i not in removed]

    return result, reassignments


def aggressive_merge(antennas, bmap):
    """
    Aggressively try to merge antennas, including using MaxRange for distant ones.
    """
    cell_size = 200
    grid = defaultdict(list)

    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    merged = set()
    new_antennas = []
    merge_count = 0

    # Sort by number of buildings (merge small ones first)
    indices = sorted(range(len(antennas)), key=lambda i: len(antennas[i]['buildings']))

    for i in indices:
        if i in merged:
            continue

        a1 = antennas[i]
        cx, cy = a1['x'] // cell_size, a1['y'] // cell_size

        best_merge = None
        best_savings = 0

        # Check nearby cells (larger radius for MaxRange)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for j in grid[(cx + dx, cy + dy)]:
                    if j <= i or j in merged:
                        continue

                    a2 = antennas[j]

                    all_bids = a1['buildings'] + a2['buildings']
                    all_blds = [bmap[bid] for bid in all_bids]
                    total_pop = sum(get_max_pop(b) for b in all_blds)

                    # Try both positions
                    for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
                        for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                            specs = ANTENNA_TYPES[atype]
                            if specs['capacity'] < total_pop:
                                continue

                            r2 = specs['range'] ** 2
                            all_ok = all(
                                dist_sq(pos[0], pos[1], b['x'], b['y']) <= r2
                                for b in all_blds
                            )

                            if not all_ok:
                                continue

                            old_cost = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
                            new_cost = specs['cost_on']
                            savings = old_cost - new_cost

                            if savings > best_savings:
                                best_savings = savings
                                best_merge = {
                                    'j': j,
                                    'type': atype,
                                    'x': pos[0],
                                    'y': pos[1],
                                    'buildings': all_bids
                                }

                            break

        if best_merge:
            merged.add(i)
            merged.add(best_merge['j'])
            new_antennas.append({
                'type': best_merge['type'],
                'x': best_merge['x'],
                'y': best_merge['y'],
                'buildings': best_merge['buildings']
            })
            merge_count += 1
        else:
            new_antennas.append(a1)

    return new_antennas, merge_count


def rebuild_from_scratch(buildings, seed=0):
    """
    Rebuild solution from scratch with better algorithm.
    """
    random.seed(seed)

    bmap = {b['id']: b for b in buildings}
    n = len(buildings)

    # Build spatial grid
    cell_size = 100
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Sort cells by density (dense first)
    cell_density = [(cell, len(blds)) for cell, blds in grid.items()]
    cell_density.sort(key=lambda x: -x[1])

    for cell, _ in cell_density:
        while True:
            cell_uncovered = [b for b in grid[cell] if b['id'] in uncovered]
            if not cell_uncovered:
                break

            # Try each building as antenna position
            best = None
            best_score = -1

            for anchor in cell_uncovered[:10]:  # Limit candidates
                cx, cy = cell

                for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                    specs = ANTENNA_TYPES[atype]
                    r2 = specs['range'] ** 2
                    cells_check = int(specs['range'] / cell_size) + 1

                    in_range = []
                    for dx in range(-cells_check, cells_check + 1):
                        for dy in range(-cells_check, cells_check + 1):
                            for b in grid[(cx + dx, cy + dy)]:
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

                    if not selected:
                        continue

                    # Score: buildings per cost
                    score = len(selected) * 1000000 / specs['cost_on']

                    if score > best_score:
                        best_score = score
                        best = {
                            'type': atype,
                            'x': anchor['x'],
                            'y': anchor['y'],
                            'buildings': selected
                        }

            if best:
                antennas.append(best)
                for bid in best['buildings']:
                    uncovered.discard(bid)
            else:
                # Fallback
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
                break

    return antennas


def main():
    from score_function import getSolutionScore

    print("Loading suburbia dataset...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    print(f"Buildings: {len(buildings)}")

    # Load current best
    print("\nLoading current best solution...")
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    antennas = sol['antennas']
    current_cost = calculate_cost(antennas)
    print(f"Current: {current_cost:,} EUR ({len(antennas)} antennas)")

    best_solution = antennas
    best_cost = current_cost

    # Phase 1: Optimize types
    print("\nPhase 1: Optimizing antenna types...")
    antennas, savings = optimize_types(antennas, bmap)
    cost = calculate_cost(antennas)
    print(f"  After type optimization: {cost:,} EUR (saved {savings:,})")
    if cost < best_cost:
        best_cost = cost
        best_solution = antennas

    # Phase 2: Reassign buildings
    print("\nPhase 2: Reassigning buildings...")
    for iteration in range(5):
        antennas, reassignments = try_reassign_buildings(list(best_solution), bmap)
        if reassignments == 0:
            break
        antennas, _ = optimize_types(antennas, bmap)
        cost = calculate_cost(antennas)
        print(f"  Iteration {iteration + 1}: {reassignments} reassignments, cost {cost:,} EUR")
        if cost < best_cost:
            best_cost = cost
            best_solution = antennas

    # Phase 3: Aggressive merge
    print("\nPhase 3: Aggressive merging...")
    for iteration in range(10):
        antennas, merges = aggressive_merge(list(best_solution), bmap)
        if merges == 0:
            break
        antennas, _ = optimize_types(antennas, bmap)
        cost = calculate_cost(antennas)
        print(f"  Iteration {iteration + 1}: {merges} merges, cost {cost:,} EUR")
        if cost < best_cost:
            best_cost = cost
            best_solution = antennas

    # Phase 4: Try rebuilding from scratch
    print("\nPhase 4: Trying fresh builds...")
    for seed in range(5):
        antennas = rebuild_from_scratch(buildings, seed=seed)
        antennas, _ = optimize_types(antennas, bmap)

        # Apply merge
        for _ in range(3):
            antennas, merges = aggressive_merge(antennas, bmap)
            if merges == 0:
                break
            antennas, _ = optimize_types(antennas, bmap)

        cost = calculate_cost(antennas)
        print(f"  Seed {seed}: {cost:,} EUR ({len(antennas)} antennas)")
        if cost < best_cost:
            best_cost = cost
            best_solution = antennas
            print("    * NEW BEST!")

    # Validate
    solution = {'antennas': best_solution}
    score, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\n{'='*60}")
    print(f"FINAL: {best_cost:,} EUR ({len(best_solution)} antennas)")
    print(f"Validation: {msg}")
    print('='*60)

    if valid:
        output = f'./solutions/solution_3_suburbia_{score}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")


if __name__ == "__main__":
    main()
