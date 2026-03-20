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

// Auth Modal Functions
// Auth Modal Functions
function openAuthModal(mode) {
  const modal = document.getElementById('authModal');
  const title = document.getElementById('modalTitle');
  const submitBtn = document.getElementById('submitBtn');
  const toggleText = document.getElementById('authToggle');
  const nameField = document.getElementById('nameField');
  
  // Clear previous errors and inputs
  document.getElementById('authForm').reset();
  const existingErrors = document.querySelectorAll('.auth-error');
  existingErrors.forEach(error => error.remove());
  
  if (mode === 'login') {
      title.textContent = 'Login';
      submitBtn.textContent = 'Login';
      toggleText.innerHTML = 'Don\'t have an account? <a href="#" onclick="toggleAuthMode()">Register</a>';
      nameField.style.display = 'none';
  } else {
      title.textContent = 'Register';
      submitBtn.textContent = 'Register';
      toggleText.innerHTML = 'Already have an account? <a href="#" onclick="toggleAuthMode()">Login</a>';
      nameField.style.display = 'block';
  }
  
  modal.style.display = 'block';
  document.getElementById('authForm').dataset.mode = mode;
}

function closeAuthModal() {
  document.getElementById('authModal').style.display = 'none';
}

function toggleAuthMode() {
  const currentMode = document.getElementById('authForm').dataset.mode;
  openAuthModal(currentMode === 'login' ? 'register' : 'login');
}

// Handle form submission
// Update the auth form submission handler
// Update the auth form submission handler
document.getElementById('authForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const mode = this.dataset.mode;
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const name = mode === 'register' ? document.getElementById('name').value : null;

  // Clear previous errors
  const existingErrors = document.querySelectorAll('.auth-error');
  existingErrors.forEach(error => error.remove());

  // Add loading state
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Processing...';

  try {
      const response = await fetch(`/api/${mode}`, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
              email, 
              password,
              ...(mode === 'register' && { name }) 
          }),
          credentials: 'include'
      });

      const data = await response.json();

      if (!response.ok) {
          throw new Error(data.error || 'An error occurred');
      }

      // Success - close modal and redirect to dashboard for both login and register
      closeAuthModal();
      window.location.href = '/dashboard';

  } catch (error) {
      console.error('Error:', error);
      const errorDiv = document.createElement('div');
      errorDiv.className = 'auth-error';
      errorDiv.textContent = error.message;
      document.getElementById('authForm').prepend(errorDiv);
  } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = mode === 'login' ? 'Login' : 'Register';
  }
});