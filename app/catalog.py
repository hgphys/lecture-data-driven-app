"""Product catalog for the shopping demo.

Generic デパート assortment; not tied to any specific school or city.
Categories are intentionally aligned with the user-registration
interests so analysis demos can group by category × interest.
"""

from __future__ import annotations

from typing import TypedDict


class Product(TypedDict):
    name: str
    category: str
    price: int


CATEGORIES: list[str] = ["食品", "ドリンク", "雑貨", "お土産", "文房具"]


CATALOG: list[Product] = [
    {"name": "たい焼き", "category": "食品", "price": 180},
    {"name": "おにぎり", "category": "食品", "price": 150},
    {"name": "おでんセット", "category": "食品", "price": 500},
    {"name": "アイスクリーム", "category": "食品", "price": 250},
    {"name": "焼き菓子セット", "category": "食品", "price": 800},
    {"name": "コーヒー", "category": "ドリンク", "price": 250},
    {"name": "ホットチョコ", "category": "ドリンク", "price": 300},
    {"name": "文房具セット", "category": "文房具", "price": 600},
    {"name": "手ぬぐい", "category": "雑貨", "price": 500},
    {"name": "お土産菓子箱", "category": "お土産", "price": 1200},
]


def find(name: str) -> Product:
    for p in CATALOG:
        if p["name"] == name:
            return p
    raise KeyError(name)
