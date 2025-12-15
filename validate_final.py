"""
Validate all final submissions
"""

import json
from score_function import getSolutionScore

DATASETS = [
    ('1_peaceful_village', 'solution_1_peaceful_village_25000.json'),
    ('2_small_town', 'solution_2_small_town_45000.json'),
    ('3_suburbia', 'solution_3_suburbia_32070000.json'),
    ('4_epitech', 'solution_4_epitech_40440000.json'),
    ('5_isogrid', 'solution_5_isogrid_195565000.json'),
    ('6_manhattan', 'solution_6_manhattan_33010000.json'),
]

print("="*70)
print("FINAL SUBMISSION VALIDATION")
print("="*70)

total = 0
all_valid = True

for dataset_name, solution_file in DATASETS:
    with open(f'./datasets/{dataset_name}.json') as f:
        dataset = json.load(f)

    with open(f'./final_submissions/{solution_file}') as f:
        solution = json.load(f)

    cost, valid, msg = getSolutionScore(json.dumps(solution), json.dumps(dataset))

    status = "OK" if valid else "FAIL"
    print(f"{status} {dataset_name}: {cost:,} EUR - {msg}")

    if valid:
        total += cost
    else:
        all_valid = False

print("="*70)
print(f"TOTAL: {total:,} EUR")
print(f"STATUS: {'ALL VALID' if all_valid else 'SOME INVALID'}")
print("="*70)
