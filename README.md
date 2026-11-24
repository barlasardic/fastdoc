<p align="center"><img src="assets/logo.svg" width="96" alt="FastDoc logo"></p>

<h1 align="center">FastDoc</h1>

[English](README.md) | [Türkçe](README.tr.md)

A very lightweight PDF viewer (Python + GTK3 + Poppler), built for smart boards and low-end machines running Pardus and other Debian-based systems.

- **Continuous scrolling** with a collapsible page thumbnail sidebar
- **Zoom** with buttons, touch pinch, or Ctrl+wheel
- **Jump to page** by typing a page number
- Single file, no pip dependencies, **0% CPU when idle**

## Why

Every PDF viewer we tried on our Pardus smart board lagged, even the ones that are supposed to be lightweight. FastDoc exists to fix that: it does only what a board needs (read, scroll, zoom, jump to a page) and nothing more.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/barlasardic/fastdoc/main/install.sh | sh
```

The script:
- Installs `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0` and `gir1.2-poppler-0.18` with `apt` if missing (asks for sudo).
- Installs the program as `~/.local/bin/fastdoc` and adds it (with its logo) to the application menu and the "Open with" list for PDFs.
- Does **not** change your default PDF application.

Make FastDoc the default PDF viewer (optional):

```sh
fastdoc --set-default
```

(or install with `... | sh -s -- --default`)

## Update

```sh
fastdoc --update
```

Checks the latest version on GitHub and reinstalls only if there is a newer one. Nothing is checked or downloaded at normal startup. Re-running the install command also works.

## Uninstall

```sh
curl -fsSL https://raw.githubusercontent.com/barlasardic/fastdoc/main/uninstall.sh | sh
```

## Usage

```sh
fastdoc file.pdf
```

| Action | How |
|---|---|
| Scroll | Pages flow continuously: mouse wheel, touch scrolling, `↑` `↓`, space |
| Page sidebar (left) | Toggle with the button or `F9`; tap a thumbnail to jump to that page |
| Go to page | Type a number in the box + Enter, arrow buttons, `PgUp`/`PgDn`, `Home`/`End` |
| Zoom in / out | `+` / `-` buttons, `+` `-` keys, Ctrl+wheel, touch pinch |
| Fit to width | Button or `0` |
| Open file | Button or Ctrl+O |

## Lightweight by design

- One file (`fastdoc.py`) using only the system's GTK3, Poppler and cairo.
- Only the pages visible on screen are rendered; the rendered-page cache is capped at 64 MB.
- No timers or polling loops, so it uses no CPU while idle.
- Measured on a 123-page PDF: about 91 MB RAM after opening, 109 MB after scrolling the whole document (a bare GTK window is ~67 MB).

## Requirements

Debian-based system (Pardus, Debian, Ubuntu) with Python 3 and GTK 3. The installer takes care of the rest.

> The interface is currently in Turkish.
