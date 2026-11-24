#!/usr/bin/python3
"""FastDoc - çok hafif PDF görüntüleyici (GTK3 + Poppler).

Sürekli kaydırma, açılıp kapanan sayfa listesi (küçük resimler), sayfa numarası
yazıp gitme ve yakınlaştırma (butonlar, dokunmatik pinch, Ctrl+tekerlek).
"""
import sys
from bisect import bisect_right
from collections import OrderedDict

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Poppler", "0.18")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Poppler  # noqa: E402

ZOOM_MIN, ZOOM_MAX, ZOOM_STEP = 0.2, 6.0, 1.25
PAD = 8                      # sayfalar arası boşluk (px)
BG = (0.82, 0.82, 0.84)
CACHE_BYTES = 64 * 1024 * 1024
THUMB_W, THUMB_LABEL = 120, 20


class ScrollArea(Gtk.DrawingArea, Gtk.Scrollable):
    """Kaydırılabilir çizim alanı. Dev bir widget yerine yalnızca görünen
    kısmı çizer; kaydırma/kinetik dokunmatik kaydırma ScrolledWindow'dan gelir."""

    hadjustment = GObject.Property(type=Gtk.Adjustment)
    vadjustment = GObject.Property(type=Gtk.Adjustment)
    hscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    vscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)

    def __init__(self):
        super().__init__()
        for name in ("hadjustment", "vadjustment"):
            self.connect(f"notify::{name}", self._adj_set, name)

    def _adj_set(self, _w, _pspec, name):
        adj = self.get_property(name)
        if adj:
            adj.connect("value-changed", self._on_scrolled)
            self.sync()

    def _on_scrolled(self, _adj):
        self.queue_draw()
        self.scrolled()

    def scrolled(self):
        pass

    def content_size(self):
        return 0, 0

    def do_size_allocate(self, alloc):
        Gtk.DrawingArea.do_size_allocate(self, alloc)
        self.sync()

    def sync(self, hval=None, vval=None):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        cw, ch = self.content_size()
        for adj, val, size, total in ((self.hadjustment, hval, w, cw), (self.vadjustment, vval, h, ch)):
            if adj:
                adj.configure(adj.get_value() if val is None else val,
                              0, max(total, size), 40, size * 0.9, size)
        self.queue_draw()


