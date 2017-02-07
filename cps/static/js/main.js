
$(function() {
    $('.discover .row').isotope({
        // options
        itemSelector : '.book',
        layoutMode : 'fitRows'
    });

    $('.load-more .row').infinitescroll({
        debug: false,
        navSelector  : ".pagination",
                   // selector for the paged navigation (it will be hidden)
        nextSelector : ".pagination a:last",
                   // selector for the NEXT link (to page 2)
        itemSelector : ".load-more .book",
        animate      : true,
        extraScrollPx: 300,
                   // selector for all items you'll retrieve
    }, function(data){
        $('.load-more .row').isotope( 'appended', $(data), null );
    });

    $('#sendbtn').click(function(){
        var $this = $(this);
        $this.text('Please wait...');
        $this.addClass('disabled');
    });
    $("#restart").click(function() {
        $.ajax({
            dataType: 'json',
            url: window.location.pathname+"/../../shutdown",
            data: {"parameter":0},
            success: function(data) {
                return alert(data.text);}
        });
    });
    $("#shutdown").click(function() {
        $.ajax({
            dataType: 'json',
            url: window.location.pathname+"/../../shutdown",
            data: {"parameter":1},
            success: function(data) {
                return alert(data.text);}
        });
    });
    $("#check_for_update").click(function() {
        var button_text = $("#check_for_update").html();
        $("#check_for_update").html('Checking...');
        $.ajax({
            dataType: 'json',
            url: window.location.pathname+"/../../get_update_status",
            success: function(data) {
            if (data.status == true) {
                $("#check_for_update").addClass('hidden');
                $("#perform_update").removeClass('hidden');
            }else{
                $("#check_for_update").html(button_text);
            };}
        });
    });

});

$(window).resize(function(event) {
    $('.discover .row').isotope('reLayout');
});
