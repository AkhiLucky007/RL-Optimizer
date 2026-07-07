import re

def extract_features(ir):

    features = {}

    instructions = re.findall(r"^\s*[a-zA-Z]", ir, re.MULTILINE)
    features["instruction_count"] = len(instructions)

    opcodes = [
        "add","sub","mul","udiv","sdiv",
        "load","store","alloca",
        "call","ret","br",
        "icmp","fcmp",
        "phi","select",
        "shl","lshr","ashr",
        "and","or","xor",
        "getelementptr",
        "bitcast","trunc","zext","sext",
        "fadd","fsub","fmul","fdiv",
        "switch","invoke","resume",
        "unreachable"
    ]

    for op in opcodes:
        features[op] = len(re.findall(r"\b"+op+r"\b", ir))

    features["basic_blocks"] = ir.count(":")
    features["functions"] = ir.count("define")

    vec = list(features.values())

    if len(vec) < 56:
        vec += [0]*(56-len(vec))

    return vec[:56], features