# Web Server Performance Analysis - Discrete Event Simulation (DES)

This project implements a Discrete Event Simulation (DES) to analyze the performance of a multi-user web server system. It compares simulation results against MVA and experimental measurements across different service and think time distributions.

## Directory Structure

* `src/`: C++ source code for the simulation engine.
* `results/`: Contains simulation CSV results and generated plots.
* `mva_model.py`: Mean Value Analysis implementation.
* `run_experiments.py`: Automation script to run simulation/MVA batches for all distributions.
* `plot_results.py`: Generates visualization and comparison graphs.
* `compare_accuracy.py`: Calculates RMSE and accuracy rankings between models.
* `run_analysis.py`: Orchestrates "What-If" isolation experiments.
* `config.txt`: Configuration file for system parameters.
* `what_if_analysis/`: Output directory for isolation experiment results, plots, and reports.

## Build Instructions

The simulation is written in C++17. Build the executable using the provided Makefile:

```bash
make 
```

To remove build artifacts:

```bash
make clean
```

## Running the Experiments

To run the full suite of experiments (CONSTANT, UNIFORM, and EXPONENTIAL distributions for both think and service times):

```bash
make run
```

This script will:
1. Build the simulator.
2. Iterate through all distribution combinations.
3. Update `config.txt` and execute the simulation for each batch.
4. Generate all the plots
5. Run the MVA model for theoretical comparison.

### Manual Execution

To run a specific distribution manually:
1. Edit `config.txt` and set `service_distribution` and `think_distribution` (options: `CONSTANT`, `UNIFORM`, `EXPONENTIAL`).
2. Run the compiled binary:

```bash
./web_sim
```

This will execute the simulation for the user counts specified in the config and output the results directly.

## Generating Plots & Analysis

After running the experiments, generate the graphs:

```bash
python3 plot_results.py
```

This will populate the `results/` subdirectories with PNG plots including:
- Response Time vs. Number of Users
- Throughput vs. Number of Users
- Server Utilization vs. Number of Users
- Performance Curves (Response Time vs. Throughput)

To calculate accuracy rankings (RMSE):

```bash
python3 compare_accuracy.py
```
## "What-If" Analysis

The project includes an isolation testing suite to answer technical "What-If" questions about server architecture and load handling.

```bash
python3 run_analysis.py
```

Results, including annotated plots and technical reports, are stored in `what_if_analysis/`.


## Configuration

System parameters can be adjusted in `config.txt`:
- `mean_think`: Average user think time (seconds).
- `mean_service`: Average server processing time per request (seconds).
- `ctx_overhead`: Context switching overhead (seconds).
- `time_slice`: Round Robin time quantum (seconds).
- `max_queue_size`: Maximum requests allowed in the server queue (-1 for infinite).
- `user_counts`: List of user loads to simulate.


### Assignment report : des_assignment.pdf
https://docs.google.com/presentation/d/1eYaL_txCG35z2D7fplwjQAiZABAEY2EEwAX7MIRHkoo/edit?usp=sharing