"""
Suburbia Grid Search Optimization
=================================

Try placing antennas at optimal grid positions, not just at building locations.
This might find positions that can cover multiple isolated buildings.
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


def find_midpoint_opportunities(buildings, bmap):
    """
    Find pairs of buildings that are between 150-400m apart
    where a MaxRange antenna at the midpoint could cover both.
    """
    opportunities = []

    for i, b1 in enumerate(buildings):
        p1 = get_max_pop(b1)

        for j, b2 in enumerate(buildings):
            if j <= i:
                continue

            p2 = get_max_pop(b2)
            d = dist(b1['x'], b1['y'], b2['x'], b2['y'])

            # Buildings between 150-400m apart (too far for Density, reachable by MaxRange)
            if 150 < d <= 400:
                combined_pop = p1 + p2

                # Check if combined population fits in MaxRange
                if combined_pop <= 3500:
                    # Calculate midpoint
                    mx = (b1['x'] + b2['x']) // 2
                    my = (b1['y'] + b2['y']) // 2

                    # Verify both buildings are within MaxRange from midpoint
                    d1 = dist(mx, my, b1['x'], b1['y'])
                    d2 = dist(mx, my, b2['x'], b2['y'])

                    if d1 <= 400 and d2 <= 400:
                        opportunities.append({
                            'b1': b1['id'],
                            'b2': b2['id'],
                            'distance': d,
                            'combined_pop': combined_pop,
                            'midpoint': (mx, my),
                            'p1': p1,
                            'p2': p2
                        })

    return opportunities


def build_solution_with_grid(buildings, bmap):
    """
    Build solution trying grid positions for antennas.
    """
    # Get bounds
    min_x = min(b['x'] for b in buildings)
    max_x = max(b['x'] for b in buildings)
    min_y = min(b['y'] for b in buildings)
    max_y = max(b['y'] for b in buildings)

    print(f"Building bounds: x=[{min_x}, {max_x}], y=[{min_y}, {max_y}]")

    # Build spatial grid for buildings
    cell_size = 100
    grid = defaultdict(list)
    for b in buildings:
        cell = (b['x'] // cell_size, b['y'] // cell_size)
        grid[cell].append(b)

    uncovered = set(b['id'] for b in buildings)
    antennas = []

    # Try MaxRange first at strategic positions
    # Grid step of 200 (half of MaxRange)
    grid_step = 200

    print(f"\nPhase 1: Trying MaxRange antennas at grid positions...")

    positions_tried = 0
    for gx in range(min_x, max_x + grid_step, grid_step):
        for gy in range(min_y, max_y + grid_step, grid_step):
            positions_tried += 1

            # Find buildings within MaxRange (400m)
            in_range = []
            cells_check = 5  # 400/100 + 1
            cx, cy = gx // cell_size, gy // cell_size

            for dx in range(-cells_check, cells_check + 1):
                for dy in range(-cells_check, cells_check + 1):
                    for b in grid[(cx + dx, cy + dy)]:
                        if b['id'] not in uncovered:
                            continue
                        if dist_sq(gx, gy, b['x'], b['y']) <= 400**2:
                            in_range.append((b['id'], get_max_pop(b)))

            if len(in_range) < 2:
                continue

            # Sort by population and pack into MaxRange
            in_range.sort(key=lambda x: x[1])
            selected = []
            total_pop = 0

            for bid, pop in in_range:
                if total_pop + pop <= 3500:
                    selected.append(bid)
                    total_pop += pop

            if len(selected) >= 2:
                # Check if this is better than individual Density antennas
                # 2 Density = 60,000, 1 MaxRange = 40,000 => saves 20,000
                individual_cost = sum(30_000 for bid in selected)  # Assume Density
                maxrange_cost = 40_000

                if maxrange_cost < individual_cost:
                    antennas.append({
                        'type': 'MaxRange',
                        'x': gx,
                        'y': gy,
                        'buildings': selected
                    })
                    for bid in selected:
                        uncovered.discard(bid)

    print(f"  Tried {positions_tried} positions")
    print(f"  MaxRange antennas placed: {len(antennas)}")
    print(f"  Buildings covered: {len(buildings) - len(uncovered)}")
    print(f"  Buildings remaining: {len(uncovered)}")

    # Phase 2: Cover remaining with Density at building positions
    print(f"\nPhase 2: Covering remaining buildings with Density...")

    remaining = [bmap[bid] for bid in uncovered]

    while uncovered:
        # Find best Density placement
        best = None
        best_count = 0

        for b in remaining:
            if b['id'] not in uncovered:
                continue

            cx, cy = b['x'] // cell_size, b['y'] // cell_size

            in_range = []
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    for bb in grid[(cx + dx, cy + dy)]:
                        if bb['id'] not in uncovered:
                            continue
                        if dist_sq(b['x'], b['y'], bb['x'], bb['y']) <= 150**2:
                            in_range.append((bb['id'], get_max_pop(bb)))

            if not in_range:
                continue

            in_range.sort(key=lambda x: x[1])
            selected = []
            total_pop = 0

            for bid, pop in in_range:
                if total_pop + pop <= 5000:
                    selected.append(bid)
                    total_pop += pop

            if len(selected) > best_count:
                best_count = len(selected)
                best = {
                    'type': 'Density',
                    'x': b['x'],
                    'y': b['y'],
                    'buildings': selected
                }

        if best:
            antennas.append(best)
            for bid in best['buildings']:
                uncovered.discard(bid)
        else:
            # Fallback: single building antenna
            bid = next(iter(uncovered))
            b = bmap[bid]
            pop = get_max_pop(b)

            for atype in ['Nano', 'Spot', 'Density', 'MaxRange']:
                if ANTENNA_TYPES[atype]['capacity'] >= pop:
                    antennas.append({
                        'type': atype,
                        'x': b['x'],
                        'y': b['y'],
                        'buildings': [bid]
                    })
                    uncovered.discard(bid)
                    break

    return antennas


def optimize_solution(antennas, bmap):
    """Optimize antenna types."""
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
            'buildings': ant['buildings']
        })

    return result


def main():
    from score_function import getSolutionScore

    print("Loading suburbia dataset...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    print("Loading current best solution...")
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        current_sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    current_cost = calculate_cost(current_sol['antennas'])

    print(f"Buildings: {len(buildings)}")
    print(f"Current best: {current_cost:,} EUR ({len(current_sol['antennas'])} antennas)")

    # Find midpoint opportunities
    print("\n=== MIDPOINT ANALYSIS ===")
    opportunities = find_midpoint_opportunities(buildings, bmap)
    print(f"Pairs between 150-400m with combined pop <= 3500: {len(opportunities)}")

    if opportunities:
        print("\nSample opportunities:")
        for opp in opportunities[:10]:
            print(f"  Buildings {opp['b1']}-{opp['b2']}: d={opp['distance']:.1f}m, "
                  f"pop={opp['p1']}+{opp['p2']}={opp['combined_pop']}")

    # Build new solution with grid search
    print("\n=== BUILDING NEW SOLUTION ===")
    antennas = build_solution_with_grid(buildings, bmap)
    antennas = optimize_solution(antennas, bmap)

    # Validate
    solution = {'antennas': antennas}
    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    print(f"\n{'='*60}")
    print(f"RESULT: {msg}")
    print(f"New cost: {cost:,} EUR ({len(antennas)} antennas)")
    print(f"Current best: {current_cost:,} EUR")
    print('='*60)

    if valid and cost < current_cost:
        print(f"\nIMPROVED! Savings: {current_cost - cost:,} EUR")
        output = f'./solutions/solution_3_suburbia_{cost}.json'
        with open(output, 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"Saved: {output}")
    elif valid:
        print(f"\nNo improvement (diff: {cost - current_cost:,} EUR)")
    else:
        print("\nINVALID SOLUTION!")


if __name__ == "__main__":
    main()
