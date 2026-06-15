import { useState } from "react";

type Props = {
  onSend: (message: string) => void;
  status: "idle" | "searching" | "booking" | "done" | "error";
  statusColor: string;
  statusLabel: string;
  finalText: string | null;
  eventsCount: number;
};

const SUGGESTIONS = [
  "Найди бассейн утром в субботу",
  "Запиши меня на теннис в среду вечером",
  "Хочу йогу завтра утром",
  "Подбери тренировку рядом",
  "Найди что-то в выходные",
];

export default function Chat({ onSend, statusColor, statusLabel, finalText, eventsCount }: Props) {
  const [text, setText] = useState("");
  const [history, setHistory] = useState<{ role: "user" | "agent"; text: string }[]>([
    { role: "agent", text: "Привет! Я AI-агент. Скажи, какую тренировку и когда хотите — я сам найду клуб, проверю слоты и календарь и забронирую." },
  ]);
  const [busy, setBusy] = useState(false);

  function submit(msg?: string) {
    const value = (msg ?? text).trim();
    if (!value || busy) return;
    setHistory((h) => [...h, { role: "user", text: value }]);
    setText("");
    setBusy(true);
    onSend(value);
    // busy снимем по событию done/error — но у нас нет onStatusChange,
    // поэтому отслеживаем через setTimeout по eventsCount — упрощённо:
    setTimeout(() => setBusy(false), 300);
  }

  // Подтягиваем финальный текст агента в историю
  if (finalText && history[history.length - 1]?.text !== finalText && history[history.length - 1]?.role !== "agent") {
    setHistory((h) => [...h, { role: "agent", text: finalText }]);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontWeight: 600, fontSize: 16 }}>Чат с агентом</div>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
          шагов: {eventsCount} · статус: <span style={{ color: statusColor, fontWeight: 600 }}>{statusLabel}</span>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        {history.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "85%",
              background: m.role === "user" ? "var(--accent)" : "var(--bg)",
              color: m.role === "user" ? "white" : "var(--text)",
              padding: "8px 12px",
              borderRadius: 10,
              boxShadow: "var(--shadow)",
            }}
          >
            {m.text}
          </div>
        ))}
      </div>

      <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => submit(s)} style={{ fontSize: 12, padding: "4px 8px" }} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          style={{ display: "flex", gap: 6 }}
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Например: хочу теннис в среду вечером"
            disabled={busy}
          />
          <button type="submit" className="primary" disabled={busy || !text.trim()}>
            →
          </button>
        </form>
      </div>
    </div>
  );
}
