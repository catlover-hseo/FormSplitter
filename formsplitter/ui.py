from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from .constants import (
        APP_TITLE,
        BRANDING_TEXT,
        EVALUATOR_INFO_COLUMN_COUNT,
        PDF_SUFFIX,
        PERFORMER_GROUP_SIZE,
    )
    from .parsing import extract_performer_names, extract_performer_names_from_text, normalize_date_label
except ImportError:
    from constants import (
        APP_TITLE,
        BRANDING_TEXT,
        EVALUATOR_INFO_COLUMN_COUNT,
        PDF_SUFFIX,
        PERFORMER_GROUP_SIZE,
    )
    from parsing import extract_performer_names, extract_performer_names_from_text, normalize_date_label


def apply_custom_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&family=Nanum+Myeongjo:wght@700;800&display=swap');

        :root {
            --adeo-ink: #211611;
            --adeo-brown: #5b3b2a;
            --adeo-accent: #b6513a;
            --adeo-bg: #f5efe5;
            --adeo-line: rgba(123, 92, 70, 0.18);
        }

        html, body, [class*="css"] {
            font-family: 'IBM Plex Sans KR', sans-serif;
        }

        .stApp {
            color: var(--adeo-ink);
            background:
                radial-gradient(circle at top right, rgba(182, 81, 58, 0.16), transparent 24%),
                radial-gradient(circle at 0% 20%, rgba(47, 106, 96, 0.12), transparent 22%),
                linear-gradient(180deg, #f8f2e8 0%, #f3ece1 100%);
        }

        section.main > div.block-container {
            max-width: 1120px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .hero-card {
            padding: 2.1rem 2.3rem 1.8rem 2.3rem;
            border-radius: 28px;
            border: 1px solid var(--adeo-line);
            background: linear-gradient(145deg, rgba(255,255,255,0.94), rgba(250,243,236,0.88));
            box-shadow: 0 28px 80px rgba(67, 41, 26, 0.10);
            backdrop-filter: blur(10px);
        }

        .hero-kicker {
            display: inline-block;
            margin-bottom: 0.8rem;
            padding: 0.35rem 0.72rem;
            border-radius: 999px;
            background: rgba(182, 81, 58, 0.11);
            color: var(--adeo-accent);
            font-size: 0.84rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .hero-title {
            margin: 0;
            color: var(--adeo-ink);
            font-family: 'Nanum Myeongjo', serif;
            font-size: 2.5rem;
            line-height: 1.18;
            font-weight: 800;
        }

        .hero-body {
            margin: 0.9rem 0 1rem 0;
            max-width: 840px;
            color: #4e3e34;
            font-size: 1.03rem;
            line-height: 1.7;
        }

        .hero-meta {
            color: #7a5c46;
            font-size: 0.92rem;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 1.2rem;
        }

        .info-card {
            padding: 1rem 1rem 1.05rem 1rem;
            border-radius: 20px;
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(123, 92, 70, 0.14);
        }

        .info-card strong {
            display: block;
            margin-bottom: 0.35rem;
            color: var(--adeo-ink);
            font-size: 1rem;
        }

        .info-card span {
            color: #5d4d43;
            font-size: 0.94rem;
            line-height: 1.6;
        }

        .section-label {
            margin: 1.4rem 0 0.65rem 0;
            color: var(--adeo-brown);
            font-size: 0.88rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .subnote {
            color: #6b584b;
            font-size: 0.93rem;
            line-height: 1.65;
            margin-bottom: 0.8rem;
        }

        div[data-testid="stFileUploader"],
        div[data-testid="stTextArea"],
        div[data-testid="stTextInput"] {
            background: rgba(255, 252, 247, 0.82);
            border: 1px solid rgba(123, 92, 70, 0.16);
            border-radius: 20px;
            padding: 0.5rem 0.7rem 0.25rem 0.7rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
        }

        div[data-testid="stFileUploader"] section {
            border: 1.5px dashed rgba(182, 81, 58, 0.32);
            border-radius: 18px;
            background: rgba(255,255,255,0.65);
        }

        div[data-testid="stRadio"] > div {
            background: rgba(255,252,247,0.72);
            border: 1px solid rgba(123, 92, 70, 0.16);
            border-radius: 18px;
            padding: 0.5rem 0.85rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 252, 248, 0.88);
            border: 1px solid rgba(123, 92, 70, 0.14);
            border-radius: 20px;
            padding: 0.7rem 1rem;
            box-shadow: 0 10px 24px rgba(67, 41, 26, 0.04);
        }

        div[data-testid="stMetricLabel"] {
            color: #7a5c46;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            color: var(--adeo-ink);
            font-size: 1.6rem;
        }

        .stButton > button,
        .stDownloadButton > button {
            width: 100%;
            border: 0;
            border-radius: 18px;
            min-height: 3.2rem;
            font-weight: 700;
            font-size: 1rem;
            color: white;
            background: linear-gradient(135deg, #b6513a 0%, #d2654c 100%);
            box-shadow: 0 16px 28px rgba(182, 81, 58, 0.24);
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #a54934 0%, #c65e47 100%);
        }

        div[data-testid="stAlert"] {
            border-radius: 18px;
        }

        details {
            background: rgba(255, 252, 248, 0.8);
            border-radius: 18px;
            border: 1px solid rgba(123, 92, 70, 0.12);
            padding: 0.3rem 0.4rem;
        }

        @media (max-width: 900px) {
            .hero-title {
                font-size: 2rem;
            }

            .info-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">ADEO FORM AUTOMATION</div>
            <h1 class="hero-title">{APP_TITLE}</h1>
            <p class="hero-body">
                구글 폼 평가 결과를 연주자별 PDF로 정리하고, 한 번에 ZIP으로 내려받을 수 있게 만든 자동 취합 도구입니다.
                정리하면 <strong>CSV는 필수</strong>이고, 연주자 명단은 <strong>HTML 자동 추출</strong> 또는
                <strong>직접 붙여넣기</strong> 중 편한 방식으로 준비하시면 됩니다.
            </p>
            <div class="hero-meta">{BRANDING_TEXT}</div>
            <div class="info-grid">
                <div class="info-card">
                    <strong>1. 명단 준비</strong>
                    <span>HTML에서 자동으로 읽거나, 공식 연주자 명단을 직접 붙여넣을 수 있습니다.</span>
                </div>
                <div class="info-card">
                    <strong>2. 응답 CSV 업로드</strong>
                    <span>평균 점수와 익명 피드백 원본은 CSV에 있으므로 이 파일은 반드시 필요합니다.</span>
                </div>
                <div class="info-card">
                    <strong>3. PDF ZIP 다운로드</strong>
                    <span>학생 전달용으로 바로 쓸 수 있는 PDF 묶음을 한 번에 받아보실 수 있습니다.</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_guide() -> None:
    st.markdown('<div class="section-label">How To Use</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="subnote">
            처음 쓰는 경우에는 아래 순서만 기억하시면 됩니다.
            <strong>명단 준비 → CSV 업로드 → 파일명 날짜 확인 → PDF 생성</strong> 순서입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("왜 CSV가 필수인가요?"):
        st.markdown(
            """
            - HTML은 보통 연주자 순서, 폼 구조, 섹션 제목 같은 뼈대 정보를 읽는 데 유리합니다.
            - 실제 점수 행과 구체적 피드백 원본은 CSV에 가장 안정적으로 들어 있습니다.
            - 그래서 현재 구조에서는 `CSV는 필수`, `HTML은 선택`으로 두는 것이 가장 안전합니다.
            """
        )

    with st.expander("파일은 어떤 이름으로 저장되나요?"):
        st.markdown(
            f"""
            - 기본 형식은 `학내날짜_대상자_{PDF_SUFFIX}.pdf` 입니다.
            - 예시: `2026-04-08_최광_{PDF_SUFFIX}.pdf`
            - 학내 날짜는 자동 감지되며, 필요하면 화면에서 직접 수정할 수 있습니다.
            """
        )

    with st.expander("오타 후보 추천은 어떻게 동작하나요?"):
        st.markdown(
            """
            - 선택 입력인 `검증용 기준 명단`을 넣으면 현재 명단과 비교해 차이를 찾아줍니다.
            - 완전 일치하지 않는 이름 중에서 `한 글자 차이` 또는 `유사도 높은 후보`를 자동으로 제안합니다.
            - 이 기능은 자동 수정이 아니라 관리자 확인용 제안입니다.
            """
        )


def get_performer_names(
    source_mode: str, html_file, roster_text: str
) -> tuple[list[str], str]:
    if source_mode == "HTML에서 자동 추출":
        if html_file is None:
            return [], "HTML 파일을 업로드하면 연주자 명단을 자동으로 읽어옵니다."
        performer_names = extract_performer_names(html_file.getvalue())
        if performer_names:
            return performer_names, f"HTML에서 연주자 {len(performer_names)}명을 인식했습니다."
        return [], "HTML에서 연주자 명단을 찾지 못했습니다. 직접 입력 모드를 사용해도 됩니다."

    performer_names = extract_performer_names_from_text(roster_text)
    if performer_names:
        return performer_names, f"직접 입력한 명단에서 연주자 {len(performer_names)}명을 인식했습니다."
    return [], "연주자 명단을 줄바꿈 기준으로 한 줄에 한 명씩 입력해 주세요."


def render_preflight_metrics(
    performer_names: list[str], dataframe: pd.DataFrame | None, event_date_label: str
) -> int:
    performer_group_count = 0
    response_count = 0
    if dataframe is not None:
        response_count = len(dataframe)
        performer_group_count = max(
            0, (len(dataframe.columns) - EVALUATOR_INFO_COLUMN_COUNT) // PERFORMER_GROUP_SIZE
        )

    status_col1, status_col2, status_col3, status_col4 = st.columns(4)
    status_col1.metric("연주자 명단", len(performer_names))
    status_col2.metric("CSV 응답 행", response_count)
    status_col3.metric("연주자 세트", performer_group_count)
    status_col4.metric("파일명 날짜", normalize_date_label(event_date_label))
    return performer_group_count


def render_validation_summary(summary_df: pd.DataFrame | None) -> None:
    st.markdown('<div class="section-label">Validation Summary</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subnote">생성 전에 연주자별 응답 상태를 한 번에 확인할 수 있는 요약 패널입니다.</div>',
        unsafe_allow_html=True,
    )
    if summary_df is None or summary_df.empty:
        st.info("연주자 명단과 CSV가 모두 준비되면 검증 표가 표시됩니다.")
        return

    st.dataframe(summary_df, use_container_width=True, hide_index=True)
