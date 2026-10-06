import fs from 'node:fs';

const host = 'tfkeramika.ru';
const base = `https://${host}`;
const key = fs.readFileSync(new URL('../indexnow-key.txt', import.meta.url), 'utf8').trim();
const changed = fs.readFileSync(0, 'utf8').split(/\r?\n/).filter(Boolean);
const urls = [...new Set(changed.flatMap((file) => {
  if (file === 'index.html') return [`${base}/`];
  if (!file.endsWith('/index.html')) return [];
  const route = file.slice(0, -'index.html'.length);
  if (!/^(products|catalog|brands|formats)\//.test(route)) return [];
  return [`${base}/${route}`];
}))];

if (!urls.length) {
  console.log('No changed HTML routes to submit.');
  process.exit(0);
}

const response = await fetch('https://yandex.com/indexnow', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
  body: JSON.stringify({
    host,
    key,
    keyLocation: `${base}/indexnow-key.txt`,
    urlList: urls,
  }),
});

if (!response.ok) {
  const detail = await response.text();
  throw new Error(`IndexNow returned ${response.status}: ${detail}`);
}
console.log(`Submitted ${urls.length} changed page URLs to IndexNow.`);
