"""Canteen menu: sample file and upload parser (Excel .xlsx or CSV).

The admin downloads a sample that already covers THIS week and NEXT week (dates follow today's date),
fills one row per day, uploads it, and the editor is filled in for review. Nothing is saved by the upload
itself. Excel support needs the `openpyxl` package; if it is missing, CSV still works and the sample is
offered as CSV.

Evening snacks come in two kinds:
  * Regular snacks   - the usual items (Maggie, Bhel, Sandwich ...)
  * Chef's special   - anything special; on those days there are no regular snacks.
Use the "Snack Type" column (Regular / Chef's Special) and put the dish in "Snack Name". A single cell such as
"Chef's Special - Pasta" or "Regular snack - Maggie" is understood too.
"""
import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

try:  # optional dependency
    import openpyxl
except ImportError:  # pragma: no cover - exercised only when the package is absent
    openpyxl = None

MAX_UPLOAD_BYTES = 1024 * 1024
MAX_UNZIPPED_BYTES = 20 * 1024 * 1024  # guards against "zip bomb" spreadsheets
MAX_LENGTH = {"lunch_veg_dal": 300, "lunch_roti": 200, "lunch_rice": 250, "lunch_curd": 250, "snacks": 300}
MENU_FIELDS = tuple(MAX_LENGTH)
WINDOW_DAYS = 14   # this week + next week

SAMPLE_COLUMNS = [
    ("Date", "date"),
    ("Holiday (Yes/No)", "is_holiday"),
    ("Veg / Dal", "lunch_veg_dal"),
    ("Roti", "lunch_roti"),
    ("Salad / Papad / Rice", "lunch_rice"),
    ("Curd / Sweet", "lunch_curd"),
    ("Snack Type (Regular / Chef's Special)", "snack_type"),
    ("Snack Name", "snacks"),
]
# veg/dal, roti, rice, curd, snack type, snack name - one example week, reused for the second week
SAMPLE_MENU = [
    ("Aloo Gobi, Dal Tadka", "Phulka", "Jeera Rice, Salad, Papad", "Curd", "Regular", "Maggie"),
    ("Paneer Butter Masala, Dal Fry", "Phulka", "Steamed Rice, Salad, Papad", "Gulab Jamun", "Regular", "Bhel"),
    ("Mix Veg, Rajma", "Phulka", "Jeera Rice, Salad, Papad", "Curd", "Regular", "Sandwich"),
    ("Bhindi Masala, Dal Tadka", "Phulka", "Pulao, Salad, Papad", "Boondi Raita", "Chef's Special", "Pasta in white sauce"),
    ("Chole, Aloo Jeera", "Bhatura", "Steamed Rice, Salad", "Kheer", "Regular", "Maggie"),
    ("", "", "", "", "", ""),  # Saturday: example of a closed day, see the Holiday column
]

_HEADER_ALIASES = {
    "date": {"date", "menudate", "daydate"},
    "is_holiday": {"holiday", "holidayyesno", "holidayyn", "closed", "canteenclosed", "holidaycanteenclosed"},
    "lunch_veg_dal": {"vegdal", "veg", "dal", "lunchvegdal", "vegdalpreparation", "vegetabledal", "sabzidal"},
    "lunch_roti": {"roti", "rotipreparation", "lunchroti"},
    "lunch_rice": {"saladpapadrice", "rice", "saladpapad", "lunchrice", "ricesaladpapad"},
    "lunch_curd": {"curdsweet", "curd", "sweet", "lunchcurd", "sweetcurd"},
    "snack_type": {"snacktype", "snacktyperegularchefsspecial", "typeofsnack", "snackcategory", "snackkind"},
    "snacks": {"eveningsnacks", "snacks", "snack", "eveningsnack", "snackname", "snacknames", "eveningsnackname"},
}
_ALIAS_TO_FIELD = {alias: field_name for field_name, aliases in _HEADER_ALIASES.items() for alias in aliases}
_YES = {"yes", "y", "true", "1", "holiday", "closed", "x", "closed/holiday"}
_BLANK = {"", "-", "--", "na", "n/a", "nil", "none", "null", "—"}
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y",
                 "%d-%b-%y", "%d/%m/%y", "%a, %d %b %Y", "%A, %d %B %Y", "%A, %d %b %Y")
_PREFIX = re.compile(r"^\s*(?P<kind>regular|chef['’]?s?|special)\s*(?:special)?\s*(?:snacks?)?\s*[-:–—]\s*(?P<name>.*)$", re.I)


class ImportProblem(Exception):
    """The file cannot be used; the message is written for the admin."""


@dataclass
class ParseResult:
    monday: date
    rows: dict = field(default_factory=dict)        # date -> {"is_holiday": bool, "snack_type": str, <menu fields>: str}
    warnings: list = field(default_factory=list)


def excel_available():
    return openpyxl is not None


def monday_of(day):
    return day - timedelta(days=day.weekday())


