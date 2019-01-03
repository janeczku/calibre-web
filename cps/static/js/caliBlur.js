// Move advanced search to side-menu
$( 'a[href*="advanced"]' ).parent().insertAfter( '#nav_new' );
$( 'body' ).addClass('blur');

// Back button
curHref = window.location.href.split('/');
prevHref = document.referrer.split('/');
$( '.navbar-form.navbar-left' )
  .before( '<div class="plexBack"><a href="' + document.referrer + '"></a></div>' );
if ( history.length === 1 ||
    curHref[0] +
    curHref[1] +
    curHref[2] !=
    prevHref[0] +
    prevHref[1] +
    prevHref[2] ||
  $( 'body.root' )>length > 0 ) {
    $( '.plexBack' ).addClass( 'noBack' );
}

//Weird missing a after pressing back from edit.
setTimeout(function() {
  if ( $( '.plexBack a').length < 1 ) {
    $( '.plexBack' ).append('<a href="' + document.referrer + '"></a>');
  }
},10);

// Home button
$( '.plexBack' ).before( '<div class="home-btn"></div>' );
$( 'a.navbar-brand' ).clone().appendTo( '.home-btn' ).empty().removeClass('navbar-brand');
/////////////////////////////////
// Start of Book Details Work //
///////////////////////////////

