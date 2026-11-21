"use strict";

class TableStrings {
  constructor() {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) throw new Error("This instrument needs a browser with Web Audio.");
    this.context = new Audio({ latencyHint: "interactive" });
    this.sources = new Set();
    this.buffers = {};
    this.seats = {};
    const ctx = this.context;
    const master = ctx.createGain();
    master.gain.value = 0.83;
    master.connect(ctx.destination);

    // A small room shared by the live hand and the hand that played earlier.
    const reverb = ctx.createConvolver();
    const impulse = ctx.createBuffer(2, Math.round(ctx.sampleRate * 0.86), ctx.sampleRate);
    let seed = 91;
    for (let ch = 0; ch < 2; ch++) {
      const h = impulse.getChannelData(ch);
      let soft = 0;
      for (let i = 0; i < h.length; i++) {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        soft = 0.70 * soft + 0.30 * (seed / 2147483648 - 1);
        const t = i / ctx.sampleRate;
        h[i] = soft * 0.0085 * Math.exp(-8.0 * t) * (1 - Math.exp(-40 * t));
      }
      h[Math.round(ctx.sampleRate * (0.021 + ch * 0.009))] += 0.086;
      h[Math.round(ctx.sampleRate * (0.048 - ch * 0.006))] -= 0.040;
    }
    reverb.normalize = false;
    reverb.buffer = impulse;
    reverb.connect(master);

    for (const voice of ["pluck", "bow"]) {
      const bytes = atob(chairBank.strings[voice]);
      const buffer = ctx.createBuffer(1, bytes.length / 2, chairBank.rate);
      const samples = buffer.getChannelData(0);
      for (let i = 0; i < samples.length; i++) {
        const word = bytes.charCodeAt(2 * i) | (bytes.charCodeAt(2 * i + 1) << 8);
        samples[i] = (word < 32768 ? word : word - 65536) / 32768;
      }
      this.buffers[voice] = buffer;
      const seat = ctx.createStereoPanner();
      seat.pan.value = voice === "pluck" ? -0.46 : 0.46;
      seat.connect(master);
      seat.connect(reverb);
      this.seats[voice] = seat;
    }
  }

  note(voice, midi, when) {
    const ctx = this.context;
    const source = ctx.createBufferSource();
    source.buffer = this.buffers[voice];
    source.playbackRate.value = 2 ** ((midi - chairBank.root) / 12);
    if (voice === "bow") {
      source.loop = true;
      source.loopStart = chairBank.loopIn / chairBank.rate;
      source.loopEnd = chairBank.loopOut / chairBank.rate;
    }
    const gate = ctx.createGain();
    source.connect(gate);
    gate.connect(this.seats[voice]);
    let ended = false;
    const handle = {
      release(at) {
        if (ended) return;
        const end = at + (voice === "bow" ? 0.36 : 0.24);
        gate.gain.setValueAtTime(1, at);
        gate.gain.exponentialRampToValueAtTime(0.0002, end);
        source.stop(end + 0.01);
      },
      stop() {
        const t = ctx.currentTime;
        gate.gain.cancelScheduledValues(t);
        gate.gain.setTargetAtTime(0, t, 0.008);
        source.stop(t + 0.05);
      },
    };
    this.sources.add(handle);
    source.onended = () => {
      ended = true;
      this.sources.delete(handle);
      source.disconnect();
      gate.disconnect();
    };
    source.start(when);
    return handle;
  }

  perform(voice, notes, start) {
    for (const n of notes) {
      const at = start + n.t;
      this.note(voice, n.midi, at).release(at + n.d);
    }
  }

  silence() {
    for (const handle of this.sources) handle.stop();
  }
}

function savePerformance(takes) {
  // A quarter lasts a second. One MIDI tick can keep a millisecond of touch.
  function variable(value) {
    const bytes = [value % 128];
    for (value = Math.floor(value / 128); value; value = Math.floor(value / 128)) {
      bytes.unshift(128 | (value % 128));
    }
    return bytes;
  }

  const bytes = [77, 84, 104, 100, 0, 0, 0, 6, 0, 1, 0, 2, 3, 232];
  for (const [channel, voice] of ["pluck", "bow"].entries()) {
    const name = voice === "pluck" ? "Plucked string" : "Bowed string";
    const track = [0, 255, 3, name.length, ...new TextEncoder().encode(name)];
    if (!channel) track.push(0, 255, 81, 3, 15, 66, 64);
    track.push(0, 192 + channel, channel ? 41 : 24, 0, 176 + channel, 10, channel ? 90 : 37);
    const events = [];
    for (const n of takes[voice]) {
      const start = Math.round(n.t * 1000);
      const end = Math.max(start + 1, Math.round((n.t + n.d) * 1000));
      events.push([start, 144 + channel, n.midi, 77], [end, 128 + channel, n.midi, 0]);
    }
    events.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    let previous = 0;
    for (const [t, status, pitch, velocity] of events) {
      track.push(...variable(t - previous), status, pitch, velocity);
      previous = t;
    }
    track.push(0, 255, 47, 0);
    const size = track.length;
    bytes.push(77, 84, 114, 107, size >>> 24, (size >>> 16) & 255,
      (size >>> 8) & 255, size & 255, ...track);
  }
  const url = URL.createObjectURL(new Blob([Uint8Array.from(bytes)], { type: "audio/midi" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "the-other-chair.mid";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
