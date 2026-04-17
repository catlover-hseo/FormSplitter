from __future__ import annotations

from datetime import datetime

import streamlit as st

try:
    from formsplitter.constants import APP_TITLE
    from formsplitter.parsing import (
        extract_event_date_from_dataframe,
        extract_event_date_from_html,
        get_performer_group_count,
        load_csv_with_fallback,
    )
    from formsplitter.service import generate_pdf_zip
    from formsplitter.ui import (
        apply_custom_styles,
        get_performer_names,
        render_guide,
        render_hero,
        render_preflight_metrics,
        render_validation_summary,
    )
    from formsplitter.validation import build_validation_summary, compare_names_against_reference
except ModuleNotFoundError:
    from constants import APP_TITLE
    from parsing import (
        extract_event_date_from_dataframe,
        extract_event_date_from_html,
        get_performer_group_count,
        load_csv_with_fallback,
    )
    from service import generate_pdf_zip
    from ui import (
        apply_custom_styles,
        get_performer_names,
        render_guide,
        render_hero,
        render_preflight_metrics,
        render_validation_summary,
    )
    from validation import build_validation_summary, compare_names_against_reference


RESULT_KEYS = (
    "result_zip",
    "result_zip_name",
    "result_count",
    "result_group_count",
    "result_error",
    "event_date_input",
)


def reset_app_state() -> None:
    for key in RESULT_KEYS:
        st.session_state.pop(key, None)


def detect_event_date(dataframe, html_file) -> str:
    if dataframe is not None:
        detected = extract_event_date_from_dataframe(dataframe)
        if detected:
            return detected

    if html_file is not None:
        detected = extract_event_date_from_html(html_file.getvalue())
        if detected:
            return detected

    return datetime.now().strftime("%Y-%m-%d")


def clear_result_state() -> None:
    for key in ("result_zip", "result_zip_name", "result_count", "result_group_count", "result_error"):
        st.session_state.pop(key, None)


def render_name_preview(performer_names: list[str]) -> None:
    if not performer_names:
        return

    with st.expander("연주자 명단 미리보기"):
        st.write("\n".join(f"{index}. {name}" for index, name in enumerate(performer_names, start=1)))


