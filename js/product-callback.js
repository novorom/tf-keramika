(() => {
  const dialog = document.querySelector('#callback-dialog');
  const trigger = document.querySelector('#order-call');
  const form = document.querySelector('#callback-form');
  if (!dialog || !trigger || !form) return;

  const phone = document.querySelector('#callback-phone');
  const name = document.querySelector('#callback-name');
  const status = document.querySelector('#callback-status');
  const success = document.querySelector('#callback-success');
  const honeypot = document.querySelector('#callback-honey');
  const item = trigger.dataset.item;
  const telegram = 'https://t.me/flyroman';
  const accessKey = '15b32313-a149-4439-8169-15ec9f6669fe';

  trigger.addEventListener('click', () => {
    status.textContent = '';
    form.hidden = false;
    success.hidden = true;
    dialog.showModal();
    window.setTimeout(() => phone.focus(), 50);
  });

  document.querySelector('#callback-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const number = phone.value.trim();
    if (number.replace(/\D/g, '').length < 10) {
      status.textContent = 'Проверьте номер телефона';
      return;
    }
    if (honeypot.value) return;

    const customer = name.value.trim();
    const message = trigger.dataset.request || `меня интересует: ${item}.`;
    const fallback = `${telegram}?text=${encodeURIComponent(`Заказ звонка: ${number}${customer ? ` (${customer})` : ''}. ${message}`)}`;
    const send = document.querySelector('#callback-send');
    send.disabled = true;
    status.textContent = 'Отправляем…';
    try {
      const response = await fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          access_key: accessKey,
          subject: 'Заказ звонка: ТФ Керамика',
          from_name: 'Сайт ТФ Керамика',
          name: customer || 'Не указано',
          phone: number,
          message
        })
      });
      const result = await response.json();
      if (!result.success) throw new Error('Request was not accepted');
      form.hidden = true;
      success.hidden = false;
      form.reset();
    } catch {
      status.innerHTML = `Не удалось отправить. Напишите нам в <a href="${fallback}" target="_blank" rel="noopener">Telegram</a>.`;
    } finally {
      send.disabled = false;
    }
  });
})();
