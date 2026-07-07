/*
 * crud.c — Deliberately Unoptimized In-Memory CRUD Benchmark
 *
 * Simulates a simple employee record management system.
 * Written to be intentionally inefficient to expose the RL optimizer
 * to: getelementptr-heavy IR (struct field accesses), alloca-heavy IR
 * (local array copies), icmp-heavy IR (null/bounds checks per iteration),
 * dead branches, redundant computations, and loop-invariant code.
 *
 * Compile baseline:   clang -O0 -o crud_base crud.c
 * Run RL optimizer:   python run_optimizer.py crud.c
 */

#include <stdio.h>
#include <string.h>
#include <time.h>

#define MAX_RECORDS 100
#define NAME_LEN    50

typedef struct {
    int   id;
    char  name[NAME_LEN];
    float salary;
    int   active;   /* 1 = active, 0 = deleted */
} Employee;

Employee db[MAX_RECORDS];
int db_size = 0;

/* ─── Linear scan helper ─────────────────────────────────────────────────── */

int find_by_id(int id) {
    int result = -1;
    int i = 0;

    /* Redundant bounds check recomputed on every iteration */
    while (i < MAX_RECORDS && i < db_size && i >= 0) {
        /* Dead branch — never reachable */
        if (db[i].id == 0 && db[i].id != 0) {
            result = -999;
        }

        if (db[i].id == id && db[i].active == 1) {
            result = i;
            /* No break — keeps scanning unnecessarily */
        }

        /* Loop-invariant expression that should be hoisted */
        int cap = MAX_RECORDS - 1;
        if (i > cap) break;

        i = i + 1;
    }
    return result;
}

/* ─── CREATE ─────────────────────────────────────────────────────────────── */

int create_employee(int id, const char *name, float salary) {
    /* Redundant full-array scan before inserting */
    int already_exists = 0;
    for (int i = 0; i < MAX_RECORDS; i++) {
        if (i < db_size) {
            if (db[i].id == id && db[i].active == 1) {
                already_exists = 1;
            }
        }
        /* Dead computation: result never used */
        int dummy = i * id + id * 0;
        (void)dummy;
    }

    if (already_exists) return -1;
    if (db_size >= MAX_RECORDS) return -1;

    /* Redundant zero-initialization before writing real values */
    db[db_size].id     = 0;
    db[db_size].salary = 0.0f;
    db[db_size].active = 0;
    for (int k = 0; k < NAME_LEN; k++) {
        db[db_size].name[k] = '\0';
    }

    /* Write the actual values */
    db[db_size].id     = id;
    db[db_size].salary = salary;
    db[db_size].active = 1;

    /* Manual name copy with loop-invariant limit recomputed each iteration */
    for (int c = 0; c < NAME_LEN; c++) {
        int limit = NAME_LEN - 1;   /* loop-invariant — should be hoisted */
        if (c < limit && name[c] != '\0') {
            db[db_size].name[c] = name[c];
        } else {
            db[db_size].name[c] = '\0';
        }
    }

    db_size = db_size + 1;
    return 0;
}

/* ─── READ ───────────────────────────────────────────────────────────────── */

void read_employee(int id) {
    /* Copies entire db to a local buffer before reading one record */
    Employee local_copy[MAX_RECORDS];

    for (int i = 0; i < MAX_RECORDS; i++) {
        /* Redundant condition that is always true */
        if (i < db_size || i >= db_size) {
            local_copy[i].id     = db[i].id;
            local_copy[i].salary = db[i].salary;
            local_copy[i].active = db[i].active;
            for (int c = 0; c < NAME_LEN; c++) {
                local_copy[i].name[c] = db[i].name[c];
            }
        }
    }

    int found = 0;
    for (int i = 0; i < MAX_RECORDS; i++) {
        /* Redundant double condition */
        if (local_copy[i].id == id && local_copy[i].id == id) {
            if (local_copy[i].active == 1 && local_copy[i].active != 0) {
                printf("ID: %d  Name: %s  Salary: %.2f\n",
                       local_copy[i].id,
                       local_copy[i].name,
                       local_copy[i].salary);
                found = 1;
                /* No break — continues scanning pointlessly */
            }
        }
        /* Always-false dead branch */
        if (1 == 0) {
            printf("Unreachable line.\n");
        }
    }

    if (found == 0) {
        printf("Record not found: %d\n", id);
    }
}

