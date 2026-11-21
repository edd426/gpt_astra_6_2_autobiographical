"use strict";

const key = document.querySelector("#key");
const listen = document.querySelector("#listen");
const reset = document.querySelector("#reset");
const save = document.querySelector("#save");
const staff = document.querySelector("#staff");
const part = document.querySelector("#part");
const cue = document.querySelector("#cue");
const count = document.querySelector("#count");
const caption = document.querySelector("#caption");
const message = document.querySelector("#message");
const label = document.querySelector("#key-label");

const takes = { pluck: [], bow: [] };
let mode = "pluck";
let strings = null;
let epoch = null;
let gestureEpoch = null;
let hiddenAt = null;
let held = null;
let animation = 0;
let lastPhysicalRelease = -Infinity;
const playable = () => mode === "pluck" || mode === "bow";
const totalTime = () => Math.max(takeLength(takes.pluck), takeLength(takes.bow));

function duration(s) {
  if (s < 0.1) return "less than a tenth of a second";
  const n = Number(s.toFixed(1));
  return `${n} ${n === 1 ? "second" : "seconds"}`;
}

function meeting() {
  const { start, end } = sharedD(takes);
  if (end > start) return `Your two holds on D overlapped for ${duration(end - start)}.`;
  if (Math.abs(end - start) < 0.025) return "One hand arrived on D just as the other lifted.";
  const later = takes.bow[5].t > takes.pluck[5].t ? "bow" : "pluck";
  return `The ${later} reached D ${duration(start - end)} after the other hand lifted.`;
}

function paint() {
  animation = 0;
  let elapsed = null;
  if (epoch !== null) {
    elapsed = playable() ? (performance.now() - gestureEpoch) / 1000
      : Math.max(0, strings.context.currentTime - epoch);
  }
  if ((mode === "tail" || mode === "replay") && elapsed >= totalTime() + 0.42) {
    mode = "done";
    epoch = null;
    update();
    return;
  }
  drawPaper(staff, takes, mode, elapsed, Boolean(held));
  if (epoch !== null && !document.hidden) requestPaint();
}

function requestPaint() {
  if (!animation) animation = requestAnimationFrame(paint);
}

function update() {
  const playing = playable();
  document.querySelector(".instrument").className = "instrument " + (playing ? mode : "both");
  key.hidden = !playing;
  listen.hidden = playing;
  save.hidden = playing;
  document.querySelector("#sill").hidden = playing;
  reset.hidden = !takes.pluck.length;
  reset.textContent = playing ? "Start over" : "New duet";
  key.classList.toggle("down", Boolean(held));
  key.setAttribute("aria-pressed", String(Boolean(held)));

  if (playing) {
    const n = takes[mode].length - (held ? 1 : 0);
    const pitch = chairBank.parts[mode][n].pitch;
    const plucking = mode === "pluck";
    part.textContent = plucking ? "Plucked string" : "Bowed string";
    if (n === 5) {
      cue.textContent = plucking
        ? "Here is the D at the crease. Hold it for your own count of six."
        : "Here is D again. Let the bow lift when you want the note to end.";
    } else {
      cue.textContent = plucking
        ? "Hold and release the button or the space bar six times. Take as long as you like on each note."
        : "Begin with the same key. Your plucked part will play back as you draw the six bow strokes.";
    }
    label.textContent = (held ? "Release " : plucking ? "Pluck " : "Bow ") + pitch;
    count.textContent = `Note ${n + 1} of 6`;
    caption.textContent = plucking
      ? "Your first take will play across from you when you begin the bow."
      : "The green marks keep the time of your earlier hand.";
    message.textContent = `${part.textContent}. ${count.textContent}. ${label.textContent}.`;
  } else {
    part.textContent = "Both chairs";
    cue.textContent = meeting();
    const p = duration(takes.pluck[5].d), b = duration(takes.bow[5].d);
    caption.textContent = `At the table, your first hand held D for ${p}. Your second held it for ${b}.`;
    listen.textContent = mode === "done" ? "Hear the duet" : "Stop listening";
    count.textContent = mode === "done" ? duration(totalTime()) : "Listening";
    message.textContent = mode === "replay" ? "Playing both takes." : cue.textContent;
  }
  staff.setAttribute("aria-label", playing
    ? `A score for two strings. ${part.textContent}, ${count.textContent}.`
    : `Your two performed phrases. ${cue.textContent} ${caption.textContent}`);
  requestPaint();
}