def _clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in _BLANK else text


def _header_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def snack_kind(text):
    """'special' for anything that mentions chef / special, otherwise 'regular'."""
    t = (text or "").lower()
    return "special" if ("special" in t or "chef" in t) else "regular"


def split_snack(type_cell, snack_cell):
    """Work out (snack_type, snack_name) from the two cells; the name cell may carry a 'Chef's Special - Pasta' prefix."""
    name = _clean(snack_cell)
    kind = snack_kind(_clean(type_cell)) if _clean(type_cell) else None
    m = _PREFIX.match(name) if name else None
    if m:
        prefix_kind = "special" if m.group("kind").lower().startswith(("chef", "special")) else "regular"
        kind = kind or prefix_kind
        name = m.group("name").strip()
    return kind or "regular", name


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 30000 < value < 80000:  # an Excel date stored as a plain number
        return date(1899, 12, 30) + timedelta(days=int(value))
    text = _clean(value)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _read_xlsx(data):
    if openpyxl is None:
        raise ImportProblem("Excel files are not enabled on this server yet. Please save the file as CSV and upload that.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > MAX_UNZIPPED_BYTES:
                raise ImportProblem("This Excel file is unexpectedly large. Please use the sample file.")
        workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except ImportProblem:
        raise
    except Exception:
        raise ImportProblem("This does not look like a valid Excel (.xlsx) file. Please use the sample file.")
    try:
        for sheet in workbook.worksheets:
            rows = [list(row) for row in sheet.iter_rows(values_only=True, max_row=400)]
            if _find_header(rows) is not None:
                return rows
    finally:
        workbook.close()
    raise ImportProblem("Could not find the menu table. The first row of the table must have the headings "
                        "Date, Holiday, Veg / Dal, Roti, Salad / Papad / Rice, Curd / Sweet, Snack Type, Snack Name.")


def _read_csv(data):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    first = text.splitlines()[0] if text.strip() else ""
    delimiter = max((",", ";", "\t"), key=first.count)
    return [list(row) for row in csv.reader(io.StringIO(text), delimiter=delimiter)][:400]


def _find_header(rows):
    """Return (row_index, {column_index: field}) for the first row that names a Date column and a menu column."""
    for index, row in enumerate(rows[:15]):
        mapping = {}
        for col, cell in enumerate(row):
            field_name = _ALIAS_TO_FIELD.get(_header_key(cell))
            if field_name and field_name not in mapping.values():
                mapping[col] = field_name
        if "date" in mapping.values() and any(f in mapping.values() for f in MENU_FIELDS):
            return index, mapping
    return None


def parse_upload(filename, data):
    """Parse an uploaded .xlsx/.csv into menu rows (up to two weeks). Raises ImportProblem for unusable files."""
    name = (filename or "").lower()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImportProblem("The file is larger than 1 MB. A menu file should be tiny; please check it.")
    if name.endswith(".xlsx"):
        rows = _read_xlsx(data)
    elif name.endswith(".csv"):
        rows = _read_csv(data)
    else:
        raise ImportProblem("Please upload an Excel (.xlsx) or CSV (.csv) file. Download the sample file to see the format.")
    header = _find_header(rows)
    if header is None:
        raise ImportProblem("Could not find the menu table. The first row of the table must have the headings "
                            "Date, Holiday, Veg / Dal, Roti, Salad / Papad / Rice, Curd / Sweet, Snack Type, Snack Name.")
    header_index, mapping = header

    parsed, warnings = {}, []
    for offset, row in enumerate(rows[header_index + 1:], start=header_index + 2):
        cells = {mapping[col]: row[col] for col in mapping if col < len(row)}
        if not any(_clean(v) for v in cells.values()):
            continue  # blank line
        day = _to_date(cells.get("date"))
        if day is None:
            warnings.append(f"Row {offset}: the date '{_clean(cells.get('date'))}' was not understood, so the row was skipped.")
            continue
        if day.weekday() == 6:
            warnings.append(f"Row {offset}: {day:%d %b %Y} is a Sunday. The menu covers Monday to Saturday, so it was skipped.")
            continue
        entry = {"is_holiday": _clean(cells.get("is_holiday")).lower() in _YES}
        for name_ in MENU_FIELDS:
            if name_ == "snacks":
                continue
            value = _clean(cells.get(name_))
            if len(value) > MAX_LENGTH[name_]:
                warnings.append(f"Row {offset}: one entry was longer than {MAX_LENGTH[name_]} characters and was shortened.")
                value = value[:MAX_LENGTH[name_]]
            entry[name_] = value
        kind, snack = split_snack(cells.get("snack_type"), cells.get("snacks"))
        if len(snack) > MAX_LENGTH["snacks"]:
            warnings.append(f"Row {offset}: the snack name was longer than {MAX_LENGTH['snacks']} characters and was shortened.")
            snack = snack[:MAX_LENGTH["snacks"]]
        entry["snack_type"], entry["snacks"] = kind, snack
        if entry["is_holiday"]:
            entry.update({name_: "" for name_ in MENU_FIELDS})  # same rule as the editor: holiday clears the menu
            entry["snack_type"] = "regular"
        if day in parsed:
            warnings.append(f"Row {offset}: {day:%d %b %Y} appears more than once; the last row was used.")
        parsed[day] = entry

    if not parsed:
        raise ImportProblem("No menu rows were found in the file. Fill at least one day under the headings.")
    monday = monday_of(min(parsed))
    limit = monday + timedelta(days=WINDOW_DAYS)
    week_rows = {d: v for d, v in sorted(parsed.items()) if d < limit}
    dropped = sorted(d for d in parsed if d >= limit)
    if dropped:
        warnings.append("The file covers more than two weeks. Only the two weeks starting %s were loaded; "
                        "upload the later dates separately." % monday.strftime("%d %b %Y"))
    return ParseResult(monday=monday, rows=week_rows, warnings=warnings)


def sample_rows(start_monday):
    """Two weeks of example rows: (date, holiday, veg, roti, rice, curd, snack_type, snack_name)."""
    out = []
    for week in range(2):
        for i, menu in enumerate(SAMPLE_MENU):
            day = start_monday + timedelta(days=week * 7 + i)
            closed = not any(menu)
            out.append((day, "Yes" if closed else "No", *menu))
    return out


def build_sample(start_monday):
    """Return (bytes, filename, content_type): a sample for this week and next week, starting at the given Monday."""
    rows = sample_rows(start_monday)
    stamp = f"{start_monday:%Y-%m-%d}"
    if openpyxl is None:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow([header for header, _ in SAMPLE_COLUMNS])
        for day, closed, *menu in rows:
            writer.writerow([day.isoformat(), closed, *menu])
        return out.getvalue().encode("utf-8-sig"), f"canteen_menu_sample_{stamp}.csv", "text/csv"

    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Menu"
    head_fill = PatternFill("solid", fgColor="D53639")
    week2_fill = PatternFill("solid", fgColor="FDF3E1")
    for col, (header, _) in enumerate(SAMPLE_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row, (day, closed, *menu) in enumerate(rows, start=2):
        ws.cell(row=row, column=1, value=day).number_format = "DD-MMM-YYYY (ddd)"
        ws.cell(row=row, column=2, value=closed)
        for col, value in enumerate(menu, start=3):
            ws.cell(row=row, column=col, value=value or None).alignment = Alignment(wrap_text=True, vertical="top")
        if day >= start_monday + timedelta(days=7):
            for col in range(1, 9):
                ws.cell(row=row, column=col).fill = week2_fill
    for letter, width in zip("ABCDEFGH", (22, 16, 34, 14, 28, 20, 24, 30)):
        ws.column_dimensions[letter].width = width
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"
    last = len(rows) + 1
    check = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    kinds = DataValidation(type="list", formula1='"Regular,Chef\'s Special"', allow_blank=True)
    ws.add_data_validation(check)
    ws.add_data_validation(kinds)
    check.add(f"B2:B{last}")
    kinds.add(f"G2:G{last}")

    guide = wb.create_sheet("How to fill")
    lines = [
        "How to fill the canteen menu (this week + next week)",
        "",
        "1. Use the 'Menu' sheet. One row per day, Monday to Saturday. The first 6 rows are THIS week, the shaded rows are NEXT week.",
        "2. The dates were set from the day you downloaded the file. Do not change them.",
        "3. Holiday (Yes/No): type Yes if the canteen is closed. The menu of that day is then ignored.",
        "4. Veg / Dal, Roti, Salad / Papad / Rice, Curd / Sweet: type the dishes, separated by commas.",
        "5. Snack Type: choose Regular or Chef's Special.",
        "     Regular - the usual snacks, for example Maggie, Bhel, Sandwich.",
        "     Chef's Special - something special. On those days there are no regular snacks.",
        "6. Snack Name: the dish. Example: Regular + Maggie, or Chef's Special + Pasta in white sauce.",
        "   (Writing  Chef's Special - Pasta  in the Snack Name cell also works.)",
        "7. Leave a cell empty if nothing is served for it. Do not rename or reorder the headings in row 1.",
        "8. Save the file (.xlsx or .csv), then in Content Manager open Canteen Menu and use 'Upload menu file'.",
        "9. The form is filled in for you to check. Nothing is saved until you press 'Save menu'.",
        "",
        "The dishes in the sample are only examples. Replace them with the real menu.",
    ]
    for row, text in enumerate(lines, start=1):
        ws2 = guide.cell(row=row, column=1, value=text)
        if row == 1:
            ws2.font = Font(bold=True, size=14, color="D53639")
    guide.column_dimensions["A"].width = 118
    buffer = io.BytesIO()
    wb.save(buffer)
    return (buffer.getvalue(), f"canteen_menu_sample_{stamp}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
