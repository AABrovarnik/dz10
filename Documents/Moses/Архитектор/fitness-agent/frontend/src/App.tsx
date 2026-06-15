import { useCallback, useEffect, useRef, useState } from "react";
import Chat from "./components/Chat/Chat";
import Logs from "./components/Logs/Logs";
import McpMethods from "./components/McpMethods/McpMethods";
import MapTab from "./components/MapTab/MapTab";
import CalendarTab from "./components/CalendarTab/CalendarTab";
import { LogEvent, startAgent, streamLogs } from "./api";

type Tab = "logs" | "mcp" | "map" | "calendar";

const TABS: { id: Tab; label: string }[] = [
  { id: "logs", label: "Логи" },
  { id: "mcp", label: "MCP методы" },
  { id: "map", label: "Карта" },
  { id: "calendar", label: "Календарь" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("logs");
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [status, setStatus] = useState<"idle" | "searching" | "booking" | "done" | "error">("idle");
  const [finalText, setFinalText] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const stepRef = useRef(0);

  const handleSend = useCallback(async (message: string) => {
    // Сброс предыдущего стрима
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setEvents([]);
    setFinalText(null);
    setStatus("searching");
    stepRef.current = 0;

    const { run_id } = await startAgent(message);
    setRunId(run_id);

    const es = streamLogs(
      run_id,
      (e) => {
        setEvents((prev) => [...prev, e]);
        stepRef.current += 1;
        // Обновляем статус по kind
        if (e.kind === "tool_call") {
          if (e.tool === "book_class") setStatus("booking");
          else setStatus("searching");
        }
        if (e.kind === "decision" && e.title?.startsWith("Готово")) setStatus("done");
        if (e.kind === "done") {
          setStatus("done");
          // Достаём финальный текст: последний decision
          setFinalText((cur) => cur);
        }
        if (e.kind === "error") setStatus("error");
      },
      () => {
        /* stream closed */
      },
    );
    esRef.current = es;
  }, []);

  // Из последнего decision-event'а делаем финальный текст
  useEffect(() => {
    const lastDecision = [...events].reverse().find((e) => e.kind === "decision");
    if (lastDecision && lastDecision.title && (lastDecision.title.startsWith("Готово") || lastDecision.title.includes("забронировал") || lastDecision.title.includes("Подходящих") || lastDecision.title.includes("Не удалось"))) {
      setFinalText(lastDecision.title);
    }
  }, [events]);

  // Снимаем SSE при unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  const statusColor: Record<typeof status, string> = {
    idle: "#6b7280",
    searching: "#2563eb",
    booking: "#d97706",
    done: "#16a34a",
    error: "#dc2626",
  };
  const statusLabel: Record<typeof status, string> = {
    idle: "ожидание",
    searching: "ищу",
    booking: "бронирую",
    done: "готово",
    error: "ошибка",
  };

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
      {/* Левая колонка: чат */}
      <aside
        style={{
          width: "25%",
          minWidth: 320,
          maxWidth: 420,
          borderRight: "1px solid var(--border)",
          background: "var(--panel)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Chat
          onSend={handleSend}
          status={status}
          statusColor={statusColor[status]}
          statusLabel={statusLabel[status]}
          finalText={finalText}
          eventsCount={events.length}
        />
      </aside>

      {/* Правая колонка: табы */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 16px",
            borderBottom: "1px solid var(--border)",
            background: "var(--panel)",
          }}
        >
          <div style={{ fontWeight: 600 }}>AI-агент + MCP · фитнес-бронирование</div>
          <div style={{ flex: 1 }} />
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: 99,
                background: statusColor[status],
                display: "inline-block",
              }}
            />
            <span>статус: <b style={{ color: statusColor[status] }}>{statusLabel[status]}</b></span>
            <span style={{ marginLeft: 8 }}>· шагов: {events.length}</span>
          </div>
        </header>

        <nav style={{ display: "flex", gap: 4, padding: "8px 12px", borderBottom: "1px solid var(--border)", background: "var(--panel)" }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                background: tab === t.id ? "var(--accent-soft)" : "transparent",
                color: tab === t.id ? "var(--accent)" : "var(--text)",
                border: "none",
                padding: "6px 12px",
                borderRadius: 6,
                fontWeight: tab === t.id ? 600 : 500,
              }}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <section style={{ flex: 1, overflow: "auto", padding: 16 }}>
          {tab === "logs" && <Logs events={events} />}
          {tab === "mcp" && <McpMethods />}
          {tab === "map" && <MapTab highlightRunId={runId} />}
          {tab === "calendar" && <CalendarTab highlightRunId={runId} />}
        </section>
      </main>
    </div>
  );
}
