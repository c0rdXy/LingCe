#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资料文本提取服务。"""

import csv
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List


class DocumentImportError(RuntimeError):
    """资料文本提取失败。"""


class DocumentImportService:
    """从常见资料文件中提取纯文本。"""

    SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".docx", ".xlsx", ".pdf"}

    def extract_text(self, file_path: str) -> str:
        """根据文件扩展名提取文本。"""
        path = Path(file_path)
        if not path.exists():
            raise DocumentImportError("文件不存在")
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise DocumentImportError("暂不支持该文件格式")

        if suffix in {".txt", ".md", ".markdown"}:
            return self._read_text_file(path)
        if suffix == ".csv":
            return self._read_csv(path)
        if suffix == ".docx":
            return self._read_docx(path)
        if suffix == ".xlsx":
            return self._read_xlsx(path)
        if suffix == ".pdf":
            return self._read_pdf(path)
        raise DocumentImportError("暂不支持该文件格式")

    @staticmethod
    def _read_text_file(path: Path) -> str:
        """读取文本类文件，兼容常见中文编码。"""
        for encoding in ("utf-8", "utf-8-sig", "gbk"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentImportError("文本编码无法识别，请另存为 UTF-8 后重试")

    @classmethod
    def _read_csv(cls, path: Path) -> str:
        text = cls._read_text_file(path)
        rows = []
        for row in csv.reader(text.splitlines()):
            rows.append("\t".join(cell.strip() for cell in row if str(cell).strip()))
        return "\n".join(row for row in rows if row.strip())

    @staticmethod
    def _xml_text(element: ET.Element) -> str:
        return "".join(element.itertext()).strip()

    @classmethod
    def _read_docx(cls, path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                xml_text = archive.read("word/document.xml")
        except (KeyError, zipfile.BadZipFile, OSError) as exc:
            raise DocumentImportError("Word 文档读取失败") from exc

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise DocumentImportError("Word 文档内容解析失败") from exc

        paragraphs = []
        for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            text = cls._xml_text(paragraph)
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)

    @classmethod
    def _read_xlsx(cls, path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                shared_strings = cls._read_xlsx_shared_strings(archive)
                worksheet_names = sorted(
                    name
                    for name in archive.namelist()
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
                )
                rows = []
                for worksheet_name in worksheet_names:
                    rows.extend(cls._read_xlsx_sheet(archive.read(worksheet_name), shared_strings))
        except (zipfile.BadZipFile, OSError) as exc:
            raise DocumentImportError("Excel 文件读取失败") from exc
        return "\n".join(row for row in rows if row.strip())

    @classmethod
    def _read_xlsx_shared_strings(cls, archive: zipfile.ZipFile) -> List[str]:
        try:
            xml_text = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        return [cls._xml_text(item) for item in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si")]

    @classmethod
    def _read_xlsx_sheet(cls, xml_text: bytes, shared_strings: List[str]) -> List[str]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        rows = []
        for row in root.iter(f"{namespace}row"):
            cells = []
            for cell in row.iter(f"{namespace}c"):
                value = cls._read_xlsx_cell(cell, shared_strings, namespace)
                if value:
                    cells.append(value)
            if cells:
                rows.append("\t".join(cells))
        return rows

    @staticmethod
    def _read_xlsx_cell(cell: ET.Element, shared_strings: List[str], namespace: str) -> str:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            inline = cell.find(f"{namespace}is")
            return "".join(inline.itertext()).strip() if inline is not None else ""

        value_node = cell.find(f"{namespace}v")
        if value_node is None or value_node.text is None:
            return ""
        raw_value = value_node.text.strip()
        if cell_type == "s":
            try:
                return shared_strings[int(raw_value)]
            except (ValueError, IndexError):
                return raw_value
        return raw_value

    @staticmethod
    def _read_pdf(path: Path) -> str:
        reader_class = None
        try:
            from pypdf import PdfReader  # type: ignore
            reader_class = PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader  # type: ignore
                reader_class = PdfReader
            except ImportError as exc:
                raise DocumentImportError("PDF 解析需要安装 pypdf 或 PyPDF2") from exc

        try:
            reader = reader_class(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise DocumentImportError("PDF 文本提取失败，扫描版 PDF 暂不支持") from exc
        return "\n\n".join(page.strip() for page in pages if page.strip())
