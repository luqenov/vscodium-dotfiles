#!/usr/bin/env bash
set -e

# Run this script from inside your dotfiles repo, on a fresh machine,
# AFTER installing VSCodium (AppImage) and closing every VSCodium window.

# Default path used by the hezkore AppImage installer. If your VSCodium
# AppImage lives somewhere else, change this line.
APPDIR="$HOME/.local/share/appimages/vscodium"
CODIUM="env APPDIR=$APPDIR $APPDIR/AppRun"
USER_DIR="$HOME/.config/VSCodium/User"

# 1) Reinstall extensions
if [ -f ./vscodium/extensions.txt ]; then
  echo "Installing extensions..."
  while read -r ext; do
    [ -z "$ext" ] && continue
    echo "Installing $ext..."
    eval "$CODIUM" --install-extension "$ext" --force || echo "!! Failed: $ext (might not be available on Open VSX — check manually)"
  done < ./vscodium/extensions.txt
else
  echo "!! Could not find ./vscodium/extensions.txt"
fi

# 2) Copy configs back into place
mkdir -p "$USER_DIR"

if [ -f ./vscodium/settings.json ]; then
  cp ./vscodium/settings.json "$USER_DIR/settings.json"
  echo "-> settings.json restored"
fi

if [ -f ./vscodium/keybindings.json ]; then
  cp ./vscodium/keybindings.json "$USER_DIR/keybindings.json"
  echo "-> keybindings.json restored"
fi

if [ -d ./vscodium/snippets ]; then
  mkdir -p "$USER_DIR/snippets"
  cp -r ./vscodium/snippets/* "$USER_DIR/snippets/"
  echo "-> snippets restored"
fi

echo ""
echo "Done! Open VSCodium to check everything."
