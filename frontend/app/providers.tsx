"use client";

import { useSyncExternalStore, type ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";

export function Providers({ children }: { children: ReactNode }) {
  // CopilotKit generates random ids on render, which Next can't prerender; mount client-side only.
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  if (!mounted) return null;

  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="sql_agent">
      {children}
    </CopilotKit>
  );
}
