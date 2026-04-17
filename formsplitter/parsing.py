from __future__ import annotations

import io
import re
from collections import Counter
from datetime import datetime
from typing import Iterable

import pandas as pd
from bs4 import BeautifulSoup

try:
    from .constants import (
        EVALUATOR_INFO_COLUMN_COUNT,
        PERFORMER_GROUP_SIZE,
        QUESTION_TITLE_CLASS,
    )
except ImportError:
    from constants import (
        EVALUATOR_INFO_COLUMN_COUNT,
        PERFORMER_GROUP_SIZE,
        QUESTION_TITLE_CLASS,
    )


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "이름없음"


def normalize_date_label(raw_text: str) -> str:
    text = clean_text(raw_text)
    if not text:
        return datetime.now().strftime("%Y-%m-%d")

    full_match = re.search(
        r"(?P<year>\d{2,4})\D+(?P<month>\d{1,2})\D+(?P<day>\d{1,2})",
        text,
    )
    if full_match:
        year = int(full_match.group("year"))
        month = int(full_match.group("month"))
        day = int(full_match.group("day"))
        if year < 100:
            year += 2000
        return f"{year:04d}-{month:02d}-{day:02d}"

    month_day_match = re.search(r"(?P<month>\d{1,2})\D+(?P<day>\d{1,2})", text)
    if month_day_match:
        month = int(month_day_match.group("month"))
        day = int(month_day_match.group("day"))
        year = datetime.now().year
        return f"{year:04d}-{month:02d}-{day:02d}"

    safe_text = sanitize_filename(text)
    safe_text = re.sub(r"[\s.]+", "-", safe_text)
    return safe_text or datetime.now().strftime("%Y-%m-%d")


def load_csv_with_fallback(csv_bytes: bytes) -> pd.DataFrame:
    encodings = ("utf-8-sig", "cp949", "euc-kr", "utf-8")
    last_error = None

    for encoding in encodings:
        for engine in (None, "python"):
            read_kwargs = {"encoding": encoding}
            if engine is not None:
                read_kwargs["engine"] = engine

            try:
                return pd.read_csv(io.BytesIO(csv_bytes), **read_kwargs)
            except UnicodeDecodeError as exc:
                last_error = exc
                break
            except Exception as exc:
                last_error = exc

    raise ValueError(
        "CSV 파일을 읽지 못했습니다. UTF-8 또는 CP949 형식인지 확인해 주세요."
    ) from last_error


def parse_performer_name(raw_text: str) -> str:
    text = clean_text(raw_text)
    text = re.sub(r"^\d+\s*[.)]?\s*", "", text)
    text = text.split("/", 1)[0].strip()
    return clean_text(text)


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def extract_performer_names_from_sections(soup: BeautifulSoup) -> list[str]:
    names: list[str] = []
    for element in soup.find_all(attrs={"aria-label": re.compile(r"^섹션 제목")}):
        performer_name = parse_performer_name(element.get_text(" ", strip=True))
        if performer_name:
            names.append(performer_name)
    return dedupe_keep_order(names)


def extract_performer_names_from_description(soup: BeautifulSoup) -> list[str]:
    names: list[str] = []
    for element in soup.find_all(attrs={"aria-label": re.compile(r"^설명")}):
        description_text = element.get_text("\n", strip=True).replace("\xa0", " ")
        lines = [line.strip() for line in description_text.splitlines() if line.strip()]
        numbered_lines = [line for line in lines if re.match(r"^\d+\s*[.)]?\s*\S+", line)]
        if len(numbered_lines) < 2:
            continue

        for line in numbered_lines:
            performer_name = parse_performer_name(line)
            if performer_name:
                names.append(performer_name)

    return dedupe_keep_order(names)


