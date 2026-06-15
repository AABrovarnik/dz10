/** Минимальный fetch-клиент + EventSource-обёртка для SSE. */

export type LogEvent = {
  run_id: string;
  step: number;
  kind: "plan" | "tool_call" | "observation" | "decision" | "status" | "done" | "error";
  title: string;
  mcp?: string | null;
  tool?: string | null;
  args?: Record<string, unknown> | null;
  result?: unknown;
  ok?: boolean;
  error?: string | null;
  latency_ms?: number | null;
  ts?: number;
};

export type AgentState = {
  run_id: string;
  status: "running" | "done" | "error";
  final: string | null;
  steps: LogEvent[];
};

export type ServerEntry = {
  server: string;
  label: string;
  url: string;
  description: string;
  tools: { name: string; description: string; input_schema: unknown }[];
};

export type ToolsRegistry = { servers: ServerEntry[]; places: Array<{ id: string; name: string; lat: number; lng: number; type: string[]; description: string; address: string }> };

const API = ""; // проксируется Vite на :8000

export async function startAgent(message: string): Promise<{ run_id: string }> {
  const r = await fetch(`${API}/api/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export function streamLogs(runId: string, onEvent: (e: LogEvent) => void, onClose: () => void): EventSource {
  const es = new EventSource(`${API}/api/logs/stream?run_id=${runId}`);
  const kinds: LogEvent["kind"][] = ["plan", "tool_call", "observation", "decision", "status", "done", "error"];
  for (const k of kinds) {
    es.addEventListener(k, (msg) => {
      try {
        const data = JSON.parse((msg as MessageEvent).data) as LogEvent;
        onEvent(data);
        if (k === "done" || k === "error") {
          es.close();
          onClose();
        }
      } catch {
        /* ignore */
      }
    });
  }
  es.onerror = () => {
    es.close();
    onClose();
  };
  return es;
}

export async function getAgentState(runId: string): Promise<AgentState> {
  const r = await fetch(`${API}/api/agent/state?run_id=${runId}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getToolsRegistry(): Promise<ToolsRegistry> {
  const r = await fetch(`${API}/api/tools`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