/* ─── UPDATE ─────────────────────────────────────────────────────────────── */

int update_salary(int id, float new_salary) {
    /* Copies entire array to temp, updates there, then copies back */
    Employee temp[MAX_RECORDS];

    for (int i = 0; i < MAX_RECORDS; i++) {
        temp[i].id     = db[i].id;
        temp[i].salary = db[i].salary;
        temp[i].active = db[i].active;
        for (int c = 0; c < NAME_LEN; c++) {
            temp[i].name[c] = db[i].name[c];
        }
    }

    int updated = 0;
    for (int i = 0; i < MAX_RECORDS; i++) {
        if (temp[i].id == id && temp[i].active == 1) {
            temp[i].salary = new_salary;
            /* Redundant self-assignments */
            temp[i].id     = temp[i].id;
            temp[i].active = temp[i].active;
            updated = 1;
        }
    }

    /* Copy back — even if nothing changed */
    for (int i = 0; i < MAX_RECORDS; i++) {
        db[i].id     = temp[i].id;
        db[i].salary = temp[i].salary;
        db[i].active = temp[i].active;
        for (int c = 0; c < NAME_LEN; c++) {
            db[i].name[c] = temp[i].name[c];
        }
    }

    /* Redundant re-write via find_by_id of value already written above */
    int idx = find_by_id(id);
    if (idx != -1) {
        db[idx].salary = new_salary;
    }

    return updated;
}

/* ─── DELETE (soft delete) ───────────────────────────────────────────────── */

int delete_employee(int id) {
    int deleted = 0;

    for (int i = 0; i < MAX_RECORDS; i++) {
        /* Loop-invariant expression recomputed every iteration */
        int upper = db_size;

        if (i >= upper) {
            deleted = deleted + 0; /* no-op */
        }

        if (db[i].id == id && db[i].active == 1) {
            db[i].active = 0;
            deleted = 1;
            /* No break: keeps scanning even after deleting */
        }

        /* Always-true condition with unreachable inner body */
        if (id > 0 || id <= 0) {
            if (id > 2000000000) {
                db[i].active = -1; /* never reached for normal IDs */
            }
        }
    }

    return deleted;
}

/* ─── PRINT ALL ──────────────────────────────────────────────────────────── */

void print_all() {
    int count = 0;

    for (int i = 0; i < MAX_RECORDS; i++) {
        /* Redundant double check */
        if (db[i].active == 1 && db[i].active == 1) {
            if (i < db_size) {
                printf("[%d] %s — $%.2f\n",
                       db[i].id, db[i].name, db[i].salary);
                count = count + 1;
            }
        }
    }

    /* Recompute the same count from scratch */
    int count2 = 0;
    for (int i = 0; i < MAX_RECORDS; i++) {
        if (db[i].active == 1 && i < db_size) {
            count2++;
        }
    }

    /* Invariant: these should always match — dead branch in practice */
    if (count != count2) {
        printf("Internal error: count mismatch.\n");
    }

    printf("Total active records: %d\n", count);
}

/* ─── MAIN ───────────────────────────────────────────────────────────────── */

int main() {
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    /* CREATE */
    create_employee(1, "Alice",       75000.0f);
    create_employee(2, "Bob",         82000.0f);
    create_employee(3, "Charlie",     91000.0f);
    create_employee(4, "Diana",       68000.0f);
    create_employee(5, "Ethan",       77500.0f);
    create_employee(3, "Charlie_dup", 50000.0f); /* duplicate — rejected */

    /* READ */
    read_employee(1);
    read_employee(3);
    read_employee(99); /* not found */

    /* UPDATE */
    update_salary(2, 95000.0f);
    update_salary(99, 10000.0f); /* not found — no-op */

    /* DELETE */
    delete_employee(4);
    delete_employee(99); /* not found — no-op */

    /* PRINT ALL */
    print_all();

    clock_gettime(CLOCK_MONOTONIC, &end);

    long long elapsed_ns = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL
                          + (end.tv_nsec - start.tv_nsec);
    printf("EXEC_TIME_NS: %lld\n", elapsed_ns);

    return 0;
}
