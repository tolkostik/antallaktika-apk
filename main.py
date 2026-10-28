"""
Ανταλλακτικά & αναλώσιμα – για τα δικά μου αυτοκίνητα.
"""
import threading
import webbrowser

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import platform

import check as C
import garage as G

IS_ANDROID = platform == "android"
Window.clearcolor = (0.95, 0.955, 0.96, 1)
INK = (0.11, 0.14, 0.2, 1)
GREY = "#6B7486"
LEVEL = {"late": ("#B4461B", "ΕΠΕΙΓΕΙ"), "soon": ("#C98A00", "ΣΥΝΤΟΜΑ"), "ok": ("#0F7B4F", "ΟΚ"),
         "unknown": ("#6B7486", "ΧΩΡΙΣ ΙΣΤΟΡΙΚΟ")}

KV = """
#:import dp kivy.metrics.dp

<Txt>:
    size_hint_y: None
    markup: True
    color: 0.11, 0.14, 0.2, 1
    halign: 'left'
    valign: 'top'
    text_size: self.width - dp(24), None
    height: self.texture_size[1] + dp(12)
    padding: dp(12), dp(6)

<Card>:
    size_hint_y: None
    markup: True
    color: 0.11, 0.14, 0.2, 1
    halign: 'left'
    valign: 'middle'
    text_size: self.width - dp(36), None
    height: max(self.texture_size[1] + dp(22), dp(58))
    padding: dp(18), dp(10)
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.x + dp(6), self.y + dp(3)
            size: self.width - dp(12), self.height - dp(6)
            radius: [dp(10)]

<Btn>:
    size_hint_y: None
    height: dp(50)
    bold: True
    background_normal: ''
    background_color: self.bg
    color: self.fg

<Root>:
    orientation: 'vertical'
    BoxLayout:
        size_hint_y: None
        height: dp(54)
        padding: dp(6), dp(6)
        spacing: dp(6)
        canvas.before:
            Color:
                rgba: 0.11, 0.14, 0.2, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Button:
            id: back
            text: '<'
            bold: True
            font_size: '22sp'
            size_hint_x: None
            width: dp(48)
            background_normal: ''
            background_color: 0.18, 0.22, 0.3, 1
            on_release: app.back()
        Label:
            id: title
            text: 'Ανταλλακτικά'
            bold: True
            font_size: '18sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            shorten: True
    ScrollView:
        id: scroll
        do_scroll_x: False
        BoxLayout:
            id: page
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: dp(6), dp(8)
            spacing: dp(4)
    BoxLayout:
        size_hint_y: None
        height: dp(54)
        Button:
            text: 'Αυτοκίνητα'
            background_normal: ''
            background_color: 0.11, 0.14, 0.2, 1
            on_release: app.home('vehicles')
        Button:
            text: 'Αναζήτηση'
            background_normal: ''
            background_color: 0.11, 0.14, 0.2, 1
            on_release: app.home('search')
        Button:
            text: 'Υπενθυμίσεις'
            background_normal: ''
            background_color: 0.11, 0.14, 0.2, 1
            on_release: app.home('reminders')
        Button:
            text: 'Αντίγραφα'
            background_normal: ''
            background_color: 0.11, 0.14, 0.2, 1
            on_release: app.home('backup')
"""


class Txt(Label):
    pass


class Card(ButtonBehavior, Label):
    bg = ListProperty([1, 1, 1, 1])


class Btn(Button):
    bg = ListProperty([0.95, 0.71, 0.14, 1])
    fg = ListProperty([0.11, 0.14, 0.2, 1])


class Root(BoxLayout):
    pass


Builder.load_string(KV)

AMBER = [0.95, 0.71, 0.14, 1]
BLUE = [0.15, 0.39, 0.79, 1]
GREEN = [0.06, 0.48, 0.31, 1]
RED = [0.7, 0.2, 0.15, 1]
LIGHT = [0.86, 0.87, 0.9, 1]
WHITE_TXT = [1, 1, 1, 1]


def esc(t):
    return str(t).replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")


def euro(x):
    return f"{x:.2f}".replace(".", ",") + " €"


def km(x):
    return f"{G.to_int(x):,}".replace(",", ".") + " χλμ"


