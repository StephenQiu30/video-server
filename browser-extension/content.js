const MESSAGE_TYPE = 'framefetch:provider-sync';

window.addEventListener('message', (event) => {
  if (event.source !== window || event.origin !== window.location.origin)
    return;
  const message = event.data;
  if (!message || message.type !== MESSAGE_TYPE) return;
  if (
    typeof message.provider !== 'string' ||
    typeof message.requestId !== 'string'
  ) return;

  chrome.runtime.sendMessage(
    { type: 'sync', provider: message.provider },
    (response) => {
      const error = chrome.runtime.lastError;
      window.postMessage(
        {
          type: `${MESSAGE_TYPE}:result`,
          requestId: message.requestId,
          provider: message.provider,
          ok: !error && response?.ok === true,
          revision: response?.revision ?? null,
          error: error?.message ?? response?.error ?? null,
        },
        window.location.origin,
      );
    },
  );
});
