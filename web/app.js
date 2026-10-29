/** GoreeCloud Notify — supplementary web client, not an OS-native replacement. */
import { validateTopic, normalizeEndpoint, subscribeOnce, publish, health, humanError, chooseToken } from "./protocol.js";
import { loadSettings, saveSettings, addTopic, removeTopic, createInbox, addMessage, filterMessages } from "./state.js";

const $ = id => document.getElementById(id);
const storage = (() => { try { return window.localStorage; } catch { return null; } })();
let settings = loadSettings(storage);
let token = ""; // Only in memory. Never save credentials or message bodies.
let healthStatus = "Not checked", healthDetail = "Run a read-only check", generation = 0, toastTimer;
const inboxes = new Map(), streams = new Map();
function inbox(topic) { if (!inboxes.has(topic)) inboxes.set(topic, createInbox()); return inboxes.get(topic); }
function persist() { try { saveSettings(storage, settings); } catch { toast("Local preferences could not be saved"); } }
function toast(message) {
  $("toast").textContent = message; $("toast").hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4200);
}
function setTheme() {
  const dark = settings.theme === "dark" || (settings.theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  $("theme-button").title = dark ? "Switch to light theme" : "Switch to dark theme";
}
function text(tag, className, value = "") {
  const el = document.createElement(tag); if (className) el.className = className;
  el.textContent = String(value); return el;
}
function viewTopic(topic) { settings.selected = topic; if (topic) inbox(topic).unread = 0; render(); }
function formatTime(seconds) {
  const date = new Date(seconds * 1000);
  return seconds && Number.isFinite(date.getTime()) ? date.toLocaleString([], {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
  }) : "Now";
}
function renderTopics() {
  const target = $("topics"); target.replaceChildren();
  $("all-topics").classList.toggle("active", settings.selected === null);
  for (const topic of settings.topics) {
    const row = text("div", "topic-list-item");
    const button = text("button", "topic-button");
    button.type = "button"; button.classList.toggle("active", settings.selected === topic);
    button.setAttribute("aria-current", settings.selected === topic ? "page" : "false");
    button.append(text("span", "topic-symbol", "#"), text("span", "topic-name", topic));
    if (inbox(topic).unread) button.append(text("span", "topic-count", inbox(topic).unread > 99 ? "99+" : inbox(topic).unread));
    button.addEventListener("click", () => viewTopic(topic));
    const remove = text("button", "remove-topic", "×"); remove.type = "button";
    remove.setAttribute("aria-label", "Unsubscribe from " + topic);
    remove.title = "Unsubscribe from " + topic;
    remove.addEventListener("click", () => {
      if (!confirm("Unsubscribe from #" + topic + "? This clears local session history, not server messages.")) return;
      removeTopic(settings, topic); streams.get(topic)?.abort(); streams.delete(topic); inboxes.delete(topic);
      persist(); render(); toast("Unsubscribed from #" + topic);
    });
    row.append(button, remove); target.append(row);
  }
}
function renderConnection() {
  const statuses = settings.topics.map(name => inbox(name).status);
  const online = statuses.filter(s => s === "Connected").length;
  const errors = statuses.some(s => s.startsWith("Error:"));
  $("connection-title").textContent = online ? online + " connected" : !settings.topics.length ? "No subscriptions"
    : errors ? "Connection issue" : "Connecting…";
  $("endpoint-name").textContent = settings.endpoint;
  $("connection-dot").className = "pulse-dot" + (online ? " online" : errors ? " error" : "");
}
function makeCard(note) {
  const article = text("article", "notification" + (note.priority === 5 ? " urgent" : ""));
  const icon = text("div", "message-avatar", note.priority === 5 ? "!" : "✦");
  icon.setAttribute("aria-hidden", "true");
  const body = text("div");
  const top = text("div", "notification-header");
  top.append(text("h3", "notification-title", note.title || "Notification"));
  const stamp = text("time", "notification-time", formatTime(note.time));
  if (note.time && Math.abs(note.time) < 8640000000000) stamp.dateTime = new Date(note.time * 1000).toISOString();
  top.append(stamp);
  body.append(top, text("span", "notification-topic", "# " + note.topic));
  body.append(text("p", "notification-message", note.message));
  if (note.tags.length || note.priority >= 4) {
    const tags = text("div", "tags");
    if (note.priority >= 4) tags.append(text("span", "tag urgent-tag", note.priority === 5 ? "Urgent" : "High priority"));
    for (const tag of note.tags) tags.append(text("span", "tag", tag));
    body.append(tags);
  }
  article.append(icon, body); return article;
}
function renderFeed() {
  const topics = settings.selected ? [settings.selected] : settings.topics;
  const all = topics.flatMap(topic => inbox(topic).notes).sort((a, b) => b.time - a.time);
  const found = filterMessages(all, $("search").value.slice(0, 120), Number($("priority").value));
  if (!found.length) {
    const empty = text("div", "empty");
    empty.append(text("div", "empty-icon", "✦"));
    empty.append(text("h3", "", all.length ? "No matching signals" : "Your signal starts here"));
    empty.append(text("p", "", all.length ? "Try another search or priority filter. Nothing has been deleted."
      : settings.topics.length ? "Messages appear here as your subscribed topics receive updates."
      : "Connect to an ntfy server and add a topic to begin."));
    $("feed").replaceChildren(empty);
  } else $("feed").replaceChildren(...found.slice(0, 400).map(makeCard));
  $("feed-summary").textContent = found.length + " of " + all.length + " messages in session memory";
}
function render() {
  renderTopics(); renderConnection();
  $("stat-received").textContent = [...inboxes.values()].reduce((n, box) => n + box.notes.length, 0);
  $("stat-topics").textContent = settings.topics.length;
  const unread = [...inboxes.values()].reduce((n, box) => n + box.unread, 0);
  $("stat-unread").textContent = unread; $("all-count").textContent = unread;
  $("stat-health").textContent = healthStatus; $("health-subtitle").textContent = healthDetail;
  $("page-title").textContent = settings.selected ? "# " + settings.selected : "Stay in the loop.";
  $("breadcrumb-topic").textContent = settings.selected ? "# " + settings.selected : "Overview";
  $("feed-title").textContent = settings.selected ? "Topic activity" : "Recent activity";
  renderFeed();
}
function abortStreams() {
  generation++;
  for (const controller of streams.values()) controller.abort();
  streams.clear();
}
function sleepUntil(ms, signal) {
  return new Promise(resolve => {
    if (signal.aborted) return resolve();
    const stop = () => { clearTimeout(timer); signal.removeEventListener("abort", stop); resolve(); };
    const timer = setTimeout(stop, ms); signal.addEventListener("abort", stop, { once: true });
  });
}
async function followTopic(topic, controller, epoch) {
  const box = inbox(topic), endpoint = settings.endpoint, sessionToken = token;
  let delay = 1000;
  while (!controller.signal.aborted && generation === epoch) {
    box.status = "Connecting"; renderConnection();
    try {
      await subscribeOnce(fetch, {
        endpoint, topic, token: sessionToken, since: box.since, signal: controller.signal,
        onOpen: () => { if (generation === epoch) { box.status = "Connected"; delay = 1000; renderConnection(); } },
        onMessage: note => {
          if (generation !== epoch || controller.signal.aborted) return;
          if (addMessage(box, note, settings.selected === topic || settings.selected === null)) render();
        },
      });
      if (!controller.signal.aborted && generation === epoch) box.status = "Reconnecting";
    } catch (error) {
      if (controller.signal.aborted || generation !== epoch) break;
      box.status = "Error: " + humanError(error);
    }
    renderConnection();
    if (controller.signal.aborted || generation !== epoch) break;
    await sleepUntil(delay, controller.signal); delay = Math.min(delay * 2, 30000);
  }
}
function startStreams(clearHistory = false) {
  abortStreams();
  if (clearHistory) inboxes.clear();
  const epoch = generation;
  for (const topic of settings.topics) {
    const controller = new AbortController();
    streams.set(topic, controller);
    void followTopic(topic, controller, epoch);
  }
  render();
}
async function testHealth() {
  const epoch = generation, started = performance.now();
  healthStatus = "Checking…"; healthDetail = "Read-only request to ntfy"; render();
  try {
    const result = await health(fetch, settings.endpoint, token);
    if (generation !== epoch) return;
    healthStatus = result ? "Healthy" : "Unhealthy";
    healthDetail = "Responded in " + Math.round(performance.now() - started) + " ms";
  } catch (error) {
    if (generation !== epoch) return;
    healthStatus = "Unavailable"; healthDetail = humanError(error);
  }
  render(); toast(healthStatus + " · " + healthDetail);
}
function openDialog(id) { $(id).showModal(); }
function closeDialog(id) { $(id).close(); }
function setup() {
  setTheme();
  $("top-settings").addEventListener("click", () => $("open-settings").click());
  $("open-settings").addEventListener("click", () => {
    $("server-input").value = settings.endpoint;
    $("token-input").value = ""; $("forget-token").checked = false;
    openDialog("settings-dialog");
  });
  $("settings-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      const endpoint = normalizeEndpoint($("server-input").value);
      const nextToken = chooseToken(settings.endpoint, endpoint, token, $("token-input").value, $("forget-token").checked);
      const changed = endpoint !== settings.endpoint || nextToken !== token;
      settings.endpoint = endpoint; token = nextToken;
      $("token-input").value = ""; persist(); closeDialog("settings-dialog");
      if (changed) {
        healthStatus = "Not checked"; healthDetail = "Run a read-only check";
        startStreams(true);
      }
      toast("Connection settings saved");
    } catch (error) { toast(humanError(error)); }
  });
  $("add-topic").addEventListener("click", () => {
    $("topic-input").value = ""; openDialog("topic-dialog");
  });
  $("topic-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      const topic = validateTopic($("topic-input").value);
      const existed = settings.topics.includes(topic);
      addTopic(settings, topic); persist(); closeDialog("topic-dialog");
      if (!existed) startStreams(); else render();
      toast("Watching #" + topic);
    } catch (error) { toast(humanError(error)); }
  });
  $("all-topics").addEventListener("click", () => viewTopic(null));
  $("search").addEventListener("input", renderFeed);
  $("priority").addEventListener("change", renderFeed);
  $("health-button").addEventListener("click", () => { void testHealth(); });
  $("theme-button").addEventListener("click", () => {
    settings.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    persist(); setTheme();
  });
  $("clear-memory").addEventListener("click", () => {
    if (!confirm("Clear in-memory notification history? Server messages will not be deleted.")) return;
    // Preserve cursors and recent IDs to avoid replaying just-cleared messages.
    for (const box of inboxes.values()) { box.notes = []; box.unread = 0; }
    render(); toast("Session history cleared");
  });
  $("compose-button").addEventListener("click", () => {
    if (!settings.topics.length) { toast("Add a topic before publishing"); return; }
    const target = $("compose-topic"); target.replaceChildren();
    for (const topic of settings.topics) {
      const option = document.createElement("option");
      option.value = topic; option.textContent = "# " + topic; target.append(option);
    }
    target.value = settings.selected || settings.topics[0];
    $("compose-message").value = ""; $("compose-heading").value = "";
    $("compose-tags").value = ""; $("compose-priority").value = "3";
    openDialog("compose-dialog");
  });
  $("compose-form").addEventListener("submit", async event => {
    event.preventDefault();
    const send = $("send-button"); send.disabled = true; send.textContent = "Sending…";
    try {
      await publish(fetch, settings.endpoint, $("compose-topic").value, $("compose-message").value,
        { title: $("compose-heading").value, priority: Number($("compose-priority").value), tags: $("compose-tags").value }, token);
      closeDialog("compose-dialog"); toast("Notification published");
    } catch (error) { toast(humanError(error)); }
    finally { send.disabled = false; send.textContent = "Send notification"; }
  });
  for (const button of document.querySelectorAll("[data-close]"))
    button.addEventListener("click", () => closeDialog(button.dataset.close));
  window.addEventListener("pagehide", abortStreams);
  window.addEventListener("pageshow", event => { if (event.persisted) startStreams(); });
  if (settings.topics.length) startStreams(); else render();
}
setup();
