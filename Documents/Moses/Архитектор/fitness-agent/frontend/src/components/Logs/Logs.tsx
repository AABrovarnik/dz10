import { useState } from "react";
import { LogEvent } from "../../api";

const KIND_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  plan: { bg: "#eef2ff", fg: "#3730a3", label: "план" },
  tool_call: { bg: "#dbeafe", fg: "#1d4ed8", label: "MCP-вызов" },
  observation: { bg: "#ecfdf5", fg: "#047857", label: "ответ MCP" },
  decision: { bg: "#fef3c7", fg: "#92400e", label: "решение агента" },
  status: { bg: "#f1f5f9", fg: "#475569", label: "статус" },
  done: { bg: "#dcfce7", fg: "#166534", label: "готово" },
  error: { bg: "#fee2e2", fg: "#991b1b", label: "ошибка" },
};

export default function Logs({ events }: { events: LogEvent[] }) {
  if (events.length === 0) {
    return (
      <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 32 }}>
        Здесь будут появляться шаги агента. Отправьте запрос слева.
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {events.map((e, i) => (
        <Card key={i} e={e} />
      ))}
    </div>
  );
}

function Card({ e }: { e: LogEvent }) {
  const [open, setOpen] = useState(false);
  const k = KIND_COLORS[e.kind] || KIND_COLORS.status;
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        boxShadow: "var(--shadow)",
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px" }}>
        <span style={{ background: k.bg, color: k.fg, fontSize: 11, padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>
          [{e.step}] {k.label}
        </span>
        <span style={{ fontWeight: 600 }}>{e.title}</span>
        <div style={{ flex: 1 }} />
        {typeof e.latency_ms === "number" && (
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>⏱ {e.latency_ms} ms</span>
        )}
        {e.ok === true && <span style={{ fontSize: 12, color: "var(--ok)" }}>● ok</span>}
        {e.ok === false && <span style={{ fontSize: 12, color: "var(--err)" }}>● fail</span>}
        {(e.args || e.result || e.error) && (
          <button onClick={() => setOpen((o) => !o)} style={{ fontSize: 12, padding: "2px 6px" }}>
            {open ? "скрыть" : "JSON"}
          </button>
        )}
      </div>
      {open && (
        <div
          style={{
            background: "var(--code-bg)",
            color: "var(--code-text)",
            padding: 10,
            maxHeight: 320,
            overflow: "auto",
            fontSize: 12,
          }}
        >
          {e.args && (
            <Section title="args">
              <pre>{JSON.stringify(e.args, null, 2)}</pre>
            </Section>
          )}
          {e.result !== undefined && e.result !== null && (
            <Section title="result">
              <pre>{JSON.stringify(e.result, null, 2)}</pre>
            </Section>
          )}
          {e.error && (
            <Section title="error">
              <pre style={{ color: "#fca5a5" }}>{e.error}</pre>
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ color: "#94a3b8", fontSize: 11, marginBottom: 4 }}>{title}</div>
      {children}
    </div>
  );
}
