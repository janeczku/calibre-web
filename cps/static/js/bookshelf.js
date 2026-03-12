/* Wooden bookshelf: group books into visual rows and inject shelf planks */
(function () {
  function buildShelves() {
    document.querySelectorAll('.row.display-flex').forEach(function (container) {
      // Collect book elements (direct children with class "book")
      var books = Array.from(container.querySelectorAll(':scope > .book'));
      if (books.length === 0) return;

      // Already processed — skip
      if (container.querySelector('.shelf-row')) return;

      // Group books by their top offset (= visual row)
      var rows = [];
      var currentRow = [];
      var currentTop = null;

      books.forEach(function (book) {
        var top = book.getBoundingClientRect().top;
        if (currentTop === null || Math.abs(top - currentTop) > 10) {
          if (currentRow.length > 0) rows.push(currentRow);
          currentRow = [book];
          currentTop = top;
        } else {
          currentRow.push(book);
        }
      });
      if (currentRow.length > 0) rows.push(currentRow);

      // Wrap each row in a shelf-row div and append a plank
      rows.forEach(function (rowBooks) {
        var shelfRow = document.createElement('div');
        shelfRow.className = 'shelf-row';

        // Insert shelfRow before the first book in this row
        container.insertBefore(shelfRow, rowBooks[0]);

        rowBooks.forEach(function (book) {
          shelfRow.appendChild(book);
        });

        // Wooden plank
        var plank = document.createElement('div');
        plank.className = 'shelf-plank';
        shelfRow.appendChild(plank);
      });
    });
  }

  // Run after images load so getBoundingClientRect is accurate
  if (document.readyState === 'complete') {
    buildShelves();
  } else {
    window.addEventListener('load', buildShelves);
  }

  // Re-run on resize (debounced), unwrapping first
  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      // Unwrap: move books back out, remove shelf-rows
      document.querySelectorAll('.shelf-row').forEach(function (row) {
        var parent = row.parentNode;
        Array.from(row.querySelectorAll('.book')).forEach(function (book) {
          parent.insertBefore(book, row);
        });
        parent.removeChild(row);
      });
      buildShelves();
    }, 200);
  });
})();
