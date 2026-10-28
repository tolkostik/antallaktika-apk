"""
Έλεγχος μεταχειρισμένου πριν την αγορά – μόνο δωρεάν πηγές.

  • Γνησιότητα πλαισίου: μορφή, ψηφίο ελέγχου (όπου ισχύει), συμφωνία με όσα λέει ο πωλητής.
  • Λογικά χιλιόμετρα για την ηλικία.
  • Ανακλήσεις και συχνά παράπονα (NHTSA, δωρεάν δημόσια υπηρεσία των ΗΠΑ).
  • Έτοιμες αναζητήσεις ζημιών στο διαδίκτυο και επίσημοι ελληνικοί έλεγχοι.
  • Λίστα επιτόπιου ελέγχου.
"""
import datetime
import json
import ssl
import urllib.parse
import urllib.request

import garage as G

_TRANS = {**{str(i): i for i in range(10)}, "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
          "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9, "S": 2, "T": 3, "U": 4, "V": 5, "W": 6,
          "X": 7, "Y": 8, "Z": 9}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

COMPONENTS = {
    "ENGINE": "Κινητήρας", "ENGINE AND ENGINE COOLING": "Κινητήρας / ψύξη", "POWER TRAIN": "Μετάδοση / κιβώτιο",
    "ELECTRICAL SYSTEM": "Ηλεκτρικά", "AIR BAGS": "Αερόσακοι", "SERVICE BRAKES": "Φρένα",
    "SERVICE BRAKES, HYDRAULIC": "Φρένα", "PARKING BRAKE": "Χειρόφρενο", "STEERING": "Τιμόνι",
    "SUSPENSION": "Ανάρτηση", "FUEL SYSTEM": "Σύστημα καυσίμου", "FUEL SYSTEM, GASOLINE": "Σύστημα καυσίμου",
    "FUEL SYSTEM, DIESEL": "Σύστημα καυσίμου (diesel)", "STRUCTURE": "Αμάξωμα / δομή", "VISIBILITY": "Ορατότητα",
    "SEAT BELTS": "Ζώνες", "SEATS": "Καθίσματα", "EXTERIOR LIGHTING": "Φώτα", "WHEELS": "Τροχοί", "TIRES": "Ελαστικά",
    "VEHICLE SPEED CONTROL": "Έλεγχος ταχύτητας", "LATCHES/LOCKS/LINKAGES": "Κλειδαριές", "BACK OVER PREVENTION":
    "Κάμερα / αισθητήρες όπισθεν", "FORWARD COLLISION AVOIDANCE": "Αποφυγή σύγκρουσης", "UNKNOWN OR OTHER": "Άλλο",
    "ELECTRONIC STABILITY CONTROL (ESC)": "ESP", "HYBRID PROPULSION SYSTEM": "Υβριδικό σύστημα",
    "EQUIPMENT": "Εξοπλισμός", "LANE DEPARTURE": "Διατήρηση λωρίδας",
}

CHECKLIST = [
    ("Έγγραφα", ["Ο αριθμός πλαισίου είναι ίδιος στην άδεια και σε 2–3 σημεία του αυτοκινήτου (παρμπρίζ, κολόνα πόρτας, πάτωμα)",
                 "Ο πωλητής είναι ο ιδιοκτήτης στην άδεια ή έχει εξουσιοδότηση",
                 "Βιβλίο service με σφραγίδες και τιμολόγια",
                 "Πρόσφατο ΚΤΕΟ σε ισχύ (τα χιλιόμετρα του ΚΤΕΟ συμφωνούν)",
                 "Δύο κλειδιά",
                 "Ασφάλεια σε ισχύ (έλεγχος στο Επικουρικό Κεφάλαιο με τον πωλητή)"]),
    ("Αμάξωμα", ["Ίδια απόχρωση σε όλες τις λαμαρίνες (κοίτα στο φως, από πλάγια)",
                 "Ίσια και ομοιόμορφα κενά ανάμεσα σε πόρτες, καπό, φτερά",
                 "Χωρίς ίχνη βαφής σε λάστιχα, τζάμια, βίδες καπό/φτερών",
                 "Ίδια ημερομηνία κατασκευής σε όλα τα τζάμια",
                 "Χωρίς συγκολλήσεις ή σκουριά σε ποδιές, πάτωμα, πορτμπαγκάζ",
                 "Ομοιόμορφη φθορά στα ελαστικά (όχι μόνο από τη μία πλευρά)"]),
    ("Εσωτερικό", ["Η φθορά τιμονιού, λεβιέ, πεντάλ, καθίσματος συμφωνεί με τα χιλιόμετρα",
                   "Η λυχνία αερόσακου ανάβει και σβήνει κανονικά στο ξεκίνημα",
                   "Χωρίς υγρασία ή μυρωδιά μούχλας (πιθανή πλημμύρα), χωρίς λάσπη κάτω από τα χαλιά"]),
    ("Κινητήρας & οδήγηση", ["Κρύο ξεκίνημα χωρίς δυσκολία, χωρίς μπλε/λευκό καπνό",
                             "Χωρίς λυχνίες βλάβης στον πίνακα μετά το ξεκίνημα",
                             "Χωρίς διαρροές λαδιών/νερών κάτω από το αυτοκίνητο",
                             "Κιβώτιο και συμπλέκτης χωρίς θόρυβο ή κλωτσιές",
                             "Ευθεία πορεία χωρίς τράβηγμα, φρένα χωρίς τρέμουλο",
                             "Διαγνωστικός έλεγχος (OBD) σε συνεργείο: σφάλματα και αποθηκευμένα χιλιόμετρα μονάδων"]),
]


