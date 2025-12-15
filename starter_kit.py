import json
import sys
import datetime
from score_function import getSolutionScore


def naive_solution(dataset):
    """
    Naive solution: places a Density antenna on each building.

    Advantages:
    - Guarantees coverage of all buildings
    - Guarantees that capacity is never exceeded

    Disadvantages:
    - Very expensive!
    - Many unnecessary antennas

    YOUR TASK: IMPROVE THIS SOLUTION!
    """
    antennas = []
    
    for building in dataset['buildings']:
        antenna = {
            "type": "Density",
            "x": building['x'],
            "y": building['y'],
            "buildings": [building['id']]
        }
        antennas.append(antenna)
    
    solution = {
        "antennas": antennas
    }
    
    return solution


def main():
    datasets = [
        "1_peaceful_village",
        "2_small_town",
        "3_suburbia",
        "4_epitech",
        "5_isogrid",
        "6_manhattan"]
    
    selected_dataset = datasets[0]
    time_now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    input_file = './datasets/' + selected_dataset + '.json'    
    
    print(f"Loading dataset: {input_file}")
    dataset = json.load(open(input_file))
    
    print(f"Number of buildings: {len(dataset['buildings'])}")
    
    print("\nGenerating solution...")
    solution = naive_solution(dataset)
    
    print(f"Solution generated with {len(solution['antennas'])} antennas")
    
    # Cost calculation (optional, for information purposes)
    cost, isValid, message = getSolutionScore(json.dumps(solution), json.dumps(dataset) )
    print(message)
    
    if isValid:
        output_file = f'./solutions/solution_{selected_dataset}_{cost}_{time_now}.json'
        with open(output_file, 'w') as f:
            json.dump(solution, f, indent=2)
            print(f"Solution saved to {output_file}")


if __name__ == "__main__":
    main()