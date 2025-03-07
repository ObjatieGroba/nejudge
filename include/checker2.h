#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

enum
{
    RUN_OK               = 0,
    RUN_COMPILE_ERR      = 1,
    RUN_RUN_TIME_ERR     = 2,
    RUN_TIME_LIMIT_ERR   = 3,
    RUN_PRESENTATION_ERR = 4,
    RUN_WRONG_ANSWER_ERR = 5,
    RUN_CHECK_FAILED     = 6,
    RUN_PARTIAL          = 7,
    RUN_ACCEPTED         = 8,
    RUN_IGNORED          = 9,
    RUN_DISQUALIFIED     = 10,
    RUN_PENDING          = 11,
    RUN_MEM_LIMIT_ERR    = 12,
    RUN_SECURITY_ERR     = 13,
    RUN_STYLE_ERR        = 14,
    RUN_WALL_TIME_LIMIT_ERR = 15,
    RUN_PENDING_REVIEW   = 16,
    RUN_REJECTED         = 17,
    RUN_SKIPPED          = 18,
    RUN_SYNC_ERR         = 19,
    RUN_SUMMONED         = 23,
};

#define xcalloc calloc

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
