//  Hypothesis Customized embedding
//  This hypothesis config function returns a new constructor which modifies
//  annotator for a better integration. Below we create our own EpubAnnotationSidebar
//  Constructor, customizing the show and hide function to take acount for the reader UI.

window.hypothesisConfig = function() {
  var Annotator = window.Annotator;
  var $main = $("#main");

  function EpubAnnotationSidebar(elem, options) {
    options = {
      server: true,
      origin: true,
      showHighlights: true,
      Toolbar: {container: '#annotation-controls'}
    }

    Annotator.Host.call(this, elem, options);
  }

  EpubAnnotationSidebar.prototype = Object.create(Annotator.Host.prototype);

  EpubAnnotationSidebar.prototype.show = function() {
    this.frame.css({
      'margin-left': (-1 * this.frame.width()) + "px"
    });
    this.frame.removeClass('annotator-collapsed');
    if (!$main.hasClass('single')) {
      $main.addClass("single");
      this.toolbar.find('[name=sidebar-toggle]').removeClass('h-icon-chevron-left').addClass('h-icon-chevron-right');
      this.setVisibleHighlights(true);
    }
  };

  EpubAnnotationSidebar.prototype.hide = function() {
    this.frame.css({
      'margin-left': ''
    });
    this.frame.addClass('annotator-collapsed');
    if ($main.hasClass('single')) {
      $main.removeClass("single");
      this.toolbar.find('[name=sidebar-toggle]').removeClass('h-icon-chevron-right').addClass('h-icon-chevron-left');
      this.setVisibleHighlights(false);
    }
  };

  return {
    constructor: EpubAnnotationSidebar,
  }
};

// This is the Epub.js plugin. Annotations are updated on location change.
EPUBJS.reader.plugins.HypothesisController = function (Book) {
  var reader = this;
  var $main = $("#main");

  var updateAnnotations = function () {
    var annotator = Book.renderer.render.window.annotator;
    if (annotator && annotator.constructor.$) {
      var annotations = getVisibleAnnotations(annotator.constructor.$);
      annotator.showAnnotations(annotations)
    }
  };

  var getVisibleAnnotations = function ($) {
    var width = Book.renderer.render.iframe.clientWidth;
    return $('.annotator-hl').map(function() {
      var $this = $(this),
          left = this.getBoundingClientRect().left;

      if (left >= 0 && left <= width) {
        return $this.data('annotation');
      }
    }).get();
  };

  Book.on("renderer:locationChanged", updateAnnotations);

  return {}
};
