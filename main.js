/* ============================================================
   UpWeb Gestão de Sinistros — main.js (vanilla)
   ============================================================ */
(function () {
  'use strict';

  /* Número oficial de atendimento (só dígitos, com DDI 55) */
  var WHATSAPP_NUMBER = '5562991790021';
  var WHATSAPP_TEXT = 'Olá, quero agendar uma demonstração da UpWeb Gestão de Sinistros.';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* 1. Header scroll ------------------------------------------------ */
  var header = $('[data-header]');
  function onScrollHeader() {
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 24);
  }

  /* 2. Mobile menu -------------------------------------------------- */
  var toggle = $('.menu-toggle');
  var menu = $('#primary-menu');
  if (toggle && menu) {
    var setMenu = function (open) {
      menu.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    };
    toggle.addEventListener('click', function () {
      setMenu(toggle.getAttribute('aria-expanded') !== 'true');
    });
    $$('a', menu).forEach(function (a) {
      a.addEventListener('click', function () { setMenu(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) {
        setMenu(false); toggle.focus();
      }
    });
  }

  /* 3/4. Reveal geral (IntersectionObserver) ------------------------ */
  var reveals = $$('.reveal');
  if (prefersReduced || !('IntersectionObserver' in window)) {
    reveals.forEach(function (el) { el.classList.add('is-inview'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-inview');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  }

  /* 5. Marquee respeita reduced-motion ------------------------------ */
  if (prefersReduced) {
    $$('[data-marquee]').forEach(function (m) { m.setAttribute('data-paused', ''); });
  }

  /* 6. Fallback de vídeo do hero ------------------------------------ */
  var heroVideo = $('[data-hero-video]');
  if (heroVideo) {
    var applyPosterFallback = function () {
      var hero = heroVideo.closest('.hero');
      if (hero) {
        hero.style.backgroundImage = "url('assets/hero-poster.jpg')";
        hero.style.backgroundSize = 'cover';
        hero.style.backgroundPosition = '78% center';
      }
      heroVideo.style.display = 'none';
    };
    heroVideo.addEventListener('error', applyPosterFallback, true);
    if (prefersReduced && heroVideo.pause) { heroVideo.pause(); }
  }

  /* 7/8. WhatsApp float + Mobile bar -------------------------------- */
  var waFloat = $('.whatsapp-float');
  var mobileBar = $('.mobile-bar');
  function onScrollFixed() {
    if (waFloat) waFloat.classList.toggle('is-visible', window.scrollY > 400);
    if (mobileBar) mobileBar.classList.toggle('is-visible', window.scrollY > 100);
  }

  /* Scroll listener único (passivo) --------------------------------- */
  window.addEventListener('scroll', function () {
    onScrollHeader();
    onScrollFixed();
  }, { passive: true });
  onScrollHeader();
  onScrollFixed();

  /* 9. Validação do formulário -------------------------------------- */
  var form = $('[data-lead-form]');
  if (form) {
    var msg = $('[data-form-message]', form);
    var showError = function (field, text) {
      field.setAttribute('aria-invalid', 'true');
      var holder = field.closest('label');
      var slot = holder && holder.querySelector('[data-error]');
      if (slot) slot.textContent = text;
    };
    var clearError = function (field) {
      field.removeAttribute('aria-invalid');
      var holder = field.closest('label');
      var slot = holder && holder.querySelector('[data-error]');
      if (slot) slot.textContent = '';
    };
    $$('input,select', form).forEach(function (f) {
      f.addEventListener('input', function () { clearError(f); });
      f.addEventListener('change', function () { clearError(f); });
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var ok = true, firstBad = null;
      $$('input,select', form).forEach(function (f) {
        if (!f.hasAttribute('required')) return;
        var val = (f.value || '').trim();
        var bad = !val;
        if (!bad && f.type === 'email') bad = !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
        if (!bad && f.name === 'whatsapp') bad = (val.replace(/\D/g, '').length < 10);
        if (bad) {
          ok = false;
          showError(f, f.name === 'email' ? 'Informe um e-mail válido.' :
                       f.name === 'whatsapp' ? 'Informe um WhatsApp válido.' :
                       'Campo obrigatório.');
          if (!firstBad) firstBad = f;
        } else { clearError(f); }
      });

      if (!ok) {
        msg.textContent = 'Revise os campos destacados.';
        msg.className = 'form-message is-err';
        if (firstBad) firstBad.focus();
        return;
      }

      msg.textContent = 'Tudo certo! Abrindo o WhatsApp para concluir seu agendamento…';
      msg.className = 'form-message is-ok';

      var data = new FormData(form);
      var resumo = 'Olá, quero agendar uma demonstração da UpWeb.%0A'
        + '%0ANome: ' + encodeURIComponent(data.get('nome') || '')
        + '%0AE-mail: ' + encodeURIComponent(data.get('email') || '')
        + '%0AWhatsApp: ' + encodeURIComponent(data.get('whatsapp') || '')
        + '%0AAssociação: ' + encodeURIComponent(data.get('associacao') || '')
        + '%0ASinistros/mês: ' + encodeURIComponent(data.get('sinistros') || '');
      var url = 'https://wa.me/' + WHATSAPP_NUMBER + '?text=' + resumo;
      window.setTimeout(function () { window.open(url, '_blank', 'noopener'); }, 600);
      form.reset();
    });
  }

  /* 10. FAQ — apenas um aberto por vez ------------------------------ */
  var faq = $('[data-faq]');
  if (faq) {
    var items = $$('details', faq);
    items.forEach(function (d) {
      d.addEventListener('toggle', function () {
        if (d.open) {
          items.forEach(function (other) { if (other !== d) other.open = false; });
        }
      });
    });
  }

  /* 11. Counter animation ------------------------------------------- */
  var statsBlock = $('[data-stats]');
  if (statsBlock) {
    var runCounters = function () {
      $$('[data-counter]', statsBlock).forEach(function (el) {
        var target = parseFloat(el.getAttribute('data-counter')) || 0;
        var prefix = el.getAttribute('data-prefix') || '';
        var suffix = el.getAttribute('data-suffix') || '';
        if (prefersReduced) { el.textContent = prefix + target + suffix; return; }
        var dur = 1400, start = null;
        var tick = function (ts) {
          if (!start) start = ts;
          var p = Math.min((ts - start) / dur, 1);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = prefix + Math.round(target * eased) + suffix;
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
    };
    if (!('IntersectionObserver' in window) || prefersReduced) {
      runCounters();
    } else {
      var so = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { runCounters(); so.disconnect(); }
        });
      }, { threshold: 0.4 });
      so.observe(statsBlock);
    }
  }

  /* 12. Links WhatsApp ---------------------------------------------- */
  var waHref = 'https://wa.me/' + WHATSAPP_NUMBER + '?text=' + encodeURIComponent(WHATSAPP_TEXT);
  $$('[data-whatsapp]').forEach(function (el) {
    el.setAttribute('href', waHref);
    el.setAttribute('target', '_blank');
    el.setAttribute('rel', 'noopener');
  });

  /* Ano no footer --------------------------------------------------- */
  var yearEl = $('[data-year]');
  if (yearEl) yearEl.textContent = new Date().getFullYear();
})();
