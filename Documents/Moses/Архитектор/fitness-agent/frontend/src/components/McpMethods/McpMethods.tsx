import { useEffect, useState } from "react";
import { getToolsRegistry, ToolsRegistry } from "../../api";

export default function McpMethods() {
  const [reg, setReg] = useState<ToolsRegistry | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getToolsRegistry()
      .then(setReg)
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div style={{ color: "var(--err)" }}>Ошибка загрузки: {err}</div>;
  if (!reg) return <div style={{ color: "var(--text-muted)" }}>Загрузка…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {reg.servers.map((s) => {
        const isOpen = open[s.server] ?? true;
        return (
          <div key={s.server} style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, boxShadow: "var(--shadow)" }}>
            <div
              onClick={() => setOpen((o) => ({ ...o, [s.server]: !isOpen }))}
              style={{ padding: "10px 14px", cursor: "pointer", display: "flex", alignItems: "center", gap: 10 }}
            >
              <span style={{ fontWeight: 600 }}>{s.label}</span>
              <code style={{ fontSize: 12, color: "var(--text-muted)" }}>{s.server}</code>
              <div style={{ flex: 1 }} />
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{s.tools.length} tools · {s.url}</span>
            </div>
            {isOpen && (
              <div style={{ padding: "0 14px 12px" }}>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>{s.description}</div>
                {s.tools.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", fontSize: 13 }}>(нет доступных tools)</div>
                ) : (
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                    {s.tools.map((t) => (
                      <li key={t.name} style={{ borderLeft: "2px solid var(--accent-soft)", paddingLeft: 10 }}>
                        <div style={{ fontFamily: "ui-monospace, monospace", fontWeight: 600 }}>{t.name}</div>
                        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{t.description}</div>
                        <pre
                          style={{
                            background: "var(--code-bg)",
                            color: "var(--code-text)",
                            padding: 8,
                            borderRadius: 6,
                            marginTop: 4,
                            fontSize: 11,
                            maxHeight: 160,
                            overflow: "auto",
                          }}
                        >
                          {JSON.stringify(t.input_schema, null, 2)}
                        </pre>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
