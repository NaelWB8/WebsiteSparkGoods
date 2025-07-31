document.addEventListener('DOMContentLoaded', () => {
  const navbar = document.querySelector('.navbar');
  const hamburger = document.querySelector('#mobile-menu');
  const navMenu = document.querySelector('.navbar__menu');

  // Hamburger menu toggle
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navMenu.classList.toggle('active');
  });

  // Navbar scroll effect
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

  window.addEventListener("scroll", function () {
    const hamburgerBars = document.querySelectorAll(".hamburger .bar");
    if (window.scrollY > 0) {
      hamburgerBars.forEach(bar => bar.classList.add("scrolled"));
    } else {
      hamburgerBars.forEach(bar => bar.classList.remove("scrolled"));
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

// Image Slider Logic
document.addEventListener('DOMContentLoaded', () => {
  const sliderBox = document.querySelector('.slider-box');
  const images = sliderBox.querySelectorAll('img');
  const leftBtn = document.querySelector('.arrow.left');
  const rightBtn = document.querySelector('.arrow.right');

  let currentIndex = 0;

  // Sembunyikan semua gambar kecuali yang aktif
  function showImage(index) {
    images.forEach((img, i) => {
      img.style.display = i === index ? 'block' : 'none';
    });
  }

  rightBtn.addEventListener('click', () => {
    currentIndex = (currentIndex + 1) % images.length;
    showImage(currentIndex);
  });

  leftBtn.addEventListener('click', () => {
    currentIndex = (currentIndex - 1 + images.length) % images.length;
    showImage(currentIndex);
  });

  // Initial setup
  showImage(currentIndex);
});

