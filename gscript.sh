#!/usr/bin/env bash
set -euo pipefail

# sync-dev-into-main.sh
# Purpose:
# 1) Merge dev into main even if histories are unrelated (Option A)
# 2) Re-anchor dev to main so GitHub PR diffs work again
#
# Safe defaults:
# - Refuses to run with a dirty working tree
# - Creates timestamped backup branches before changes
# - Uses --ff-only for pulls
# - Uses --force-with-lease (not --force) when re-anchoring dev

MAIN_BRANCH="${MAIN_BRANCH:-main}"
DEV_BRANCH="${DEV_BRANCH:-dev}"
REMOTE="${REMOTE:-origin}"

timestamp() { date +"%Y%m%d-%H%M%S"; }

die() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

require_cmd git

# Must be inside a repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not inside a git repository."

# Ensure clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
  die "Working tree is not clean. Commit or stash changes first."
fi

# Ensure remote exists
git remote get-url "$REMOTE" >/dev/null 2>&1 || die "Remote '$REMOTE' not found."

echo "Repo: $(basename "$(git rev-parse --show-toplevel)")"
echo "Remote: $REMOTE"
echo "Main branch: $MAIN_BRANCH"
echo "Dev branch:  $DEV_BRANCH"
echo

# Fetch everything
echo "Fetching from $REMOTE..."
git fetch --prune "$REMOTE"

# Ensure branches exist on remote
git show-ref --verify --quiet "refs/remotes/$REMOTE/$MAIN_BRANCH" || die "Remote branch '$REMOTE/$MAIN_BRANCH' not found."
git show-ref --verify --quiet "refs/remotes/$REMOTE/$DEV_BRANCH"  || die "Remote branch '$REMOTE/$DEV_BRANCH' not found."

# Create local branches tracking remote if missing
ensure_local_branch() {
  local branch="$1"
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    return 0
  fi
  echo "Creating local branch '$branch' tracking '$REMOTE/$branch'..."
  git branch --track "$branch" "$REMOTE/$branch" >/dev/null 2>&1 || git checkout -b "$branch" "$REMOTE/$branch" >/dev/null
}

ensure_local_branch "$MAIN_BRANCH"
ensure_local_branch "$DEV_BRANCH"

# Update dev
echo
echo "Updating '$DEV_BRANCH' (fast-forward only)..."
git checkout "$DEV_BRANCH" >/dev/null
git pull --ff-only "$REMOTE" "$DEV_BRANCH"

# Update main
echo
echo "Updating '$MAIN_BRANCH' (fast-forward only)..."
git checkout "$MAIN_BRANCH" >/dev/null
git pull --ff-only "$REMOTE" "$MAIN_BRANCH"

# Create backup branches
ts="$(timestamp)"
backup_main="backup/${MAIN_BRANCH}-before-merge-${ts}"
backup_dev="backup/${DEV_BRANCH}-before-merge-${ts}"

echo
echo "Creating backup branches:"
echo "  $backup_main -> $MAIN_BRANCH"
echo "  $backup_dev  -> $DEV_BRANCH"
git branch "$backup_main" "$MAIN_BRANCH"
git branch "$backup_dev"  "$DEV_BRANCH"

echo
echo "Attempting merge: '$DEV_BRANCH' -> '$MAIN_BRANCH' (allow unrelated histories if needed)..."

set +e
git merge "$DEV_BRANCH" --no-edit --allow-unrelated-histories
merge_rc=$?
set -e

if [[ $merge_rc -ne 0 ]]; then
  echo
  echo "Merge stopped (likely conflicts)."
  echo "Resolve conflicts, then run:"
  echo "  git add -A"
  echo "  git commit"
  echo
  echo "After committing, rerun this script to complete the PR-fix step,"
  echo "or manually continue with:"
  echo "  git push $REMOTE $MAIN_BRANCH"
  echo "  git checkout -B $DEV_BRANCH $MAIN_BRANCH"
  echo "  git push --force-with-lease $REMOTE $DEV_BRANCH"
  exit 2
fi

# Push main
echo
echo "Pushing merged '$MAIN_BRANCH' to '$REMOTE'..."
git push "$REMOTE" "$MAIN_BRANCH"

# Re-anchor dev to main so PRs work (dev becomes a normal branch off main again)
echo
echo "Re-anchoring '$DEV_BRANCH' to '$MAIN_BRANCH' so PR diffs work again..."
git checkout "$MAIN_BRANCH" >/dev/null

# Update local dev to point at main
git checkout -B "$DEV_BRANCH" "$MAIN_BRANCH" >/dev/null

echo "Pushing re-anchored '$DEV_BRANCH' to '$REMOTE' using --force-with-lease..."
git push --force-with-lease "$REMOTE" "$DEV_BRANCH"

echo
echo "Done."
echo "Backups created locally:"
echo "  $backup_main"
echo "  $backup_dev"
echo
echo "If you need to undo locally:"
echo "  git checkout $MAIN_BRANCH && git reset --hard $backup_main"
echo "  git checkout $DEV_BRANCH  && git reset --hard $backup_dev"
