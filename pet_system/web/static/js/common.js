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
