#!/bin/bash
# Fifth Symphony - External Repos Auto-Update
# Updates all external repos with git pull (fast-forward only)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configure this path for your environment
EXTERNAL_REPOS_DIR="${GIT_ROOT:-$HOME/git}/external/repos"

echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   📚 External Repos Auto-Update${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}\n"

# Count repos
total_repos=$(find "$EXTERNAL_REPOS_DIR" -maxdepth 1 -type d | wc -l | tr -d ' ')
total_repos=$((total_repos - 1))  # Subtract parent directory

updated_count=0
skipped_count=0
error_count=0

echo -e "${BLUE}Found $total_repos repositories in $EXTERNAL_REPOS_DIR${NC}\n"

# Iterate through repos
for repo in "$EXTERNAL_REPOS_DIR"/*/ ; do
    if [ ! -d "$repo/.git" ]; then
        continue  # Skip non-git directories
    fi

    cd "$repo"
    repo_name=$(basename "$repo")

    echo -e "${CYAN}──────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}📦 $repo_name${NC}"

    # Check if repo is clean
    if [[ -n $(git status -s) ]]; then
        echo -e "${YELLOW}⚠️  Skipping (uncommitted changes)${NC}"
        skipped_count=$((skipped_count + 1))
        continue
    fi

    # Get current branch
    current_branch=$(git branch --show-current)

    # Check if behind remote
    git fetch --quiet

    commits_behind=$(git rev-list HEAD..@{u} --count 2>/dev/null || echo "0")

    if [ "$commits_behind" -eq 0 ]; then
        echo -e "${GREEN}✓ Already up to date${NC}"
    else
        echo -e "${YELLOW}↓ $commits_behind commits behind, pulling...${NC}"

        # Attempt fast-forward pull
        if git pull --ff-only; then
            echo -e "${GREEN}✅ Updated successfully${NC}"
            updated_count=$((updated_count + 1))
        else
            echo -e "${RED}❌ Pull failed (merge required)${NC}"
            error_count=$((error_count + 1))
        fi
    fi
done

# Summary
echo -e "\n${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   📊 Update Summary${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Updated: $updated_count${NC}"
echo -e "${YELLOW}⚠️  Skipped: $skipped_count${NC}"
echo -e "${RED}❌ Errors: $error_count${NC}"
echo -e "${BLUE}📚 Total: $total_repos${NC}\n"

if [ $error_count -gt 0 ]; then
    echo -e "${RED}Some repos require manual intervention (merge conflicts or diverged branches)${NC}"
    exit 1
fi

if [ $updated_count -gt 0 ]; then
    echo -e "${GREEN}🎉 External repos updated successfully!${NC}"
fi
