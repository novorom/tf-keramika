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
    else if (/^https?:\/\/(?:www\.)?yandex\.(?:ru|com)\/maps\/org\/iltima\//i.test(href)) reachGoal('yandex_maps_click');
    else if (/^https?:\/\/www\.avito\.ru\/user\/0f9d6bc281bab39ce62a9b63316d1548\//i.test(href)) reachGoal('avito_profile_click');
  });

  document.addEventListener('click', event => {
    const button = event.target.closest('#hcall, #ccall, #order-call');
    if (button) reachGoal('callback_form_open');
  });

  window.iltimaAnalytics = { reachGoal };
})();
