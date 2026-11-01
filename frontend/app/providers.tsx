"use client";

import { Suspense, type ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";

export function Providers({ children }: { children: ReactNode }) {
  // CopilotKit generates random ids on render, which can't be prerendered.
  // Suspense makes this subtree render per request instead of at build time,
  // while still letting Next render (and validate) the page on the server.
  return (
    <Suspense fallback={null}>
      <CopilotKit runtimeUrl="/api/copilotkit" agent="sql_agent">
        {children}
      </CopilotKit>
    </Suspense>
  );
}
