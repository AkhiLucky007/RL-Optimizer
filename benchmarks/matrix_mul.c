#include <stdio.h>
#include <time.h>

int main(){

    int A[2][2]={{1,2},{3,4}};
    int B[2][2]={{5,6},{7,8}};
    int C[2][2];

    struct timespec start, end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for(int i=0;i<2;i++)
        for(int j=0;j<2;j++){
            C[i][j]=0;
            for(int k=0;k<2;k++)
                C[i][j]+=A[i][k]*B[k][j];
        }

    clock_gettime(CLOCK_MONOTONIC, &end);

    printf("%d",C[0][0]);

    long long elapsed_ns = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL
                          + (end.tv_nsec - start.tv_nsec);
    printf("\nEXEC_TIME_NS: %lld\n", elapsed_ns);

    return 0;
}
