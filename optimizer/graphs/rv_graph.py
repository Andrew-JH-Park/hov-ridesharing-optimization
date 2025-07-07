from itertools import combinations
import networkx as nx
from optimizer.network.road_network import travel


def generate_rv_graph(graph, vehicles, requests, current_time, max_capacity=2, max_delay=600, prune_edges=False, top_k=30, debug=False):
    """
    Generate an RV graph with Request-Request (RR) and Vehicle-Request (VR) edges.

    Parameters:
    - graph: networkx.Graph, the road network.
    - vehicles: list of dicts, each containing vehicle attributes.
    - requests: list of dicts, each containing request attributes.
    - max_capacity: int, maximum passenger capacity per vehicle.
    - max_delay: int, maximum allowable delay time in seconds.
    - prune_edges: bool, whether to limit edges per node.
    - top_k: int, max edges per node when pruning.

    Returns:
    - rv_graph: networkx.Graph, the RV type graph.
    """

    import heapq

    # Helper function for pruning edges
    def prune_edges(rv_graph, top_k):
        """
        Prune edges in the RV graph to limit the maximum number of edges per node.

        Parameters:
        - rv_graph: networkx.Graph, the RV type graph.
        - top_k: int, maximum number of edges per node.

        Returns:
        - pruned_graph: networkx.Graph, a new graph with pruned edges.
        """
        # Make a copy of the original graph to avoid modifying in place
        pruned_graph = rv_graph.copy()

        for node in list(pruned_graph.nodes):

            if node.startswith("r"):
                edges = [(u, v, data) for u, v, data in pruned_graph.edges(node, data=True) if
                         data.get("edge_type") == "rr"]

            else:
                edges = [(u, v, data) for u, v, data in pruned_graph.edges(node, data=True) if
                         data.get("edge_type") == "rv"]

            # Check if the number of edges exceeds the limit
            if len(edges) > top_k:
                # Sort edges based on "travel_time" (or other cost metric)
                edges_sorted = sorted(edges, key=lambda e: e[2]["travel_time"])

                # Identify edges to remove (edges beyond the top_k)
                edges_to_remove = edges_sorted[top_k:]

                # Remove excess edges
                for u, v, _ in edges_to_remove:
                    pruned_graph.remove_edge(u, v)

        return pruned_graph

    rv_graph = nx.Graph()  # Create an empty type graph

    # Add request nodes
    for request in requests:
        rv_graph.add_node(request["id"], type="request", **request)

    # Add vehicle nodes
    for vehicle in vehicles:
        rv_graph.add_node(vehicle["id"], type="vehicle", **vehicle)

    print("RV graph - VR edge starting...")
    # Step 1: Vehicle-Request (VR) Edges
    for vehicle in vehicles:
        # Skip vehicles without spare capacity
        if vehicle["passengers"] >= max_capacity:
            if debug:
                print(f'\t skipping {vehicle["id"]} due to max passenger')
            continue

        print(f'Processing {vehicle["id"]}... into travel(vehicle, [request])')

        for request in requests:
            if debug:
                print(f'\t generating vid {vehicle["id"]} - request id: {request["id"]}')
            # Use the `travel` function to validate the trip
            valid_trip, trip_cost = travel(vehicle, [request], graph, max_capacity, max_delay, debug)
            if valid_trip:
                if debug:
                    print(f'\t \t adding valid edge {request["id"]} to {vehicle["id"]}')
                rv_graph.add_edge(vehicle["id"], request["id"], travel_time=trip_cost, stops= valid_trip, edge_type='rv')

    # Step 2: Request-Request (RR) Edges
    for req1, req2 in combinations(requests, 2):
        try:
            if debug:
                print(f'\t req-req edge evaluation at {req1["id"]}-{req2["id"]} - combinatorial comparison')

            max_delay_req1 = req1["t_r^*"] + max_delay
            max_delay_req2 = req2["t_r^*"] + max_delay

            # compare max waiting time
            o1d1 = nx.shortest_path_length(graph, source=req1["o_r"], target=req2["o_r"], weight="travel_time")
            d1o2 = nx.shortest_path_length(graph, source=req1["d_r"], target=req2["o_r"], weight="travel_time")
            o2d2 = nx.shortest_path_length(graph, source=req2["o_r"], target=req2["d_r"], weight="travel_time")
            o1o2 = nx.shortest_path_length(graph, source=req1["o_r"], target=req2["o_r"], weight="travel_time")
            d1d2 = nx.shortest_path_length(graph, source=req1["d_r"], target=req2["d_r"], weight="travel_time")

            if (current_time+o1d1 <= max_delay_req1 and current_time+o1d1+d1o2 <= req2["t_r^pl"] and current_time+o1d1+d1o2+o2d2 <= max_delay_req2) or \
                    (current_time+o1o2 <= req2["t_r^pl"] and current_time+o1o2+o2d2 <= max_delay_req2 and current_time+o1o2+o2d2+d1d2 <= max_delay_req1) or \
                    (current_time+o1o2 <= req2["t_r^pl"] and current_time+o1o2+d1o2 <= max_delay_req1 and current_time+o1o2+d1o2+d1d2 <= max_delay_req2):
                rv_graph.add_edge(req1["id"], req2["id"], travel_time=o1o2, edge_type='rr')

        except nx.NetworkXNoPath:
            continue

        # # Method 2 : use Travel function
        # try:
        #     if debug:
        #         print(f'\t req-req edge evaluation at {req1["id"]}-{req2["id"]} - combinatorial comparison')
        #     # Create a virtual vehicle at req1's origin with no passengers
        #     virtual_vehicle = {
        #         "id": 'virtual',
        #         "q_v": req1["o_r"],  # Start position at req1's origin
        #         "t_v": vehicles[-1]["t_v"],  # Current time set to req1's request time
        #         "passengers": 0,
        #         "trip_set": []  # No passengers initially
        #     }
        #
        #     # Run the travel function to validate the trip for [req1, req2]
        #     valid_trip, trip_cost = travel(virtual_vehicle, [req1, req2], graph, max_delay=max_delay, debug=True)
        #
        #     if valid_trip:
        #         # Add edge to the RV graph if the trip is valid
        #         rv_graph.add_edge(req1["id"], req2["id"], travel_time=trip_cost, edge_type='rr')
        #
        # except nx.NetworkXNoPath:
        #     # Skip if no path exists between the nodes
        #     continue
        #
        # # Method 1: wrong
        # try:
        #     # compare max waiting time
        #     travel_time = nx.shortest_path_length(
        #         graph, source=req1["o_r"], target=req2["o_r"], weight="travel_time"
        #     )
        #
        #     if req1["t_r^*"] + travel_time <= req2["t_r^pl"]:
        #         rv_graph.add_edge(req1["id"], req2["id"], travel_time=travel_time, edge_type='rr')
        # except nx.NetworkXNoPath:
        #     continue

    # Prune edges if requested
    if prune_edges:
        rv_graph = prune_edges(rv_graph, top_k=top_k)

    return rv_graph