class AntallaktikaApp(App):
    title = "Antallaktika"

    def build(self):
        G.set_dir(self.user_data_dir)
        self.d = G.load()
        self.root_w = Root()
        self.stack = []
        Window.bind(on_keyboard=self._key)
        self.home("vehicles")
        return self.root_w

    def on_pause(self):
        return True

    # ------------------------------------------------------------ πλοήγηση
    @property
    def page(self):
        return self.root_w.ids.page

    def go(self, fn, *args, push=True):
        if push and self.stack and self.stack[-1] == (fn, args):
            push = False
        if push:
            self.stack.append((fn, args))
        self.page.clear_widgets()
        self.root_w.ids.scroll.scroll_y = 1
        getattr(self, "pg_" + fn)(*args)

    def home(self, fn):
        self.stack = []
        self.go(fn)

    def back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            fn, args = self.stack[-1]
            self.go(fn, *args, push=False)
            return True
        return False

    def reload(self):
        fn, args = self.stack[-1]
        self.go(fn, *args, push=False)

    def _key(self, win, key, *a):
        if key == 27:
            return self.back()
        return False

    def set_title(self, t):
        self.root_w.ids.title.text = t

    # ------------------------------------------------------------ βοηθητικά widgets
    def txt(self, t, **kw):
        w = Txt(text=t, **kw)
        self.page.add_widget(w)
        return w

    def card(self, t, cb=None, bg=None):
        c = Card(text=t, bg=bg or [1, 1, 1, 1])
        if cb:
            c.bind(on_release=lambda *a: cb())
        self.page.add_widget(c)
        return c

    def btn(self, t, cb, bg=None, fg=None, parent=None):
        b = Btn(text=t, bg=bg or AMBER, fg=fg or [0.11, 0.14, 0.2, 1])
        b.bind(on_release=lambda *a: cb())
        (parent or self.page).add_widget(b)
        return b

    def row(self, *widgets, h=50):
        r = BoxLayout(size_hint_y=None, height=dp(h), spacing=dp(6), padding=(dp(6), 0))
        for w in widgets:
            r.add_widget(w)
        self.page.add_widget(r)
        return r

    def field(self, label, value="", hint="", numeric=False, multiline=False, h=50):
        self.page.add_widget(Txt(text=f"[size=13sp][color={GREY}]{label}[/color][/size]"))
        ti = TextInput(text=str(value or ""), hint_text=hint, multiline=multiline, size_hint_y=None,
                       height=dp(h), input_filter="float" if numeric else None, font_size="16sp")
        box = BoxLayout(size_hint_y=None, height=dp(h), padding=(dp(8), 0))
        box.add_widget(ti)
        self.page.add_widget(box)
        return ti

    def choice(self, label, value, values):
        self.page.add_widget(Txt(text=f"[size=13sp][color={GREY}]{label}[/color][/size]"))
        sp = Spinner(text=value or values[0], values=values, size_hint_y=None, height=dp(48))
        box = BoxLayout(size_hint_y=None, height=dp(48), padding=(dp(8), 0))
        box.add_widget(sp)
        self.page.add_widget(box)
        return sp

    def open_url(self, url):
        webbrowser.open(url)

    def share(self, text, subject):
        if not IS_ANDROID:
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(text)
            except Exception:  # noqa: BLE001
                pass
            return
        from jnius import autoclass, cast
        Intent = autoclass("android.content.Intent")
        String = autoclass("java.lang.String")
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        i = Intent(Intent.ACTION_SEND)
        i.setType("text/plain")
        i.putExtra(Intent.EXTRA_SUBJECT, cast("java.lang.CharSequence", String(subject)))
        i.putExtra(Intent.EXTRA_TEXT, cast("java.lang.CharSequence", String(text)))
        act.startActivity(Intent.createChooser(i, cast("java.lang.CharSequence", String(subject))))

    # ------------------------------------------------------------ αυτοκίνητα
    def pg_vehicles(self):
        self.set_title("Τα αυτοκίνητά μου")
        vs = self.d["vehicles"]
        if not vs:
            self.txt("Πρόσθεσε το πρώτο σου αυτοκίνητο. Μπορείς να ξεκινήσεις από τον [b]αριθμό πλαισίου[/b] (VIN) "
                     "που γράφει η άδεια κυκλοφορίας, στο πεδίο E.")
        for v in vs:
            late = [r for r in G.reminders(self.d, v["id"]) if r[2][0] in ("late", "soon")]
            warn = f"\n[color=#B4461B][b]{len(late)} αλλαγές επείγουν ή πλησιάζουν[/b][/color]" if late else ""
            self.card(f"[b][size=17sp]{esc(G.vehicle_title(v))}[/size][/b]\n[size=13sp][color={GREY}]"
                      f"{esc(G.vehicle_sub(v))}[/color][/size]\n{km(v.get('km', 0))}{warn}",
                      lambda vid=v["id"]: self.go("vehicle", vid))
        self.btn("+ ΝΕΟ ΑΥΤΟΚΙΝΗΤΟ", lambda: self.go("vehicle_form", None))
        self.btn("+ ΑΠΟ ΑΡΙΘΜΟ ΠΛΑΙΣΙΟΥ (VIN)", lambda: self.go("vin"), bg=BLUE, fg=WHITE_TXT)
        self.btn("ΕΛΕΓΧΟΣ ΜΕΤΑΧΕΙΡΙΣΜΕΝΟΥ ΠΡΙΝ ΤΗΝ ΑΓΟΡΑ", lambda: self.go("checks"), bg=GREEN, fg=WHITE_TXT)

    def pg_vin(self):
        self.set_title("Αριθμός πλαισίου")
        self.txt("Γράψε τα 17 ψηφία του αριθμού πλαισίου (άδεια κυκλοφορίας, πεδίο E, ή στο κάτω μέρος του "
                 "παρμπρίζ).")
        vin = self.field("Αριθμός πλαισίου (VIN)", hint="π.χ. WVWZZZ1KZBW123456")
        msg = self.txt("")

        def decode():
            msg.text = "Αποκωδικοποίηση…"
            code = vin.text.strip().upper()

            def work():
                info, notes = G.decode_vin(code)
                Clock.schedule_once(lambda dt: done(info, notes))

            def done(info, notes):
                if not info:
                    msg.text = f"[color=#B4461B]{esc(notes[0])}[/color]"
                    return
                self.go("vehicle_form", None, info, notes)
            threading.Thread(target=work, daemon=True).start()
        self.btn("ΑΠΟΚΩΔΙΚΟΠΟΙΗΣΗ", decode)

    def pg_vehicle_form(self, vid=None, prefill=None, notes=None):
        v = dict(G.vehicle(self.d, vid) or {}) if vid else {}
        if prefill:
            for k, val in prefill.items():
                if val and not v.get(k):
                    v[k] = val
        self.set_title("Επεξεργασία αυτοκινήτου" if vid else "Νέο αυτοκίνητο")
        if prefill:
            info = [f"Κατασκευαστής: [b]{esc(prefill.get('brand') or '—')}[/b]",
                    f"Χώρα: {esc(prefill.get('country') or '—')}"]
            for k, lbl in (("body", "Αμάξωμα"), ("plant", "Εργοστάσιο"), ("trim", "Έκδοση")):
                if prefill.get(k):
                    info.append(f"{lbl}: {esc(prefill[k])}")
            self.card("\n".join(info) + ("\n[size=13sp][color=#C98A00]" + "\n".join(esc(n) for n in notes or [])
                                         + "[/color][/size]" if notes else ""), bg=[0.92, 0.95, 1, 1])
        f = {
            "nickname": self.field("Όνομα (προαιρετικό)", v.get("nickname"), "π.χ. Το Golf"),
            "brand": self.field("Μάρκα", v.get("brand"), "π.χ. Volkswagen"),
            "model": self.field("Μοντέλο", v.get("model"), "π.χ. Golf VI"),
            "year": self.field("Έτος", v.get("year"), numeric=True),
            "engine_desc": self.field("Κινητήρας", v.get("engine_desc"), "π.χ. 1.6 TDI 105 hp"),
            "engine_code": self.field("Κωδικός κινητήρα", v.get("engine_code"), "π.χ. CAYC (στο βιβλίο service)"),
        }
        fuel = self.choice("Καύσιμο", v.get("fuel") or "Βενζίνη", G.FUELS)
        f["vin"] = self.field("Αριθμός πλαισίου (VIN)", v.get("vin"))
        f["plate"] = self.field("Πινακίδα", v.get("plate"))
        kmf = self.field("Χιλιόμετρα τώρα", v.get("km", ""), numeric=True)
        plan = None
        if not vid:
            plan = CheckBox(active=True, size_hint_x=None, width=dp(44), color=INK)
            self.row(plan, Label(text="Δημιουργία βασικού πλάνου service (λάδια, φίλτρα, ιμάντας…)", color=INK,
                                 halign="left", valign="middle", text_size=(Window.width - dp(80), None)))

        def save():
            nv = dict(v)
            for k, w in f.items():
                nv[k] = w.text.strip()
            nv["fuel"] = fuel.text
            nv["km"] = G.to_int(kmf.text, 0)
            nv["km_date"] = G.today()
            for k in ("country", "year_guess", "body", "plant", "trim"):
                nv.pop(k, None)
            nv = G.upsert_vehicle(self.d, nv)
            if plan is not None and plan.active:
                G.add_base_plan(self.d, nv["id"])
            self.stack = [("vehicles", ())]
            self.go("vehicle", nv["id"])
        self.btn("ΑΠΟΘΗΚΕΥΣΗ", save)

    def pg_vehicle(self, vid):
        v = G.vehicle(self.d, vid)
        if not v:
            return self.home("vehicles")
        self.set_title(G.vehicle_title(v))
        self.card(f"[b][size=17sp]{esc(G.vehicle_title(v))}[/size][/b]\n{esc(G.vehicle_sub(v))}"
                  + (f"\nΠλαίσιο: {esc(v['vin'])}" if v.get("vin") else "")
                  + f"\n[b]{km(v.get('km', 0))}[/b] [size=12sp][color={GREY}](ενημέρωση {v.get('km_date', '-')})"
                    f"[/color][/size]", bg=[0.92, 0.95, 1, 1])
        kmi = TextInput(hint_text="Νέα χιλιόμετρα", input_filter="int", multiline=False)
        b = Btn(text="ΕΝΗΜΕΡΩΣΗ ΧΛΜ", bg=BLUE, fg=WHITE_TXT, size_hint_x=0.45)
        b.bind(on_release=lambda *a: (G.set_km(self.d, vid, kmi.text), self.reload()) if kmi.text else None)
        self.row(kmi, b)
        rems = [r for r in G.reminders(self.d, vid) if r[2][0] in ("late", "soon")]
        if rems:
            lines = [f"[color={LEVEL[r[0]][0]}][b]{LEVEL[r[0]][1]}[/b][/color] {esc(p['name'])}: {esc(r[1])}"
                     for _, p, r in rems]
            self.card("[b]Υπενθυμίσεις[/b]\n" + "\n".join(lines), bg=[1, 0.95, 0.9, 1])
        self.txt("[size=16sp][b]Ανταλλακτικά & αναλώσιμα[/b][/size]")
        for p in G.parts_of(self.d, vid):
            r = G.reminder(self.d, p, v)
            codes = ", ".join(p.get("oem", [])[:2])
            bp = G.best_price(p)
            sub = " · ".join(x for x in (codes and f"OEM {codes}", p.get("spec"),
                                         bp and f"από {euro(bp['price'])}") if x)
            st = f"\n[color={LEVEL[r[0]][0]}]{esc(r[1])}[/color]" if r and r[0] != "unknown" else ""
            self.card(f"[b]{esc(p['name'])}[/b]" + (f"  [size=12sp][color={GREY}]{esc(p['category'])}[/color][/size]"
                                                       if p["name"] != p["category"] else "")
                      + (f"\n[size=13sp]{esc(sub)}[/size]" if sub else "") + st,
                      lambda pid=p["id"]: self.go("part", pid, vid))
        self.btn("+ ΑΝΤΑΛΛΑΚΤΙΚΟ / ΑΝΑΛΩΣΙΜΟ", lambda: self.go("part_form", None, vid))
        self.btn("+ ΚΑΤΑΓΡΑΦΗ SERVICE / ΑΛΛΑΓΗΣ", lambda: self.go("service_form", vid), bg=GREEN, fg=WHITE_TXT)
        self.btn("ΙΣΤΟΡΙΚΟ SERVICE", lambda: self.go("history", vid), bg=BLUE, fg=WHITE_TXT)
        if v.get("vin"):
            self.btn("Έλεγχος ιστορικού & ανακλήσεων", lambda: self.go("check_from_vehicle", vid), bg=LIGHT)
        self.btn("Επεξεργασία στοιχείων", lambda: self.go("vehicle_form", vid), bg=LIGHT)
        self.btn("Προσθήκη βασικού πλάνου service", lambda: (G.add_base_plan(self.d, vid), self.reload()), bg=LIGHT)
        self.btn("Διαγραφή αυτοκινήτου", lambda: self.go("confirm", "vehicle", vid), bg=LIGHT, fg=RED)

    def pg_confirm(self, kind, oid, extra=None):
        self.set_title("Επιβεβαίωση")
        what = {"vehicle": "το αυτοκίνητο με όλα τα ανταλλακτικά και το ιστορικό του",
                "part": "αυτό το ανταλλακτικό", "service": "αυτή την καταγραφή service"}[kind]
        self.txt(f"Σίγουρα θέλεις να διαγράψεις {what};")

        def do():
            if kind == "vehicle":
                G.delete_vehicle(self.d, oid)
                self.home("vehicles")
            elif kind == "part":
                G.delete_part(self.d, oid)
                self.stack.pop()
                self.stack.pop()
                self.reload()
            else:
                G.delete_service(self.d, oid)
                self.back()
        self.btn("ΝΑΙ, ΔΙΑΓΡΑΦΗ", do, bg=RED, fg=WHITE_TXT)
        self.btn("Άκυρο", self.back, bg=LIGHT)

    # ------------------------------------------------------------ ανταλλακτικά
    def pg_part_form(self, pid, vid):
        p = dict(G.part(self.d, pid) or {}) if pid else {"category": "Άλλο", "vehicles": [vid]}
        self.set_title("Επεξεργασία ανταλλακτικού" if pid else "Νέο ανταλλακτικό")
        cat = self.choice("Κατηγορία", p.get("category"), G.CATEGORIES)
        name = self.field("Όνομα / περιγραφή", p.get("name"), "π.χ. Φίλτρο λαδιού")
        oem = self.field("Κωδικοί OEM (κατασκευαστή), με κόμμα", ", ".join(p.get("oem", [])), "π.χ. 03L115562")
        eq = self.field("Αντιστοιχίες: μία ανά γραμμή «Μάρκα κωδικός»", G.equiv_text(p.get("equiv", [])),
                        "MANN HU 7008 z\nBosch F026407079", multiline=True, h=110)
        hint = self.txt("")
        spec = self.field("Προδιαγραφή / ποσότητα", p.get("spec"), "π.χ. 5W-30 VW 507.00, 4,3 λίτρα")
        ikm = self.field("Αλλαγή κάθε … χλμ (0 = χωρίς)", p.get("interval_km", 0), numeric=True)
        imo = self.field("ή κάθε … μήνες (0 = χωρίς)", p.get("interval_months", 0), numeric=True)
        notes = self.field("Σημειώσεις", p.get("notes"), multiline=True, h=80)

        def check(*a):
            tmp = {"id": pid, "oem": G.parse_codes(oem.text), "equiv": G.parse_equiv(eq.text)}
            same = G.same_codes(self.d, tmp)
            if same:
                lst = [f"• {esc(q['name'])} – {esc(', '.join(G.vehicle_title(G.vehicle(self.d, x)) for x in q['vehicles'] if G.vehicle(self.d, x)))}"
                       for q in same[:5]]
                hint.text = "[color=#0F7B4F][b]Ίδιος κωδικός υπάρχει ήδη στη βάση σου:[/b][/color]\n" + "\n".join(lst)
            else:
                hint.text = ""
        oem.bind(text=check)
        eq.bind(text=check)
        check()

        def save():
            np = dict(p)
            np.update(category=cat.text, name=name.text.strip() or cat.text, oem=G.parse_codes(oem.text),
                      equiv=G.parse_equiv(eq.text), spec=spec.text.strip(), interval_km=G.to_int(ikm.text),
                      interval_months=G.to_int(imo.text), notes=notes.text.strip())
            np = G.upsert_part(self.d, np)
            self.stack.pop()
            if pid:
                self.reload()
            else:
                self.go("part", np["id"], vid)
        self.btn("ΑΠΟΘΗΚΕΥΣΗ", save)

    def pg_part(self, pid, vid):
        p = G.part(self.d, pid)
        v = G.vehicle(self.d, vid)
        if not p or not v:
            return self.back()
        self.set_title(p["name"])
        lines = [f"[b][size=17sp]{esc(p['name'])}[/size][/b]  [size=12sp][color={GREY}]{esc(p['category'])}"
                 f"[/color][/size]"]
        if p.get("oem"):
            lines.append("[b]OEM:[/b] " + esc(", ".join(p["oem"])))
        if p.get("spec"):
            lines.append("[b]Προδιαγραφή:[/b] " + esc(p["spec"]))
        iv = []
        if G.to_int(p.get("interval_km")):
            iv.append(km(p["interval_km"]))
        if G.to_int(p.get("interval_months")):
            iv.append(f"{p['interval_months']} μήνες")
        if iv:
            lines.append("[b]Αλλαγή κάθε:[/b] " + " ή ".join(iv))
        r = G.reminder(self.d, p, v)
        if r:
            lines.append(f"[color={LEVEL[r[0]][0]}][b]{LEVEL[r[0]][1]}[/b] {esc(r[1])}[/color]")
        if p.get("notes"):
            lines.append(f"[size=13sp][color={GREY}]{esc(p['notes'])}[/color][/size]")
        self.card("\n".join(lines), bg=[0.92, 0.95, 1, 1])

        self.txt("[size=16sp][b]Αντιστοιχίες[/b][/size]")
        if p.get("equiv"):
            self.card("\n".join(f"• [b]{esc(e['brand'])}[/b] {esc(e['code'])}" for e in p["equiv"]))
        else:
            self.txt(f"[color={GREY}]Καμία ακόμα. Πάτα «ΒΡΕΣ ΑΝΤΙΣΤΟΙΧΙΕΣ» και πρόσθεσε ό,τι βρεις.[/color]")
        same = G.same_codes(self.d, p)
        if same:
            self.card("[b]Ίδιο ανταλλακτικό και σε:[/b]\n" + "\n".join(
                f"• {esc(G.vehicle_title(G.vehicle(self.d, x)))}: {esc(q['name'])}"
                for q in same for x in q["vehicles"] if G.vehicle(self.d, x)), bg=[0.9, 0.97, 0.92, 1])

        links_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        links_box.bind(minimum_height=links_box.setter("height"))

        def show_links():
            links_box.clear_widgets()
            links = G.web_searches(p, v)
            if not p.get("oem"):
                links_box.add_widget(Txt(text="[color=#C98A00]Χωρίς κωδικό OEM η αναζήτηση γίνεται με το όνομα και "
                                              "το αυτοκίνητο. Αν βρεις τον κωδικό, γράψ' τον για ακριβέστερα "
                                              "αποτελέσματα.[/color]"))
            for t, u in links:
                b = Btn(text=t, bg=LIGHT, height=dp(46))
                b.bind(on_release=lambda w, url=u: self.open_url(url))
                links_box.add_widget(b)
        self.btn("ΒΡΕΣ ΑΝΤΙΣΤΟΙΧΙΕΣ & ΤΙΜΕΣ ΣΤΟ ΔΙΑΔΙΚΤΥΟ", show_links, bg=BLUE, fg=WHITE_TXT)
        self.page.add_widget(links_box)

        self.txt("[size=16sp][b]Τιμές & προμηθευτές[/b][/size]")
        prices = sorted(p.get("prices", []), key=lambda x: x["price"])
        if prices:
            best = prices[0]["price"]
            self.card("\n".join(
                f"• {esc(x['supplier'])}: [b]{euro(x['price'])}[/b] [size=12sp]({x['date']})[/size]"
                + ("  [color=#0F7B4F][b]φθηνότερο[/b][/color]" if x["price"] == best else "") for x in prices))
        sup = TextInput(hint_text="Προμηθευτής", multiline=False)
        pr = TextInput(hint_text="Τιμή €", input_filter="float", multiline=False, size_hint_x=0.5)
        self.row(sup, pr)
        self.btn("ΠΡΟΣΘΗΚΗ ΤΙΜΗΣ", lambda: (G.add_price(self.d, pid, sup.text, G.to_float(pr.text, 0.0)),
                                            self.reload()) if G.to_float(pr.text) else None, bg=GREEN, fg=WHITE_TXT)

        hist = [s for s in G.services_of(self.d, vid) if pid in s.get("parts", [])]
        if hist:
            self.txt("[size=16sp][b]Αλλαγές[/b][/size]")
            self.card("\n".join(f"• {s['date']} στα {km(s['km'])}" + (f" · {esc(s['where'])}" if s.get("where")
                                                                       else "") for s in hist))
        self.btn("Επεξεργασία", lambda: self.go("part_form", pid, vid), bg=LIGHT)
        self.btn("Διαγραφή", lambda: self.go("confirm", "part", pid), bg=LIGHT, fg=RED)

    # ------------------------------------------------------------ service
    def pg_service_form(self, vid):
        v = G.vehicle(self.d, vid)
        self.set_title("Καταγραφή service")
        date = self.field("Ημερομηνία", G.today())
        kmf = self.field("Χιλιόμετρα", v.get("km", ""), numeric=True)
        self.txt("[b]Τι άλλαξε;[/b]")
        checks = {}
        for p in G.parts_of(self.d, vid):
            cb = CheckBox(size_hint_x=None, width=dp(44), color=INK)
            self.row(cb, Label(text=p["name"], color=INK, halign="left", valign="middle",
                               text_size=(Window.width - dp(80), None)), h=44)
            checks[p["id"]] = cb
        cost = self.field("Κόστος €", "", numeric=True)
        where = self.field("Πού (συνεργείο / μόνος μου)")
        notes = self.field("Σημειώσεις", multiline=True, h=80)

        def save():
            ids = [pid for pid, cb in checks.items() if cb.active]
            G.add_service(self.d, vid, date.text.strip(), kmf.text, ids, cost.text, where.text, notes.text)
            self.back()
            self.reload()
        self.btn("ΑΠΟΘΗΚΕΥΣΗ", save, bg=GREEN, fg=WHITE_TXT)

    def pg_history(self, vid):
        v = G.vehicle(self.d, vid)
        self.set_title("Ιστορικό – " + G.vehicle_title(v))
        ss = G.services_of(self.d, vid)
        total = sum(s.get("cost", 0) for s in ss)
        self.card(f"[b]{len(ss)} καταγραφές[/b] · συνολικό κόστος [b]{euro(total)}[/b]", bg=[0.92, 0.95, 1, 1])
        for s in ss:
            names = [G.part(self.d, x)["name"] for x in s.get("parts", []) if G.part(self.d, x)]
            self.card(f"[b]{s['date']}[/b] · {km(s['km'])}" + (f" · {euro(s['cost'])}" if s.get("cost") else "")
                      + (f"\n{esc(', '.join(names))}" if names else "")
                      + (f"\n[size=13sp][color={GREY}]{esc(s['where'])}{' · ' + esc(s['notes']) if s.get('notes') else ''}"
                         f"[/color][/size]" if s.get("where") or s.get("notes") else ""),
                      lambda sid=s["id"]: self.go("confirm", "service", sid))
        if ss:
            self.txt(f"[size=12sp][color={GREY}]Πάτα μια καταγραφή για να τη διαγράψεις.[/color][/size]")


    # ------------------------------------------------------------ έλεγχος πριν την αγορά
    def pg_checks(self):
        self.set_title("Έλεγχος πριν την αγορά")
        self.txt("Έλεγξε ένα μεταχειρισμένο πριν δώσεις προκαταβολή: γνησιότητα πλαισίου, λογικά χιλιόμετρα, "
                 "ανακλήσεις, αναζήτηση ζημιών, επίσημοι έλεγχοι και λίστα επιτόπιου ελέγχου. Όλα δωρεάν.")
        self.btn("+ ΝΕΟΣ ΕΛΕΓΧΟΣ", lambda: self.go("check_form", None), bg=GREEN, fg=WHITE_TXT)
        for c in C.load_checks(self.d):
            ok, tot = C.checklist_score(c.get("states", {}))
            cl = c.get("claims", {})
            self.card(f"[b]{esc(' '.join(x for x in (cl.get('brand'), cl.get('model'), cl.get('year')) if x) or 'Έλεγχος')}"
                      f"[/b]\n[size=13sp]{esc(c['vin'])} · {c['date']} · λίστα {ok}/{tot}[/size]",
                      lambda cid=c["id"]: self.go("check", cid))

    def pg_check_from_vehicle(self, vid):
        v = G.vehicle(self.d, vid)
        chk = {"id": G.new_id(), "date": G.today(), "vin": v.get("vin", ""), "plate": v.get("plate", ""),
               "claims": {"brand": v.get("brand", ""), "model": v.get("model", ""), "year": v.get("year", ""),
                          "km": v.get("km", "")}, "states": {}, "notes": ""}
        C.save_check(self.d, chk)
        self.stack.pop()
        self.go("check", chk["id"])

    def pg_check_form(self, cid=None):
        c = next((x for x in C.load_checks(self.d) if x["id"] == cid), None) if cid else None
        c = c or {"claims": {}}
        cl = c.get("claims", {})
        self.set_title("Στοιχεία αυτοκινήτου")
        self.txt("Γράψε τον αριθμό πλαισίου (από την άδεια ΚΑΙ από το ίδιο το αυτοκίνητο) και ό,τι σου λέει ο "
                 "πωλητής. Η εφαρμογή θα ελέγξει αν συμφωνούν.")
        vin = self.field("Αριθμός πλαισίου (VIN)", c.get("vin"), "17 χαρακτήρες")
        plate = self.field("Πινακίδα (προαιρετικά)", c.get("plate"))
        brand = self.field("Μάρκα (κατά τον πωλητή)", cl.get("brand"))
        model = self.field("Μοντέλο", cl.get("model"))
        year = self.field("Έτος", cl.get("year"), numeric=True)
        kmf = self.field("Χιλιόμετρα (κατά τον πωλητή)", cl.get("km"), numeric=True)
        msg = self.txt("")

        def go():
            code = vin.text.strip().upper().replace(" ", "")
            info, err = G.vin_offline(code)
            if err:
                msg.text = f"[color=#B4461B]{esc(err)}[/color]"
                return
            chk = dict(c)
            chk.update(id=c.get("id") or G.new_id(), date=c.get("date") or G.today(), vin=code,
                       plate=plate.text.strip(), claims={"brand": brand.text.strip(), "model": model.text.strip(),
                                                         "year": year.text.strip(), "km": kmf.text.strip()})
            chk.setdefault("states", {})
            chk.setdefault("notes", "")
            C.save_check(self.d, chk)
            self.online_cache.pop(chk["id"], None)
            self.stack.pop()
            self.go("check", chk["id"])
        self.btn("ΕΛΕΓΧΟΣ", go, bg=GREEN, fg=WHITE_TXT)

    online_cache = {}

    def pg_check(self, cid):
        c = next((x for x in C.load_checks(self.d) if x["id"] == cid), None)
        if not c:
            return self.back()
        cl = c["claims"]
        name = " ".join(x for x in (cl.get("brand"), cl.get("model"), cl.get("year")) if x) or "Αυτοκίνητο"
        self.set_title("Έλεγχος: " + name)
        icon = {"ok": ("#0F7B4F", "ΟΚ"), "warn": ("#C98A00", "ΠΡΟΣΟΧΗ"), "bad": ("#B4461B", "ΠΡΟΒΛΗΜΑ"),
                "info": ("#6B7486", "ΣΗΜ.")}

        def lines(items):
            return "\n".join(f"[color={icon[l][0]}][b]{icon[l][1]}[/b][/color] {esc(t)}" for l, t in items)

        found, info = C.vin_findings(c["vin"], cl)
        self.txt("[size=16sp][b]1. Αριθμός πλαισίου[/b][/size]")
        self.card(f"[b]{esc(c['vin'])}[/b]\n" + lines(found))
        mf = C.mileage_findings(cl)
        if mf:
            self.txt("[size=16sp][b]2. Χιλιόμετρα[/b][/size]")
            self.card(lines(mf))

        self.txt("[size=16sp][b]3. Ανακλήσεις & συχνά προβλήματα[/b][/size]")
        res = self.online_cache.get(cid)
        if res is None:
            ph = self.card("Αναζήτηση στη βάση ανακλήσεων…")

            def work():
                try:
                    decoded = None
                    if not (cl.get("brand") and cl.get("model") and cl.get("year")):
                        decoded, _ = G.decode_vin(c["vin"])
                    r = C.online(c["vin"], cl, decoded)
                except Exception as e:  # noqa: BLE001
                    r = {"error": str(e)[:80]}
                self.online_cache[cid] = r
                Clock.schedule_once(lambda dt: self.reload() if self.stack and self.stack[-1] == ("check", (cid,))
                                    else None)
            threading.Thread(target=work, daemon=True).start()
        else:
            if res.get("error"):
                self.card(f"[color={GREY}]{esc(res['error'])}[/color]")
            else:
                rc = res.get("recalls")
                if rc:
                    t = f"[b]{len(rc)} ανακλήσεις[/b] για {esc(res['make'])} {esc(res['model'])} {esc(res['year'])}:\n"
                    t += "\n".join(f"• {esc(r['component'] or 'Γενικά')} ({esc(r['date'])})" for r in rc[:8])
                    t += ("\n[size=12sp][color=#6B7486]Ρώτα σε αντιπροσωπεία με τον αριθμό πλαισίου αν έχουν γίνει. "
                          "Οι ανακλήσεις στην Ευρώπη μπορεί να διαφέρουν.[/color][/size]")
                    self.card(t)
                elif "recalls" in res:
                    self.card("Δεν βρέθηκαν ανακλήσεις στη βάση των ΗΠΑ για αυτό το μοντέλο/έτος. "
                              "[size=12sp][color=#6B7486](Για ευρωπαϊκά μοντέλα η βάση συχνά δεν έχει στοιχεία.)"
                              "[/color][/size]")
                cp = res.get("complaints")
                if cp and cp[0]:
                    n, comps = cp
                    self.card(f"[b]{n} παράπονα ιδιοκτητών[/b], συνηθέστερα σε:\n" +
                              "\n".join(f"• {esc(k)}: {v}" for k, v in comps) +
                              "\n[size=12sp][color=#6B7486]Δείχνει τι να προσέξεις στο συγκεκριμένο μοντέλο.[/color]"
                              "[/size]")
                if res.get("recalls_err") or res.get("complaints_err"):
                    self.txt(f"[size=12sp][color={GREY}]Η βάση ανακλήσεων δεν απάντησε πλήρως.[/color][/size]")

        def links(title, items, copy=None):
            self.txt(f"[size=16sp][b]{title}[/b][/size]")
            for t, u in items:
                def op(url=u):
                    if copy:
                        try:
                            from kivy.core.clipboard import Clipboard
                            Clipboard.copy(copy)
                        except Exception:  # noqa: BLE001
                            pass
                    self.open_url(url)
                self.btn(t, op, bg=LIGHT)

        links("4. Αναζήτηση ζημιών στο διαδίκτυο", C.damage_links(c["vin"]))
        self.txt(f"[size=12sp][color={GREY}]Αν το αυτοκίνητο έχει πουληθεί τρακαρισμένο σε δημοπρασία (συνηθισμένο "
                 f"σε εισαγωγές από ΗΠΑ), εδώ συχνά εμφανίζονται φωτογραφίες της ζημιάς.[/color][/size]")
        links("5. Επίσημοι έλεγχοι (Ελλάδα, δωρεάν)", C.official_links(), copy=c.get("plate") or None)
        self.txt(f"[size=12sp][color={GREY}]Ο έλεγχος ασφάλισης θέλει πινακίδα και ΑΦΜ ιδιοκτήτη: κάνε τον μαζί με "
                 f"τον πωλητή. Η πινακίδα αντιγράφεται αυτόματα για επικόλληση.[/color][/size]")
        pl = C.price_links(cl)
        if pl:
            links("6. Τιμή & γνώμες", pl)
        links("7. Πλήρες ιστορικό ατυχημάτων (επί πληρωμής)", C.paid_links(), copy=c["vin"])
        self.txt(f"[size=12sp][color={GREY}]Ο αριθμός πλαισίου αντιγράφεται αυτόματα: απλώς επικόλλησέ τον στη "
                 f"σελίδα.[/color][/size]")

        self.txt("[size=16sp][b]8. Επιτόπιος έλεγχος[/b][/size]")
        states = dict(c.get("states", {}))
        score_lbl = self.txt("")

        def upd_score():
            ok, tot = C.checklist_score(states)
            score_lbl.text = f"[b]{ok}/{tot}[/b] σημεία ΟΚ"
        for gi, (group, items) in enumerate(C.CHECKLIST):
            self.txt(f"[b]{group}[/b]")
            for ii, item in enumerate(items):
                k = f"{gi}-{ii}"
                cb = CheckBox(active=bool(states.get(k)), size_hint_x=None, width=dp(44), color=INK)

                def on_act(w, val, key=k):
                    states[key] = bool(val)
                    c["states"] = states
                    C.save_check(self.d, c)
                    upd_score()
                cb.bind(active=on_act)
                lab = Label(text=item, color=INK, halign="left", valign="middle", font_size="14sp",
                            text_size=(Window.width - dp(80), None))
                r = self.row(cb, lab, h=max(48, 20 * (len(item) // 38 + 1) + 10))
        upd_score()
        notes = self.field("Σημειώσεις", c.get("notes"), multiline=True, h=90)

        def save_notes():
            c["notes"] = notes.text
            C.save_check(self.d, c)
        self.btn("ΑΠΟΘΗΚΕΥΣΗ ΣΗΜΕΙΩΣΕΩΝ", save_notes, bg=GREEN, fg=WHITE_TXT)
        self.btn("Αλλαγή στοιχείων", lambda: self.go("check_form", cid), bg=LIGHT)

        def adopt():
            nv = G.upsert_vehicle(self.d, {"brand": cl.get("brand", ""), "model": cl.get("model", ""),
                                           "year": cl.get("year", ""), "vin": c["vin"], "plate": c.get("plate", ""),
                                           "km": G.to_int(cl.get("km", 0)), "km_date": G.today(), "fuel": "Βενζίνη"})
            self.stack = [("vehicles", ())]
            self.go("vehicle_form", nv["id"])
        if not any(v.get("vin") == c["vin"] for v in self.d["vehicles"]):
            self.btn("Το αγόρασα: πρόσθεσέ το στα αυτοκίνητά μου", adopt, bg=BLUE, fg=WHITE_TXT)
        self.btn("Διαγραφή ελέγχου", lambda: (C.delete_check(self.d, cid), self.back()), bg=LIGHT, fg=RED)

    # ------------------------------------------------------------ αναζήτηση
    def pg_search(self, q=""):
        self.set_title("Αναζήτηση")
        self.txt("Ψάξε με [b]κωδικό ανταλλακτικού[/b] (OEM ή αντιστοιχία), [b]κωδικό κινητήρα[/b], "
                 "[b]αριθμό πλαισίου[/b], πινακίδα ή όνομα. Οι κωδικοί συγκρίνονται χωρίς κενά και παύλες.")
        ti = TextInput(text=q, hint_text="π.χ. HU7008, CAYC, 03L115562", multiline=False)
        b = Btn(text="ΑΝΑΖΗΤΗΣΗ", size_hint_x=0.4)
        b.bind(on_release=lambda *a: self.go("search", ti.text, push=False))
        ti.bind(on_text_validate=lambda *a: self.go("search", ti.text, push=False))
        self.row(ti, b)
        self.stack[-1] = ("search", (q,))
        if not q:
            return
        res = G.search(self.d, q)
        if not res:
            self.txt("Δεν βρέθηκε τίποτα στη βάση σου.")
        for kind, o in res:
            if kind == "vehicle":
                self.card(f"[b]{esc(G.vehicle_title(o))}[/b]\n[size=13sp]{esc(G.vehicle_sub(o))}[/size]",
                          lambda vid=o["id"]: self.go("vehicle", vid))
            elif kind == "part":
                for vid in o.get("vehicles", []):
                    v = G.vehicle(self.d, vid)
                    if v:
                        self.card(f"[b]{esc(o['name'])}[/b] – {esc(G.vehicle_title(v))}\n[size=13sp]"
                                  f"{esc(', '.join(o.get('oem', []) + [e['brand'] + ' ' + e['code'] for e in o.get('equiv', [])]))}"
                                  f"[/size]", lambda pid=o["id"], v_id=vid: self.go("part", pid, v_id))
            else:
                v = G.vehicle(self.d, o["vehicle"])
                if v:
                    self.card(f"Service {o['date']} – {esc(G.vehicle_title(v))}\n[size=13sp]{esc(o.get('where', ''))}"
                              f"[/size]", lambda vid=v["id"]: self.go("history", vid))
        self.txt("[b]Αναζήτηση στο διαδίκτυο[/b]")
        for t, u in G.web_searches({"oem": [q], "name": q, "category": ""}, None):
            self.btn(t, lambda url=u: self.open_url(url), bg=LIGHT)

    # ------------------------------------------------------------ υπενθυμίσεις
    def pg_reminders(self):
        self.set_title("Υπενθυμίσεις service")
        rs = G.reminders(self.d)
        if not rs:
            self.txt("Δεν υπάρχουν ανταλλακτικά με διάστημα αλλαγής. Πρόσθεσε αυτοκίνητο με «βασικό πλάνο "
                     "service» ή όρισε «Αλλαγή κάθε … χλμ/μήνες» σε ένα ανταλλακτικό.")
        for v, p, r in rs:
            col, lab = LEVEL[r[0]]
            self.card(f"[color={col}][b]{lab}[/b][/color] · {esc(G.vehicle_title(v))}\n[b]{esc(p['name'])}[/b]: "
                      f"{esc(r[1])}", lambda pid=p["id"], vid=v["id"]: self.go("part", pid, vid))
        self.txt(f"[size=12sp][color={GREY}]Για σωστές υπενθυμίσεις: ενημέρωνε τα χιλιόμετρα κάθε αυτοκινήτου και "
                 f"κατέγραφε κάθε αλλαγή στο «Καταγραφή service».[/color][/size]")

    # ------------------------------------------------------------ αντίγραφα
    def pg_backup(self):
        self.set_title("Αντίγραφα & εισαγωγή")
        n = (len(self.d["vehicles"]), len(self.d["parts"]), len(self.d["services"]))
        self.txt(f"Η βάση σου: {n[0]} αυτοκίνητα, {n[1]} ανταλλακτικά, {n[2]} καταγραφές service.")
        self.btn("ΑΠΟΣΤΟΛΗ ΑΝΤΙΓΡΑΦΟΥ (email, Viber, Drive…)",
                 lambda: self.share(G.export_text(self.d), "Αντίγραφο ανταλλακτικών"), bg=BLUE, fg=WHITE_TXT)
        self.txt(f"[size=13sp][color={GREY}]Στέλνει όλη τη βάση ως κείμενο. Κράτησέ το σε email ή Drive για "
                 f"ασφάλεια ή για μεταφορά σε άλλο κινητό.[/color][/size]")
        self.txt("[size=16sp][b]Επαναφορά από αντίγραφο[/b][/size]")
        ti = self.field("Επικόλλησε εδώ το κείμενο του αντιγράφου", multiline=True, h=120)
        msg = self.txt("")

        def restore():
            try:
                self.d = G.import_text(ti.text)
                msg.text = "[color=#0F7B4F]Η επαναφορά έγινε.[/color]"
            except Exception as e:  # noqa: BLE001
                msg.text = f"[color=#B4461B]Δεν έγινε επαναφορά: {esc(str(e)[:80])}[/color]"
        self.btn("ΕΠΑΝΑΦΟΡΑ (αντικαθιστά τα τωρινά)", restore, bg=LIGHT, fg=RED)

        if self.d["vehicles"]:
            self.txt("[size=16sp][b]Εισαγωγή λίστας από Excel[/b][/size]")
            self.txt(f"[size=13sp][color={GREY}]Στο Excel φτιάξε στήλες: κατηγορία; όνομα; κωδικοί OEM; αντιστοιχίες "
                     f"(Μάρκα:κωδικός | Μάρκα:κωδικός); προδιαγραφή; χλμ; μήνες. Αντέγραψε τις γραμμές και "
                     f"επικόλλησέ τες εδώ.[/color][/size]")
            car = self.choice("Για το αυτοκίνητο", G.vehicle_title(self.d["vehicles"][0]),
                              [G.vehicle_title(v) for v in self.d["vehicles"]])
            csvt = self.field("Γραμμές από Excel", multiline=True, h=120)
            msg2 = self.txt("")

            def imp():
                v = next((x for x in self.d["vehicles"] if G.vehicle_title(x) == car.text), None)
                if not v:
                    return
                try:
                    k = G.import_csv(self.d, v["id"], csvt.text)
                    msg2.text = f"[color=#0F7B4F]Προστέθηκαν {k} ανταλλακτικά.[/color]"
                except Exception as e:  # noqa: BLE001
                    msg2.text = f"[color=#B4461B]Σφάλμα: {esc(str(e)[:80])}[/color]"
            self.btn("ΕΙΣΑΓΩΓΗ", imp)


if __name__ == "__main__":
    AntallaktikaApp().run()
