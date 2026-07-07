import pandas as pd
import matplotlib.pyplot as plt
from evaluate import pass_counter, pipeline_lengths

df = pd.read_csv("benchmark_results.csv")

df.set_index("Program").plot(kind="bar")

plt.title("Binary Size Comparison")
plt.ylabel("Binary Size (bytes)")
plt.xlabel("Program")

plt.show()

import pandas as pd
import matplotlib.pyplot as plt

data = pd.read_csv("logs/progress.csv")

plt.plot(data["time/total_timesteps"], data["rollout/ep_rew_mean"])

plt.xlabel("Training Steps")
plt.ylabel("Average Reward")
plt.title("RL Training Curve")

plt.show()

import matplotlib.pyplot as plt

passes = list(pass_counter.keys())
counts = list(pass_counter.values())

plt.bar(passes, counts)

plt.xticks(rotation=45)
plt.title("Optimization Pass Frequency")

plt.ylabel("Usage Count")

plt.show()

plt.bar(df["Program"], pipeline_lengths)

plt.title("RL Optimization Pipeline Length")

plt.ylabel("Number of Passes")

plt.show()