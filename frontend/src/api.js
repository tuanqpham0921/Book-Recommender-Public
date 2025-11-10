const BASE_URL = import.meta.env.VITE_API_URL

/**
 * Wrapper for fetch with timeout and abort signal handling.
 * 
 * @param {string} url - Target URL
 * @param {Object} options - Fetch options
 * @param {number} timeoutMs - Request timeout in milliseconds
 * @returns {Promise<Response>} Fetch response
 */
async function fetch_api(url, options = {}, timeoutMs = 120000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const userSignal = options.signal;
  let combinedSignal = controller.signal;

  if (userSignal) {
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

/**
 * Check backend health status.
 * @returns {Promise<boolean>} True if backend is healthy
 */
async function backEndHealthReady() {
  try {
    const res = await fetch_api(BASE_URL + '/health', { method: 'POST' });
    const data = await res.json();
    return data.status === 'ok';
  } catch (e) {
    return false;
  }
}

/**
 * Create a new chat session.
 * @returns {Promise<Object>} Session data with session_id
 */
async function createSession() {
  const res = await fetch_api(BASE_URL + '/session/new', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

/**
 * Send a chat message and get streaming response.
 * 
 * @param {string} sessionId - Session identifier
 * @param {string} message - User message
 * @param {AbortSignal} abortSignal - Signal for cancelling request
 * @param {number} timeoutMs - Request timeout
 * @returns {Promise<ReadableStream>} Stream of SSE events
 */
async function sendChatMessage(sessionId, message, abortSignal = null, timeoutMs = 120000) {
  const res = await fetch_api(
    BASE_URL + `/session/${sessionId}/message`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal: abortSignal
    },
    timeoutMs
  );
  return res.body;
}

/**
 * Get recommended books for a session.
 * 
 * @param {string} sessionId - Session identifier
 * @returns {Promise<Object>} Recommended books data
 */
async function getRecommendedBooks(sessionId) {
  const res = await fetch_api(BASE_URL + `/session/${sessionId}/recommended_books`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

/**
 * Get task plan diagram for a session.
 * 
 * @param {string} sessionId - Session identifier  
 * @returns {Promise<Object>} Diagram data
 */
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