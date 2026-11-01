"use client";

import { useState } from "react";
import { useInterrupt } from "@copilotkit/react-core/v2";
import styles from "./cards.module.css";

type AskUserCardProps = {
  question: string;
  options: string[];
  onAnswer: (answer: string) => void;
  onSkip: () => void;
};

function AskUserCard({ question, options, onAnswer, onSkip }: AskUserCardProps) {
  const [custom, setCustom] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function answer(text: string) {
    if (submitted || !text.trim()) return;
    setSubmitted(true);
    onAnswer(text.trim());
  }

  function skip() {
    if (submitted) return;
    setSubmitted(true);
    onSkip();
  }

  return (
    <div className={styles.askUser}>
      <p className={styles.question}>{question}</p>
      <div className={styles.options}>
        {options.map((option) => (
          <button
            key={option}
            className={styles.button}
            onClick={() => answer(option)}
            disabled={submitted}
          >
            {option}
          </button>
        ))}
      </div>
      <form
        className={styles.custom}
        onSubmit={(e) => {
          e.preventDefault();
          answer(custom);
        }}
      >
        <input
          className={styles.input}
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          placeholder="Or type your own answer…"
          disabled={submitted}
        />
        <button
          type="submit"
          className={styles.button}
          disabled={submitted || !custom.trim()}
        >
          Send
        </button>
      </form>
      <button className={styles.skip} onClick={skip} disabled={submitted}>
        Skip, let the agent decide
      </button>
    </div>
  );
}

// Shows the agent's ask_user interrupts in the chat. The backend tool calls
// LangGraph interrupt(); resolve() resumes the run with the chosen answer and
// cancel() resumes it without one (the agent then states its own assumption).
export function AskUser() {
  useInterrupt({
    agentId: "sql_agent",
    enabled: (event) => event.value?.reason === "ask_user",
    render: ({ interrupt, resolve, cancel }) => (
      <AskUserCard
        question={interrupt?.message ?? ""}
        options={interrupt?.metadata?.langgraph?.raw?.options ?? []}
        onAnswer={(text) => resolve(text)}
        onSkip={() => cancel()}
      />
    ),
  });
  return null;
}