// Wrap book description in div container
if ( $( 'body.book' ).length > 0 ) {

  /* description = $( 'h3:contains("Description:")' ).nextUntil( '.morestuff' ).slice(0,-1);
  bookInfo = $( '.author' ).nextUntil( 'h3:contains("Description:")');
  $( 'h3:contains("Description:")' ).hide();
  $( description ).detach();
  $( bookInfo ).wrapAll( '<div class="bookinfo"></div>' );
  $( 'h3:contains("Description:")' ).after( '<div class="description"></div>' );
  $( '.languages' ).appendTo( '.bookinfo' );
  $('.hr').detach();
  if ( $( '.identifiers ').length > 0 ) {
    console.log(".identifiers length " + $( '.identifiers ').length );
      $( '.identifiers' ).before( '<div class="hr"></div>' );
    } else {
    if ( $( '.bookinfo > p:first-child' ).length > 0 ) {
      console.log(".bookinfo > p:first-child length " +  $( '.bookinfo > p' ).length );
      $( '.bookinfo > p:first-child' ).first().after( '<div class="hr"></div>' );
      } else{
        if ( $( '.bookinfo a[href*="/series/"]' ).length > 0 ) {
          console.log( 'series text found; placing hr below series' );
          $( '.bookinfo a[href*="/series/"]' ).parent().after( '<div class="hr"></div>' );
        } else {
        console.log("prepending hr div to top of .bookinfo");
      $( '.bookinfo' ).prepend( '<div class="hr"></div>' );
      }
    }
  }
  $( '.rating' ).insertBefore( '.hr' );
  $( 'div.description' ).hide();
  $( '#remove-from-shelves' ).insertAfter( '.hr' );

  /* if book description is not in html format, Remove extra line breaks
  Remove blank lines/unnecessary spaces, split by line break to array
  Push array into .description div. If there is still a wall of text,
  find sentences and split wall into groups of three sentence paragraphs.
  If the book format is in html format, Keep html, but strip away inline
  styles and empty elements */
/*
  // If text is sitting in div as text node
  if ( description[0] === undefined ) {
    textValue = $( '.book-meta' )
      .contents()
      .filter(function() {
        return this.nodeType == Node.TEXT_NODE;
      }).text();
    description = $.makeArray(
      textValue.replace(/(?:(?:\r\n|\r|\n)\s*){2}/gm, "")
    );
    $( '.book-meta' ).contents().filter(function() {
      return this.nodeType === 3;
    }).remove();
  }
  if ( description[1] === undefined ) {
    newdesc = description.toString()
    .replace(/^(?=\n)$|^\s*|\s*$|\n\n+/gm,"").split(/\n/);
    $.each(newdesc, function(i, val) {
    $( 'div.description' ).append( '<p>' + newdesc[i] + '</p>' );
    });
    $( '.description' ).fadeIn(100);
    //If still a wall of text create 3 sentence paragraphs.
   if( $( '.description p' ).length === 1 ) {
     if ( description.context != undefined ) {
     newdesc = description.text()
      .replace(/^(?=\n)$|^\s*|\s*$|\n\n+/gm,"").split(/\n/);
     }
     else {
       newdesc = description.toString();
     }
     doc = nlp ( newdesc.toString() );
     sentences = doc.map((m)=> m.out( 'text' ));
     $( '.description p' ).remove();
     let size = 3; let sentenceChunks = [];
     for (var i=0; i<sentences.length; i+=size) {
       sentenceChunks.push(sentences.slice(i,i+size));
     }
     let output = '';
     $.each(sentenceChunks, function(i, val) {
         let preOutput = '';
         $.each(val, function(i, val) {
         preOutput += val;
       });
       output += '<p>' + preOutput + '</p>';
     });
     $( 'div.description' ).append( output );
   }
  } else {
      $.each(description, function(i, val) {
      $( description[i].outerHTML ).appendTo( '.description' );
      $( 'div.description :empty' ).remove();
      $( 'div.description ').attr( 'style', '' );
      });
    $( 'div.description' ).fadeIn( 100 );
  }*/

  description = $( '.comments' );
  bookInfo = $( '.author' ).nextUntil( 'h3:contains("Description:")');
  $( 'h3:contains("Description:")' ).detach();
  $( '.comments' ).detach();
  $( bookInfo ).wrapAll( '<div class="bookinfo"></div>' );
//  $( 'h3:contains("Description:")' ).after( '<div class="description"></div>' );
  $( '.languages' ).appendTo( '.bookinfo' );
  $('.hr').detach();
  if ( $( '.identifiers ').length > 0 ) {
    console.log(".identifiers length " + $( '.identifiers ').length );
      $( '.identifiers' ).before( '<div class="hr"></div>' );
    } else {
    if ( $( '.bookinfo > p:first-child' ).length > 0 ) {
      console.log(".bookinfo > p:first-child length " +  $( '.bookinfo > p' ).length );
      $( '.bookinfo > p:first-child' ).first().after( '<div class="hr"></div>' );
      } else{
        if ( $( '.bookinfo a[href*="/series/"]' ).length > 0 ) {
          console.log( 'series text found; placing hr below series' );
          $( '.bookinfo a[href*="/series/"]' ).parent().after( '<div class="hr"></div>' );
        } else {
        console.log("prepending hr div to top of .bookinfo");
      $( '.bookinfo' ).prepend( '<div class="hr"></div>' );
      }
    }
  }
  $( '.rating' ).insertBefore( '.hr' );
  $( '#remove-from-shelves' ).insertAfter( '.hr' );
  $( description ).appendTo('.bookinfo')
  /* if book description is not in html format, Remove extra line breaks
  Remove blank lines/unnecessary spaces, split by line break to array
  Push array into .description div. If there is still a wall of text,
  find sentences and split wall into groups of three sentence paragraphs.
  If the book format is in html format, Keep html, but strip away inline
  styles and empty elements */

  // If text is sitting in div as text node
  if ( $('.comments:has(p)' ).length === 0 ) {
    newdesc = description.text()
    .replace(/^(?=\n)$|^\s*|\s*$|\n\n+/gm,"").split(/\n/);
    $('.comments' ).empty();
    $.each(newdesc, function(i, val) {
    $( 'div.comments' ).append( '<p>' + newdesc[i] + '</p>' );
    });
    $( '.comments' ).fadeIn(100);
  }    //If still a wall of text create 3 sentence paragraphs.
   if( $( '.comments p' ).length === 1 ) {
     if ( description.context != undefined ) {
     newdesc = description.text()
      .replace(/^(?=\n)$|^\s*|\s*$|\n\n+/gm,"").split(/\n/);
     }
     else {
       newdesc = description.toString();
     }
     doc = nlp ( newdesc.toString() );
     sentences = doc.map((m)=> m.out( 'text' ));
     sentences[0] = sentences[0].replace(",","");
     $( '.comments p' ).remove();
     let size = 3; let sentenceChunks = [];
     for (var i=0; i<sentences.length; i+=size) {
       sentenceChunks.push(sentences.slice(i,i+size));
     }
     let output = '';
     $.each(sentenceChunks, function(i, val) {
         let preOutput = '';
         $.each(val, function(i, val) {
         preOutput += val;
       });
       output += '<p>' + preOutput + '</p>';
     });
     $( 'div.comments' ).append( output );
   }
   else {
      $.each(description, function(i, val) {
//      $( description[i].outerHTML ).appendTo( '.comments' );
      $( 'div.comments :empty' ).remove();
      $( 'div.comments ').attr( 'style', '' );
      });
    $( 'div.comments' ).fadeIn( 100 );
  }

  // Sexy blurred backgrounds
  cover = $( '.cover img' ).attr( 'src' );
  $( '#loader + .container-fluid' )
    .prepend( '<div class="blur-wrapper"></div' );
  $( '.blur-wrapper' )
    .prepend( '<div><img class="bg-blur" src="' + cover + '"></div>' );

  // Fix-up book detail headings
  publisher = $( '.publishers p span' ).text().split( ': ' );
  $( '.publishers p span' ).remove();
  $.each(publisher, function(i, val) {
    $( '.publishers' ).append( '<span>' + publisher[i] + '</span>' );
  });
  published = $( '.book-meta p:contains("Publishing date")' )
  .text().split(': ');
  $( '.book-meta p:contains("Publishing date")' )
  .before( '<div class="published-date"></div>' );
  $( '.book-meta p:contains("Publishing date")' ).remove();
  $.each(published, function(i, val) {
    $( '.published-date' ).append( '<span>' + published[i] + '</span>' );
  });
  languages = $( '.languages p span' ).text().split( ': ' );
  $( '.languages p span' ).remove();
  $.each(languages, function(i, val) {
    $( '.languages' ).append( '<span>' + languages[i] + '</span>' );
  });

  $( '.book-meta h2:first' ).clone()
  .prependTo( '.book-meta > .btn-toolbar:first' );


  // If only one download type exists still put the items into a drop-drown list.
  downloads = $( 'a[id^=btnGroupDrop]' ).get();
  if ( $( downloads ).length === 1 ) {
    $( '<button id="btnGroupDrop1" type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"><span class="glyphicon glyphicon-download"></span>Download :<span class="caret"></span></button><ul class="dropdown-menu leramslist aria-labelledby="btnGroupDrop1"></ul>' ).insertBefore( downloads[downloads.length-1] );
    $( downloads ).detach();
    $.each(downloads, function(i, val) {
      $( '<li>' + downloads[i].outerHTML + '</li>' ).appendTo( '.leramslist' );
    });
    $( '.leramslist' ).find( 'span' ).remove();
    $( '.leramslist a' ).removeClass( 'btn btn-primary' ).removeAttr( 'role' );
  }

  // Add classes to buttons
  $( '#sendbtn' ).parent().addClass( 'sendBtn' );
  $( '[id*=btnGroupDrop]' ).parent().addClass( 'downloadBtn' );
  $( 'read-in-browser' ).parent().addClass( 'readBtn' );
  $( '.downloadBtn button:first' ).addClass( 'download-text' );

  // Move all options in book details page to the same group
  $( '[aria-label*="Delete book"]' )
    .prependTo( '[aria-label^="Download, send"]' )
    .children().removeClass( 'btn-sm' );
  $( '.custom_columns' )
    .addClass(' btn-group' )
    .attr('role', 'group' )
    .removeClass( 'custom_columns' )
    .prependTo( '[aria-label^="Download, send"]' );
  $( '#have_read_cb' )
    .after( '<label class="block-label readLbl" for="#have_read_cb"></label>' );
  $( '#shelf-actions' ).prependTo( '[aria-label^="Download, send"]' );


  // Move dropdown lists higher in dom, replace bootstrap toggle with own toggle.
  $( 'ul[aria-labelledby="read-in-browser"]' ).insertBefore( '.blur-wrapper' ).addClass('readinbrowser-drop');
  $( '.leramslist' ).insertBefore( '.blur-wrapper' );
  $( 'ul[aria-labelledby="btnGroupDrop1"]' ).insertBefore( '.blur-wrapper' ).addClass('leramslist');
  $( '#add-to-shelves' ).insertBefore( '.blur-wrapper' );

  $( '#read-in-browser' ).click( function() {
    $(  '.readinbrowser-drop' ).toggle();
  });

  $('.downloadBtn' ).click( function() {
    $(  '.leramslist' ).toggle();
  });

  $('div[aria-label="Add to shelves"]' ).click( function() {
    $(  '#add-to-shelves' ).toggle();
  });

  // Fix formatting error on book detail languages
  if ( !$( '.book-meta > .bookinfo > .languages > span:last-of-type' ).text().startsWith(" ") ) {
      $( '.book-meta > .bookinfo > .languages > span:last-of-type' ).prepend(" ");
  }

  //Work to reposition dropdowns. Does not currently solve for
  //screen resizing
  function dropdownToggle() {

    topPos = $( '.book-meta > .btn-toolbar:first' ).offset().top

    if ( $( '#read-in-browser' ).length > 0 ) {
      position = $( '#read-in-browser'  ).offset().left
      if ( position + $(  '.readinbrowser-drop' ).width() > $( window ).width() ) {
        positionOff = position + $( '.readinbrowser-drop' ).width() - $( window ).width();
        ribPosition = position - positionOff - 5
        $( '.readinbrowser-drop' ).attr("style", "left: " + ribPosition + "px !important; right: auto; top: " + topPos + "px");
      } else {
          $( '.readinbrowser-drop' ).attr("style", "left: " + position + "px !important; right: auto; top: " + topPos + "px");
      }
    }

    if ( $( '.downloadBtn' ).length > 0 ) {

      position = $( '#btnGroupDrop1'  ).offset().left

      if ( position + $(  '.leramslist' ).width() > $( window ).width() ) {
        positionOff = position + $( '.leramslist' ).width() - $( window ).width();
        dlPosition = position - positionOff - 5
        $( '.leramslist' ).attr("style", "left: " + dlPosition + "px !important; right: auto;  top: " + topPos + "px");
      } else {
        $( '.leramslist' ).attr("style", "left: " + position + "px !important; right: auto;  top: " + topPos + "px");
      }
    }

    if ( $( 'div[aria-label="Add to shelves"]' ).length > 0 ) {

      position = $( 'div[aria-label="Add to shelves"]'  ).offset().left

      if ( position + $(  '#add-to-shelves' ).width() > $( window ).width() ) {
        positionOff = position + $( '#add-to-shelves' ).width() - $( window ).width();
        adsPosition = position - positionOff - 5
        $(  '#add-to-shelves' ).attr("style", "left: " + adsPosition + "px !important; right: auto;  top: " + topPos + "px");
      } else {
        $(  '#add-to-shelves' ).attr("style", "left: " + position + "px !important; right: auto;  top: " + topPos + "px");
      }
    }
  }
  dropdownToggle();

  $( window ).on( 'resize', function() {
    dropdownToggle();
  });

// Clone book rating for mobile view.
$( '.book-meta > .bookinfo > .rating' ).clone().insertBefore( '.book-meta > .description' ).addClass('rating-mobile');
}

