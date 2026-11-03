import streamlit as st

from db.database import (
    create_class,
    create_teacher,
    delete_teacher_profile,
    get_classes,
    get_teachers,
    update_class,
    update_teacher,
)


@st.dialog("Xác nhận xóa hồ sơ giáo viên")
def confirm_delete_teacher(teacher_id, teacher_code, full_name):
    st.warning(f"Bạn sắp xóa hồ sơ giáo viên {teacher_code} – {full_name}.")
    st.info(
        "Hồ sơ sẽ được ngừng hoạt động để bảo toàn dữ liệu. "
        "Thông tin phân công chủ nhiệm và các hồ sơ liên quan sẽ được giữ nguyên."
    )
    confirm_col, cancel_col = st.columns(2)
    if confirm_col.button(
        "Xác nhận xóa",
        type="primary",
        key=f"confirm_delete_teacher_{teacher_id}",
    ):
        try:
            result = delete_teacher_profile(teacher_id)
            detail = (
                f" {result['assigned_class_count']} lớp vẫn giữ nguyên liên kết giáo viên chủ nhiệm."
                if result["assigned_class_count"]
                else ""
            )
            st.session_state["teacher_management_notice"] = (
                f"Đã xóa hồ sơ giáo viên {result['teacher_code']} – "
                f"{full_name}.{detail}"
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if cancel_col.button("Hủy", key=f"cancel_delete_teacher_{teacher_id}"):
        st.rerun()


notice = st.session_state.pop("teacher_management_notice", None)
if notice:
    st.success(notice)

st.title("Quản lý lớp học và giáo viên")
st.caption("Thiết lập lớp, giáo viên chủ nhiệm và danh sách giáo viên.")

classes = get_classes(active_only=False)
teachers = get_teachers(active_only=False)
teacher_map = {row.id: row for row in teachers}

st.subheader("Danh sách lớp học")
st.dataframe(
    [
        {
            "Mã lớp": row.class_code,
            "Tên lớp": row.name,
            "Giáo viên chủ nhiệm": (
                teacher_map[row.homeroom_teacher_id].full_name
                if row.homeroom_teacher_id in teacher_map else "Chưa phân công"
            ),
            "Trạng thái": "Đang hoạt động" if row.active else "Ngừng hoạt động",
        }
        for row in classes
    ],
    width="stretch",
    hide_index=True,
)

class_tabs = st.tabs(["Thêm lớp", "Cập nhật lớp", "Giáo viên"])
with class_tabs[0]:
    with st.form("create_class_form", clear_on_submit=True):
        class_code = st.text_input("Mã lớp (để trống để tự tạo)", placeholder="Ví dụ: 10A1")
        class_name = st.text_input("Tên lớp", placeholder="Ví dụ: Lớp 10A1")
        teacher_options = [None] + [row.id for row in teachers if row.active]
        advisor_id = st.selectbox(
            "Giáo viên chủ nhiệm",
            teacher_options,
            format_func=lambda value: (
                "Chưa phân công" if value is None else teacher_map[value].full_name
            ),
        )
        create_submitted = st.form_submit_button("Tạo lớp", type="primary")
    if create_submitted:
        try:
            create_class(class_name, class_code or None, advisor_id)
            st.success("Đã tạo lớp học.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

with class_tabs[1]:
    if not classes:
        st.info("Chưa có lớp học.")
    else:
        class_by_id = {row.id: row for row in classes}
        selected_class_id = st.selectbox(
            "Chọn lớp",
            list(class_by_id),
            format_func=lambda value: (
                f"{class_by_id[value].class_code} · {class_by_id[value].name}"
            ),
        )
        selected_class = class_by_id[selected_class_id]
        with st.form("edit_class_form"):
            updated_code = st.text_input("Mã lớp", value=selected_class.class_code)
            updated_name = st.text_input("Tên lớp", value=selected_class.name)
            active = st.checkbox("Lớp đang hoạt động", value=selected_class.active)
            advisor_options = [None] + [row.id for row in teachers if row.active]
            current_advisor = (
                selected_class.homeroom_teacher_id
                if selected_class.homeroom_teacher_id in advisor_options else None
            )
            updated_advisor = st.selectbox(
                "Giáo viên chủ nhiệm",
                advisor_options,
                index=advisor_options.index(current_advisor),
                format_func=lambda value: (
                    "Chưa phân công" if value is None else teacher_map[value].full_name
                ),
            )
            update_submitted = st.form_submit_button("Lưu thay đổi", type="primary")
        if update_submitted:
            try:
                update_class(
                    selected_class_id,
                    updated_name,
                    updated_code,
                    updated_advisor,
                    active,
                )
                st.success("Đã cập nhật lớp.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

with class_tabs[2]:
    st.caption("Tài khoản giáo viên chỉ phục vụ quản lý hồ sơ; đăng nhập và phân quyền chưa được triển khai.")
    with st.expander("Thêm giáo viên"):
        with st.form("create_teacher_form", clear_on_submit=True):
            teacher_code = st.text_input("Mã giáo viên")
            teacher_name = st.text_input("Họ và tên giáo viên")
            username = st.text_input("Tên tài khoản (không bắt buộc)")
            teacher_submitted = st.form_submit_button("Thêm giáo viên")
        if teacher_submitted:
            try:
                create_teacher(teacher_code, teacher_name, username)
                st.success("Đã thêm giáo viên.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    if teachers:
        teacher_by_id = {row.id: row for row in teachers}
        teacher_id = st.selectbox(
            "Chọn giáo viên để cập nhật",
            list(teacher_by_id),
            format_func=lambda value: (
                f"{teacher_by_id[value].teacher_code} · {teacher_by_id[value].full_name}"
            ),
        )
        selected_teacher = teacher_by_id[teacher_id]
        with st.form("edit_teacher_form"):
            updated_teacher_code = st.text_input(
                "Mã giáo viên",
                value=selected_teacher.teacher_code,
            )
            updated_teacher_name = st.text_input(
                "Họ và tên",
                value=selected_teacher.full_name,
            )
            updated_username = st.text_input(
                "Tên tài khoản",
                value=selected_teacher.username or "",
            )
            teacher_active = st.checkbox(
                "Đang công tác",
                value=selected_teacher.active,
            )
            teacher_action_cols = st.columns(2)
            teacher_update_submitted = teacher_action_cols[0].form_submit_button(
                "Lưu hồ sơ giáo viên",
                type="primary",
            )
            teacher_delete_submitted = teacher_action_cols[1].form_submit_button(
                "Xóa hồ sơ",
                disabled=not selected_teacher.active,
            )
        if teacher_update_submitted:
            try:
                update_teacher(
                    teacher_id,
                    updated_teacher_code,
                    updated_teacher_name,
                    updated_username,
                    teacher_active,
                )
                st.success("Đã cập nhật hồ sơ giáo viên.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if teacher_delete_submitted:
            confirm_delete_teacher(
                teacher_id,
                selected_teacher.teacher_code,
                selected_teacher.full_name,
            )
