const languageButtons = document.querySelectorAll('[data-lang]');
const translatedNodes = document.querySelectorAll('[data-zh][data-en]');

function setLanguage(language) {
  document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  document.title = language === 'zh' ? '许颂毓 | 多模态大模型研究' : 'Songyu Xu | Multimodal Model Research';

  translatedNodes.forEach((node) => {
    node.textContent = node.dataset[language];
  });

  languageButtons.forEach((button) => {
    const active = button.dataset.lang === language;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });

  localStorage.setItem('xsy-language', language);
}

languageButtons.forEach((button) => {
  button.addEventListener('click', () => setLanguage(button.dataset.lang));
});

document.getElementById('year').textContent = new Date().getFullYear();
setLanguage(localStorage.getItem('xsy-language') === 'en' ? 'en' : 'zh');
