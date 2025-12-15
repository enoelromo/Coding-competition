"""
Manhattan Optimization
======================

Optimize dataset 6 (Manhattan).
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


def optimize_types(antennas, bmap):
    """Downgrade antenna types where possible."""
    result = []
    savings = 0

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

        if best_type != ant['type']:
            savings += current_cost - best_cost

        result.append({
            'type': best_type,
            'x': ant['x'],
            'y': ant['y'],
            'buildings': list(ant['buildings'])
        })

    return result, savings


def find_reposition_improvements(buildings, antennas, bmap):
    """Find antennas that could be repositioned to cover more buildings."""
    cell_size = 200
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    building_to_antenna = {}
    for i, ant in enumerate(antennas):
        for bid in ant['buildings']:
            building_to_antenna[bid] = i

    improved = 0
    new_antennas = []

    for i, ant in enumerate(antennas):
        current_blds = [bmap[bid] for bid in ant['buildings']]
        current_pop = sum(get_max_pop(b) for b in current_blds)

        cx = sum(b['x'] for b in current_blds) // len(current_blds)
        cy = sum(b['y'] for b in current_blds) // len(current_blds)
        cx_cell, cy_cell = cx // cell_size, cy // cell_size

        best_pos = (ant['x'], ant['y'])
        best_type = ant['type']
        best_buildings = list(ant['buildings'])
        best_score = len(ant['buildings']) * 1000000 / ANTENNA_TYPES[ant['type']]['cost_on']

        for dx in range(-4, 5):
            for dy in range(-4, 5):
                for candidate_b in grid[(cx_cell + dx, cy_cell + dy)]:
                    pos = (candidate_b['x'], candidate_b['y'])

                    for atype in ['Density', 'MaxRange', 'Spot', 'Nano']:
                        specs = ANTENNA_TYPES[atype]
                        r2 = specs['range'] ** 2

                        all_current_ok = all(
                            dist_sq(pos[0], pos[1], b['x'], b['y']) <= r2
                            for b in current_blds
                        )
                        if not all_current_ok:
                            continue

                        covered_pop = current_pop
                        covered_bids = list(ant['buildings'])

                        check_range = int(specs['range'] / cell_size) + 1
                        pos_cell = (pos[0] // cell_size, pos[1] // cell_size)

                        for ddx in range(-check_range, check_range + 1):
                            for ddy in range(-check_range, check_range + 1):
                                for extra_b in grid[(pos_cell[0] + ddx, pos_cell[1] + ddy)]:
                                    if extra_b['id'] in covered_bids:
                                        continue
                                    if building_to_antenna.get(extra_b['id']) is not None:
                                        continue

                                    if dist_sq(pos[0], pos[1], extra_b['x'], extra_b['y']) <= r2:
                                        extra_pop = get_max_pop(extra_b)
                                        if covered_pop + extra_pop <= specs['capacity']:
                                            covered_pop += extra_pop
                                            covered_bids.append(extra_b['id'])

                        score = len(covered_bids) * 1000000 / specs['cost_on']

                        if score > best_score:
                            best_pos = pos
                            best_type = atype
                            best_buildings = covered_bids
                            best_score = score

                        break

        if len(best_buildings) > len(ant['buildings']) or best_type != ant['type']:
            improved += 1

        new_antennas.append({
            'type': best_type,
            'x': best_pos[0],
            'y': best_pos[1],
            'buildings': best_buildings
        })

    return new_antennas, improved


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

        for dx in range(-4, 5):
            for dy in range(-4, 5):
                for j in grid[(cx + dx, cy + dy)]:
                    if j <= i:
                        continue

                    a2 = antennas[j]
                    blds2 = [bmap[bid] for bid in a2['buildings']]
                    pop2 = sum(get_max_pop(b) for b in blds2)
                    cost2 = ANTENNA_TYPES[a2['type']]['cost_on']

                    combined_pop = pop1 + pop2
                    all_blds = blds1 + blds2

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

                            if savings > 0:
                                opportunities.append((i, j, atype, pos, savings))
                            break

    return opportunities


def apply_merges(antennas, bmap):
    """Apply merge opportunities."""
    merges = find_merge_opportunities(antennas, bmap)

    if not merges:
        return antennas, 0

    merges.sort(key=lambda x: -x[4])
    merged = set()
    merge_list = []

    for i, j, atype, pos, savings in merges:
        if i in merged or j in merged:
            continue

        merged.add(i)
        merged.add(j)
        merge_list.append((i, j, atype, pos, savings))

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

    return new_antennas, len(merge_list)


def main():
    from score_function import getSolutionScore

    print("Loading Manhattan dataset...")
    with open('./datasets/6_manhattan.json') as f:
        dataset = json.load(f)

    print("Loading best solution...")
    with open('./solutions/solution_6_manhattan_33405000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']
    original_cost = calculate_cost(antennas)

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {original_cost:,} EUR")

    analyze_solution(antennas, bmap)

    best_antennas = antennas
    best_cost = original_cost

    for iteration in range(20):
        print(f"\n=== ITERATION {iteration + 1} ===")

        antennas, improved = find_reposition_improvements(buildings, best_antennas, bmap)
        antennas, type_savings = optimize_types(antennas, bmap)
        print(f"  Repositioned: {improved}, Type savings: {type_savings:,} EUR")

        antennas, merge_count = apply_merges(antennas, bmap)
        antennas, type_savings2 = optimize_types(antennas, bmap)
        print(f"  Merges: {merge_count}, Type savings: {type_savings2:,} EUR")

        solution = {'antennas': antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"  Cost: {cost:,} EUR ({len(antennas)} antennas)")

        if valid and cost < best_cost:
            print(f"  * NEW BEST! Savings: {best_cost - cost:,} EUR")
            best_cost = cost
            best_antennas = antennas
        elif improved == 0 and merge_count == 0 and type_savings == 0 and type_savings2 == 0:
            print("  No more improvements possible")
            break

    print("\n" + "="*60)
    print(f"FINAL: {best_cost:,} EUR ({len(best_antennas)} antennas)")
    print(f"Total savings: {original_cost - best_cost:,} EUR")
    print("="*60)

    if best_cost < original_cost:
        output = f'./solutions/solution_6_manhattan_{best_cost}.json'
        solution = {'antennas': best_antennas}
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    else:
        print("No improvement found")


if __name__ == "__main__":
    main()