def visualize_rv_graph(graph, rv_graph, filepath="rv_graph_visualization.png"):
    """
    Visualize the RV graph with VR (Vehicle-Request) and RR (Request-Request) edges overlaid on the road network,
    and differentiate nodes based on their types (vehicles and requests).

    Parameters:
    - graph: networkx.Graph, the road network.
    - rv_graph: networkx.Graph, the RV graph with edge_type attribute ('rv' or 'rr').
    - filepath: str, file path to save the visualization.

    Returns:
    - None (saves the visualization to the specified file path).
    """
    import matplotlib.pyplot as plt
    import osmnx as ox

    # Base road network visualization
    fig, ax = ox.plot_graph(graph, show=False, close=False, node_size=5, edge_color="gray", bgcolor="white")

    # Get positions for road network nodes
    pos = {node: (data['x'], data['y']) for node, data in graph.nodes(data=True)}

    # Plot nodes (vehicles and requests)
    for node, data in rv_graph.nodes(data=True):
        if data["type"] == "vehicle":  # Vehicle nodes
            vehicle_pos = pos.get(data["q_v"])
            if vehicle_pos:
                ax.scatter(vehicle_pos[0], vehicle_pos[1], c="blue", s=50, label="Vehicle" if "Vehicle" not in ax.get_legend_handles_labels()[1] else None)
        elif data["type"] == "request":  # Request nodes
            request_pos = pos.get(data["o_r"])
            if request_pos:
                ax.scatter(request_pos[0], request_pos[1], c="red", s=30, label="Request" if "Request" not in ax.get_legend_handles_labels()[1] else None)

    # Draw edges with different colors based on edge_type
    for u, v, edge_data in rv_graph.edges(data=True):
        # edge_type = edge_data.get("edge_type", "unknown")  # Default to unknown if edge_type is missing
        # Determine roles of nodes based on type attribute
        if rv_graph.nodes[u]["type"] == "vehicle" or rv_graph.nodes[v]["type"] == "vehicle":
            if pos.get(rv_graph.nodes[u].get("q_v")):
                vehicle_pos = pos.get(rv_graph.nodes[u].get("q_v"))
                request_pos = pos.get(rv_graph.nodes[v].get("o_r"))
            else:
                vehicle_pos = pos.get(rv_graph.nodes[v].get("q_v"))
                request_pos = pos.get(rv_graph.nodes[u].get("o_r"))

            ax.plot([vehicle_pos[0], request_pos[0]], [vehicle_pos[1], request_pos[1]],
                    c="blue", linestyle="--", alpha=0.7, linewidth=1,
                    label="VR Edge" if "VR Edge" not in ax.get_legend_handles_labels()[1] else None)

        elif rv_graph.nodes[u]["type"] == "request" and rv_graph.nodes[v]["type"] == "request":
            request_u_pos = pos.get(rv_graph.nodes[u].get("o_r"))
            request_v_pos = pos.get(rv_graph.nodes[v].get("o_r"))

            ax.plot([request_u_pos[0], request_v_pos[0]], [request_u_pos[1], request_v_pos[1]],
                    c="green", linestyle="-", alpha=0.7, linewidth=1, label="RR Edge" if "RR Edge" not in ax.get_legend_handles_labels()[1] else None)

        else:
            print(f'warning: unrecognized edge at u: {rv_graph.nodes[u].get("id")} & v: {rv_graph.nodes[v].get("id")}')

    # Add legend and save the figure
    ax.legend(loc="upper right")
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def visualize_rv_graph_with_annotations(graph, rv_graph, option_od = True, option_rv = True, filepath="rv_graph_visualization_with_annotation.png"):
    """
    Visualize the RV graph with VR (Vehicle-Request) and RR (Request-Request) edges overlaid on the road network,
    and differentiate nodes based on their types (vehicles and requests).

    Parameters:
    - graph: networkx.Graph, the road network.
    - rv_graph: networkx.Graph, the RV graph with edge_type attribute ('rv' or 'rr').
    - filepath: str, file path to save the visualization.

    Returns:
    - None (saves the visualization to the specified file path).
    """
    import matplotlib.pyplot as plt
    import osmnx as ox

    # Base road network visualization
    fig, ax = ox.plot_graph(graph, show=False, close=False, node_size=5, edge_color="gray", bgcolor="white")

    # Get positions for road network nodes
    pos = {node: (data['x'], data['y']) for node, data in graph.nodes(data=True)}

    # Plot nodes (vehicles and requests)
    for node, data in rv_graph.nodes(data=True):
        if data["type"] == "vehicle":  # Vehicle nodes
            vehicle_pos = pos.get(data["q_v"])
            if vehicle_pos:
                ax.scatter(vehicle_pos[0], vehicle_pos[1], c="blue", s=50, label="Vehicle" if "Vehicle" not in ax.get_legend_handles_labels()[1] else None)
                ax.text(vehicle_pos[0], vehicle_pos[1], data["passengers"], fontsize=9, color="green", ha="right", va="top")

                if option_od:
                    if len(data["trip_set"]) > 0:
                        for req_v in data["trip_set"]:
                            dest_v = pos.get(req_v["d_r"])
                            ax.plot([vehicle_pos[0], dest_v[0]], [vehicle_pos[1], dest_v[1]], c="purple",
                                    linestyle="--", marker=">", alpha=0.7, linewidth=1,
                                    label="Vehicle Route" if "Vehicle Route" not in ax.get_legend_handles_labels()[1] else None)
                            vehicle_pos = dest_v

        elif data["type"] == "request":  # Request nodes
            request_pos = pos.get(data["o_r"])
            request_des = pos.get(data["d_r"])

            if request_pos:
                ax.scatter(request_pos[0], request_pos[1], c="red", s=30, label="Request" if "Request" not in ax.get_legend_handles_labels()[1] else None)
                if option_od:
                    ax.plot([request_pos[0], request_des[0]], [request_pos[1], request_des[1]], c="orange", linestyle="--", marker=">", alpha=0.7, linewidth=1,
                            label="OD Pair" if "OD Pair" not in ax.get_legend_handles_labels()[1] else None)

    if option_rv:
        # Draw edges with different colors based on edge_type
        for u, v, edge_data in rv_graph.edges(data=True):
            # edge_type = edge_data.get("edge_type", "unknown")  # Default to unknown if edge_type is missing
            # Determine roles of nodes based on type attribute
            if rv_graph.nodes[u]["type"] == "vehicle" or rv_graph.nodes[v]["type"] == "vehicle":
                if pos.get(rv_graph.nodes[u].get("q_v")):
                    vehicle_pos = pos.get(rv_graph.nodes[u].get("q_v"))
                    request_pos = pos.get(rv_graph.nodes[v].get("o_r"))
                else:
                    vehicle_pos = pos.get(rv_graph.nodes[v].get("q_v"))
                    request_pos = pos.get(rv_graph.nodes[u].get("o_r"))

                ax.plot([vehicle_pos[0], request_pos[0]], [vehicle_pos[1], request_pos[1]],
                        c="purple", linestyle="--", alpha=0.7, linewidth=1,
                        label="VR Edge" if "VR Edge" not in ax.get_legend_handles_labels()[1] else None)

            elif rv_graph.nodes[u]["type"] == "request" and rv_graph.nodes[v]["type"] == "request":
                request_u_pos = pos.get(rv_graph.nodes[u].get("o_r"))
                request_v_pos = pos.get(rv_graph.nodes[v].get("o_r"))

                request_u_des = pos.get(rv_graph.nodes[u].get("d_r"))
                request_v_des = pos.get(rv_graph.nodes[v].get("d_r"))

                ax.plot([request_u_pos[0], request_v_pos[0]], [request_u_pos[1], request_v_pos[1]],
                        c="green", linestyle="-", alpha=0.7, linewidth=1, label="RR Edge" if "RR Edge" not in ax.get_legend_handles_labels()[1] else None)

            else:
                print(f'warning: unrecognized edge at u: {rv_graph.nodes[u].get("id")} & v: {rv_graph.nodes[v].get("id")}')

    # Add legend and save the figure
    ax.legend(loc="upper right")
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)

