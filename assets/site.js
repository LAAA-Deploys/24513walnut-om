(function () {
  'use strict';

  var button = document.querySelector('.menu-toggle');
  var nav = document.querySelector('#primary-nav');
  var label = button ? button.querySelector('.menu-label') : null;
  var backdrop = document.querySelector('.menu-backdrop');
  var header = document.querySelector('.site-header');
  var pageRegions = [document.querySelector('main'), document.querySelector('footer'), document.querySelector('.mobile-cta')].filter(Boolean);
  var menuOpen = false;

  function syncMenuTop() {
    if (!header) return;
    var rect = header.getBoundingClientRect();
    var bottom = Math.max(0, Math.round(rect.bottom));
    document.documentElement.style.setProperty('--menu-top', bottom + 'px');
    document.documentElement.style.setProperty('--menu-offset', Math.round(rect.height) + 'px');
  }

  function setBackgroundInert(inert) {
    pageRegions.forEach(function (region) {
      region.inert = inert;
      if (inert) region.setAttribute('aria-hidden', 'true');
      else region.removeAttribute('aria-hidden');
    });
  }

  function closeMenu(restoreFocus) {
    if (!button || !nav) return;
    menuOpen = false;
    button.setAttribute('aria-expanded', 'false');
    if (label) label.textContent = 'Open navigation';
    nav.classList.remove('open');
    document.body.classList.remove('menu-open');
    setBackgroundInert(false);
    if (backdrop) backdrop.hidden = true;
    if (restoreFocus) button.focus();
  }

  function openMenu() {
    if (!button || !nav) return;
    syncMenuTop();
    menuOpen = true;
    button.setAttribute('aria-expanded', 'true');
    if (label) label.textContent = 'Close navigation';
    nav.classList.add('open');
    document.body.classList.add('menu-open');
    setBackgroundInert(true);
    if (backdrop) backdrop.hidden = false;
    var firstLink = nav.querySelector('a');
    if (firstLink) firstLink.focus();
  }

  if (button && nav) {
    button.addEventListener('click', function () {
      if (menuOpen) closeMenu(true);
      else openMenu();
    });

    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        closeMenu(false);
        window.requestAnimationFrame(function () { button.focus(); });
      });
    });

    if (backdrop) {
      backdrop.addEventListener('click', function () {
        closeMenu(true);
      });
    }

    document.addEventListener('keydown', function (event) {
      if (!menuOpen) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        closeMenu(true);
        return;
      }
      if (event.key !== 'Tab') return;
      var focusable = [button].concat(Array.from(nav.querySelectorAll('a')));
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });

    document.addEventListener('pointerdown', function (event) {
      if (menuOpen && !nav.contains(event.target) && !button.contains(event.target) && event.target !== backdrop) {
        closeMenu(true);
      }
    });

    window.addEventListener('resize', function () {
      syncMenuTop();
      if (window.innerWidth > 900 && menuOpen) closeMenu(false);
    }, { passive: true });
    window.addEventListener('scroll', syncMenuTop, { passive: true });
    syncMenuTop();
  }

  document.querySelectorAll('.table-shell').forEach(function (region) {
    function updateOverflowState() {
      var overflow = region.scrollWidth > region.clientWidth + 1;
      var atEnd = region.scrollLeft + region.clientWidth >= region.scrollWidth - 2;
      region.classList.toggle('has-overflow', overflow);
      region.classList.toggle('at-end', overflow && atEnd);
      var cue = region.parentElement ? region.parentElement.querySelector('.table-scroll-cue') : null;
      if (cue) cue.hidden = !overflow;
    }
    region.addEventListener('scroll', updateOverflowState, { passive: true });
    window.addEventListener('resize', updateOverflowState, { passive: true });
    updateOverflowState();
  });

  window.addEventListener('scroll', function () {
    if (header) header.classList.toggle('compact', window.scrollY > 32);
  }, { passive: true });
})();
