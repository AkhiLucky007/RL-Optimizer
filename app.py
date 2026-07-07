import streamlit as st # type: ignore
import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

from streamlit_ace import st_ace # type: ignore

from stable_baselines3 import PPO
from llvm_env import LLVMEnv
from llvm_utils import (
    compile_to_bc,
    bc_to_binary,
    get_binary_size,
    run_binary,
    measure_execution_time_ns,
)

# ----------------------------
# PAGE CONFIG
# ----------------------------

st.set_page_config(
    page_title="RL Compiler Optimizer",
    layout="wide"
)

st.markdown("""
<style>

.big-title {
    font-size:40px;
    font-weight:700;
}

.section {
    background-color:#f5f5f5;
    padding:20px;
    border-radius:10px;
    margin-bottom:20px;
}

</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">RL Compiler Optimization Dashboard</p>', unsafe_allow_html=True)


# ----------------------------
# BENCHMARK LIST
# ----------------------------

benchmarks = [
    "benchmarks/fibonacci.c",
    "benchmarks/matrix_mul.c",
    "benchmarks/sort.c",
    "benchmarks/search.c",
    "benchmarks/slow.c",
    "benchmarks/crud.c",
]


# ----------------------------
# LOAD RL MODEL
# ----------------------------

@st.cache_resource
def load_model():
    return PPO.load("rl_optimizer")

model = load_model()

#model = PPO.load("rl_optimizer")


# ----------------------------
# INPUT MODE
# ----------------------------

st.subheader("Input Source")

input_mode = st.radio(
    "Choose Input Mode",
    ["Upload C File", "Type Code", "Run Default Benchmarks"]
)

programs = []


# ----------------------------
# FILE UPLOAD
# ----------------------------

if input_mode == "Upload C File":

    uploaded_file = st.file_uploader("Upload .c file", type=["c"])

    if uploaded_file:

        with open("input.c", "wb") as f:
            f.write(uploaded_file.read())

        programs = ["input.c"]


# ----------------------------
# CODE EDITOR
# ----------------------------

elif input_mode == "Type Code":

    code = st_ace(
        language="c_cpp",
        theme="monokai",
        height=300
    )

    if code:

        with open("input.c", "w") as f:
            f.write(code)

        programs = ["input.c"]


# ----------------------------
# DEFAULT BENCHMARKS
# ----------------------------

elif input_mode == "Run Default Benchmarks":

    programs = benchmarks


# ----------------------------
# RUN BUTTON
# ----------------------------

run_eval = st.button("Run Optimization")


# ----------------------------
# EVALUATION FUNCTION
# ----------------------------

def run_evaluation(program_list):

    results = []
    pass_counter = Counter()
    pipelines = {}
    pipeline_lengths = {}
    security_totals = {}

    for program in program_list:

        name = os.path.basename(program)

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

        security_total = 0

        for _ in range(10):

            action, _ = model.predict(obs)

            obs, reward, done, _, info = env.step(action)

            # accumulate security penalties
            if "security_penalty" in info:
                security_total += info["security_penalty"]

            if done:
                break

        bc_to_binary("current.bc", "rl_binary")

        rl_size = get_binary_size("rl_binary")

        try:
            _, returncode, timed_out = run_binary("rl_binary", timeout=5)
            if timed_out:
                correctness = "TIMEOUT"
            elif returncode != 0:
                correctness = "CRASH"
            else:
                correctness = "PASS"
        except Exception:
            correctness = "CRASH"

        # Runtime is read from the EXEC_TIME_NS line the benchmark itself
        # prints via clock_gettime() - not measured by wrapping
        # subprocess.run() in time.time(). Forking a new process costs a
        # few milliseconds on its own, which would swamp these
        # microsecond-scale benchmarks and make every optimization level
        # look identical.
        exec_time_ns = measure_execution_time_ns("rl_binary", timeout=5)
        runtime = round(exec_time_ns / 1e9, 9) if exec_time_ns is not None else None

        pipelines[name] = env.pipeline
        pass_counter.update(env.pipeline)

        pipeline_len = len(env.pipeline)
        pipeline_lengths[name] = pipeline_len

        security_totals[name] = security_total

        # ---------- Improvements ----------
        improvement_o2 = ((o2_size - rl_size) / o2_size) * 100
        improvement_o3 = ((o3_size - rl_size) / o3_size) * 100

        # ---------- Efficiency metric ----------
        if pipeline_len > 0:
            efficiency = improvement_o2 / pipeline_len
        else:
            efficiency = 0

        # ---------- Unique passes metric ----------
        unique_passes = len(set(env.pipeline))

        results.append({
            "Program": name,
            "O1": o1_size,
            "O2": o2_size,
            "O3": o3_size,
            "RL": rl_size,
            "RL vs O2 (%)": round(improvement_o2, 2),
            "RL vs O3 (%)": round(improvement_o3, 2),
            "Pipeline Length": pipeline_len,
            "Unique Passes": unique_passes,
            "Security Violations": security_total,
            "Efficiency Score": round(efficiency, 3),
            "Correctness": correctness,
            "Runtime (s)": runtime
        })

    df = pd.DataFrame(results)

    most_used_pass = None
    least_used_pass = None

    if pass_counter:
        most_used_pass = pass_counter.most_common(1)[0][0]
        least_used_pass = min(pass_counter, key=pass_counter.get)

    return {
        "table": df,
        "pass_freq": pass_counter,
        "pipelines": pipelines,
        "pipeline_lengths": pipeline_lengths,
        "security_totals": security_totals,
        "most_used_pass": most_used_pass,
        "least_used_pass": least_used_pass
    }


# ----------------------------
# RUN EVALUATION
# ----------------------------

if run_eval and programs:

    with st.spinner("Running Optimization..."):

        st.session_state["results"] = run_evaluation(programs)

    st.success("Evaluation Complete")


# ----------------------------
# VISUALIZATION OPTIONS
# ----------------------------

if "results" in st.session_state:

    st.subheader("Visualization Options")

    col1, col2 = st.columns(2)

    with col1:
        show_binary = st.checkbox("Binary Size Comparison")
        show_pass_seq = st.checkbox("Optimization Pass Sequence")
        show_pass_freq = st.checkbox("Pass Frequency")

    with col2:
        show_pipeline = st.checkbox("Pipeline Length")
        show_reward = st.checkbox("Training Reward Curve")

    results = st.session_state["results"]

    st.subheader("Explainability Insights")

    st.write("Most frequently used optimization pass:",
         results["most_used_pass"])

    st.write("Least frequently used optimization pass:",
         results["least_used_pass"])


    # ----------------------------
    # BINARY SIZE COMPARISON
    # ----------------------------

    if show_binary:

        st.subheader("Binary Size Comparison")

        df = results["table"]

        st.dataframe(df.style.highlight_max(axis=0))
        
        fig, ax = plt.subplots()

        df_plot = df.set_index("Program")[["O1","O2","O3","RL"]]

        df_plot.plot(kind="bar", ax=ax)

        ax.set_ylabel("Binary Size (bytes)")

        st.pyplot(fig)


    # ----------------------------
    # PASS SEQUENCE
    # ----------------------------

    if show_pass_seq:

        st.subheader("Optimization Pass Sequence")

        for prog, seq in results["pipelines"].items():

            st.write(f"**{prog}**")

            st.code(f"Length {len(seq)}: " + " → ".join(seq))


    # ----------------------------
    # PASS FREQUENCY
    # ----------------------------

    if show_pass_freq:

        st.subheader("Optimization Pass Frequency")

        freq = results["pass_freq"]

        fig, ax = plt.subplots()

        sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)

        passes, counts = zip(*sorted_items)

        ax.bar(passes, counts)

        plt.xticks(rotation=45)

        st.pyplot(fig)


    # ----------------------------
    # PIPELINE LENGTH
    # ----------------------------

    if show_pipeline:

        st.subheader("Pipeline Length")

        lengths = results["pipeline_lengths"]

        fig, ax = plt.subplots()

        ax.bar(lengths.keys(), lengths.values())

        ax.set_ylabel("Number of Passes")

        st.pyplot(fig)


    # ----------------------------
    # REWARD CURVE
    # ----------------------------

    if show_reward:

        st.subheader("Training Reward Curve")

        try:

            data = pd.read_csv("logs/progress.csv")

            fig, ax = plt.subplots()

            ax.plot(
                data["time/total_timesteps"],
                data["rollout/ep_rew_mean"]
            )

            st.write("Final average reward:",
                round(data["rollout/ep_rew_mean"].iloc[-1], 3))

            ax.set_xlabel("Training Steps")
            ax.set_ylabel("Average Reward")

            st.pyplot(fig)

        except:

            st.write("Training logs not found")