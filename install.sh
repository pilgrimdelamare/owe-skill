#!/usr/bin/env bash
# OWE install.sh — installs the skill and patches ~/.claude/CLAUDE.md automatically

set -e

SKILLS_DIR="$HOME/.claude/skills/owe-skill"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
SCRIPTS_DIR="$SKILLS_DIR/scripts"

echo "[OWE] Installing skill to $SKILLS_DIR..."
mkdir -p "$SKILLS_DIR"
cp -r owe-skill/. "$SKILLS_DIR/"
echo "[OWE] Skill installed."

# Patch CLAUDE.md only if OWE block is not already present
if grep -q "owe-skill" "$CLAUDE_MD" 2>/dev/null; then
    echo "[OWE] CLAUDE.md already contains OWE instructions — skipping."
else
    echo "[OWE] Adding OWE instructions to $CLAUDE_MD..."
    cat >> "$CLAUDE_MD" << 'OWEEOF'

# OWE — Once Was Enough

At the start of every session, before responding:

1. Check if $HOME/.owe/owe.db exists:
   - Not found → tell the user: "[OWE] Database not found. Run: python $HOME/.claude/skills/owe-skill/scripts/census.py"
   - Found → run python $HOME/.claude/skills/owe-skill/scripts/verify.py --status and report as [OWE] <output>

2. Run python $HOME/.claude/skills/owe-skill/scripts/prefs.py --load and keep preferences in context for the session.

Before writing any code: python $HOME/.claude/skills/owe-skill/scripts/search.py keyword1 keyword2
OWEEOF
    echo "[OWE] CLAUDE.md updated."
fi

echo ""
echo "[OWE] Installation complete."
echo ""
echo "Next step — run the initial census:"
echo "  python $SCRIPTS_DIR/census.py"
