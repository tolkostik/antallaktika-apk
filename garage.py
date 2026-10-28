"""
Ανταλλακτικά & αναλώσιμα για τα δικά μου αυτοκίνητα.

Δεδομένα: ένα αρχείο JSON στο κινητό (οχήματα, ανταλλακτικά, τιμές, ιστορικό service).
Αποκωδικοποίηση πλαισίου: εκτός σύνδεσης (κατασκευαστής, χώρα, έτος) και
online μέσω της δωρεάν υπηρεσίας vPIC της NHTSA (μοντέλο, κινητήρας όπου υπάρχουν).
"""
import datetime
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path.home() / ".antallaktika"
UA = "Antallaktika/1.0 (Android; personal use)"

CATEGORIES = ["Λάδι κινητήρα", "Φίλτρο λαδιού", "Φίλτρο αέρα", "Φίλτρο καμπίνας", "Φίλτρο καυσίμου", "Μπουζί",
              "Προθερμαντήρες", "Τακάκια εμπρός", "Τακάκια πίσω", "Δισκόπλακες εμπρός", "Δισκόπλακες πίσω",
              "Ιμάντας χρονισμού (κιτ)", "Ιμάντας βοηθητικών", "Αντλία νερού", "Αντιψυκτικό", "Υγρό φρένων",
              "Λάδι κιβωτίου", "Μπαταρία", "Λάμπες", "Υαλοκαθαριστήρες", "Ελαστικά", "Αμορτισέρ", "Συμπλέκτης",
              "Άλλο"]

# Ενδεικτικό βασικό πλάνο service: (κατηγορία, χλμ, μήνες, μόνο για καύσιμο)
BASE_PLAN = [("Λάδι κινητήρα", 15000, 12, None), ("Φίλτρο λαδιού", 15000, 12, None),
             ("Φίλτρο αέρα", 30000, 24, None), ("Φίλτρο καμπίνας", 15000, 12, None),
             ("Φίλτρο καυσίμου", 30000, 24, "Diesel"), ("Φίλτρο καυσίμου", 60000, 48, "Βενζίνη"),
             ("Μπουζί", 60000, 48, "Βενζίνη"), ("Υγρό φρένων", 0, 24, None), ("Αντιψυκτικό", 0, 60, None),
             ("Ιμάντας χρονισμού (κιτ)", 90000, 60, None), ("Τακάκια εμπρός", 0, 0, None),
             ("Μπαταρία", 0, 0, None)]
FUELS = ["Βενζίνη", "Diesel", "Υγραέριο", "Υβριδικό", "Ηλεκτρικό"]


def set_dir(p):
    global DATA_DIR
    DATA_DIR = Path(p)


# ------------------------------------------------------------------ αποθήκευση
def _empty():
    return {"vehicles": [], "parts": [], "services": [], "checks": [], "version": 1}


def load():
    try:
        d = json.loads((DATA_DIR / "garage.json").read_text(encoding="utf-8"))
        for k, v in _empty().items():
            d.setdefault(k, v)
        ids = [x["id"] for k in ("vehicles", "parts", "services") for x in d[k]]
        if ids:
            _LAST_ID[0] = max(_LAST_ID[0], max(ids))
        return d
    except Exception:  # noqa: BLE001
        return _empty()


def save(d):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_DIR / "garage.tmp"
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(DATA_DIR / "garage.json")


_LAST_ID = [0]


def new_id():
    """Μοναδικός αριθμός, πάντα αυξανόμενος (ακόμα κι αν δημιουργηθούν πολλά μέσα στο ίδιο χιλιοστό)."""
    nid = max(int(time.time() * 1000), _LAST_ID[0] + 1)
    _LAST_ID[0] = nid
    return nid


def today():
    return datetime.date.today().strftime("%d/%m/%Y")


def parse_date(s):
    try:
        return datetime.datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None


def to_int(x, default=0):
    try:
        return int(float(str(x).replace(".", "").replace(",", ".").strip() or default))
    except ValueError:
        return default


def to_float(x, default=None):
    try:
        return float(str(x).replace(",", ".").strip())
    except ValueError:
        return default


# ------------------------------------------------------------------ οχήματα
def vehicle(d, vid):
    return next((v for v in d["vehicles"] if v["id"] == vid), None)


def vehicle_title(v):
    t = " ".join(x for x in (v.get("brand"), v.get("model")) if x) or "Όχημα"
    if v.get("nickname"):
        t = f"{v['nickname']} ({t})"
    return t