///////////////////////////////
// End of Book Details Work //
/////////////////////////////

/////////////////////////////////
//    Start of Global Work    //
///////////////////////////////

// Hide dropdown and collapse menus on click-off
$(document).mouseup(function (e) {
  var container = new Array();
  container.push($('ul[aria-labelledby="read-in-browser"]'));
  container.push($('.leramslist'));
  container.push($('#add-to-shelves'));
  container.push($('.navbar-collapse.collapse.in'));

  $.each(container, function(key, value) {
    if (!$(value).is(e.target) // if the target of the click isn't the container...
    && $(value).has(e.target).length === 0) // ... nor a descendant of the container
    {
      if ( $(value).hasClass('dropdown-menu') )
      {
        $(value).hide();
      } else
      {
        if ( $(value).hasClass('collapse') )
        {
          $(value).collapse('toggle');
        }
      }
    }
  });
});

// Split path name to array and remove blanks
url = window.location.pathname
  .split( "/" ).filter( function(v){return v!==''} );
// Add classes to some body elements that don't have it
if ( jQuery.inArray( 'epub', url ) != -1 ) {
  $( 'body' ).addClass( url[3] );
} else {
  $( 'body' ).addClass( url[1] );
}
if ( $( 'body.shelf' ).length > 0 ) {
  $( 'a[href*= "'+url[1]+"/"+url[2]+'"]' )
    .parent()
    .addClass( 'active' );
}

