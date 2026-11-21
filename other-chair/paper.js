"use strict";

function sharedD(takes) {
  const p = takes.pluck[5];
  const b = takes.bow[5];
  if (!p || !b || p.d == null || b.d == null) return null;
  return { start: Math.max(p.t, b.t), end: Math.min(p.t + p.d, b.t + b.d) };
}

function takeLength(notes) {
  const last = notes[notes.length - 1];
  return last ? last.t + (last.d || 0) : 0;
}

function drawPaper(canvas, takes, mode, elapsed, keyDown) {
  const g = canvas.getContext("2d");
  const width = canvas.clientWidth, height = canvas.clientHeight;
  const ratio = Math.min(3, window.devicePixelRatio || 1);
  if (!width || !height) return;
  if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
  }
  g.setTransform(ratio, 0, 0, ratio, 0, 0);
  g.clearRect(0, 0, width, height);
  const left = width < 500 ? 54 : 83, right = width - 10;
  const ground = height - 24;
  const occupied = takes.pluck.length > 0;
  const running = elapsed != null;
  const longest = Math.max(takeLength(takes.pluck), takeLength(takes.bow), elapsed || 0);
  let span = Math.max(0.05, longest * 1.035);
  if (mode === "pluck" || mode === "bow") span = Math.max(8, Math.ceil((longest + 0.3) / 2) * 2);
  const x = seconds => left + (right - left) * seconds / span;
  const both = sharedD(takes);
  if (both && both.end > both.start) {
    g.fillStyle = "#943a2612";
    g.fillRect(x(both.start), 3, x(both.end) - x(both.start), ground - 6);
  }
  const serif = '"STIX Two Text", "Iowan Old Style", Georgia, serif';
  for (const [i, voice] of ["pluck", "bow"].entries()) {
    const centre = ground * (i ? 0.75 : 0.25);
    const position = midi => centre - (midi - 62) * ground * 0.017;
    const ink = voice === "pluck" ? "#2d584f" : "#943a26";
    const notes = takes[voice];
    g.fillStyle = ink;
    g.font = `italic ${width < 500 ? 17 : 21}px ${serif}`;
    g.textAlign = "left";
    g.textBaseline = "middle";
    g.fillText(voice === "pluck" ? "Pluck" : "Bow", 0, centre);
    g.lineWidth = 1;
    for (const pitch of [57, 60, 62, 65, 69]) {
      const y = Math.round(position(pitch)) + 0.5;
      g.strokeStyle = pitch === 62 ? "#bbb9a3" : "#dedccd";
      g.beginPath();
      g.moveTo(left, y);
      g.lineTo(right, y);
      g.stroke();
    }
    const guide = !notes.length;
    const marks = guide ? chairBank.parts[voice] : notes;
    for (const n of marks) {
      const y = position(n.midi);
      const t = guide ? n.beat / 15 * span : n.t;
      const d = guide ? n.length / 15 * span : (n.d ?? Math.max(0, (elapsed || 0) - n.t));
      const x1 = x(t), x2 = Math.min(right, Math.max(x1 + 3, x(t + d)));
      g.beginPath();
      g.roundRect(x1 + 0.5, y - 3.5, Math.max(2, x2 - x1 - 1), 7, 2.5);
      g.fillStyle = guide ? "#f7f4ea" : ink;
      g.fill();
      if (guide) {
        g.strokeStyle = voice === "pluck" ? "#80958a" : "#b48a79";
        g.stroke();
      }
      const stillHeld = n.d == null && keyDown && voice === mode;
      if (!guide && running && elapsed >= t && (elapsed < t + d || stillHeld)) {
        g.beginPath();
        g.arc(x(elapsed), y, 5, 0, 2 * Math.PI);
        g.fillStyle = ink;
        g.fill();
      }
    }
  }
  if (!occupied) return;
  if (running) {
    const pen = Math.min(right, x(elapsed));
    g.strokeStyle = "#777763";
    g.beginPath(); g.moveTo(pen, 2); g.lineTo(pen, ground); g.stroke();
    g.fillStyle = "#656750";
    g.beginPath(); g.moveTo(pen, 8); g.lineTo(pen - 3, 2); g.lineTo(pen + 3, 2); g.fill();
  }
  g.font = `14px ${serif}`;
  g.fillStyle = "#636553";
  g.textAlign = "left"; g.fillText("0 s", left, height - 7);
  g.textAlign = "right"; g.fillText(`${Number(span.toFixed(span < 1 ? 2 : 1))} s`, right, height - 7);
}
