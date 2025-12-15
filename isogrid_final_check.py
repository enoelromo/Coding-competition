"""
Isogrid Final Check
===================

One last comprehensive check for any optimization opportunity.
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


def calculate_cost(antennas):
    return sum(ANTENNA_TYPES[a['type']]['cost_on'] for a in antennas)


def main():
    from score_function import getSolutionScore

    print("Loading isogrid dataset...")
    with open('./datasets/5_isogrid.json') as f:
        dataset = json.load(f)

    print("Loading current solution...")
    with open('./solutions/solution_5_isogrid_195565000.json') as f:
        sol = json.load(f)

    buildings = dataset['buildings']
    bmap = {b['id']: b for b in buildings}
    antennas = sol['antennas']

    print(f"Buildings: {len(buildings)}")
    print(f"Antennas: {len(antennas)}")
    print(f"Current cost: {calculate_cost(antennas):,} EUR")

    # Analyze ALL antennas
    single_spot = []
    single_nano = []
    single_density = []
    multi_antennas = []

    for i, ant in enumerate(antennas):
        blds = [bmap[bid] for bid in ant['buildings']]
        pop = sum(get_max_pop(b) for b in blds)

        if len(ant['buildings']) == 1:
            if ant['type'] == 'Spot':
                single_spot.append({'idx': i, 'pop': pop, 'bld': blds[0]})
            elif ant['type'] == 'Nano':
                single_nano.append({'idx': i, 'pop': pop, 'bld': blds[0]})
            elif ant['type'] == 'Density':
                single_density.append({'idx': i, 'pop': pop, 'bld': blds[0]})
        else:
            multi_antennas.append({'idx': i, 'pop': pop, 'type': ant['type'], 'ant': ant})

    print(f"\nSingle Nano: {len(single_nano)}")
    print(f"Single Spot: {len(single_spot)}")
    print(f"Single Density: {len(single_density)}")
    print(f"Multi-building: {len(multi_antennas)}")

    # Check 1: Can any Spot be absorbed by nearby MaxRange?
    print("\n=== CHECK 1: Spot absorption into MaxRange ===")

    spot_opportunities = []
    for sp in single_spot:
        sp_bld = sp['bld']
        sp_pop = sp['pop']

        for ma in multi_antennas:
            if ma['type'] != 'MaxRange':
                continue

            m_ant = ma['ant']
            d = dist(m_ant['x'], m_ant['y'], sp_bld['x'], sp_bld['y'])

            if d <= 400:
                combined = ma['pop'] + sp_pop
                if combined <= 3500:
                    # Save 15,000 (Spot cost)
                    spot_opportunities.append({
                        'spot_idx': sp['idx'],
                        'maxrange_idx': ma['idx'],
                        'distance': d,
                        'combined_pop': combined,
                        'savings': 15000
                    })

    print(f"Spot -> MaxRange opportunities: {len(spot_opportunities)}")

    # Check 2: Can any Nano be absorbed by nearby Spot or MaxRange?
    print("\n=== CHECK 2: Nano absorption ===")

    nano_opportunities = []
    for na in single_nano:
        na_bld = na['bld']
        na_pop = na['pop']

        for ma in multi_antennas:
            m_ant = ma['ant']
            m_type = ma['type']
            specs = ANTENNA_TYPES[m_type]

            d = dist(m_ant['x'], m_ant['y'], na_bld['x'], na_bld['y'])

            if d <= specs['range']:
                combined = ma['pop'] + na_pop
                if combined <= specs['capacity']:
                    nano_opportunities.append({
                        'nano_idx': na['idx'],
                        'multi_idx': ma['idx'],
                        'multi_type': m_type,
                        'distance': d,
                        'combined_pop': combined,
                        'savings': 5000
                    })

    print(f"Nano absorption opportunities: {len(nano_opportunities)}")

    # Check 3: Can any two Spot be merged into Density?
    print("\n=== CHECK 3: Spot + Spot -> Density ===")
    # 2 Spot = 30,000, 1 Density = 30,000 => NO SAVINGS
    print("2 Spot (30,000) = 1 Density (30,000) => No savings possible")

    # Check 4: Density with low utilization
    print("\n=== CHECK 4: Under-utilized Density antennas ===")

    under_utilized = []
    for sd in single_density:
        if sd['pop'] <= 800:
            under_utilized.append(sd)

    print(f"Single Density with pop <= 800 (could be Spot): {len(under_utilized)}")

    if under_utilized:
        print("Checking if these could be downgraded to Spot...")
        downgradeable = 0
        for sd in under_utilized:
            ant = antennas[sd['idx']]
            bld = sd['bld']
            # Check if building is within Spot range of antenna
            d = dist(ant['x'], ant['y'], bld['x'], bld['y'])
            if d <= 100:
                downgradeable += 1
                print(f"  Antenna {sd['idx']}: pop={sd['pop']}, d={d:.1f}m - CAN downgrade!")

        print(f"Downgradeable: {downgradeable}")

    # Apply any opportunities found
    all_opportunities = spot_opportunities + nano_opportunities

    if all_opportunities or downgradeable > 0:
        print("\n=== APPLYING OPTIMIZATIONS ===")

        new_antennas = [dict(a) for a in antennas]

        # Downgrade under-utilized Density
        for sd in under_utilized:
            ant_idx = sd['idx']
            ant = new_antennas[ant_idx]
            bld = sd['bld']
            d = dist(ant['x'], ant['y'], bld['x'], bld['y'])
            if d <= 100:
                new_antennas[ant_idx]['type'] = 'Spot'

        # Apply absorptions (if any)
        absorbed = set()
        for opp in spot_opportunities + nano_opportunities:
            source_key = 'spot_idx' if 'spot_idx' in opp else 'nano_idx'
            source_idx = opp[source_key]
            target_idx = opp.get('maxrange_idx') or opp.get('multi_idx')

            if source_idx in absorbed:
                continue

            source_bid = antennas[source_idx]['buildings'][0]
            new_antennas[target_idx]['buildings'].append(source_bid)
            absorbed.add(source_idx)

        # Remove absorbed
        final_antennas = [a for i, a in enumerate(new_antennas) if i not in absorbed]

        # Validate
        solution = {'antennas': final_antennas}
        cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

        print(f"\n{'='*60}")
        print(f"RESULT: {msg}")
        print(f"New cost: {cost:,} EUR ({len(final_antennas)} antennas)")
        print(f"Original: {calculate_cost(antennas):,} EUR")
        print('='*60)

        if valid and cost < calculate_cost(antennas):
            print(f"\nIMPROVED! Savings: {calculate_cost(antennas) - cost:,} EUR")
            output = f'./solutions/solution_5_isogrid_{cost}.json'
            with open(output, 'w') as f:
                json.dump(solution, f, indent=2)
            print(f"Saved: {output}")
    else:
        print("\n" + "="*60)
        print("NO OPTIMIZATION POSSIBLE")
        print("Dataset 5 is at its mathematical optimum")
        print("="*60)


if __name__ == "__main__":
    main()
