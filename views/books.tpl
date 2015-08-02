<!doctype html>
<!-- paulirish.com/2008/conditional-stylesheets-vs-css-hacks-answer-neither/ -->
<!--[if lt IE 7]> <html class="no-js lt-ie9 lt-ie8 lt-ie7" lang="de"> <![endif]-->
<!--[if IE 7]>    <html class="no-js lt-ie9 lt-ie8" lang="de"> <![endif]-->
<!--[if IE 8]>    <html class="no-js lt-ie9" lang="de"> <![endif]-->
<!-- Consider adding a manifest.appcache: h5bp.com/d/Offline -->
<!--[if gt IE 8]><!--> <html class="no-js" lang="de"> <!--<![endif]-->
<head>
  <meta charset="utf-8">

  <!-- Use the .htaccess and remove these lines to avoid edge case issues.
       More info: h5bp.com/i/378 -->
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">

  <title></title>
  <meta name="description" content="">

  <!-- Mobile viewport optimized: h5bp.com/viewport -->
  <meta name="viewport" content="width=device-width">


  <script src="/static/js/modernizr.custom.js"></script>

  <!-- Place favicon.ico and apple-touch-icon.png in the root directory: mathiasbynens.be/notes/touch-icons -->
  <link rel="stylesheet" type="text/css" href="/static/css/default.css" />
  <link rel="stylesheet" type="text/css" href="/static/css/component.css" />

  <!-- More ideas for your <head> here: h5bp.com/d/head-Tips -->

  <!--[if lt IE 9]>
      <script src="js/libs/html5.js"></script>
  <![endif]-->

  <!-- All JavaScript at the bottom, except this Modernizr build.
       Modernizr enables HTML5 elements & feature detects for optimal performance.
       Create your own custom Modernizr build: www.modernizr.com/download/
  <script src="/static/views/js/libs/modernizr-2.6.2.min.js"></script>-->
</head>
<body>
  <div class="container">
<header class="clearfix">
        <h1>Calibre Last added Books</h1>
        <span class="support-note">CalibreServer is still in a verry early state...</span>
      </header>
%import re

  <div class="main">
    <ul id="bk-list" class="bk-list clearfix">
      %count = 0
        %for entry in content:
        %count += 1
        %TAG_RE = re.compile(r'<[^>]+>')
        %string=TAG_RE.sub('', entry.comments[0].text).replace("Kurzbeschreibung","").replace("Klappentext","").replace("Amazon","")
      <li>
        <div class="bk-book book-1 bk-bookdefault">
          <div class="bk-front">
            <div class="bk-cover" style="background: url('/download/{{entry.path}}/cover.jpg'); background-size: cover;">
              <!-- <h2>
                <span>{{entry.authors[0].name}}</span>
                <span>{{entry.title}}</span>
              </h2> -->
            </div>
            <div class="bk-cover-back"></div>
          </div>
          <div class="bk-page">
            <div class="bk-content bk-content-current">
              <p>{{string[:400]}}</p>
            </div>
            <div class="bk-content">
              <p>{{string[400:800]}}</p>
            </div>
            <div class="bk-content">
              <p>{{string[800:1200]}}</p>
            </div>
          </div>
          <div class="bk-back">
            <p>{{string[:400]}}</p>
          </div>
          <div class="bk-right"></div>
          <div class="bk-left">
            <h2>
              <span>{{entry.authors[0].name}}</span>
              <span>{{entry.title}}</span>
            </h2>
          </div>
          <div class="bk-top"></div>
          <div class="bk-bottom"></div>
        </div>
        <div class="bk-info">
          <button class="bk-bookback">Flip</button>
          <button class="bk-bookview">View inside</button>
          <button class="bk-bookback">epub</button>
          <h3>
            <span>{{entry.authors[0].name}}</span>
            <span>{{entry.title}}</span>
          </h3>

          <p>{{string[:100]}} [...]</p>
        </div>
      </li>
       %end for

     </ul>
  </div>
</div>
<footer>

</footer>


  <!-- JavaScript at the bottom for fast page loading -->

  <!-- Grab Google CDN's jQuery, with a protocol relative URL; fall back to local if offline -->
  <script src="/static/js/libs/jquery-1.8.1.min.js"></script>

  <!-- scripts concatenated and minified via build script -->
  <script src="/static/js/books1.js"></script>
  <script type="text/javascript">
    $(function() {

        Books.init();

      });
  </script>
  <!-- end scripts -->


</body>
</html>