def check_digit(vin):
    s = 0
    for i, ch in enumerate(vin):
        v = _TRANS.get(ch)
        if v is None:
            return None
        s += v * _WEIGHTS[i]
    r = s % 11
    return "X" if r == 10 else str(r)


def vin_findings(vin, claims):
    """Λίστα (επίπεδο 'ok'|'warn'|'bad'|'info', κείμενο)."""
    out = []
    info, err = G.vin_offline(vin)
    if err:
        return [("bad", err)], None
    vin = info["vin"]
    out.append(("ok", "Ο αριθμός πλαισίου έχει σωστή μορφή (17 χαρακτήρες, χωρίς I/O/Q)."))
    cd = check_digit(vin)
    north_america = vin[0] in "12345"
    if north_america:
        if cd == vin[8]:
            out.append(("ok", "Το ψηφίο ελέγχου (9ο) είναι σωστό: το πλαίσιο είναι μαθηματικά έγκυρο."))
        else:
            out.append(("bad", f"Το ψηφίο ελέγχου δεν ταιριάζει (είναι {vin[8]}, έπρεπε {cd}). Σε αμερικανικό "
                               f"πλαίσιο αυτό σημαίνει λάθος πληκτρολόγηση ή αλλοιωμένο αριθμό."))
        out.append(("warn", "Αυτοκίνητο κατασκευασμένο για τη Βόρεια Αμερική: έλεγξε οπωσδήποτε τις αναζητήσεις "
                            "ζημιών παρακάτω (πολλά έρχονται από δημοπρασίες τρακαρισμένων)."))
    else:
        out.append(("info", "Για ευρωπαϊκά αυτοκίνητα το ψηφίο ελέγχου δεν είναι υποχρεωτικό, οπότε δεν ελέγχεται."))
    cb = (claims.get("brand") or "").strip().lower()
    if info.get("brand"):
        if cb and cb.split()[0][:4] not in info["brand"].lower():
            out.append(("bad", f"Το πλαίσιο δείχνει «{info['brand']}», ενώ ο πωλητής λέει «{claims['brand']}»."))
        else:
            out.append(("ok", f"Κατασκευαστής από το πλαίσιο: {info['brand']}" +
                        (f" ({info['country']})" if info.get("country") else "")))
    yg = info.get("year_guess")
    cy = G.to_int(claims.get("year", 0))
    if yg and cy:
        if abs(yg - cy) <= 1:
            out.append(("ok", f"Το έτος από το πλαίσιο ({yg}) συμφωνεί με το δηλωμένο."))
        else:
            out.append(("warn", f"Το πλαίσιο δείχνει έτος μοντέλου {yg}, ο πωλητής λέει {cy}. Σε πολλούς ευρωπαίους "
                                f"κατασκευαστές το 10ο ψηφίο δεν δείχνει πάντα έτος: ζήτα εξήγηση και δες την άδεια."))
    return out, info


def mileage_findings(claims):
    out = []
    km = G.to_int(claims.get("km", 0))
    year = G.to_int(claims.get("year", 0))
    if not km or not year:
        return out
    age = max(0.5, datetime.date.today().year - year + 0.5)
    per = km / age
    txt = f"{km:,} χλμ σε ~{age:.0f} χρόνια = {per:,.0f} χλμ τον χρόνο".replace(",", ".")
    if per < 6000:
        out.append(("warn", txt + ". Πολύ λίγα: πιθανόν γυρισμένα χιλιόμετρα. Σύγκρινε με ΚΤΕΟ, βιβλίο service "
                                  "και φθορά εσωτερικού."))
    elif per > 35000:
        out.append(("warn", txt + ". Πολύ μεγάλη χρήση (π.χ. ταξί, εταιρικό, ενοικίαση)."))
    else:
        out.append(("ok", txt + ". Λογικά για την ηλικία."))
    return out


def _get(url):
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": G.UA})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _q(s):
    return urllib.parse.quote(str(s or "").strip())


