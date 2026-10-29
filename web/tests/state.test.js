import test from "node:test";
import assert from "node:assert/strict";
import { freshState, loadSettings, saveSettings, SETTINGS_KEY, addTopic, removeTopic,
  createInbox, addMessage, filterMessages, markRead, MAX_MESSAGES, MAX_RECENT_IDS } from "../state.js";

function memoryStore() {
  const items = new Map();
  return { getItem: key => items.get(key), setItem: (key, value) => items.set(key, value) };
}
test("settings persist only nonsecret connection metadata", () => {
  const storage = memoryStore(), state = freshState();
  state.endpoint = "/api/ntfy"; addTopic(state, "infra"); state.theme = "dark";
  saveSettings(storage, state);
  const raw = storage.getItem(SETTINGS_KEY);
  assert.ok(raw.includes("infra"));
  assert.ok(!raw.includes("token"));
  assert.deepEqual(loadSettings(storage).topics, ["infra"]);
  assert.equal(loadSettings(storage).selected, "infra");
});
test("corrupt settings recover to safe defaults", () => {
  assert.equal(loadSettings({ getItem: () => "{invalid" }).endpoint, "/api/ntfy");
  assert.deepEqual(loadSettings({ getItem: () => '{"topics":["../traversal"]}' }).topics, []);
});
test("topic addition deduplicates and removal updates selection", () => {
  const state = freshState();
  addTopic(state, "first"); addTopic(state, "second"); addTopic(state, "first");
  assert.deepEqual(state.topics, ["first", "second"]);
  removeTopic(state, "first");
  assert.equal(state.selected, "second");
  removeTopic(state, "second");
  assert.equal(state.selected, null);
});
test("message deduplication, bounded history, unread and cursors", () => {
  const box = createInbox();
  const note = i => ({ id: String(i), topic: "alerts", title: "", message: "m", priority: 3, time: i, tags: [] });
  for (let i = 0; i < MAX_MESSAGES + 10; i++) addMessage(box, note(i));
  assert.equal(box.notes.length, MAX_MESSAGES);
  assert.equal(box.since, String(MAX_MESSAGES + 9));
  assert.equal(box.unread, MAX_MESSAGES + 10);
  assert.equal(addMessage(box, note(1)), false);
  assert.equal(box.idQueue.length, MAX_MESSAGES + 10);
  for (let i = MAX_MESSAGES + 10; i < MAX_RECENT_IDS + 5; i++) addMessage(box, note(i), true);
  assert.equal(box.idQueue.length, MAX_RECENT_IDS);
  assert.equal(box.notes.length, MAX_MESSAGES);
});
test("offline filtering is case-insensitive and all words must match", () => {
  const notes = [
    { title: "Backup complete", topic: "infra", message: "ZFS okay", tags: ["success"], priority: 3 },
    { title: "Storage alert", topic: "infra", message: "Pool degraded", tags: ["ZFS"], priority: 5 },
  ];
  assert.deepEqual(filterMessages(notes, "storage DEGRADED", 4), [notes[1]]);
  assert.deepEqual(filterMessages(notes, "ZFS"), notes);
  assert.deepEqual(filterMessages(notes, "no match"), []);
});

test("combined feed marks all inboxes read, topic view only its own inbox", () => {
  const inboxes = new Map([["alerts", createInbox()], ["ops", createInbox()]]);
  inboxes.get("alerts").unread = 3;
  inboxes.get("ops").unread = 4;
  markRead(inboxes, "alerts");
  assert.equal(inboxes.get("alerts").unread, 0);
  assert.equal(inboxes.get("ops").unread, 4);
  markRead(inboxes, null);
  assert.equal(inboxes.get("ops").unread, 0);
});