def extract_performer_names_from_text(raw_text: str) -> list[str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    performer_names = [parse_performer_name(line) for line in lines]
    return dedupe_keep_order([name for name in performer_names if name])


def extract_performer_names(html_bytes: bytes) -> list[str]:
    soup = BeautifulSoup(html_bytes, "html.parser")
    legacy_titles = [
        element.get_text(" ", strip=True)
        for element in soup.find_all(class_=QUESTION_TITLE_CLASS)
    ]
    performer_names = [clean_text(name) for name in legacy_titles[1:] if clean_text(name)]
    if performer_names:
        return performer_names

    performer_names = extract_performer_names_from_sections(soup)
    if performer_names:
        return performer_names

    return extract_performer_names_from_description(soup)


def extract_event_date_from_dataframe(dataframe: pd.DataFrame) -> str:
    if dataframe.empty:
        return ""

    first_column = dataframe.iloc[:, 0].dropna().astype(str).tolist()
    extracted_dates: list[str] = []
    for value in first_column:
        match = re.search(
            r"(?P<year>\d{2,4})\D+(?P<month>\d{1,2})\D+(?P<day>\d{1,2})",
            value,
        )
        if not match:
            continue

        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
        if year < 100:
            year += 2000
        extracted_dates.append(f"{year:04d}-{month:02d}-{day:02d}")

    if not extracted_dates:
        return ""

    return Counter(extracted_dates).most_common(1)[0][0]


def extract_event_date_from_html(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    title_text = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    text_candidates = [title_text]

    if soup.body:
        body_text = clean_text(soup.body.get_text(" ", strip=True))
        text_candidates.append(body_text[:5000])

    for text in text_candidates:
        if not text:
            continue

        semester_match = re.search(
            r"(?P<year>\d{2,4})\s*-\s*\d+\s*/\s*(?P<month>\d{1,2})\s*/\s*(?P<day>\d{1,2})",
            text,
        )
        if semester_match:
            year = int(semester_match.group("year"))
            if year < 100:
                year += 2000
            month = int(semester_match.group("month"))
            day = int(semester_match.group("day"))
            return f"{year:04d}-{month:02d}-{day:02d}"

        full_match = re.search(
            r"(?P<year>\d{2,4})\D+(?P<month>\d{1,2})\D+(?P<day>\d{1,2})",
            text,
        )
        if full_match:
            year = int(full_match.group("year"))
            if year < 100:
                year += 2000
            month = int(full_match.group("month"))
            day = int(full_match.group("day"))
            return f"{year:04d}-{month:02d}-{day:02d}"

        month_day_match = re.search(r"(?P<month>\d{1,2})\s*/\s*(?P<day>\d{1,2})", text)
        if month_day_match:
            year = datetime.now().year
            month = int(month_day_match.group("month"))
            day = int(month_day_match.group("day"))
            return f"{year:04d}-{month:02d}-{day:02d}"

    return ""


def normalize_performer_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.replace(r"^\s*$", pd.NA, regex=True)


def coerce_numeric_series(series: pd.Series) -> pd.Series:
    stripped = series.astype("string").str.replace(r"[^\d.\-]", "", regex=True)
    stripped = stripped.replace("", pd.NA)
    return pd.to_numeric(stripped, errors="coerce")


def get_performer_group_count(dataframe: pd.DataFrame) -> int:
    return max(
        0, (len(dataframe.columns) - EVALUATOR_INFO_COLUMN_COUNT) // PERFORMER_GROUP_SIZE
    )


def iter_performer_groups(
    dataframe: pd.DataFrame, performer_names: Iterable[str]
) -> Iterable[tuple[int, str, pd.DataFrame]]:
    base_index = EVALUATOR_INFO_COLUMN_COUNT
    for index, performer_name in enumerate(performer_names, start=1):
        start = base_index + (index - 1) * PERFORMER_GROUP_SIZE
        end = start + PERFORMER_GROUP_SIZE
        if end > len(dataframe.columns):
            break
        yield index, performer_name, dataframe.iloc[:, start:end].copy()