def recalls(make, model, year):
    js = _get(f"https://api.nhtsa.gov/recalls/recallsByVehicle?make={_q(make)}&model={_q(model)}&modelYear={_q(year)}")
    out = []
    for r in js.get("results", []) or js.get("Results", []):
        comp = r.get("Component", "")
        out.append({"id": r.get("NHTSACampaignNumber", ""), "date": r.get("ReportReceivedDate", ""),
                    "component": translate_components(comp), "summary": r.get("Summary", "")})
    return out


def translate_components(text):
    parts = [p.strip() for p in str(text).replace(":", ",").split(",") if p.strip()]
    gr = []
    for p in parts:
        g = COMPONENTS.get(p.upper()) or COMPONENTS.get(p.upper().split(",")[0])
        if g and g not in gr:
            gr.append(g)
    return ", ".join(gr) or (parts[0].title() if parts else "")


def complaints(make, model, year):
    js = _get(f"https://api.nhtsa.gov/complaints/complaintsByVehicle?make={_q(make)}&model={_q(model)}"
              f"&modelYear={_q(year)}")
    counts = {}
    res = js.get("results", []) or js.get("Results", [])
    for r in res:
        for p in str(r.get("components", "")).split(","):
            p = p.strip().upper()
            if not p:
                continue
            g = COMPONENTS.get(p, p.title())
            counts[g] = counts.get(g, 0) + 1
    return len(res), sorted(counts.items(), key=lambda kv: -kv[1])[:6]


def online(vin, claims, decoded):
    """Ανακλήσεις & παράπονα. Επιστρέφει dict με αποτελέσματα ή σφάλματα."""
    make = claims.get("brand") or (decoded or {}).get("brand") or ""
    model = claims.get("model") or (decoded or {}).get("model") or ""
    year = claims.get("year") or (decoded or {}).get("year") or (decoded or {}).get("year_guess") or ""
    res = {"make": make, "model": model, "year": year}
    if not (make and model and year):
        res["error"] = "Για ανακλήσεις και συχνά προβλήματα χρειάζονται μάρκα, μοντέλο και έτος."
        return res
    make_q = make.split("(")[0].strip()
    model_q = model.split()[0] if model else model
    try:
        res["recalls"] = recalls(make_q, model_q, year)
    except Exception as e:  # noqa: BLE001
        res["recalls_err"] = str(e)[:80]
    try:
        res["complaints"] = complaints(make_q, model_q, year)
    except Exception as e:  # noqa: BLE001
        res["complaints_err"] = str(e)[:80]
    return res


def damage_links(vin):
    g = "https://www.google.com/search?q="
    return [("Google: αναζήτηση του πλαισίου", g + _q(f'"{vin}"')),
            ("Google Εικόνες: φωτογραφίες με αυτό το πλαίσιο", "https://www.google.com/search?tbm=isch&q=" + _q(f'"{vin}"')),
            ("Δημοπρασίες τρακαρισμένων (Copart / IAAI)", g + _q(f'"{vin}" copart OR iaai OR salvage OR damage')),
            ("NICB VINCheck (κλοπή/ολική καταστροφή, ΗΠΑ)", "https://www.nicb.org/vincheck")]


def official_links():
    return [("Έλεγχος ασφάλισης (Επικουρικό Κεφάλαιο)", "https://www.hic.gr/hic/Check_ins.aspx"),
            ("Open Car – ΑΑΔΕ (gov.gr)",
             "https://www.gov.gr/arxes/anexartete-arkhe-demosion-esodon-aade/anexartete-arkhe-demosion-esodon-aade/opencar")]


def price_links(claims):
    q = " ".join(x for x in (claims.get("brand"), claims.get("model"), claims.get("year")) if x)
    if not q:
        return []
    g = "https://www.google.com/search?q="
    return [("Σύγκρινε τιμή: παρόμοια στο car.gr", g + _q(f"site:car.gr {q}")),
            ("Συχνά προβλήματα του μοντέλου (forum)", g + _q(f"{q} συχνά προβλήματα"))]


def paid_links():
    return [("carlytics.eu (πλήρες ιστορικό, επί πληρωμής)", "https://www.carlytics.eu/el/elenchos-vin"),
            ("carVertical (επί πληρωμής)", "https://www.carvertical.com/gr"),
            ("autoistoriko.gr (βασικά δωρεάν)", "https://autoistoriko.gr/")]


# ------------------------------------------------------------------ αποθήκευση ελέγχων
def load_checks(d):
    return d.setdefault("checks", [])


def save_check(d, chk):
    lst = [c for c in d.get("checks", []) if c["id"] != chk["id"]]
    lst.insert(0, chk)
    d["checks"] = lst[:50]
    G.save(d)


def delete_check(d, cid):
    d["checks"] = [c for c in d.get("checks", []) if c["id"] != cid]
    G.save(d)


def checklist_score(states):
    total = sum(len(items) for _, items in CHECKLIST)
    ok = sum(1 for v in states.values() if v)
    return ok, total
