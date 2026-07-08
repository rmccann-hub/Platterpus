/* Verification harness for the proposed cyanrip append_missing_keys() fix.
 *
 * Models cyanrip's src/cyanrip_main.c append_missing_keys() faithfully using
 * standard C equivalents for the FFmpeg helpers it uses:
 *   av_mallocz  -> calloc         av_strtok -> strtok_r
 * (Our test inputs contain no consecutive ':' delimiters, so the av_strtok vs
 * strtok_r merge-empties nuance does not affect any case here.)
 *
 * It reproduces the CURRENT function verbatim, then the FIXED function (current
 * + a guard that skips positional-key injection when the string is already
 * explicit key=value), and asserts behaviour on the real cases.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/* ---- CURRENT: transcribed 1:1 from cyanrip master (av_* -> libc) ---------- */
static char *current(char *src, const char *key1, const char *key2)
{
    char *copy = calloc(strlen(src) + strlen(key1) + strlen(key2) + 1, 1);
    memcpy(copy, src, strlen(src));

    int add_key1_offset = -1;
    int add_key2_offset = -1;

    int count = 0;
    char *p_save, *p = strtok_r(src, ":", &p_save);
    while (p) {
        if (!strstr(p, "=")) {
            if (count == 0)      add_key1_offset = p - src;
            else if (count == 1) add_key2_offset = p - src;
        }
        p = strtok_r(NULL, ":", &p_save);
        if (++count >= 2) break;
    }
    if (add_key1_offset >= 0) {
        memmove(&copy[add_key1_offset + strlen(key1)], &copy[add_key1_offset],
                strlen(copy) - add_key1_offset);
        memcpy(&copy[add_key1_offset], key1, strlen(key1));
        if (add_key2_offset >= 0) add_key2_offset += strlen(key1);
    }
    if (add_key2_offset >= 0) {
        memmove(&copy[add_key2_offset + strlen(key2)], &copy[add_key2_offset],
                strlen(copy) - add_key2_offset);
        memcpy(&copy[add_key2_offset], key2, strlen(key2));
    }
    return copy;
}

/* ---- FIXED: identical, plus the explicit-mode guard --------------------- */
static char *fixed(char *src, const char *key1, const char *key2)
{
    char *copy = calloc(strlen(src) + strlen(key1) + strlen(key2) + 1, 1);
    memcpy(copy, src, strlen(src));

    /* If already explicit key=value (an '=' before the first ':'), skip the
     * positional-shorthand injection; av_dict_parse_string honours '\:'. */
    char *first_colon = strchr(src, ':');
    char *first_eq    = strchr(src, '=');
    if (first_eq && (!first_colon || first_eq < first_colon))
        return copy;

    int add_key1_offset = -1;
    int add_key2_offset = -1;

    int count = 0;
    char *p_save, *p = strtok_r(src, ":", &p_save);
    while (p) {
        if (!strstr(p, "=")) {
            if (count == 0)      add_key1_offset = p - src;
            else if (count == 1) add_key2_offset = p - src;
        }
        p = strtok_r(NULL, ":", &p_save);
        if (++count >= 2) break;
    }
    if (add_key1_offset >= 0) {
        memmove(&copy[add_key1_offset + strlen(key1)], &copy[add_key1_offset],
                strlen(copy) - add_key1_offset);
        memcpy(&copy[add_key1_offset], key1, strlen(key1));
        if (add_key2_offset >= 0) add_key2_offset += strlen(key1);
    }
    if (add_key2_offset >= 0) {
        memmove(&copy[add_key2_offset + strlen(key2)], &copy[add_key2_offset],
                strlen(copy) - add_key2_offset);
        memcpy(&copy[add_key2_offset], key2, strlen(key2));
    }
    return copy;
}

typedef char *(*fn)(char *, const char *, const char *);
static char *run(fn f, const char *in) {
    char *dup = strdup(in);                 /* the fn mutates src via strtok */
    char *out = f(dup, "album=", "album_artist=");
    free(dup);
    return out;
}

int main(void)
{
    /* 1. The bug: a literal ':' in an explicit value. */
    const char *bug = "album=Every Breath You Take: The Classics";
    char *cur = run(current, bug);
    char *fix = run(fixed, bug);
    printf("case 1  in : %s\n", bug);
    printf("        cur: %s\n", cur);
    printf("        fix: %s\n", fix);
    assert(strstr(cur, "album_artist=") != NULL);   /* current CORRUPTS */
    assert(strcmp(fix, bug) == 0);                  /* fixed leaves it intact */
    free(cur); free(fix);

    /* 2. Positional shorthand still works (both identical). */
    const char *pos = "Some Album:Some Artist";
    char *cp = run(current, pos), *fp = run(fixed, pos);
    printf("case 2  in : %s\n        cur: %s\n        fix: %s\n", pos, cp, fp);
    assert(strcmp(cp, "album=Some Album:album_artist=Some Artist") == 0);
    assert(strcmp(fp, cp) == 0);                    /* fix preserves shorthand */
    free(cp); free(fp);

    /* 3. Explicit multi-key, no colons in values (both fine, identical). */
    const char *ex = "album=Foo:date=2020";
    char *ce = run(current, ex), *fe = run(fixed, ex);
    printf("case 3  in : %s\n        cur: %s\n        fix: %s\n", ex, ce, fe);
    assert(strcmp(ce, ex) == 0 && strcmp(fe, ex) == 0);
    free(ce); free(fe);

    /* 4. The escaped colon we'd actually send post-fix survives untouched. */
    const char *esc = "album=Every Breath You Take\\: The Classics";
    char *cx = run(current, esc), *fx = run(fixed, esc);
    printf("case 4  in : %s\n        cur: %s\n        fix: %s\n", esc, cx, fx);
    assert(strstr(cx, "album_artist=") != NULL);    /* current still corrupts */
    assert(strcmp(fx, esc) == 0);                   /* fixed keeps the \: intact */
    free(cx); free(fx);

    printf("\nALL ASSERTIONS PASSED — the guard fixes the colon corruption "
           "and preserves positional shorthand.\n");
    return 0;
}
