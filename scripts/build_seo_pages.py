import json, re, html, unicodedata, sys, shutil
from urllib.parse import quote
from pathlib import Path

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
SITE_URL = 'https://tfkeramika.ru'
index_path = root / 'index.html'
s = index_path.read_text()
m = re.search(r'const ITEMS=(\[.*?\]);\n', s)
items = json.loads(m.group(1))
legacy_urls = {it.get('a') or it['n']: it.get('url', '') for it in items}
legacy_entries = [(it.get('a') or it['n'], it['n'], it.get('url', '')) for it in items]

trans = str.maketrans({'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'})
def slugify(text):
    text = text.lower().translate(trans)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text or 'tile'
def esc(x): return html.escape(str(x), quote=True)
def image_path(it):
    photo=it.get('ph')
    if photo and (root/photo).is_file(): return photo
    image=it.get('img')
    if image and (root/image).is_file(): return image
    return photo or image or ''
def fmt_num(n): return f'{n:,}'.replace(',', '\u00a0')
def relative_asset(path): return '../../' + path.lstrip('/')
def price_text(it): return f"{fmt_num(it['p'])} ₽/м² с НДС" if it.get('p') else 'Цена по запросу'

# Stable, distinct human-readable URLs for products sharing a name.
for i,it in enumerate(items, 1):
    # The source stock file puts the country of manufacture in the brand column.
    # Keep that fact, but don't publish it as a manufacturer/brand.
    if it.get('b') == 'Казахстан':
        it['origin'] = 'Казахстан'
        it['b'] = ''
    if it['n'] == 'ВAITEREK BEJ': it['n'] = 'Baiterek Beige'
    if it['n'] == 'В60324': it['n'] = 'B60324'
    if it['n'] == 'Гермес Короичневый': it['n'] = 'Гермес Коричневый'
    suffix = slugify(f"{it['s']} {it.get('g','')}")
    it['url'] = f"products/{slugify(it['n'])}-{suffix}/"

