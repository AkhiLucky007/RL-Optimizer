import os
import subprocess
import sys
from stable_baselines3 import PPO

from llvm_env import LLVMEnv
from llvm_utils import bc_to_binary, get_binary_size


MODEL_PATH = "rl_optimizer"


def compile_baseline(program):

    subprocess.run(
        ["clang", "-O2", program, "-o", "baseline"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return get_binary_size("baseline")


def run_rl_optimizer(program):

    env = LLVMEnv()
    env.set_program(program)

    obs, _ = env.reset()

    model = PPO.load(MODEL_PATH)

    total_security_penalty = 0

    for step in range(env.max_steps):

        action, _ = model.predict(obs, deterministic=False)

        obs, reward, done, _, info = env.step(action)

        if "security_penalty" in info:
            total_security_penalty += info["security_penalty"]

        if done:
            break

    bc_to_binary("current.bc", "rl_binary")

    rl_size = get_binary_size("rl_binary")

    return rl_size, env.pipeline, total_security_penalty


def evaluate(program):

    print("\nEvaluating:", program)

    baseline_size = compile_baseline(program)

    print("Baseline (-O2) size:", baseline_size, "bytes")

    rl_size, pipeline, security = run_rl_optimizer(program)

    print("RL optimized size:", rl_size, "bytes")

    improvement = (
        (baseline_size - rl_size) /
        baseline_size
    ) * 100

    print("\nImprovement vs O2:", round(improvement, 2), "%")

    print("\nPipeline used:")

    print(" -> ".join(pipeline))

    print("\nSecurity penalty total:", security)


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("\nUsage:")

        print("python run_optimizer.py program.c")

        sys.exit()

    program = sys.argv[1]

    evaluate(program)