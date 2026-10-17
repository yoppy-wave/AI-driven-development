import * as cdk from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ApplicationStack, stackNameForEnvironment } from "../lib/application-stack";

const lambdaDirectory = join(process.cwd(), "lambda");

function lambdaAsset(): { hash: string; files: string[] } {
  const outdir = mkdtempSync(join(tmpdir(), "ai-driven-development-cdk-"));
  try {
    const app = new cdk.App({ outdir });
    new ApplicationStack(app, "AssetTest", { environment: "development" });
    app.synth();

    const assetDirectory = readdirSync(outdir, { withFileTypes: true }).find(
      (entry) => entry.isDirectory() && entry.name.startsWith("asset."),
    );
    if (!assetDirectory) {
      throw new Error("Lambda asset was not staged");
    }

    const directory = join(outdir, assetDirectory.name);
    return {
      hash: assetDirectory.name.slice("asset.".length),
      files: ["handler.py", "handler_test.py", "nested/handler_test.py"].filter((file) => existsSync(join(directory, file))),
    };
  } finally {
    rmSync(outdir, { recursive: true, force: true });
  }
}

describe("ApplicationStack", () => {
  test("creates an API, Python Lambda asset, and DynamoDB table", () => {
    const app = new cdk.App();
    const stack = new ApplicationStack(app, stackNameForEnvironment("pr-42"), { environment: "pr-42" });
    const template = Template.fromStack(stack);
    template.resourceCountIs("AWS::DynamoDB::Table", 1);
    template.hasResourceProperties("AWS::Lambda::Function", {
      Runtime: "python3.12",
      Handler: "handler.handler",
      Code: Match.objectLike({ S3Key: Match.anyValue() }),
      Environment: { Variables: Match.objectLike({ APP_ENVIRONMENT: "pr-42" }) },
    });
    template.resourceCountIs("AWS::ApiGateway::RestApi", 1);
  });

  test("retains DynamoDB data only in production", () => {
    const production = Template.fromStack(new ApplicationStack(new cdk.App(), "Production", { environment: "production" }));
    const preview = Template.fromStack(new ApplicationStack(new cdk.App(), "Preview", { environment: "pr-42" }));
    production.hasResource("AWS::DynamoDB::Table", { DeletionPolicy: "Retain" });
    preview.hasResource("AWS::DynamoDB::Table", { DeletionPolicy: "Delete" });
  });

  test.each([["development", "app-development"], ["staging", "app-staging"], ["production", "app-production"], ["pr-123", "app-pr-123"]])(
    "uses an environment-scoped stack name for %s",
    (environment, expected) => expect(stackNameForEnvironment(environment)).toBe(expected),
  );

  test("rejects a stack environment that cannot be safely targeted", () => {
    expect(() => stackNameForEnvironment("prod")).toThrow("environment must be");
  });

  test("excludes Python tests from the Lambda asset without masking implementation changes", () => {
    const handlerPath = join(lambdaDirectory, "handler.py");
    const testPath = join(lambdaDirectory, "handler_test.py");
    const nestedDirectory = join(lambdaDirectory, "nested");
    const nestedTestPath = join(nestedDirectory, "handler_test.py");
    const originalHandler = readFileSync(handlerPath, "utf8");
    const originalTest = readFileSync(testPath, "utf8");

    mkdirSync(nestedDirectory, { recursive: true });
    writeFileSync(nestedTestPath, "def test_nested_handler() -> None:\n    pass\n");

    try {
      const initialAsset = lambdaAsset();
      expect(initialAsset.files).toEqual(["handler.py"]);

      writeFileSync(testPath, `${originalTest}\n# Asset exclusion regression test.\n`);
      expect(lambdaAsset().hash).toBe(initialAsset.hash);

      writeFileSync(handlerPath, `${originalHandler}\n# Asset hash regression test.\n`);
      expect(lambdaAsset().hash).not.toBe(initialAsset.hash);
    } finally {
      writeFileSync(handlerPath, originalHandler);
      writeFileSync(testPath, originalTest);
      rmSync(nestedDirectory, { recursive: true, force: true });
    }
  });
});