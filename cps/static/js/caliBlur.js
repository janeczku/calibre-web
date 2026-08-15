/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018-2019  hexeth
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
// Back button
curHref = window.location.href.split("/");
prevHref = document.referrer.split("/");
$(".plexBack a").attr('href', encodeURI(document.referrer));

if (history.length === 1 ||
    curHref[0] +
    curHref[1] +
    curHref[2] !=
    prevHref[0] +
    prevHref[1] +
    prevHref[2] ||
    $("body.root") > length > 0) {
    $(".plexBack").addClass("noBack");
}

//Weird missing a after pressing back from edit.
setTimeout(function () {
    $(".plexBack a").attr('href', encodeURI(document.referrer));
}, 10);

/////////////////////////////////
// Start of Book Details Work //
///////////////////////////////

// Wrap book description in div container
if ($("body.book").length > 0) {

    description = $(".comments");
    bookInfo = $(".author").nextUntil("#decription");
    $("#decription").detach();
    $(".comments").detach();
    $(bookInfo).wrapAll('<div class="bookinfo"></div>');
//  $( 'h3:contains("Description:")' ).after( '<div class="description"></div>' );
    $(".languages").appendTo(".bookinfo");
    $(".hr").detach();
    if ($(".identifiers ").length > 0) {
        $('.identifiers').before('<div class="hr"></div>');
    } else {
        if ($(".bookinfo > p:first-child").length > 0) {
            $(".bookinfo > p:first-child").first().after('<div class="hr"></div>');
        } else {
            if ($('.bookinfo a[href*="/series/"]').length > 0) {
                $('.bookinfo a[href*="/series/"]').parent().after('<div class="hr"></div>');
            } else {
                $(".bookinfo").prepend('<div class="hr"></div>');
            }
        }
    }
    $(".rating").insertBefore(".hr");
    $("#remove-from-shelves").insertAfter(".hr");
    $(description).appendTo(".bookinfo")

    // Sexy blurred backgrounds
    cover = $(".cover img").attr("src");
    $("#loader + .container-fluid")
        .prepend("<div class='blur-wrapper'></div>");
    $(".blur-wrapper")
        .prepend('<div><img alt="Blurred cover" class="bg-blur" src="' + cover + '"></div>');

    // Metadata Fields - Publishers, Published, Languages and Custom
    $('.publishers, .publishing-date, .real_custom_columns, .languages').each(function () {
        var splitText = $(this).text().split(':');
        var label = splitText.shift().trim();
        var value = splitText.join(':').trim();
        var class_value = ""
        // Preserve Links
        if ($(this).find('a').length) {
            value = $(this).find('a').first().removeClass();
        }
        // Preserve glyphicons
        if ($(this).find('span').length) {
            class_value = $(this).find('span').first().attr('class');
        }
        $(this).html('<span>' + label + '</span><span class="' + class_value + '"></span>').find('span').last().append(value);
    });

    $(".book-meta h2:first").clone()
        .prependTo(".book-meta > .btn-toolbar:first");

    $(".more-stuff .col-sm-12 #back").hide()

// Clone book rating for mobile view.
    $(".book-meta > .bookinfo > .rating").clone().insertBefore(".book-meta > .description").addClass("rating-mobile");
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
    container.push($(".navbar-collapse.collapse.in"));

    $.each(container, function (key, value) {
        if (!$(value).is(e.target) // if the target of the click isn't the container...
            && $(value).has(e.target).length === 0) // ... nor a descendant of the container
        {
            if ($(value).hasClass("dropdown-menu")) {
                $(value).hide();
            } else {
                if ($(value).hasClass("collapse")) {
                    $(value).collapse("toggle");
                }
            }
        }
    });
});

// Remove the modals except from some areas where they are needed
bodyClass = $("body").attr("class").split(" ");
modalWanted = ["admin", "editbook", "config", "uiconfig", "me", "edituser"];

if ($.inArray(bodyClass[0], modalWanted) != -1) {
} else {
    $(" a:not(.dropdown-toggle) ")
        .removeAttr("data-toggle", "data-target", "data-remote");
}


// Search button work
$("input#query").focus(function () {
    $('form[role="search"]').addClass("search-focus");
});
$("input#query").focusout(function () {
    setTimeout(function () {
        $('form[role="search"]').removeClass("search-focus");
    }, 100);
});

// Check if dropdown goes out of viewport and add class

$(document).on("click", ".dropdown-toggle", function () {
    // Add .offscreen if part of container not visible
    $(".dropdown-menu:visible").filter(function () {
        return $(this).visible() === false;
    }).each(function () {
        $(this).addClass("offscreen");
    });
});

// Collapse long text into read-more
var readMoreText = $("body").data("readmore-more") || "READ MORE";
var readLessText = $("body").data("readmore-less") || "READ LESS";
$("div.comments").readmore({
    collapsedHeight: 134,
    heightMargin: 45,
    speed: 300,
    moreLink: '<a href="#">' + readMoreText + '</a>',
    lessLink: '<a href="#">' + readLessText + '</a>',
});
/////////////////////////////////
//     End of Global Work     //
///////////////////////////////

// Author Page Background Blur
if ($("body.author").length > 0) {
    cover = $(".author-bio img").attr("src");
    $("#loader + .container-fluid")
        .prepend('<div class="blur-wrapper"></div>');
    $(".blur-wrapper").prepend('<img alt="Blurred author bio" class="bg-blur" src="' + cover + '">');
    // Place undefined cover images inside container
    if ($('.bg-blur[src="undefined"]').length > 0) {
        $(".bg-blur").before('<div class="bg-blur undefined-img"></div>');
        $("img.bg-blur").appendTo('.undefined-img');
    }
}

// Split path name to array and remove blanks
url = window.location.pathname
// Ereader Page - add class to iframe body on ereader page after it loads.
backurl = "../../book/" + url[2]
$("body.epub #title-controls")
    .append('<div class="epub-back"><input action="action" onclick="location.href=backurl; return false;" type="button" value="Back" /></div>')

// Check if link is external and force _blank attribute
$(function () { // document ready
    $("a").filter(function () {
        return this.hostname && this.hostname !== location.hostname;
    }).each(function () {
        $(this).addClass("external").attr("target", "_blank");
    });
});

// Keep add-to-shelf button state in sync with current dropdown content
function updateAddToShelfState() {
    if ($("#add-to-shelves li").length === 0) {
        $("#add-to-shelf").addClass("empty-ul");
    } else {
        $("#add-to-shelf").removeClass("empty-ul");
    }
}

updateAddToShelfState();

$("#add-to-shelves, #remove-from-shelves").on("click", "[data-shelf-action]", function () {
    setTimeout(updateAddToShelfState, 100);
});

// Rest of Tooltips
if ($("body.epub").length === 0) {
    $(document).ready(function () {
        $("[data-toggle='tooltip']").tooltip({container: "body", trigger: "hover"});
        $("[data-toggle-two='tooltip']").tooltip({container: "body", trigger: "hover"});
    });


    $('[data-toggle-two="tooltip"]').click(function () {
        $('[data-toggle-two="tooltip"]').tooltip("hide");
    });

    $('[data-toggle="tooltip"]').click(function () {
        $('[data-toggle="tooltip"]').tooltip("hide");
    });
}

if ($(".edit-shelf-btn").length > 1) {
    $(".edit-shelf-btn:first").remove();
}
if ($(".order-shelf-btn").length > 1) {
    $(".order-shelf-btn:first").remove();
}

// Turn off bootstrap animations
$(function () {
    $.support.transition = false;
})
