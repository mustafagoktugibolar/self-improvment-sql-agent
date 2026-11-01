import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import type { NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// Agent name must match the one used in <CopilotKit agent="..."> and the Python LangGraphAgent name.
const runtime = new CopilotRuntime({
  agents: {
    sql_agent: new HttpAgent({ url: `${BACKEND_URL}/agent` }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
