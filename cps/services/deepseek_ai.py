# -*- coding: utf-8 -*-
import os
import logging
import re
import requests

from .. import config, calibre_db

log = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = os.getenv(
    "DEEPSEEK_API_BASE",
    "https://api.deepseek.com/v1/chat/completions",  # 按 DeepSeek 官方文档需要可自行修改
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()


def _build_book_context(book) -> str:
    authors = ", ".join(a.name.replace("|", ",") for a in book.authors) if book.authors else "未知作者"
    tags = ", ".join(t.name for t in book.tags) if book.tags else "无标签"
    publishers = ", ".join(p.name for p in book.publishers) if book.publishers else "未知出版社"
    lang = ", ".join(getattr(l, "lang_code", "") for l in book.languages) if book.languages else "未知语言"
    comments = ""
    if getattr(book, "comments", None):
        try:
            comments = _strip_html(book.comments[0].text or "")
        except Exception:
            comments = ""

    parts = [
        f"书名: {book.title}",
        f"作者: {authors}",
        f"出版社: {publishers}",
        f"语言: {lang}",
        f"标签: {tags}",
    ]
    if comments:
        parts.append(f"简介: {comments[:2000]}")
    return "\n".join(parts)


def _call_deepseek(system_prompt: str, user_prompt: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(DEEPSEEK_API_BASE, headers=headers, json=payload, timeout=40)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        # DeepSeek 返回的不是合法 JSON，打印原始内容帮助排查
        log.error("DeepSeek 响应不是合法 JSON，status=%s, text=%s",
                  resp.status_code, resp.text[:500])
        raise ValueError("deepseek_invalid_json")
    return data["choices"][0]["message"]["content"].strip()


def get_book_summary(book_id: int) -> str:
    """生成书籍中文概述。"""
    book = calibre_db.get_filtered_book(book_id)
    if not book:
        raise ValueError("book_not_found")

    context = _build_book_context(book)
    system_prompt = "你是一个电子书内容讲解助手，请使用简体中文回答用户。"
    user_prompt = (
        "下面是一本书的元数据信息，请根据这些信息，用 3-5 段简明的中文介绍这本书的内容概要，适合普通读者：\n\n"
        f"{context}"
    )
    return _call_deepseek(system_prompt, user_prompt)


def get_related_books(book_id: int, limit: int = 5) -> str:
    """生成推荐书籍说明（文本即可，前端直接展示）。"""
    book = calibre_db.get_filtered_book(book_id)
    if not book:
        raise ValueError("book_not_found")

    context = _build_book_context(book)
    system_prompt = "你是一个电子书推荐助手，请使用简体中文回答用户。"
    user_prompt = (
        f"根据下面这本书的信息，推荐 {limit} 本主题或风格相似的书籍（不必局限于当前书库）。"
        "请使用有序列表格式回答，每一条包含：书名 + 作者（如果知道）+ 1 句推荐理由：\n\n"
        f"{context}"
    )
    return _call_deepseek(system_prompt, user_prompt)