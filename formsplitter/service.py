from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

import pandas as pd

try:
    from .constants import EVALUATOR_INFO_COLUMN_COUNT, PDF_SUFFIX, PERFORMER_GROUP_SIZE
    from .parsing import (
        coerce_numeric_series,
        get_performer_group_count,
        iter_performer_groups,
        normalize_date_label,
        normalize_performer_frame,
        sanitize_filename,
    )
    from .pdf_export import create_pdf_document
except ImportError:
    from constants import EVALUATOR_INFO_COLUMN_COUNT, PDF_SUFFIX, PERFORMER_GROUP_SIZE
    from parsing import (
        coerce_numeric_series,
        get_performer_group_count,
        iter_performer_groups,
        normalize_date_label,
        normalize_performer_frame,
        sanitize_filename,
    )
    from pdf_export import create_pdf_document


@dataclass(slots=True)
class GenerationResult:
    zip_bytes: bytes
    zip_filename: str
    created_count: int
    matched_count: int


def build_zip_filename(event_date_label: str) -> str:
    safe_date = normalize_date_label(event_date_label)
    return f"{safe_date}_학내연주_{PDF_SUFFIX}_PDF.zip"


def generate_pdf_zip(
    dataframe: pd.DataFrame, performer_names: list[str], event_date_label: str
) -> GenerationResult:
    if not performer_names:
        raise ValueError(
            "연주자 명단을 찾지 못했습니다. HTML 업로드 또는 명단 직접 입력을 확인해 주세요."
        )

    minimum_column_count = EVALUATOR_INFO_COLUMN_COUNT + PERFORMER_GROUP_SIZE
    if len(dataframe.columns) < minimum_column_count:
        raise ValueError("CSV 열 구성이 예상과 다릅니다. 응답 결과 파일을 다시 확인해 주세요.")

    safe_date = normalize_date_label(event_date_label)
    zip_buffer = io.BytesIO()
    created_count = 0
    matched_count = min(len(performer_names), get_performer_group_count(dataframe))

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for _, performer_name, group_frame in iter_performer_groups(dataframe, performer_names):
            normalized = normalize_performer_frame(group_frame)
            filtered = normalized.dropna(how="all")

            score_values = [
                coerce_numeric_series(filtered.iloc[:, column_index]).mean()
                for column_index in range(5)
            ]
            averages = [
                round(value, 2) if pd.notna(value) else None for value in score_values
            ]
            feedbacks = [
                feedback.strip()
                for feedback in filtered.iloc[:, 5].dropna().astype(str).tolist()
                if feedback.strip()
            ]

            pdf_bytes = create_pdf_document(
                performer_name=performer_name,
                averages=averages,
                feedbacks=feedbacks,
                event_date_label=safe_date,
            )
            safe_name = sanitize_filename(performer_name)
            archive.writestr(f"{safe_date}_{safe_name}_{PDF_SUFFIX}.pdf", pdf_bytes)
            created_count += 1

    zip_buffer.seek(0)
    return GenerationResult(
        zip_bytes=zip_buffer.getvalue(),
        zip_filename=build_zip_filename(safe_date),
        created_count=created_count,
        matched_count=matched_count,
    )
