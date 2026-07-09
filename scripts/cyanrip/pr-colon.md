<!-- Ready-to-paste GitHub PR body for the colon fix (cyanreg/cyanrip).
     One focused commit on a `fix/meta-colon` branch off upstream master. -->

Title: cyanrip_main: don't inject positional keys into an explicit key=value tag string

`append_missing_keys()` tokenises the `-a`/`-t` string with `av_strtok(src, ":")`
to support the positional `album:album_artist` shorthand, then hands the result
to `av_dict_parse_string(&meta, copy, "=", ":", 0)`. But `av_strtok` splits on
*every* `:` and, unlike `av_dict_parse_string`, doesn't honour the `\` escape —
so a literal colon in an explicit value gets a spurious key injected:

```
-a "album=Every Breath You Take: The Classics"
  → "album=Every Breath You Take:album_artist= The Classics"   (wrong)
```

This guard skips the positional-shorthand injection when the string is already
explicit `key=value` (an `=` appears before the first `:`). The positional path
is unchanged; explicit strings now pass through to `av_dict_parse_string`, which
already unescapes `\:` correctly. A ~4-line change, no new behaviour for the
shorthand path, no reformatting.

Cases:

| Input | Behaviour |
|---|---|
| `Some Album:Some Artist` (positional) | inject keys — unchanged |
| `album=Foo:date=2020` | skip injection → both parse |
| `album=…Take\: The Classics` | skip → `av_dict_parse_string` unescapes `\:` |
| `Foo:artist=Bar` (mixed, `=` after `:`) | inject `album=` — unchanged |

Verified with a standalone transcription of the function (current vs. fixed),
built ASan/UBSan-clean; all four cases pass.
