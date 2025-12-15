"""
Suburbia Absorption Analysis
============================

Check if any single-building antenna could be absorbed by a nearby
multi-building antenna (possibly by upgrading to MaxRange).
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


def main():
    from score_function import getSolutionScore

    print("Loading suburbia dataset...")
    with open('./datasets/3_suburbia.json') as f:
        dataset = json.load(f)

    print("Loading current best solution...")
    with open('./solutions/solution_3_suburbia_32070000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {calculate_cost(antennas):,} EUR")

    # Categorize antennas
    single_antennas = []
    multi_antennas = []

    for i, ant in enumerate(antennas):
        ant_blds = [bmap[bid] for bid in ant['buildings']]
        ant_pop = sum(get_max_pop(b) for b in ant_blds)

        if len(ant['buildings']) == 1:
            single_antennas.append({
                'index': i,
                'ant': ant,
                'pop': ant_pop,
                'cost': ANTENNA_TYPES[ant['type']]['cost_on']
            })
        else:
            multi_antennas.append({
                'index': i,
                'ant': ant,
                'pop': ant_pop,
                'cost': ANTENNA_TYPES[ant['type']]['cost_on'],
                'blds': ant_blds
            })

    print(f"\nSingle-building antennas: {len(single_antennas)}")
    print(f"Multi-building antennas: {len(multi_antennas)}")

    # For each single antenna, check if it can be absorbed by a multi antenna
    print("\n=== ABSORPTION ANALYSIS ===")

    absorption_opportunities = []

    for sa in single_antennas:
        s_ant = sa['ant']
        s_bid = s_ant['buildings'][0]
        s_bld = bmap[s_bid]
        s_pop = sa['pop']
        s_cost = sa['cost']

        for ma in multi_antennas:
            m_ant = ma['ant']
            m_pop = ma['pop']
            m_cost = ma['cost']

            # Check if building is within MaxRange of multi-antenna
            d = dist(m_ant['x'], m_ant['y'], s_bld['x'], s_bld['y'])

            if d > 400:
                continue

            combined_pop = m_pop + s_pop

            # Try each antenna type for the combined group
            for atype in ['Density', 'MaxRange']:
                specs = ANTENNA_TYPES[atype]

                if combined_pop > specs['capacity']:
                    continue

                r2 = specs['range'] ** 2

                # Check if all current buildings of multi-antenna are in range
                all_in_range = all(
                    dist_sq(m_ant['x'], m_ant['y'], b['x'], b['y']) <= r2
                    for b in ma['blds']
                )

                if not all_in_range:
                    continue

                # Check if single building is in range
                if dist_sq(m_ant['x'], m_ant['y'], s_bld['x'], s_bld['y']) > r2:
                    continue

                # Calculate savings
                old_cost = s_cost + m_cost
                new_cost = specs['cost_on']
                savings = old_cost - new_cost

                if savings > 0:
                    absorption_opportunities.append({
                        'single_idx': sa['index'],
                        'multi_idx': ma['index'],
                        'new_type': atype,
                        'savings': savings,
                        'distance': d,
                        'combined_pop': combined_pop
                    })

                break  # Found a valid type

    print(f"Absorption opportunities found: {len(absorption_opportunities)}")

    if absorption_opportunities:
        absorption_opportunities.sort(key=lambda x: -x['savings'])

        print("\nTop 10 opportunities:")
        for opp in absorption_opportunities[:10]:
            print(f"  Single {opp['single_idx']} -> Multi {opp['multi_idx']}: "
                  f"type={opp['new_type']}, d={opp['distance']:.1f}m, "
                  f"combined_pop={opp['combined_pop']}, savings={opp['savings']:,} EUR")

        # Apply absorptions greedily
        print("\n=== APPLYING ABSORPTIONS ===")

        absorbed_singles = set()
        modified_multis = {}

        for opp in absorption_opportunities:
            if opp['single_idx'] in absorbed_singles:
                continue
            if opp['multi_idx'] in modified_multis:
                continue

            absorbed_singles.add(opp['single_idx'])
            modified_multis[opp['multi_idx']] = opp

        print(f"Absorptions to apply: {len(absorbed_singles)}")
        total_savings = sum(modified_multis[k]['savings'] for k in modified_multis)
        print(f"Expected savings: {total_savings:,} EUR")

        # Build new antenna list
        new_antennas = []

        for i, ant in enumerate(antennas):
            if i in absorbed_singles:
                continue  # Skip absorbed single antennas

            if i in modified_multis:
                opp = modified_multis[i]
                single_idx = opp['single_idx']
                single_bid = antennas[single_idx]['buildings'][0]

                new_antennas.append({
                    'type': opp['new_type'],
                    'x': ant['x'],
                    'y': ant['y'],
                    'buildings': ant['buildings'] + [single_bid]
                })
            else:
                new_antennas.append(ant)

        # Validate
        solution = {'antennas': new_antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"\n{'='*60}")
        print(f"RESULT: {msg}")
        print(f"New cost: {cost:,} EUR ({len(new_antennas)} antennas)")
        print(f"Original: {calculate_cost(antennas):,} EUR")
        print('='*60)

        if valid and cost < calculate_cost(antennas):
            print(f"\nIMPROVED! Actual savings: {calculate_cost(antennas) - cost:,} EUR")
            output = f'./solutions/solution_3_suburbia_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
    else:
        print("\nNo absorption opportunities!")
        print("Single-building antennas are all too isolated from multi-building antennas")

        # Analyze why
        print("\n=== DETAILED ANALYSIS ===")

        # For sample singles, find nearest multi
        for sa in single_antennas[:5]:
            s_ant = sa['ant']
            s_bid = s_ant['buildings'][0]
            s_bld = bmap[s_bid]
            s_pop = sa['pop']

            nearest_dist = float('inf')
            nearest_info = None

            for ma in multi_antennas:
                m_ant = ma['ant']
                d = dist(m_ant['x'], m_ant['y'], s_bld['x'], s_bld['y'])

                if d < nearest_dist:
                    nearest_dist = d
                    nearest_info = ma

            if nearest_info:
                combined = s_pop + nearest_info['pop']
                print(f"\nSingle antenna {sa['index']} (pop={s_pop}):")
                print(f"  Nearest multi: {nearest_info['index']} at {nearest_dist:.1f}m")
                print(f"  Multi pop: {nearest_info['pop']}")
                print(f"  Combined: {combined}")
                print(f"  MaxRange capacity: 3500, Density capacity: 5000")

                if nearest_dist > 400:
                    print(f"  REASON: Too far (>400m)")
                elif combined > 5000:
                    print(f"  REASON: Combined pop exceeds Density (5000)")
                elif combined > 3500 and nearest_dist > 150:
                    print(f"  REASON: Combined pop exceeds MaxRange (3500) and too far for Density")


if __name__ == "__main__":
    main()
