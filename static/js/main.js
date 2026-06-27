/* ============================================================
   SENTINEL — main.js
   ============================================================ */

// ── HEADER scroll state ──────────────────────────────────────
const header = document.getElementById('header');
window.addEventListener('scroll', () => {
  header.classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

// ── BURGER MENU ──────────────────────────────────────────────
const burger = document.getElementById('burger');
const nav    = document.getElementById('nav');

burger.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  burger.setAttribute('aria-expanded', open);
});

// Close nav on link click (mobile)
document.querySelectorAll('.nav__link').forEach(link => {
  link.addEventListener('click', () => nav.classList.remove('open'));
});

// ── TERMINAL TYPEWRITER ──────────────────────────────────────
const terminalBody = document.getElementById('terminal-body');
const typedText    = document.getElementById('typed-text');

const sequences = [
  {
    command: 'sentinel --scan --full',
    outputs: [
      { cls: 'info',   text: '[ Inicializando varredura do sistema... ]' },
      { cls: 'ok',     text: '✔  CPU: 23% uso — Normal' },
      { cls: 'ok',     text: '✔  RAM: 4.2 GB / 16 GB — Saudável' },
      { cls: 'ok',     text: '✔  Disco: 340 GB livres — OK' },
      { cls: 'warn',   text: '⚠  Processo suspeito detectado: pid 4821' },
      { cls: 'threat', text: '✘  Ameaça bloqueada: Trojan.GenericKD.72' },
      { cls: 'ok',     text: '✔  Sistema protegido — 1 ameaça neutralizada' },
    ]
  },
  {
    command: 'sentinel --network --monitor',
    outputs: [
      { cls: 'info',   text: '[ Analisando tráfego de rede... ]' },
      { cls: 'ok',     text: '✔  Conexões ativas: 14 — Verificadas' },
      { cls: 'warn',   text: '⚠  IP externo suspeito: 192.168.x.x' },
      { cls: 'threat', text: '✘  Tentativa de intrusão bloqueada' },
      { cls: 'ok',     text: '✔  Firewall ativo — Regras atualizadas' },
    ]
  }
];

let seqIdx  = 0;
let outLines = [];

function typeText(text, el, speed, cb) {
  let i = 0;
  el.textContent = '';
  const iv = setInterval(() => {
    el.textContent += text[i++];
    if (i >= text.length) { clearInterval(iv); if (cb) setTimeout(cb, 400); }
  }, speed);
}

function showOutput(outputs, idx, cb) {
  if (idx >= outputs.length) { if (cb) setTimeout(cb, 1200); return; }
  const line = document.createElement('div');
  line.className = `terminal__output`;
  const inner = document.createElement('span');
  inner.className = outputs[idx].cls;
  inner.textContent = outputs[idx].text;
  line.appendChild(inner);
  terminalBody.appendChild(line);
  outLines.push(line);
  setTimeout(() => showOutput(outputs, idx + 1, cb), 280);
}

function runSequence() {
  // Clear previous outputs
  outLines.forEach(l => l.remove());
  outLines = [];

  const seq = sequences[seqIdx % sequences.length];
  typeText(seq.command, typedText, 55, () => {
    showOutput(seq.outputs, 0, () => {
      seqIdx++;
      setTimeout(runSequence, 2600);
    });
  });
}

// Start after a short delay
setTimeout(runSequence, 800);

// ── COUNTER ANIMATION ─────────────────────────────────────────
function animateCounter(el, target, decimals, duration) {
  const start = performance.now();
  const step = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = (target * ease).toFixed(decimals);
    el.textContent = val;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── INTERSECTION OBSERVER — reveal + counters ─────────────────
const revealEls = document.querySelectorAll(
  '.card, .portfolio__card, .sobre__grid, .contato__grid, .hero__stats'
);

revealEls.forEach(el => el.classList.add('reveal'));

const counterEls = document.querySelectorAll('.stat__num');
let countersStarted = false;

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

revealEls.forEach(el => observer.observe(el));

// Counters triggered when stats section enters view
const statsSection = document.querySelector('.hero__stats');
if (statsSection) {
  const statsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !countersStarted) {
      countersStarted = true;
      counterEls.forEach(el => {
        const target = parseFloat(el.dataset.target);
        const decimals = target % 1 !== 0 ? 1 : 0;
        animateCounter(el, target, decimals, 1600);
      });
      statsObserver.disconnect();
    }
  }, { threshold: 0.5 });
  statsObserver.observe(statsSection);
}

// ── CONTACT FORM ──────────────────────────────────────────────
const form        = document.getElementById('contact-form');
const feedback    = document.getElementById('form-feedback');
const submitBtn   = document.getElementById('submit-btn');
const btnText     = submitBtn?.querySelector('.btn__text');
const btnLoading  = submitBtn?.querySelector('.btn__loading');

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    feedback.textContent = '';
    feedback.className   = 'form__feedback';

    const name    = document.getElementById('name').value.trim();
    const email   = document.getElementById('email').value.trim();
    const message = document.getElementById('message').value.trim();

    if (!name || !email || !message) {
      feedback.textContent = 'Por favor, preencha todos os campos.';
      feedback.classList.add('error');
      return;
    }

    // Loading state
    btnText.hidden    = true;
    btnLoading.hidden = false;
    submitBtn.disabled = true;

    try {
      const res  = await fetch('/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, message })
      });
      const data = await res.json();

      if (data.success) {
        feedback.textContent = data.message;
        feedback.classList.add('success');
        form.reset();
      } else {
        throw new Error(data.error || 'Erro ao enviar.');
      }
    } catch (err) {
      feedback.textContent = err.message || 'Erro inesperado. Tente novamente.';
      feedback.classList.add('error');
    } finally {
      btnText.hidden    = false;
      btnLoading.hidden = true;
      submitBtn.disabled = false;
    }
  });
}