// Move create shelf
$( '#nav_createshelf' ).prependTo( 'li:contains("Your Shelves")' );

// Create drop-down for profile and move elements to it
$( '#main-nav' )
  .prepend( '<li class="dropdown"><a href="#" class="dropdown-toggle profileDrop" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false"><span class="glyphicon glyphicon-user"></span></a><ul class="dropdown-menu profileDropli"></ul></li>' );
$( '#top_user' ).parent().addClass( 'dropdown' ).appendTo( '.profileDropli' );
$( '#nav_about' ).addClass( 'dropdown' ).appendTo( '.profileDropli' );
$( '#register' ).parent().addClass( 'dropdown' ).appendTo( '.profileDropli' );
$( '#logout' ).parent().addClass( 'dropdown' ).appendTo( '.profileDropli' );

// Remove the modals except from some areas where they are needed
bodyClass = $( 'body' ).attr( 'class' ).split(' ');
modalWanted = ['admin', 'editbook', 'config', 'uiconfig'];

if ( $.inArray( bodyClass[0], modalWanted) != -1 ) {
} else {
  $(' a:not(.dropdown-toggle) ')
    .removeAttr( 'data-toggle', 'data-target', 'data-remote' );
}


// Add classes to global buttons
$( '#top_tasks' ).parent().addClass( 'top_tasks' );
$( '#top_admin' ).parent().addClass( 'top_admin' );
$( '#form-upload' ).parent().addClass( 'form-upload' );

