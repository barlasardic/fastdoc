#!/bin/sh
# FastDoc'u kaldırır.
set -eu
rm -f "$HOME/.local/bin/fastdoc" \
      "$HOME/.local/share/applications/fastdoc.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/fastdoc.svg"
# FastDoc varsayılan PDF uygulamasıysa o kaydı da temizle
MIMEAPPS="$HOME/.config/mimeapps.list"
[ -f "$MIMEAPPS" ] && sed -i '/^application\/pdf=fastdoc\.desktop$/d' "$MIMEAPPS"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "FastDoc kaldırıldı."
