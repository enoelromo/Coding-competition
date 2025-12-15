"""
Suburbia Systematic Search
==========================

Systematically search for ANY improvement by trying all possible moves.
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


def get_cheapest_type(x, y, bids, bmap):
    """Find cheapest antenna type."""
    blds = [bmap[bid] for bid in bids]
    total_pop = sum(get_max_pop(b) for b in blds)

    for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
        specs = ANTENNA_TYPES[atype]
        if specs['capacity'] < total_pop:
            continue

        r2 = specs['range'] ** 2
        if all(dist_sq(x, y, b['x'], b['y']) <= r2 for b in blds):
            return atype

    return None


def main():
    from score_function import getSolutionScore

    print("Loading data...")
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
    print(f"Original cost: {original_cost:,} EUR")

    # Index antennas by grid
    cell_size = 200
    grid = defaultdict(list)
    for i, ant in enumerate(antennas):
        cell = (ant['x'] // cell_size, ant['y'] // cell_size)
        grid[cell].append(i)

    # 1. Check if any antenna can be downgraded
    print("\n=== CHECKING TYPE DOWNGRADES ===")
    downgrades = 0
    for i, ant in enumerate(antennas):
        blds = [bmap[bid] for bid in ant['buildings']]
        total_pop = sum(get_max_pop(b) for b in blds)

        for atype in ['Nano', 'Spot', 'Density']:
            if ANTENNA_TYPES[atype]['cost_on'] >= ANTENNA_TYPES[ant['type']]['cost_on']:
                continue

            specs = ANTENNA_TYPES[atype]
            if specs['capacity'] < total_pop:
                continue

            r2 = specs['range'] ** 2
            if all(dist_sq(ant['x'], ant['y'], b['x'], b['y']) <= r2 for b in blds):
                print(f"  Antenna {i}: {ant['type']} -> {atype} (saves {ANTENNA_TYPES[ant['type']]['cost_on'] - specs['cost_on']:,})")
                downgrades += 1
                break

    print(f"Possible downgrades: {downgrades}")

    # 2. Check ALL pairs for merge potential (exhaustive)
    print("\n=== EXHAUSTIVE MERGE CHECK ===")
    merge_count = 0

    for i in range(len(antennas)):
        a1 = antennas[i]
        blds1 = [bmap[bid] for bid in a1['buildings']]
        pop1 = sum(get_max_pop(b) for b in blds1)

        cx, cy = a1['x'] // cell_size, a1['y'] // cell_size

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for j in grid[(cx + dx, cy + dy)]:
                    if j <= i:
                        continue

                    a2 = antennas[j]
                    blds2 = [bmap[bid] for bid in a2['buildings']]
                    pop2 = sum(get_max_pop(b) for b in blds2)

                    # Combined check
                    combined_pop = pop1 + pop2
                    all_blds = blds1 + blds2

                    # Try all positions (both antenna positions + all building positions)
                    positions = [(a1['x'], a1['y']), (a2['x'], a2['y'])]
                    for b in all_blds:
                        positions.append((b['x'], b['y']))

                    for px, py in positions:
                        for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                            specs = ANTENNA_TYPES[atype]
                            if specs['capacity'] < combined_pop:
                                continue

                            r2 = specs['range'] ** 2
                            if all(dist_sq(px, py, b['x'], b['y']) <= r2 for b in all_blds):
                                old_cost = ANTENNA_TYPES[a1['type']]['cost_on'] + ANTENNA_TYPES[a2['type']]['cost_on']
                                new_cost = specs['cost_on']
                                savings = old_cost - new_cost

                                if savings > 0:
                                    merge_count += 1
                                    if merge_count <= 10:
                                        print(f"  Merge {i},{j}: {a1['type']}+{a2['type']} -> {atype}")
                                        print(f"    Position: ({px}, {py})")
                                        print(f"    Savings: {savings:,} EUR")

                                break
                        else:
                            continue
                        break

    print(f"\nTotal possible merges: {merge_count}")

    # 3. Check if relocating antenna to building position helps
    print("\n=== CHECKING RELOCATIONS ===")
    relocations = 0

    for i, ant in enumerate(antennas):
        blds = [bmap[bid] for bid in ant['buildings']]

        for b in blds:
            new_type = get_cheapest_type(b['x'], b['y'], ant['buildings'], bmap)
            if new_type and ANTENNA_TYPES[new_type]['cost_on'] < ANTENNA_TYPES[ant['type']]['cost_on']:
                print(f"  Antenna {i}: relocate to ({b['x']}, {b['y']}), {ant['type']} -> {new_type}")
                relocations += 1
                break

    print(f"Possible relocations: {relocations}")


if __name__ == "__main__":
    main()
