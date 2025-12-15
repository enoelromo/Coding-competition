"""
Epitech Aggressive Optimization
===============================

More aggressive search for optimization opportunities.
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


def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def optimize_types(antennas, bmap):
    """Downgrade antenna types where possible."""
    result = []

    for ant in antennas:
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)
        current_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        best_type = ant['type']
        best_cost = current_cost

        for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            r2 = specs['range'] ** 2
            all_ok = all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= r2 for b in blds)

            if all_ok and specs['cost_on'] < best_cost:
                best_type = atype
                best_cost = specs['cost_on']

        result.append({
            'type': best_type,
            'x': ant['x'],
            'y': ant['y'],
            'buildings': list(ant['buildings'])
        })

    return result


def try_absorb_into_multi(antennas, bmap):
    """Try to absorb single-building antennas into nearby multi-building ones."""
    cell_size = 200
    grid = defaultdict(list)

    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    single_indices = [i for i, a in enumerate(antennas) if len(a['buildings']) == 1]
    multi_indices = [i for i, a in enumerate(antennas) if len(a['buildings']) > 1]

    absorbed = set()
    absorptions = []

    for si in single_indices:
        sant = antennas[si]
        sbid = sant['buildings'][0]
        sb = bmap[sbid]
        spop = get_max_pop(sb)
        scost = ANTENNA_TYPES[sant['type']]['cost_on']

        cx, cy = sant['x'] // cell_size, sant['y'] // cell_size

        best_target = None
        best_savings = 0

        for dx in range(-4, 5):
            for dy in range(-4, 5):
                for mi in grid[(cx + dx, cy + dy)]:
                    if mi == si or mi in absorbed:
                        continue

                    mant = antennas[mi]
                    mblds = [bmap[bid] for bid in mant['buildings']]
                    mpop = sum(get_max_pop(b) for b in mblds)
                    mcost = ANTENNA_TYPES[mant['type']]['cost_on']

                    combined_pop = mpop + spop

                    # Try each antenna type
                    for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                        specs = ANTENNA_TYPES[atype]

                        if combined_pop > specs['capacity']:
                            continue

                        r2 = specs['range'] ** 2

                        # Check all current buildings in range
                        all_ok = all(
                            dist_sq(mant['x'], mant['y'], b['x'], b['y']) <= r2
                            for b in mblds
                        )
                        if not all_ok:
                            continue

                        # Check new building in range
                        if dist_sq(mant['x'], mant['y'], sb['x'], sb['y']) > r2:
                            continue

                        # Calculate savings
                        old_cost = scost + mcost
                        new_cost = specs['cost_on']
                        savings = old_cost - new_cost

                        if savings > best_savings:
                            best_savings = savings
                            best_target = (mi, atype)

                        break

        if best_target:
            ti, new_type = best_target
            absorptions.append((si, ti, new_type, best_savings))

    # Apply absorptions (sorted by savings)
    absorptions.sort(key=lambda x: -x[3])

    used_targets = set()
    for si, ti, new_type, savings in absorptions:
        if si in absorbed or ti in used_targets:
            continue

        sbid = antennas[si]['buildings'][0]
        antennas[ti]['buildings'].append(sbid)
        antennas[ti]['type'] = new_type
        absorbed.add(si)
        used_targets.add(ti)

    # Remove absorbed antennas
    result = [a for i, a in enumerate(antennas) if i not in absorbed]

    return result, len(absorbed)


def try_wide_merge(antennas, bmap):
    """Try to merge antennas with wider search radius."""
    cell_size = 200
    grid = defaultdict(list)

    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    merged = set()
    new_antennas = []
    merge_count = 0

    indices = sorted(range(len(antennas)), key=lambda i: len(antennas[i]['buildings']))

    for i in indices:
        if i in merged:
            continue

        a1 = antennas[i]
        blds1 = [bmap[bid] for bid in a1['buildings']]
        pop1 = sum(get_max_pop(b) for b in blds1)
        cost1 = ANTENNA_TYPES[a1['type']]['cost_on']

        cx, cy = a1['x'] // cell_size, a1['y'] // cell_size

        best_merge = None
        best_savings = 0

        for dx in range(-5, 6):
            for dy in range(-5, 6):
                for j in grid[(cx + dx, cy + dy)]:
                    if j <= i or j in merged:
                        continue

                    a2 = antennas[j]
                    blds2 = [bmap[bid] for bid in a2['buildings']]
                    pop2 = sum(get_max_pop(b) for b in blds2)
                    cost2 = ANTENNA_TYPES[a2['type']]['cost_on']

                    combined_pop = pop1 + pop2
                    all_blds = blds1 + blds2

                    # Try all building positions as potential antenna positions
                    positions = [(b['x'], b['y']) for b in all_blds]
                    positions.extend([(a1['x'], a1['y']), (a2['x'], a2['y'])])

                    for pos in positions:
                        for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                            specs = ANTENNA_TYPES[atype]

                            if combined_pop > specs['capacity']:
                                continue

                            r2 = specs['range'] ** 2
                            all_ok = all(
                                dist_sq(pos[0], pos[1], b['x'], b['y']) <= r2
                                for b in all_blds
                            )

                            if not all_ok:
                                continue

                            savings = cost1 + cost2 - specs['cost_on']

                            if savings > best_savings:
                                best_savings = savings
                                best_merge = {
                                    'j': j,
                                    'type': atype,
                                    'x': pos[0],
                                    'y': pos[1],
                                    'buildings': a1['buildings'] + a2['buildings']
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


def main():
    from score_function import getSolutionScore

    print("Loading epitech dataset...")
    with open('./datasets/4_epitech.json') as f:
        dataset = json.load(f)

    print("Loading best solution...")
    with open('./solutions/solution_4_epitech_40440000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']
    original_cost = calculate_cost(antennas)

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {original_cost:,} EUR")

    best_antennas = antennas
    best_cost = original_cost

    for iteration in range(20):
        print(f"\n=== ITERATION {iteration + 1} ===")

        # Try absorption
        antennas, absorbed = try_absorb_into_multi([dict(a) for a in best_antennas], bmap)
        print(f"  Absorbed: {absorbed}")

        # Optimize types
        antennas = optimize_types(antennas, bmap)

        # Try wide merge
        antennas, merges = try_wide_merge(antennas, bmap)
        print(f"  Merges: {merges}")

        # Optimize types again
        antennas = optimize_types(antennas, bmap)

        # Validate
        solution = {'antennas': antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"  Cost: {cost:,} EUR ({len(antennas)} antennas)")

        if valid and cost < best_cost:
            print(f"  * NEW BEST! Savings: {best_cost - cost:,} EUR")
            best_cost = cost
            best_antennas = antennas
        elif absorbed == 0 and merges == 0:
            print("  No more improvements possible")
            break

    print("\n" + "="*60)
    print(f"FINAL: {best_cost:,} EUR ({len(best_antennas)} antennas)")
    print(f"Total savings from start: {original_cost - best_cost:,} EUR")
    print("="*60)

    if best_cost < original_cost:
        output = f'./solutions/solution_4_epitech_{best_cost}.json'
        solution = {'antennas': best_antennas}
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    else:
        print("No improvement from this run")


if __name__ == "__main__":
    main()
