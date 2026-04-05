#!/usr/bin/env python3
"""
Collect and classify publicly accessible application-related posts.

This script is designed for lawful collection of content that you already have
permission to access, such as:
1. A list of public page URLs you gathered manually or via compliant search.
2. Local HTML files exported from pages you can access.

It does not include any logic for bypassing authentication, rate limits,
captchas, signatures, or other access controls.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

NEW_MEDIA_KEYWORDS = [
    "新传",
    "新闻传播",
    "新闻学",
    "传播学",
    "传媒",
    "媒体研究",
    "数字传播",
    "国际传播",
    "journalism",
    "communication",
    "media studies",
    "strategic communication",
]

HK_PHD_KEYWORDS = [
    "香港博士",
    "港博",
    "香港phd",
    "香港 phd",
    "hkphd",
    "hong kong phd",
    "港三",
    "港中文",
    "港大",
    "港科大",
    "港城大",
    "浸会",
    "岭南",
    "理大",
    "edu hk",
]

CN_PHD_KEYWORDS = [
    "内地博士",
    "国内博士",
    "大陆博士",
    "考博",
    "申请考核",
    "博士申请",
    "博士招生",
    "博士录取",
    "博士上岸",
    "直博",
    "硕博连读",
    "复旦博士",
    "人大博士",
    "清华博士",
    "北大博士",
    "中传博士",
]

DIY_KEYWORDS = [
    "diy",
    "全diy",
    "纯diy",
    "自己申请",
    "自己准备",
    "自己联系",
    "自己套磁",
    "无中介",
    "没找中介",
    "独立申请",
]

AGENCY_KEYWORDS = [
    "中介",
    "机构",
    "留学机构",
    "申请机构",
    "文书机构",
    "全程服务",
    "保录",
    "付费申请",
    "顾问老师",
    "申请老师",
    "背景提升机构",
]

SEMI_DIY_KEYWORDS = [
    "半diy",
    "半 diy",
    "半自助",
    "部分diy",
    "部分 diy",
    "找人改文书",
    "文书润色",
    "只买文书",
    "只做文书",
    "找老师修改",
    "自己申+机构",
    "diy+中介",
]

STAGE_KEYWORDS = {
    "background": ["背景", "绩点", "gpa", "科研", "论文", "实习", "竞赛", "项目经历"],
    "school_selection": ["选校", "定位", "择校", "院校定位", "项目匹配"],
    "supervisor_contact": ["套磁", "联系导师", "导师回复", "面试邀约", "陶瓷"],
    "materials": ["文书", "ps", "cv", "简历", "rp", "research proposal", "writing sample"],
    "interview": ["面试", "面邀", "skype", "zoom", "面经"],
    "result": ["offer", "录取", "上岸", "拒信", "waiting list", "wl"],
}

POST_HINTS = [
    "经验贴",
    "总结",
    "申请季",
    "上岸",
    "时间线",
    "选校",
    "套磁",
    "文书",
    "申请",
    "博士",
    "申博",
]

SCHOOL_TAGS = {
    "hku": ["港大", "香港大学", "the university of hong kong"],
    "cuhk": ["港中文", "香港中文大学", "cuhk"],
    "hkust": ["港科大", "香港科技大学", "hkust"],
    "cityu": ["港城大", "香港城市大学", "cityu"],
    "hkbu": ["浸会", "香港浸会大学", "hkbu"],
    "polyu": ["理大", "香港理工大学", "polyu"],
    "lingnan": ["岭南", "岭南大学", "lingnan university"],
    "eduhk": ["教大", "香港教育大学", "edu hk", "eduhk"],
    "cuc": ["中传", "中国传媒大学", "communication university of china"],
    "fudan": ["复旦", "复旦大学", "fudan"],
    "ruc": ["人大", "中国人民大学", "renmin university"],
    "pku": ["北大", "北京大学", "peking university"],
    "thu": ["清华", "清华大学", "tsinghua"],
    "ecnu": ["华东师大", "华东师范大学", "ecnu"],
    "jnu": ["暨南", "暨南大学", "jnu"],
}


@dataclass
class Classification:
    is_relevant: bool
    relevance_score: int
    primary_track: str
    region: str
    service_mode: str
    service_detail: str
    content_type: str
    stage_tags: List[str] = field(default_factory=list)
    school_tags: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class PostRecord:
    source: str
    url: str
    title: str
    content: str
    publish_time: str
    classification: Classification

    def to_row(self) -> dict:
        row = {
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "publish_time": self.publish_time,
            "is_relevant": self.classification.is_relevant,
            "relevance_score": self.classification.relevance_score,
            "primary_track": self.classification.primary_track,
            "region": self.classification.region,
            "service_mode": self.classification.service_mode,
            "service_detail": self.classification.service_detail,
            "content_type": self.classification.content_type,
            "stage_tags": "|".join(self.classification.stage_tags),
            "school_tags": "|".join(self.classification.school_tags),
            "matched_keywords": "|".join(self.classification.matched_keywords),
            "reason": self.classification.reason,
        }
        return row


def load_text_lines(path: Path) -> List[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fetch_html(url: str, timeout: int, sleep_seconds: float) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return response.text


def parse_html(source: str, url: str, html: str) -> PostRecord:
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)
    content = extract_content(soup)
    publish_time = extract_publish_time(soup)
    classification = classify_post(title=title, content=content)
    return PostRecord(
        source=source,
        url=url,
        title=title,
        content=content,
        publish_time=publish_time,
        classification=classification,
    )


def extract_title(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "title"}),
        soup.find("title"),
        soup.find(["h1", "h2"]),
    ]
    for node in candidates:
        if not node:
            continue
        if node.name == "meta":
            text = node.get("content", "")
        else:
            text = node.get_text(" ", strip=True)
        text = normalize_whitespace(text)
        if text:
            return text
    return ""


def extract_content(soup: BeautifulSoup) -> str:
    meta_candidates = [
        soup.find("meta", attrs={"name": "description"}),
        soup.find("meta", attrs={"property": "og:description"}),
    ]
    texts: List[str] = []
    for node in meta_candidates:
        if node and node.get("content"):
            texts.append(node["content"])

    selectors = [
        "article",
        "[class*=content]",
        "[class*=desc]",
        "[class*=note]",
        "[class*=article]",
        "[class*=post]",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            text = normalize_whitespace(node.get_text(" ", strip=True))
            if text and len(text) > 40:
                texts.append(text)

    combined = " ".join(texts)
    combined = normalize_whitespace(combined)
    return combined[:5000]


def extract_publish_time(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "article:published_time"}),
        soup.find("meta", attrs={"name": "publish_time"}),
        soup.find("time"),
    ]
    for node in candidates:
        if not node:
            continue
        if node.name == "meta":
            value = node.get("content", "")
        else:
            value = node.get("datetime", "") or node.get_text(" ", strip=True)
        value = normalize_whitespace(value)
        if value:
            return value
    return ""


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def classify_post(title: str, content: str) -> Classification:
    text = normalize_whitespace(f"{title} {content}")
    text_lower = text.lower()

    matched_keywords: List[str] = []
    score = 0

    def collect_score(words: Sequence[str], weight: int) -> int:
        local_hits = 0
        for word in words:
            if word.lower() in text_lower:
                matched_keywords.append(word)
                local_hits += 1
        return local_hits * weight

    score += collect_score(NEW_MEDIA_KEYWORDS, 3)
    score += collect_score(HK_PHD_KEYWORDS, 3)
    score += collect_score(CN_PHD_KEYWORDS, 3)
    score += collect_score(POST_HINTS, 1)

    region = detect_region(text_lower)
    service_mode, service_detail = detect_service_mode(text_lower)
    content_type = detect_content_type(text_lower)
    stage_tags = detect_stage_tags(text_lower)
    school_tags = detect_school_tags(text_lower)
    primary_track = detect_primary_track(text_lower, region)

    if primary_track != "other":
        score += 3
    if region != "unknown":
        score += 2
    if service_mode != "unknown":
        score += 2

    is_relevant = (
        primary_track in {"hk_phd_new_media", "cn_phd_new_media"}
        or (
            any(word.lower() in text_lower for word in NEW_MEDIA_KEYWORDS)
            and region in {"hong_kong", "mainland"}
        )
    )

    reason = build_reason(
        title=title,
        primary_track=primary_track,
        region=region,
        service_mode=service_mode,
        service_detail=service_detail,
        content_type=content_type,
        stage_tags=stage_tags,
        school_tags=school_tags,
    )

    return Classification(
        is_relevant=is_relevant,
        relevance_score=score,
        primary_track=primary_track,
        region=region,
        service_mode=service_mode,
        service_detail=service_detail,
        content_type=content_type,
        stage_tags=stage_tags,
        school_tags=school_tags,
        matched_keywords=dedupe_preserve_order(matched_keywords),
        reason=reason,
    )


def detect_region(text_lower: str) -> str:
    hk_hits = sum(1 for word in HK_PHD_KEYWORDS if word.lower() in text_lower)
    cn_hits = sum(1 for word in CN_PHD_KEYWORDS if word.lower() in text_lower)
    if hk_hits and cn_hits:
        return "mixed"
    if hk_hits:
        return "hong_kong"
    if cn_hits:
        return "mainland"
    return "unknown"


def detect_service_mode(text_lower: str) -> tuple[str, str]:
    semi_hits = sum(1 for word in SEMI_DIY_KEYWORDS if word.lower() in text_lower)
    diy_hits = sum(1 for word in DIY_KEYWORDS if word.lower() in text_lower)
    negative_agency_phrases = [
        "没找中介",
        "没有找中介",
        "无中介",
        "不用中介",
        "拒绝中介",
        "不找机构",
        "没有找机构",
    ]
    has_negative_agency = any(phrase in text_lower for phrase in negative_agency_phrases)
    agency_hits = 0
    if not has_negative_agency:
        agency_hits = sum(1 for word in AGENCY_KEYWORDS if word.lower() in text_lower)

    essay_only = any(word in text_lower for word in ["文书润色", "改文书", "只做文书", "只买文书", "cv修改"])
    consulting_only = any(word in text_lower for word in ["咨询", "定位", "选校建议", "申请规划", "导师匹配"])
    full_service = any(word in text_lower for word in ["全程服务", "一条龙", "全包", "保姆级", "代申请"])

    if semi_hits:
        if essay_only:
            return "semi_diy", "essay_only"
        if consulting_only:
            return "semi_diy", "consulting_only"
        return "semi_diy", "mixed_support"
    if diy_hits and agency_hits:
        if essay_only:
            return "semi_diy", "essay_only"
        if consulting_only:
            return "semi_diy", "consulting_only"
        return "semi_diy", "mixed_support"
    if diy_hits:
        return "diy", "full_self_managed"
    if agency_hits:
        if full_service:
            return "agency", "full_service"
        if essay_only:
            return "agency", "essay_only"
        if consulting_only:
            return "agency", "consulting_only"
        return "agency", "unspecified_paid_service"
    return "unknown", "unknown"


def detect_content_type(text_lower: str) -> str:
    if any(word in text_lower for word in ["经验贴", "上岸", "申请总结", "时间线"]):
        return "experience"
    if any(word in text_lower for word in ["求助", "求定位", "求建议", "有无"]):
        return "help_request"
    promotion_markers = [
        "广告",
        "保姆级服务",
        "全程服务",
        "保录",
        "代申请",
        "付费申请",
        "加微信",
        "私信咨询",
        "咨询请",
    ]
    if any(word in text_lower for word in promotion_markers):
        return "promotion"
    return "general"


def detect_stage_tags(text_lower: str) -> List[str]:
    tags = []
    for tag, words in STAGE_KEYWORDS.items():
        if any(word.lower() in text_lower for word in words):
            tags.append(tag)
    return tags


def detect_school_tags(text_lower: str) -> List[str]:
    tags = []
    for tag, words in SCHOOL_TAGS.items():
        if any(word.lower() in text_lower for word in words):
            tags.append(tag)
    return tags


def detect_primary_track(text_lower: str, region: str) -> str:
    has_new_media = any(word.lower() in text_lower for word in NEW_MEDIA_KEYWORDS)
    if not has_new_media:
        return "other"
    if region == "hong_kong":
        return "hk_phd_new_media"
    if region == "mainland":
        return "cn_phd_new_media"
    if region == "mixed":
        return "mixed_new_media_phd"
    return "other"


def build_reason(
    title: str,
    primary_track: str,
    region: str,
    service_mode: str,
    service_detail: str,
    content_type: str,
    stage_tags: Sequence[str],
    school_tags: Sequence[str],
) -> str:
    parts = []
    if title:
        parts.append(f"title={title[:40]}")
    parts.append(f"track={primary_track}")
    parts.append(f"region={region}")
    parts.append(f"service={service_mode}")
    parts.append(f"service_detail={service_detail}")
    parts.append(f"type={content_type}")
    if stage_tags:
        parts.append(f"stages={','.join(stage_tags)}")
    if school_tags:
        parts.append(f"schools={','.join(school_tags)}")
    return "; ".join(parts)


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def read_urls_from_args(urls: Optional[Sequence[str]], url_file: Optional[Path]) -> List[str]:
    collected = list(urls or [])
    if url_file:
        collected.extend(load_text_lines(url_file))
    return dedupe_preserve_order(collected)


def read_html_paths(input_dir: Optional[Path], html_files: Optional[Sequence[Path]]) -> List[str]:
    paths = list(html_files or [])
    if input_dir:
        paths.extend(sorted(input_dir.glob("*.html")))
        paths.extend(sorted(input_dir.glob("*.htm")))
    return dedupe_preserve_order(str(path) for path in paths)


def collect_from_urls(urls: Sequence[str], timeout: int, sleep_seconds: float) -> List[PostRecord]:
    records = []
    for url in urls:
        try:
            html = fetch_html(url=url, timeout=timeout, sleep_seconds=sleep_seconds)
            records.append(parse_html(source="url", url=url, html=html))
        except Exception as exc:
            records.append(
                PostRecord(
                    source="url",
                    url=url,
                    title="",
                    content="",
                    publish_time="",
                    classification=Classification(
                        is_relevant=False,
                        relevance_score=0,
                        primary_track="fetch_error",
                        region="unknown",
                        service_mode="unknown",
                        service_detail="unknown",
                        content_type="error",
                        stage_tags=[],
                        school_tags=[],
                        matched_keywords=[],
                        reason=str(exc),
                    ),
                )
            )
    return records


def collect_from_html_files(paths: Sequence[str]) -> List[PostRecord]:
    records = []
    for raw_path in paths:
        path = Path(raw_path)
        html = path.read_text(encoding="utf-8", errors="ignore")
        records.append(parse_html(source="html_file", url=str(path), html=html))
    return records


def write_csv(records: Sequence[PostRecord], output_path: Path) -> None:
    fieldnames = [
        "source",
        "url",
        "title",
        "content",
        "publish_time",
        "is_relevant",
        "relevance_score",
        "primary_track",
        "region",
        "service_mode",
        "service_detail",
        "content_type",
        "stage_tags",
        "school_tags",
        "matched_keywords",
        "reason",
    ]
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())


def write_summary(records: Sequence[PostRecord], summary_path: Path) -> None:
    relevant = [item for item in records if item.classification.is_relevant]
    stats = {
        "total_records": len(records),
        "relevant_records": len(relevant),
        "primary_track": count_by(records, lambda x: x.classification.primary_track),
        "region": count_by(records, lambda x: x.classification.region),
        "service_mode": count_by(records, lambda x: x.classification.service_mode),
        "service_detail": count_by(records, lambda x: x.classification.service_detail),
        "content_type": count_by(records, lambda x: x.classification.content_type),
    }
    summary_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def count_by(records: Sequence[PostRecord], key_func: Callable[[PostRecord], str]) -> dict:
    result = {}
    for record in records:
        key = key_func(record)
        result[key] = result.get(key, 0) + 1
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect and classify public PhD application posts for journalism/communication."
    )
    parser.add_argument("--url", action="append", help="A public page URL. Can be repeated.")
    parser.add_argument("--url-file", type=Path, help="Text file with one public URL per line.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing local HTML files.")
    parser.add_argument("--html-file", type=Path, action="append", help="Local HTML file. Can be repeated.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("xhs_shenbo_classified.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("xhs_shenbo_summary.json"),
        help="Output JSON summary path.",
    )
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.5,
        help="Delay between URL fetches to avoid hammering the server.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    urls = read_urls_from_args(args.url, args.url_file)
    html_paths = read_html_paths(args.input_dir, args.html_file)

    if not urls and not html_paths:
        parser.error("Provide at least one input via --url, --url-file, --input-dir, or --html-file.")

    records: List[PostRecord] = []
    if urls:
        records.extend(collect_from_urls(urls=urls, timeout=args.timeout, sleep_seconds=args.sleep_seconds))
    if html_paths:
        records.extend(collect_from_html_files(paths=html_paths))

    records.sort(
        key=lambda item: (
            not item.classification.is_relevant,
            -item.classification.relevance_score,
            item.url,
        )
    )

    write_csv(records, args.output)
    write_summary(records, args.summary_output)

    print(f"Wrote {len(records)} records to {args.output}")
    print(f"Wrote summary to {args.summary_output}")


if __name__ == "__main__":
    main()
