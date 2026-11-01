"use client";

import { useRenderTool } from "@copilotkit/react-core/v2";

type ToolProps = {
  name: string;
  parameters: Record<string, unknown>;
  status: string;
  result?: string;
};

// Compact summary of what the SQL agent is doing for each tool call.
function describe(name: string, params: Record<string, unknown>): string {
  if (name === "sql_db_list_tables") return "Listing tables";
  if (name === "sql_db_schema") return `Reading schema: ${params.table_names ?? ""}`;
  if (name === "sql_db_query") return "Running query";
  return name;
}

function ToolCard({ name, parameters, status, result }: ToolProps) {
  const done = status === "complete";
  const query = name === "sql_db_query" ? String(parameters.query ?? "") : "";

  return (
    <details className="tool-card">
      <summary>
        <span className={`dot ${done ? "done" : "running"}`} />
        {describe(name, parameters)}
        {!done && "…"}
      </summary>
      {query && <pre className="sql">{query}</pre>}
      {done && result && <pre className="result">{result}</pre>}
    </details>
  );
}

// Registers a wildcard renderer: every tool call the agent makes is drawn as a card.
export function ToolCalls() {
  useRenderTool(
    {
      name: "*",
      render: (props: ToolProps) => <ToolCard {...props} />,
    },
    [],
  );
  return null;
}
