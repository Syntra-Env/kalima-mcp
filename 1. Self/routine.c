#include <stdio.h>

struct character {
    int energy;
};

void time() {
    int day = 1440;
    int i;
    for(i=0; i<day;i++){
        float time = i/60;
        printf("%d\n", time);
    }
}

int main () {
    time();
    return 0;
}

