<!-- Ready-to-paste GitHub ISSUE body for cyanreg/cyanrip. Title on the first
     line, body below. Rationale + verification: docs/cyanrip-soft-fork.md §2. -->

Title: `-a`/`-t`: a literal `:` in a tag value is corrupted by `append_missing_keys`

A colon inside an explicit metadata value is mangled. Example:

```
cyanrip … -a "album=Every Breath You Take: The Classics"
```

lands as album `Every Breath You Take` with a spurious `album_artist= The
Classics`, because `append_missing_keys()` (`src/cyanrip_main.c`) tokenises the
string with `av_strtok(src, ":")` before `av_dict_parse_string()` runs.
`av_strtok` splits on every `:` and ignores backslash escapes, so the fragment
after the colon looks like a keyless positional value and gets a key injected. A
backslash-escaped `\:` doesn't help either, because `av_strtok` doesn't honour it
(only the later `av_dict_parse_string` does).

Colons in album/track titles are common (subtitles, classical works), so this
bites any front-end feeding explicit tags.

**Proposed fix:** skip the positional-key injection when the string is already
explicit `key=value` (an `=` before the first `:`); then a caller can pass a
literal colon as `\:` and `av_dict_parse_string` handles it. Positional shorthand
(`album:album_artist`) is unaffected. Happy to open a PR — the patch is a ~4-line
guard in `append_missing_keys()`.
