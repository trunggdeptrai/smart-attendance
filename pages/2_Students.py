import zipfile

import pandas as pd
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from core.birth_date import DEFAULT_BIRTH_DATE, birth_date_input, compose_birth_date
from db.database import (
    create_student,
    deactivate_student,
    delete_student_profile,
    get_classes,
    get_students,
    update_student,
)


@st.dialog("Xác nhận xóa hồ sơ học sinh")
def confirm_delete_student(student_id, student_code, full_name):
    st.warning(f"Bạn sắp xóa hồ sơ học sinh {student_code} – {full_name}.")
    st.info(
        "Hồ sơ sẽ được chuyển sang trạng thái “Đã xóa”. "
        "Lịch sử điểm danh và dữ liệu khuôn mặt sẽ được giữ nguyên."
    )
    confirm_col, cancel_col = st.columns(2)
    if confirm_col.button(
        "Xác nhận xóa",
        type="primary",
        key=f"confirm_delete_student_{student_id}",
    ):
        try:
            result = delete_student_profile(student_id)
            retained_logs = result["attendance_count"]
            detail = (
                f" Đã bảo toàn {retained_logs} lượt điểm danh liên quan."
                if retained_logs else " Dữ liệu khuôn mặt (nếu có) vẫn được giữ nguyên."
            )
            st.session_state["student_management_notice"] = {
                "success": (
                    f"Đã xóa hồ sơ học sinh {result['student_code']} – "
                    f"{full_name}.{detail}"
                ),
                "errors": [],
            }
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if cancel_col.button("Hủy", key=f"cancel_delete_student_{student_id}"):
        st.rerun()


st.title("Quản lý học sinh")
st.caption("Quản lý hồ sơ, lớp học và trạng thái học tập của học sinh.")
notice = st.session_state.pop("student_management_notice", None)
if notice:
    if notice.get("success"):
        st.success(notice["success"])
    if notice.get("errors"):
        st.warning("\n".join(notice["errors"]))

classes = get_classes()
class_map = {row.id: row for row in classes}
students = get_students(active_only=False)

search = st.text_input(
    "Tìm kiếm học sinh",
    placeholder="Nhập mã học sinh, họ tên hoặc lớp...",
)
student_statuses = ["Đang học", "Tạm nghỉ", "Đã chuyển trường", "Đã xóa"]
active_filter = st.selectbox(
    "Trạng thái",
    ["Tất cả"] + student_statuses,
)
visible_students = [
    row for row in students
    if (active_filter == "Tất cả" or row.status == active_filter)
    and (
        not search
        or search.casefold() in row.student_code.casefold()
        or search.casefold() in row.full_name.casefold()
        or search.casefold() in row.class_name.casefold()
    )
]

st.dataframe(
    pd.DataFrame(
        [
        {
            "Mã học sinh": row.student_code,
            "Họ và tên": row.full_name,
            "Lớp": row.class_name,
            "Ngày sinh": row.date_of_birth,
            "Trạng thái": row.status,
        }
            for row in visible_students
        ],
        columns=["Mã học sinh", "Họ và tên", "Lớp", "Ngày sinh", "Trạng thái"],
    ),
    width="stretch",
    hide_index=True,
)

