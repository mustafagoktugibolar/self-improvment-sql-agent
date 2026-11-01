"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { ToolCalls } from "@/components/ToolCalls";
import { BACKEND_URL } from "@/lib/config";

export default function Home() {
  return (
    <main>
      <header>
        <h1>SQL Agent</h1>
        <span className="status">AG-UI · backend {BACKEND_URL}/agent</span>
      </header>
      <ToolCalls />
      <div className="chat">
        <CopilotChat agentId="sql_agent" />
      </div>
    </main>
  );
}
