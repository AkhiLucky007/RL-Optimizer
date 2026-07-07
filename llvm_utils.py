import os
import re
import subprocess

# Benchmarks print their self-measured execution time as a line like:
#   EXEC_TIME_NS: 123456
# See benchmarks/*.c for the clock_gettime() instrumentation that produces it.
_TIMING_MARKER = re.compile(r"EXEC_TIME_NS:\s*(\d+)")


def bc_to_binary(bc_file, output_binary):

    subprocess.run(
        [
            "clang",
            bc_file,
            "-O0",
            "-o",
            output_binary
        ],
        check=True
    )


def get_binary_size(binary):
    """
    Returns the size (in bytes) of the compiled machine code, i.e. the
    ELF `.text` section - NOT the size of the file on disk.

    os.path.getsize() measures the whole file, which is dominated by fixed
    ELF headers and statically-linked CRT boilerplate. Those are constant
    overhead of a few KB regardless of what the optimizer does, so shrinking
    the actual instructions of a tiny benchmark by even 50 IR instructions
    barely moves the on-disk size. The `.text` section is where the compiled
    instructions actually live, so it's the part that reflects what the
    optimization pipeline changed.
    """

    try:
        result = subprocess.run(
            ["size", binary],
            capture_output=True,
            text=True,
            check=True
        )

        # `size` output looks like:
        #    text    data     bss     dec     hex filename
        #    1600     584       8    2192     890 /tmp/t
        lines = result.stdout.strip().splitlines()
        text_size = int(lines[1].split()[0])
        return text_size

    except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
        # Fall back to whole-file size if `size`/`llvm-size` isn't available.
        return os.path.getsize(binary)


def run_binary(binary, timeout=5):
    """
    Runs a compiled benchmark binary and returns (stdout, returncode, timed_out).

    This never raises. Callers use returncode/timed_out to detect a crashed,
    hung, or otherwise broken binary - which includes the case where an
    optimization pass (or dead-code elimination) silently deleted the
    program's actual work.
    """

    path = binary if binary.startswith(("./", "/")) else os.path.join(".", binary)

    try:
        result = subprocess.run(
            [path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.returncode, False

    except subprocess.TimeoutExpired:
        return "", None, True

    except OSError:
        return "", None, False


def measure_execution_time_ns(binary, timeout=5):
    """
    Runs `binary` and extracts the execution time (in nanoseconds) that the
    C program itself measured with clock_gettime() around its target loop,
    and printed as `EXEC_TIME_NS: <n>`.

    We deliberately do NOT time this from Python by wrapping subprocess.run()
    in time.time(). Forking a new process and letting the OS load/link it
    costs roughly 2-10ms on its own, which completely swamps benchmarks that
    themselves run in microseconds - -O0, -O2, and a single "sroa" pass would
    all measure as "~10ms" even though the actual compiled code executes in
    wildly different amounts of time. Measuring inside the C program and
    parsing its printed result sidesteps the OS/process overhead entirely.

    Returns None if the binary crashed, timed out, or didn't print a
    parsable timing line (e.g. because the computation got deleted).
    """

    stdout, returncode, timed_out = run_binary(binary, timeout=timeout)

    if timed_out or returncode != 0:
        return None

    match = _TIMING_MARKER.search(stdout)

    if not match:
        return None

    return float(match.group(1))


def strip_timing_output(stdout):
    """
    Removes the `EXEC_TIME_NS: ...` line so the remaining text can be
    compared against a reference/baseline run for correctness, without the
    timing benchmark itself (which naturally varies run to run) causing a
    false mismatch.
    """

    return _TIMING_MARKER.sub("", stdout).strip()


def compile_to_bc(c_file, bc_file):

    subprocess.run(
        [
            "clang",
            "-O0",
            "-Xclang",
            "-disable-O0-optnone",
            "-emit-llvm",
            "-c",
            c_file,
            "-o",
            bc_file
        ],
        check=True
    )

    _strip_noinline(bc_file)


def _strip_noinline(bc_file):
    """
    Clang's -O0 pipeline tags every function `noinline`, and
    `-Xclang -disable-O0-optnone` only removes the `optnone` attribute, not
    `noinline`. Left in place, the RL agent's "inline" action is a no-op on
    every single benchmark, regardless of which pass sequence it picks -
    `opt` will refuse to inline a function explicitly marked noinline.

    We still want -O0-style unoptimized starting IR (no mem2reg, no
    constant folding, etc.) so the agent has real work to do - we just don't
    want the one attribute that silently disables one of its 16 actions.
    This strips only the `noinline` keyword from the IR's attribute groups
    and reassembles it, leaving everything else untouched.
    """

    ir = subprocess.run(
        ["llvm-dis", bc_file, "-o", "-"],
        capture_output=True,
        text=True,
        check=True
    ).stdout

    cleaned_ir = re.sub(r"\bnoinline\b\s*", "", ir)

    subprocess.run(
        ["llvm-as", "-o", bc_file],
        input=cleaned_ir,
        text=True,
        check=True
    )


def bc_to_ir(bc_file):

    result = subprocess.run(
        ["llvm-dis", bc_file, "-o", "-"],
        capture_output=True,
        text=True
    )

    return result.stdout

# Most of the RL agent's passes are ordinary function passes and fit the
# `function(name)` template, but a few need a different pipeline shape in
# LLVM's new pass manager:
#   - "licm" only runs inside a loop pass manager with MemorySSA available.
#   - "inline" is a CGSCC-level transform, not a function pass; "inline" by
#     itself in the new PM refers to the mandatory-only inliner, which does
#     nothing for ordinary calls. `module-inline` does real inlining.
_PASS_PIPELINES = {
    "licm": "function(loop-mssa(licm))",
    "inline": "module-inline",
    # LLVM 18's new-PM instcombine defaults to max-iterations=1 and treats
    # not converging as a fatal error (process abort, not just a returncode)
    # rather than a clean failure. Anything past a handful of instructions -
    # crud.c is the one benchmark here that trips it - can need more than
    # one pass to reach a fixpoint, so give it real headroom.
    "instcombine": "function(instcombine<max-iterations=4>)",
}


def _pipeline_for(pass_name):
    return _PASS_PIPELINES.get(pass_name, f"function({pass_name})")


def apply_pass(bc_file, pass_name, output_bc):

    try:

        result = subprocess.run(
            [
                "opt",
                f"-passes={_pipeline_for(pass_name)}",
                bc_file,
                "-o",
                output_bc
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False

        return True

    except Exception:
        return False