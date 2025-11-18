/**
 * Calibre-Web Professional Theme JavaScript
 * Enhances user experience with smooth interactions
 */

(function() {
  'use strict';

  // Wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', function() {

    // ===== SMOOTH SCROLL TO TOP =====
    createScrollToTopButton();

    // ===== ENHANCED BOOK CARDS =====
    enhanceBookCards();

    // ===== LAZY LOADING FOR IMAGES =====
    setupLazyLoading();

    // ===== IMPROVED SEARCH =====
    enhanceSearch();

    // ===== KEYBOARD SHORTCUTS =====
    setupKeyboardShortcuts();

    // ===== TOAST NOTIFICATIONS =====
    enhanceAlerts();

    // ===== LOADING STATES =====
    setupLoadingStates();
  });

  /**
   * Creates a smooth scroll-to-top button
   */
  function createScrollToTopButton() {
    // Create button element
    const scrollBtn = document.createElement('button');
    scrollBtn.innerHTML = '<span class="glyphicon glyphicon-chevron-up"></span>';
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.setAttribute('aria-label', 'Scroll to top');
    scrollBtn.style.cssText = `
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      width: 3rem;
      height: 3rem;
      border-radius: 50%;
      background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
      color: white;
      border: none;
      cursor: pointer;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    document.body.appendChild(scrollBtn);

    // Show/hide button based on scroll position
    let scrollTimeout;
    window.addEventListener('scroll', function() {
      clearTimeout(scrollTimeout);

      if (window.pageYOffset > 300) {
        scrollBtn.style.opacity = '1';
        scrollBtn.style.visibility = 'visible';
      } else {
        scrollBtn.style.opacity = '0';
        scrollBtn.style.visibility = 'hidden';
      }
    });

    // Scroll to top on click
    scrollBtn.addEventListener('click', function() {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });

    // Hover effect
    scrollBtn.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-4px) scale(1.1)';
      this.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.2)';
    });

    scrollBtn.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
      this.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
    });
  }

  /**
   * Enhances book cards with additional interactions
   */
  function enhanceBookCards() {
    const bookCards = document.querySelectorAll('.book');

    bookCards.forEach(function(card, index) {
      // Add stagger animation delay
      card.style.animationDelay = (index * 0.05) + 's';

      // Add click ripple effect
      card.addEventListener('click', function(e) {
        // Only add ripple if clicking on the card itself, not links
        if (e.target === card || e.target.classList.contains('cover') || e.target.classList.contains('meta')) {
          createRipple(e, this);
        }
      });

      // Add keyboard navigation support
      const titleLink = card.querySelector('.title a');
      if (titleLink) {
        card.setAttribute('tabindex', '0');
        card.addEventListener('keypress', function(e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            titleLink.click();
          }
        });
      }
    });
  }

  /**
   * Creates a ripple effect on click
   */
  function createRipple(event, element) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    ripple.style.cssText = `
      position: absolute;
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      background: rgba(37, 99, 235, 0.3);
      left: ${x}px;
      top: ${y}px;
      pointer-events: none;
      transform: scale(0);
      animation: ripple-animation 0.6s ease-out;
    `;

    // Add ripple animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes ripple-animation {
        to {
          transform: scale(4);
          opacity: 0;
        }
      }
    `;
    if (!document.querySelector('#ripple-animation-style')) {
      style.id = 'ripple-animation-style';
      document.head.appendChild(style);
    }

    element.style.position = 'relative';
    element.style.overflow = 'hidden';
    element.appendChild(ripple);

    setTimeout(function() {
      ripple.remove();
    }, 600);
  }

  /**
   * Setup lazy loading for images
   */
  function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver(function(entries, observer) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
              observer.unobserve(img);

              // Add fade-in effect
              img.style.opacity = '0';
              img.style.transition = 'opacity 0.3s';
              img.addEventListener('load', function() {
                img.style.opacity = '1';
              });
            }
          }
        });
      }, {
        rootMargin: '50px'
      });

      // Observe all images with data-src attribute
      document.querySelectorAll('img[data-src]').forEach(function(img) {
        imageObserver.observe(img);
      });
    }
  }

  /**
   * Enhances search functionality
   */
  function enhanceSearch() {
    const searchInput = document.querySelector('#query');
    if (!searchInput) return;

    // Add search icon animation on focus
    searchInput.addEventListener('focus', function() {
      const searchBtn = document.querySelector('#query_submit');
      if (searchBtn) {
        searchBtn.style.transform = 'scale(1.05)';
      }
    });

    searchInput.addEventListener('blur', function() {
      const searchBtn = document.querySelector('#query_submit');
      if (searchBtn) {
        searchBtn.style.transform = 'scale(1)';
      }
    });

    // Add clear button to search input
    if (searchInput.value) {
      addClearButton(searchInput);
    }

    searchInput.addEventListener('input', function() {
      if (this.value) {
        addClearButton(this);
      } else {
        removeClearButton(this);
      }
    });
  }

  /**
   * Adds a clear button to input field
   */
  function addClearButton(input) {
    if (input.parentElement.querySelector('.clear-search-btn')) return;

    const clearBtn = document.createElement('button');
    clearBtn.innerHTML = '&times;';
    clearBtn.className = 'clear-search-btn';
    clearBtn.type = 'button';
    clearBtn.setAttribute('aria-label', 'Clear search');
    clearBtn.style.cssText = `
      position: absolute;
      right: 80px;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      font-size: 1.5rem;
      color: #6b7280;
      cursor: pointer;
      padding: 0 0.5rem;
      line-height: 1;
      transition: color 0.2s;
    `;

    clearBtn.addEventListener('click', function() {
      input.value = '';
      input.focus();
      removeClearButton(input);
    });

    clearBtn.addEventListener('mouseenter', function() {
      this.style.color = '#2563eb';
    });

    clearBtn.addEventListener('mouseleave', function() {
      this.style.color = '#6b7280';
    });

    input.parentElement.style.position = 'relative';
    input.parentElement.appendChild(clearBtn);
  }

  /**
   * Removes clear button from input field
   */
  function removeClearButton(input) {
    const clearBtn = input.parentElement.querySelector('.clear-search-btn');
    if (clearBtn) {
      clearBtn.remove();
    }
  }

  /**
   * Setup keyboard shortcuts
   */
  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
      // Focus search with '/' key
      if (e.key === '/' && !isInputFocused()) {
        e.preventDefault();
        const searchInput = document.querySelector('#query');
        if (searchInput) {
          searchInput.focus();
        }
      }

      // Escape key to clear/blur search
      if (e.key === 'Escape') {
        const searchInput = document.querySelector('#query');
        if (searchInput && document.activeElement === searchInput) {
          searchInput.value = '';
          searchInput.blur();
          removeClearButton(searchInput);
        }
      }
    });
  }

  /**
   * Check if an input element is focused
   */
  function isInputFocused() {
    const activeElement = document.activeElement;
    return activeElement && (
      activeElement.tagName === 'INPUT' ||
      activeElement.tagName === 'TEXTAREA' ||
      activeElement.isContentEditable
    );
  }

  /**
   * Enhances alert messages
   */
  function enhanceAlerts() {
    const alerts = document.querySelectorAll('.alert');

    alerts.forEach(function(alert) {
      // Make alerts dismissible
      if (!alert.querySelector('.close')) {
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&times;';
        closeBtn.className = 'close';
        closeBtn.type = 'button';
        closeBtn.setAttribute('aria-label', 'Close');
        closeBtn.style.cssText = `
          position: absolute;
          top: 1rem;
          right: 1rem;
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          opacity: 0.7;
          transition: opacity 0.2s;
          line-height: 1;
          padding: 0;
          width: 1.5rem;
          height: 1.5rem;
        `;

        closeBtn.addEventListener('click', function() {
          alert.style.animation = 'slideOutRight 0.3s ease-out';
          setTimeout(function() {
            alert.remove();
          }, 300);
        });

        closeBtn.addEventListener('mouseenter', function() {
          this.style.opacity = '1';
        });

        closeBtn.addEventListener('mouseleave', function() {
          this.style.opacity = '0.7';
        });

        alert.style.position = 'relative';
        alert.insertBefore(closeBtn, alert.firstChild);
      }

      // Auto-dismiss after 5 seconds
      setTimeout(function() {
        if (alert.parentElement) {
          alert.style.animation = 'slideOutRight 0.3s ease-out';
          setTimeout(function() {
            if (alert.parentElement) {
              alert.remove();
            }
          }, 300);
        }
      }, 5000);
    });

    // Add slide out animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideOutRight {
        from {
          opacity: 1;
          transform: translateX(0);
        }
        to {
          opacity: 0;
          transform: translateX(100%);
        }
      }
    `;
    if (!document.querySelector('#alert-animation-style')) {
      style.id = 'alert-animation-style';
      document.head.appendChild(style);
    }
  }

  /**
   * Setup loading states for buttons and forms
   */
  function setupLoadingStates() {
    const forms = document.querySelectorAll('form');

    forms.forEach(function(form) {
      form.addEventListener('submit', function(e) {
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          // Add loading state
          submitBtn.disabled = true;
          submitBtn.style.position = 'relative';
          submitBtn.style.pointerEvents = 'none';

          const originalContent = submitBtn.innerHTML;
          submitBtn.setAttribute('data-original-content', originalContent);

          // Add spinner
          submitBtn.innerHTML = `
            <span style="display: inline-flex; align-items: center; gap: 0.5rem;">
              <span class="spinner-small" style="
                display: inline-block;
                width: 1rem;
                height: 1rem;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-top-color: white;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
              "></span>
              ${originalContent}
            </span>
          `;
        }
      });
    });
  }

  /**
   * Utility function to show toast notification
   */
  window.showToast = function(message, type) {
    type = type || 'info';

    const toast = document.createElement('div');
    toast.className = 'alert alert-' + type;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      top: 2rem;
      right: 2rem;
      z-index: 9999;
      max-width: 300px;
      animation: slideInRight 0.3s ease-out;
    `;

    document.body.appendChild(toast);

    // Auto dismiss after 3 seconds
    setTimeout(function() {
      toast.style.animation = 'slideOutRight 0.3s ease-out';
      setTimeout(function() {
        toast.remove();
      }, 300);
    }, 3000);
  };

  /**
   * Add smooth reveal animation for elements as they enter viewport
   */
  if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1
    });

    // Observe elements with reveal class
    document.querySelectorAll('.reveal-on-scroll').forEach(function(el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
      revealObserver.observe(el);
    });
  }

})();