// Search button work
$( 'input#query' ).focus(function() {
      $( 'form[role="search"]' ).addClass( 'search-focus' );
});
$( 'input#query' ).focusout(function() {
  setTimeout(function() {
            $( 'form[role="search"]' ).removeClass( 'search-focus' );
  }, 100);
});

// Add class to random book discover
// ToDo: done
$( 'h2:contains("Discover (Random Books")' )
  .parent()
  .addClass( 'random-books' );

// Check if dropdown goes out of viewport and add class

$(document).on('click','.dropdown-toggle',function() {
 // Add .offscreen if part of container not visible
  $('.dropdown-menu:visible').filter(function(){
    return $(this).visible() === false;
  }).each(function(){
    $(this).addClass('offscreen');
  });
});

// Fade out content on page unload
// delegate all clicks on "a" tag (links)
$(document).on("click", "a:not(.btn-toolbar a, a[href*='shelf/remove'], .identifiers a, .bookinfo , .btn-group > a, #add-to-shelves a, #book-list a, .stat.blur.stats a )", function () {

    // get the href attribute
    var newUrl = $(this).attr("href");

    // veryfy if the new url exists or is a hash
    if (!newUrl || newUrl[0] === "#") {
        // set that hash
        location.hash = newUrl;
        return;
    }

    // now, fadeout the html (whole page)
      $( '.blur-wrapper' ).fadeOut(250);
    $(".row-fluid .col-sm-10").fadeOut(500,function () {
        // when the animation is complete, set the new location
        location = newUrl;
    });

    // prevent the default browser behavior.
    return false;
});

