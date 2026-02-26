#!/usr/bin/env bash
set -euo pipefail

# Updates the Homebrew formula with a new version's URL and SHA256.
#
# Usage:
#   ./scripts/update-homebrew-formula.sh 0.2.0
#   ./scripts/update-homebrew-formula.sh            # reads from pyproject.toml

FORMULA="homebrew/mediascribe.rb"

if [[ $# -ge 1 ]]; then
    VERSION="$1"
else
    VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
fi

TARBALL_URL="https://pypi.io/packages/source/m/mediascribe/mediascribe-${VERSION}.tar.gz"
echo "Version:  $VERSION"
echo "URL:      $TARBALL_URL"

# Try to download and compute SHA256 (only works after PyPI publish)
if command -v curl &>/dev/null; then
    TMPFILE=$(mktemp)
    if curl -sSfL "$TARBALL_URL" -o "$TMPFILE" 2>/dev/null; then
        SHA256=$(sha256sum "$TMPFILE" | awk '{print $1}')
        rm -f "$TMPFILE"
        echo "SHA256:   $SHA256"
    else
        rm -f "$TMPFILE"
        SHA256="PLACEHOLDER_SHA256"
        echo "SHA256:   (tarball not yet available, using placeholder)"
    fi
else
    SHA256="PLACEHOLDER_SHA256"
    echo "SHA256:   (curl not available, using placeholder)"
fi

# Update the formula
sed -i "s|url \".*\"|url \"$TARBALL_URL\"|" "$FORMULA"
sed -i "s|sha256 \".*\"|sha256 \"$SHA256\"|" "$FORMULA"

echo ""
echo "Updated $FORMULA"
echo ""
echo "To set up a Homebrew tap:"
echo "  1. Create a repo: github.com/shawnpetros/homebrew-mediascribe"
echo "  2. Copy homebrew/mediascribe.rb to Formula/mediascribe.rb in that repo"
echo "  3. Users install via: brew tap shawnpetros/mediascribe && brew install mediascribe"
