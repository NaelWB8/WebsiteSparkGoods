document.addEventListener('DOMContentLoaded', () => {
  const navbar = document.querySelector('.navbar');

  // Mobile menu toggle
  const menu = document.getElementById('mobile-menu');
  const menuLinks = document.querySelector('.navbar__menu');

  if (menu) {
    menu.addEventListener('click', () => {
      menu.classList.toggle('is-active');
      menuLinks.classList.toggle('active');
    });
  }

  // Navbar scroll effect
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

  // Counter animation
  const counters = document.querySelectorAll('.impact-number');
  const duration = 2000;

  function animateCounter(counter) {
    const target = +counter.getAttribute('data-target');
    const prefix = counter.getAttribute('data-prefix') || '';
    const suffix = counter.getAttribute('data-suffix') || '';
    const increment = target / (duration / 16);
    let count = 0;

    const updateCount = () => {
      count += increment;
      if (count < target) {
        counter.textContent = prefix + Math.floor(count).toLocaleString() + suffix;
        requestAnimationFrame(updateCount);
      } else {
        counter.textContent = prefix + target.toLocaleString() + suffix;
      }
    };

    updateCount();
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
        animateCounter(entry.target);
        entry.target.classList.add('animated');
      }
    });
  }, {
    threshold: 0.5
  });

  counters.forEach(counter => observer.observe(counter));
});
