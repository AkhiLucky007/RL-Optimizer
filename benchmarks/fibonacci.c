#include <stdio.h>
#include <time.h>

int fib(int n){
    if(n<=1) return n;
    return fib(n-1)+fib(n-2);
}

int main(){

    struct timespec start, end;

    clock_gettime(CLOCK_MONOTONIC, &start);
    int result = fib(10);
    clock_gettime(CLOCK_MONOTONIC, &end);

    printf("%d",result);

    long long elapsed_ns = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL
                          + (end.tv_nsec - start.tv_nsec);
    printf("\nEXEC_TIME_NS: %lld\n", elapsed_ns);

    return 0;
}
