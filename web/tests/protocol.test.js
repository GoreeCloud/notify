import test from "node:test";
import assert from "node:assert/strict";
import { ReadableStream } from "node:stream/web";
import { normalizeEndpoint, validateTopic, topicUrl, parseEvent, makePublishRequest,
  publish, health, subscribeOnce, chooseToken, MAX_EVENT_LINE } from "../protocol.js";

test("endpoint accepts same-origin and HTTPS/loopback; rejects unsafe addresses", () => {
  assert.equal(normalizeEndpoint("/api/ntfy/"), "/api/ntfy");
  assert.equal(normalizeEndpoint("https://ntfy.example.test/proxy/"), "https://ntfy.example.test/proxy");
  assert.equal(normalizeEndpoint("http://localhost:8090"), "http://localhost:8090");
  for (const invalid of ["", "//evil.test", "http://evil.test", "ftp://evil.test", "https://a:b@evil.test",
    "https://ntfy.test/?token=x", "/api/../other", "https://ntfy.test/#secret"]) {
    assert.throws(() => normalizeEndpoint(invalid), undefined, invalid);
  }
});
test("topics are validated before constructing any path", () => {
  assert.equal(validateTopic("  backup_01  "), "backup_01");
  assert.equal(topicUrl("/api/ntfy", "alerts", "json"), "/api/ntfy/alerts/json");
  for (const topic of ["", "../data", "hello world", "foo/bar", "foo?token=x", "a".repeat(65)])
    assert.throws(() => validateTopic(topic));
});
test("parser accepts only correctly typed message events", () => {
  const msg = { event: "message", id: "a", topic: "alerts", message: "<img src=x>", tags: ["good"], priority: 5, time: 123 };
  assert.equal(parseEvent(JSON.stringify(msg)).message, "<img src=x>");
  assert.deepEqual(parseEvent(msg).tags, ["good"]);
  for (const event of ["bad json", { event: "open" }, { ...msg, priority: 99 },
    { ...msg, id: null }, { ...msg, topic: "../admin" }]) assert.equal(parseEvent(event), null);
});
test("publish validates body, headers, token and destination", async () => {
  const { url, init } = makePublishRequest("/api/ntfy", "alerts", "Backups done", {
    title: "Success", priority: 4, tags: "backup,success"
  }, "token-test");
  assert.equal(url, "/api/ntfy/alerts");
  assert.equal(init.headers.Authorization, "Bearer token-test");
  assert.equal(init.headers.Priority, "4");
  const calls = [];
  await publish(async (...args) => { calls.push(args); return { ok: true }; },
    "/api/ntfy", "alerts", "test", {}, "token-test");
  assert.equal(calls.length, 1);
  for (const message of ["  ", "x".repeat(8193)]) assert.throws(() => makePublishRequest("/api/ntfy", "alerts", message));
  assert.throws(() => makePublishRequest("/api/ntfy", "alerts", "test", { title: "oops\r\nInjected" }));
  await assert.rejects(
    publish(async () => ({ ok: false, status: 403 }), "/api/ntfy", "alerts", "hello"),
    error => error.name === "NtfyRequestError" && error.status === 403 && /Access denied/.test(error.message)
  );
});
test("health recognizes booleans and rejects malformed response", async () => {
  assert.equal(await health(async () => ({ ok: true, text: async () => '{"healthy":true}' }), "/api/ntfy"), true);
  assert.equal(await health(async () => ({ ok: true, text: async () => '{"healthy":false}' }), "/api/ntfy"), false);
  await assert.rejects(health(async () => ({ ok: true, text: async () => '{"healthy":"yes"}' }), "/api/ntfy"), /Unrecognized/);
});
function response(chunks) {
  return {
    ok: true,
    body: new ReadableStream({
      start(controller) { for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk)); controller.close(); }
    })
  };
}
test("stream parses fragmented NDJSON, ignores keepalive and wrong topics", async () => {
  const got = []; const calls = [];
  await subscribeOnce(async (url, opts) => {
    calls.push([url, opts]);
    return response([
      '{"event":"open"}\n{"event":"message","id":"a","topic":"alerts","message":"Par',
      'tial","time":12}\n{"event":"keepalive"}\n',
      '{"event":"message","id":"b","topic":"other","message":"ignored"}\n'
    ]);
  }, { endpoint: "/api/ntfy", topic: "alerts", since: "10m", onMessage: n => got.push(n) });
  assert.equal(calls[0][0], "/api/ntfy/alerts/json?since=10m");
  assert.deepEqual(got.map(n => n.id), ["a"]);
  assert.equal(got[0].message, "Partial");
});
test("stream enforces event bounds and disables redirects", async () => {
  await assert.rejects(subscribeOnce(async () => response(["x".repeat(MAX_EVENT_LINE + 10) + "\n"]),
    { endpoint: "/api/ntfy", topic: "alerts" }), /Oversized/);
  await assert.rejects(subscribeOnce(async () => ({ ok: true, redirected: true }),
    { endpoint: "/api/ntfy", topic: "alerts" }), /Redirect/);
});

test("tokens do not leak across endpoint changes", () => {
  assert.equal(chooseToken("/api/ntfy", "/api/ntfy", "secret-A", "", false), "secret-A");
  assert.equal(chooseToken("https://one.test", "https://two.test", "secret-A", "", false), "");
  assert.equal(chooseToken("https://one.test", "https://two.test", "secret-A", "secret-B", false), "secret-B");
  assert.equal(chooseToken("/api/ntfy", "/api/ntfy", "secret-A", "", true), "");
  assert.throws(() => chooseToken("/api/ntfy", "/api/ntfy", "", "bad\r\ntoken"), /Invalid/);
});

test("health response is bounded before it is fully read", async () => {
  let cancelled = false;
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(4097));
    },
    cancel() { cancelled = true; },
  });
  await assert.rejects(
    health(async () => ({ ok: true, body }), "/api/ntfy"),
    /Oversized health response/,
  );
  assert.equal(cancelled, true);
});
