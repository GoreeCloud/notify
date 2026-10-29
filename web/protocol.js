/** ntfy browser protocol boundary: no GUI or persistence dependencies. */
export const MAX_EVENT_LINE = 65536;
export const MAX_BODY = 8192;
const TOPIC = /^[A-Za-z0-9_-]{1,64}$/;

export function validateTopic(value) {
  const topic = String(value ?? "").trim();
  if (!TOPIC.test(topic)) throw new Error("Topics must use 1–64 letters, numbers, _ or -");
  return topic;
}
export function normalizeEndpoint(value) {
  const raw = String(value ?? "").trim();
  if (!raw || /[\r\n\\]/.test(raw)) throw new Error("Enter a valid ntfy endpoint");
  if (raw.startsWith("/") && !raw.startsWith("//")) {
    if (!/^\/[A-Za-z0-9/_-]*$/.test(raw) || raw.includes("..")) throw new Error("Invalid endpoint path");
    return raw.replace(/\/$/, "") || "/";
  }
  let url;
  try { url = new URL(raw); } catch { throw new Error("Enter an HTTPS URL or same-origin path"); }
  if (!["https:", "http:"].includes(url.protocol) || !url.hostname || url.username || url.password
      || url.search || url.hash) throw new Error("Endpoint must not contain credentials, query or fragment");
  if (url.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))
    throw new Error("Remote endpoints require HTTPS");
  return url.href.replace(/\/$/, "");
}
export function topicUrl(endpoint, topic, mode = "") {
  if (mode && mode !== "json") throw new Error("Unsupported subscription mode");
  return normalizeEndpoint(endpoint).replace(/\/$/, "") + "/" + validateTopic(topic) + (mode ? "/json" : "");
}
export function parseEvent(input) {
  let data;
  try { data = typeof input === "string" ? JSON.parse(input) : input; } catch { return null; }
  if (!data || typeof data !== "object" || Array.isArray(data) || data.event !== "message") return null;
  if (typeof data.id !== "string" || data.id.length > 128 || typeof data.topic !== "string"
    || !TOPIC.test(data.topic) || typeof data.message !== "string" || data.message.length > MAX_EVENT_LINE) return null;
  const priority = data.priority == null ? 3 : Number(data.priority);
  const time = data.time == null ? 0 : Number(data.time);
  if (!Number.isInteger(priority) || priority < 1 || priority > 5
    || !Number.isSafeInteger(time) || time < 0) return null;
  return {
    id: data.id, topic: data.topic, message: data.message,
    title: typeof data.title === "string" ? data.title.slice(0, 240) : "",
    priority, time,
    tags: Array.isArray(data.tags) ? data.tags.filter(x => typeof x === "string").slice(0, 12).map(x => x.slice(0, 40)) : [],
  };
}
function headers(token = "", extra = {}) {
  if (/[\r\n]/.test(token)) throw new Error("Invalid token");
  return { Accept: "application/x-ndjson", ...(token ? { Authorization: "Bearer " + token } : {}), ...extra };
}
export function makePublishRequest(endpoint, topic, message, options = {}, token = "") {
  if (typeof message !== "string" || !message.trim() || new TextEncoder().encode(message).length > MAX_BODY)
    throw new Error("Message must contain 1–8192 UTF-8 bytes");
  const priority = Number(options.priority ?? 3);
  if (!Number.isInteger(priority) || priority < 1 || priority > 5) throw new Error("Priority must be 1–5");
  const title = String(options.title ?? "").trim(), tags = String(options.tags ?? "").trim();
  if (title.length > 160 || tags.length > 120 || /[\r\n]/.test(title + tags)) throw new Error("Invalid title or tags");
  return {
    url: topicUrl(endpoint, topic),
    init: {
      method: "POST", redirect: "error",
      headers: headers(token, {
        "Content-Type": "text/plain; charset=utf-8", Priority: String(priority),
        ...(title ? { Title: title } : {}), ...(tags ? { Tags: tags } : {}),
      }),
      body: message,
    },
  };
}
/** Never reuse a bearer token when switching to a different server. */
export function chooseToken(previousEndpoint, nextEndpoint, currentToken, enteredToken, forget = false) {
  if (forget) return "";
  if (enteredToken) {
    if (/[\r\n]/.test(enteredToken)) throw new Error("Invalid token");
    return enteredToken;
  }
  return previousEndpoint === nextEndpoint ? currentToken : "";
}
export function humanError(error) {
  if (error?.name === "AbortError") return "Disconnected";
  if (error instanceof TypeError) return "Network unavailable or cross-origin access blocked";
  return error instanceof Error ? error.message : "Request failed";
}
async function checkResponse(response) {
  if (response.type === "opaqueredirect" || response.redirected)
    throw new Error("Redirect blocked: server configuration requires review");
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) throw new Error("Access denied. Check token and permissions");
    if (response.status === 429) throw new Error("Rate limited by ntfy server");
    throw new Error("ntfy returned HTTP " + response.status);
  }
}
export async function publish(fetcher, endpoint, topic, message, options = {}, token = "", signal) {
  const { url, init } = makePublishRequest(endpoint, topic, message, options, token);
  await checkResponse(await fetcher(url, { ...init, signal }));
}
export async function health(fetcher, endpoint, token = "", signal) {
  const url = normalizeEndpoint(endpoint).replace(/\/$/, "") + "/v1/health";
  const response = await fetcher(url, { method: "GET", redirect: "error", headers: headers(token), signal });
  await checkResponse(response);
  const body = await response.text();
  if (body.length > 4096) throw new Error("Oversized health response");
  let payload;
  try { payload = JSON.parse(body); } catch { throw new Error("Invalid health response"); }
  if (typeof payload?.healthy !== "boolean") throw new Error("Unrecognized health response");
  return payload.healthy;
}
/** Reads NDJSON, accounting for partial UTF-8 chunks, keepalives and cancellation. */
export async function subscribeOnce(fetcher, { endpoint, topic, token = "", since = "10m", signal, onOpen, onMessage }) {
  if (!/^([A-Za-z0-9_-]{1,128}|[0-9]+[smhd])$/.test(since)) throw new Error("Invalid resume cursor");
  const url = topicUrl(endpoint, topic, "json") + "?since=" + encodeURIComponent(since);
  const response = await fetcher(url, {
    method: "GET", redirect: "error", cache: "no-store", headers: headers(token), signal,
  });
  await checkResponse(response);
  if (!response.body?.getReader) throw new Error("Streaming unsupported by this browser");
  onOpen?.();
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let pending = "";
  try {
    while (true) {
      if (signal?.aborted) return;
      const { done, value } = await reader.read();
      if (done) break;
      pending += decoder.decode(value, { stream: true });
      let end;
      while ((end = pending.indexOf("\n")) !== -1) {
        const line = pending.slice(0, end).trim();
        pending = pending.slice(end + 1);
        if (line.length > MAX_EVENT_LINE) throw new Error("Oversized notification");
        if (!line) continue;
        const msg = parseEvent(line);
        if (msg && msg.topic === topic) onMessage?.(msg);
      }
      if (pending.length > MAX_EVENT_LINE) throw new Error("Oversized notification");
    }
    pending += decoder.decode();
    if (pending.trim()) {
      if (pending.length > MAX_EVENT_LINE) throw new Error("Oversized notification");
      const msg = parseEvent(pending.trim());
      if (msg && msg.topic === topic) onMessage?.(msg);
    }
  } finally { reader.releaseLock(); }
}
