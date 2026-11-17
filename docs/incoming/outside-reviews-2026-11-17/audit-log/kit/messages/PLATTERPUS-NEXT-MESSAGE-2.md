The claude-code-skills session had an independent session check #396 and #398 at 7394e151. Seven of the eight items are done, and nothing verified in #393 regressed. The locks install cleanly with `--require-hashes`, and the reverts it tried for items 5 and 7 each turn a test red. What's left, most urgent first. Fix it in a pull request, merge it when it's green, and send one line back for each in your next handoff:

1. **The locks will rot.** Dependabot doesn't read `build/locks/*.lock`, and no job regenerates them, so a widened range (as in #399) changes nothing CI installs. Add a scheduled or Dependabot-triggered job that regenerates the locks and opens a pull request. Pin the regeneration with `--exclude-newer` so it's reproducible over time.
2. **Item 3 is partly done.** The ignores don't work: Dependabot's #399 widens mypy in `pinned-minor`, though mypy has been ignored since September. Find out why (ignore names, or `dependency-name` matching under a group), and fix it. Also, `pinned-minor` is one group of 12 packages, not one each as #398's body and `dependabot.yml:113` say: change the config or the comment.
3. **Reverts your tests don't catch:**
   - dropping `--no-isolation` (`publish-pypi.yml:136`, `build_appimage.sh:132`), which then fetches setuptools and wheel unhashed in the `id-token: write` job;
   - the build script's refusal without its lock;
   - dropping `--only-binary`;
   - a `pipx install` in `release.yml`;
   - a 7-day wait set to 0;
   - deleting a dependency from `release.lock`.

   Add a test for each.
4. **The locks are first exercised at publish or release time.** No pull request installs `publish.lock`, and `release.lock` is first installed on `main`. Add a pull-request job that installs each lock with `--require-hashes`, and builds without publishing.
5. **Not covered by locks:** the required `sbom` job (`ci.yml:599-600`, ranges plus a pip upgrade), `workflow-lint`, `shellcheck` and `mutation.yml`. TASKS R91 records this. Lock at least `sbom`, since it's required.
6. **Smaller:**
   - stale comments at `build/python-appimage/requirements.txt:27-29,46-47`;
   - `_CI_TOOLS` hard-coded at `test_dependabot_holds_the_pins.py:35`;
   - the cache test misses `actions/cache/restore@` and setup-uv's cache;
   - the publish gate accepts a `v*` tag on an older `main` commit, so say whether that's intended.

Hold your next lap and release nothing until I say so.
