#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#define fatal_WA(...) fprintf(stderr, __VA_ARGS__); fprintf(stderr, "\n"); exit(1)
#define fatal_PE(...) fprintf(stderr, __VA_ARGS__); fprintf(stderr, "\n"); exit(1)
#define fatal_CF(...) fprintf(stderr, __VA_ARGS__); fprintf(stderr, "\n"); exit(1)

#define checker_drain() ;

#define checker_kill kill

int checker_stoi(const char * str, int base, int *val) {
    char *end = NULL;
    *val = strtol(str, &end, base);
    return *end == '\0';
}
