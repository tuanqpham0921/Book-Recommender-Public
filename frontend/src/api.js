const BASE_URL = import.meta.env.VITE_API_URL
// const BASE_URL = 'https://book-rec-api-286869228046.us-central1.run.app'


async function fetch_api(url, options = {}, timeoutMs = 120000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Combine timeout signal with user-provided signal
  const userSignal = options.signal;
  let combinedSignal = controller.signal;

  if (userSignal) {
    // Create a combined signal that aborts when either signal aborts
    const combinedController = new AbortController();
    combinedSignal = combinedController.signal;

    const abort = (reason) => combinedController.abort(reason);

    if (controller.signal.aborted || userSignal.aborted) {
      abort();
    } else {
      controller.signal.addEventListener('abort', () => abort('timeout'));
      userSignal.addEventListener('abort', () => abort('user_cancelled'));
    }
  }

  try {
    const res = await fetch(url, {
      ...options,
      signal: combinedSignal
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorData = res.headers.get('content-type')?.includes('application/json')
        ? await res.json()
        : { error: 'Request failed' };
      return Promise.reject({ status: res.status, data: errorData });
    }

    return res;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      return Promise.reject({ status: 408, data: { error: 'Request timeout or cancelled' } });
    }
    throw error;
  }
}


async function backEndHealthReady() {
  try {
    const res = await fetch_api(BASE_URL + '/health', { method: 'GET' });
    const data = await res.json();
    return data.status === 'ok';
  } catch (e) {
    return false;
  }
}

async function createSession() {
  const res = await fetch_api(BASE_URL + '/session/new', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

async function sendChatMessage(sessionId, message, abortSignal = null, timeoutMs = 120000) {
  const res = await fetch_api(
    BASE_URL + `/session/${sessionId}/message`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal: abortSignal // Pass abort signal to fetch_api
    },
    timeoutMs
  );
  return res.body;
}


async function getRecommendedBooks(sessionId) {
  const res = await fetch_api(BASE_URL + `/session/${sessionId}/recommended_books`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

// TODO: implment this, using sse stream for now
async function getTaskPlanDiagram(sessionId) {
  const res = await fetch_api(BASE_URL + `/diagram/${sessionId}/task_plan`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

export default {
  createSession, sendChatMessage, getRecommendedBooks, backEndHealthReady
};