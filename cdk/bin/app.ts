#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { SpliceStack } from "../lib/splice-stack";

const app = new cdk.App();

new SpliceStack(app, "SpliceStack", {
  description: "Meta-tooling layer demo: context orchestration above AI coding assistants",
});
