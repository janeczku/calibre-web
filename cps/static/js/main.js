// Generic control/related handler to show/hide fields based on a checkbox' value
// e.g.
//  <input type="checkbox" data-control="stuff-to-show">
//  <div data-related="stuff-to-show">...</div>
$(document).on("change", "input[type=\"checkbox\"][data-control]", function () {
    var $this = $(this);
    var name = $this.data("control");
    var showOrHide = $this.prop("checked");

    $("[data-related=\"" + name + "\"]").each(function () {
        $(this).toggle(showOrHide);
    });
});

$(function() {
    var updateTimerID;
    var updateText;

    // Allow ajax prefilters to be added/removed dynamically
    // eslint-disable-next-line new-cap
    var preFilters = $.Callbacks();
    $.ajaxPrefilter(preFilters.fire);

    function restartTimer() {
        $("#spinner").addClass("hidden");
        $("#RestartDialog").modal("hide");
    }

    function updateTimer() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../get_updater_status",
            success: function success(data) {
                // console.log(data.status);
                $("#Updatecontent").html(updateText[data.status]);
                if (data.status > 6) {
                    clearInterval(updateTimerID);
                    $("#spinner2").hide();
                    $("#updateFinished").removeClass("hidden");
                    $("#check_for_update").removeClass("hidden");
                    $("#perform_update").addClass("hidden");
                }
            },
            error: function error() {
                // console.log('Done');
                clearInterval(updateTimerID);
                $("#spinner2").hide();
                $("#Updatecontent").html(updateText[7]);
                $("#updateFinished").removeClass("hidden");
                $("#check_for_update").removeClass("hidden");
                $("#perform_update").addClass("hidden");
            },
            timeout: 2000
        });
    }

    $(".discover .row").isotope({
        // options
        itemSelector : ".book",
        layoutMode : "fitRows"
    });

    $(".load-more .row").infinitescroll({
        debug: false,
        navSelector  : ".pagination",
        // selector for the paged navigation (it will be hidden)
        nextSelector : ".pagination a:last",
        // selector for the NEXT link (to page 2)
        itemSelector : ".load-more .book",
        animate      : true,
        extraScrollPx: 300
        // selector for all items you'll retrieve
    }, function(data) {
        $(".load-more .row").isotope( "appended", $(data), null );
    });

    $("#sendbtn").click(function() {
        var $this = $(this);
        $this.text("Please wait...");
        $this.addClass("disabled");
    });
    $("#restart").click(function() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../shutdown",
            data: {"parameter":0},
            success: function success() {
                $("#spinner").show();
                setTimeout(restartTimer, 3000);
            }
        });
    });
    $("#shutdown").click(function() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../shutdown",
            data: {"parameter":1},
            success: function success(data) {
                return alert(data.text);
            }
        });
    });
    $("#check_for_update").click(function() {
        var $this = $(this);
        var buttonText = $this.html();
        $this.html("...");
        $("#update_error").addClass("hidden");
        if($("#message").length){
            $("#message").alert("close");
        }
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../get_update_status",
            success: function success(data) {
                $this.html(buttonText);

                var cssClass = '';
                var message = ''

                if (data.success === true) {
                    if (data.update === true) {
                        $("#check_for_update").addClass("hidden");
                        $("#perform_update").removeClass("hidden");
                        $("#update_info")
                            .removeClass("hidden")
                            .find("span").html(data.commit);

                        data.history.reverse().forEach(function(entry, index) {
                            $("<tr><td>" + entry[0] + "</td><td>" + entry[1] + "</td></tr>").appendTo($("#update_table"));
                        });
                        cssClass = 'alert-warning';
                    } else {
                        cssClass = 'alert-success';
                    }
                } else {
                    cssClass = 'alert-danger';
                }

                message = '<div id="message" class="alert ' + cssClass
                    + ' fade in"><a href="#" class="close" data-dismiss="alert">&times;</a>' + data.message + '</div>';

                $(message).insertAfter($("#update_table"));
            }
        });
    });
    $("#restart_database").click(function() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../shutdown",
            data: {"parameter":2}
        });
    });
    $("#perform_update").click(function() {
        $("#spinner2").show();
        $.ajax({
            type: "POST",
            dataType: "json",
            data: { start: "True"},
            url: window.location.pathname + "/../../get_updater_status",
            success: function success(data) {
                updateText = data.text;
                $("#Updatecontent").html(updateText[data.status]);
                // console.log(data.status);
                updateTimerID = setInterval(updateTimer, 2000);
            }
        });
    });

    $("input[data-control]").trigger("change");

    $("#bookDetailsModal")
        .on("show.bs.modal", function(e) {
            var $modalBody = $(this).find(".modal-body");

            // Prevent static assets from loading multiple times
            var useCache = function(options) {
                options.async = true;
                options.cache = true;
            };
            preFilters.add(useCache);

            $.get(e.relatedTarget.href).done(function(content) {
                $modalBody.html(content);
                preFilters.remove(useCache);
            });
        })
        .on("hidden.bs.modal", function() {
            $(this).find(".modal-body").html("...");
        });

    $(window).resize(function() {
        $(".discover .row").isotope("reLayout");
    });
});
