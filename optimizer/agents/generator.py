import random
import networkx as nx

# Function to generate random vehicles
def generate_requests_for_vehicle(graph, vehicle_node, num_passengers, omega=600, max_delay=600):
    """
    Generate a set of requests for a given vehicle and its passengers, ensuring feasibility.

    Parameters:
    - graph: networkx.Graph, road network with precomputed travel times.
    - vehicle_node: int, current position of the vehicle (node ID).
    - num_passengers: int, number of passengers to generate requests for.
    - max_delay: int, maximum delay allowed for arrival at destinations (in seconds).

    Returns:
    - trip_set: list of dicts, each representing a request with pickup/drop-off info.
    """
    nodes = list(graph.nodes)
    trip_set = []
    current_time = 0  # Assume the vehicle is at time 0
    time_offset = -80  # Each passenger picked up at intervals of -80 seconds

    for i in range(num_passengers):
        pickup_time = 0
        expected_arrival_time = 0
        while True:
            # Generate random origin and destination
            origin = vehicle_node if i == 0 else random.choice(nodes)  # First origin is vehicle's current position
            destination = random.choice(nodes)
            while destination == origin:  # Ensure origin and destination are different
                destination = random.choice(nodes)

            try:
                # Calculate travel time from origin to destination
                travel_time = nx.shortest_path_length(
                    graph, source=origin, target=destination, weight="travel_time"
                )
                # Calculate pickup time and drop-off time
                pickup_time = current_time + ((i+1) * time_offset)  # Offset based on passenger order
                expected_arrival_time = pickup_time + travel_time

                # Ensure drop-off time satisfies time constraints
                if expected_arrival_time <= (pickup_time + max_delay):
                    break  # Exit loop if valid request
            except nx.NetworkXNoPath:
                continue  # Retry with a new destination if no path exists

        # Add request to trip set
        trip_set.append({
            "id": f"r_p{i + 1}",  # Request ID
            "o_r": origin,  # Origin node
            "d_r": destination,  # Destination node
            "t_r^r": pickup_time-30,
            "t_r^pl": pickup_time - 30 + omega,
            "t_r^p": pickup_time,  # Pickup time
            "t_r^d": expected_arrival_time,  # Drop-off time
            "t_r^*": expected_arrival_time-30  # Earliest drop-off time
        })

    return trip_set

def initialize_vehicles(graph, num_vehicles, max_capacity=2, omega=600, max_delay=600):
    """
    Initialize random vehicles across the graph.

    Parameters:
    - graph: networkx.Graph, the road network
    - num_vehicles: int, number of vehicles to generate
    - max_passengers: int, maximum number of passengers per vehicle

    Returns:
    - vehicles: list of dicts, each containing vehicle info
    """
    nodes = list(graph.nodes)
    vehicles = []
    for i in range(num_vehicles):
        print(f'initializing vehicle {i}')
        current_passengers = random.randint(0, max_capacity)  # Random passenger count

        # Randomly assign vehicle position
        vehicle_node = random.choice(nodes)

        # Generate a trip set for the vehicle based on the current passengers
        trip_set = generate_requests_for_vehicle(graph, vehicle_node, current_passengers, omega, max_delay)

        vehicle = {
            "id": f"v{i + 1}",  # Unique vehicle ID
            "q_v": vehicle_node,  # Randomly assigned node (position)
            "t_v": 0,  # Current time (always 0 initially)
            "passengers": current_passengers,  # Random passenger count
            "trip_set": trip_set  # Initial trip set for current passengers
        }
        vehicles.append(vehicle)
    return vehicles

# Function to generate requests
def generate_requests(graph, num_requests, omega=600):
    """
    Generate a set of random requests with origins, destinations, and attributes.

    Parameters:
    - graph: networkx.Graph, road network with precomputed travel times
    - num_requests: int, number of requests to generate
    - omega: int, maximum wait time in seconds (default: 600 seconds)

    Returns:
    - requests: list of dicts, each containing request attributes
    """
    nodes = list(graph.nodes)
    generated_requests = []
    travel_time = -1
    for i in range(num_requests):
        while True:  # Loop until a valid origin-destination pair is found
            origin = random.choice(nodes)
            destination = random.choice(nodes)
            if origin != destination:  # Ensure origin and destination are different
                try:
                    # Test reachability and calculate travel time
                    travel_time = nx.shortest_path_length(graph, source=origin, target=destination,
                                                          weight="travel_time")
                    break  # Exit the loop if reachable
                except nx.NetworkXNoPath:
                    # If not reachable, retry with a new pair
                    continue

        if travel_time > 0:
            # Compute the earliest drop-off time t_r*
            t_r_star = travel_time  # Earliest drop-off time

            # Create request dictionary
            new_request = {
                "id": f"r{i + 1}",  # Request ID
                "o_r": origin,  # Origin node
                "d_r": destination,  # Destination node
                "t_r^r": 0,  # Request time
                "t_r^pl": 0 + omega,  # Latest acceptable pickup time
                "t_r^p": -1, # pick up time
                "t_r^d": -1, # expected drop off
                "t_r^*": 0 + t_r_star  # Earliest drop-off time
                # t_r^p and t_r^d will be computed during vehicle matching
            }
            generated_requests.append(new_request)
    return generated_requests

# Function to check each request is reachable
def validate_request_reachability(graph, requests, vehicles):
    """
    Validates that each request's origin is reachable by at least one vehicle.

    Parameters:
    - graph: networkx.Graph, road network with precomputed travel times
    - requests: list of dicts, each containing request attributes
    - vehicles: list of dicts, each containing vehicle attributes

    Returns:
    - reachable_requests: list of dicts, requests that are reachable by at least one vehicle
    - unreachable_requests: list of dicts, requests that are unreachable
    """
    reachable_requests = []
    unreachable_requests = []

    for request in requests:
        o_r = request["o_r"]  # Origin node of the request
        is_reachable = False
        for vehicle in vehicles:
            q_v = vehicle["q_v"]  # Current node of the vehicle
            # Check if there's a path from vehicle's position to the request origin
            if nx.has_path(graph, source=q_v, target=o_r):
                is_reachable = True
                break  # No need to check further vehicles if one is reachable

        if is_reachable:
            reachable_requests.append(request)
        else:
            unreachable_requests.append(request)

    return reachable_requests, unreachable_requests