def analyze_security(old_features, new_features, ir):

    penalty = 0

    # -------------------------
    # Constraint 1: Dangerous functions
    # -------------------------

    dangerous_functions = [
        "gets(",
        "strcpy(",
        "sprintf(",
        'scanf("%s"'
    ]

    for func in dangerous_functions:
        if func in ir:
            penalty += 25


    # -------------------------
    # Constraint 2: Pointer arithmetic explosion
    # -------------------------

    old_gep = old_features.get("getelementptr", 0)
    new_gep = new_features.get("getelementptr", 0)

    if new_gep > old_gep * 1.5:
        penalty += 10


    # -------------------------
    # Constraint 3: Safety branch removal
    # -------------------------

    old_icmp = old_features.get("icmp", 0)
    new_icmp = new_features.get("icmp", 0)

    old_br = old_features.get("br", 0)
    new_br = new_features.get("br", 0)

    if new_icmp < old_icmp:
        penalty += 5

    if new_br < old_br:
        penalty += 5


    # -------------------------
    # Constraint 4: Stack allocation explosion
    # -------------------------

    old_alloca = old_features.get("alloca", 0)
    new_alloca = new_features.get("alloca", 0)

    if new_alloca > old_alloca * 1.3:
        penalty += 10

    # -------------------------
    # Constraint 5: Funciton call explosion
    # -------------------------
    old_calls = old_features.get("call", 0)
    new_calls = new_features.get("call", 0)

    if new_calls > old_calls * 1.4:
        penalty += 10


    return penalty