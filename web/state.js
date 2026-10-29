/** Local-only state. Never persist credentials or notification bodies. */
import { normalizeEndpoint, validateTopic } from "./protocol.js";
export const DEFAULT_ENDPOINT = "/api/ntfy";
export const MAX_TOPICS = 50, MAX_MESSAGES = 200, MAX_RECENT_IDS = 500;
export const SETTINGS_KEY = "goreecloud.notify.web.settings.v1";
export function freshState() {
  return { endpoint: DEFAULT_ENDPOINT, topics: [], theme: "system", selected: null };
}
export function loadSettings(storage) {
  const state = freshState();
  if (!storage) return state;
  try {
    const raw = JSON.parse(storage.getItem(SETTINGS_KEY) || "{}");
    if (typeof raw.endpoint === "string") state.endpoint = normalizeEndpoint(raw.endpoint);
    if (Array.isArray(raw.topics)) state.topics = [...new Set(raw.topics.map(validateTopic))].slice(0, MAX_TOPICS);
    if (["light", "dark", "system"].includes(raw.theme)) state.theme = raw.theme;
  } catch { return freshState(); }
  state.selected = state.topics[0] || null;
  return state;
}
export function saveSettings(storage, state) {
  if (!storage) return;
  storage.setItem(SETTINGS_KEY, JSON.stringify({
    endpoint: normalizeEndpoint(state.endpoint), topics: state.topics.map(validateTopic).slice(0, MAX_TOPICS),
    theme: ["light", "dark", "system"].includes(state.theme) ? state.theme : "system",
  }));
}
export function addTopic(state, value) {
  const topic = validateTopic(value);
  if (!state.topics.includes(topic)) {
    if (state.topics.length >= MAX_TOPICS) throw new Error("Topic limit reached (50)");
    state.topics.push(topic);
  }
  state.selected = topic;
  return topic;
}
export function removeTopic(state, topic) {
  state.topics = state.topics.filter(name => name !== topic);
  if (state.selected === topic) state.selected = state.topics[0] || null;
}
export function createInbox() {
  return { notes: [], recentIds: new Set(), idQueue: [], unread: 0, since: "10m", status: "Idle" };
}
export function addMessage(inbox, note, selected = false) {
  if (inbox.recentIds.has(note.id)) return false;
  inbox.recentIds.add(note.id);
  inbox.idQueue.push(note.id);
  if (inbox.idQueue.length > MAX_RECENT_IDS) inbox.recentIds.delete(inbox.idQueue.shift());
  inbox.notes.push(note);
  if (inbox.notes.length > MAX_MESSAGES) inbox.notes.splice(0, inbox.notes.length - MAX_MESSAGES);
  inbox.since = note.id;
  if (!selected) inbox.unread += 1;
  return true;
}
/** Opening the combined inbox marks every visible topic as read. */
export function markRead(inboxes, selectedTopic = null) {
  for (const [topic, box] of inboxes) {
    if (selectedTopic === null || topic === selectedTopic) box.unread = 0;
  }
}
export function filterMessages(notes, query = "", minPriority = 1) {
  const words = String(query).trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return notes.filter(note => {
    if (note.priority < minPriority) return false;
    const all = [note.title, note.message, note.topic, ...(note.tags || [])].join(" ").toLocaleLowerCase();
    return words.every(word => all.includes(word));
  });
}
