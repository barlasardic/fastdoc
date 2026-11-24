# FastDoc

[English](README.md) | **Türkçe**

Çok hafif PDF görüntüleyici (Python + GTK3 + Poppler). Pardus ve diğer Debian tabanlı sistemler için yapıldı.

## Kurulum

```sh
curl -fsSL https://raw.githubusercontent.com/barlasardic/fastdoc/main/install.sh | sh
```

Betik şunları yapar:
- Eksikse `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0`, `gir1.2-poppler-0.18` paketlerini `apt` ile kurar (sudo ister).
- Programı `~/.local/bin/fastdoc` olarak kurar.
- Uygulama menüsüne ekler ve **varsayılan PDF uygulaması** yapar. PDF'e çift tıklayınca FastDoc açılır.

Kaldırma: `curl -fsSL https://raw.githubusercontent.com/barlasardic/fastdoc/main/uninstall.sh | sh`

## Kullanım

```sh
fastdoc dosya.pdf
```

| İşlem | Nasıl |
|---|---|
| Gezinme | Sayfalar alt alta kesintisiz akar; tekerlek, dokunmatik kaydırma, `↑` `↓`, boşluk |
| Sayfa listesi (sol) | Buton veya `F9` ile aç/kapat; küçük resme dokununca o sayfaya gider |
| Sayfaya git | Kutuya numara yaz + Enter, ok butonları, `PgUp`/`PgDn`, `Home`/`End` |
| Yakınlaştır / uzaklaştır | `+` / `-` butonları, `+` `-` tuşları, Ctrl+tekerlek, dokunmatik pinch |
| Genişliğe sığdır | Buton veya `0` |
| Aç | Buton veya Ctrl+O |

## Hafiflik

- Tek dosya (`fastdoc.py`), ek pip bağımlılığı yok; sadece sistemdeki GTK3, Poppler ve cairo.
- Yalnızca ekranda görünen sayfalar çizilir; çizilmiş sayfa önbelleği 64 MB ile sınırlıdır.
- Boştayken CPU kullanmaz (zamanlayıcı/döngü yok).
