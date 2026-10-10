import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/worker.mjs";

test("worker returns the expected response", async () => {
  const response = await worker.fetch(new Request("https://example.test/"));

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "Hello from the reusable CI/CD foundation.\n");
});