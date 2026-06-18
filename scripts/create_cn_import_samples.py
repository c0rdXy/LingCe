#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文五题型 AI 导入测试素材。"""

import csv
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


QUESTIONS = [
    {
        "type": "single",
        "type_name": "单选题",
        "question": "Python 中用于定义函数的关键字是哪一个？",
        "options": ["class", "def", "return", "import"],
        "answer": "B",
        "explanation": "Python 使用 def 关键字定义函数。",
    },
    {
        "type": "multiple",
        "type_name": "多选题",
        "question": "下列哪些属于常见的关系型数据库？",
        "options": ["MySQL", "PostgreSQL", "Redis", "SQLite"],
        "answer": "ABD",
        "explanation": "MySQL、PostgreSQL、SQLite 是关系型数据库；Redis 通常是键值型内存数据库。",
    },
    {
        "type": "judgement",
        "type_name": "判断题",
        "question": "HTTP 状态码 404 通常表示服务器内部错误。",
        "options": [],
        "answer": "错误",
        "explanation": "404 表示资源未找到；服务器内部错误通常是 500。",
    },
    {
        "type": "fill",
        "type_name": "填空题",
        "question": "在 Git 中，用于查看当前工作区状态的命令是 git ____。",
        "options": [],
        "answer": "status",
        "explanation": "git status 可查看暂存区、工作区和分支状态。",
    },
    {
        "type": "short",
        "type_name": "简答题",
        "question": "请简述单元测试的主要作用。",
        "options": [],
        "answer": "单元测试用于验证最小代码单元的行为是否符合预期，帮助尽早发现回归问题，并提升代码修改时的信心。",
        "explanation": "答案应包含验证功能、发现问题、降低回归风险等要点。",
    },
    {
        "type": "single",
        "type_name": "单选题",
        "question": "在计算机网络中，DNS 的主要作用是什么？",
        "options": ["加密网络通信", "把域名解析为 IP 地址", "压缩网页内容", "检测硬盘坏道"],
        "answer": "B",
        "explanation": "DNS 负责域名和 IP 地址之间的解析。",
    },
    {
        "type": "multiple",
        "type_name": "多选题",
        "question": "下列哪些做法有助于保护账号安全？",
        "options": ["启用双因素认证", "多个网站使用同一个简单密码", "定期更新密码", "不随意点击陌生链接"],
        "answer": "ACD",
        "explanation": "双因素认证、定期更新密码、不点击陌生链接都有助于安全；复用简单密码风险较高。",
    },
    {
        "type": "judgement",
        "type_name": "判断题",
        "question": "JSON 是一种常见的数据交换格式。",
        "options": [],
        "answer": "正确",
        "explanation": "JSON 结构清晰、易读，常用于接口数据交换。",
    },
]


def lines_for(question, index):
    lines = [
        f"第 {index} 题 [{question['type_name']}]",
        f"Type: {question['type']}",
        f"题干：{question['question']}",
    ]
    for option_index, option in enumerate(question["options"]):
        lines.append(f"{chr(ord('A') + option_index)}. {option}")
    lines.extend([
        f"答案：{question['answer']}",
        f"解析：{question['explanation']}",
        "",
    ])
    return lines


def create_docx(path: Path, paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in paragraphs)
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", doc_xml)


def create_xlsx(path: Path):
    rows = [["type", "type_name", "question", "option_a", "option_b", "option_c", "option_d", "answer", "explanation"]]
    for question in QUESTIONS:
        options = question["options"] + ["", "", "", ""]
        rows.append([
            question["type"],
            question["type_name"],
            question["question"],
            *options[:4],
            question["answer"],
            question["explanation"],
        ])

    shared = []
    shared_index = {}

    def shared_id(value):
        text = str(value)
        if text not in shared_index:
            shared_index[text] = len(shared)
            shared.append(text)
        return shared_index[text]

    def col_name(number):
        name = ""
        while number:
            number, rem = divmod(number - 1, 26)
            name = chr(65 + rem) + name
        return name

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            f'<c r="{col_name(col_index)}{row_index}" t="s"><v>{shared_id(value)}</v></c>'
            for col_index, value in enumerate(row, start=1)
        )
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')

    shared_items = "".join(f"<si><t>{escape(text)}</t></si>" for text in shared)
    sst_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">{shared_items}</sst>'
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Questions" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/sharedStrings.xml", sst_xml)


def create_pdf(path: Path):
    lines = []
    for index, question in enumerate(QUESTIONS, start=1):
        lines.extend([
            f"Question {index} [{question['type']}]",
            f"Type: {question['type_name']}",
            f"Q: {question['question']}",
        ])
        for option_index, option in enumerate(question["options"]):
            lines.append(f"{chr(ord('A') + option_index)}. {option}")
        lines.extend([
            f"Answer: {question['answer']}",
            f"Explanation: {question['explanation']}",
            "",
        ])

    def text_hex(text):
        return (b"\xfe\xff" + text.encode("utf-16-be")).hex().upper()

    content = ["BT", "/F1 10 Tf", "50 790 Td", "15 TL"]
    for line in lines:
        content.append(f"<{text_hex(line[:60])}> Tj")
        content.append("T*")
    content.append("ET")
    stream = "\n".join(content).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(pdf))


def main():
    output_dir = Path("import_question_samples_cn")
    output_dir.mkdir(exist_ok=True)
    output_dir.joinpath("source_questions_cn.json").write_text(
        json.dumps(QUESTIONS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    paragraphs = [line for index, question in enumerate(QUESTIONS, start=1) for line in lines_for(question, index)]
    output_dir.joinpath("cn_questions.txt").write_text("\n".join(paragraphs), encoding="utf-8")

    md = ["# 中文五题型题库示例", "", "用于测试 LingCe 的 AI 解析导入功能。", ""]
    for index, question in enumerate(QUESTIONS, start=1):
        md.extend([
            f"## 第 {index} 题",
            "",
            f"**题型：** {question['type_name']}",
            f"**Type:** {question['type']}",
            "",
            f"**题干：** {question['question']}",
            "",
        ])
        for option_index, option in enumerate(question["options"]):
            md.append(f"- {chr(ord('A') + option_index)}. {option}")
        md.extend(["", f"**答案：** {question['answer']}", f"**解析：** {question['explanation']}", ""])
    output_dir.joinpath("cn_questions.md").write_text("\n".join(md), encoding="utf-8")

    with output_dir.joinpath("cn_questions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["type", "type_name", "question", "option_a", "option_b", "option_c", "option_d", "answer", "explanation"])
        for question in QUESTIONS:
            options = question["options"] + ["", "", "", ""]
            writer.writerow([
                question["type"],
                question["type_name"],
                question["question"],
                *options[:4],
                question["answer"],
                question["explanation"],
            ])

    create_docx(output_dir / "cn_questions.docx", paragraphs)
    create_xlsx(output_dir / "cn_questions.xlsx")
    create_pdf(output_dir / "cn_questions.pdf")


if __name__ == "__main__":
    main()
