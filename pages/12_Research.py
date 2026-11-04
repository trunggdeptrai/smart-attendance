"""Trang Đánh giá thực nghiệm: thống kê từ nhật ký nghiên cứu.

Mọi số liệu trên trang này được tính trực tiếp từ log thực tế do ứng dụng ghi
(research_logs/) hoặc từ kết quả chạy research/evaluate_recognition.py
(research_results/). Trang không tạo hay ước lượng số liệu.
"""

import pandas as pd
import streamlit as st

from core.paths import RESEARCH_LOG_DIR, RESEARCH_RESULT_DIR
from core.research_log import DECISION_LOG, RECOGNITION_LOG, is_enabled, read_log

REASON_LABELS = {
    "": "Khớp hồ sơ",
    "above_threshold": "Khoảng cách vượt ngưỡng",
    "margin_gap": "Hai ứng viên quá gần nhau",
    "no_majority": "Không đạt đa số phiếu K-NN",
    "low_contrast": "Ảnh quá tối/đồng nhất",
    "no_encoding": "Không trích xuất được đặc trưng",
    "invalid_image": "Ảnh không hợp lệ",
    "empty_model": "Mô hình rỗng",
}

st.title("Đánh giá thực nghiệm")
st.caption(
    "Số liệu được tính trực tiếp từ nhật ký do ứng dụng ghi trong quá trình sử dụng. "
    "Nhật ký không chứa ảnh hay vector khuôn mặt."
)
if not is_enabled():
    st.warning("Ghi nhật ký nghiên cứu đang tắt (SMART_ATTENDANCE_RESEARCH_LOG=0).")

recognition_tab, decision_tab, offline_tab = st.tabs(
    ["Nhật ký nhận diện", "Quyết định của giáo viên", "Kết quả đánh giá offline"]
)

with recognition_tab:
    events = read_log(RECOGNITION_LOG)
    if events.empty:
        st.info("Chưa có lượt nhận diện nào được ghi nhận.")
    else:
        events["timestamp"] = pd.to_datetime(events["timestamp"], errors="coerce")
        events["date"] = events["timestamp"].dt.date
        dates = sorted(events["date"].dropna().unique())
        selected = st.multiselect("Lọc theo ngày", dates, default=dates)
        sources = sorted(events["source"].dropna().unique())
        selected_sources = st.multiselect("Nguồn", sources, default=sources)
        view = events[events["date"].isin(selected) & events["source"].isin(selected_sources)]

        total = len(view)
        matched = int(view["is_match"].sum()) if total else 0
        latency = pd.to_numeric(view["latency_ms"], errors="coerce").dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Số lượt nhận diện", total)
        c2.metric("Khớp hồ sơ", f"{matched} ({matched / total:.1%})" if total else "0")
        c3.metric("Thời gian TB (ms)", f"{latency.mean():.0f}" if not latency.empty else "—")
        c4.metric("Trung vị / P95 (ms)", (
            f"{latency.median():.0f} / {latency.quantile(0.95):.0f}" if not latency.empty else "—"
        ))

        reasons = (
            view["reject_reason"].fillna("").astype(str)
            .map(lambda value: REASON_LABELS.get(value, value))
            .value_counts()
            .rename_axis("Kết quả")
            .reset_index(name="Số lượt")
        )
        st.markdown("**Phân bố kết quả / lý do từ chối**")
        st.dataframe(reasons, hide_index=True, width="stretch")

        distances = pd.to_numeric(view["distance"], errors="coerce").dropna()
        distances = distances[distances < 1.0]
        if not distances.empty:
            st.markdown("**Phân bố khoảng cách nhỏ nhất (càng nhỏ càng giống)**")
            histogram = pd.cut(distances, bins=[0, 0.3, 0.35, 0.4, 0.44, 0.48, 0.55, 0.6, 1.0])
            st.bar_chart(histogram.value_counts().sort_index().rename(lambda b: str(b)))
        st.download_button(
            "Tải nhật ký nhận diện (CSV)",
            view.drop(columns=["date"]).to_csv(index=False).encode("utf-8-sig"),
            file_name="recognition_events.csv",
            mime="text/csv",
        )

with decision_tab:
    decisions = read_log(DECISION_LOG)
    if decisions.empty:
        st.info("Chưa có quyết định xác nhận/điều chỉnh nào được ghi nhận.")
    else:
        counts = decisions["action"].value_counts()
        d1, d2, d3 = st.columns(3)
        d1.metric("Xác nhận kết quả nhận diện", int(counts.get("confirm", 0)))
        d2.metric("Ghi nhận thủ công", int(counts.get("manual", 0)))
        d3.metric("Điều chỉnh sau khi lưu", int(counts.get("correct", 0)))
        corrections = decisions[decisions["action"] == "correct"]
        if not corrections.empty:
            changed = corrections[
                corrections["predicted_code"].astype(str) != corrections["final_code"].astype(str)
            ]
            st.caption(
                f"Trong {len(corrections)} lần điều chỉnh có {len(changed)} lần đổi sang học sinh khác "
                "(dấu hiệu nhận nhầm cần đối chiếu với nhật ký nghiên cứu)."
            )
        st.dataframe(decisions, hide_index=True, width="stretch")
        st.download_button(
            "Tải nhật ký quyết định (CSV)",
            decisions.to_csv(index=False).encode("utf-8-sig"),
            file_name="teacher_decisions.csv",
            mime="text/csv",
        )

with offline_tab:
    st.caption(
        "Chạy `python -m research.evaluate_recognition --eval-dir <thư mục ảnh kiểm thử>` "
        "để tạo kết quả. Xem docs/RESEARCH_TOOLKIT.md."
    )
    summaries = sorted(RESEARCH_RESULT_DIR.glob("*/summary.csv"), reverse=True)
    if not summaries:
        st.info("Chưa có kết quả đánh giá offline.")
    else:
        chosen = st.selectbox("Lần chạy", summaries, format_func=lambda p: p.parent.name)
        st.dataframe(pd.read_csv(chosen, encoding="utf-8-sig"), hide_index=True, width="stretch")
        sweep = chosen.parent / "threshold_sweep.csv"
        if sweep.exists():
            sweep_df = pd.read_csv(sweep, encoding="utf-8-sig")
            st.markdown("**Quét ngưỡng (chiến lược 1-NN đối chứng)**")
            st.line_chart(sweep_df, x="threshold", y=["accuracy", "false_accept_rate", "false_reject_rate"])

st.caption(f"Thư mục nhật ký: {RESEARCH_LOG_DIR.name}/ · Thư mục kết quả: {RESEARCH_RESULT_DIR.name}/")
