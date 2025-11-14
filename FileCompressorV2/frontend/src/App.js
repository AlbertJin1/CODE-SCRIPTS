// frontend/src/App.js
import { useState, useRef, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  // ----- state -------------------------------------------------
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("percent"); // "percent" | "size"
  const [percent, setPercent] = useState(75);
  const [targetMb, setTargetMb] = useState(2);
  const [status, setStatus] = useState("Waiting for server…");
  const [progress, setProgress] = useState(0);
  const [ready, setReady] = useState(false);
  const fileInputRef = useRef(null);

  // ----- 1. Health-check (poll /health) -----------------------
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      for (let i = 0; i < 30; i++) {
        if (cancelled) break;
        try {
          const r = await fetch(`${API_BASE}/health`, { cache: "no-store" });
          if (r.ok) {
            setReady(true);
            setStatus("Ready");
            return;
          }
        } catch {
          // ignore – just retry
        }
        await new Promise((res) => setTimeout(res, 500));
      }
      if (!cancelled) {
        setStatus("Server not responding");
      }
    };
    check();
    return () => {
      cancelled = true;
    };
  }, []);

  // ----- 2. Compression ---------------------------------------
  const startCompress = async () => {
    if (!file || !ready) return;

    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);
    form.append("percent", String(percent));
    form.append("target_mb", String(targetMb));

    setStatus("Uploading…");
    setProgress(0);

    try {
      const resp = await fetch(`${API_BASE}/compress`, {
        method: "POST",
        body: form,
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      // resp.body may be null in very old browsers – guard it
      if (!resp.body) throw new Error("No response body");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line) continue;
          let data;
          try {
            data = JSON.parse(line);
          } catch {
            continue;
          }

          if (data.progress !== undefined) setProgress(data.progress);
          if (data.status) setStatus(data.status);
          if (data.download) {
            const a = document.createElement("a");
            a.href = data.download;
            a.download = data.filename ?? "compressed";
            a.click();
            setStatus("Done!");
            setProgress(100);
            return;
          }
        }
        if (done) break;
      }
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    }
  };

  // ----- UI ---------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl space-y-8">
        <h1 className="text-4xl font-bold text-center text-cyan-400">
          CompressMaster
        </h1>

        {/* hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.xlsx,.jpg,.jpeg,.png,.webp,.bmp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />

        {/* browse button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 rounded-lg font-semibold"
        >
          {file ? file.name : "Browse…"}
        </button>

        {/* mode selector */}
        <div className="flex gap-4">
          <label className="flex items-center">
            <input
              type="radio"
              name="mode"
              checked={mode === "percent"}
              onChange={() => setMode("percent")}
              className="mr-2"
            />
            By %
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="mode"
              checked={mode === "size"}
              onChange={() => setMode("size")}
              className="mr-2"
            />
            Target MB
          </label>
        </div>

        {/* percent / target controls */}
        {mode === "percent" ? (
          <input
            type="range"
            min="10"
            max="95"
            value={percent}
            onChange={(e) => setPercent(Number(e.target.value))}
            className="w-full"
          />
        ) : (
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={targetMb}
            onChange={(e) => setTargetMb(Number(e.target.value))}
            className="w-full p-2 bg-gray-800 rounded"
          />
        )}

        {/* compress button */}
        <button
          onClick={startCompress}
          disabled={!file || !ready}
          className="w-full py-3 bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-lg font-semibold"
        >
          Compress
        </button>

        {/* progress bar */}
        <div className="relative h-6 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="absolute h-full bg-green-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="text-center">{status}</p>

        <footer className="text-center text-xs text-gray-500">
          PDF • DOCX • XLSX • JPG • PNG • WebP
        </footer>
      </div>
    </div>
  );
}