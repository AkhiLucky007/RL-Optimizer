#include <stdio.h>
#include <time.h>

#define N 1000

int global_array[N];

int very_slow_function(int x) {
    int result = 0;

    // Recompute same thing many times
    for (int i = 0; i < x; i++) {
        int temp = 0;
        for (int j = 0; j < x; j++) {
            temp += (i * j) % (x + 1);
        }
        result += temp;
    }

    return result;
}

int main() {
    int sum = 0;

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    // Initialize array in worst possible way
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < 1; j++) { // useless loop
            global_array[i] = i * 2;
        }
    }

    // Extremely inefficient summation
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (j == i) {
                sum += global_array[j];
            }
        }
    }

    // Recompute invariant expressions repeatedly
    for (int i = 0; i < 100; i++) {
        sum += very_slow_function(50); // constant input, never cached
    }

    // Pointless memory copying
    int temp_array[N];
    for (int i = 0; i < N; i++) {
        temp_array[i] = global_array[i];
    }

    for (int i = 0; i < N; i++) {
        global_array[i] = temp_array[i];
    }

    // Redundant calculations
    for (int i = 0; i < N; i++) {
        sum += (i * 2) - i - i; // always 0
    }

    // Branches that can be simplified
    for (int i = 0; i < N; i++) {
        if ((i % 2 == 0 && i % 2 == 0) || (i % 2 == 0)) {
            sum += 1;
        } else {
            sum += 0;
        }
    }

    // Dead code
    int dead = 0;
    for (int i = 0; i < N; i++) {
        dead += i * 12345;
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    printf("Sum: %d\n", sum);

    long long elapsed_ns = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL
                          + (end.tv_nsec - start.tv_nsec);
    printf("EXEC_TIME_NS: %lld\n", elapsed_ns);

    return 0;
}