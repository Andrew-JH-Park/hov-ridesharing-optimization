# HOV Ridesharing Optimization Module

This project implements a real-time optimization algorithm for assigning vehicles to ride requests in a shared autonomous vehicle (SAV) setting. It builds on dynamic trip-vehicle assignment principles introduced by Alonso-Mora et al. and formulates the matching process as an ILP-based optimization problem. This module is designed to be embedded in larger simulation environments or used for offline evaluation of algorithm performance.

---

## 🚀 Features

- Static road network loading from `.graphml` (OpenStreetMap)
- Random request and vehicle generation
- Request-Vehicle (RV) graph construction
- Request-Trip-Vehicle (RTV) graph construction
- Greedy heuristic and MILP optimization (via Gurobi)
- Visual output of final assignment

---

## 📂 Project Structure

```
hov-ridesharing-optimization/
├── data/                             # Road network input and output images
│   ├── san_francisco.graphml        # Example road network
│   └── out_ilp_assignment_visualization.png
├── scripts/
│   └── run_solver.py                # Main entry point
├── optimizer/
│   ├── agents/                      # Request and vehicle generators
│   ├── graphs/                      # RV and RTV graph construction
│   ├── network/                     # Road network generation and utilities
│   └── solver/                      # Optimization logic (greedy + ILP)
├── report.pdf                       # Final project report
└── README.md
```

---

## 📖 Problem Overview

At each decision epoch, the system aims to:

1. Construct feasible **trip-vehicle** combinations respecting:
   - Pickup time windows (Ω)
   - Maximum travel delay (Δ)
   - Vehicle capacity
2. Build the **RTV graph** where:
   - Nodes = trips, vehicles
   - Edges = feasible assignments
3. Solve an **integer linear program (ILP)** to minimize:
   - Total passenger delay
   - Penalty for unserved requests

---

## ⚙️ Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> Make sure you have a valid [Gurobi license](https://www.gurobi.com/downloads/) and `gurobipy` installed.

### 2. Run optimization

```bash
python scripts/run_solver.py
```

#### Optional arguments:
| Flag              | Description                      | Default |
|-------------------|----------------------------------|---------|
| `--mc`            | Max vehicle capacity             | 2       |
| `--om`            | Max pickup window (Ω) in sec     | 200     |
| `--md`            | Max delay (Δ) in sec             | 300     |
| `--num_vehicles`  | Number of vehicles               | 25      |
| `--num_requests`  | Number of ride requests          | 50      |

---

## 🗺️ Input Data

- Road network: `.graphml` file loaded from `./data/`
- Vehicle/request positions are sampled from the road network nodes

---

## 🖼️ Output

- ILP assignment visualized as `out_ilp_assignment_visualization.png`
- Console output shows how many requests were reachable and assigned

---

## 📚 References

- Alonso-Mora et al., 2017. *On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment*. PNAS.
- Jiang et al., 2024. *Large-scale multi-GPU based parallel traffic simulation*. TR Part C.
- OpenStreetMap Contributors, 2024.

See `report.pdf` for full documentation.

---

## 🧠 Future Work

- Integration with real-time simulators (e.g., SUMO, LPSim)
- Energy-optimal routing and battery-aware fleet models
- GPU-accelerated RTV graph computation
- Support for real-world demand datasets

---

## 🧑‍💻 Author

**Andrew Park**  
EE227BT Final Project – UC Berkeley  
Contact: `jungho.park@berkeley.edu`
