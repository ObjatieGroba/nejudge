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

FILE * f_in = NULL;
FILE * f_out = NULL;

const char * _(const char *s) {
    return s;
}

void checker_do_init(int argc, char **argv, int corr_flag, int info_flag, int tgz_flag) {
    if (argc < 3) {
        fatal_CF(_("arguments expected '%d'"), argc);
    }

    if (!(f_in = fopen(argv[1], "r"))) {
        fatal_CF(_("Cannot open input file '%s'"), argv[1]);
    }
    if (!(f_out = fopen(argv[2], "r"))) {
        fatal_PE(_("Cannot open output file '%s'"), argv[2]);
    }
}

int checker_read_in_unsigned_long_long(const char *name, int eof_error_flag, unsigned long long *p_val) {
    int r = fscanf(f_in, "%llu", p_val);
    if (eof_error_flag && r == EOF) {
        fatal_PE(_("Unexpected EOF while reading %s"), name);
    }
    return r;
}

int checker_read_in_int(const char *name, int eof_error_flag, int *p_val) {
    int r = fscanf(f_in, "%d", p_val);
    if (eof_error_flag && r == EOF) {
        fatal_PE(_("Unexpected EOF while reading %s"), name);
    }
    return r;
}

int checker_read_out_unsigned_long_long(const char *name, int eof_error_flag, unsigned long long *p_val) {
    int r = fscanf(f_out, "%llu", p_val);
    if (eof_error_flag && r == EOF) {
        fatal_PE(_("Unexpected EOF while reading %s"), name);
    }
    return r;
}

void checker_in_eof(void) {
    int c;

    while ((c = getc(f_in)) != EOF && isspace(c));
    if (c != EOF) {
        if (c < ' ') {
            fatal_CF(_("%s: invalid control character with code %d"),
                     "input", c);
        } else {
            fatal_CF(_("%s: garbage where EOF expected"), "input");
        }
    }
    if (ferror(f_in)) {
        fatal_CF(_("%s: input error"), "input");
    }
}

void checker_in_close(void) {
    if (!f_in) return;
    fclose(f_in);
    f_in = NULL;
}

void checker_out_eof(void) {
    int c;

    while ((c = getc(f_out)) != EOF && isspace(c));
    if (c != EOF) {
        if (c < ' ') {
            fatal_CF(_("%s: invalid control character with code %d"),
                     "output", c);
        } else {
            fatal_CF(_("%s: garbage where EOF expected"), "output");
        }
    }
    if (ferror(f_out)) {
        fatal_CF(_("%s: input error"), "output");
    }
}

void checker_out_close(void) {
    if (!f_out) return;
    fclose(f_out);
    f_out = NULL;
}

int checker_stoi(const char * str, int base, int *val) {
    char *end = NULL;
    *val = strtol(str, &end, base);
    return *end == '\0';
}
