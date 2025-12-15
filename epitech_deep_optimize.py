"""
Epitech Deep Optimization
=========================

Comprehensive analysis and optimization for dataset 4.
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


def analyze_solution(antennas, bmap):
    """Detailed analysis of current solution."""
    print("\n=== SOLUTION ANALYSIS ===")

    type_counts = defaultdict(int)
    type_costs = defaultdict(int)
    single_building = defaultdict(list)
    multi_building = defaultdict(list)

    for i, ant in enumerate(antennas):
        atype = ant['type']
        type_counts[atype] += 1
        type_costs[atype] += ANTENNA_TYPES[atype]['cost_on']

        if len(ant['buildings']) == 1:
            single_building[atype].append(i)
        else:
            multi_building[atype].append(i)

    print("\nAntenna distribution:")
    for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
        if type_counts[atype] > 0:
            print(f"  {atype}: {type_counts[atype]} antennas, {type_costs[atype]:,} EUR")
            print(f"    - Single-building: {len(single_building[atype])}")
            print(f"    - Multi-building: {len(multi_building[atype])}")

    return single_building, multi_building


def find_downgrade_opportunities(antennas, bmap):
    """Find antennas that could use a cheaper type."""
    opportunities = []

    for i, ant in enumerate(antennas):
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)
        current_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        for atype in ['Nano', 'Spot', 'MaxRange', 'Density']:
            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue
            if specs['cost_on'] >= current_cost:
                continue

            r2 = specs['range'] ** 2
            all_ok = all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= r2 for b in blds)

            if all_ok:
                savings = current_cost - specs['cost_on']
                opportunities.append((i, ant['type'], atype, savings))
                break

    return opportunities


def find_absorption_opportunities(antennas, bmap):
    """Find single-building antennas that could be absorbed by nearby multi-building antennas."""
    cell_size = 200
    grid = defaultdict(list)

    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    opportunities = []

    for i, ant in enumerate(antennas):
        if len(ant['buildings']) != 1:
            continue

        bid = ant['buildings'][0]
        b = bmap[bid]
        pop = get_max_pop(b)
        current_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        cx, cy = ant['x'] // cell_size, ant['y'] // cell_size

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for j in grid[(cx + dx, cy + dy)]:
                    if j == i:
                        continue

                    target = antennas[j]
                    target_blds = [bmap[tbid] for tbid in target['buildings']]
                    target_pop = sum(get_max_pop(tb) for tb in target_blds)

                    # Check if building can be added to target
                    for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                        specs = ANTENNA_TYPES[atype]

                        if target_pop + pop > specs['capacity']:
                            continue

                        # Check range for all buildings including new one
                        r2 = specs['range'] ** 2
                        all_ok = all(
                            dist_sq(target['x'], target['y'], tb['x'], tb['y']) <= r2
                            for tb in target_blds
                        )
                        if not all_ok:
                            continue

                        if dist_sq(target['x'], target['y'], b['x'], b['y']) > r2:
                            continue

                        # Calculate savings
                        old_cost = current_cost + ANTENNA_TYPES[target['type']]['cost_on']
                        new_cost = specs['cost_on']
                        savings = old_cost - new_cost

                        if savings > 0:
                            opportunities.append((i, j, atype, savings))
                        break

    return opportunities


def find_merge_opportunities(antennas, bmap):
    """Find pairs of antennas that could be merged."""
    cell_size = 200
    grid = defaultdict(list)

    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    opportunities = []

    for i, a1 in enumerate(antennas):
        blds1 = [bmap[bid] for bid in a1['buildings']]
        pop1 = sum(get_max_pop(b) for b in blds1)
        cost1 = ANTENNA_TYPES[a1['type']]['cost_on']

        cx, cy = a1['x'] // cell_size, a1['y'] // cell_size

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for j in grid[(cx + dx, cy + dy)]:
                    if j <= i:
                        continue

                    a2 = antennas[j]
                    blds2 = [bmap[bid] for bid in a2['buildings']]
                    pop2 = sum(get_max_pop(b) for b in blds2)
                    cost2 = ANTENNA_TYPES[a2['type']]['cost_on']

                    combined_pop = pop1 + pop2
                    all_blds = blds1 + blds2

                    # Try both positions
                    for pos in [(a1['x'], a1['y']), (a2['x'], a2['y'])]:
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

                            if savings > 0:
                                opportunities.append((i, j, atype, pos, savings))
                            break

    return opportunities


def apply_optimizations(antennas, bmap):
    """Apply all possible optimizations."""
    antennas = [dict(a) for a in antennas]
    total_savings = 0

    # Phase 1: Downgrade types
    print("\nPhase 1: Downgrading antenna types...")
    downgrades = find_downgrade_opportunities(antennas, bmap)
    for i, old_type, new_type, savings in downgrades:
        antennas[i]['type'] = new_type
        total_savings += savings
    print(f"  Downgrades: {len(downgrades)}, Savings: {sum(d[3] for d in downgrades):,} EUR")

    # Phase 2: Absorptions
    print("\nPhase 2: Absorbing single-building antennas...")
    absorptions = find_absorption_opportunities(antennas, bmap)

    if absorptions:
        # Sort by savings (descending) and apply greedily
        absorptions.sort(key=lambda x: -x[3])
        absorbed = set()

        for source_i, target_j, new_type, savings in absorptions:
            if source_i in absorbed or target_j in absorbed:
                continue

            # Apply absorption
            bid = antennas[source_i]['buildings'][0]
            antennas[target_j]['buildings'].append(bid)
            antennas[target_j]['type'] = new_type
            absorbed.add(source_i)
            total_savings += savings

        # Remove absorbed antennas
        antennas = [a for i, a in enumerate(antennas) if i not in absorbed]
        print(f"  Absorptions: {len(absorbed)}, Savings: {sum(a[3] for a in absorptions if a[0] not in absorbed):,} EUR")
    else:
        print("  No absorption opportunities found")

    # Phase 3: Merges
    print("\nPhase 3: Merging antennas...")
    merges = find_merge_opportunities(antennas, bmap)

    if merges:
        merges.sort(key=lambda x: -x[4])
        merged = set()
        merge_list = []

        for i, j, atype, pos, savings in merges:
            if i in merged or j in merged:
                continue

            merged.add(i)
            merged.add(j)
            merge_list.append((i, j, atype, pos, savings))
            total_savings += savings

        # Apply merges
        new_antennas = []
        for i, j, atype, pos, _ in merge_list:
            new_antennas.append({
                'type': atype,
                'x': pos[0],
                'y': pos[1],
                'buildings': antennas[i]['buildings'] + antennas[j]['buildings']
            })

        for i, a in enumerate(antennas):
            if i not in merged:
                new_antennas.append(a)

        antennas = new_antennas
        print(f"  Merges: {len(merge_list)}, Savings: {sum(m[4] for m in merge_list):,} EUR")
    else:
        print("  No merge opportunities found")

    return antennas, total_savings


def analyze_isolation(antennas, bmap):
    """Analyze why single-building antennas can't be merged."""
    print("\n=== ISOLATION ANALYSIS ===")

    single_density = []
    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1 and ant['type'] == 'Density':
            bid = ant['buildings'][0]
            b = bmap[bid]
            single_density.append((i, bid, b, get_max_pop(b)))

    print(f"Single-building Density antennas: {len(single_density)}")

    # Find nearest neighbor for each
    isolation_reasons = {
        'distance_too_far': 0,
        'combined_pop_exceeds_density': 0,
        'combined_pop_exceeds_maxrange': 0,
        'could_merge': 0
    }

    for idx1, (i, bid1, b1, pop1) in enumerate(single_density):
        best_dist = float('inf')
        best_reason = None

        for idx2, (j, bid2, b2, pop2) in enumerate(single_density):
            if idx2 <= idx1:
                continue

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])
            combined_pop = pop1 + pop2

            if d < best_dist:
                best_dist = d

                if d <= 150 and combined_pop <= 5000:
                    best_reason = 'could_merge'
                elif d <= 400 and combined_pop <= 3500:
                    best_reason = 'could_merge'
                elif d > 400:
                    best_reason = 'distance_too_far'
                elif combined_pop > 5000:
                    best_reason = 'combined_pop_exceeds_density'
                elif combined_pop > 3500:
                    best_reason = 'combined_pop_exceeds_maxrange'

        if best_reason:
            isolation_reasons[best_reason] += 1

    print("\nIsolation reasons (for nearest neighbor):")
    for reason, count in isolation_reasons.items():
        print(f"  {reason}: {count}")

    # Check low-population pairs that could merge
    print("\n=== LOW POPULATION PAIRS ===")
    low_pop_pairs = []

    for idx1, (i, bid1, b1, pop1) in enumerate(single_density):
        if pop1 > 2500:  # Only consider lower-population buildings
            continue

        for idx2, (j, bid2, b2, pop2) in enumerate(single_density):
            if idx2 <= idx1:
                continue
            if pop2 > 2500:
                continue

            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])
            combined_pop = pop1 + pop2

            if d <= 150 and combined_pop <= 5000:
                low_pop_pairs.append((i, j, d, pop1, pop2, combined_pop, 'Density'))
            elif d <= 400 and combined_pop <= 3500:
                low_pop_pairs.append((i, j, d, pop1, pop2, combined_pop, 'MaxRange'))

    print(f"Found {len(low_pop_pairs)} low-population mergeable pairs")

    for pair in low_pop_pairs[:10]:
        print(f"  Pair: d={pair[2]:.1f}, pop1={pair[3]}, pop2={pair[4]}, combined={pair[5]}, type={pair[6]}")


def main():
    from score_function import getSolutionScore

    print("Loading epitech dataset...")
    with open('./datasets/4_epitech.json') as f:
        dataset = json.load(f)

    print("Loading current solution...")
    with open('./solutions/solution_4_epitech_40585000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {calculate_cost(antennas):,} EUR")

    # Analyze current solution
    single_building, multi_building = analyze_solution(antennas, bmap)

    # Analyze isolation
    analyze_isolation(antennas, bmap)

    # Try optimizations
    print("\n" + "="*60)
    print("APPLYING OPTIMIZATIONS")
    print("="*60)

    optimized_antennas, total_savings = apply_optimizations(antennas, bmap)

    # Validate
    solution = {'antennas': optimized_antennas}
    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print("\n" + "="*60)
    print(f"RESULT: {msg}")
    print(f"New cost: {cost:,} EUR ({len(optimized_antennas)} antennas)")
    print(f"Expected savings: {total_savings:,} EUR")
    print("="*60)

    if valid and cost < calculate_cost(antennas):
        output = f'./solutions/solution_4_epitech_{cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    else:
        print("No improvement or invalid solution")


if __name__ == "__main__":
    main()