def vehicle_sub(v):
    parts = [v.get("year"), v.get("engine_desc"), v.get("engine_code") and f"κινητήρας {v['engine_code']}",
             v.get("fuel"), v.get("plate")]
    return " · ".join(str(x) for x in parts if x)


def upsert_vehicle(d, v):
    if not v.get("id"):
        v["id"] = new_id()
        d["vehicles"].append(v)
    else:
        d["vehicles"] = [v if x["id"] == v["id"] else x for x in d["vehicles"]]
    save(d)
    return v


def delete_vehicle(d, vid):
    d["vehicles"] = [v for v in d["vehicles"] if v["id"] != vid]
    for p in d["parts"]:
        p["vehicles"] = [x for x in p.get("vehicles", []) if x != vid]
    d["parts"] = [p for p in d["parts"] if p.get("vehicles")]
    d["services"] = [s for s in d["services"] if s["vehicle"] != vid]
    save(d)


def set_km(d, vid, km):
    v = vehicle(d, vid)
    if v:
        v["km"] = to_int(km, v.get("km", 0))
        v["km_date"] = today()
        save(d)


def add_base_plan(d, vid):
    v = vehicle(d, vid)
    have = {p["category"] for p in parts_of(d, vid)}
    added = 0
    for cat, km, months, fuel in BASE_PLAN:
        if fuel and v.get("fuel") and fuel != v.get("fuel"):
            continue
        if fuel and not v.get("fuel"):
            continue
        if cat in have:
            continue
        upsert_part(d, {"category": cat, "name": cat, "vehicles": [vid], "oem": [], "equiv": [], "spec": "",
                        "interval_km": km, "interval_months": months, "notes": "Ενδεικτικό διάστημα: έλεγξε το "
                        "βιβλίο service του αυτοκινήτου.", "prices": []})
        have.add(cat)
        added += 1
    return added


# ------------------------------------------------------------------ ανταλλακτικά
def norm(code):
    return re.sub(r"[^0-9A-ZΑ-Ω]", "", str(code).upper())


def parse_codes(text):
    return [c.strip() for c in re.split(r"[,;\n]", text or "") if c.strip()]


def parse_equiv(text):
    """Γραμμές «Μάρκα κωδικός» → [{'brand', 'code'}]."""
    out = []
    for line in re.split(r"[\n;]", text or ""):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            b, c = line.split(":", 1)
        else:
            bits = line.split()
            b, c = (bits[0], " ".join(bits[1:])) if len(bits) > 1 else ("", bits[0])
        out.append({"brand": b.strip(), "code": c.strip()})
    return out


def equiv_text(eq):
    return "\n".join(f"{e['brand']} {e['code']}".strip() for e in eq)


def part(d, pid):
    return next((p for p in d["parts"] if p["id"] == pid), None)


def parts_of(d, vid):
    ps = [p for p in d["parts"] if vid in p.get("vehicles", [])]
    order = {c: i for i, c in enumerate(CATEGORIES)}
    return sorted(ps, key=lambda p: (order.get(p["category"], 99), p.get("name", "")))


def upsert_part(d, p):
    p.setdefault("prices", [])
    if not p.get("id"):
        p["id"] = new_id()
        d["parts"].append(p)
    else:
        d["parts"] = [p if x["id"] == p["id"] else x for x in d["parts"]]
    save(d)
    return p


def delete_part(d, pid):
    d["parts"] = [p for p in d["parts"] if p["id"] != pid]
    for s in d["services"]:
        s["parts"] = [x for x in s.get("parts", []) if x != pid]
    save(d)


def all_codes(p):
    return [norm(c) for c in p.get("oem", [])] + [norm(e["code"]) for e in p.get("equiv", [])]


def same_codes(d, p):
    """Άλλα ανταλλακτικά της βάσης με κοινό κωδικό (OEM ή αντιστοιχία)."""
    mine = {c for c in all_codes(p) if len(c) >= 4}
    if not mine:
        return []
    return [q for q in d["parts"] if q["id"] != p.get("id") and mine & set(all_codes(q))]


def add_price(d, pid, supplier, price, url=""):
    p = part(d, pid)
    if not p:
        return
    p.setdefault("prices", []).append({"supplier": supplier.strip() or "—", "price": round(price, 2),
                                       "date": today(), "url": url.strip()})
    save(d)


def best_price(p):
    ps = sorted(p.get("prices", []), key=lambda x: x["price"])
    return ps[0] if ps else None


# ------------------------------------------------------------------ service / ιστορικό
def services_of(d, vid):
    ss = [s for s in d["services"] if s["vehicle"] == vid]
    return sorted(ss, key=lambda s: (parse_date(s["date"]) or datetime.date.min, s.get("km", 0)), reverse=True)