// Collapse long text into read-more
$( 'div.comments' ).readmore( {
  collapsedHeight: 134,
  heightMargin: 45,
  speed: 300,
  moreLink: '<a href="#">READ MORE</a>',
  lessLink: '<a href="#">READ LESS</a>',
});
/////////////////////////////////
//     End of Global Work     //
///////////////////////////////

// Author Page Background Blur
if ( $( 'body.author' ).length >0 ) {
  cover = $( '.author-bio img' ).attr( 'src' );
  $( '#loader + .container-fluid' )
    .prepend( '<div class="blur-wrapper"></div>' );
  $( '.blur-wrapper' ).prepend( '<img class="bg-blur" src="' + cover + '">' );
  // Place undefined cover images inside container
  if ( $( '.bg-blur[src="undefined"]' ).length > 0 ) {
    $( '.bg-blur' ).before( '<div class="bg-blur undefined-img"></div>' );
    $( 'img.bg-blur' ).appendTo( '.undefined-img' );
  }
}

// Ereader Page - add class to iframe body on ereader page after it loads.
backurl = '../../book/' + url[2]
$( 'body.epub #title-controls' )
  .append('<div class="epub-back"><input action="action" onclick="location.href=backurl; return false;" type="button" value="Back" /></div>')

$(  'body.stats .col-sm-10 p:first' ).insertAfter( '#libs' );

// Check if link is external and force _blank attribute
$(function(){ // document ready
  $( 'a' ).filter(function () {
      return this.hostname && this.hostname !== location.hostname;
  }).each(function () {
      $(this).addClass("external").attr( 'target', '_blank' );
  });
});

// Check if lists are empty and add class to buttons
if ( $.trim( $('#add-to-shelves').html() ).length === 0 ) {
  $( '#add-to-shelf' ).addClass( 'empty-ul' );
}

shelfLength = $('#add-to-shelves li').length
emptyLength = 0

$('#add-to-shelves').on('click','li a',function(){
  console.log('#remove-from-shelves change registered' );
  emptyLength++

  setTimeout(function() {
    if ( emptyLength >= shelfLength ) {
        console.log('list is empty; adding empty-ul class' );
      $( '#add-to-shelf' ).addClass( 'empty-ul' );
    } else {
      console.log('list is not empty; removing empty-ul class' );
      $( '#add-to-shelf' ).removeClass( 'empty-ul' );
    }
  },100);
});

if ( $.trim( $( 'ul[aria-labelledby="read-in-browser"] li' ).html() ).length === 0 ) {
  $('#read-in-browser').addClass('empty-ul');
}

// Shelf Buttons and Tooltips
if ( $( 'body.shelf' ).length > 0 ) {
  $( 'div[data-target="#DeleteShelfDialog"]' )
    .before( '<div class=".btn-group shelf-btn-group"></div>' )
    .appendTo( '.shelf-btn-group' )
    .addClass( 'delete-shelf-btn' );

    $( 'a[href*="edit"]' )
      .appendTo( '.shelf-btn-group' )
      .addClass( 'edit-shelf-btn' );

    $( 'a[href*="order"]' )
      .appendTo( '.shelf-btn-group' )
      .addClass( 'order-shelf-btn' );
  $( '.delete-shelf-btn' ).attr({
      'data-toggle-two': 'tooltip',
      'title': 'Delete Shelf',
      'data-placement': 'bottom' })
      .addClass('delete-btn-tooltip');

  $( '.edit-shelf-btn' ).attr({
      'data-toggle-two': 'tooltip',
      'title': 'Edit Shelf',
      'data-placement': 'bottom' })
      .addClass('edit-btn-tooltip');

  $( '.order-shelf-btn' ).attr({
      'data-toggle-two': 'tooltip',
      'title': 'Reorder Shelf',
      'data-placement': 'bottom' })
      .addClass('order-btn-tooltip');
}

