import { useEffect, useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";

type Ev = {
  event_id: string;
  title: string;
  start: string;
  end: string;
  location: string;
  description: string;
  source: string;
};

export default function CalendarTab({ highlightRunId: _ }: { highlightRunId: string | null }) {
  const [events, setEvents] = useState<Ev[]>([]);
  const [loading, setLoading] = useState(true);
  const calRef = useRef<FullCalendar | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const r = await fetch("/api/agent/state?run_id=" + (window.localStorage.getItem("last_run_id") || "noop"));
      if (!r.ok) throw new Error("no state");
      const data = await r.json();
      // В календарь попадают события из calendar_mcp.list_events, но мы
      // берём их проще — из последнего шага с result.events, если есть.
      // Надёжнее: пробежаться по всем шагам observation/list_events.
      // Но простой способ: рефреш через прямой запрос — добавим endpoint позже.
    } catch {
      /* ignore */
    }
    setLoading(false);
  }

  // Надёжный путь: подтянуть события напрямую из state через свой endpoint
  useEffect(() => {
    fetch("/api/calendar/events")
      .then((r) => (r.ok ? r.json() : { events: [] }))
      .then((d) => setEvents(d.events || []))
      .finally(() => setLoading(false));
  }, []);

  const fcEvents = events.map((e) => ({
    id: e.event_id,
    title: `${e.title}${e.location ? " · " + e.location : ""}`,
    start: e.start,
    end: e.end,
    backgroundColor: e.source === "agent" ? "#2563eb" : "#94a3b8",
    borderColor: e.source === "agent" ? "#2563eb" : "#94a3b8",
  }));

  return (
    <div style={{ background: "var(--panel)", padding: 12, borderRadius: 8, border: "1px solid var(--border)", boxShadow: "var(--shadow)" }}>
      {loading ? (
        <div style={{ color: "var(--text-muted)" }}>Загрузка…</div>
      ) : (
        <FullCalendar
          ref={calRef}
          plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{ left: "prev,next today", center: "title", right: "timeGridDay,timeGridWeek,dayGridMonth" }}
          locale="ru"
          firstDay={1}
          slotMinTime="06:00:00"
          slotMaxTime="23:00:00"
          height="auto"
          events={fcEvents}
          eventClick={(info) => {
            const ev = events.find((e) => e.event_id === info.event.id);
            if (!ev) return;
            alert(`${ev.title}\n${new Date(ev.start).toLocaleString("ru")} – ${new Date(ev.end).toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })}\n${ev.location}\n\n${ev.description}`);
          }}
        />
      )}
    </div>
  );
}
