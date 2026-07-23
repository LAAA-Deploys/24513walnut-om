(function () {
  'use strict';

  var menuButton = document.querySelector('.menu-toggle');
  var nav = document.querySelector('#primary-nav');
  var menuLabel = menuButton ? menuButton.querySelector('.menu-label') : null;
  var backdrop = document.querySelector('.menu-backdrop');
  var header = document.querySelector('.site-header');
  var pageRegions = [document.querySelector('main'), document.querySelector('footer'), document.querySelector('.mobile-cta')].filter(Boolean);
  var menuOpen = false;

  function syncMenuTop() {
    if (!header) return;
    var bottom = Math.max(0, Math.round(header.getBoundingClientRect().bottom));
    document.documentElement.style.setProperty('--menu-top', bottom + 'px');
  }

  function setBackgroundInert(inert) {
    pageRegions.forEach(function (region) {
      region.inert = inert;
      if (inert) region.setAttribute('aria-hidden', 'true');
      else region.removeAttribute('aria-hidden');
    });
  }

  function closeMenu(restoreFocus) {
    if (!menuButton || !nav) return;
    menuOpen = false;
    menuButton.setAttribute('aria-expanded', 'false');
    if (menuLabel) menuLabel.textContent = 'Open navigation';
    nav.classList.remove('open');
    document.body.classList.remove('menu-open');
    setBackgroundInert(false);
    if (backdrop) backdrop.hidden = true;
    if (restoreFocus) menuButton.focus();
  }

  function openMenu() {
    if (!menuButton || !nav) return;
    syncMenuTop();
    menuOpen = true;
    menuButton.setAttribute('aria-expanded', 'true');
    if (menuLabel) menuLabel.textContent = 'Close navigation';
    nav.classList.add('open');
    document.body.classList.add('menu-open');
    setBackgroundInert(true);
    if (backdrop) backdrop.hidden = false;
    var firstLink = nav.querySelector('a');
    if (firstLink) firstLink.focus();
  }

  if (menuButton && nav) {
    menuButton.addEventListener('click', function () { menuOpen ? closeMenu(true) : openMenu(); });
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        var target = link.hash ? document.getElementById(link.hash.slice(1)) : null;
        closeMenu(false);
        if (target) {
          var hadTabindex = target.hasAttribute('tabindex');
          if (!hadTabindex) target.setAttribute('tabindex', '-1');
          window.requestAnimationFrame(function () {
            target.focus({ preventScroll: true });
            if (!hadTabindex) {
              target.addEventListener('blur', function () { target.removeAttribute('tabindex'); }, { once: true });
            }
          });
        }
      });
    });
    if (backdrop) backdrop.addEventListener('click', function () { closeMenu(true); });
    document.addEventListener('keydown', function (event) {
      if (!menuOpen) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        closeMenu(true);
        return;
      }
      if (event.key !== 'Tab') return;
      var focusable = [menuButton].concat(Array.from(nav.querySelectorAll('a')));
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
      if (menuOpen && !nav.contains(event.target) && !menuButton.contains(event.target) && event.target !== backdrop) closeMenu(true);
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
      var wrapper = region.closest('.table-region');
      var cue = wrapper ? wrapper.querySelector('.table-scroll-cue') : null;
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
  var galleryTouchStart = null;

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
    galleryDialog.addEventListener('click', function (event) { if (event.target === galleryDialog) galleryDialog.close(); });
    galleryDialog.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowLeft') { event.preventDefault(); showGalleryImage(galleryIndex - 1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); showGalleryImage(galleryIndex + 1); }
    });
    galleryDialog.addEventListener('touchstart', function (event) { galleryTouchStart = event.changedTouches[0].clientX; }, { passive: true });
    galleryDialog.addEventListener('touchend', function (event) {
      if (galleryTouchStart === null) return;
      var delta = event.changedTouches[0].clientX - galleryTouchStart;
      if (Math.abs(delta) > 45) showGalleryImage(galleryIndex + (delta < 0 ? 1 : -1));
      galleryTouchStart = null;
    }, { passive: true });
    galleryDialog.addEventListener('close', function () { document.body.classList.remove('lightbox-open'); });
  }

  var locationButtons = Array.from(document.querySelectorAll('[data-location-view]'));
  var locationPanels = Array.from(document.querySelectorAll('[data-location-panel]'));
  var mapConfigElement = document.querySelector('#map-config');
  var mapConfig = null;
  var locationMap = null;
  var locationTransitLayer = null;
  var compGoogleMap = null;
  var googleMapConstructor = null;
  var googleMarkerConstructor = null;
  var compGoogleBounds = null;
  var compMarkerById = {};
  var googleMapsRequested = false;
  var googleMapsScript = null;
  var googleMapsAttempts = 0;
  var googleMapsRetryTimer = null;
  var mapObserver = null;
  var activeLocationButton = locationButtons.find(function (button) {
    return button.getAttribute('aria-pressed') === 'true';
  });
  var activeLocationView = activeLocationButton ? activeLocationButton.dataset.locationView : 'district';

  try {
    mapConfig = mapConfigElement ? JSON.parse(mapConfigElement.textContent) : null;
  } catch (error) {
    mapConfig = null;
  }

  function setLocationButtonState(view) {
    locationButtons.forEach(function (candidate) {
      var active = candidate.dataset.locationView === view;
      candidate.classList.toggle('active', active);
      candidate.setAttribute('aria-pressed', String(active));
    });
  }

  function showLocationFallback(view) {
    locationPanels.forEach(function (panel) { panel.hidden = panel.dataset.locationPanel !== view; });
  }

  function activateLocationView(view) {
    activeLocationView = view;
    setLocationButtonState(view);
    if (!locationMap || !mapConfig) {
      showLocationFallback(view);
      return;
    }
    locationMap.getStreetView().setVisible(false);
    if (locationTransitLayer) locationTransitLayer.setMap(null);
    if (view === 'satellite') {
      locationMap.setMapTypeId('satellite');
      locationMap.setZoom(19);
      locationMap.panTo(mapConfig.subject);
    } else if (view === 'transit') {
      locationMap.setMapTypeId('roadmap');
      locationMap.setZoom(15);
      locationMap.panTo(mapConfig.subject);
      if (locationTransitLayer) locationTransitLayer.setMap(locationMap);
    } else if (view === 'street') {
      var panorama = locationMap.getStreetView();
      panorama.setPosition(mapConfig.subject);
      panorama.setPov({ heading: 15, pitch: 0 });
      panorama.setVisible(true);
    } else {
      locationMap.setMapTypeId('roadmap');
      locationMap.setZoom(15);
      locationMap.panTo(mapConfig.subject);
    }
  }

  locationButtons.forEach(function (button) {
    button.addEventListener('click', function () { activateLocationView(button.dataset.locationView); });
  });

  function handleGoogleMapsFailure() {
    googleMapsRequested = false;
    if (googleMapsScript) googleMapsScript.remove();
    googleMapsScript = null;
    locationMap = null;
    locationTransitLayer = null;
    compGoogleMap = null;
    googleMapConstructor = null;
    googleMarkerConstructor = null;
    compGoogleBounds = null;
    compMarkerById = {};
    document.querySelectorAll('[data-google-map]').forEach(function (canvas) {
      canvas.replaceChildren();
      canvas.hidden = true;
    });
    document.querySelectorAll('[data-map-fallback]').forEach(function (fallback) { fallback.hidden = false; });
    showLocationFallback(activeLocationView);
    var compCanvas = document.querySelector('[data-google-map="comps"]');
    if (compCanvas) compCanvas.closest('.comp-map-canvas').classList.remove('maps-active');
    if (googleMapsAttempts < 2 && !googleMapsRetryTimer) {
      googleMapsRetryTimer = window.setTimeout(function () {
        googleMapsRetryTimer = null;
        requestGoogleMaps();
      }, 1000);
    }
    var locationStatus = document.querySelector('[data-map-status="location"]');
    if (locationStatus) locationStatus.textContent = 'Location overview · Google map data.';
  }

  function markerContent(label, subject) {
    var element = document.createElement('span');
    element.className = 'google-marker' + (subject ? ' google-marker-subject' : '');
    element.textContent = label;
    return element;
  }

  function initCompGoogleMap() {
    var compCanvas = document.querySelector('[data-google-map="comps"]');
    var compPanel = compCanvas ? compCanvas.closest('.comp-map-panel') : null;
    if (!compCanvas || !googleMapConstructor || !googleMarkerConstructor || compGoogleMap) return;
    if (compPanel && window.getComputedStyle(compPanel).display === 'none') return;

    compCanvas.hidden = false;
    compGoogleMap = new googleMapConstructor(compCanvas, {
      center: { lat: 34.31, lng: -118.43 },
      zoom: 10,
      mapId: 'DEMO_MAP_ID',
      mapTypeControl: true,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
      clickableIcons: false
    });
    compGoogleBounds = new google.maps.LatLngBounds();
    compGoogleBounds.extend(mapConfig.subject);
    var subjectMarker = new googleMarkerConstructor({
      map: compGoogleMap,
      position: mapConfig.subject,
      title: mapConfig.subject.title,
      content: markerContent('S', true),
      gmpClickable: true
    });
    subjectMarker.addListener('click', function () { compGoogleMap.panTo(mapConfig.subject); });
    mapConfig.comps.forEach(function (point) {
      compGoogleBounds.extend(point);
      var content = markerContent(point.label, false);
      var marker = new googleMarkerConstructor({
        map: compGoogleMap,
        position: point,
        title: point.title,
        content: content,
        gmpClickable: true
      });
      marker.addListener('click', function () { selectComp(point.id, 'pin'); });
      compMarkerById[point.id] = { marker: marker, content: content, point: point };
    });
    compCanvas.closest('.comp-map-canvas').classList.add('maps-active');
    compGoogleMap.fitBounds(compGoogleBounds, 42);
    if (compIds.length) selectComp(compIds[selectedCompIndex]);
  }

  function initGoogleMaps() {
    if (!mapConfig || !window.google || !google.maps || !google.maps.importLibrary) {
      handleGoogleMapsFailure();
      return;
    }
    Promise.all([google.maps.importLibrary('maps'), google.maps.importLibrary('marker')]).then(function (libraries) {
      googleMapConstructor = libraries[0].Map;
      googleMarkerConstructor = libraries[1].AdvancedMarkerElement;
      var locationCanvas = document.querySelector('[data-google-map="location"]');

      if (locationCanvas) {
        locationCanvas.hidden = false;
        locationMap = new googleMapConstructor(locationCanvas, {
          center: mapConfig.subject,
          zoom: 15,
          mapId: 'DEMO_MAP_ID',
          mapTypeControl: true,
          streetViewControl: true,
          fullscreenControl: true,
          zoomControl: true,
          clickableIcons: false
        });
        locationTransitLayer = new google.maps.TransitLayer();
        mapConfig.locations.forEach(function (point) {
          var content = markerContent(point.label, point.id === 'subject');
          var marker = new googleMarkerConstructor({
            map: locationMap,
            position: point,
            title: point.title,
            content: content,
            gmpClickable: true
          });
          marker.addListener('click', function () {
            locationMap.panTo(point);
            locationMap.setZoom(point.id === 'subject' ? 18 : 16);
          });
        });
        var locationFallback = document.querySelector('[data-map-fallback="location"]');
        if (locationFallback) locationFallback.hidden = true;
        var locationStatus = document.querySelector('[data-map-status="location"]');
        if (locationStatus) locationStatus.textContent = 'Interactive Google map · select a labeled marker for its location.';
      }

      initCompGoogleMap();
      activateLocationView(activeLocationView);
      if (googleMapsRetryTimer) window.clearTimeout(googleMapsRetryTimer);
      googleMapsRetryTimer = null;
      if (mapObserver) mapObserver.disconnect();
    }).catch(handleGoogleMapsFailure);
  }

  function requestGoogleMaps() {
    if (googleMapsRequested) return true;
    var keyMeta = document.querySelector('meta[name="google-maps-browser-key"]');
    var key = String(window.LAAA_GOOGLE_MAPS_BROWSER_KEY || (keyMeta && keyMeta.content) || '').trim();
    if (!key) return false;
    if (googleMapsAttempts >= 2) return false;
    googleMapsAttempts += 1;
    googleMapsRequested = true;
    window.LAAAInitGoogleMaps = initGoogleMaps;
    googleMapsScript = document.createElement('script');
    googleMapsScript.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(key) + '&loading=async&v=weekly&libraries=marker&callback=LAAAInitGoogleMaps&auth_referrer_policy=origin';
    googleMapsScript.async = true;
    googleMapsScript.onerror = handleGoogleMapsFailure;
    document.head.appendChild(googleMapsScript);
    return true;
  }

  var mapSections = Array.from(document.querySelectorAll('[data-location-map], .comp-map-panel'));
  if ('IntersectionObserver' in window && mapSections.length) {
    mapObserver = new IntersectionObserver(function (entries) {
      if (entries.some(function (entry) { return entry.isIntersecting; })) {
        requestGoogleMaps();
      }
    }, { rootMargin: '500px 0px' });
    mapSections.forEach(function (section) { mapObserver.observe(section); });
  } else {
    requestGoogleMaps();
  }

  var financialButtons = Array.from(document.querySelectorAll('[data-fin-basis]'));
  var financialValues = Array.from(document.querySelectorAll('[data-fin-value]'));
  financialButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var basis = button.dataset.finBasis;
      financialButtons.forEach(function (candidate) {
        var active = candidate === button;
        candidate.classList.toggle('active', active);
        candidate.setAttribute('aria-pressed', String(active));
      });
      financialValues.forEach(function (cell) { cell.textContent = cell.dataset[basis] || '—'; });
    });
  });

  var compIds = Array.from(document.querySelectorAll('.comp-summary[data-comp-select]')).map(function (button) { return button.dataset.compSelect; });
  var compSelectors = Array.from(document.querySelectorAll('[data-comp-select]'));
  var compPreviews = Array.from(document.querySelectorAll('[data-comp-preview]'));
  var compPosition = document.querySelector('[data-comp-position]');
  var compExplorer = document.querySelector('.comp-explorer');
  var selectedCompIndex = 0;
  var compTouchStart = null;

  function selectComp(id, focusOrigin) {
    var index = compIds.indexOf(id);
    if (index < 0) return;
    selectedCompIndex = index;
    compSelectors.forEach(function (control) {
      var selected = control.dataset.compSelect === id;
      control.classList.toggle('is-selected', selected);
      if (control.hasAttribute('aria-pressed')) control.setAttribute('aria-pressed', String(selected));
    });
    compPreviews.forEach(function (preview) { preview.hidden = preview.dataset.compPreview !== id; });
    if (compPosition) compPosition.textContent = (index + 1) + ' of ' + compIds.length;
    Object.keys(compMarkerById).forEach(function (markerId) {
      var entry = compMarkerById[markerId];
      entry.content.classList.toggle('is-selected', markerId === id);
      entry.marker.zIndex = markerId === id ? 10 : 1;
    });
    if (focusOrigin && compGoogleMap && compMarkerById[id]) compGoogleMap.panTo(compMarkerById[id].point);
    if (focusOrigin === 'pin') {
      var summary = document.querySelector('.comp-summary[data-comp-select="' + id + '"]');
      if (summary) summary.setAttribute('aria-current', 'true');
    }
    document.querySelectorAll('.comp-summary[aria-current]').forEach(function (summary) {
      if (summary.dataset.compSelect !== id) summary.removeAttribute('aria-current');
    });
  }

  compSelectors.forEach(function (control) {
    control.addEventListener('click', function () { selectComp(control.dataset.compSelect, control.classList.contains('map-pin') ? 'pin' : 'list'); });
  });
  var previousComp = document.querySelector('[data-comp-previous]');
  var nextComp = document.querySelector('[data-comp-next]');
  if (previousComp) previousComp.addEventListener('click', function () { selectComp(compIds[(selectedCompIndex - 1 + compIds.length) % compIds.length], 'step'); });
  if (nextComp) nextComp.addEventListener('click', function () { selectComp(compIds[(selectedCompIndex + 1) % compIds.length], 'step'); });

  var compSwipeSurface = document.querySelector('.comp-preview-stack');
  if (compSwipeSurface) {
    compSwipeSurface.addEventListener('touchstart', function (event) { compTouchStart = event.changedTouches[0].clientX; }, { passive: true });
    compSwipeSurface.addEventListener('touchend', function (event) {
      if (compTouchStart === null) return;
      var delta = event.changedTouches[0].clientX - compTouchStart;
      if (Math.abs(delta) > 55) selectComp(compIds[(selectedCompIndex + (delta < 0 ? 1 : -1) + compIds.length) % compIds.length], 'swipe');
      compTouchStart = null;
    }, { passive: true });
  }

  var compViewButtons = Array.from(document.querySelectorAll('[data-comp-view]'));
  compViewButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var view = button.dataset.compView;
      compViewButtons.forEach(function (candidate) {
        var active = candidate === button;
        candidate.classList.toggle('active', active);
        candidate.setAttribute('aria-pressed', String(active));
      });
      if (compExplorer) compExplorer.dataset.mobileView = view;
      if (view === 'map') {
        window.requestAnimationFrame(function () {
          initCompGoogleMap();
          if (compGoogleMap && compGoogleBounds) {
            if (window.google && google.maps && google.maps.event) google.maps.event.trigger(compGoogleMap, 'resize');
            compGoogleMap.fitBounds(compGoogleBounds, 42);
          }
        });
      }
    });
  });
  if (compExplorer) compExplorer.dataset.mobileView = 'list';
  if (compIds.length) selectComp(compIds[0]);
})();