def render_matching_notice(performer_names: list[str], dataframe) -> None:
    if not performer_names or dataframe is None:
        return

    performer_group_count = get_performer_group_count(dataframe)
    if len(performer_names) > performer_group_count:
        st.warning(
            "명단 수가 CSV의 연주자 세트 수보다 많습니다. 앞에서부터 매칭 가능한 인원까지만 PDF가 생성됩니다."
        )
    elif len(performer_names) < performer_group_count:
        st.info(
            "CSV의 연주자 세트 수가 더 많습니다. 현재 명단에 있는 인원 수만큼만 PDF를 생성합니다."
        )


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🎼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    apply_custom_styles()
    render_hero()
    render_guide()

    st.markdown('<div class="section-label">Input Setup</div>', unsafe_allow_html=True)
    source_mode = st.radio(
        "연주자 명단 준비 방식",
        ("HTML에서 자동 추출", "명단 직접 입력"),
        horizontal=True,
        help="CSV는 필수입니다. 명단은 HTML 자동 추출과 직접 입력 중 하나를 고를 수 있습니다.",
    )

    left_col, right_col = st.columns([1.08, 1], gap="large")
    html_file = None
    roster_text = ""

    with left_col:
        if source_mode == "HTML에서 자동 추출":
            st.markdown('<div class="section-label">Performer Source</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="subnote">구글 폼 HTML 사본에서 연주자 순서와 이름을 자동 추출합니다.</div>',
                unsafe_allow_html=True,
            )
            html_file = st.file_uploader(
                "HTML 파일(평가지 사본)",
                type=["html", "htm"],
                key="html_uploader",
                on_change=reset_app_state,
            )
        else:
            st.markdown('<div class="section-label">Performer List</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="subnote">공식 명단을 한 줄에 한 명씩 붙여넣으면 됩니다. 번호가 있어도 자동으로 정리합니다.</div>',
                unsafe_allow_html=True,
            )
            roster_text = st.text_area(
                "연주자 명단 직접 입력",
                height=260,
                placeholder="1. 강사랑\n2. 최광\n3. 손율이\n4. 김태은",
            )

    with right_col:
        st.markdown('<div class="section-label">Response Data</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="subnote">평균 점수와 익명 피드백 원본은 응답 CSV에 들어 있으므로 반드시 업로드해 주세요.</div>',
            unsafe_allow_html=True,
        )
        csv_file = st.file_uploader(
            "CSV 파일(응답 결과)",
            type=["csv"],
            key="csv_uploader",
            on_change=reset_app_state,
        )

    st.markdown('<div class="section-label">Optional Name Check</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subnote">공식 명단이나 학사 명단이 있다면 붙여넣어 현재 명단과 자동 대조할 수 있습니다. 선택 입력입니다.</div>',
        unsafe_allow_html=True,
    )
    reference_roster_text = st.text_area(
        "검증용 기준 명단(선택)",
        height=140,
        placeholder="강사랑\n최광\n손율이\n김태은",
        help="현재 명단과 비교해 오타 후보나 누락 이름을 보여줍니다.",
    )

    performer_names, roster_message = get_performer_names(source_mode, html_file, roster_text)
    dataframe = None
    csv_error = ""
    if csv_file is not None:
        try:
            dataframe = load_csv_with_fallback(csv_file.getvalue())
        except Exception as exc:
            csv_error = str(exc)

    detected_event_date = detect_event_date(dataframe, html_file)
    if "event_date_input" not in st.session_state:
        st.session_state["event_date_input"] = detected_event_date

    validation_summary_df = None
    if dataframe is not None and performer_names:
        validation_summary_df = build_validation_summary(dataframe, performer_names)

    name_comparison = compare_names_against_reference(performer_names, reference_roster_text)

    st.markdown('<div class="section-label">Preflight Check</div>', unsafe_allow_html=True)
    render_preflight_metrics(performer_names, dataframe, st.session_state["event_date_input"])

    if performer_names:
        st.success(roster_message)
    else:
        st.info(roster_message)

    if csv_error:
        st.error(csv_error)

    render_name_preview(performer_names)
    render_matching_notice(performer_names, dataframe)
    render_validation_summary(validation_summary_df)

    if performer_names and name_comparison is not None:
        st.markdown('<div class="section-label">Name Comparison</div>', unsafe_allow_html=True)
        compare_col1, compare_col2, compare_col3 = st.columns(3)
        compare_col1.metric("기준 명단 수", len(name_comparison.reference_names))
        compare_col2.metric("정확 일치", name_comparison.exact_match_count)
        compare_col3.metric("검토 대상", len(name_comparison.current_only))

        if name_comparison.current_only:
            st.warning(
                "기준 명단과 완전 일치하지 않는 이름이 있습니다. 아래 추천 후보를 확인해 주세요."
            )
        else:
            st.success("현재 명단이 기준 명단과 모두 일치합니다.")

        with st.expander("기준 명단 대조 결과 보기", expanded=bool(name_comparison.current_only)):
            if not name_comparison.suggestions_df.empty:
                st.dataframe(name_comparison.suggestions_df, use_container_width=True, hide_index=True)
            elif name_comparison.current_only:
                st.info("자동 추천 후보는 찾지 못했지만, 아래 이름들은 수동 확인이 필요합니다.")

            if name_comparison.current_only:
                st.markdown(
                    "**현재 명단에서 수동 확인이 필요한 이름**\n\n"
                    + "\n".join(f"- {name}" for name in name_comparison.current_only)
                )

            if name_comparison.reference_only:
                st.markdown(
                    "**기준 명단에는 있으나 현재 명단에는 없는 이름**\n\n"
                    + "\n".join(f"- {name}" for name in name_comparison.reference_only)
                )

    st.markdown('<div class="section-label">Output Option</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subnote">PDF 파일명에 들어갈 학내 날짜를 확인해 주세요. 자동 감지값이 맞지 않으면 직접 수정하실 수 있습니다.</div>',
        unsafe_allow_html=True,
    )
    st.text_input(
        "PDF 파일명용 학내 날짜",
        key="event_date_input",
        help="예: 2026-04-08",
    )

    if st.button("PDF 자동 생성 시작", type="primary", use_container_width=True):
        clear_result_state()

        if dataframe is None:
            st.session_state["result_error"] = "응답 CSV를 먼저 업로드해 주세요."
        elif not performer_names:
            st.session_state["result_error"] = (
                "연주자 명단을 먼저 준비해 주세요. HTML 자동 추출 또는 직접 입력 둘 중 하나가 필요합니다."
            )
        else:
            try:
                result = generate_pdf_zip(
                    dataframe=dataframe,
                    performer_names=performer_names,
                    event_date_label=st.session_state["event_date_input"],
                )
                st.session_state["result_zip"] = result.zip_bytes
                st.session_state["result_zip_name"] = result.zip_filename
                st.session_state["result_count"] = result.created_count
                st.session_state["result_group_count"] = result.matched_count
            except Exception as exc:
                st.session_state["result_error"] = str(exc)

    if "result_error" in st.session_state:
        st.error(st.session_state["result_error"])

    if "result_zip" in st.session_state:
        st.success(
            f"총 {st.session_state['result_count']}개의 PDF를 생성했습니다. "
            f"(실제 매칭된 연주자 수: {st.session_state['result_group_count']}명)"
        )
        st.download_button(
            label="PDF ZIP 다운로드",
            data=st.session_state["result_zip"],
            file_name=st.session_state["result_zip_name"],
            mime="application/zip",
            use_container_width=True,
        )

    with st.expander("오타 방지 설계 아이디어 보기"):
        st.markdown(
            """
            - 현재 앱은 연주자 이름을 응답자가 직접 적는 구조가 아니라, `명단 순서`와 `CSV 열 순서`를 맞춰서 처리하므로 `최광`과 `최굉` 같은 오타 문제를 원천적으로 거의 피할 수 있습니다.
            - 만약 앞으로 이름을 직접 입력받는 폼으로 바뀐다면, 가장 안전한 방법은 `공식 명단 기준값`을 따로 두고 자동 매칭하는 것입니다.
            - 추천 로직은 `정확 일치 -> 공백/특수문자 정리 후 재비교 -> 유사도 매칭(예: 최광/최굉) -> 애매하면 관리자 확인` 순서입니다.
            - 여기에 `학번`, `전공`, `연주 순서` 중 하나만 추가로 같이 받으면 이름 오타가 있어도 훨씬 안정적으로 보정할 수 있습니다.
            """
        )


if __name__ == "__main__":
    main()
