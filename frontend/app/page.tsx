"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { AskUser } from "@/components/AskUser";
import { ToolCalls } from "@/components/ToolCalls";

export default function Home() {
  return (
    <main>
      <ToolCalls />
      <AskUser />
      <CopilotChat agentId="sql_agent" />
    </main>
  );
}
