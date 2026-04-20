(() => {
  const current = document.location.pathname.split('/').pop();
  document.querySelectorAll('.sidebar a').forEach(a => {
    if (a.getAttribute('href').endsWith(current)) {
      a.parentElement.classList.add('active');
    }
  });
})();
