# RL-Optimizer: Reinforcement Learning for LLVM Compiler Pass Sequencing

## Overview
**RL-Optimizer** is an experimental machine learning framework that leverages Reinforcement Learning (Proximal Policy Optimization) to autonomously discover optimal LLVM compiler pass sequences. By wrapping the LLVM/Clang toolchain in a custom Gymnasium environment, the agent dynamically navigates the compiler optimization space to out-perform standard, human-engineered static heuristics (`-O1`, `-O2`, `-O3`). 

Unlike standard optimization suites, this agent utilizes a multi-objective reward function that explicitly balances **binary size reduction**, **execution speed**, and **static security constraints** while maintaining 100% execution correctness.

---

## Key Features
*   **Custom LLVM Gym Environment (`llvm_env.py`):** A custom reinforcement learning environment that directly interfaces with LLVM's `opt` and `clang` tools to apply dynamic optimization passes.
*   **Intelligent Feature Extraction (`feature_extractor.py`):** Parses raw LLVM Intermediate Representation (IR) to feed meaningful state representations into the PPO agent.
*   **Security-Aware Optimization (`security_analyzer.py`):** Tracks and penalizes optimization sequences that introduce security violations or strip away necessary safety checks.
*   **Multi-Objective Rewards:** Agent is rewarded based on a highly-tuned balance of runtime reduction, text-section size compression, and pipeline efficiency.

---

## Benchmark Results
The PPO agent was evaluated against standard LLVM optimization levels (`-O1`, `-O2`, `-O3`) across various C programs. The agent was restricted to a maximum pipeline length of 10 passes and typically utilized 2 to 4 unique passes per program. 

*Note: Positive percentage values indicate the RL agent achieved a smaller binary size than the baseline.*

| Benchmark | RL vs `-O2` (%) | RL vs `-O3` (%) | Correctness | Security Violations | Unique Passes Used |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`slow.c`** | **+41.25%** | **+41.91%** | PASS | 10 | 3 |
| **`crud.c`** | **+28.26%** | **+36.28%** | PASS | 20 | 4 |
| **`fibonacci.c`** | +1.34% | +1.34% | PASS | 5 | 3 |
| **`search.c`** | -7.30% | -7.30% | PASS | 5 | 2 |
| **`sort.c`** | -13.97% | -13.97% | PASS | 10 | 3 |
| **`matrix_mul.c`**| -19.72% | -19.72% | PASS | 15 | 4 |

**Highlights:** The agent successfully avoided aggressive, code-inflating optimizations (such as extensive loop unrolling) on complex control-flow programs like `slow.c` and `crud.c`, drastically outperforming `-O2` and `-O3` in code size reduction. For programs like `matrix_mul.c`, the agent actively explored trade-offs, demonstrating a dynamic, non-static approach to compilation.

---

## Project Architecture

```text
RL-Optimizer/
├── app.py                   # Main application entry point / runner
├── train.py                 # PPO agent training loop
├── evaluate.py              # Benchmarking and model evaluation script
├── test_agent.py            # Sandbox for testing specific agent policies
├── llvm_env.py              # Custom Gymnasium environment wrapping LLVM
├── llvm_utils.py            # Subprocess handlers for Clang and LLVM 'opt'
├── feature_extractor.py     # Parses LLVM IR into tensor states
├── security_analyzer.py     # Static analysis constraints for the reward function
├── visualize_results.py     # Generates plots from benchmarking CSV data
├── benchmarks/              # C source files (crud.c, matrix_mul.c, sort.c, etc.)
├── models/                  # Saved Stable-Baselines3 PPO checkpoints
└── logs/                    # TensorBoard event logs for training metrics
```

---

## Getting Started

### Prerequisites
*   Python 3.8+
*   LLVM / Clang toolchain installed and accessible in the system PATH.
*   Required Python packages (see `Requirements.txt`).

### Installation
1. Clone the repository.
2. Install the required dependencies:
   ```bash
   pip install -r Requirements.txt
   ```

### Usage
**Training the Agent**
To start training the PPO agent from scratch using the benchmark files:
```bash
python train.py
```
Training progress can be monitored using TensorBoard:
```bash
tensorboard --logdir=logs/
```

**Evaluating Checkpoints**
To evaluate a trained model against standard `-O1`, `-O2`, and `-O3` flags and generate the `benchmark_results.csv`:
```bash
python evaluate.py
```

**Visualizing Data**
To graph the performance metrics of the agent against the baseline compilers:
```bash
python visualize_results.py
```
