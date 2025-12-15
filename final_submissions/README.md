# 5G Network Optimization - Final Submissions

## Hackathon Epitech Marseille - December 2024

### Results Summary

| Dataset | Buildings | Antennas | Cost (EUR) |
|---------|-----------|----------|------------|
| 1. peaceful_village | 4 | 2 | 25,000 |
| 2. small_town | 4 | 2 | 45,000 |
| 3. suburbia | 2,601 | 1,049 | 32,070,000 |
| 4. epitech | 5,000 | 1,281 | 40,440,000 |
| 5. isogrid | 8,217 | 6,157 | 195,565,000 |
| 6. manhattan | 10,000 | 1,080 | 33,010,000 |

### **TOTAL: 301,155,000 EUR**

---

### Antenna Types Used

| Type | Range | Capacity | Cost |
|------|-------|----------|------|
| Nano | 50m | 200 | 5,000 EUR |
| Spot | 100m | 800 | 15,000 EUR |
| Density | 150m | 5,000 | 30,000 EUR |
| MaxRange | 400m | 3,500 | 40,000 EUR |

---

### Optimization Algorithms

1. **Greedy placement** with spatial grid indexing
2. **Type optimization** - downgrade to cheapest valid type
3. **Merge optimization** - combine nearby antennas when beneficial
4. **Repositioning** - move antennas to optimal building positions
5. **Simulated Annealing** - escape local optima (tested)

---

### Files

- `solution_1_peaceful_village_25000.json`
- `solution_2_small_town_45000.json`
- `solution_3_suburbia_32070000.json`
- `solution_4_epitech_40440000.json`
- `solution_5_isogrid_195565000.json`
- `solution_6_manhattan_33010000.json`

Each JSON file contains the antenna configuration in the format:
```json
{
  "antennas": [
    {
      "type": "Density",
      "x": 100,
      "y": 200,
      "buildings": [1, 2, 3]
    }
  ]
}
```

---

### Validation

All solutions validated using `score_function.py` from the starter kit.

To validate: `python validate_final.py`