# Product pages are static HTML so their key content exists before scripts run.
products_dir = root / 'products'
products_dir.mkdir(exist_ok=True)
for i,it in enumerate(items):
    name, brand, size = it['n'], it['b'], it['s']
    url = it['url']
    product_type = 'керамическая плитка' if it['t'] == 'tile' else 'керамогранит'
    grade_text = f", {it['g']}" if it.get('g') else ''
    dimensions = re.search(r'(\d+)\s*×\s*(\d+)', size)
    title_size = f"{dimensions.group(1)}×{dimensions.group(2)}" if dimensions else size
    title = f"Купить {name} {title_size}{grade_text} — {product_type}"
    if brand and brand.lower() not in name.lower() and len(title) + len(', '+brand) + len(' в СПб') <= 100:
        title += ', ' + brand
    title += ' в СПб'
    if len(title) > 100:
        title = title.replace('Купить ', '', 1)
    facts = [name, brand, size]
    if it.get('g'): facts.append(it['g'])
    desc = f"{name}" + (f" — {brand}" if brand else "") + f", {size}" + (f", {it['g']}" if it.get('g') else '') + (f". Страна производства: {it['origin']}." if it.get('origin') else '') + (f" Артикул {it['a']}." if it.get('a') else '') + f" В наличии {fmt_num(it['q'])} м². {price_text(it)}. Склад в Войскорово, доставка по Санкт-Петербургу и области."
    photo = image_path(it)
    if photo:
        fallback=it.get('img') if photo != it.get('img') else ''
        fallback_attr=f' data-fallback="{esc(relative_asset(fallback))}" onerror="this.onerror=null;this.src=this.dataset.fallback;"' if fallback else ''
        img = f'<img class="product-photo" src="{esc(relative_asset(photo))}"{fallback_attr} alt="{esc(name + (' — '+brand if brand else ''))}, {esc(size)}" loading="eager" fetchpriority="high" decoding="async">'
    else:
        img = '<div class="no-photo" role="img" aria-label="Фото товара пока не добавлено">Фото товара уточняйте у менеджера</div>'
    article = f'<dt>Артикул</dt><dd>{esc(it["a"])}</dd>' if it.get('a') else ''
    grade = f'<dt>Сорт</dt><dd>{esc(it["g"])}</dd>' if it.get('g') else ''
    price = f'<dt>Цена</dt><dd>{esc(price_text(it))}</dd>'
    callback_item = ', '.join(x for x in (name, size, brand, it.get('g'), f'артикул {it["a"]}' if it.get('a') else '') if x)
    compact_size = re.sub(r'\s*×\s*', '×', size)
    email_parts = [name, compact_size, brand, it.get('g', ''), f'артикул {it["a"]}' if it.get('a') else '']
    email_body = 'меня интересует: ' + ','.join(x for x in email_parts if x) + '.'
    email_href = 'mailto:novorom@mail.ru?subject=' + quote('Заявка на ' + name, safe='') + '&body=' + quote(email_body.replace('\n', '\r\n'), safe='')
    telegram_href = 'https://t.me/flyroman?text=' + quote(email_body, safe='')
    category_slug = 'keramicheskaya-plitka-spb' if it['t'] == 'tile' else 'keramogranit-spb'
    canonical_url = SITE_URL + '/' + url.lstrip('/')
    product_schema = {'@context':'https://schema.org','@type':'Product','name':name,'description':desc,'url':canonical_url}
    if brand: product_schema['brand'] = {'@type':'Brand','name':brand}
    if it.get('origin'): product_schema['countryOfOrigin'] = it['origin']
    if it.get('p'):
        product_schema['offers'] = {'@type':'Offer','url':canonical_url,'price':str(it['p']),'priceCurrency':'RUB','availability':'https://schema.org/InStock'}
    if it.get('a'): product_schema['sku'] = it['a']
    if photo: product_schema['image'] = SITE_URL + '/' + photo.lstrip('/')
    schema = json.dumps(product_schema, ensure_ascii=False, separators=(',',':')).replace('</','<\\/')
    breadcrumb_schema = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
        {'@type':'ListItem','position':1,'name':'Главная','item':SITE_URL+'/'},
        {'@type':'ListItem','position':2,'name':'Керамическая плитка' if it['t']=='tile' else 'Керамогранит','item':SITE_URL+'/catalog/'+('keramicheskaya-plitka-spb' if it['t']=='tile' else 'keramogranit-spb')+'/'},
        {'@type':'ListItem','position':3,'name':name,'item':canonical_url}]}
    breadcrumb_json = json.dumps(breadcrumb_schema, ensure_ascii=False, separators=(',',':')).replace('</','<\\/')
    related = []
    for j,other in enumerate(items):
        if j == i: continue
        if brand and other['b'] == brand: related.append(other)
        if len(related) == 4: break
    if len(related) < 4:
        for j,other in enumerate(items):
            if j == i or other in related: continue
            if other['k'] == it['k']:
                related.append(other)
            if len(related) == 4: break
    related_html=''.join(f'<li><a href="../{esc(other["url"].removeprefix("products/"))}">{esc(other["n"])} — {esc(other["s"])}</a></li>' for other in related)
    page=f'''<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(canonical_url)}">
<meta property="og:type" content="product"><meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">{f'<meta property="og:image" content="{esc(SITE_URL + "/" + photo.lstrip("/"))}">' if photo else ''}
<script type="application/ld+json">{schema}</script><script type="application/ld+json">{breadcrumb_json}</script>
<style>
:root{{--bg:#e9e8e4;--card:#f6f5f2;--ink:#1f2429;--mut:#5d646b;--line:#c6c5be;--tag:#f4c400}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}}.wrap{{max-width:920px;margin:auto;padding:0 18px}}header{{border-bottom:1px solid var(--line)}}header .wrap{{min-height:60px;display:flex;align-items:center;justify-content:space-between;gap:16px}}.brand{{font-weight:800;font-size:1.2rem;text-decoration:none;color:var(--ink)}}a{{color:#174e75}}.crumb{{font-size:.9rem;color:var(--mut);margin:22px 0}}main{{padding-bottom:42px}}h1,h2{{font-family:"Arial Narrow",Arial,sans-serif;line-height:1.15}}h1{{font-size:clamp(1.8rem,5vw,2.8rem);margin:.3em 0}}h2{{font-size:1.4rem}}.grid{{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,.9fr);gap:28px;align-items:start}}.product-photo,.no-photo{{width:100%;aspect-ratio:1/1;object-fit:cover;border:1px solid var(--line);border-radius:10px;background:var(--card)}}.no-photo{{display:grid;place-items:center;color:var(--mut);text-align:center;padding:20px}}.panel{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:22px}}.facts{{display:grid;grid-template-columns:auto 1fr;gap:7px 14px;margin:16px 0 22px}}.facts dt{{color:var(--mut)}}.facts dd{{margin:0;font-weight:650}}.btn{{display:inline-block;padding:11px 18px;background:#1f2429;border-radius:6px;color:#fff;text-decoration:none;font-weight:700;margin:4px 8px 4px 0}}button.btn{{border:0;cursor:pointer;font:inherit}}.product-email{{display:block;text-align:center;margin:12px 0 0}}.stock{{color:#375f36}}.note{{color:var(--mut);font-size:.9rem}}dialog{{border:0;border-radius:12px;padding:0;max-width:440px;width:calc(100% - 24px);background:var(--card);color:var(--ink)}}dialog::backdrop{{background:rgba(20,24,28,.6)}}.dbody{{padding:18px 20px 20px}}.dbody h2{{margin:0 0 4px;font-size:1.3rem;line-height:1.2}}.x{{position:absolute;right:10px;top:10px;width:40px;height:40px;border:0;border-radius:50%;background:var(--card);font-size:1.4rem;cursor:pointer}}.f{{display:grid;gap:10px}}.qty{{display:block;margin:8px 0 0;font-weight:600}}.qty input{{display:block;width:100%;margin-top:6px;padding:10px 12px;border:1.5px solid var(--line);border-radius:6px;background:#fff;font-size:1rem;color:var(--ink)}}.hint{{color:var(--mut);font-size:.85rem;margin:8px 0 0}}#callback-status{{min-height:1.3em;color:#9b1c1c}}[hidden]{{display:none!important}}footer{{padding:22px 0 36px;color:var(--mut);font-size:.9rem;border-top:1px solid var(--line)}}@media(max-width:680px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class="wrap"><a class="brand" href="../../index.html">ТФ Керамика</a></div></header>
<main class="wrap"><nav class="crumb" aria-label="Навигационная цепочка"><a href="../../index.html">Все товары</a> › <a href="../../catalog/{category_slug}/index.html">{esc('Керамическая плитка' if it['t']=='tile' else 'Керамогранит')}</a> › {esc(name)}</nav>
<h1>{esc(name)}</h1><div class="grid"><div>{img}<a class="btn product-email" href="{esc(email_href)}">Написать заявку на электронную почту</a></div><section class="panel">{f'<p><strong>{esc(brand)}</strong></p>' if brand else ''}<dl class="facts"><dt>Размер</dt><dd>{esc(size)}</dd>{grade}{article}{'<dt>Страна производства</dt><dd>'+esc(it['origin'])+'</dd>' if it.get('origin') else ''}<dt>Наличие</dt><dd class="stock">{fmt_num(it['q'])} м²</dd>{price}</dl>
<p class="note">Остаток указан по данным на 1 октября 2026 года. Перед заказом уточните наличие и цену у менеджера.</p><button class="btn" id="order-call" type="button" data-item="{esc(callback_item)}" data-request="{esc(email_body)}">Заказать звонок</button><a class="btn" href="{esc(telegram_href)}" target="_blank" rel="noopener">Написать в Telegram</a>
<p>Поможем рассчитать количество плитки для объекта, проверить остаток и согласовать самовывоз или доставку в Санкт-Петербурге и Ленинградской области.</p></section></div>
<section><h2>Другие товары</h2><ul>{related_html}</ul></section>
</main><footer><div class="wrap"><p>ТФ Керамика · Склад: Ленинградская область, Тосненский район, посёлок Войскорово, 14В</p><p>Пн–Пт, 09:00–18:00 · <a href="mailto:novorom@mail.ru">Email: novorom@mail.ru</a> · <a href="../../index.html">В каталог</a></p></div></footer>
<dialog id="callback-dialog" aria-labelledby="callback-title"><button class="x" id="callback-close" aria-label="Закрыть">×</button><div class="dbody"><h2 id="callback-title">Заказать звонок</h2><p class="note">Оставьте номер, перезвоним в рабочее время: Пн–Пт, с 09:00 до 18:00.</p><p class="note" id="callback-item">{esc(email_body)}</p><form id="callback-form" class="f" novalidate><label class="qty">Телефон<input id="callback-phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="+7 900 000-00-00" required></label><label class="qty">Имя (по желанию)<input id="callback-name" type="text" autocomplete="name"></label><input id="callback-honey" type="text" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px"><button class="btn" id="callback-send" type="submit">Перезвоните мне</button><p class="hint" id="callback-status" aria-live="polite"></p><p class="hint">Нажимая кнопку, вы соглашаетесь на обработку персональных данных для связи с вами.</p></form><p id="callback-success" hidden><strong>Спасибо! Заявка принята.</strong> Перезвоним в рабочее время.</p></div></dialog>
<script src="../../js/product-callback.js" defer></script>
</body></html>'''
    folder=products_dir / url.removeprefix('products/').strip('/')
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'index.html').write_text(page)

