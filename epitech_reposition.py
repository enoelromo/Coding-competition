"""
Epitech Repositioning Optimization
==================================

Try repositioning antennas to optimal locations that could cover more buildings.
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


def find_optimal_positions(buildings, antennas, bmap):
    """
    For each antenna, try to find a better position by trying all building positions
    that could cover all current buildings plus possibly more.
    """
    cell_size = 200
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    # Track which buildings are covered by which antenna
    building_to_antenna = {}
    for i, ant in enumerate(antennas):
        for bid in ant['buildings']:
            building_to_antenna[bid] = i

    improved = 0
    new_antennas = []

    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1:
            # Single building - try to find if it could be merged with nearby uncovered
            new_antennas.append(dict(ant))
            continue

        current_blds = [bmap[bid] for bid in ant['buildings']]
        current_pop = sum(get_max_pop(b) for b in current_blds)

        cx = sum(b['x'] for b in current_blds) // len(current_blds)
        cy = sum(b['y'] for b in current_blds) // len(current_blds)
        cx_cell, cy_cell = cx // cell_size, cy // cell_size

        best_pos = (ant['x'], ant['y'])
        best_type = ant['type']
        best_buildings = ant['buildings']
        best_cost = ANTENNA_TYPES[ant['type']]['cost_on']

        # Try building positions as potential antenna positions
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for candidate_b in grid[(cx_cell + dx, cy_cell + dy)]:
                    pos = (candidate_b['x'], candidate_b['y'])

                    # For each antenna type, check what buildings could be covered
                    for atype in ['Density', 'MaxRange']:  # Focus on main types
                        specs = ANTENNA_TYPES[atype]
                        r2 = specs['range'] ** 2

                        # Must cover all current buildings
                        all_current_ok = all(
                            dist_sq(pos[0], pos[1], b['x'], b['y']) <= r2
                            for b in current_blds
                        )
                        if not all_current_ok:
                            continue

                        # Find additional buildings that could be covered
                        covered_pop = current_pop
                        covered_bids = list(ant['buildings'])

                        for extra_b in grid[(cx_cell + dx, cy_cell + dy)]:
                            if extra_b['id'] in covered_bids:
                                continue
                            if building_to_antenna.get(extra_b['id']) is not None:
                                continue  # Already covered by another antenna

                            if dist_sq(pos[0], pos[1], extra_b['x'], extra_b['y']) <= r2:
                                extra_pop = get_max_pop(extra_b)
                                if covered_pop + extra_pop <= specs['capacity']:
                                    covered_pop += extra_pop
                                    covered_bids.append(extra_b['id'])

                        # Check if this is an improvement
                        cost = specs['cost_on']
                        if len(covered_bids) > len(best_buildings) and cost <= best_cost:
                            best_pos = pos
                            best_type = atype
                            best_buildings = covered_bids
                            best_cost = cost
                        elif cost < best_cost and len(covered_bids) >= len(best_buildings):
                            best_pos = pos
                            best_type = atype
                            best_buildings = covered_bids
                            best_cost = cost

        if len(best_buildings) > len(ant['buildings']) or best_cost < ANTENNA_TYPES[ant['type']]['cost_on']:
            improved += 1

        new_antennas.append({
            'type': best_type,
            'x': best_pos[0],
            'y': best_pos[1],
            'buildings': best_buildings
        })

    return new_antennas, improved


def try_three_way_merge(antennas, bmap):
    """Try to merge 3 single-building antennas into one."""
    cell_size = 200
    grid = defaultdict(list)

    single_indices = []
    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1:
            single_indices.append(i)
            cell = (ant['x'] // cell_size, ant['y'] // cell_size)
            grid[cell].append(i)

    merges = []

    for i in single_indices:
        a1 = antennas[i]
        b1 = bmap[a1['buildings'][0]]
        p1 = get_max_pop(b1)
        c1 = ANTENNA_TYPES[a1['type']]['cost_on']

        cx, cy = a1['x'] // cell_size, a1['y'] // cell_size

        # Find nearby single-building antennas
        nearby = []
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for j in grid[(cx + dx, cy + dy)]:
                    if j != i:
                        nearby.append(j)

        # Try pairs from nearby
        for idx1, j in enumerate(nearby):
            a2 = antennas[j]
            b2 = bmap[a2['buildings'][0]]
            p2 = get_max_pop(b2)
            c2 = ANTENNA_TYPES[a2['type']]['cost_on']

            for k in nearby[idx1+1:]:
                a3 = antennas[k]
                b3 = bmap[a3['buildings'][0]]
                p3 = get_max_pop(b3)
                c3 = ANTENNA_TYPES[a3['type']]['cost_on']

                combined_pop = p1 + p2 + p3
                old_cost = c1 + c2 + c3

                # Try MaxRange (400m range, 3500 capacity)
                if combined_pop <= 3500:
                    # Try each building position
                    for pos in [(b1['x'], b1['y']), (b2['x'], b2['y']), (b3['x'], b3['y'])]:
                        d1 = dist(pos[0], pos[1], b1['x'], b1['y'])
                        d2 = dist(pos[0], pos[1], b2['x'], b2['y'])
                        d3 = dist(pos[0], pos[1], b3['x'], b3['y'])

                        if d1 <= 400 and d2 <= 400 and d3 <= 400:
                            new_cost = 40_000  # MaxRange cost
                            savings = old_cost - new_cost

                            if savings > 0:
                                ids = sorted([i, j, k])
                                merges.append((tuple(ids), pos, 'MaxRange', savings))
                            break

    # Deduplicate and sort by savings
    seen = set()
    unique_merges = []
    for ids, pos, atype, savings in merges:
        if ids not in seen:
            seen.add(ids)
            unique_merges.append((ids, pos, atype, savings))

    unique_merges.sort(key=lambda x: -x[3])

    return unique_merges


def apply_three_way_merges(antennas, merges, bmap):
    """Apply three-way merges."""
    merged = set()
    new_antennas = []

    applied = []
    for ids, pos, atype, savings in merges:
        if any(i in merged for i in ids):
            continue

        for i in ids:
            merged.add(i)

        combined_bids = []
        for i in ids:
            combined_bids.extend(antennas[i]['buildings'])

        new_antennas.append({
            'type': atype,
            'x': pos[0],
            'y': pos[1],
            'buildings': combined_bids
        })
        applied.append((ids, savings))

    # Add unmerged antennas
    for i, ant in enumerate(antennas):
        if i not in merged:
            new_antennas.append(ant)

    return new_antennas, applied


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
    original_cost = calculate_cost(antennas)

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {original_cost:,} EUR")

    # Phase 1: Try repositioning
    print("\n=== PHASE 1: Repositioning ===")
    antennas, improved = find_optimal_positions(buildings, antennas, bmap)
    cost = calculate_cost(antennas)
    print(f"Improved positions: {improved}")
    print(f"Cost after repositioning: {cost:,} EUR")

    # Phase 2: Try three-way merges
    print("\n=== PHASE 2: Three-way merges ===")
    merges = try_three_way_merge(antennas, bmap)
    print(f"Potential three-way merges: {len(merges)}")

    if merges:
        for ids, pos, atype, savings in merges[:5]:
            print(f"  {ids}: {savings:,} EUR savings")

        antennas, applied = apply_three_way_merges(antennas, merges, bmap)
        print(f"Applied merges: {len(applied)}")
        cost = calculate_cost(antennas)
        print(f"Cost after three-way merges: {cost:,} EUR")
    else:
        print("No three-way merge opportunities found")

    # Validate
    solution = {'antennas': antennas}
    final_cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print("\n" + "="*60)
    print(f"RESULT: {msg}")
    print(f"Final cost: {final_cost:,} EUR ({len(antennas)} antennas)")
    print(f"Savings: {original_cost - final_cost:,} EUR")
    print("="*60)

    if valid and final_cost < original_cost:
        output = f'./solutions/solution_4_epitech_{final_cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    else:
        print("No improvement or invalid solution")


if __name__ == "__main__":
    main()
