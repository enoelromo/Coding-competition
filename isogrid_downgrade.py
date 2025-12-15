"""
Isogrid Downgrade Analysis
==========================

Check if Density antennas covering single buildings could be downgraded to Spot.
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


def dist_sq(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def main():
    from score_function import getSolutionScore

    print("Loading isogrid dataset...")
    with open('./datasets/5_isogrid.json') as f:
        dataset = json.load(f)

    print("Loading solution...")
    with open('./solutions/solution_5_isogrid_195565000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {calculate_cost(antennas):,} EUR")

    # Find single-building Density antennas
    single_density = []
    for i, ant in enumerate(antennas):
        if len(ant['buildings']) == 1 and ant['type'] == 'Density':
            bid = ant['buildings'][0]
            b = bmap[bid]
            pop = get_max_pop(b)
            single_density.append((i, bid, pop))

    print(f"\nSingle-building Density antennas: {len(single_density)}")

    # Check population distribution
    pops = [p for _, _, p in single_density]
    print(f"Population range: {min(pops)} - {max(pops)}")

    # Count how many could potentially downgrade
    could_downgrade_spot = sum(1 for _, _, p in single_density if p <= 800)
    could_downgrade_nano = sum(1 for _, _, p in single_density if p <= 200)

    print(f"\nCould downgrade to Spot (pop <= 800): {could_downgrade_spot}")
    print(f"Could downgrade to Nano (pop <= 200): {could_downgrade_nano}")

    # But we also need to check range - antenna position must be within range of building
    downgrades_spot = []
    downgrades_nano = []

    for i, bid, pop in single_density:
        ant = antennas[i]
        b = bmap[bid]

        d2 = dist_sq(ant['x'], ant['y'], b['x'], b['y'])

        if pop <= 200 and d2 <= 50**2:
            downgrades_nano.append(i)
        elif pop <= 800 and d2 <= 100**2:
            downgrades_spot.append(i)

    print(f"\nActual downgrades possible:")
    print(f"  To Nano: {len(downgrades_nano)} (saves {len(downgrades_nano) * 25_000:,} EUR)")
    print(f"  To Spot: {len(downgrades_spot)} (saves {len(downgrades_spot) * 15_000:,} EUR)")

    if downgrades_nano or downgrades_spot:
        # Apply downgrades
        new_antennas = []
        for i, ant in enumerate(antennas):
            new_ant = dict(ant)
            if i in downgrades_nano:
                new_ant['type'] = 'Nano'
            elif i in downgrades_spot:
                new_ant['type'] = 'Spot'
            new_antennas.append(new_ant)

        # Validate
        solution = {'antennas': new_antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"\n{msg}")
        print(f"New cost: {cost:,} EUR")

        if valid and cost < calculate_cost(antennas):
            output = f'./solutions/solution_5_isogrid_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
    else:
        print("\nNo downgrades possible - buildings require larger antenna range")


if __name__ == "__main__":
    main()
