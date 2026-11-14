const languageButtons = document.querySelectorAll('[data-lang]');
const translatedNodes = document.querySelectorAll('[data-zh][data-en]');
let currentLanguage = 'zh';
let scholarData = null;

function normalizeTitle(title) {
  return title.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
}

function renderScholar() {
  if (!scholarData || scholarData.status !== 'ok') return;
  const total = scholarData.total_citations;
  const updated = new Date(scholarData.updated_at);
  if (!Number.isInteger(total) || total < 0 || Number.isNaN(updated.getTime())) return;
  const zh = currentLanguage === 'zh';
  const summary = document.querySelector('.scholar-summary');
  summary.querySelector('.scholar-total').textContent = zh ? `Google Scholar · 总引用 ${total}` : `${total} citations on Google Scholar`;
  const date = new Intl.DateTimeFormat(zh ? 'zh-CN' : 'en-GB', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'Asia/Shanghai' }).format(updated);
  summary.querySelector('.scholar-updated').textContent = zh ? `更新于 ${date}` : `Updated ${date}`;
  summary.hidden = false;
  document.querySelectorAll('[data-paper-title]').forEach((row) => {
    const paper = (scholarData.papers || []).find((p) => normalizeTitle(p.title) === normalizeTitle(row.dataset.paperTitle));
    const link = row.querySelector('.paper-citations');
    if (!paper || !Number.isInteger(paper.citations) || paper.citations < 0) return;
    let url;
    try { url = new URL(paper.scholar_url); } catch { return; }
    if (url.protocol !== 'https:' || url.hostname !== 'scholar.google.com') return;
    link.href = url.href;
    link.textContent = zh ? `引用 ${paper.citations}` : `Cited by ${paper.citations}`;
    link.hidden = false;
  });
}

function setLanguage(language) {
  currentLanguage = language;
  document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  document.title = language === 'zh' ? '许颂毓 | Songyu Xu' : 'Songyu Xu | 许颂毓';
  translatedNodes.forEach((node) => { node.textContent = node.dataset[language]; });
  languageButtons.forEach((button) => {
    const active = button.dataset.lang === language;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  document.querySelector('nav').setAttribute('aria-label', language === 'zh' ? '页面导航' : 'Page sections');
  document.querySelectorAll('[data-figure]').forEach((button) => {
    const title = button.closest('.publication').dataset.paperTitle.split(':')[0];
    button.setAttribute('aria-label', language === 'zh' ? `查看 ${title} 配图` : `Enlarge ${title} figure`);
  });
  try { localStorage.setItem('xsy-language', language); } catch { /* Browsing also works without storage. */ }
  renderScholar();
}

languageButtons.forEach((button) => button.addEventListener('click', () => setLanguage(button.dataset.lang)));
document.getElementById('year').textContent = new Date().getFullYear();
let savedLanguage = 'zh';
try { savedLanguage = localStorage.getItem('xsy-language') === 'en' ? 'en' : 'zh'; } catch { /* Use Chinese by default. */ }
setLanguage(savedLanguage);

// Show the bundled snapshot promptly, then refresh from the latest daily commit.
async function loadScholar(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error('Scholar snapshot unavailable');
  const data = await response.json();
  if (data.status !== 'ok' || !Array.isArray(data.papers)) return;
  const timestamp = new Date(data.updated_at).getTime();
  if (!Number.isFinite(timestamp)) return;
  if (!scholarData || timestamp > new Date(scholarData.updated_at).getTime()) {
    scholarData = data;
    renderScholar();
  }
}
loadScholar('assets/scholar.json').catch(() => {});
if (location.hostname === 'notyourkev.github.io') {
  loadScholar('https://raw.githubusercontent.com/notyourkev/notyourkev.github.io/main/assets/scholar.json').catch(() => {});
}

const navLinks = [...document.querySelectorAll('nav a')];
const sections = navLinks.map((link) => document.querySelector(link.getAttribute('href')));
let scrollPending = false;
function updateNavigation() {
  const threshold = window.innerWidth <= 1180 ? 130 : 120;
  let active = sections[0];
  sections.forEach((section) => { if (section.getBoundingClientRect().top <= threshold) active = section; });
  if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 3) active = sections[sections.length - 1];
  navLinks.forEach((link) => {
    const selected = link.getAttribute('href') === `#${active.id}`;
    link.classList.toggle('active', selected);
    if (selected) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
  scrollPending = false;
}
window.addEventListener('scroll', () => {
  if (!scrollPending) { scrollPending = true; requestAnimationFrame(updateNavigation); }
}, { passive: true });
window.addEventListener('resize', updateNavigation);
updateNavigation();

const dialog = document.querySelector('.figure-dialog');
document.querySelectorAll('[data-figure]').forEach((button) => {
  button.addEventListener('click', () => {
    const image = button.querySelector('img');
    const preview = document.getElementById('figure-image');
    preview.src = image.src;
    preview.alt = image.alt;
    document.getElementById('figure-caption').textContent = button.closest('.publication').dataset.paperTitle;
    dialog.showModal();
  });
});
dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => {
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
});