function restart() {
  strings?.silence();
  takes.pluck.length = 0;
  takes.bow.length = 0;
  epoch = gestureEpoch = held = null;
  mode = "pluck";
  update();
}

function soundFailure() {
  restart();
  cue.textContent = "Sound could not start. Press the key again, or open this page in a browser with Web Audio.";
  message.textContent = cue.textContent;
}

function wakeStrings() {
  try {
    if (!strings) strings = new TableStrings();
    if (strings.context.state !== "running") strings.context.resume().catch(soundFailure);
    return true;
  } catch {
    soundFailure();
    return false;
  }
}

function press(input) {
  if (held || !playable() || !wakeStrings()) return;
  const down = performance.now();
  const at = strings.context.currentTime + 0.008;
  const notes = takes[mode];
  const scoreNote = chairBank.parts[mode][notes.length];
  if (!notes.length) {
    epoch = at;
    gestureEpoch = down;
    if (mode === "bow") strings.perform("pluck", takes.pluck, epoch);
  }
  const note = { midi: scoreNote.midi, t: (down - gestureEpoch) / 1000, d: null };
  notes.push(note);
  held = { input, note, at, wall: down, sound: strings.note(mode, note.midi, at) };
  update();
}

function release(input) {
  if (!held || held.input !== input) return;
  // Keep finger time even if the sound device is still waking up, or its
  // clock advances in blocks longer than a very short tap.
  held.note.d = Math.max(0.001, (performance.now() - held.wall) / 1000);
  held.sound.release(held.at + held.note.d);
  held = null;
  if (input !== "activation") lastPhysicalRelease = performance.now();
  if (takes[mode].length === 6) {
    if (mode === "pluck") {
      mode = "bow";
      epoch = gestureEpoch = null;
    } else {
      mode = "tail";
    }
  }
  update();
  if (!playable() && document.activeElement === document.body) listen.focus({ preventScroll: true });
}

function toggleListening() {
  if (playable()) return;
  if (mode === "done") {
    if (!wakeStrings()) return;
    mode = "replay";
    epoch = strings.context.currentTime + 0.035;
    for (const voice of ["pluck", "bow"]) strings.perform(voice, takes[voice], epoch);
  } else {
    strings.silence();
    mode = "done";
    epoch = null;
  }
  update();
}

key.addEventListener("pointerdown", event => {
  if (event.button !== 0 || !event.isPrimary || held) return;
  event.preventDefault();
  key.focus({ preventScroll: true });
  key.setPointerCapture(event.pointerId);
  press(event.pointerId);
});
for (const kind of ["pointerup", "pointercancel", "lostpointercapture"]) {
  key.addEventListener(kind, event => release(event.pointerId));
}
key.addEventListener("contextmenu", event => event.preventDefault());
// Assistive activation without a down/up pair works as a press, then a lift.
key.addEventListener("click", event => {
  if (event.detail || performance.now() - lastPhysicalRelease < 100 || !playable()) return;
  if (held?.input === "activation") release("activation");
  else press("activation");
});

document.addEventListener("keydown", event => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const target = event.target;
  if (target.closest?.("a, button, input, select, textarea, [contenteditable=true]") && target !== key) return;
  if (event.code !== "Space" && !(event.key === "Enter" && target === key)) return;
  event.preventDefault();
  if (event.repeat) return;
  if (playable()) press(event.code);
  else toggleListening();
});
document.addEventListener("keyup", event => {
  if (held?.input !== event.code) return;
  event.preventDefault();
  release(event.code);
});
window.addEventListener("blur", () => { if (held) release(held.input); });
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    if (held) release(held.input);
    hiddenAt = performance.now();
    strings?.context.suspend().catch(() => {});
  } else {
    if (hiddenAt !== null && gestureEpoch !== null) gestureEpoch += performance.now() - hiddenAt;
    hiddenAt = null;
    if (strings && epoch !== null) strings.context.resume().catch(soundFailure);
    requestPaint();
  }
});
listen.addEventListener("click", toggleListening);
reset.addEventListener("click", () => {
  restart();
  key.focus({ preventScroll: true });
});
save.addEventListener("click", () => savePerformance(takes));
new ResizeObserver(requestPaint).observe(staff);
update();
