import osmnx as ox
import networkx as nx

def clean_adjacency_list(adj_list, keys_to_keep):
    """
    Cleans an adjacency list by dropping unnecessary features.

    Parameters:
    - adj_list: dict, adjacency list from nx.to_dict_of_dicts(G)
    - keys_to_keep: list, keys to retain in edge attributes

    Returns:
    - cleaned_adj_list: dict, adjacency list with only specified keys
    """
    cleaned_adj_list = {}
    for node, neighbors in adj_list.items():
        cleaned_adj_list[node] = {}
        for neighbor, edges in neighbors.items():
            cleaned_adj_list[node][neighbor] = {}
            for edge_key, attributes in edges.items():  # Account for multi-edges
                cleaned_attributes = {key: attributes[key] for key in keys_to_keep if key in attributes}
                if cleaned_attributes:  # Only add if attributes are retained
                    cleaned_adj_list[node][neighbor][edge_key] = cleaned_attributes
    return cleaned_adj_list

def extract_maxspeed(maxspeed_list):
    """
    Extract and return the maximum speed from a list of speed strings.
    Parameters:
    - maxspeed_list: list of speed limit strings (e.g., ['40 mph', '50 mph'])

    Returns:
    - max_speed: int, the maximum speed limit in the list (or a default value if unavailable).
    """
    speeds = []
    for speed in maxspeed_list:
        try:
            speeds.append(int(speed.split()[0]))  # Extract numeric part
        except (ValueError, IndexError):
            continue  # Skip invalid entries
    return max(speeds) if speeds else 50  # Default to 50 mph if no valid speed



def generate_sliced_static_network(filepath, north=37.8, south=37.77200, east=-122.38700, west=-122.42500):
    # calculate travel time - assume 60% average speed
    G = ox.load_graphml(filepath)
    for u, v, data in G.edges(data=True):
        if "maxspeed" in data:
            if isinstance(data["maxspeed"], list):  # Multiple speeds
                max_speed = extract_maxspeed(data["maxspeed"])
            else:  # Single speed
                max_speed = int(data["maxspeed"].split()[0]) if data["maxspeed"].isdigit() else 50  # Default to 50 mph
        else:
            max_speed = 25  # Default speed if maxspeed is missing

        # Convert max_speed to meters per second
        speed_mps = (max_speed * 0.6 * 1000) / 3600
        if "length" in data:
            data["travel_time"] = data["length"] / speed_mps  # Time in seconds

    # Define the bounding box: north, south, east, west
    north=north
    south=south
    east=east
    west=west  #37.8, 37.77200, -122.38700, -122.42500

    # Get nodes within the bounding box
    nodes_within_bbox = [n for n, d in G.nodes(data=True)
                         if south <= d['y'] <= north and west <= d['x'] <= east]

    # Create a subgraph with these nodes
    G_sliced = G.subgraph(nodes_within_bbox).copy()

    # Convert the osmnx graph to an adjacency list
    adj_list = nx.to_dict_of_dicts(G_sliced)

    # Define keys to keep
    keys_to_keep = ['length', 'geometry', 'lanes', 'oneway', 'reversed', 'maxspeed']

    # Clean the adjacency list
    cleaned_adj_list = clean_adjacency_list(adj_list, keys_to_keep)

    return G_sliced, cleaned_adj_list
