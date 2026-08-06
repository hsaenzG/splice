import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import { Construct } from "constructs";
import * as path from "path";

export class SpliceStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const sessionsTable = new dynamodb.Table(this, "SessionsTable", {
      tableName: "splice-sessions",
      partitionKey: { name: "sessionId", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const bedrockPolicy = new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: ["*"],
    });

    const lambdaEnv = {
      SESSIONS_TABLE: sessionsTable.tableName,
      SPLICE_ORCHESTRATOR: "bedrock",
      BEDROCK_MODEL_ID: "amazon.nova-lite-v1:0",
    };

    const makeHandler = (id: string, handler: string) => {
      const fn = new lambda.Function(this, id, {
        runtime: lambda.Runtime.PYTHON_3_12,
        handler,
        code: lambda.Code.fromAsset(path.join(__dirname, "../../src")),
        environment: lambdaEnv,
        timeout: cdk.Duration.seconds(30),
        memorySize: 256,
      });
      sessionsTable.grantReadWriteData(fn);
      fn.addToRolePolicy(bedrockPolicy);
      return fn;
    };

    const createSessionFn = makeHandler("CreateSessionFn", "handlers.create_session.handler");
    const ingestContextFn = makeHandler("IngestContextFn", "handlers.ingest_context.handler");
    const orchestrateFn = makeHandler("OrchestrateFn", "handlers.orchestrate.handler");
    const getInsightsFn = makeHandler("GetInsightsFn", "handlers.get_insights.handler");
    const enricherFn = makeHandler("ContextEnricherFn", "handlers.context_enricher.handler");

    const api = new apigateway.RestApi(this, "SpliceApi", {
      restApiName: "Splice API",
      description: "Meta-tooling layer for AI coding assistant context orchestration",
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      },
    });

    const sessions = api.root.addResource("sessions");
    sessions.addMethod("POST", new apigateway.LambdaIntegration(createSessionFn));

    const session = sessions.addResource("{sessionId}");
    const ingest = session.addResource("ingest");
    ingest.addMethod("POST", new apigateway.LambdaIntegration(ingestContextFn));

    const orchestrate = session.addResource("orchestrate");
    orchestrate.addMethod("POST", new apigateway.LambdaIntegration(orchestrateFn));

    const insights = session.addResource("insights");
    insights.addMethod("GET", new apigateway.LambdaIntegration(getInsightsFn));

    const eventBus = new events.EventBus(this, "SpliceBus", {
      eventBusName: "splice-bus",
    });

    new events.Rule(this, "ContextIngestedRule", {
      eventBus,
      eventPattern: {
        source: ["splice"],
        detailType: ["ContextIngested"],
      },
      targets: [new targets.LambdaFunction(enricherFn)],
    });

    ingestContextFn.addEnvironment("EVENT_BUS_NAME", eventBus.eventBusName);
    eventBus.grantPutEventsTo(ingestContextFn);

    const webBucket = new s3.Bucket(this, "InsightsWebBucket", {
      websiteIndexDocument: "index.html",
      publicReadAccess: true,
      blockPublicAccess: new s3.BlockPublicAccess({
        blockPublicAcls: false,
        blockPublicPolicy: false,
        ignorePublicAcls: false,
        restrictPublicBuckets: false,
      }),
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    new s3deploy.BucketDeployment(this, "DeployWeb", {
      sources: [s3deploy.Source.asset(path.join(__dirname, "../../web"))],
      destinationBucket: webBucket,
    });

    new cdk.CfnOutput(this, "ApiUrl", {
      value: api.url,
      description: "Splice API base URL",
    });

    new cdk.CfnOutput(this, "WebUrl", {
      value: webBucket.bucketWebsiteUrl,
      description: "Insights dashboard URL",
    });

    new cdk.CfnOutput(this, "EventBusName", {
      value: eventBus.eventBusName,
    });
  }
}
