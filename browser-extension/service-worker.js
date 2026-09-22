const NATIVE_HOST = 'com.framefetch.provider.browser';
const PROVIDER_DOMAINS = {
  youtube: ['youtube.com', 'youtube-nocookie.com'],
  douyin: ['douyin.com', 'iesdouyin.com'],
  xiaohongshu: ['xiaohongshu.com'],
  x: ['x.com', 'twitter.com'],
  instagram: ['instagram.com'],
  facebook: ['facebook.com'],
  reddit: ['reddit.com'],
  pinterest: ['pinterest.com'],
};

const providerSyncs = new Map();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (
    message?.type !== 'sync' ||
    typeof message.provider !== 'string' ||
    !/^[0-9a-f]{32}$/.test(message.transactionId)
  ) {
    return false;
  }
  scheduleSync(message.provider).then(
    (result) => sendResponse(result),
    (error) => sendResponse({
      ok: false,
      error: error instanceof Error ? error.message : 'browser_sync_failed',
    }),
  );
  return true;
});

function scheduleSync(provider) {
  const previous = providerSyncs.get(provider) ?? Promise.resolve();
  const current = previous.catch(() => undefined).then(() => syncProvider(provider));
  providerSyncs.set(provider, current);
  return current.finally(() => {
    if (providerSyncs.get(provider) === current) providerSyncs.delete(provider);
  });
}

async function syncProvider(provider) {
  const domains = PROVIDER_DOMAINS[provider];
  if (!domains) return;
  const revision = crypto.randomUUID();
  const cookies = new Map();
  for (const domain of domains) {
    const values = await chrome.cookies.getAll({ domain });
    for (const cookie of values) {
      if (!isAllowedDomain(cookie.domain, domains)) continue;
      const key = `${cookie.domain}\t${cookie.path}\t${cookie.name}`;
      cookies.set(key, {
        domain: cookie.domain,
        name: cookie.name,
        value: cookie.value,
        path: cookie.path,
        secure: cookie.secure,
        httpOnly: cookie.httpOnly,
        hostOnly: cookie.hostOnly,
        storeId: cookie.storeId,
        expirationDate: cookie.expirationDate ?? null,
      });
    }
  }
  const response = await sendNative({
    type: 'sync',
      provider,
      transaction_id: message.transactionId,
      revision,
    cookies: [...cookies.values()],
  });
  if (response.provider !== provider || response.revision !== revision) {
    throw new Error('browser bridge returned a stale acknowledgement');
  }
  return response;
}

function sendNative(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(NATIVE_HOST, message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
      } else if (response?.ok) {
        resolve(response);
      } else {
        reject(new Error(response?.error || 'browser bridge rejected'));
      }
    });
  });
}

function isAllowedDomain(domain, domains) {
  const normalized = domain.replace(/^\./, '').toLowerCase();
  return domains.some(
    (item) => normalized === item || normalized.endsWith(`.${item}`),
  );
}
