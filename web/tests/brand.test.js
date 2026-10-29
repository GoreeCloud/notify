import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
const read=p=>readFileSync(new URL("../"+p,import.meta.url));
test("web favicon uses central official Notify icon",()=>{
 const icon=read("favicon.svg");
 const gitSha=createHash("sha1").update("blob "+icon.length).update(Buffer.from([0])).update(icon).digest("hex");
 assert.equal(gitSha,"cd95f8f3e578b70691e738f63646ff9c06e2d7f3");
});
test("sidebar renders same icon as browser tab",()=>{
 const html=read("index.html").toString("utf8");
 const css=read("styles.css").toString("utf8");
 assert.match(html,/href="\.\/favicon\.svg"/);
 assert.match(html,/<img src="\.\/favicon\.svg" width="40" height="40" alt="">/);
 assert.match(css,/\.mark img\{/);
});

test("native icon and web favicon are byte identical",()=>{
 const web=read("favicon.svg");
 const native=readFileSync(new URL("../../packaging/linux/com.goreecloud.Notify.svg",import.meta.url));
 assert.ok(web.equals(native));
});