def add_service(d, vid, date, km, part_ids, cost, where, notes):
    s = {"id": new_id(), "vehicle": vid, "date": date or today(), "km": to_int(km), "parts": list(part_ids),
         "cost": to_float(cost, 0.0) or 0.0, "where": where.strip(), "notes": notes.strip()}
    d["services"].append(s)
    v = vehicle(d, vid)
    if v and s["km"] > to_int(v.get("km", 0)):
        v["km"] = s["km"]
        v["km_date"] = s["date"]
    save(d)
    return s


def delete_service(d, sid):
    d["services"] = [s for s in d["services"] if s["id"] != sid]
    save(d)


def last_change(d, pid):
    ss = [s for s in d["services"] if pid in s.get("parts", [])]
    ss.sort(key=lambda s: (parse_date(s["date"]) or datetime.date.min, s.get("km", 0)), reverse=True)
    return ss[0] if ss else None


def _add_months(dt, m):
    y, mo = divmod(dt.month - 1 + m, 12)
    import calendar
    day = min(dt.day, calendar.monthrange(dt.year + y, mo + 1)[1])
    return datetime.date(dt.year + y, mo + 1, day)


def reminder(d, p, v):
    """Κατάσταση αλλαγής: (επίπεδο 'late'|'soon'|'ok'|'unknown', κείμενο, χλμ που απομένουν)."""
    ikm, imo = to_int(p.get("interval_km", 0)), to_int(p.get("interval_months", 0))
    if not ikm and not imo:
        return None
    last = last_change(d, p["id"])
    if not last:
        return ("unknown", "Δεν έχει καταγραφεί αλλαγή", None)
    msgs, level, left_km = [], "ok", None
    cur_km = to_int(v.get("km", 0))
    if ikm:
        due_km = last["km"] + ikm
        left_km = due_km - cur_km
        if cur_km:
            if left_km <= 0:
                level = "late"
                msgs.append(f"πέρασε κατά {abs(left_km):,} χλμ".replace(",", "."))
            else:
                if left_km <= max(1000, ikm * 0.1):
                    level = "soon"
                msgs.append(f"σε {left_km:,} χλμ (στα {due_km:,})".replace(",", "."))
    if imo:
        ld = parse_date(last["date"])
        if ld:
            due = _add_months(ld, imo)
            days = (due - datetime.date.today()).days
            if days < 0:
                level = "late"
                msgs.append(f"έληξε {due:%d/%m/%Y}")
            else:
                if days <= 30 and level != "late":
                    level = "soon"
                msgs.append(f"έως {due:%d/%m/%Y}")
    return (level, " · ".join(msgs), left_km)


def reminders(d, vid=None):
    out = []
    for v in d["vehicles"]:
        if vid and v["id"] != vid:
            continue
        for p in parts_of(d, v["id"]):
            r = reminder(d, p, v)
            if r:
                out.append((v, p, r))
    rank = {"late": 0, "soon": 1, "unknown": 2, "ok": 3}
    out.sort(key=lambda t: (rank[t[2][0]], t[2][2] if t[2][2] is not None else 10 ** 9))
    return out


# ------------------------------------------------------------------ αναζήτηση
def search(d, q):
    q = q.strip()
    if not q:
        return []
    nq, lq = norm(q), q.lower()
    res = []
    for v in d["vehicles"]:
        hay = " ".join(str(v.get(k, "")) for k in ("nickname", "brand", "model", "year", "engine_code",
                                                   "engine_desc", "vin", "plate", "fuel")).lower()
        if lq in hay or (len(nq) >= 3 and nq in norm(hay)):
            res.append(("vehicle", v))
    for p in d["parts"]:
        hay = " ".join([p.get("name", ""), p.get("category", ""), p.get("spec", ""), p.get("notes", "")]).lower()
        codes = all_codes(p)
        if lq in hay or (len(nq) >= 3 and any(nq in c for c in codes)):
            res.append(("part", p))
    for s in d["services"]:
        hay = " ".join([s.get("where", ""), s.get("notes", "")]).lower()
        if lq in hay:
            res.append(("service", s))
    return res


