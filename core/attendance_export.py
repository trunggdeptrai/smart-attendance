from datetime import date, datetime, time
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

EXPORT_COLUMNS = [
    "STT",
    "Mã học sinh",
    "Họ và tên",
    "Lớp",
    "Ngày",
    "Giờ vào",
    "Giờ ra",
    "Trạng thái",
]


def build_attendance_excel(records, title):
    if records.empty:
        raise ValueError("Không có dữ liệu điểm danh để xuất Excel.")

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Điểm danh"
    worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    title_cell = worksheet.cell(row=1, column=1, value=title)
    title_cell.font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1D4ED8")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    worksheet.row_dimensions[1].height = 28

    for column_index, column_name in enumerate(EXPORT_COLUMNS, start=1):
        cell = worksheet.cell(row=3, column=column_index, value=column_name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2563EB")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_index, record in enumerate(
        records[EXPORT_COLUMNS[1:]].itertuples(index=False, name=None),
        start=4,
    ):
        values = [row_index - 3, *record]
        for column_index, value in enumerate(values, start=1):
            cell = worksheet.cell(
                row=row_index,
                column=column_index,
                value=_excel_value(value, EXPORT_COLUMNS[column_index - 1]),
            )
            cell.alignment = Alignment(vertical="center")
        worksheet.cell(row=row_index, column=5).number_format = "dd/mm/yyyy"
        worksheet.cell(row=row_index, column=6).number_format = "hh:mm:ss"
        worksheet.cell(row=row_index, column=7).number_format = "hh:mm:ss"

    worksheet.freeze_panes = "A4"
    worksheet.auto_filter.ref = f"A3:H{worksheet.max_row}"
    for column, width in {
        "A": 8,
        "B": 18,
        "C": 30,
        "D": 16,
        "E": 15,
        "F": 16,
        "G": 16,
        "H": 24,
    }.items():
        worksheet.column_dimensions[column].width = width

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _excel_value(value, column_name):
    if value is None:
        return "Chưa ghi nhận"
    if column_name == "Ngày":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return "Chưa ghi nhận"
    if column_name in {"Giờ vào", "Giờ ra"}:
        if isinstance(value, time):
            return value
        try:
            return datetime.strptime(str(value), "%H:%M:%S").time()
        except ValueError:
            return "Chưa ghi nhận"
    if isinstance(value, float) and value != value:
        return "Chưa ghi nhận"
    return value
