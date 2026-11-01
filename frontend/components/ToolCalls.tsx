"use client";

import { useRenderTool } from "@copilotkit/react-core/v2";
import styles from "./cards.module.css";

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
  if (name === "business_definitions") return `Looking up: ${params.terms ?? ""}`;
  if (name === "ask_user") return "Asking you a question";
  return name;
}

// Tool results are compact JSON (fewer tokens for the model); indent them for people.
function formatResult(result: string): string {
  try {
    return JSON.stringify(JSON.parse(result), null, 2);
  } catch {
    return result;
  }
}

function ToolCard({ name, parameters, status, result }: ToolProps) {
  const done = status === "complete";
  const query = name === "sql_db_query" ? String(parameters.query ?? "") : "";

  return (
    <details className={styles.toolCard}>
      <summary>
        <span className={`${styles.dot} ${done ? styles.done : styles.running}`} />
        {describe(name, parameters)}
        {!done && "…"}
      </summary>
      {query && <pre>{query}</pre>}
      {done && result && <pre>{formatResult(result)}</pre>}
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
