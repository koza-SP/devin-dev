"""最小構成の xlsx ライター。

外部依存なしで複数シートの .xlsx を生成する。
inlineStr のみを使うため sharedStrings は持たない（Excel / Google スプレッドシート双方で開ける）。
"""

import zipfile
from xml.sax.saxutils import escape

MAX_COL_WIDTH = 60
MIN_COL_WIDTH = 8


def _col_letter(idx: int) -> str:
    """0 起点の列番号を A, B, ... AA 形式に変換する。"""
    name = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        name = chr(65 + rem) + name
    return name


def _display_width(text: str) -> int:
    """全角を2文字幅として概算する。"""
    return sum(2 if ord(ch) > 0x2000 else 1 for ch in text)


def _sheet_xml(rows, freeze_header=True):
    if not rows:
        rows = [[""]]
    ncols = max(len(r) for r in rows)

    widths = []
    for c in range(ncols):
        w = max(
            (_display_width(str(r[c])) for r in rows[:200] if c < len(r)),
            default=MIN_COL_WIDTH,
        )
        widths.append(max(MIN_COL_WIDTH, min(MAX_COL_WIDTH, w + 2)))

    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
    ]
    if freeze_header:
        out.append(
            '<sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            "</sheetView></sheetViews>"
        )
    out.append('<sheetFormatPr defaultRowHeight="15"/>')
    out.append("<cols>")
    for i, w in enumerate(widths):
        out.append(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>')
    out.append("</cols>")
    out.append("<sheetData>")

    for ri, row in enumerate(rows, start=1):
        style = 1 if (freeze_header and ri == 1) else 2
        out.append(f'<row r="{ri}">')
        for ci in range(ncols):
            value = str(row[ci]) if ci < len(row) and row[ci] is not None else ""
            ref = f"{_col_letter(ci)}{ri}"
            out.append(
                f'<c r="{ref}" s="{style}" t="inlineStr">'
                f"<is><t xml:space=\"preserve\">{escape(value)}</t></is></c>"
            )
        out.append("</row>")

    out.append("</sheetData>")
    if freeze_header and len(rows) > 1:
        out.append(f'<autoFilter ref="A1:{_col_letter(ncols - 1)}{len(rows)}"/>')
    out.append("</worksheet>")
    return "".join(out)


_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3">
<font><sz val="10"/><name val="Yu Gothic"/></font>
<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Yu Gothic"/></font>
<font><b/><sz val="10"/><name val="Yu Gothic"/></font>
</fonts>
<fills count="3">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF2B3A55"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border>
<left style="thin"><color rgb="FFBFC7D5"/></left>
<right style="thin"><color rgb="FFBFC7D5"/></right>
<top style="thin"><color rgb="FFBFC7D5"/></top>
<bottom style="thin"><color rgb="FFBFC7D5"/></bottom>
<diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
<alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">
<alignment vertical="top" wrapText="1"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def write_xlsx(path, sheets):
    """sheets: [(sheet_name, rows)] を .xlsx として書き出す。"""
    n = len(sheets)

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for i in range(1, n + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    wb = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>',
    ]
    for i, (name, _) in enumerate(sheets, start=1):
        wb.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
    wb.append("</sheets></workbook>")

    wb_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i in range(1, n + 1):
        wb_rels.append(
            f'<Relationship Id="rId{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
        )
    wb_rels.append(
        f'<Relationship Id="rId{n + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    wb_rels.append("</Relationships>")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(content_types))
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(wb_rels))
        z.writestr("xl/styles.xml", _STYLES)
        for i, (_, rows) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))
