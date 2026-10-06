#!/usr/bin/env python3
"""Build crawlable brand and size pages from the visible stock catalog."""
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://tfkeramika.ru'
TODAY = '2026-10-05'
source = (ROOT / 'index.html').read_text()
items = json.loads(re.search(r'const ITEMS=(\[.*?\]);\n', source).group(1))

def esc(value):
    return html.escape(str(value), quote=True)

def slug(value):
    table = str.maketrans({'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'})
    return re.sub(r'[^a-z0-9]+', '-', value.lower().translate(table)).strip('-')

def stock_num(value):
    return f'{int(value):,}'.replace(',', '\u00a0')

def row(it):
    candidates = [it.get('ph'), it.get('img')]
    img = next((path for path in candidates if path and (ROOT / path).is_file()), '')
    image = f'<img src="../../{esc(img)}" alt="{esc(it["n"])} — {esc(it["s"])}" loading="lazy" decoding="async">' if img else ''
    brand = it.get('b') or (f'производство: {it["origin"]}' if it.get('origin') else '')
    meta = ', '.join(x for x in (it['s'], brand, it.get('g', '')) if x)
    price = f'{stock_num(it["p"])} ₽/м²' if it.get('p') else 'Узнать цену'
    article = f'<span>Артикул: {esc(it["a"])}</span>' if it.get('a') else ''
    return (f'<a class="item" href="../../{esc(it["url"])}"><span class="thumb">{image}</span>'
            f'<span class="info"><strong>{esc(it["n"])}</strong><span>{esc(meta)}</span>'
            f'<span class="stock">В наличии {stock_num(it["q"])} м²</span>{article}</span>'
            f'<span class="price">{price}</span></a>')

CSS = '''<style>
:root{--bg:#e9e8e4;--card:#f6f5f2;--ink:#1f2429;--mut:#5d646b;--line:#c6c5be;--tag:#f4c400}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}.wrap{max-width:980px;margin:auto;padding:0 16px}header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:2}header .wrap{height:58px;display:flex;align-items:center;justify-content:space-between}.brand{font-size:1.2rem;font-weight:800;color:var(--ink);text-decoration:none}.crumb{padding:18px 0 4px;font-size:.9rem;color:var(--mut)}.crumb a{color:inherit}h1,h2{font-family:"Arial Narrow",Arial,sans-serif;line-height:1.12}h1{font-size:clamp(2rem,5vw,3rem);margin:14px 0 10px}h2{font-size:1.55rem;margin:28px 0 12px}.intro{max-width:760px;color:var(--mut);margin:0 0 10px}.facts{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.fact{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-weight:700}.note{color:var(--mut);font-size:.88rem}.items{display:grid;gap:8px;margin:18px 0 28px}.item{display:grid;grid-template-columns:64px minmax(0,1fr) auto;align-items:center;gap:12px;padding:10px;background:var(--card);border:1px solid var(--line);border-radius:8px;color:var(--ink);text-decoration:none}.item:hover{border-color:var(--ink)}.thumb{width:64px;height:64px;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:#ddd}.thumb img{width:100%;height:100%;object-fit:cover}.info{display:grid;gap:2px}.info strong{line-height:1.25}.info>span{font-size:.88rem;color:var(--mut)}.info .stock{color:#315a2d;font-weight:700}.price{background:var(--tag);padding:6px 10px;font-weight:800;white-space:nowrap}.cta{background:var(--ink);color:#fff;border-radius:10px;padding:18px;margin:24px 0}.cta p{margin:6px 0 14px}.btn{display:inline-flex;min-height:48px;align-items:center;justify-content:center;padding:10px 16px;border-radius:6px;background:var(--tag);color:#111;text-decoration:none;font-weight:750}.other-links{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 28px}.other-links a{background:var(--card);padding:8px 12px;border:1px solid var(--line);border-radius:7px;color:var(--ink);text-decoration:none}footer{border-top:1px solid var(--line);padding:18px 0 30px;color:var(--mut);font-size:.9rem}footer a{color:inherit}@media(max-width:560px){.item{grid-template-columns:56px minmax(0,1fr)}.thumb{width:56px;height:56px}.price{grid-column:2;justify-self:start}.wrap{padding:0 13px}}
</style>'''

