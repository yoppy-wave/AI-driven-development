const fs = require("node:fs");
const path = require("node:path");
const actionlint = require("actionlint");

const workflowDirectory = path.join(process.cwd(), ".github", "workflows");
async function main() {
  const lint = await actionlint.createLinter();
  const findings = [];
  for (const file of fs.readdirSync(workflowDirectory).filter((name) => /\.ya?ml$/.test(name)).sort()) {
    const source = fs.readFileSync(path.join(workflowDirectory, file), "utf8");
    for (const error of lint(source, file)) {
      const knownActionlintGap =
        error.kind === "runner-label" && error.message.includes('label "ubuntu-24.04" is unknown') ||
        (error.kind === "expression" && error.message.includes('undefined variable "vars"') && /^(ai-coding|ai-question)\.yml$/.test(file)) ||
        (error.kind === "expression" && error.message.includes('property "workflow_sha" is not defined') && /^(cicd-preview-cleanup|reusable-aws-cdk)\.yml$/.test(file)) ||
        (error.kind === "syntax-check" && error.message.includes('unexpected key "queue"') && /^(cicd|cicd-preview-cleanup)\.yml$/.test(file));
      if (knownActionlintGap) continue;
      findings.push(`${file}:${error.line}:${error.column}: ${error.message} [${error.kind}]`);
    }
  }
  if (findings.length) throw new Error(findings.join("\n"));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});