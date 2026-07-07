import os
import subprocess
import pandas as pd

from stable_baselines3 import PPO
from llvm_env import LLVMEnv
from llvm_utils import compile_to_bc, bc_to_binary, get_binary_size

benchmarks = [
    "benchmarks/fibonacci.c",
    "benchmarks/matrix_mul.c",
    "benchmarks/sort.c",
    "benchmarks/search.c",
    "benchmarks/slow.c",
    "benchmarks/crud.c",
]

model = PPO.load("rl_optimizer")

results = []

pipeline_lengths = []

from collections import Counter

pass_counter = Counter()

for program in benchmarks:

    name = os.path.basename(program)

    print("Evaluating:", name)

    # ---------- O1 ----------
    subprocess.run(["clang", "-O1", program, "-o", "o1"])
    o1_size = get_binary_size("o1")

    # ---------- O2 ----------
    subprocess.run(["clang", "-O2", program, "-o", "o2"])
    o2_size = get_binary_size("o2")

    # ---------- O3 ----------
    subprocess.run(["clang", "-O3", program, "-o", "o3"])
    o3_size = get_binary_size("o3")

    # ---------- RL ----------
    env = LLVMEnv()
    env.program = program

    compile_to_bc(program, "current.bc")

    obs, _ = env.reset()

    for _ in range(10):

        action, _ = model.predict(obs)

        obs, reward, done, _, _ = env.step(action)

        if done:
            break

    pass_counter.update(env.pipeline)
    pipeline_lengths.append(len(env.pipeline))

    bc_to_binary("current.bc", "rl_binary")

    rl_size = get_binary_size("rl_binary")

    results.append({
        "Program": name,
        "O1": o1_size,
        "O2": o2_size,
        "O3": o3_size,
        "RL": rl_size
    })

print(pass_counter)

df = pd.DataFrame(results)

print("\nBenchmark Results")
print(df)

df.to_csv("benchmark_results.csv", index=False)