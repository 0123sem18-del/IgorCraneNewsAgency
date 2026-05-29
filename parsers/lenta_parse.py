"""Разбор HTML главной https://lenta.ru/ в структуру для шаблона."""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://lenta.ru"
_TIME_TAIL = re.compile(r"\s+(\d{1,2}:\d{2})\s*$")
_RUBRIC_IN_HREF = re.compile(r"/rubrics/([^/]+)/?")

# Соответствие slug рубрик Lenta.ru пунктам меню на сайте
MENU_TOPIC_RUBRIC_SLUGS: dict[str, frozenset[str]] = {
    "Политика": frozenset({"russia", "politics", "ussr", "forces"}),
    "Общество": frozenset({"life", "culture", "media", "style", "society"}),
    "Экономика": frozenset({"economics", "realty", "money"}),
    "В мире": frozenset({"world"}),
    "Происшествия": frozenset({"incident", "conflicts", "crime", "forces"}),
    "Спорт": frozenset({"sport"}),
    "Наука": frozenset({"science"}),
    "Туризм": frozenset({"travel"}),
}


def _abs(href: str | None) -> str:
    if not href:
        return BASE + "/"
    return urljoin(BASE, href)


def _short_time(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    return s.split(",")[0].strip()


def _split_title_time(text: str) -> tuple[str, str]:
    text = " ".join(text.split())
    m = _TIME_TAIL.search(text)
    if m:
        return text[: m.start()].strip(), m.group(1)
    return text, ""


def _news_item(
    title: str,
    href: str | None,
    category: str,
    time_display: str,
    image_url: str | None = None,
    lead: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title.strip() or "Новость",
        "url": _abs(href),
        "category": (category or "Новости").strip() or "Новости",
        "time_display": (time_display or "").strip(),
        "image_url": (image_url or "").strip(),
        "lead": (lead or "").strip(),
    }


def _pick_image_url(root) -> str:
    if not root:
        return ""
    img = root.select_one(
        "img.picture__image[src], "
        "img.card-big__image[src], "
        "img.card-mini__image[src], "
        "img[src]"
    )
    if not img:
        return ""
    # На Lenta картинки часто лежат в data-src/data-original/srcset
    src = (
        (img.get("src") or "").strip()
        or (img.get("data-src") or "").strip()
        or (img.get("data-original") or "").strip()
    )
    if not src:
        srcset = (img.get("srcset") or "").strip()
        if srcset:
            # Берём самый первый URL из srcset (обычно он валидный и быстрый)
            first = srcset.split(",")[0].strip().split(" ")[0].strip()
            src = first
    if not src:
        return ""
    if src.startswith("//"):
        src = "https:" + src
    return urljoin(BASE, src)


def _from_card_big(a) -> dict[str, Any] | None:
    if not a:
        return None
    href = a.get("href")
    h3 = a.select_one("h3.card-big__title, h3")
    title = h3.get_text(" ", strip=True) if h3 else ""
    if not title:
        title = a.get_text(" ", strip=True)
    tim = a.select_one("time")
    t_raw = tim.get_text(" ", strip=True) if tim else ""
    # Рубрика на главной не выводится; подтягивается со страницы статьи в main.load_news().
    return _news_item(
        title,
        href,
        "Новости",
        _short_time(t_raw) or t_raw,
        image_url=_pick_image_url(a),
    )


def _from_card_mini(a) -> dict[str, Any] | None:
    if not a:
        return None
    href = a.get("href")
    h3 = a.select_one("h3.card-mini__title, h3")
    title = h3.get_text(" ", strip=True) if h3 else ""
    tim = a.select_one("time")
    t_raw = tim.get_text(" ", strip=True) if tim else ""
    return _news_item(
        title,
        href,
        "Новости",
        _short_time(t_raw) or t_raw,
        image_url=_pick_image_url(a),
    )


def _with_article_image(item: dict[str, Any], soup: BeautifulSoup) -> dict[str, Any]:
    """Если в карточке нет <img>, пробуем найти рядом <img> по ссылке."""
    if not item or item.get("image_url"):
        return item
    url = item.get("url") or ""
    if not url:
        return item
    # ищем соответствующую ссылку и картинку внутри
    a = soup.select_one(f"a[href='{url.replace(BASE, '')}'], a[href='{url}']")
    img_url = _pick_image_url(a) if a else ""
    if img_url:
        item["image_url"] = img_url
    return item


def _extract_daily(soup: BeautifulSoup) -> list[dict[str, Any]]:
    box = soup.select_one(".topnews")
    if not box:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for a in box.select("a[href^='/news/'], a[href^='/articles/']"):
        href = a.get("href")
        if not href or href in seen:
            continue
        seen.add(href)
        raw = a.get_text(" ", strip=True)
        title, tstr = _split_title_time(raw)
        if not title:
            h3 = a.find("h3")
            if h3:
                title = h3.get_text(" ", strip=True)
        if not title:
            continue
        out.append(_news_item(title, href, "Новости", tstr, image_url=_pick_image_url(a)))
        if len(out) >= 12:
            break
    return out


def _extract_main(
    soup: BeautifulSoup,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    sec = soup.select_one(".main-page__section")
    if not sec:
        return None, []
    hero_el = sec.select_one(
        "a.card-big[href^='/news/'], a.card-big[href^='/articles/']"
    )
    hero = _from_card_big(hero_el)
    if hero and not hero.get("image_url"):
        # Иногда <img> может оказаться выше/рядом с ссылкой
        parent = getattr(hero_el, "parent", None)
        hero["image_url"] = _pick_image_url(parent) or _pick_image_url(sec)
    grid: list[dict[str, Any]] = []
    seen: set[str] = set()
    if hero:
        seen.add(hero["url"])

    # На главной Lenta "сеткой" часто идут не card-mini, а card-big/_longgrid и card-feature.
    candidates = sec.select(
        "a.card-feature[href^='/news/'], a.card-feature[href^='/articles/'], "
        "a.card-big._longgrid[href^='/news/'], a.card-big._longgrid[href^='/articles/'], "
        "a.card-big._topnews[href^='/news/'], a.card-big._topnews[href^='/articles/']"
    )
    for a in candidates:
        href = a.get("href")
        if not href:
            continue
        url = _abs(href)
        if url in seen:
            continue
        seen.add(url)
        item = _from_card_big(a) or _from_card_mini(a)
        if item:
            grid.append(item)
        if len(grid) >= 6:
            break

    # Fallback: если кандидатов нет — старый вариант с card-mini
    if len(grid) < 4:
        for a in sec.select(
            "a.card-mini[href^='/news/'], a.card-mini[href^='/articles/']"
        ):
            href = a.get("href")
            if not href:
                continue
            url = _abs(href)
            if url in seen:
                continue
            seen.add(url)
            item = _from_card_mini(a)
            if item:
                grid.append(item)
            if len(grid) >= 6:
                break

    return hero, grid


def _extract_popular(
    soup: BeautifulSoup,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    box = soup.select_one("div.slider._popular")
    if not box:
        return None, []
    cards = box.select(
        "a.card-big._article[href^='/news/'], "
        "a.card-big._article[href^='/articles/']"
    )
    if not cards:
        cards = box.select(
            "a.card-big._popular[href^='/news/'], "
            "a.card-big._popular[href^='/articles/']"
        )
    items: list[dict[str, Any]] = []
    for a in cards:
        it = _from_card_big(a)
        if it:
            items.append(it)
        if len(items) >= 7:
            break
    if not items:
        return None, []
    return items[0], items[1:4]


def is_bot_challenge_page(html: str) -> bool:
    low = html.lower()
    return (
        "just a moment" in low
        or "cf-browser-verification" in low
        or "проверка браузера" in low
    )


_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_MONTHS_GEN = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def extract_article_published(article_html: str) -> tuple[str, str, str]:
    """Возвращает (date_display, time_display, datetime_iso) из страницы статьи."""
    if not article_html or len(article_html) < 2000:
        return "", "", ""
    soup = BeautifulSoup(article_html, "lxml")

    # Часто публикуется через <meta property="article:published_time" ...>
    meta = soup.select_one("meta[property='article:published_time'][content]")
    dt_raw = (meta.get("content") or "").strip() if meta else ""
    if not dt_raw:
        t = soup.select_one("time[datetime]")
        dt_raw = (t.get("datetime") or "").strip() if t else ""
    if not dt_raw:
        return "", "", ""

    # Нормализация ISO
    iso = dt_raw.replace("Z", "+00:00")
    try:
        dt = _dt.datetime.fromisoformat(iso)
    except ValueError:
        m = re.search(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})", dt_raw)
        if not m:
            return "", "", ""
        date_display = m.group(1)
        time_display = m.group(2)
        return date_display, time_display, dt_raw

    date_display = f"{dt.day} {_MONTHS_GEN[dt.month - 1]} {dt.year}"
    time_display = f"{dt.hour:02d}:{dt.minute:02d}"
    return date_display, time_display, dt_raw


def extract_first_sentence(article_html: str) -> str:
    """Пытаемся извлечь первое предложение статьи Lenta.ru."""
    if not article_html or len(article_html) < 2000:
        return ""
    soup = BeautifulSoup(article_html, "lxml")
    # Основной контент может меняться, поэтому используем несколько селекторов.
    container = soup.select_one(
        ".topic-body__content, .topic-body, article, .b-topic__content"
    )
    if not container:
        container = soup
    for p in container.select("p"):
        txt = p.get_text(" ", strip=True)
        if not txt or len(txt) < 40:
            continue
        # берем только первое предложение
        parts = _SENT_SPLIT.split(txt, maxsplit=1)
        return (parts[0] or "").strip()
    return ""


def extract_article_rubric(article_html: str) -> tuple[str, str]:
    """
    Рубрика со страницы статьи: подпись и slug из /rubrics/<slug>/.
    Возвращает (label, slug), например («Спорт», «sport»).
    """
    if not article_html or len(article_html) < 2000:
        return "", ""
    soup = BeautifulSoup(article_html, "lxml")
    a = soup.select_one(
        ".topic-header__rubric a[href*='/rubrics/'], "
        "a.topic-header__rubric[href*='/rubrics/']"
    )
    if not a:
        return "", ""
    href = (a.get("href") or "").strip()
    label = a.get_text(" ", strip=True)
    m = re.search(r"/rubrics/([^/]+)/?", href)
    slug = (m.group(1) if m else "").lower()
    return label, slug


def extract_article_image_url(article_html: str) -> str:
    """Пытаемся извлечь основную картинку статьи (обычно detail_*.jpg)."""
    if not article_html or len(article_html) < 2000:
        return ""
    soup = BeautifulSoup(article_html, "lxml")
    img = soup.select_one(
        "img.picture__image[src], "
        "figure img[src], "
        "article img[src]"
    )
    if not img:
        return ""
    src = (img.get("src") or "").strip()
    if not src:
        return ""
    if src.startswith("//"):
        src = "https:" + src
    return urljoin(BASE, src)


def parse_lenta_home(html: str) -> dict[str, Any]:
    if not html or len(html) < 5000:
        raise ValueError("Слишком короткий ответ")
    if is_bot_challenge_page(html):
        raise ValueError("Страница защиты (challenge)")
    soup = BeautifulSoup(html, "lxml")
    daily = _extract_daily(soup)
    hero, grid = _extract_main(soup)
    pop_f, pop_list = _extract_popular(soup)

    # Некоторые блоки приходят без <img> внутри карточек (картинки могут быть фоном/в соседних узлах)
    if hero:
        hero = _with_article_image(hero, soup)
    grid = [_with_article_image(dict(x), soup) for x in (grid or [])]
    pop_f = _with_article_image(pop_f, soup) if pop_f else pop_f

    if len(daily) < 4:
        raise ValueError("Не удалось извлечь ленту новостей")

    if not hero and daily:
        hero = dict(daily[0])
    if len(grid) < 4 and len(daily) > 1:
        used = {hero["url"]} if hero else set()
        for d in daily:
            if d["url"] in used:
                continue
            used.add(d["url"])
            grid.append(dict(d))
            if len(grid) >= 4:
                break

    if not pop_f and len(daily) > 6:
        pop_f = dict(daily[6])
    if not pop_f and daily:
        pop_f = dict(daily[-1])
    if len(pop_list) < 3:
        extra = daily[7:10] if len(daily) > 7 else []
        for e in extra:
            if len(pop_list) >= 3:
                break
            if pop_f and e["url"] == pop_f["url"]:
                continue
            pop_list.append(dict(e))
    skip_pop = {pop_f["url"]} if pop_f else set()
    skip_pop.update(p["url"] for p in pop_list)
    idx = 0
    while len(pop_list) < 3 and idx < len(daily):
        d = daily[idx]
        idx += 1
        if d["url"] in skip_pop:
            continue
        pop_list.append(dict(d))
        skip_pop.add(d["url"])

    while len(grid) < 4 and len(daily) > 1:
        added = False
        for d in daily:
            if hero and d["url"] == hero["url"]:
                continue
            if any(g["url"] == d["url"] for g in grid):
                continue
            grid.append(dict(d))
            added = True
            if len(grid) >= 4:
                break
        if not added:
            break

    return {
        "daily_news": daily[:6],
        "main_hero": hero,
        "main_grid": grid[:4],
        "popular_featured": pop_f,
        "popular_list": pop_list[:3],
    }
