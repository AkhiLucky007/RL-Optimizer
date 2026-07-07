import matplotlib.pyplot as plt
import pandas as pd
import os


log_dir = "logs"

rewards = []
steps = []

for root, dirs, files in os.walk(log_dir):

    for file in files:

        if file.endswith(".csv"):

            path = os.path.join(root, file)

            data = pd.read_csv(path)

            if "rollout/ep_rew_mean" in data.columns:

                rewards = data["rollout/ep_rew_mean"]
                steps = data["time/total_timesteps"]


plt.figure()

plt.plot(steps, rewards)

plt.xlabel("Training Steps")
plt.ylabel("Average Reward")
plt.title("RL Compiler Optimization Learning Curve")

plt.show()