class PageView(ScrollArea):
    """Sayfaları alt alta, kesintisiz gösterir."""

    def __init__(self, on_page, on_zoom):
        super().__init__()
        self.on_page, self.on_zoom = on_page, on_zoom
        self.doc, self.sizes, self.tops = None, [], []
        self.zoom, self.maxw, self.total_h = 1.0, 0.0, 0
        self.cur, self._jump = 0, False
        self.cache, self.cache_bytes = OrderedDict(), 0

    def load(self, doc, sizes):
        self.doc, self.sizes = doc, sizes
        self.cache.clear()
        self.cache_bytes = 0
        self.layout()
        self.sync(0, 0)
        self._set_cur(0)

    def layout(self):
        z, y, tops = self.zoom, PAD, []
        for _, h in self.sizes:
            tops.append(y)
            y += h * z + PAD
        self.tops, self.total_h = tops, y
        self.maxw = max((w for w, _ in self.sizes), default=0) * z

    def content_size(self):
        return (int(self.maxw) + 2 * PAD, int(self.total_h)) if self.doc else (0, 0)

    def fit_width(self):
        if self.doc:
            parent = self.get_parent()      # dikey çubuğun payını hesaba kat
            bar = parent.get_vscrollbar().get_preferred_width()[1] + parent.style_get_property("scrollbar-spacing")
            avail = parent.get_allocated_width() - bar
            self.set_zoom((avail - 2 * PAD) / max(w for w, _ in self.sizes))

    def set_zoom(self, z, ax=None, ay=None):
        z = max(ZOOM_MIN, min(ZOOM_MAX, z))
        if not self.doc or abs(z - self.zoom) < 1e-6:
            return
        aw, ah = self.get_allocated_width(), self.get_allocated_height()
        ax = aw / 2 if ax is None else ax
        ay = ah / 2 if ay is None else ay
        cw, ch = self.content_size()
        fx = (self.hadjustment.get_value() + ax - max(0, (aw - cw) / 2)) / max(cw, 1)
        fy = (self.vadjustment.get_value() + ay) / max(ch, 1)
        self.zoom = z
        self.cache.clear()
        self.cache_bytes = 0
        self.layout()
        cw, ch = self.content_size()
        self._jump = True
        self.sync(fx * cw + max(0, (aw - cw) / 2) - ax, fy * ch - ay)
        self._jump = False
        self.on_zoom(z)
        self.update_current()

    def goto(self, n):
        if not self.doc:
            return
        n = max(0, min(n, len(self.sizes) - 1))
        self._jump = True
        self.sync(vval=self.tops[n] - PAD)
        self._jump = False
        self._set_cur(n)

    def _set_cur(self, n):
        self.cur = n
        self.on_page(n)

    def scrolled(self):
        if not self._jump:
            self.update_current()

    def update_current(self):
        if not self.doc:
            return
        adj, ah = self.vadjustment, self.get_allocated_height()
        v = adj.get_value()
        if v <= 0:
            n = 0
        elif v + ah >= adj.get_upper() - 1:
            n = len(self.sizes) - 1
        else:
            n = max(0, bisect_right(self.tops, v + ah / 2) - 1)
        if n != self.cur:
            self._set_cur(n)

    def _surface(self, i, wz, hz, sx, sy):
        s = self.cache.get(i)
        if s:
            self.cache.move_to_end(i)
            return s
        if wz * hz * 4 > CACHE_BYTES // 2:      # çok büyük: önbelleğe alma
            return None
        s = cairo.ImageSurface(cairo.FORMAT_RGB24, wz, hz)
        c = cairo.Context(s)
        c.set_source_rgb(1, 1, 1)
        c.paint()
        c.scale(sx, sy)
        self.doc.get_page(i).render(c)
        self.cache[i] = s
        self.cache_bytes += wz * hz * 4
        while self.cache_bytes > CACHE_BYTES and len(self.cache) > 1:
            _, old = self.cache.popitem(last=False)
            self.cache_bytes -= old.get_width() * old.get_height() * 4
        return s

    def do_draw(self, cr):
        cr.set_source_rgb(*BG)
        cr.paint()
        if not self.doc:
            return False
        aw, ah = self.get_allocated_width(), self.get_allocated_height()
        v, hv = self.vadjustment.get_value(), self.hadjustment.get_value()
        xoff = max(0, (aw - int(self.maxw) - 2 * PAD) // 2) - hv
        i, n = max(0, bisect_right(self.tops, v) - 1), len(self.tops)
        while i < n and self.tops[i] < v + ah:
            w, h = self.sizes[i]
            wz, hz = max(1, round(w * self.zoom)), max(1, round(h * self.zoom))
            x = round(xoff + PAD + (self.maxw - w * self.zoom) / 2)
            y = round(self.tops[i] - v)
            sx, sy = wz / w, hz / h
            surf = self._surface(i, wz, hz, sx, sy)
            if surf:
                cr.set_source_surface(surf, x, y)
                cr.paint()
            else:
                cr.save()
                cr.translate(x, y)
                cr.rectangle(0, 0, wz, hz)
                cr.clip()
                cr.set_source_rgb(1, 1, 1)
                cr.paint()
                cr.scale(sx, sy)
                self.doc.get_page(i).render(cr)
                cr.restore()
            i += 1
        return False


class Thumbs(ScrollArea):
    """Sol taraftaki sayfa listesi; yalnızca görünen küçük resimleri çizer."""

    def __init__(self, on_pick):
        super().__init__()
        self.on_pick = on_pick
        self.doc, self.sizes, self.tops, self.heights = None, [], [], []
        self.total, self.cur = 0, 0
        self.cache = OrderedDict()
        self.click = Gtk.GestureMultiPress.new(self)
        self.click.connect("released", self._released)

    def load(self, doc, sizes):
        self.doc, self.sizes, self.cur = doc, sizes, 0
        self.cache.clear()
        y, self.tops, self.heights = PAD, [], []
        for w, h in sizes:
            th = max(1, round(h * THUMB_W / w))
            self.tops.append(y)
            self.heights.append(th)
            y += th + THUMB_LABEL + PAD
        self.total = y
        self.sync(0, 0)

    def content_size(self):
        return THUMB_W + 2 * PAD, self.total

    def set_current(self, n):
        self.cur = n
        if self.doc and self.vadjustment:
            v, ah = self.vadjustment.get_value(), self.get_allocated_height()
            top, bottom = self.tops[n] - PAD, self.tops[n] + self.heights[n] + THUMB_LABEL + PAD
            if top < v or bottom > v + ah:
                self.vadjustment.set_value(top - (ah - (bottom - top)) / 2)
        self.queue_draw()

    def _released(self, _g, _n, _x, y):
        if self.doc:
            i = bisect_right(self.tops, self.vadjustment.get_value() + y) - 1
            if 0 <= i < len(self.tops):
                self.on_pick(i)

    def _thumb(self, i, th):
        s = self.cache.get(i)
        if s:
            self.cache.move_to_end(i)
            return s
        w, h = self.sizes[i]
        s = cairo.ImageSurface(cairo.FORMAT_RGB24, THUMB_W, th)
        c = cairo.Context(s)
        c.set_source_rgb(1, 1, 1)
        c.paint()
        c.scale(THUMB_W / w, th / h)
        self.doc.get_page(i).render(c)
        self.cache[i] = s
        if len(self.cache) > 80:
            self.cache.popitem(last=False)
        return s

    def do_draw(self, cr):
        cr.set_source_rgb(0.93, 0.93, 0.94)
        cr.paint()
        if not self.doc:
            return False
        aw, ah = self.get_allocated_width(), self.get_allocated_height()
        v = self.vadjustment.get_value()
        x = max(PAD, (aw - THUMB_W) // 2)
        cr.set_font_size(11)
        i, n = max(0, bisect_right(self.tops, v) - 1), len(self.tops)
        while i < n and self.tops[i] < v + ah:
            th, y = self.heights[i], round(self.tops[i] - v)
            if i == self.cur:
                cr.set_source_rgb(0.2, 0.5, 0.9)
                cr.rectangle(x - 4, y - 4, THUMB_W + 8, th + THUMB_LABEL + 8)
                cr.fill()
            cr.set_source_surface(self._thumb(i, th), x, y)
            cr.paint()
            cr.set_source_rgb(*((1, 1, 1) if i == self.cur else (0.2, 0.2, 0.25)))
            txt = str(i + 1)
            cr.move_to(x + (THUMB_W - cr.text_extents(txt).x_advance) / 2, y + th + 14)
            cr.show_text(txt)
            i += 1
        return False


class FastDoc(Gtk.Window):
    def __init__(self):
        super().__init__(title="FastDoc")
        self.set_default_size(1000, 700)
        self._pinch_base = 1.0

        # --- araç çubuğu ---
        bar = self.bar = Gtk.HeaderBar(show_close_button=True, title="FastDoc")
        self.set_titlebar(bar)

        self.side_btn = Gtk.ToggleButton(active=True)
        self.side_btn.set_image(Gtk.Image.new_from_icon_name("view-list-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
        self.side_btn.connect("toggled", lambda b: self.side.set_visible(b.get_active()))
        open_btn = self._icon_button("document-open-symbolic", lambda *_: self.open_dialog())
        bar.pack_start(self.side_btn)
        bar.pack_start(open_btn)

        nav = Gtk.Box(spacing=4)
        self.prev_btn = self._icon_button("go-previous-symbolic", lambda *_: self.view.goto(self.view.cur - 1))
        self.next_btn = self._icon_button("go-next-symbolic", lambda *_: self.view.goto(self.view.cur + 1))
        self.page_entry = Gtk.Entry(width_chars=4, max_width_chars=6, xalign=0.5)
        self.page_entry.connect("activate", self.on_page_entry)
        self.total_label = Gtk.Label(label="/ 0")
        for w in (self.prev_btn, self.page_entry, self.total_label, self.next_btn):
            nav.pack_start(w, False, False, 0)
        bar.pack_start(nav)

        zoom_box = Gtk.Box(spacing=4)
        self.zoom_label = Gtk.Label(label="100%", width_chars=5)
        for w in (
            self._icon_button("zoom-out-symbolic", lambda *_: self.zoom_by(1 / ZOOM_STEP)),
            self.zoom_label,
            self._icon_button("zoom-in-symbolic", lambda *_: self.zoom_by(ZOOM_STEP)),
            self._icon_button("zoom-fit-best-symbolic", lambda *_: self.view.fit_width()),
        ):
            zoom_box.pack_start(w, False, False, 0)
        bar.pack_end(zoom_box)

        # --- gövde: sol sayfa listesi + sayfa alanı ---
        self.thumbs = Thumbs(lambda i: self.view.goto(i))
        self.side = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, width_request=THUMB_W + 2 * PAD + 14)
        self.side.add(self.thumbs)

        self.view = PageView(self.on_page, self.on_zoom)
        self.scroll = Gtk.ScrolledWindow(overlay_scrolling=False)
        self.scroll.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.scroll.connect("scroll-event", self.on_scroll)
        self.scroll.add(self.view)

        body = Gtk.Box()
        body.pack_start(self.side, False, False, 0)
        body.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        body.pack_start(self.scroll, True, True, 0)
        self.add(body)

        # dokunmatik pinch
        self.pinch = Gtk.GestureZoom.new(self.scroll)
        self.pinch.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.pinch.connect("begin", lambda *_: setattr(self, "_pinch_base", self.view.zoom))
        self.pinch.connect("scale-changed", self.on_pinch)

        self.connect("key-press-event", self.on_key)
        self.connect("destroy", Gtk.main_quit)
        self.on_page(0)

    # ---------- yardımcılar ----------
    def _icon_button(self, icon, cb):
        b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        b.connect("clicked", cb)
        return b

    def open_dialog(self):
        dlg = Gtk.FileChooserDialog(title="PDF aç", parent=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("İptal", Gtk.ResponseType.CANCEL, "Aç", Gtk.ResponseType.OK)
        flt = Gtk.FileFilter()
        flt.set_name("PDF")
        flt.add_mime_type("application/pdf")
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.OK:
            self.load(dlg.get_filename())
        dlg.destroy()

    def load(self, path):
        try:
            doc = Poppler.Document.new_from_file(Gio.File.new_for_path(path).get_uri(), None)
        except GLib.Error as e:
            msg = Gtk.MessageDialog(parent=self, message_type=Gtk.MessageType.ERROR,
                                    buttons=Gtk.ButtonsType.CLOSE, text="PDF açılamadı")
            msg.format_secondary_text(e.message)
            msg.run()
            msg.destroy()
            return
        sizes = []
        for i in range(doc.get_n_pages()):
            page = doc.get_page(i)
            sizes.append(page.get_size() if page else (612.0, 792.0))
        name = path.rsplit("/", 1)[-1]
        self.set_title(name)
        self.bar.set_title(name)
        self.view.zoom = 1.0
        self.view.load(doc, sizes)
        self.thumbs.load(doc, sizes)
        self.total_label.set_text(f"/ {len(sizes)}")
        self.view.fit_width()
        self.view.goto(0)

    # ---------- geri çağrılar ----------
    def on_page(self, n):
        total = len(self.view.sizes)
        if not self.page_entry.has_focus():
            self.page_entry.set_text(str(n + 1) if total else "")
        self.prev_btn.set_sensitive(total > 0 and n > 0)
        self.next_btn.set_sensitive(total > 0 and n < total - 1)
        self.thumbs.set_current(n)

    def on_zoom(self, z):
        self.zoom_label.set_text(f"{round(z * 100)}%")

    def on_page_entry(self, entry):
        try:
            self.view.goto(int(entry.get_text()) - 1)
        except ValueError:
            self.on_page(self.view.cur)
        self.view.grab_focus()

    def zoom_by(self, f):
        self.view.set_zoom(self.view.zoom * f)

    def on_pinch(self, gesture, scale):
        ok, x, y = gesture.get_bounding_box_center()
        self.view.set_zoom(self._pinch_base * scale, x if ok else None, y if ok else None)

    def on_scroll(self, _w, ev):
        if not ev.state & Gdk.ModifierType.CONTROL_MASK:
            return False
        ok, _, dy = ev.get_scroll_deltas()
        if not ok:
            dy = {Gdk.ScrollDirection.UP: -1, Gdk.ScrollDirection.DOWN: 1}.get(ev.direction, 0)
        if dy:
            self.view.set_zoom(self.view.zoom * (ZOOM_STEP if dy < 0 else 1 / ZOOM_STEP), ev.x, ev.y)
        return True

    def on_key(self, _w, ev):
        if self.page_entry.has_focus():
            return False
        k = Gdk.keyval_name(ev.keyval)
        adj = self.view.vadjustment
        if ev.state & Gdk.ModifierType.CONTROL_MASK and k == "o":
            self.open_dialog()
        elif k == "F9":
            self.side_btn.set_active(not self.side_btn.get_active())
        elif k in ("plus", "equal", "KP_Add"):
            self.zoom_by(ZOOM_STEP)
        elif k in ("minus", "KP_Subtract"):
            self.zoom_by(1 / ZOOM_STEP)
        elif k in ("0", "KP_0"):
            self.view.fit_width()
        elif k in ("Page_Down", "Right"):
            self.view.goto(self.view.cur + 1)
        elif k in ("Page_Up", "Left"):
            self.view.goto(self.view.cur - 1)
        elif k == "Home":
            self.view.goto(0)
        elif k == "End":
            self.view.goto(len(self.view.sizes) - 1)
        elif k == "Down":
            adj.set_value(adj.get_value() + 60)
        elif k == "Up":
            adj.set_value(adj.get_value() - 60)
        elif k == "space":
            adj.set_value(adj.get_value() + adj.get_page_size() * 0.9)
        else:
            return False
        return True


def main():
    win = FastDoc()
    win.show_all()
    if len(sys.argv) > 1:
        GLib.idle_add(win.load, sys.argv[1])
    Gtk.main()


if __name__ == "__main__":
    main()
