from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import pandas as pd

try:
    from .constants import EVALUATOR_INFO_COLUMN_COUNT, PERFORMER_GROUP_SIZE
    from .parsing import (
        clean_text,
        coerce_numeric_series,
        dedupe_keep_order,
        get_performer_group_count,
        iter_performer_groups,
        normalize_performer_frame,
        parse_performer_name,
    )
except ImportError:
    from constants import EVALUATOR_INFO_COLUMN_COUNT, PERFORMER_GROUP_SIZE
    from parsing import (
        clean_text,
        coerce_numeric_series,
        dedupe_keep_order,
        get_performer_group_count,
        iter_performer_groups,
        normalize_performer_frame,
        parse_performer_name,
    )


def build_validation_summary(dataframe: pd.DataFrame, performer_names: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    performer_group_count = get_performer_group_count(dataframe)
    matched_count = min(len(performer_names), performer_group_count)

    for performer_index, performer_name, group_frame in iter_performer_groups(
        dataframe, performer_names
    ):
        normalized = normalize_performer_frame(group_frame)
        filtered = normalized.dropna(how="all")
        score_count = sum(
            int(coerce_numeric_series(filtered.iloc[:, column_index]).notna().sum())
            for column_index in range(5)
        )
        feedback_count = int(
            filtered.iloc[:, 5]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .shape[0]
        )

        if filtered.empty:
            status = "응답 없음"
            note = "이 연주자 세트는 6개 항목이 모두 비어 있습니다."
        elif feedback_count == 0:
            status = "검토"
            note = "점수 데이터는 있지만 구체적 피드백은 없습니다."
        else:
            status = "정상"
            note = "PDF 생성 준비가 완료되었습니다."

        rows.append(
            {
                "순번": performer_index,
                "연주자": performer_name,
                "CSV 세트": performer_index,
                "응답 수": int(filtered.shape[0]),
                "점수 데이터 수": score_count,
                "피드백 수": feedback_count,
                "상태": status,
                "메모": note,
            }
        )

    for performer_index in range(matched_count + 1, len(performer_names) + 1):
        rows.append(
            {
                "순번": performer_index,
                "연주자": performer_names[performer_index - 1],
                "CSV 세트": "-",
                "응답 수": 0,
                "점수 데이터 수": 0,
                "피드백 수": 0,
                "상태": "CSV 부족",
                "메모": "명단은 있지만 대응되는 CSV 열 세트가 없습니다.",
            }
        )

    for performer_index in range(len(performer_names) + 1, performer_group_count + 1):
        start = EVALUATOR_INFO_COLUMN_COUNT + (performer_index - 1) * PERFORMER_GROUP_SIZE
        end = start + PERFORMER_GROUP_SIZE
        group_frame = dataframe.iloc[:, start:end].copy()
        normalized = normalize_performer_frame(group_frame)
        filtered = normalized.dropna(how="all")
        score_count = sum(
            int(coerce_numeric_series(filtered.iloc[:, column_index]).notna().sum())
            for column_index in range(5)
        )
        feedback_count = int(
            filtered.iloc[:, 5]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .shape[0]
        )
        rows.append(
            {
                "순번": performer_index,
                "연주자": "(명단 없음)",
                "CSV 세트": performer_index,
                "응답 수": int(filtered.shape[0]),
                "점수 데이터 수": score_count,
                "피드백 수": feedback_count,
                "상태": "명단 필요",
                "메모": "CSV 세트는 있으나 현재 명단에서 대응 이름을 찾지 못했습니다.",
            }
        )

    return pd.DataFrame(rows)


def normalize_name_key(name: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]", "", clean_text(name))
    return normalized.casefold()


def _char_distance(a: str, b: str) -> int | None:
    if len(a) != len(b):
        return None
    return sum(left != right for left, right in zip(a, b))


def _pick_best_candidate(current_name: str, reference_names: list[str]) -> tuple[str, float, str] | None:
    current_key = normalize_name_key(current_name)
    candidates: list[tuple[float, str, str]] = []

    for reference_name in reference_names:
        reference_key = normalize_name_key(reference_name)
        distance = _char_distance(current_key, reference_key)
        if distance == 1 and current_key and reference_key:
            candidates.append((0.96, reference_name, "한 글자 차이"))
            continue

        score = SequenceMatcher(None, current_key, reference_key).ratio()
        if score >= 0.62:
            candidates.append((score, reference_name, "유사도 기반 후보"))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_name, reason = candidates[0]
    return best_name, best_score, reason


@dataclass(slots=True)
class NameComparisonResult:
    reference_names: list[str]
    exact_match_count: int
    current_only: list[str]
    reference_only: list[str]
    suggestions_df: pd.DataFrame


def compare_names_against_reference(
    performer_names: list[str], reference_text: str
) -> NameComparisonResult | None:
    reference_names = dedupe_keep_order(
        [parse_performer_name(line) for line in reference_text.splitlines() if line.strip()]
    )
    reference_names = [name for name in reference_names if name]
    if not reference_names:
        return None

    performer_names = dedupe_keep_order(performer_names)
    performer_map = {normalize_name_key(name): name for name in performer_names}
    reference_map = {normalize_name_key(name): name for name in reference_names}

    exact_keys = set(performer_map) & set(reference_map)
    current_only = [
        name for name in performer_names if normalize_name_key(name) not in exact_keys
    ]
    reference_only = [
        name for name in reference_names if normalize_name_key(name) not in exact_keys
    ]

    suggestion_rows: list[dict[str, object]] = []
    for current_name in current_only:
        best_candidate = _pick_best_candidate(current_name, reference_only)
        if best_candidate is None:
            continue
        suggested_name, similarity, reason = best_candidate
        suggestion_rows.append(
            {
                "현재 명단 이름": current_name,
                "추천 기준 이름": suggested_name,
                "유사도": round(similarity, 2),
                "근거": reason,
            }
        )

    suggestions_df = pd.DataFrame(suggestion_rows)
    if not suggestions_df.empty:
        suggestions_df = suggestions_df.sort_values(
            by=["유사도", "현재 명단 이름"], ascending=[False, True]
        ).reset_index(drop=True)

    return NameComparisonResult(
        reference_names=reference_names,
        exact_match_count=len(exact_keys),
        current_only=current_only,
        reference_only=reference_only,
        suggestions_df=suggestions_df,
    )
