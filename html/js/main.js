$(window).load(function(){
    //initialize background slideshow
	if(!$('body').hasClass("no-bg-slides")){
        $.vegas('slideshow', {
            delay: 50000,
            backgrounds:[
                { src:'images/slide01.jpg', fade: 1000 },
                { src:'images/slide02.jpg', fade: 1000 },
                { src:'images/slide03.jpg', fade: 1000 },
                { src:'images/slide04.jpg', fade: 1000 }
            ]
        })();
    }

});


$(function() {
    //toggle the slideshow mode
    $('#gallery-swap').click(function(event) {
        if ($('body').hasClass('slideshow')){
            $('body').removeClass('slideshow');

        } else {
            $('body').addClass('slideshow');
        }
    });

    //slideshow naviagaion
    $('.slide-nav li').click(function(event) {
        if ($(this).hasClass('next')) {
            $.vegas('next');
        } else {
            $.vegas('previous');
        }
    });

    $('nav li a').click(function(event) {
        $(this).parents('ul').find('li').removeClass('active');
        $(this).parent('li').addClass('active');
    });

    //keyboard navigation for slideshow.
    //left, right, esc
    $(window).keydown(function(event) {
        if($('body').hasClass('slideshow')) {
            if(event.keyCode==37){
                $.vegas('previous');
            }
            if(event.keyCode==39){
                $.vegas('next');
            }
            if(event.keyCode==27){
                $('body').removeClass('slideshow');
            }
        }
    });

    $('#open-menu').click(function(){
        $('nav').toggleClass('open');
        $('body').toggleClass('open');
    });

    $('header').swipe({
        swipe: function(event, direction, distance, duration, fingers){
            // console.log(direction, distance, event, duration);
            if(direction=="right"){
                $('nav').addClass('open');
                $('body').addClass('open');
            }

            if(direction=="left"){
                $('nav').removeClass('open');
                $('body').removeClass('open');
            }
        }
    });

    $('.magnific').magnificPopup({
        type: 'image',
        mainClass: 'mfp-with-zoom',
        gallery: {
            enabled: true,
            tCounter: '<span class="mfp-counter">%curr%/%total%</span>',
            arrowMarkup: '<button title="%title%" type="button" class="entypo slide-button chevron-thin-%dir%"></button>'
            //arrowMarkup: '<span class="entypo slide-button chevron-thin-%dir%"></span>'
            //<span class="entypo chevron-thin-left"></span>
        },
        zoom: {
            enabled: true, // By default it's false, so don't forget to enable it

            duration: 300, // duration of the effect, in milliseconds
            easing: 'ease-in-out', // CSS transition easing function

            // The "opener" function should return the element from which popup will be zoomed in
            // and to which popup will be scaled down
            // By defailt it looks for an image tag:
            opener: function(openerElement) {
              // openerElement is the element on which popup was initialized, in this case its <a> tag
              // you don't need to add "opener" option if this code matches your needs, it's defailt one.
              return openerElement.is('img') ? openerElement : openerElement.find('img');
            }
        }
    });


});
