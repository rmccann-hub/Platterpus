#!/usr/bin/env bash
# Build one run folder per (repository, skill): a fresh clone of the repository's snapshot, a
# copy of the one skill from a release tag, an empty output folder, and the brief filled in.
#
#   make-runs.sh <tag> [<repo> ...]      e.g. make-runs.sh v0.1.23 platterpus cyanrip
#
# Skills come from the tag's skills/ folder, so a new skill gets its runs with no change here.
# Repositories are the folders under snapshots/; with none named, every snapshot is used.
set -euo pipefail

kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skills_repo="${SKILLS_REPO:-$kit/../..}"
tag="${1:?usage: make-runs.sh <tag> [<repo> ...]}"
shift
if (($# == 0)); then
  mapfile -t repos < <(find "$kit/snapshots" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
else
  repos=("$@")
fi

mapfile -t skills < <(git -C "$skills_repo" ls-tree --name-only "$tag:skills")
for repo in "${repos[@]}"; do
  [[ -d "$kit/snapshots/$repo/.git" ]] || { echo "no snapshot: $repo" >&2; exit 1; }
  for skill in "${skills[@]}"; do
    run="$kit/runs/$tag/$repo/$skill"
    if [[ -e "$run" ]]; then
      echo "exists, left as it is: $run"
      continue
    fi
    mkdir -p "$run/out"
    git clone -q --no-local "$kit/snapshots/$repo" "$run/repo"
    git -C "$run/repo" remote remove origin
    mkdir -p "$run/skill"
    git -C "$skills_repo" archive "$tag" "skills/$skill" | tar -x -C "$run/skill" --strip-components=2
    sed -e "s#{SKILL_DIR}#$run/skill#g" -e "s#{REPO_DIR}#$run/repo#g" -e "s#{OUT_DIR}#$run/out#g" \
      "$kit/brief.md" > "$run/brief.md"
    echo "built: $run"
  done
done