# ------------------------------------------------------------------ αναζήτηση στο διαδίκτυο
def web_searches(p=None, v=None, text=None):
    """[(τίτλος, url)] για αντιστοιχίες / τιμές ενός ανταλλακτικού."""
    code = (p.get("oem") or [None])[0] if p else None
    car = " ".join(x for x in (v.get("brand"), v.get("model"), v.get("engine_desc"), v.get("engine_code"),
                               v.get("year")) if x) if v else ""
    what = text or (p.get("name") or p.get("category")) if p else text
    out = []
    g = "https://www.google.com/search?q="
    if code:
        out.append((f"Google: «{code}»", g + urllib.parse.quote(code)))
        out.append(("Αντιστοιχίες (cross reference)", g + urllib.parse.quote(f"{code} cross reference αντιστοιχία")))
        out.append(("Autodoc", g + urllib.parse.quote(f"site:autodoc.gr {code}")))
        out.append(("Skroutz", "https://www.skroutz.gr/search?keyphrase=" + urllib.parse.quote(code)))
        out.append(("eBay", "https://www.ebay.com/sch/i.html?_nkw=" + urllib.parse.quote(code)))
    if what and car:
        q = f"{what} {car}"
        out.append((f"Google: {what} για το αυτοκίνητό μου", g + urllib.parse.quote(q)))
        out.append(("Skroutz: " + what, "https://www.skroutz.gr/search?keyphrase=" + urllib.parse.quote(q)))
        out.append(("Κωδικός OEM για " + what, g + urllib.parse.quote(f"{what} {car} OEM κωδικός")))
    return out


# ------------------------------------------------------------------ αριθμός πλαισίου (VIN)
WMI = {
    "WVW": "Volkswagen", "WV1": "Volkswagen (επαγγελματικά)", "WV2": "Volkswagen (βαν)", "WAU": "Audi",
    "WBA": "BMW", "WBS": "BMW M", "WMW": "MINI", "WDB": "Mercedes-Benz", "WDD": "Mercedes-Benz",
    "W1K": "Mercedes-Benz", "WDC": "Mercedes-Benz (SUV)", "W0L": "Opel", "W0V": "Opel", "WF0": "Ford (Γερμανία)",
    "WP0": "Porsche", "VF1": "Renault", "VF3": "Peugeot", "VR3": "Peugeot", "VF7": "Citroën", "VR7": "Citroën",
    "UU1": "Dacia", "ZFA": "Fiat", "ZAR": "Alfa Romeo", "ZLA": "Lancia", "TMB": "Škoda", "VSS": "SEAT",
    "VSK": "Nissan (Ισπανία)", "SJN": "Nissan (Ηνωμένο Βασίλειο)", "JN1": "Nissan", "VNK": "Toyota (Γαλλία)",
    "SB1": "Toyota (Ηνωμένο Βασίλειο)", "NMT": "Toyota (Τουρκία)", "JTD": "Toyota", "JTN": "Toyota",
    "JTE": "Toyota", "JT2": "Toyota", "TMA": "Hyundai (Τσεχία)", "KMH": "Hyundai", "NLH": "Hyundai (Τουρκία)",
    "MAL": "Hyundai (Ινδία)", "KNA": "Kia", "KNE": "Kia", "U5Y": "Kia (Σλοβακία)", "JMZ": "Mazda", "JM1": "Mazda",
    "JHM": "Honda", "SHH": "Honda (Ηνωμένο Βασίλειο)", "JS2": "Suzuki", "TSM": "Suzuki (Ουγγαρία)",
    "MA3": "Suzuki (Ινδία)", "JMB": "Mitsubishi", "YV1": "Volvo", "SAL": "Land Rover", "SAJ": "Jaguar",
    "ZAM": "Maserati", "ZFF": "Ferrari", "LSV": "Volkswagen (Κίνα)", "XTA": "Lada", "VSE": "Suzuki (Ισπανία)",
    "SCC": "Lotus", "TRU": "Audi (Ουγγαρία)", "WUA": "Audi Sport", "ZHW": "Lamborghini", "SAR": "Rover",
}
COUNTRY = {"W": "Γερμανία", "V": "Γαλλία / Ισπανία", "Z": "Ιταλία", "T": "Τσεχία / Ουγγαρία / Τουρκία",
           "S": "Ηνωμένο Βασίλειο", "U": "Ρουμανία / Σλοβακία", "Y": "Σουηδία / Φινλανδία", "J": "Ιαπωνία",
           "K": "Κορέα", "L": "Κίνα", "M": "Ινδία / Ταϊλάνδη", "N": "Τουρκία", "1": "ΗΠΑ", "4": "ΗΠΑ",
           "5": "ΗΠΑ", "2": "Καναδάς", "3": "Μεξικό", "X": "Ρωσία"}
YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"


