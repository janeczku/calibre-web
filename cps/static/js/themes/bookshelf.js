/* Wooden bookshelf: inject shelf planks at the base of book rows */
(function () {
  function buildShelves() {
    document.querySelectorAll('.row.display-flex').forEach(function (container) {
      // Remove existing planks first
      container.querySelectorAll('.shelf-plank').forEach(function(p) { p.remove(); });

      var books = Array.from(container.querySelectorAll('.book'));
      if (books.length === 0) return;

      // Group books by their vertical position
      var rows = {};
      var containerRect = container.getBoundingClientRect();

      books.forEach(function (book) {
        var rect = book.getBoundingClientRect();
        // Use a 20px tolerance for grouping rows
        var rowKey = Math.round(rect.top / 20) * 20;
        if (!rows[rowKey]) rows[rowKey] = [];
        rows[rowKey].push(rect);
      });

      // For each row, find the lowest point and place a plank there
      Object.keys(rows).forEach(function (key) {
        var rowRects = rows[key];
        var maxBottom = 0;
        rowRects.forEach(function(r) {
          if (r.bottom > maxBottom) maxBottom = r.bottom;
        });

        // Calculate relative top for the plank
        // The plank should sit at the bottom of the books
        var relativeTop = maxBottom - containerRect.top;

        var plank = document.createElement('div');
        plank.className = 'shelf-plank';
        // Adjust plank to sit slightly higher to overlap the book bottom as per theme style
        plank.style.top = (relativeTop - 25) + 'px';
        container.appendChild(plank);
      });
    });
  }

  // Watch for new books added via infinite scroll
  var observer = new MutationObserver(function(mutations) {
    var shouldUpdate = false;
    mutations.forEach(function(mutation) {
      for (var i = 0; i < mutation.addedNodes.length; i++) {
        var node = mutation.addedNodes[i];
        if (node.nodeType === 1 && (node.classList.contains('book') || node.querySelector('.book'))) {
          shouldUpdate = true;
          break;
        }
      }
    });
    if (shouldUpdate) {
      // Small timeout to allow Isotope to finish positioning
      setTimeout(buildShelves, 100);
    }
  });

  document.querySelectorAll('.row.display-flex').forEach(function(container) {
    observer.observe(container, { childList: true });
  });

  // Run on load and resize
  if (document.readyState === 'complete') {
    buildShelves();
  } else {
    window.addEventListener('load', buildShelves);
  }

  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(buildShelves, 200);
  });
})();