// Rest of Tooltips
$( '.home-btn > a' ).attr({
    'data-toggle': 'tooltip',
    'title': 'Home',
    'data-placement': 'bottom' })
    .addClass('home-btn-tooltip');

$( '.plexBack > a' ).attr({
   'data-toggle': 'tooltip',
   'title': 'Back',
   'data-placement': 'bottom' })
   .addClass('back-btn-tooltip');

$( '#top_tasks' ).attr({
    'data-toggle': 'tooltip',
    'title': 'Tasks',
    'data-placement': 'bottom',
    'data-viewport': '#main-nav' })
    .addClass('tasks-btn-tooltip');

$( '#top_admin' ).attr({
  'data-toggle': 'tooltip',
  'title': 'Settings',
  'data-placement': 'bottom',
  'data-viewport': '#main-nav' })
  .addClass('admin-btn-tooltip');

$( '.profileDrop' ).attr({
  'title': 'Account',
  'data-placement': 'bottom',
  'data-toggle-two': 'tooltip',
  'data-viewport': '#main-nav' })
  .addClass('send-btn-tooltip dropdown');

$( '#btn-upload' ).attr({
  'data-toggle': 'tooltip',
  'title': 'Upload',
  'data-placement': 'bottom',
  'data-viewport': '#main-nav' })
  .addClass('upload-btn-tooltip');

$( '#add-to-shelf' ).attr({
  'data-toggle-two': 'tooltip',
  'title': 'Add to Shelf',
  'data-placement': 'bottom',
  'data-viewport': '.btn-toolbar' })
  .addClass('addtoshelf-btn-tooltip');

$( '#have_read_cb' ).attr({
  'data-toggle': 'tooltip',
  'title': 'Mark As Read',
  'data-placement': 'bottom',
  'data-viewport': '.btn-toolbar' })
  .addClass('readunread-btn-tooltip');

$( '#have_read_cb:checked' ).attr({
  'data-toggle': 'tooltip',
  'title': 'Mark As Unread',
  'data-placement': 'bottom',
  'data-viewport': '.btn-toolbar' })
  .addClass('readunread-btn-tooltip');

  $( 'button#delete' ).attr({
    'data-toggle-two': 'tooltip',
    'title': 'Delete',
    'data-placement': 'bottom',
    'data-viewport': '.btn-toolbar' })
    .addClass('delete-book-btn-tooltip');

$( '#have_read_cb' ).click(function() {
  if ( $( '#have_read_cb:checked' ).length > 0 ) {
      $( this ).attr('data-original-title', 'Mark as Unread');
  } else {
      $( this).attr('data-original-title', 'Mark as Read');
  }
});

$( '.btn-group[aria-label="Edit/Delete book"] a' ).attr({
   'data-toggle': 'tooltip',
   'title': 'Edit',
   'data-placement': 'bottom',
   'data-viewport': '.btn-toolbar' })
   .addClass('edit-btn-tooltip');

$( '#sendbtn' ).attr({
  'data-toggle': 'tooltip',
  'title': 'Send to Kindle',
  'data-placement': 'bottom',
  'data-viewport': '.btn-toolbar' })
  .addClass('send-btn-tooltip');

$( '#read-in-browser' ).attr({
  'data-toggle-two': 'tooltip',
  'title': 'Read',
  'data-placement': 'bottom',
  'data-viewport': '.btn-toolbar'})
  .addClass('send-btn-tooltip');

$( '#btnGroupDrop1' ).attr({
  'data-toggle-two': 'tooltip',
  'title': 'Download',
  'data-placement': 'bottom',
  'data-viewport': '.btn-toolbar' });