all_brands = sorted({x.get('b') for x in items if x.get('b') and x.get('b') != 'Казахстан'})
format_counts = Counter(x.get('k') for x in items)
popular_formats = [k for k,n in format_counts.most_common() if k and n >= 10]

def format_links():
    return ''.join(f'<a href="../../formats/{slug(k.replace("×","x"))}/">{esc(k)} мм · {format_counts[k]} позиций</a>' for k in popular_formats)

brand_pages = []
for brand in all_brands:
    selected = [x for x in items if x.get('b') == brand]
    if len(selected) < 5:
        continue
    page_slug = slug(brand)
    path = f'brands/{page_slug}/'
    name = f'Плитка и керамогранит {brand} в наличии в СПб'
    title = f'{brand}: плитка и керамогранит в наличии в СПб | ТФ Керамика'
    desc = f'{len(selected)} позиций {brand} из наличия на складе в Войскорово: размеры, сорта, артикулы и остатки. Уточните цену, наличие и доставку по Санкт-Петербургу и Ленинградской области.'
    total = sum(int(x['q']) for x in selected)
    types = Counter(x['t'] for x in selected)
    category_words = []
    if types['tile']: category_words.append(f'{types["tile"]} позиций керамической плитки')
    if types['gres']: category_words.append(f'{types["gres"]} позиций керамогранита')
    schema = {'@context':'https://schema.org','@type':'CollectionPage','name':name,'description':desc,'url':f'{BASE}/{path}','mainEntity':{'@type':'ItemList','numberOfItems':len(selected),'itemListElement':[{'@type':'ListItem','position':i+1,'url':f'{BASE}/{x["url"]}'} for i,x in enumerate(selected)]}}
    breadcrumb = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Главная','item':f'{BASE}/'},{'@type':'ListItem','position':2,'name':'Бренды','item':f'{BASE}/#brands'},{'@type':'ListItem','position':3,'name':brand,'item':f'{BASE}/{path}'}]}
    content = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{BASE}/{path}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(',',':'))}</script><script type="application/ld+json">{json.dumps(breadcrumb,ensure_ascii=False,separators=(',',':'))}</script>{CSS}</head><body><header><div class="wrap"><a class="brand" href="../../">ТФ Керамика</a><a class="btn" href="../../index.html#prices">Запросить цену</a></div></header><main class="wrap"><nav class="crumb" aria-label="Навигационная цепочка"><a href="../../">Главная</a> › Бренды › {esc(brand)}</nav><h1>{esc(name)}</h1><p class="intro">В каталоге — {', '.join(category_words)} {esc(brand)} с указанными размерами, сортами и артикулами. Можно проверить остаток по конкретной позиции, запросить цену и подготовить расчёт для объекта.</p><div class="facts"><span class="fact">{len(selected)} позиций в каталоге</span><span class="fact">Суммарный остаток: {stock_num(total)} м²</span><span class="fact">Самовывоз из Войскорово</span></div><p class="note">Остатки указаны по складскому каталогу на 1 октября 2026 года и требуют подтверждения перед заказом. Доставка согласуется по адресу объекта.</p><h2>Позиции {esc(brand)} в наличии</h2><div class="items">{''.join(row(x) for x in selected)}</div><section class="cta" id="contact"><h2>Нужен расчёт для объекта?</h2><p>Отправьте артикулы или названия и необходимое количество. Уточним актуальный остаток и цену, подготовим счёт и согласуем самовывоз или доставку.</p><a class="btn" href="mailto:novorom@mail.ru?subject={quote('Расчёт плитки ' + brand)}">Написать на электронную почту</a></section><h2>Каталог по размерам</h2><div class="other-links">{format_links()}</div></main><footer><div class="wrap">Склад: Ленинградская область, Тосненский район, посёлок Войскорово, 14В · Пн–Пт, 09:00–18:00 · <a href="mailto:novorom@mail.ru">novorom@mail.ru</a> · <a href="../../">Все товары</a></div></footer><script>(function(){{if(location.protocol!=="file:")return;document.querySelectorAll('a[href]').forEach(function(a){{var h=a.getAttribute('href');if(h&&h.endsWith('/'))a.setAttribute('href',h+'index.html')}})}})();</script></body></html>'''
    out = ROOT / path / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    brand_pages.append((brand, path, len(selected)))

format_pages = []

for dimensions in popular_formats:
    selected = [x for x in items if x.get('k') == dimensions]
    page_slug = slug(dimensions.replace('×','x'))
    path = f'formats/{page_slug}/'
    title = f'Плитка и керамогранит {dimensions} мм в наличии в СПб | ТФ Керамика'
    name = f'Плитка и керамогранит {dimensions} мм в наличии в СПб'
    desc = f'{len(selected)} позиций плитки и керамогранита формата {dimensions} мм со склада в Войскорово: производители, сорта, артикулы и остатки. Уточните цену и доставку по Санкт-Петербургу и области.'
    brands = Counter(x.get('b') for x in selected if x.get('b'))
    brand_summary = ', '.join(f'{b} ({n})' for b,n in brands.most_common(5))
    total = sum(int(x['q']) for x in selected)
    types = Counter(x['t'] for x in selected)
    type_text = ' и '.join(x for x,n in [('керамической плитки',types['tile']),('керамогранита',types['gres'])] if n)
    schema = {'@context':'https://schema.org','@type':'CollectionPage','name':name,'description':desc,'url':f'{BASE}/{path}','mainEntity':{'@type':'ItemList','numberOfItems':len(selected),'itemListElement':[{'@type':'ListItem','position':i+1,'url':f'{BASE}/{x["url"]}'} for i,x in enumerate(selected)]}}
    breadcrumb = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Главная','item':f'{BASE}/'},{'@type':'ListItem','position':2,'name':'Размеры','item':f'{BASE}/#sizes'},{'@type':'ListItem','position':3,'name':dimensions+' мм','item':f'{BASE}/{path}'}]}
    content = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{BASE}/{path}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(',',':'))}</script><script type="application/ld+json">{json.dumps(breadcrumb,ensure_ascii=False,separators=(',',':'))}</script>{CSS}</head><body><header><div class="wrap"><a class="brand" href="../../">ТФ Керамика</a><a class="btn" href="../../index.html#prices">Запросить цену</a></div></header><main class="wrap"><nav class="crumb" aria-label="Навигационная цепочка"><a href="../../">Главная</a> › Размеры › {esc(dimensions)} мм</nav><h1>{esc(name)}</h1><p class="intro">Подборка {esc(type_text)} размера {esc(dimensions)} мм, которые сейчас опубликованы в складском каталоге. В карточках указаны фактические названия, производители, сорта, артикулы и складские остатки.</p><div class="facts"><span class="fact">{len(selected)} позиций</span><span class="fact">Суммарный остаток: {stock_num(total)} м²</span></div><p class="note">Производители в подборке: {esc(brand_summary) if brand_summary else 'указаны в карточках товаров'}. Остатки по складскому каталогу на 1 октября 2026 года; подтвердите перед заказом. Наличие доставки и её стоимость согласуются по адресу объекта.</p><h2>Товары размера {esc(dimensions)} мм</h2><div class="items">{''.join(row(x) for x in selected)}</div><section class="cta" id="contact"><h2>Нужен расчёт для объекта?</h2><p>Напишите выбранные позиции и площадь объекта. Уточним актуальные остатки, цену и варианты отгрузки.</p><a class="btn" href="mailto:novorom@mail.ru?subject={quote('Расчёт плитки ' + dimensions)}">Запросить расчёт по почте</a></section><h2>Другие популярные размеры</h2><div class="other-links">{format_links()}</div></main><footer><div class="wrap">Склад: Ленинградская область, Тосненский район, посёлок Войскорово, 14В · Пн–Пт, 09:00–18:00 · <a href="mailto:novorom@mail.ru">novorom@mail.ru</a> · <a href="../../">Все товары</a></div></footer><script>(function(){{if(location.protocol!=="file:")return;document.querySelectorAll('a[href]').forEach(function(a){{var h=a.getAttribute('href');if(h&&h.endsWith('/'))a.setAttribute('href',h+'index.html')}})}})();</script></body></html>'''
    out = ROOT / path / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    format_pages.append((dimensions, path, len(selected)))

