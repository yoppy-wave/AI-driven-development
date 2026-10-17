import * as cdk from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { ApplicationStack, stackNameForEnvironment } from "../lib/application-stack";

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
});