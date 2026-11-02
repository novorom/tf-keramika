#!/usr/bin/env python3
"""Monitor public pages and purchase/contact paths for iltima.ru."""

from __future__ import annotations

import argparse
import concurrent.futures
import html.parser
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


BASE = "https://iltima.ru"
SITEMAP = f"{BASE}/sitemap.xml"
USER_AGENT = "IltimaSiteHealth/1.0 (+https://iltima.ru/)"
QUICK_PATHS = [
    "/",
    "/catalog/keramicheskaya-plitka-spb/",
    "/catalog/keramogranit-spb/",
    "/delivery-and-returns/",
    "/products/tesina-pesochnyy-600-200-9-mm-standart/",
    "/products/mirabo-seryy-obreznoy-600-600-9-mm-1-sort/",
]


class PageParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.in_title = False
        self.description = ""
        self.canonical = ""
        self.phone_link = False
        self.callback_button = False
        self.callback_form = False
        self.callback_script = False
        self.product_schema = False
        self.product_offer = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content") or ""
        if tag == "link" and values.get("rel", "").lower() == "canonical":
            self.canonical = values.get("href") or ""
        if tag == "a" and (values.get("href") or "").startswith("tel:"):
            self.phone_link = True
        if tag == "button" and (
            values.get("id") in {"order-call", "hcall", "ccall", "sticky-call"}
            or "Заказать звонок" in (values.get("aria-label") or "")
        ):
            self.callback_button = True
        if tag == "form" and values.get("id") == "callback-form":
            self.callback_form = True
        if tag == "script" and (values.get("src") or "").endswith("/js/product-callback.js"):
            self.callback_script = True
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._schema_script = True
            self._schema_text = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag == "script" and getattr(self, "_schema_script", False):
            content = self._schema_text
            if '"Product"' in content or '"ProductGroup"' in content:
                self.product_schema = True
            if '"offers"' in content:
                self.product_offer = True
            self._schema_script = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data
        if getattr(self, "_schema_script", False):
            self._schema_text += data


def fetch(url: str) -> tuple[str, int | None, str, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read(2_500_000).decode("utf-8", errors="replace")
            return url, response.status, body, response.geturl()
    except urllib.error.HTTPError as error:
        return url, error.code, "", error.geturl()
    except Exception as error:  # network failures should become actionable alerts
        return url, None, "", str(error)


def sitemap_urls() -> list[str]:
    _, status, body, final = fetch(SITEMAP)
    if status != 200:
        raise RuntimeError(f"Sitemap returned {status}: {final}")
    root = ET.fromstring(body)
    urls = [node.text.strip() for node in root.iter() if node.tag.endswith("loc") and node.text]
    if not urls:
        raise RuntimeError("Sitemap contains no page URLs")
    return urls


def check_conversion_assets(errors: list[str]) -> None:
    checks = {
        "/js/product-callback.js": ["api.web3forms.com/submit", "callback_request_sent"],
        "/js/analytics-goals.js": ["phone_click", "callback_form_open"],
    }
    for path, markers in checks.items():
        url, status, body, final = fetch(f"{BASE}{path}")
        if status != 200:
            errors.append(f"- `{url}` — скрипт заказа/звонка недоступен: HTTP {status} ({final})")
            continue
        for marker in markers:
            if marker not in body:
                errors.append(f"- `{url}` — в скрипте отсутствует ожидаемая функция связи `{marker}`")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="check every sitemap URL")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    check_conversion_assets(errors)
    if args.full:
        try:
            urls = sitemap_urls()
        except Exception as error:
            print(f"# Проверка Илтима: ошибка\n\n- Не удалось прочитать карту сайта: `{error}`")
            return 1
    else:
        urls = [urllib.parse.urljoin(BASE, path) for path in QUICK_PATHS]

    results: list[tuple[str, int | None, str, str | None]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results.extend(pool.map(fetch, urls))

    checked_products = 0
    for url, status, body, final in results:
        path = urllib.parse.urlparse(url).path
        if status != 200:
            errors.append(f"- `{url}` — HTTP {status if status is not None else 'ошибка сети'} ({final})")
            continue
        page = PageParser()
        try:
            page.feed(body)
        except Exception as error:
            errors.append(f"- `{url}` — не удалось разобрать страницу ({error})")
            continue
        if not page.title.strip():
            errors.append(f"- `{url}` — отсутствует заголовок страницы")
        if not page.description.strip():
            errors.append(f"- `{url}` — отсутствует описание для поиска")
        expected = urllib.parse.urljoin(BASE, path)
        if page.canonical.rstrip("/") != expected.rstrip("/"):
            errors.append(f"- `{url}` — canonical не совпадает с адресом страницы")
        if path.startswith("/products/"):
            checked_products += 1
            if not page.phone_link:
                errors.append(f"- `{url}` — нет прямой кнопки звонка")
            if not page.callback_button:
                errors.append(f"- `{url}` — нет кнопки заказа звонка")
            if not page.callback_form:
                errors.append(f"- `{url}` — нет формы обратного звонка")
            if not page.callback_script:
                errors.append(f"- `{url}` — не подключён обработчик отправки заявки")
            if not page.product_schema:
                warnings.append(f"- `{url}` — отсутствует Product-разметка")
            elif not page.product_offer:
                warnings.append(f"- `{url}` — Product-разметка без offers")

    mode = "все страницы из sitemap" if args.full else "главная, каталоги и ключевые товары"
    lines = [
        "# Проверка сайта Илтима",
        "",
        f"- Режим: {mode}",
        f"- Страниц проверено: {len(results)}",
        f"- Карточек товара проверено: {checked_products}",
        f"- Критических проблем: {len(errors)}",
        f"- Замечаний по Product-разметке: {len(warnings)}",
    ]
    if errors:
        lines += ["", "## Нужно исправить", *errors]
    if warnings:
        lines += ["", "## SEO-наблюдения", *warnings[:50]]
        if len(warnings) > 50:
            lines.append(f"- И ещё {len(warnings) - 50} аналогичных замечаний.")
    if not errors and not warnings:
        lines += ["", "Критичных проблем не найдено."]
    print("\n".join(lines))
    return 1 if errors or warnings else 0


if __name__ == "__main__":
    sys.exit(main())