tab_add, tab_edit = st.tabs(["Thêm học sinh", "Cập nhật hồ sơ"])
with tab_add:
    if not classes:
        st.info("Hãy tạo lớp học trước khi thêm hồ sơ học sinh.")
    else:
        with st.form("add_student_form", clear_on_submit=True):
            name = st.text_input("Họ và tên")
            class_id = st.selectbox(
                "Lớp học",
                list(class_map),
                format_func=lambda value: (
                    f"{class_map[value].class_code} · {class_map[value].name}"
                ),
            )
            dob_parts = birth_date_input("Ngày sinh", DEFAULT_BIRTH_DATE, key="add_student_dob")
            submitted = st.form_submit_button("Thêm học sinh", type="primary")
        if submitted:
            try:
                dob = compose_birth_date(*dob_parts)
                code = create_student(name, class_id, dob)
                st.success(f"Đã tạo hồ sơ học sinh {code}.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        with st.expander("Nhập danh sách học sinh từ Excel"):
            st.caption("Cột bắt buộc: Họ và tên, Mã lớp. Cột Ngày sinh không bắt buộc.")
            excel_file = st.file_uploader(
                "Chọn tệp Excel",
                type=["xlsx", "xls"],
                key="student_excel_file",
            )
            if st.button(
                "Nhập danh sách",
                disabled=excel_file is None,
                key="import_students",
            ):
                try:
                    import_df = pd.read_excel(excel_file)
                except (
                    ImportError,
                    InvalidFileException,
                    OSError,
                    ValueError,
                    zipfile.BadZipFile,
                ) as error:
                    st.error(f"Không thể đọc tệp Excel: {error}")
                else:
                    required_columns = {"Họ và tên", "Mã lớp"}
                    missing_columns = required_columns - set(import_df.columns)
                    if missing_columns:
                        st.error(
                            "Thiếu cột bắt buộc: "
                            + ", ".join(sorted(missing_columns))
                        )
                    else:
                        class_ids = {
                            row.class_code.casefold(): row.id
                            for row in classes
                        }
                        imported = 0
                        errors = []
                        for row_number, row in import_df.iterrows():
                            name_value = row["Họ và tên"]
                            class_code_value = row["Mã lớp"]
                            if pd.isna(name_value) or pd.isna(class_code_value):
                                errors.append(
                                    f"Dòng {row_number + 2}: thiếu họ tên hoặc mã lớp."
                                )
                                continue
                            class_id_for_row = class_ids.get(
                                str(class_code_value).strip().casefold()
                            )
                            if class_id_for_row is None:
                                errors.append(
                                    f"Dòng {row_number + 2}: không tìm thấy lớp "
                                    f"{class_code_value}."
                                )
                                continue
                            birth_date = row.get("Ngày sinh")
                            if pd.isna(birth_date):
                                birth_date = None
                            try:
                                create_student(
                                    str(name_value),
                                    class_id_for_row,
                                    birth_date,
                                )
                                imported += 1
                            except ValueError as error:
                                errors.append(f"Dòng {row_number + 2}: {error}")
                        if imported:
                            st.session_state["student_management_notice"] = {
                                "success": f"Đã nhập {imported} hồ sơ học sinh.",
                                "errors": errors,
                            }
                            st.rerun()
                        elif errors:
                            st.warning("\n".join(errors))

with tab_edit:
    if not students:
        st.info("Chưa có hồ sơ học sinh.")
    elif not classes:
        st.warning("Không có lớp học đang hoạt động.")
    else:
        student_map = {row.student_code: row for row in students}
        selected_code = st.selectbox("Chọn học sinh", list(student_map))
        selected = student_map[selected_code]
        with st.form("edit_student_form"):
            edit_name = st.text_input("Họ và tên", value=selected.full_name)
            edit_class = st.selectbox(
                "Lớp học",
                list(class_map),
                index=(
                    list(class_map).index(selected.class_id)
                    if selected.class_id in class_map else 0
                ),
                format_func=lambda value: (
                    f"{class_map[value].class_code} · {class_map[value].name}"
                ),
            )
            edit_dob_parts = birth_date_input(
                "Ngày sinh",
                selected.date_of_birth,
                key=f"edit_student_dob_{selected.id}",
            )
            edit_status = st.selectbox(
                "Trạng thái",
                student_statuses,
                index=student_statuses.index(selected.status),
            )
            action_cols = st.columns(2)
            update_submitted = action_cols[0].form_submit_button(
                "Lưu thay đổi",
                type="primary",
            )
            delete_submitted = action_cols[1].form_submit_button(
                "Xóa hồ sơ",
                disabled=selected.status == "Đã xóa",
            )
        if update_submitted:
            try:
                edit_dob = compose_birth_date(*edit_dob_parts)
                update_student(
                    selected.id,
                    edit_name,
                    edit_class,
                    edit_status,
                    edit_dob,
                )
                st.success(f"Đã cập nhật hồ sơ {selected_code}.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        if delete_submitted:
            confirm_delete_student(
                selected.id,
                selected.student_code,
                selected.full_name,
            )

        if selected.status == "Đang học":
            st.warning("Hồ sơ được lưu trữ, không xóa dữ liệu điểm danh hoặc ảnh khuôn mặt.")
            if st.button("Chuyển trạng thái sang đã chuyển trường", key="deactivate_student"):
                try:
                    deactivate_student(selected.id)
                    st.success(f"Đã cập nhật trạng thái {selected_code}.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
