import io

import pytest
from openpyxl import Workbook

from app.core.errors import AppError
from app.attachments.parsing import parse_document, split_into_chunks, validate_filename


def test_text_and_csv_parsers_return_searchable_text() -> None:
    assert "矩阵秩" in parse_document("lesson.md", "矩阵秩".encode()).text
    assert "姓名 | 得分" in parse_document("scores.csv", "姓名,得分\n匿名-1,90".encode()).text


def test_xlsx_parser_reads_student_attendance_records() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "出勤记录"
    sheet.append(["匿名编号", "第一次出勤", "第二次出勤"])
    sheet.append(["A01", "出勤", "缺勤"])
    content = io.BytesIO()
    workbook.save(content)

    parsed = parse_document("attendance.xlsx", content.getvalue())

    assert "[工作表: 出勤记录]" in parsed.text
    assert "匿名编号 | 第一次出勤 | 第二次出勤" in parsed.text
    assert "A01 | 出勤 | 缺勤" in parsed.text


def test_chunking_keeps_overlap_and_rejects_unsupported_files() -> None:
    chunks = split_into_chunks("abc\n" * 500)
    assert len(chunks) > 1
    assert validate_filename("report.PDF") == "report.PDF"
    with pytest.raises(AppError, match="unsupported_attachment_type"):
        validate_filename("image.png")
