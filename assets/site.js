(function () {
  var button = document.querySelector('.menu-toggle');
  var nav = document.querySelector('#primary-nav');
  if (button && nav) {
    button.addEventListener('click', function () {
      var open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!open));
      nav.classList.toggle('open', !open);
      document.body.classList.toggle('menu-open', !open);
    });
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        button.setAttribute('aria-expanded', 'false');
        nav.classList.remove('open');
        document.body.classList.remove('menu-open');
      });
    });
  }

  var header = document.querySelector('.site-header');
  var lastY = 0;
  window.addEventListener('scroll', function () {
    var y = window.scrollY;
    if (header) header.classList.toggle('compact', y > 32);
    lastY = y;
  }, { passive: true });
})();

