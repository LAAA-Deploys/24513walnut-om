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

  var galleryLinks = Array.from(document.querySelectorAll('[data-gallery-link]'));
  var galleryDialog = document.querySelector('[data-gallery-dialog]');
  var galleryImage = galleryDialog ? galleryDialog.querySelector('[data-gallery-image]') : null;
  var galleryCaption = galleryDialog ? galleryDialog.querySelector('[data-gallery-caption]') : null;
  var galleryIndex = 0;

  function showGalleryImage(index) {
    if (!galleryLinks.length || !galleryImage || !galleryCaption) return;
    galleryIndex = (index + galleryLinks.length) % galleryLinks.length;
    var link = galleryLinks[galleryIndex];
    var source = link.querySelector('img');
    var caption = link.querySelector('figcaption');
    galleryImage.src = link.getAttribute('href');
    galleryImage.alt = source ? source.alt : '';
    galleryCaption.textContent = caption ? caption.childNodes[0].textContent.trim() : '';
  }

  if (galleryDialog && typeof galleryDialog.showModal === 'function') {
    galleryLinks.forEach(function (link, index) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        showGalleryImage(index);
        galleryDialog.showModal();
        document.body.classList.add('lightbox-open');
      });
    });
    galleryDialog.querySelector('[data-gallery-close]').addEventListener('click', function () { galleryDialog.close(); });
    galleryDialog.querySelector('[data-gallery-previous]').addEventListener('click', function () { showGalleryImage(galleryIndex - 1); });
    galleryDialog.querySelector('[data-gallery-next]').addEventListener('click', function () { showGalleryImage(galleryIndex + 1); });
    galleryDialog.addEventListener('click', function (event) {
      if (event.target === galleryDialog) galleryDialog.close();
    });
    galleryDialog.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowLeft') { event.preventDefault(); showGalleryImage(galleryIndex - 1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); showGalleryImage(galleryIndex + 1); }
    });
    galleryDialog.addEventListener('close', function () { document.body.classList.remove('lightbox-open'); });
  }

  var compCards = Array.from(document.querySelectorAll('[data-comp-card]'));
  var compFilters = Array.from(document.querySelectorAll('[data-comp-filter]'));
  var compStatus = document.querySelector('[data-comp-status]');

  function filterComps(filter) {
    var visibleCount = 0;
    compCards.forEach(function (card) {
      var visible = filter === 'all' || card.dataset.compTags.split(/\s+/).includes(filter);
      card.hidden = !visible;
      card.classList.remove('is-highlighted');
      if (visible) visibleCount += 1;
    });
    compFilters.forEach(function (button) {
      var active = button.dataset.compFilter === filter;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    if (compStatus) compStatus.textContent = 'Showing ' + visibleCount + ' of ' + compCards.length + ' sale comparables.';
  }

  compFilters.forEach(function (filterButton) {
    filterButton.addEventListener('click', function () { filterComps(filterButton.dataset.compFilter); });
  });

  document.querySelectorAll('[data-comp-target]').forEach(function (targetButton) {
    targetButton.addEventListener('click', function () {
      filterComps('all');
      var card = document.querySelector('[data-comp-id="' + targetButton.dataset.compTarget + '"]');
      if (!card) return;
      card.classList.add('is-highlighted');
      var details = card.querySelector('details');
      if (details) details.open = true;
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      window.setTimeout(function () {
        var summary = card.querySelector('summary');
        if (summary) summary.focus({ preventScroll: true });
      }, 450);
    });
  });

  window.addEventListener('scroll', function () {
    if (header) header.classList.toggle('compact', window.scrollY > 32);
  }, { passive: true });
})();
