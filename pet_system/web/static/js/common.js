// 通用工具：fetch 封装、提示、音效、彩带
window.Pet = {
  async api(url, opts) {
    const r = await fetch(url, Object.assign({headers: {'Content-Type': 'application/json'}}, opts || {}));
    const j = await r.json();
    if (!j.ok && j.code === 'NO_AUTH') { location.href = '/child/login'; }
    return j;
  },
  post(url, data) {
    return this.api(url, {method: 'POST', body: JSON.stringify(data || {})});
  },
  toast(msg, bad) {
    let el = document.getElementById('toast');
    if (!el) { el = document.createElement('div'); el.id = 'toast'; document.body.appendChild(el); }
    el.textContent = msg || '';
    el.style.cssText = 'position:fixed;left:50%;bottom:40px;transform:translateX(-50%);' +
      'background:' + (bad ? '#E53E3E' : '#2F855A') + ';color:#fff;font-size:22px;font-weight:700;' +
      'padding:16px 30px;border-radius:18px;z-index:100;box-shadow:0 6px 20px rgba(0,0,0,.2);' +
      'transition:opacity .3s;opacity:1;max-width:90%;text-align:center';
    clearTimeout(this._tt);
    this._tt = setTimeout(() => { el.style.opacity = '0'; }, 2200);
  },
  sound(name) {
    try {
      const a = new Audio('/static/audio/' + name + '.wav');
      a.volume = 0.6; a.play();
    } catch (e) {}
  },
  // 每种怪兽用档案里的 waveform + 音阶现场合成叫声，无需为每个新物种准备音频文件
  creatureSound(voice, mood) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!this._actx) this._actx = new AudioCtx();
      const ctx = this._actx;
      if (ctx.state === 'suspended') ctx.resume();
      let notes = (voice && voice.notes && voice.notes.length) ? voice.notes.slice() : [523, 659];
      if (mood === 'hello') notes = [notes[0], notes[0], notes[notes.length - 1]];
      const step = Math.max(0.06, (voice && voice.step) || 0.12);
      const peak = Math.min(0.18, (voice && voice.gain) || 0.1);
      const t0 = ctx.currentTime + 0.01;
      notes.forEach((freq, i) => {
        if (!freq) return;
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        const at = t0 + i * step;
        osc.type = (voice && voice.wave) || 'sine';
        osc.frequency.setValueAtTime(freq, at);
        if (mood === 'hello') {
          osc.frequency.exponentialRampToValueAtTime(freq * 1.12, at + step * 0.7);
        }
        g.gain.setValueAtTime(0.0001, at);
        g.gain.exponentialRampToValueAtTime(peak, at + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, at + step * 0.9);
        osc.connect(g);
        g.connect(ctx.destination);
        osc.start(at);
        osc.stop(at + step);
      });
    } catch (e) {}
  },
  confetti() {
    const colors = ['#FF6384','#36A2EB','#FFCE56','#4BC0C0','#9966FF'];
    for (let i = 0; i < 30; i++) {
      const c = document.createElement('div');
      c.className = 'confetti';
      c.textContent = '★';
      c.style.left = (Math.random() * 100) + 'vw';
      c.style.top = (Math.random() * 20) + 'vh';
      c.style.color = colors[i % colors.length];
      c.style.animationDelay = (Math.random() * 0.4) + 's';
      document.body.appendChild(c);
      setTimeout(() => c.remove(), 2400);
    }
  },
  uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
};
