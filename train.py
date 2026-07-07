from stable_baselines3 import PPO
from llvm_env import LLVMEnv

from stable_baselines3.common.callbacks import CheckpointCallback

from stable_baselines3.common.logger import configure

import torch
import random
import numpy as np

seed = 42

random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

env = LLVMEnv()

checkpoint_callback = CheckpointCallback(
    save_freq=1000,
    save_path="./models/",
    name_prefix="rl_model"
)

new_logger = configure("./logs/", ["stdout", "csv", "tensorboard"])

model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    learning_rate=0.0003,
    n_steps=256,
    batch_size=64,
    gamma=0.99
)

model.set_logger(new_logger)

model.learn(
    total_timesteps=30000,
    callback=checkpoint_callback
)

model.save("rl_optimizer")

print("Training complete.")