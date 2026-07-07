import gymnasium as gym
import numpy as np
import random
import os

from llvm_utils import (
    compile_to_bc,
    bc_to_ir,
    apply_pass,
    bc_to_binary,
    get_binary_size,
    run_binary,
    measure_execution_time_ns,
    strip_timing_output,
)
from feature_extractor import extract_features
from security_analyzer import analyze_security

class LLVMEnv(gym.Env):

    def __init__(self):

        super().__init__()

        self.passes = [
            "mem2reg",
            "instcombine",
            "simplifycfg",
            "gvn",
            "reassociate",
            "dce",
            "adce",
            "loop-simplify",
            "licm",
            "loop-unroll",
            "loop-rotate",
            "jump-threading",
            "sccp",
            "sroa",
            "inline",
            "STOP"
        ]

        self.action_space = gym.spaces.Discrete(len(self.passes))

        self.observation_space = gym.spaces.Box(
            low=0,
            high=10000,
            shape=(56,),
            dtype=np.float32
        )

        self.benchmarks = [
            "benchmarks/fibonacci.c",
            "benchmarks/matrix_mul.c",
            "benchmarks/sort.c",
            "benchmarks/search.c",
            "benchmarks/slow.c",
            "benchmarks/crud.c",
        ]

        self.max_steps = 15


    def set_program(self, program):
        self.program = program

    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        self.pipeline = []

        self.steps = 0

        if not hasattr(self,"program"):
            self.program = random.choice(self.benchmarks)

        compile_to_bc(self.program, "current.bc")

        bc_to_binary("current.bc", "starting_binary")
        self.initial_size = get_binary_size("starting_binary")

        # Baseline (-O0) reference output/time. Used later to (a) catch any
        # pass sequence that crashes the program or changes its behavior -
        # including the case where the "unused" computation just got
        # dead-code-eliminated - and (b) turn real speedups into reward
        # instead of measuring OS/process-fork overhead.
        baseline_stdout, baseline_returncode, baseline_timed_out = run_binary("starting_binary")

        if baseline_timed_out or baseline_returncode != 0:
            self.reference_output = None
            self.baseline_time_ns = None
        else:
            self.reference_output = strip_timing_output(baseline_stdout)
            self.baseline_time_ns = measure_execution_time_ns("starting_binary")

        ir = bc_to_ir("current.bc")

        self.state, self.feature_dict = extract_features(ir)

        return np.array(self.state, dtype=np.float32), {}


    def _check_correctness_and_speed(self, binary):
        """
        Runs `binary` and returns (broke_program, speed_reward).

        broke_program is True if the binary crashed, hung, or its output no
        longer matches the unoptimized baseline. This is what catches a pass
        sequence that deletes (or otherwise breaks) the program instead of
        legitimately speeding it up - e.g. an aggressive DCE pass wiping out
        a computation whose result the RL agent never sees printed. Without
        this check, a deleted program would look like a free win: 0 bytes,
        0 seconds, no penalty.

        speed_reward is a clipped, baseline-relative measure of the real
        execution-time improvement, taken from the time the benchmark
        measured internally via clock_gettime() (see benchmarks/*.c),
        never from timing the subprocess call itself.
        """

        stdout, returncode, timed_out = run_binary(binary)

        if timed_out or returncode != 0:
            return True, 0.0

        if self.reference_output is not None:
            if strip_timing_output(stdout) != self.reference_output:
                return True, 0.0

        speed_reward = 0.0

        if self.baseline_time_ns:
            exec_time_ns = measure_execution_time_ns(binary)

            if exec_time_ns is not None:
                speed_reward = (self.baseline_time_ns - exec_time_ns) / self.baseline_time_ns
                speed_reward = max(-2.0, min(speed_reward, 2.0))

        return False, speed_reward

    def step(self, action):

        self.steps += 1

        pass_name = self.passes[action]

        self.pipeline.append(pass_name)

        if pass_name == "STOP":

            bc_to_binary("current.bc", "final_binary")
            final_size = get_binary_size("final_binary")

            broke_program, speed_reward = self._check_correctness_and_speed("final_binary")

            if broke_program:
                # The chosen pipeline produced a binary that crashes, hangs,
                # or no longer matches the baseline's output - most likely
                # because a DCE-style pass deleted the "unused" computation
                # entirely. A 0-byte / 0ms program is not a real win, so we
                # penalize it instead of letting it look like -O2-beating
                # performance.
                reward = -10
                done = True

                info = {
                    "security_penalty": 0,
                    "broke_program": True
                }

                return (
                    np.array(self.state, dtype=np.float32),
                    reward,
                    done,
                    False,
                    info
                )

            improvement = self.initial_size - final_size

            final_ir = bc_to_ir("current.bc")

            security_penalty = analyze_security(
                self.feature_dict,
                self.feature_dict,
                final_ir
            )

            reward = (
                (improvement / self.initial_size) * 10 +
                speed_reward * 5
                - security_penalty
            )

            done = True

            info = {
                "security_penalty": security_penalty,
                "speed_reward": speed_reward,
                "broke_program": False
            }

            return (
                np.array(self.state, dtype=np.float32),
                reward,
                done,
                False,
                info
            )

        success = apply_pass("current.bc", pass_name, "next.bc")
        
        # If pass failed, give penalty and end episode
        if not success:
            reward = -5
            done = True

            return (
                np.array(self.state, dtype=np.float32),
                reward,
                done,
                False,
                {}
            )

        os.replace("next.bc", "current.bc")

        bc_to_binary("current.bc", "end_binary")
        new_size = get_binary_size("end_binary")

        broke_program, speed_reward = self._check_correctness_and_speed("end_binary")

        if broke_program:
            # Same DCE/correctness guard as the STOP branch: don't reward a
            # pipeline for making the program disappear or misbehave.
            reward = -10
            done = True

            return (
                np.array(self.state, dtype=np.float32),
                reward,
                done,
                False,
                {"security_penalty": 0, "broke_program": True}
            )

        size_reduction = self.initial_size - new_size

        size_reward = size_reduction / self.initial_size

        old_features = self.state

        ir = bc_to_ir("current.bc")

        new_features, new_feature_dict = extract_features(ir)

        instr_reduction = (
            (old_features[0] - new_features[0]) +
            (old_features[6] - new_features[6]) +
            (old_features[7] - new_features[7]) +
            (old_features[11] - new_features[11])
        )

        security_penalty = analyze_security(
            self.feature_dict,
            new_feature_dict,
            ir
        )

        if security_penalty > 0:
            print("Security penalty:", security_penalty)

        reward = (
            0.5 * instr_reduction +
            0.2 * size_reward +
            0.3 * speed_reward -
            1.0 * security_penalty
        )

        self.state = new_features
        self.feature_dict = new_feature_dict

        done = self.steps >= self.max_steps

        if not success:
            # failed optimization pass
            reward = -5
            done = True
            return (
                np.array(self.state, dtype=np.float32),
                reward,
                done,
                False,
                {}
            )
        
        info = {
            "security_penalty": security_penalty,
            "speed_reward": speed_reward,
            "broke_program": False
        }

        return np.array(self.state, dtype=np.float32), reward, done, False, info