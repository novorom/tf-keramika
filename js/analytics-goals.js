(() => {
  const counterId = 113474855;

  function reachGoal(name) {
    if (typeof window.ym === 'function') {
      window.ym(counterId, 'reachGoal', name);
    }
  }

  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link) return;

    const href = link.getAttribute('href') || '';
    if (/^tel:/i.test(href)) reachGoal('phone_click');
    else if (/^mailto:/i.test(href)) reachGoal('email_click');
    else if (/^https?:\/\/(?:www\.)?t\.me\//i.test(href)) reachGoal('telegram_click');
  });

  window.iltimaAnalytics = { reachGoal };
})();
