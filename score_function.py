import json
import math

def getSolutionScore(solution_txt, dataset_txt):
    """This function is exactly the one that evaluates the solution on the server.
    It is not necessary to use it, but it can help you debug your solution locally.

    Evaluate the solution and return a tuple (score, isValid, error_message).

    Arguments:
    solution_txt -- the solution to be evaluated (JSON string)
    dataset_txt -- the dataset for which the solution is made (JSON string)
    """
    try:
        dataset = json.loads(dataset_txt)
    except:
        return 0, False, 'Error while processing the dataset. Please contact the contest organizer.'
    
    # Parse solution
    try:
        solution = json.loads(solution_txt)
    except:
        return 0, False, 'Submission is not a valid JSON object'
    
    if 'antennas' not in solution:
        return 0, False, 'Submission does not contain the "antennas" key'
    if not isinstance(solution['antennas'], list):
        return 0, False, 'antennas is not a list'
    
    # Define antenna types
    antenna_types = {
        'Nano': {'range': 50, 'capacity': 200, 'cost_on_building': 5_000, 'cost_off_building': 6_000},
        'Spot': {'range': 100, 'capacity': 800, 'cost_on_building': 15_000, 'cost_off_building': 20_000},
        'Density': {'range': 150, 'capacity': 5_000, 'cost_on_building': 30_000, 'cost_off_building': 50_000},
        'MaxRange': {'range': 400, 'capacity': 3_500, 'cost_on_building': 40_000, 'cost_off_building': 50_000}
    }
    
    # Create building map
    building_map = {}
    building_positions = {}
    for building in dataset['buildings']:
        building_id = building['id']
        building_map[building_id] = building
        building_positions[(building['x'], building['y'])] = building_id
    
    # Track which buildings are covered
    building_coverage = {}
    total_cost = 0
    
    # Process each antenna
    for i, antenna in enumerate(solution['antennas']):
        # Validate antenna structure
        if 'type' not in antenna:
            return 0, False, f'Antenna {i} does not contain the "type" key'
        if 'x' not in antenna:
            return 0, False, f'Antenna {i} does not contain the "x" key'
        if 'y' not in antenna:
            return 0, False, f'Antenna {i} does not contain the "y" key'
        if 'buildings' not in antenna:
            return 0, False, f'Antenna {i} does not contain the "buildings" key'
        
        antenna_type = antenna['type']
        if antenna_type not in antenna_types:
            return 0, False, f'Antenna {i} has invalid type "{antenna_type}". Valid types are: {", ".join(antenna_types.keys())}'
        
        if not isinstance(antenna['x'], int):
            return 0, False, f'Antenna {i} has non-integer x coordinate'
        if not isinstance(antenna['y'], int):
            return 0, False, f'Antenna {i} has non-integer y coordinate'
        if antenna['x'] < 0 or antenna['y'] < 0:
            return 0, False, f'Antenna {i} has negative coordinates'
        
        if not isinstance(antenna['buildings'], list):
            return 0, False, f'Antenna {i}: buildings field is not a list'
        
        antenna_x = antenna['x']
        antenna_y = antenna['y']
        antenna_spec = antenna_types[antenna_type]
        
        # Determine if antenna is on a building
        is_on_building = (antenna_x, antenna_y) in building_positions
        cost = antenna_spec['cost_on_building'] if is_on_building else antenna_spec['cost_off_building']
        total_cost += cost
        
        # Check coverage and capacity
        total_peak = 0
        total_off_peak = 0
        total_night = 0
        
        for building_id in antenna['buildings']:
            if not isinstance(building_id, int):
                return 0, False, f'Antenna {i}: building list contains non-integer value "{building_id}"'
            
            if building_id not in building_map:
                return 0, False, f'Antenna {i}: building {building_id} does not exist in the dataset'
            
            # Check if building is already covered
            if building_id in building_coverage:
                return 0, False, f'Building {building_id} is covered by multiple antennas (antennas {building_coverage[building_id]} and {i})'
            
            building = building_map[building_id]
            building_x = building['x']
            building_y = building['y']
            
            # Check distance (euclidean)
            distance_sq = (antenna_x - building_x) ** 2 + (antenna_y - building_y) ** 2
            if distance_sq > antenna_spec['range'] ** 2:
                return 0, False, f'Antenna {i} at ({antenna_x}, {antenna_y}): building {building_id} at ({building_x}, {building_y}) is out of range (distance: {math.sqrt(distance_sq):.2f}, max range: {antenna_spec["range"]})'
            
            # Sum populations for each period
            total_peak += building['populationPeakHours']
            total_off_peak += building['populationOffPeakHours']
            total_night += building['populationNight']
            
            building_coverage[building_id] = i
        
        # Check capacity for each period
        max_load = max(total_peak, total_off_peak, total_night)
        if max_load > antenna_spec['capacity']:
            return 0, False, f'Antenna {i}: capacity exceeded during peak period (peak hours: {total_peak}, off-peak: {total_off_peak}, night: {total_night}, max capacity: {antenna_spec["capacity"]})'
    
    # Check that all buildings are covered
    uncovered_buildings = set(building_map.keys()) - set(building_coverage.keys())
    if uncovered_buildings:
        return 0, False, f'The following buildings are not covered by any antenna: {sorted(uncovered_buildings)}'
    
    # Score is the total cost (lower is better)
    # For ranking, we want lower cost to be better, so the score is just the cost
    success_message = f'Solution is valid! Total cost: {total_cost:,} €'
    
    return total_cost, True, success_message