def vin_offline(vin):
    vin = vin.strip().upper().replace(" ", "")
    if len(vin) != 17:
        return None, "Ο αριθμός πλαισίου έχει 17 χαρακτήρες."
    if re.search(r"[IOQ]", vin) or not re.fullmatch(r"[A-Z0-9]{17}", vin):
        return None, "Μη έγκυρος αριθμός πλαισίου (δεν περιέχει I, O, Q)."
    info = {"vin": vin}
    info["brand"] = WMI.get(vin[:3], "")
    info["country"] = COUNTRY.get(vin[0], "")
    c = vin[9]
    if c in YEAR_CODES:
        idx = YEAR_CODES.index(c)
        cand = [1980 + idx + 30 * k for k in range(3)]
        cur = datetime.date.today().year + 1
        yrs = [y for y in cand if y <= cur]
        if yrs:
            info["year_guess"] = yrs[-1]
    return info, None


def vin_online(vin):
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        js = json.loads(r.read().decode("utf-8"))
    res = (js.get("Results") or [{}])[0]

    def g(k):
        v = (res.get(k) or "").strip()
        return "" if v in ("", "Not Applicable", "0") else v
    disp = g("DisplacementL")
    eng = " ".join(x for x in (f"{float(disp):.1f}L" if disp else "", g("EngineConfiguration"),
                               g("EngineCylinders") and f"{g('EngineCylinders')} κύλ.",
                               g("EngineHP") and f"{g('EngineHP')} hp") if x)
    fuel_map = {"Gasoline": "Βενζίνη", "Diesel": "Diesel", "Electric": "Ηλεκτρικό"}
    return {"brand": g("Make").title() if g("Make") else "", "model": g("Model"), "year": g("ModelYear"),
            "engine_code": g("EngineModel"), "engine_desc": eng, "fuel": fuel_map.get(g("FuelTypePrimary"), ""),
            "body": g("BodyClass"), "plant": g("PlantCountry"), "trim": g("Trim")}


def decode_vin(vin):
    """Συνδυάζει εκτός σύνδεσης και online αποκωδικοποίηση. Επιστρέφει (στοιχεία, σημειώσεις)."""
    info, err = vin_offline(vin)
    if err:
        return None, [err]
    notes = []
    try:
        on = vin_online(info["vin"])
        for k, v in on.items():
            if v and not info.get(k):
                info[k] = v
        if not on.get("model"):
            notes.append("Η online υπηρεσία δεν είχε μοντέλο/κινητήρα για αυτό το πλαίσιο (συνηθισμένο σε "
                         "ευρωπαϊκά αυτοκίνητα). Συμπλήρωσέ τα από την άδεια κυκλοφορίας.")
    except Exception:  # noqa: BLE001
        notes.append("Χωρίς σύνδεση: βρέθηκαν μόνο κατασκευαστής, χώρα και πιθανό έτος.")
    if info.get("year_guess") and not info.get("year"):
        info["year"] = str(info["year_guess"])
        notes.append("Το έτος είναι εκτίμηση από το πλαίσιο: έλεγξέ το.")
    if not info.get("brand"):
        notes.append("Ο κατασκευαστής δεν αναγνωρίστηκε από το πλαίσιο.")
    return info, notes


# ------------------------------------------------------------------ αντίγραφα ασφαλείας / CSV
def export_text(d):
    return json.dumps(d, ensure_ascii=False)


def import_text(text):
    d = json.loads(text)
    if not isinstance(d, dict) or "vehicles" not in d:
        raise ValueError("Δεν είναι αντίγραφο αυτής της εφαρμογής.")
    for k, v in _empty().items():
        d.setdefault(k, v)
    save(d)
    return d


def import_csv(d, vid, text):
    """Γραμμές: κατηγορία; όνομα; κωδικοί OEM (με κόμμα); αντιστοιχίες (Μάρκα:κωδικός | ...); προδιαγραφή;
    χλμ; μήνες. Χωρίστηκό: ; ή tab."""
    import csv
    import io
    rows = list(csv.reader(io.StringIO(text.strip()), delimiter=";" if ";" in text else "\t"))
    added = 0
    for r in rows:
        if not r or not any(x.strip() for x in r):
            continue
        r = [x.strip() for x in r] + [""] * 7
        if r[0].lower() in ("κατηγορία", "category"):
            continue
        cat = r[0] if r[0] in CATEGORIES else "Άλλο"
        upsert_part(d, {"category": cat, "name": r[1] or r[0], "vehicles": [vid], "oem": parse_codes(r[2]),
                        "equiv": parse_equiv(r[3].replace("|", "\n")), "spec": r[4],
                        "interval_km": to_int(r[5]), "interval_months": to_int(r[6]), "notes": "", "prices": []})
        added += 1
    return added
