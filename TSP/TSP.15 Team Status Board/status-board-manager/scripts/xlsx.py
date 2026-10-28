# -*- coding: utf-8 -*-
"""A small Excel workbook reader and writer, standard library only.

Writes what the status board needs and nothing more: sheets of text and
numbers, a bold header row, column widths, a frozen header, one table with
its filter, and list validations. Reads any workbook Excel or Copilot saves:
shared or inline strings, numbers, booleans and date serials, sheets by name.
"""
import io
import re
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
EPOCH = date(1899, 12, 30)


def col_letter(i):
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def serial_to_date(v):
    return (EPOCH + timedelta(days=int(float(v)))).isoformat()


# ─── Reading ─────────────────────────────────────────────────────────────────

def read(path):
    """{sheet name: [[cell values as str], ...]}, rows in order, padded to
    their widest. Numbers come back as text ('12', not '12.0'); a cell
    whose number format is a date comes back as YYYY-MM-DD."""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        date_styles = _date_styles(z, names)
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
        out = {}
        for sh in wb.find("m:sheets", NS).findall("m:sheet", NS):
            rid = sh.get("{%s}id" % NS["r"])
            t = target[rid].lstrip("/")
            part = t if t.startswith("xl/") else "xl/" + t
            out[sh.get("name")] = _sheet_rows(ET.fromstring(z.read(part)), shared, date_styles)
        return out


def _date_styles(z, names):
    """Indexes of cell styles whose number format shows a date."""
    if "xl/styles.xml" not in names:
        return set()
    root = ET.fromstring(z.read("xl/styles.xml"))
    custom = {}
    nf = root.find("m:numFmts", NS)
    if nf is not None:
        for f in nf.findall("m:numFmt", NS):
            custom[int(f.get("numFmtId"))] = f.get("formatCode") or ""
    out = set()
    xfs = root.find("m:cellXfs", NS)
    if xfs is None:
        return out
    for i, xf in enumerate(xfs.findall("m:xf", NS)):
        fid = int(xf.get("numFmtId") or 0)
        code = custom.get(fid, "")
        if 14 <= fid <= 22 or (code and re.search(r"[dmy]", re.sub(r'"[^"]*"|\[[^\]]*\]', "", code), re.I)
                               and not re.search(r"[h]", code, re.I)):
            out.add(i)
    return out


def _sheet_rows(root, shared, date_styles):
    rows = []
    data = root.find("m:sheetData", NS)
    if data is None:
        return rows
    for r in data.findall("m:row", NS):
        idx = int(r.get("r")) - 1 if r.get("r") else len(rows)
        while len(rows) < idx:
            rows.append([])
        cells = []
        for c in r.findall("m:c", NS):
            ci = col_index(c.get("r")) if c.get("r") else len(cells)
            while len(cells) < ci:
                cells.append("")
            cells.append(_cell_value(c, shared, date_styles))
        rows.append(cells)
    width = max([len(r) for r in rows] or [0])
    return [r + [""] * (width - len(r)) for r in rows]


def _cell_value(c, shared, date_styles):
    t = c.get("t")
    v = c.find("m:v", NS)
    if t == "inlineStr":
        is_ = c.find("m:is", NS)
        return "".join(x.text or "" for x in is_.iter("{%s}t" % NS["m"])) if is_ is not None else ""
    if v is None or v.text is None:
        return ""
    if t == "s":
        return shared[int(v.text)]
    if t == "b":
        return "TRUE" if v.text == "1" else "FALSE"
    if t in ("str", "e"):
        return v.text
    if c.get("s") and int(c.get("s")) in date_styles:
        return serial_to_date(v.text)
    num = float(v.text)
    return str(int(num)) if num.is_integer() else v.text


# ─── Writing ─────────────────────────────────────────────────────────────────

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
STYLE = {"wrap": 0, "bold": 1, "title": 2, "plain": 3}


class Sheet(object):
    """rows: lists of values (str, int, float or None). styles: {row index:
    style name} for whole rows. widths: column widths in characters. table:
    (name, header row index) to make the block from that row a table.
    validations: [(column index, [values], first row, last row)]."""

    def __init__(self, name, rows, widths=None, styles=None, table=None, validations=None, freeze=False):
        self.name, self.rows = name, rows
        self.widths, self.styles = widths or [], styles or {}
        self.table, self.validations, self.freeze = table, validations or [], freeze


def _cell(ref, value, style):
    s = ' s="%d"' % STYLE[style]
    if value is None or value == "":
        return '<c r="%s"%s/>' % (ref, s)
    if isinstance(value, bool):
        return '<c r="%s"%s t="b"><v>%d</v></c>' % (ref, s, 1 if value else 0)
    if isinstance(value, (int, float)):
        return '<c r="%s"%s><v>%s</v></c>' % (ref, s, value)
    return '<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, s, escape(str(value)))