# Search landing pages make the two main product categories directly discoverable.
categories = [
    ('tile', 'keramicheskaya-plitka-spb', 'Керамическая плитка в СПб — каталог и наличие со склада | ТФ Керамика',
     'Керамическая плитка в наличии в Санкт-Петербурге',
     'Каталог керамической плитки для строительных бригад и подрядчиков. Сравните размеры, сорт и артикулы, проверьте цену за м² с НДС. Склад в Войскорово, самовывоз и доставка по Санкт-Петербургу и Ленинградской области.'),
    ('gres', 'keramogranit-spb', 'Керамогранит в СПб — каталог и наличие со склада | ТФ Керамика',
     'Керамогранит в наличии в Санкт-Петербурге',
     'Каталог керамогранита для строительных объектов. Сравните форматы, сорт и артикулы, проверьте цену за м² с НДС. Склад в Войскорово, самовывоз и доставка по Санкт-Петербургу и Ленинградской области.'),
]
for kind,slug,title,h1,intro in categories:
    group=[it for it in items if it['t']==kind]
    format_counts={}
    for item in group: format_counts[item['k']]=format_counts.get(item['k'],0)+1
    formats=', '.join(sorted(format_counts,key=lambda size:(-format_counts[size],size)))
    category_url = f'{SITE_URL}/catalog/{slug}/'
    category_breadcrumb = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
        {'@type':'ListItem','position':1,'name':'Главная','item':SITE_URL+'/'},
        {'@type':'ListItem','position':2,'name':h1,'item':category_url}]}
    category_breadcrumb_json = json.dumps(category_breadcrumb, ensure_ascii=False, separators=(',',':')).replace('</','<\\/')
    cards=[]
    for it in group:
        photo=image_path(it)
        image=f'<img src="../../{esc(photo)}" alt="{esc(it["n"])}" loading="lazy" decoding="async">' if photo else '<span class="no-photo">Фото уточняйте</span>'
        details=', '.join(x for x in (it['s'],it.get('b'),('производство '+it['origin']) if it.get('origin') else '',it.get('g')) if x)
        article=f'<span>Артикул: {esc(it["a"])}</span>' if it.get('a') else ''
        price=price_text(it).replace(' с НДС','')
        price_class='price' if it.get('p') else 'price ask'
        cards.append(f'<a class="item" href="../../{esc(it["url"])}"><span class="thumb">{image}</span><span class="info"><strong>{esc(it["n"])}</strong><span>{esc(details)}</span><span>В наличии {fmt_num(it["q"])} м²</span>{article}</span><span class="{price_class}">{esc(price)}</span></a>')
    cat_page=f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(intro)}"><link rel="canonical" href="{esc(category_url)}"><meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(intro)}">
