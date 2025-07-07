from itertools import permutations
import networkx as nx

def travel(vehicle, new_requests, graph, max_capacity=2, max_delay=600, debug=False):
    """
    Compute the shortest feasible trip sequence for a vehicle and a set of requests,
    considering all permutations of stops, including flexible pickup positions for new requests.

    Parameters:
    - vehicle: dict, vehicle attributes (current position, trip set, passengers).
    - requests: list of dicts, new requests to validate.
    - graph: networkx.Graph, road network.
    - max_delay: int, maximum allowable delay time in seconds.

    Returns:
    - tuple: (valid_trip, shortest_trip_cost)
        - valid_trip: list of dicts, the shortest valid trip sequence.
        - shortest_trip_cost: float, the total travel cost for the trip.
    """

    if not new_requests and not vehicle["trip_set"]:
        # No requests to process
        return None, float("inf")

    if not new_requests:
        # Only handle drop-offs for existing passengers
        return vehicle["trip_set"], 0  # Assuming no additional cost

    # Prepare stops: drop-offs for existing passengers and both pickup/drop-off for new requests
    stops = [{"type": "dropoff", "node": r["d_r"], "request": r} for r in vehicle["trip_set"]] + \
            [{"type": "pickup", "node": r["o_r"], "request": r} for r in new_requests] + \
            [{"type": "dropoff", "node": r["d_r"], "request": r} for r in new_requests]

    shortest_trip = None
    shortest_trip_cost = float("inf")

    # Helper function to validate pickup-before-dropoff
    def is_valid_permutation(permutation):
        """
        Validate a stop permutation considering pickup-before-dropoff constraints and additional rules
        for when drop-offs must occur before pickups of new requests.

        Parameters:
        - permutation: list of stops (pickup/dropoff)
        Returns:
        - bool: True if the permutation satisfies all constraints, False otherwise.
        """
        if debug:
            print(f'evaluating permutation: {permutation}')

        # Track pickup and drop-off statuses
        pickup_seen = set()
        dropoffs_made = 0
        pickups_made = 0

        # vehicle is empty
        if not vehicle["trip_set"]:
            for stop in permutation:
                if stop["type"] == "dropoff":
                    # Ensure drop-off happens only after its pickup
                    if stop["request"]["id"] not in pickup_seen:
                        if debug:
                            print(f'\t\t\tdropped off before pickup at stop: {stop}')
                        return False
                    dropoffs_made += 1

                elif stop["type"] == "pickup":
                    # Allow pickup since no other passengers are in the vehicle
                    pickup_seen.add(stop["request"]["id"])
                    pickups_made += 1

                    # Ensure pickups do not exceed current drop-offs
                    if pickups_made > dropoffs_made + max_capacity:
                        if debug:
                            print(f'\t\t\tpick up made exceeded maximum: {stop}')
                        return False

        # vehicle is not empty
        else:
            dropoffs_made = 0
            pickups_made =  len(vehicle["trip_set"])
            pickup_seen.update({r["id"] for r in vehicle["trip_set"]})
            min_dropoffs_before_new_pickups = max(0, len(new_requests) - max_capacity + len(vehicle["trip_set"]))

            for stop in permutation:
                if stop["type"] == "dropoff":
                    dropoffs_made += 1

                    # Ensure drop-off happens only after its pickup
                    if stop["request"]["id"] not in pickup_seen:
                        if debug:
                            print(f'\t\t\tdrop-off made before pickup: {stop}')
                        return False

                elif stop["type"] == "pickup":
                    # Enforce rule: New pickups can only occur after required drop-offs
                    if dropoffs_made < min_dropoffs_before_new_pickups:
                        if debug:
                            print(f'\t\t\t pick up can be made after required pick up: pu-made - {pickups_made}, do req: {min_dropoffs_before_new_pickups}, stop: {stop}')
                        return False

                    pickup_seen.add(stop["request"]["id"])
                    pickups_made += 1

                    # Ensure pickups do not exceed current drop-offs + existing trip capacity
                    if pickups_made > dropoffs_made + len(vehicle["trip_set"]):
                        if debug:
                            print(f'\t\t\t vehicle passenger going below 0 - stop: {stop}')
                        return False

        return True

    for stop_order in filter(is_valid_permutation, permutations(stops)):
        if debug:
            for stop in stop_order:
                print(f'\t {stop["request"]["id"]}-{stop["type"]}')

        current_time = vehicle["t_v"]
        current_position = vehicle["q_v"]
        valid = True
        total_cost = 0

        for stop in stop_order:
            if debug:
                print(f'\t {stop["request"]["id"]}-{stop["type"]}')
            # Travel to the next stop
            try:
                travel_time = nx.shortest_path_length(
                    graph, source=current_position, target=stop["node"], weight="travel_time"
                )
            except nx.NetworkXNoPath:
                valid = False
                break

            current_time += travel_time
            total_cost += travel_time

            # Ensure pickup is valid (max waiting time)
            if stop["type"] == "pickup" and current_time > stop["request"]["t_r^pl"]:
                valid = False
                break

            elif stop["type"] == "dropoff":
                # Ensure drop-off is valid (max delay)
                t_r_star = stop["request"]["t_r^*"]
                if current_time > t_r_star + max_delay:
                    valid = False
                    break

            # Update current position
            current_position = stop["node"]

        if valid and total_cost < shortest_trip_cost:
            shortest_trip = stop_order
            shortest_trip_cost = total_cost

    if shortest_trip:
        return [stop for stop in shortest_trip], shortest_trip_cost
    else:
        return None, float("inf")  # No valid trip found
