#include <stdio.h>
#include <time.h>

int main(){

    int arr[5]={1,3,5,7,9};
    int key=7;

    struct timespec start, end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for(int i=0;i<5;i++){
        if(arr[i]==key){
            printf("found");
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    long long elapsed_ns = (long long)(end.tv_sec - start.tv_sec) * 1000000000LL
                          + (end.tv_nsec - start.tv_nsec);
    printf("\nEXEC_TIME_NS: %lld\n", elapsed_ns);

    return 0;
}
