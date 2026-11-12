#!/usr/bin/env bash
set -e

# Run this script from inside your dotfiles repo
# (e.g. ~/Documents/github/vscodium-dotfiles)

# Default path used by the hezkore AppImage installer. If your VSCodium
# AppImage lives somewhere else, change this line.
APPDIR="$HOME/.local/share/appimages/vscodium"
CODIUM="env APPDIR=$APPDIR $APPDIR/AppRun"
USER_DIR="$HOME/.config/VSCodium/User"

mkdir -p ./vscodium

# 1) List of installed extensions (one ID per line, no version —
#    so it can be reinstalled on any machine later)
echo "Exporting extension list..."
eval "$CODIUM" --list-extensions > ./vscodium/extensions.txt
echo "-> ./vscodium/extensions.txt ($(wc -l < ./vscodium/extensions.txt) extensions)"

# 2) settings.json
if [ -f "$USER_DIR/settings.json" ]; then
  cp "$USER_DIR/settings.json" ./vscodium/settings.json
  echo "-> ./vscodium/settings.json"
else
  echo "!! Could not find $USER_DIR/settings.json"
fi

# 3) keybindings.json (only copied if you've customized it)
if [ -f "$USER_DIR/keybindings.json" ]; then
  cp "$USER_DIR/keybindings.json" ./vscodium/keybindings.json
  echo "-> ./vscodium/keybindings.json"
fi

# 4) snippets (if you have any)
if [ -d "$USER_DIR/snippets" ] && [ "$(ls -A "$USER_DIR/snippets" 2>/dev/null)" ]; then
  mkdir -p ./vscodium/snippets
  cp -r "$USER_DIR"/snippets/* ./vscodium/snippets/
  echo "-> ./vscodium/snippets/"
fi

echo ""
echo "Done. Review what landed in ./vscodium/ before committing."
