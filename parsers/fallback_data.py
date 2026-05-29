"""Статические новости из исходной вёрстки (если парсинг недоступен)."""

from __future__ import annotations

from typing import Any

_PLACE = "https://lenta.ru/"


def get_fallback() -> dict[str, Any]:
    daily = [
        {
            "title": "Кот Ахилл предсказал победу российской сборной над Египтом на ЧМ-2018",
            "url": _PLACE,
            "category": "ЧМ по футболу",
            "time_display": "10:48",
        },
        {
            "title": "«Нафтогаз»: суд разрешил заморозить активы «Газпрома» в Великобритании",
            "url": _PLACE,
            "category": "Политика",
            "time_display": "10:48",
        },
        {
            "title": "Минтранс предписал оборудовать общественный транспорт кондиционерами",
            "url": _PLACE,
            "category": "Транспорт",
            "time_display": "10:48",
        },
        {
            "title": "Летние кафе Москвы временно закроются из-за непогоды",
            "url": _PLACE,
            "category": "Погода",
            "time_display": "10:48",
        },
        {
            "title": "Комплексное благоустройство Щелковского шоссе завершится в июне",
            "url": _PLACE,
            "category": "Транспорт",
            "time_display": "10:48",
        },
        {
            "title": "В Москве назвали самое популярное мороженное у болельщиков ЧМ-2018",
            "url": _PLACE,
            "category": "ЧМ по футболу",
            "time_display": "10:48",
        },
    ]
    hero = {
        "title": "В Крыму отреагировали на слова Кравчука о возврате полуострова",
        "url": _PLACE,
        "category": "Политика",
        "time_display": "10:48",
        "image_url": "Img/clean-news-article.png",
    }
    grid = [
        {
            "title": "Алексей Навальный объявил акцию против пенсионной реформы 1 июля",
            "url": _PLACE,
            "category": "Политика",
            "time_display": "10:48",
        },
        {
            "title": "Дума увеличила пошлины за выдачу загранпаспортов и водительских прав",
            "url": _PLACE,
            "category": "Общество",
            "time_display": "12:33",
        },
        {
            "title": "В России заработал стриминговый сервис You Tube",
            "url": _PLACE,
            "category": "Интернет",
            "time_display": "11:17",
        },
        {
            "title": "Кейн признан лучшим игроком матча ЧМ-2018 Тунис-Англия",
            "url": _PLACE,
            "category": "Политика",
            "time_display": "11:39",
        },
    ]
    pop_f = {
        "title": "Пекин обвинил Вашингтон в развязывании торговой войны",
        "url": _PLACE,
        "category": "Политика",
        "time_display": "10:48",
        "image_url": "Img/clean-special-article.png",
        "lead": "Министерство коммерции Китая заявило, что Пекин примет «качественные» и «количественные» меры, если президент США Дональд Трамп введет дополнительные пошлины на китайские товары.",
    }
    pop_list = [
        {
            "title": "В Турции пообещали найти альтернативу из-за отказа США поставить F-35",
            "url": _PLACE,
            "category": "Политика",
            "time_display": "11:39",
        },
        {
            "title": "Назван минимальный доход для причисления к среднему классу",
            "url": _PLACE,
            "category": "Политика",
            "time_display": "11:39",
        },
        {
            "title": "Назван минимальный доход для причисления к среднему классу",
            "url": _PLACE,
            "category": "Политика",
            "time_display": "11:39",
        },
    ]
    return {
        "daily_news": daily,
        "main_hero": hero,
        "main_grid": grid,
        "popular_featured": pop_f,
        "popular_list": pop_list,
    }