def _sheet_xml(sh, table_rid):
    width = max([len(r) for r in sh.rows] or [1])
    last = "%s%d" % (col_letter(width - 1), max(len(sh.rows), 1))
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="%s" xmlns:r="%s">' % (NS["m"], NS["r"]),
           '<dimension ref="A1:%s"/>' % last]
    if sh.freeze and sh.table:
        top = sh.table[1] + 2
        out.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="%d" topLeftCell="A%d" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
                   % (top - 1, top))
    else:
        out.append('<sheetViews><sheetView workbookViewId="0"/></sheetViews>')
    out.append('<sheetFormatPr defaultRowHeight="15"/>')
    if sh.widths:
        out.append("<cols>%s</cols>" % "".join('<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, w)
                                              for i, w in enumerate(sh.widths)))
    out.append("<sheetData>")
    for ri, row in enumerate(sh.rows):
        style = sh.styles.get(ri, "wrap" if sh.table and ri > sh.table[1] else "plain")
        cells = "".join(_cell("%s%d" % (col_letter(ci), ri + 1), v, style) for ci, v in enumerate(row))
        out.append('<row r="%d">%s</row>' % (ri + 1, cells))
    out.append("</sheetData>")
    if sh.validations:
        out.append('<dataValidations count="%d">' % len(sh.validations))
        for ci, values, first, lastrow in sh.validations:
            col = col_letter(ci)
            out.append('<dataValidation type="list" allowBlank="1" showErrorMessage="1" '
                       'errorTitle="Not on the list" error="Pick one of the values in the list." '
                       'sqref="%s%d:%s%d"><formula1>"%s"</formula1></dataValidation>'
                       % (col, first + 1, col, lastrow + 1, escape(",".join(values))))
        out.append("</dataValidations>")
    out.append('<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>')
    if table_rid:
        out.append('<tableParts count="1"><tablePart r:id="%s"/></tableParts>' % table_rid)
    out.append("</worksheet>")
    return "".join(out)


def _table_xml(sh, tid):
    name, hr = sh.table
    header = sh.rows[hr]
    last_row = max(len(sh.rows), hr + 2)
    ref = "A%d:%s%d" % (hr + 1, col_letter(len(header) - 1), last_row)
    cols = "".join('<tableColumn id="%d" name="%s"/>' % (i + 1, escape(str(h))) for i, h in enumerate(header))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<table xmlns="%s" id="%d" name="%s" displayName="%s" ref="%s" totalsRowShown="0">'
            '<autoFilter ref="%s"/><tableColumns count="%d">%s</tableColumns>'
            '<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/>'
            '</table>' % (NS["m"], tid, name, name, ref, ref, len(header), cols))


def write(path, sheets, title=""):
    """Write the sheets to a new workbook at path, replacing any file there.
    A table needs a data row below its header, so an empty one is padded."""
    for sh in sheets:
        if sh.table and len(sh.rows) < sh.table[1] + 2:
            sh.rows.append([None] * len(sh.rows[sh.table[1]]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        tables = [i for i, s in enumerate(sheets) if s.table]
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '<Default Extension="xml" ContentType="application/xml"/>',
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
              '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>']
        for i in range(len(sheets)):
            ct.append('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1))
        for n, _ in enumerate(tables):
            ct.append('<Override PartName="/xl/tables/table%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>' % (n + 1))
        ct.append("</Types>")
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="%s">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                   '</Relationships>' % NS["rel"])
        z.writestr("docProps/core.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                   'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>%s</dc:title></cp:coreProperties>' % escape(title))
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="%s" xmlns:r="%s"><bookViews><workbookView/></bookViews><sheets>%s</sheets></workbook>'
                   % (NS["m"], NS["r"], "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(s.name), i + 1, i + 1)
                                                for i, s in enumerate(sheets))))
        rels = "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'
                       % (i + 1, i + 1) for i in range(len(sheets)))
        rels += '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(sheets) + 1)
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%s">%s</Relationships>' % (NS["rel"], rels))
        z.writestr("xl/styles.xml", STYLES)
        tnum = 0
        for i, sh in enumerate(sheets):
            rid = None
            if sh.table:
                tnum += 1
                rid = "rId1"
                z.writestr("xl/worksheets/_rels/sheet%d.xml.rels" % (i + 1),
                           '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%s">'
                           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table%d.xml"/>'
                           '</Relationships>' % (NS["rel"], tnum))
                z.writestr("xl/tables/table%d.xml" % tnum, _table_xml(sh, tnum))
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), _sheet_xml(sh, rid))
    with open(path, "wb") as fh:
        fh.write(buf.getvalue())
