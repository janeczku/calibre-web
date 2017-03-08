var displaytext;
var updateTimerID;
var updateText;

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
                $('#spinner').show();
                displaytext=data.text;
                setTimeout(restartTimer, 3000);}
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
        $("#check_for_update").html('...');
        $.ajax({
            dataType: 'json',
            url: window.location.pathname+"/../../get_update_status",
            success: function(data) {
                $("#check_for_update").html(button_text);
                if (data.status == true) {
                    $("#check_for_update").addClass('hidden');
                    $("#perform_update").removeClass('hidden');
                    $("#update_info").removeClass('hidden');
                    $("#update_info").find('span').html(data.commit);
                }
            }
        });
    });
    $("#restart_database").click(function() {
        $.ajax({
            dataType: 'json',
            url: window.location.pathname+"/../../shutdown",
            data: {"parameter":2}
        });
    });
    $("#perform_update").click(function() {
        $('#spinner2').show();
        $.ajax({
        type: "POST",
        dataType: 'json',
        data: { start: "True"},
        url: window.location.pathname+"/../../get_updater_status",
        success: function(data) {
            updateText=data.text
            $("#UpdateprogressDialog #Updatecontent").html(updateText[data.status]);
            console.log(data.status);
            updateTimerID=setInterval(updateTimer, 2000);}
        });
    });
});


function restartTimer() {
    $('#spinner').hide();
    $('#RestartDialog').modal('hide');
}

function updateTimer() {
    $.ajax({
    dataType: 'json',
    url: window.location.pathname+"/../../get_updater_status",
    success: function(data) {
        console.log(data.status);
        $("#UpdateprogressDialog #Updatecontent").html(updateText[data.status]);
        if (data.status >6){
            clearInterval(updateTimerID);
            $('#spinner2').hide();
            $('#UpdateprogressDialog #updateFinished').removeClass('hidden');
            $("#check_for_update").removeClass('hidden');
            $("#perform_update").addClass('hidden');
        }
    },
    error: function() {
        console.log('Done');
        clearInterval(updateTimerID);
        $('#spinner2').hide();
        $("#UpdateprogressDialog #Updatecontent").html(updateText[7]);
        $('#UpdateprogressDialog #updateFinished').removeClass('hidden');
        $("#check_for_update").removeClass('hidden');
        $("#perform_update").addClass('hidden');
        },
    timeout:2000
    });
}


$(window).resize(function(event) {
    $('.discover .row').isotope('reLayout');
});
