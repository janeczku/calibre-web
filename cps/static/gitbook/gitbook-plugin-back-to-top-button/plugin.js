var gitbook = window.gitbook;

gitbook.events.on('page.change', function() {

    var back_to_top_button = ['<div class="back-to-top"><i class="fa fa-arrow-up"></i></div>'].join("");
    $(".book").append(back_to_top_button)

    $(".back-to-top").hide();

    $('.book-body,.body-inner').on('scroll', function () {
        if ($(this).scrollTop() > 100) {
            $('.back-to-top').fadeIn();
        } else {
            $('.back-to-top').fadeOut();
        }
    });

    $('.back-to-top').click(function () {
        $('.book-body,.body-inner').animate({
            scrollTop: 0
        }, 800);
        return false;
    });

});