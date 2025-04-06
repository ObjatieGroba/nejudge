#include <linux/limits.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>


int checker_main(int argc, char **argv);

//struct testinfo_array
//{
//    char **v;
//    int u;
//};
//
//struct testinfo_struct
//{
//    struct testinfo_array cmd;
//    struct testinfo_array env;
//    struct testinfo_array checker_env;
//    struct testinfo_array interactor_env;
//    struct testinfo_array init_env;
//    struct testinfo_array compiler_env;
//    struct testinfo_array style_checker_env;
//    struct testinfo_array ok_language;
//    char *comment;
//    char *team_comment;
//    char *source_stub;
//    char *working_dir;
//    char *program_name;
//    char *check_cmd;
//    long long max_vm_size;
//    long long max_stack_size;
//    long long max_file_size;
//    long long max_rss_size;
//    int exit_code;
//    int ignore_exit_code;
//    int check_stderr;
//    int disable_stderr;
//    int enable_subst;
//    int compiler_must_fail;
//    int disable_valgrind;
//    int max_open_file_count;
//    int max_process_count;
//    int time_limit_ms;
//    int real_time_limit_ms;
//    int allow_compile_error;
//    int ignore_term_signal;
//};
//typedef struct testinfo_struct testinfo_t;
//
//
//testinfo_t test_info = {};

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
    OLD_RUN_MAX_STATUS   = 19, // obsoleted
    RUN_NORMAL_LAST      = 19, // may safely overlap pseudo statuses

    RUN_PSEUDO_FIRST     = 20,
    RUN_VIRTUAL_START    = 20,
    RUN_VIRTUAL_STOP     = 21,
    RUN_EMPTY            = 22,
    RUN_PSEUDO_LAST      = 22,

    RUN_SUMMONED         = 23, // summoned for oral defence
    RUN_LOW_LAST         = 23, // will be == RUN_NORMAL_LAST later

    RUN_TRANSIENT_FIRST  = 95,
    RUN_FULL_REJUDGE     = 95,    /* cannot appear in runlog */
    RUN_RUNNING          = 96,
    RUN_COMPILED         = 97,
    RUN_COMPILING        = 98,
    RUN_AVAILABLE        = 99,
    RUN_REJUDGE          = 99,
    RUN_TRANSIENT_LAST   = 99,

    RUN_STATUS_SIZE      = 100
};

void checker_OK(void) {
    fprintf(stderr, "OK\n");
    exit(0);
}

void fatal_WA(char const *format, ...) {
    va_list args;

    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fprintf(stderr, "\n");
    exit(RUN_WRONG_ANSWER_ERR);
}

void fatal_CF(char const *format, ...) {
    va_list args;

    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fprintf(stderr, "\n");
    exit(RUN_CHECK_FAILED);
}

void
checker_read_file_f(FILE *f, char **out, size_t *out_len)
{
    unsigned char read_buf[512];
    unsigned char *buf = 0;
    size_t buf_len = 0, read_len = 0;

    while (1) {
        read_len = fread(read_buf, 1, sizeof(read_buf), f);
        if (!read_len) break;
        if (!buf_len) {
            buf = (unsigned char*) calloc(read_len + 1, 1);
            memcpy(buf, read_buf, read_len);
            buf_len = read_len;
        } else {
            buf = (unsigned char*) realloc(buf, buf_len + read_len + 1);
            memcpy(buf + buf_len, read_buf, read_len);
            buf_len += read_len;
            buf[buf_len] = 0;
        }
    }
    if (ferror(f)) {
        fatal_CF("Input error: %s", strerror(errno));
    }
    if (!buf_len) {
        buf = (unsigned char*) malloc(1);
        buf[0] = 0;
        buf_len = 0;
    }
    if (out) *out = (char*)buf;
    if (out_len) *out_len = buf_len;
}

void
checker_read_file_by_line(FILE* f,
                          char ***out_lines,
                          size_t *out_lines_num,
                          const char *name)
{
    char **lb_v = 0;
    size_t lb_a = 0, lb_u = 0;
    unsigned char *b_v = 0;
    size_t b_a = 0, b_u = 0;
    int c;

    lb_a = 128;
    lb_v = (char **) calloc(lb_a, sizeof(lb_v[0]));
    lb_v[0] = NULL;

    b_a = 1024;
    b_v = (unsigned char *) malloc(b_a);
    b_v[0] = 0;

    while ((c = getc(f)) != EOF) {
        if (!c)  fatal_CF("\\0 byte in file");
        if (b_u + 1 >= b_a) {
            b_v = (unsigned char*) realloc(b_v, (b_a *= 2) * sizeof(b_v[0]));
        }
        b_v[b_u++] = c;
        b_v[b_u] = 0;
        if (c != '\n') continue;

        if (lb_u + 1 >= lb_a) {
            lb_a *= 2;
            lb_v = (char **) realloc(lb_v, lb_a * sizeof(lb_v[0]));
        }
        lb_v[lb_u++] = strdup((char*)b_v);
        lb_v[lb_u] = NULL;
        b_u = 0;
        b_v[b_u] = 0;
    }
    if (ferror(f)) {
        fatal_CF("Input error from file %s", name);
    }
    if (b_u > 0) {
        if (lb_u + 1 >= lb_a) {
            lb_v = realloc(lb_v, (lb_a *= 2) * sizeof(lb_v[0]));
        }
        lb_v[lb_u++] = strdup((char*)b_v);
        lb_v[lb_u] = NULL;
    }

    if (out_lines_num) *out_lines_num = lb_u;
    if (out_lines) *out_lines = lb_v;

    free(b_v);
}

void
checker_normalize_file(char **lines, size_t *lines_num)
{
    int i;
    size_t len;
    char *p;

    for (i = 0; i < *lines_num; i++) {
        if (!(p = lines[i])) fatal_CF("lines[%d] is NULL!", i);
        len = strlen(p);
        while (len > 0 && isspace(p[len - 1])) p[--len] = 0;
    }

    i = *lines_num;
    while (i > 0 && !lines[i - 1][0]) {
        i--;
        free(lines[i]);
        lines[i] = 0;
    }
    *lines_num = i;
}

int main(int argc, char **argv) {

    return checker_main(argc, argv);
}
