#!/bin/sh
# FastDoc'u kaldırır.
set -eu
rm -f "$HOME/.local/bin/fastdoc" \
      "$HOME/.local/share/applications/fastdoc.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/fastdoc.svg"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "FastDoc kaldırıldı. (Varsayılan PDF uygulamasını ayarlardan tekrar seçebilirsin.)"
