#include <stdio.h>
#include <time.h>

int main(){

    int arr[5]={5,4,3,2,1};

    struct timespec start, end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for(int i=0;i<5;i++)
        for(int j=0;j<4;j++)
            if(arr[j]>arr[j+1]){
                int t=arr[j];
                arr[j]=arr[j+1];
                arr[j+1]=t;
            }

    clock_gettime(CLOCK_MONOTONIC, &end);

    printf("%d",arr[0]);

    long long elapsed_ns = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL
                          + (end.tv_nsec - start.tv_nsec);
    printf("\nEXEC_TIME_NS: %lld\n", elapsed_ns);

    return 0;
}