if ( $( 'body.epub').length === 0 ) {
  $(document).ready(function(){
      $('[data-toggle="tooltip"]').tooltip({container: 'body', trigger: 'hover'});
      $('[data-toggle-two="tooltip"]').tooltip({container: 'body', trigger: 'hover'});
      $( '#btn-upload' ).attr('title', " ");
  });


  $( '[data-toggle-two="tooltip"]' ).click(function(){
       $('[data-toggle-two="tooltip"]').tooltip('hide');
  });

  $( '[data-toggle="tooltip"]' ).click(function(){
      $('[data-toggle="tooltip"]').tooltip('hide');
  });
}

$( '#read-in-browser a' ).attr('target',"");

if ( $( '.edit-shelf-btn').length > 1 ) {
  $( '.edit-shelf-btn:first').remove();
}
if ( $( '.order-shelf-btn').length > 1 ) {
  $( '.order-shelf-btn:first').remove();
}

$( '#top_user > span.hidden-sm' ).clone().insertBefore( '.profileDropli' );
$( '.navbar-collapse.collapse.in').before('<div class="sidebar-backdrop"></div>');

// Get rid of leading white space
recentlyAdded = $( '#nav_new a:contains("Recently")' ).text().trim();
$('#nav_new a:contains("Recently")').contents().filter(function() {
    return this.nodeType == 3
}).each(function(){
    this.textContent = this.textContent.replace(' Recently Added',recentlyAdded);
});

// Change shelf textValue
shelfText = $( '.shelf .discover h2:first' ).text().replace(':',' —').replace(/\'/g,'');
$( '.shelf .discover h2:first' ).text(shelfText);

shelfText = $( '.shelforder .col-sm-10 .col-sm-6.col-lg-6.col-xs-6 h2:first' ).text().replace(':',' —').replace(/\'/g,'');
$( '.shelforder .col-sm-10 .col-sm-6.col-lg-6.col-xs-6 h2:first' ).text(shelfText);


function mobileSupport() {
if ( $( window ).width() <= 768 ) {
  //Move menu to collapse
  $( '.row-fluid > .col-sm-2:first' ).appendTo( '.navbar-collapse.collapse:first');
  if ( $( '.sidebar-backdrop' ).length < 1 ) {
    $( '.navbar-collapse.collapse:first' ).after( '<div class="sidebar-backdrop"></div>' );
  }
   } else {
  //Move menu out of collapse
    $( '.col-sm-2:first' ).insertBefore( '.col-sm-10:first');
    $( '.sidebar-backdrop' ).remove();
   }
}

// LayerCake plug
if ( $(' .stat.blur.stats p').length > 0 ) {
  $(' .stat.blur.stats p').append(" and <a href='https://github.com/leram84/layer.Cake/tree/master/caliBlur' target='_blank'>layer.Cake</a>");
  str = $(' .stat.blur.stats p').html().replace("</a>.","</a>");
  $(' .stat.blur.stats p').html(str);
}
// Collect delete buttons in editbook to single dropdown
$( '.editbook .text-center.more-stuff' ).prepend( '<button id="deleteButton" type="button" class="btn btn-danger dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"><span class="glyphicon glyphicon-remove"></span>Delete Format<span class="caret"></span></button><ul class="dropdown-menu delete-dropdown"></ul>' );

deleteButtons = $(  '.editbook .text-center.more-stuff a' ).removeClass('btn btn-danger' ).attr( 'type', '').get();

$( deleteButtons ).detach();
$( '.editbook .text-center.more-stuff h4' ).remove();
$.each(deleteButtons, function(i, val) {
  $( '<li>' + deleteButtons[i].outerHTML + '</li>' ).appendTo( '.delete-dropdown' );
});

// Turn off bootstrap animations
$(function() { $.support.transition = false; })

mobileSupport();

// Only call function once resize is complete
//var id;
$( window ).on('resize',function() {
//  clearTimeout(id);
//  id = setTimeout(mobileSupport, 500);
mobileSupport();
});
