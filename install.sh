#!/bin/sh
# FastDoc kurulum betiği (kullanıcı seviyesinde, uygulama için sudo gerekmez).
#
# Uzaktan:  curl -fsSL https://raw.githubusercontent.com/barlasardic/fastdoc/main/install.sh | sh
# Yerelden: ./install.sh        (fastdoc.py yanındaysa onu kullanır)
set -eu

REPO="${FASTDOC_REPO:-barlasardic/fastdoc}"   # GitHub "kullanici/repo"
BRANCH="${FASTDOC_BRANCH:-main}"

BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

say() { printf '==> %s\n' "$*"; }

# 1) Bağımlılıklar (Debian/Pardus): python3-gi, python3-gi-cairo, GTK3, Poppler
have_deps() {
    /usr/bin/python3 - <<'EOF' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Poppler", "0.18")
from gi.repository import Gtk, Poppler
gi.require_foreign("cairo")
EOF
}

if [ "${FASTDOC_SKIP_DEPS:-0}" != "1" ] && ! have_deps; then
    say "Bağımlılıklar kuruluyor (sudo şifresi istenebilir)..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-poppler-0.18
    else
        echo "apt-get yok. Şunları elle kur: PyGObject, GTK3 ve Poppler GObject bağlantısı." >&2
        exit 1
    fi
    have_deps || { echo "Bağımlılıklar kurulamadı." >&2; exit 1; }
fi

mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR" "$HOME/.config"

# 2) Programı yerleştir (yerelde varsa oradan, yoksa GitHub'dan)
SRC_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"
if [ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/fastdoc.py" ]; then
    say "Yerel fastdoc.py kopyalanıyor"
    cp "$SRC_DIR/fastdoc.py" "$BIN_DIR/fastdoc"
else
    URL="https://raw.githubusercontent.com/$REPO/$BRANCH/fastdoc.py"
    say "İndiriliyor: $URL"
    curl -fsSL "$URL" -o "$BIN_DIR/fastdoc"
fi
chmod +x "$BIN_DIR/fastdoc"

# 3) İkon
cat > "$ICON_DIR/fastdoc.svg" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <path d="M30 10h44l28 28v80H30z" fill="#fff" stroke="#c0392b" stroke-width="6" stroke-linejoin="round"/>
  <path d="M74 10v28h28" fill="#f3d9d6" stroke="#c0392b" stroke-width="6" stroke-linejoin="round"/>
  <rect x="42" y="62" width="48" height="8" rx="2" fill="#c0392b"/>
  <rect x="42" y="80" width="48" height="8" rx="2" fill="#c0392b"/>
  <rect x="42" y="98" width="30" height="8" rx="2" fill="#c0392b"/>
</svg>
EOF

# 4) Masaüstü girişi (PDF'leri açabilen uygulama olarak kaydolur)
cat > "$APP_DIR/fastdoc.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=FastDoc
GenericName=PDF Görüntüleyici
Comment=Çok hafif PDF görüntüleyici
Exec=$BIN_DIR/fastdoc %f
Icon=fastdoc
Terminal=false
Categories=Office;Viewer;GTK;
MimeType=application/pdf;
StartupNotify=true
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

# 5) Varsayılan PDF uygulaması yap
if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default fastdoc.desktop application/pdf
    say "Varsayılan PDF uygulaması: $(xdg-mime query default application/pdf)"
else
    echo "xdg-mime yok; varsayılan uygulamayı elle seçmen gerekir." >&2
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) say "Not: $BIN_DIR PATH'te değil; terminalden 'fastdoc' için oturumu yeniden aç." ;;
esac

say "Kuruldu. PDF'e çift tıkla veya: fastdoc dosya.pdf"