<script type="application/ld+json">{category_breadcrumb_json}</script>
<style>:root{{--bg:#e9e8e4;--card:#f6f5f2;--ink:#1f2429;--mut:#5d646b;--line:#c6c5be;--tag:#f4c400}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}}.wrap{{max-width:960px;margin:auto;padding:0 18px}}header{{border-bottom:1px solid var(--line)}}header .wrap{{min-height:60px;display:flex;align-items:center;justify-content:space-between;gap:14px}}header a{{color:var(--ink)}}.brand{{font-weight:800;font-size:1.2rem;text-decoration:none}}main{{padding-bottom:38px}}.crumb{{margin:20px 0;color:var(--mut);font-size:.9rem}}h1,h2{{font-family:"Arial Narrow",Arial,sans-serif;line-height:1.15}}h1{{font-size:clamp(2rem,5vw,3rem);margin:.3em 0}}.intro{{max-width:760px;color:var(--mut)}}.summary{{font-weight:700;margin:24px 0 12px}}.list{{display:grid;gap:8px}}.item{{display:grid;grid-template-columns:64px minmax(0,1fr) auto;align-items:center;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;text-decoration:none;color:var(--ink)}}.item:hover,.item:focus-visible{{border-color:var(--ink);outline:2px solid var(--ink);outline-offset:1px}}.thumb{{width:64px;height:64px;border:1px solid var(--line);border-radius:5px;overflow:hidden;background:#ddd}}.thumb img{{width:100%;height:100%;display:block;object-fit:cover}}.no-photo{{display:grid;place-items:center;height:100%;font-size:.7rem;color:var(--mut);text-align:center}}.info{{display:grid;gap:2px}}.info>span{{font-size:.9rem;color:var(--mut)}}.price{{background:var(--tag);padding:5px 10px;font-weight:800;white-space:nowrap}}.ask{{background:transparent;border:1px dashed var(--line);color:var(--mut);font-size:.9rem}}.cta{{margin:28px 0;padding:18px;background:var(--ink);color:#fff;border-radius:9px}}.cta a{{color:#fff}}footer{{padding:20px 0 32px;color:var(--mut);border-top:1px solid var(--line);font-size:.9rem}}@media(max-width:520px){{.item{{grid-template-columns:52px minmax(0,1fr);gap:10px;padding:9px}}.thumb{{width:52px;height:52px}}.price{{grid-column:2;justify-self:start}}}}</style></head>
<body><header><div class="wrap"><a class="brand" href="../../index.html">ТФ Керамика</a><a href="tel:+79052050900">+7 905 205-09-00</a></div></header>
<main class="wrap"><nav class="crumb"><a href="../../index.html">Каталог товаров</a> › {esc('Керамическая плитка' if kind=='tile' else 'Керамогранит')}</nav>
<h1>{esc(h1)}</h1><p class="intro">{esc(intro)}</p><section><h2>Форматы и характеристики</h2><p>В подборке есть форматы: {esc(formats)} мм. На странице каждой позиции указаны размер, сорт и артикул, если они есть в исходных данных, а также остаток и цена или отметка «Цена по запросу». Перед оплатой уточните наличие у менеджера.</p></section><p class="summary">В каталоге {len(group)} позиций · обновлено 1 октября 2026 года · остаток от 30 м²</p>
<div class="list">{''.join(cards)}</div><section class="cta"><h2>Нужен расчёт для объекта?</h2><p>Сообщите артикул или название и количество. Поможем уточнить актуальный остаток и цену, подготовить счёт, согласовать самовывоз или доставку.</p><a href="tel:+79052050900">Позвонить: +7 905 205-09-00</a></section>
</main><footer><div class="wrap">Склад: Ленинградская область, Тосненский район, посёлок Войскорово, 14В · Пн–Пт, 09:00–18:00 · <a href="../../index.html">Все товары</a></div></footer></body></html>'''
    cat_dir=root/'catalog'/slug
    cat_dir.mkdir(parents=True,exist_ok=True)
    (cat_dir/'index.html').write_text(cat_page)

# Keep product URLs embedded in the data for JS-created cards.
s = re.sub(r'const ITEMS=(\[.*?\]);\n', 'const ITEMS='+json.dumps(items,ensure_ascii=False,separators=(',',':'))+';\n', s, count=1)
s = s.replace('placeholder="Название или размер" aria-label="Поиск по названию или размеру"','placeholder="Название, размер или артикул" aria-label="Поиск по названию, размеру или артикулу"')
s = re.sub(r'(?m)^\.row\{display:grid;grid-template-columns:64px 1fr auto;(?:text-decoration:none;)+', '.row{display:grid;grid-template-columns:76px minmax(0,1fr) auto;text-decoration:none;', s)
s = s.replace("'<button class=\"row\" data-i=\"'+i+'\">", "'<a class=\"row\" href=\"'+it.url+'\" data-i=\"'+i+'\">")
s = s.replace("</button>').join(''", "</a>').join(''")
# Product cards are ordinary links: the whole row leads to the static detail page.
old_handler = """$('#list').onclick=e=>{const r=e.target.closest('.row');if(!r)return;const it=ITEMS[+r.dataset.i];if(it.img&&e.target.closest('.sw')){e.preventDefault();openLb(it)}};"""
s = s.replace(old_handler, '')
s = s.replace("'+k+'</a>'", "'+k+'</button>'")
s = s.replace('Нажмите на позицию, чтобы открыть карточку. Цены за м², с НДС.', 'Откройте товар, чтобы посмотреть фото и характеристики. Цены за м², с НДС.')
# Render all product links in the original HTML, before JavaScript runs, so crawlers can discover every URL.
def card(it,i):
    photo=image_path(it)
    sw=f'<div class="sw"><img src="{esc(photo)}" alt="{esc(it["n"])}" loading="lazy" decoding="async"></div>' if photo else '<div class="sw" aria-hidden="true"></div>'
    price_html=f'{fmt_num(it["p"])} <small>₽/м²</small>' if it.get('p') else 'Цена по запросу'
    sub=', '.join(x for x in (it['s'],it['b'],('производство '+it['origin']) if it.get('origin') else '',it.get('g')) if x)
    article=f'<div class="sub">Артикул: {esc(it["a"])}</div>' if it.get('a') else ''
    return f'<a class="row" data-i="{i}" href="{esc(it["url"])}">{sw}<div><div class="nm">{esc(it["n"])}</div><div class="sub">{esc(sub)}</div><div class="sub">В наличии {fmt_num(it["q"])} м²</div>{article}</div><div class="price{"" if it.get("p") else " ask"}">{price_html}</div></a>'
static='\n'.join(card(it,i) for i,it in enumerate(items))
s=re.sub(r'(<div class="list" id="list">).*?(</div>\s*<p style="text-align:center">)',lambda m:m.group(1)+static+m.group(2),s,count=1,flags=re.S)
s=s.replace('Найдено: 192 позиции','Найдено: 191 позиция')
s = s.replace('Цены действуют до 31 октября 2026 года или до окончания остатков.', 'Цены и остатки обновлены 1 октября 2026 года; перед заказом уточните актуальное наличие и стоимость.')
s = s.replace('Да, рассчёт количества бесплатный.', 'Да, расчёт количества бесплатный.')
s = s.replace('ВAITEREK BEJ', 'Baiterek Beige').replace('В60324', 'B60324').replace('Гермес Короичневый', 'Гермес Коричневый')
s = re.sub(r'<noscript><section>.*?</section></noscript>', '', s, flags=re.S)
s = s.replace('href="catalog/keramicheskaya-plitka-spb/index.html"', 'href="catalog/keramicheskaya-plitka-spb/"')
s = s.replace('href="catalog/keramogranit-spb/index.html"', 'href="catalog/keramogranit-spb/"')
faq_anchor = '<div><dt>Поможете рассчитать количество плитки для объекта?</dt>'
faq_addition = '<div><dt>Что означают обозначения сорта и ПК?</dt><dd>Обозначения в каталоге перенесены из данных поставщиков. Их значение и критерии могут различаться у производителей, поэтому для конкретной партии запросите у менеджера документы и характеристики.</dd></div>\n'
if 'Что означают обозначения сорта и ПК?' not in s:
    s = s.replace(faq_anchor, faq_addition + faq_anchor)
canonical_home = SITE_URL + '/'
home_graph = {'@context':'https://schema.org','@type':'Store','name':'ООО «ТФ Керамика»','url':canonical_home,'email':'novorom@mail.ru',
    'address':{'@type':'PostalAddress','streetAddress':'посёлок Войскорово, 14В','addressLocality':'Войскорово','addressRegion':'Ленинградская область','addressCountry':'RU'},
    'openingHoursSpecification':[{'@type':'OpeningHoursSpecification','dayOfWeek':['Monday','Tuesday','Wednesday','Thursday','Friday'],'opens':'09:00','closes':'18:00'}]}
home_graph_json = json.dumps(home_graph, ensure_ascii=False, separators=(',',':')).replace('</','<\\/')
if 'rel="canonical" href="'+canonical_home+'"' not in s:
    s = s.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', '<meta name="viewport" content="width=device-width, initial-scale=1">\n<link rel="canonical" href="'+canonical_home+'">\n<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:image" content="'+SITE_URL+'/img/photos/003.jpg"><meta property="og:image:alt" content="Плитка Bianco Белый из каталога ТФ Керамика"><meta name="twitter:card" content="summary_large_image">\n<script type="application/ld+json">'+home_graph_json+'</script>')
home_schema_tag = '<script type="application/ld+json">'+home_graph_json+'</script>'
s = re.sub(r'<script type="application/ld\+json">.*?"@type":"Store".*?</script>', '', s, flags=re.S)
s = s.replace('<link rel="canonical" href="'+canonical_home+'">', '<link rel="canonical" href="'+canonical_home+'">\n'+home_schema_tag, 1)
dedupe = [
    '<link rel="canonical" href="'+canonical_home+'">',
    '<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="ТФ Керамика"><meta property="og:image" content="'+SITE_URL+'/img/photos/003.jpg"><meta property="og:image:alt" content="Плитка Bianco Белый из каталога ТФ Керамика"><meta name="twitter:card" content="summary_large_image">',
    home_schema_tag,
    faq_addition.rstrip('\n')]
for fragment in dedupe:
    first = s.find(fragment)
    if first >= 0:
        s = s[:first+len(fragment)] + s[first+len(fragment):].replace(fragment, '')
index_path.write_text(s)

# Use directory URLs consistently, and keep old index.html URLs as permanent redirects.
for page_path in root.rglob('*.html'):
    page = page_path.read_text()
    page_path.write_text(page.replace('index.html', ''))

(root/'vercel.json').write_text(json.dumps({'$schema':'https://openapi.vercel.sh/vercel.json','trailingSlash':True,'redirects':json.loads((Path(__file__).resolve().parent/'legacy-urls.json').read_text())},ensure_ascii=False,indent=2)+'\n')

sitemap_urls = [canonical_home, SITE_URL+'/catalog/keramicheskaya-plitka-spb/', SITE_URL+'/catalog/keramogranit-spb/'] + [SITE_URL+'/'+it['url'].lstrip('/') for it in items]
sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{html.escape(url)}</loc><lastmod>2026-10-01</lastmod></url>\n' for url in sitemap_urls) + '</urlset>\n'
(root/'sitemap.xml').write_text(sitemap)
(root/'robots.txt').write_text('User-agent: Yandex\nAllow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n\nUser-agent: *\nAllow: /\n\nSitemap: '+SITE_URL+'/sitemap.xml\n')

# Remove obsolete generated product folders only after redirect targets are recorded.
valid_product_dirs = {url.removeprefix('products/').strip('/') for url in (it['url'] for it in items)}
for page_path in products_dir.glob('*/index.html'):
    if page_path.parent.name not in valid_product_dirs:
        shutil.rmtree(page_path.parent)
print(f'Generated {len(items)} static product pages and crawlable product links.')
print(f'Article codes on pages: {sum(bool(it.get("a")) for it in items)} of {len(items)}.')
