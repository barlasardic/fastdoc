#!/bin/sh
# FastDoc kurulum betiği (kullanıcı seviyesinde, uygulama için sudo gerekmez).
#
# Uzaktan:  curl -fsSL https://raw.githubusercontent.com/barlasardic/fastdoc/main/install.sh | sh
# Yerelden: ./install.sh        (fastdoc.py yanındaysa onu kullanır)
#
# Varsayılan PDF uygulaması yapmak için (isteğe bağlı):  ... | sh -s -- --default
# ya da kurduktan sonra:  fastdoc --set-default
set -eu

REPO="${FASTDOC_REPO:-barlasardic/fastdoc}"   # GitHub "kullanici/repo"
BRANCH="${FASTDOC_BRANCH:-main}"
RAW="${FASTDOC_RAW:-https://raw.githubusercontent.com/$REPO/$BRANCH}"

BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

SET_DEFAULT=0
for arg in "$@"; do
    case "$arg" in
        --default) SET_DEFAULT=1 ;;
        *) echo "Bilinmeyen seçenek: $arg (geçerli: --default)" >&2; exit 2 ;;
    esac
done

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

# 2) Program ve logo (dosya olarak çalıştırıldıysa ve yanında varsa oradan, yoksa GitHub'dan)
SRC_DIR=""
if [ -f "$0" ]; then SRC_DIR="$(cd "$(dirname "$0")" && pwd)"; fi

fetch() {  # fetch <repo-içi-yol> <hedef>
    if [ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/$1" ]; then
        cp "$SRC_DIR/$1" "$2"
    else
        say "İndiriliyor: $RAW/$1"
        curl -fsSL "$RAW/$1" -o "$2"
    fi
}

fetch fastdoc.py "$BIN_DIR/fastdoc.tmp"
fetch assets/logo.svg "$ICON_DIR/fastdoc.svg"
chmod +x "$BIN_DIR/fastdoc.tmp"
mv "$BIN_DIR/fastdoc.tmp" "$BIN_DIR/fastdoc"      # çalışan kopyayı bozmadan değiştir

# 3) Masaüstü girişi ("Birlikte aç" listesine PDF uygulaması olarak ekler)
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

# 4) Varsayılan PDF uygulaması: yalnızca istenirse
if [ "$SET_DEFAULT" = "1" ]; then
    xdg-mime default fastdoc.desktop application/pdf
    say "Varsayılan PDF uygulaması: $(xdg-mime query default application/pdf)"
else
    say "Varsayılan PDF uygulaması DEĞİŞTİRİLMEDİ. İstersen: fastdoc --set-default"
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) say "Not: $BIN_DIR PATH'te değil; terminalden 'fastdoc' için oturumu yeniden aç." ;;
esac

say "Kuruldu. Uygulama menüsünden aç, PDF'e sağ tık > FastDoc ile aç ya da: fastdoc dosya.pdf"
