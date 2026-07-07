import os

from stable_baselines3 import PPO
from llvm_env import LLVMEnv

from llvm_utils import get_binary_size, bc_to_binary
import subprocess

env = LLVMEnv()

total_reward = 0

obs, _ = env.reset()

model = PPO.load("rl_optimizer")

# baseline using -O2
subprocess.run(["clang", "-O2", env.program, "-o", "baseline"])

baseline_size = get_binary_size("baseline")

print("Baseline (-O2) binary size:", baseline_size)

for step in range(10):

    action, _ = model.predict(obs)

    obs, reward, done, _, _ = env.step(action)

    total_reward += reward

    print("Step:", step)
    print("Action:", action)
    print("Reward:", reward)
    print()

    if done:
        break

print("Total reward:", total_reward)

print("\nChosen Optimization Pipeline:")
print(" -> ".join(env.pipeline))

bc_to_binary("current.bc", "rl_binary")
rl_size = get_binary_size("rl_binary")
#rl_size = get_binary_size("current.bc")

print("RL optimized binary size:", rl_size)

improvement = ((baseline_size - rl_size) / baseline_size) * 100

print("Size improvement vs O2:", improvement, "%")