# Color pages use the same broad color grouping as the catalog filter.
COLOR_RULES = [
    ('Серый', re.compile(r'сер|\bgrey\b|\bgray\b', re.I)),
    ('Белый', re.compile(r'бел|\bwhite\b|\bice\b', re.I)),
    ('Бежевый', re.compile(r'беж|\bbeige\b|\bcrema\b', re.I)),
    ('Песочный', re.compile(r'песоч', re.I)),
    ('Чёрный', re.compile(r'черн|чёрн|\bblack\b', re.I)),
    ('Коричневый', re.compile(r'корич|\bbrown\b|\bamber\b', re.I)),
    ('Терракотовый', re.compile(r'терракот', re.I)),
    ('Красный', re.compile(r'красн|\bred\b', re.I)),
    ('Оранжевый', re.compile(r'оранж|\borange\b', re.I)),
    ('Жёлтый', re.compile(r'желт|жёлт|\byellow\b', re.I)),
    ('Зелёный', re.compile(r'зелен|\bgreen\b|\bolive\b', re.I)),
    ('Бирюзовый', re.compile(r'бирюз|\bturquoise\b', re.I)),
    ('Синий', re.compile(r'син|голуб|\bblue\b|\bnavy\b', re.I)),
    ('Розовый', re.compile(r'роз|\bpink\b', re.I)),
    ('Фиолетовый', re.compile(r'фиол|лилов|\bpurple\b', re.I)),
]

