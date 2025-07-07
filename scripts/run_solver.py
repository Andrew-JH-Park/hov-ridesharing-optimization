import argparse
import os
from pathlib import Path

from optimizer.network.network_generator import generate_sliced_static_network
import optimizer.agents.generator as generator
from optimizer.graphs.rv_graph import generate_rv_graph
from optimizer.graphs.rtv_graph import generate_rtv_graph, visualize_assignment
import optimizer.solver.problem_formulation as solve

# define parameters
MAX_CAPACITY = 2
OMEGA = 200
MAX_DELAY = 300
NUM_VEHICLES = 25
NUM_REQUESTS = 50

DEBUG = False

def main(config):
    current_time = 0
    script_dir = Path(__file__).resolve().parent.parent


    graph,_ = generate_sliced_static_network(filepath=os.path.join(script_dir, "data", "san_francisco.graphml"))
    vehicles = generator.initialize_vehicles(graph,
                                   num_vehicles=config.num_vehicles,
                                   max_capacity=config.mc,
                                   omega=config.om,
                                   max_delay=config.md)

    requests = generator.generate_requests(graph,
                                 num_requests=config.num_requests,
                                 omega=config.om)

    reachable_requests, unreachable_requests = generator.validate_request_reachability(graph, requests, vehicles)

    # Print results
    print(f"Reachable requests: {len(reachable_requests)}")
    print(f"Unreachable requests: {len(unreachable_requests)}")

    rv_graph = generate_rv_graph(
        graph=graph,
        vehicles=vehicles,
        requests=reachable_requests,
        current_time=current_time,
        max_capacity=config.mc,
        max_delay=config.md,
        prune_edges=True,
        top_k=10,
        debug=DEBUG
    )

    rtv_graph = generate_rtv_graph(rv_graph,
                                   vehicles,
                                   requests,
                                   graph,
                                   max_capacity=config.mc,
                                   max_delay=config.md,
                                   debug=DEBUG)

    # Perform Greedy Assignment for initial solution
    initial_assignment = solve.greedy_assignment(rtv_graph, vehicles, debug=DEBUG)
    optimized_assignment = solve.assignment_ilp(rtv_graph, vehicles, requests, initial_assignment,
                                                cost_penalty=1000,
                                                time_limit=30,
                                                gap=0.001)

    visualize_assignment(graph, vehicles, requests, optimized_assignment, rtv_graph,
                         filepath="data/out_ilp_assignment_visualization.png")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ridesharing optimization solver")
    parser.add_argument("--mc", type=int, default=MAX_CAPACITY,
                        help="max vehicle passenger capacity")
    parser.add_argument("--om", type=int, default=OMEGA,
                        help="NA")
    parser.add_argument("--md", type=int, default=MAX_DELAY,
                        help="Maximum trip delay in seconds")
    parser.add_argument("--num_vehicles", type=int, default=NUM_VEHICLES,
                        help="Number of vehicles in fleet")
    parser.add_argument("--num_requests", type=int, default=NUM_REQUESTS,
                        help="Number of requests in the system")

    args = parser.parse_args()
    main(args)