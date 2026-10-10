import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import * as cloudflare from "@pulumi/cloudflare";
import * as pulumi from "@pulumi/pulumi";

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} must be set by the CI/CD workflow or local development environment.`);
  }
  return value;
}

const accountId = requiredEnvironment("CLOUDFLARE_ACCOUNT_ID");
const workerName = requiredEnvironment("CLOUDFLARE_WORKER_NAME");
const workersDevSubdomain = requiredEnvironment("CLOUDFLARE_WORKERS_DEV_SUBDOMAIN");

const workerSource = readFileSync(resolve(import.meta.dirname, "..", "src", "worker.mjs"), "utf8");

new cloudflare.WorkersScript("worker", {
  accountId,
  scriptName: workerName,
  content: workerSource,
  compatibilityDate: "2026-10-10",
});

export const workerUrl = pulumi.interpolate`https://${workerName}.${workersDevSubdomain}.workers.dev`;