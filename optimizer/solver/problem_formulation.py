import networkx as nx
from gurobipy import Model, GRB, quicksum

def greedy_assignment(rtv_graph, vehicles, debug=False):
    """
    Perform greedy assignment of trips to vehicles based on Algorithm 2.

    Parameters:
    - rtv_graph: networkx.Graph, the RTV graph containing trips, vehicles, and requests.
    - vehicles: list of dicts, vehicle attributes.
    - requests: list of dicts, request attributes.

    Returns:
    - assignment: dict, mapping of vehicle IDs to trip IDs.
    """
    assignment = {}
    # only include vehicles with non-zero degrees
    unassigned_vehicles = {vehicle["id"] for vehicle in vehicles if rtv_graph.degree(vehicle["id"]) > 0}
    assigned_requests = set()

    # Iterate until no vehicles or trips can be assigned
    while unassigned_vehicles:
        best_vehicle = None
        best_trip = None
        min_cost = float("inf")

        # Iterate over all vehicles and trips in the RTV graph
        for vehicle_id in unassigned_vehicles:
            neighbors = list(rtv_graph.neighbors(vehicle_id))

            for trip_id in neighbors:
                if rtv_graph.nodes[trip_id]["type"] == "trip":

                    # Check if trip involves already assigned requests
                    trip_requests = rtv_graph.nodes[trip_id]["requests"]
                    number_of_trips = len(trip_requests)

                    if trip_requests & assigned_requests:
                        continue  # Skip trips with already assigned requests

                    # Calculate the cost of assigning this trip to the vehicle
                    edge_data = rtv_graph.get_edge_data(vehicle_id, trip_id, {})
                    cost = edge_data.get("travel_time", float("inf"))
                    relative_cost = cost/number_of_trips # greedily look for a vehicle that can support multiple trips

                    if relative_cost < min_cost:
                        min_cost = relative_cost
                        best_vehicle = vehicle_id
                        best_trip = trip_id

                        if debug and vehicle_id == 'v3':
                                print(
                                    f'{vehicle_id} - {trip_id} trip assigned \t\t'
                                    f'length: {len(rtv_graph.nodes[trip_id]["requests"])} '
                                    f'trips: {rtv_graph.nodes[trip_id]["requests"]} '
                                    f'cost: {rtv_graph.nodes[trip_id]["cost"]} '
                                    f'relative cost: {relative_cost}')

        # Assign the best trip to the best vehicle
        if best_vehicle and best_trip:
            assignment[best_vehicle] = best_trip
            unassigned_vehicles.remove(best_vehicle)

            # Mark requests in the assigned trip as served
            for request_id in rtv_graph.neighbors(best_trip):
                if rtv_graph.nodes[request_id]["type"] == "request":
                    assigned_requests.add(request_id)
        else:
            break  # No more feasible assignments can be made

    return assignment

def assignment_ilp(rtv_graph, vehicles, requests, greedy_assignment, cost_penalty=1000, time_limit=30, gap=0.001):
    """
    Perform ILP optimization for trip-vehicle assignment using Gurobi.

    Parameters:
    - rtv_graph: networkx.Graph, the RTV graph containing trips, vehicles, and requests.
    - vehicles: list of dicts, vehicle attributes.
    - requests: list of dicts, request attributes.
    - greedy_assignment: dict, initial feasible solution from the greedy algorithm.
    - cost_penalty: float, penalty for unserved requests.
    - time_limit: int, time limit for solving the ILP (in seconds).
    - gap: float, optimality gap (e.g., 0.001 for 0.1%).

    Returns:
    - optimal_assignment: dict, refined mapping of vehicle IDs to trip IDs.
    """
    # Create the Gurobi model
    model = Model("Ride_Sharing_Optimization")
    model.setParam("TimeLimit", time_limit)
    model.setParam("MIPGap", gap)

    # Define variables
    epsilon = {}  # Binary variables for trip-vehicle assignments
    chi = {}  # Binary variables for unserved requests

    # Define epsilon_{i,j} for all trip-vehicle pairs in the RTV graph
    for trip in rtv_graph.nodes:
        if rtv_graph.nodes[trip]["type"] == "trip":
            for neighboring_node in rtv_graph.neighbors(trip):
                if rtv_graph.nodes[neighboring_node]["type"] == "vehicle":
                    epsilon[(trip, neighboring_node)] = model.addVar(vtype=GRB.BINARY, name=f"epsilon_{trip}_{neighboring_node}")

    # Define chi for all requests
    for request in requests:
        chi[request["id"]] = model.addVar(vtype=GRB.BINARY, name=f"chi_{request['id']}")

    # Set the objective function
    trip_cost_terms = quicksum(
        rtv_graph.edges[trip, vehicle]["travel_time"] * epsilon[(trip, vehicle)]
        for trip, vehicle in epsilon
    )
    unserved_penalty_terms = quicksum(
        cost_penalty * chi[request["id"]] for request in requests
    )
    model.setObjective(trip_cost_terms + unserved_penalty_terms, GRB.MINIMIZE)


    # Constraint 1: Each vehicle is assigned to at most one trip
    for vehicle_data  in vehicles:
        vehicle_id = vehicle_data["id"]
        vehicle_edges = [
            (trip, vehicle)
            for trip, vehicle in epsilon
            if vehicle == vehicle_id
        ]
        # print(vehicle_edges)
        model.addConstr(
            quicksum(epsilon[edge] for edge in vehicle_edges) <= 1,
            name=f"VehicleConstraint_{vehicle_id}"
        )

    # Constraint 2: Each request is assigned to one trip or marked unserved
    for request in requests:
        # Identify all trips that include this request
        relevant_trips = [
            trip for trip in rtv_graph.nodes
            if rtv_graph.nodes[trip]["type"] == "trip" and
               request["id"] in rtv_graph.nodes[trip]["requests"]
        ]

        # Loop over these trips and their connected vehicles
        relevant_edges = [
            (trip, vehicle)
            for trip in relevant_trips
            for vehicle in rtv_graph.neighbors(trip)
            if (trip, vehicle) in epsilon
        ]

        # print(relevant_edges)

        # Add the constraint
        model.addConstr(
            quicksum(epsilon[edge] for edge in relevant_edges) + chi[request["id"]] == 1,
            name=f"RequestConstraint_{request['id']}"
        )

    for vehicle, trip in greedy_assignment.items():
        if (trip, vehicle) in epsilon:
            epsilon[(trip, vehicle)].start = 1


    # Optimize the model
    model.optimize()

    # Extract the optimal assignment
    optimal_assignment = {}
    for edge in epsilon:
        if epsilon[edge].x > 0.5:  # If assigned
            trip, vehicle = edge
            optimal_assignment[vehicle] = trip

    return optimal_assignment