def color_of(item):
    for color, rule in COLOR_RULES:
        if rule.search(item.get('n', '')):
            return color
    if re.search(r'светл', item.get('n', ''), re.I):
        return 'Белый'
    return 'Другие'

COLOR_FORMS = {
    ('tile','Серый'):('серая','серой'), ('tile','Белый'):('белая','белой'), ('tile','Бежевый'):('бежевая','бежевой'),
    ('gres','Серый'):('серый','серого'), ('gres','Белый'):('белый','белого'), ('gres','Бежевый'):('бежевый','бежевого'),
}
TYPE_WORD = {'tile':'керамическая плитка','gres':'керамогранит'}
color_pages = []
for product_type in ('tile','gres'):
    for color in ('Серый','Белый','Бежевый'):
        selected = [x for x in items if x['t'] == product_type and color_of(x) == color]
        if len(selected) < 10:
            continue
        adjective, genitive = COLOR_FORMS[(product_type,color)]
        type_word = TYPE_WORD[product_type]
        phrase = f'{adjective} {type_word}' if product_type == 'tile' else f'{adjective} {type_word}'
        slug_part = f'keramicheskaya-plitka-{slug(color)}' if product_type == 'tile' else f'keramogranit-{slug(color)}'
        path = f'colors/{slug_part}/'
        title = f'{phrase.capitalize()} в СПб: каталог и наличие со склада | ТФ Керамика'
        name = f'{phrase.capitalize()} в наличии в Санкт-Петербурге'
        desc = f'{len(selected)} позиций: {phrase} разных форматов и производителей со склада в Войскорово. Сравните размеры, сорта и артикулы, уточните цену и доставку по СПб и Ленинградской области.'
        brands = Counter(x.get('b') for x in selected if x.get('b'))
        formats = Counter(x.get('k') for x in selected if x.get('k'))
        total = sum(int(x['q']) for x in selected)
        schema = {'@context':'https://schema.org','@type':'CollectionPage','name':name,'description':desc,'url':f'{BASE}/{path}','mainEntity':{'@type':'ItemList','numberOfItems':len(selected),'itemListElement':[{'@type':'ListItem','position':i+1,'url':f'{BASE}/{x["url"]}'} for i,x in enumerate(selected)]}}
        breadcrumb = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Главная','item':f'{BASE}/'},{'@type':'ListItem','position':2,'name':type_word.capitalize(),'item':f'{BASE}/catalog/keramicheskaya-plitka-spb/' if product_type == 'tile' else f'{BASE}/catalog/keramogranit-spb/'},{'@type':'ListItem','position':3,'name':name,'item':f'{BASE}/{path}'}]}
        content = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{BASE}/{path}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(',',':'))}</script><script type="application/ld+json">{json.dumps(breadcrumb,ensure_ascii=False,separators=(',',':'))}</script>{CSS}</head><body><header><div class="wrap"><a class="brand" href="../../">ТФ Керамика</a><a class="btn" href="../../index.html#prices">Запросить цену</a></div></header><main class="wrap"><nav class="crumb" aria-label="Навигационная цепочка"><a href="../../">Главная</a> › {esc(type_word.capitalize())} › {esc(color)}</nav><h1>{esc(name)}</h1><p class="intro">Подборка {len(selected)} позиций категории «{esc(phrase)}»: реальные товары из складского каталога с размерами, производителями, сортами и артикулами. Оттенки объединены в общий цвет по названию товара.</p><div class="facts"><span class="fact">{len(selected)} позиций</span><span class="fact">Суммарный остаток: {stock_num(total)} м²</span><span class="fact">{len(formats)} форматов</span></div><p class="note">Производители в подборке: {esc(', '.join(b for b,_ in brands.most_common(6)))}. Остатки по складскому каталогу на 1 октября 2026 года; уточните наличие и цену перед заказом.</p><h2>{esc(phrase.capitalize())} в наличии</h2><div class="items">{''.join(row(x) for x in selected)}</div><section class="cta" id="contact"><h2>Нужен расчёт для объекта?</h2><p>Отправьте артикулы или названия и необходимое количество. Проверим актуальные остатки, цену и варианты отгрузки.</p><a class="btn" href="mailto:novorom@mail.ru?subject={quote('Расчёт ' + phrase)}">Запросить расчёт по почте</a></section><h2>Популярные размеры</h2><div class="other-links">{format_links()}</div></main><footer><div class="wrap">Склад: Ленинградская область, Тосненский район, посёлок Войскорово, 14В · Пн–Пт, 09:00–18:00 · <a href="mailto:novorom@mail.ru">novorom@mail.ru</a> · <a href="../../">Все товары</a></div></footer><script>(function(){{if(location.protocol!=="file:")return;document.querySelectorAll('a[href]').forEach(function(a){{var h=a.getAttribute('href');if(h&&h.endsWith('/'))a.setAttribute('href',h+'index.html')}})}})();</script></body></html>'''
        out = ROOT / path / 'index.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content)
        color_pages.append((phrase.capitalize(),path,len(selected)))

# Add direct, crawlable links in the homepage, close to the existing conversion CTA.
links_html = '<section class="seo-navigation" aria-labelledby="seo-navigation-title"><h2 id="seo-navigation-title">Подбор плитки по бренду и размеру</h2><p>Быстрый переход к производителям и популярным форматам из складского каталога.</p><h3 id="brands">Бренды</h3><ul>'
links_html += ''.join(f'<li><a href="{path}">{esc(brand)} — {count} позиций</a></li>' for brand,path,count in brand_pages)
links_html += '</ul><h3 id="sizes">Популярные размеры</h3><ul>'
links_html += ''.join(f'<li><a href="formats/{slug(dim.replace("×","x"))}/">{esc(dim)} мм — {count} позиций</a></li>' for dim,count in format_counts.most_common() if dim in popular_formats)
links_html += '</ul><h3>Подборки по цвету</h3><ul>'
links_html += ''.join(f'<li><a href="{path}">{esc(label)} — {count} позиций</a></li>' for label,path,count in color_pages)
links_html += '</ul></section>'
style = '<style>.seo-navigation{padding:24px 0 8px;border-top:1px solid var(--line)}.seo-navigation h2{margin-bottom:8px}.seo-navigation h3{margin:16px 0 5px;font-size:1rem}.seo-navigation ul{display:flex;flex-wrap:wrap;gap:7px 18px;list-style:none;padding:0;margin:0}.seo-navigation a{color:var(--ink)}.seo-navigation p{color:var(--mut);margin:0}</style>'
if re.search(r'<section class="seo-navigation".*?</section>', source, re.S):
    source = re.sub(r'<section class="seo-navigation".*?</section>', links_html, source, count=1, flags=re.S)
else:
    source = source.replace('</main>', links_html + '\n</main>')
if '.seo-navigation{' not in source:
    source = source.replace('</head>', style + '\n</head>')
(ROOT / 'index.html').write_text(source)

# One accurate Store entity on the home page (remove the duplicate entity).
source = (ROOT / 'index.html').read_text()
scripts = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', source, re.S))
store_scripts = []
for match in scripts:
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        continue
    if data.get('@type') in ('Store','LocalBusiness'):
        store_scripts.append(match)
store = {'@context':'https://schema.org','@type':'Store','@id':f'{BASE}/#store','name':'ТФ Керамика','url':f'{BASE}/','email':'novorom@mail.ru','description':'Плитка и керамогранит для строителей в Санкт-Петербурге и Ленинградской области. Склад в посёлке Войскорово, самовывоз и доставка по согласованию.','address':{'@type':'PostalAddress','streetAddress':'14В','addressLocality':'посёлок Войскорово','addressRegion':'Ленинградская область','addressCountry':'RU'},'openingHoursSpecification':[{'@type':'OpeningHoursSpecification','dayOfWeek':['Monday','Tuesday','Wednesday','Thursday','Friday'],'opens':'09:00','closes':'18:00'}]}
if store_scripts:
    first = store_scripts[0]
    source = source[:first.start()] + '<script type="application/ld+json">' + json.dumps(store,ensure_ascii=False,separators=(',',':')) + '</script>' + source[first.end():]
    # Locate and remove any remaining duplicate Store/LocalBusiness blocks after replacement.
    for match in reversed(list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', source, re.S))):
        try: data = json.loads(match.group(1))
        except json.JSONDecodeError: continue
        if data.get('@type') in ('Store','LocalBusiness') and data.get('@id') != store['@id']:
            source = source[:match.start()] + source[match.end():]
    (ROOT / 'index.html').write_text(source)

# Keep sitemap changes truthful and include only the pages generated here.
sitemap_path = ROOT / 'sitemap.xml'
sitemap = sitemap_path.read_text()
home_url = f'{BASE}/'
sitemap = re.sub(r'(<loc>' + re.escape(home_url) + r'</loc><lastmod>)[^<]+(</lastmod>)', rf'\g<1>{TODAY}\g<2>', sitemap)
existing = set(re.findall(r'<loc>(.*?)</loc>', sitemap))
for _,path,_ in brand_pages + format_pages + color_pages:
    url = f'{BASE}/{path}'
    if url not in existing:
        sitemap = sitemap.replace('</urlset>', f'  <url><loc>{url}</loc><lastmod>{TODAY}</lastmod></url>\n</urlset>')
sitemap_path.write_text(sitemap)

# Ensure explicit clean canonical routes are served directly from static folders.
vercel_path = ROOT / 'vercel.json'
vercel = json.loads(vercel_path.read_text())
for _,path,_ in brand_pages + format_pages:
    src = '/' + path.rstrip('/') + '/index.html'
    dest = '/' + path
    if not any(rule.get('source') == src for rule in vercel.get('redirects', [])):
        vercel.setdefault('redirects', []).append({'source':src,'destination':dest,'permanent':True})
vercel_path.write_text(json.dumps(vercel,ensure_ascii=False,indent=2)+'\n')
print(f'Created {len(brand_pages)} brand, {len(format_pages)} size, and {len(color_pages)} color landing pages')
