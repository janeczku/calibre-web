
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

});

$(window).resize(function(event) {
    $('.discover .row').isotope('reLayout');
});
