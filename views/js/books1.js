var Books = (function() {

	var $books = $( '#bk-list > li > div.bk-book' ), booksCount = $books.length;
	
	function init() {

		$books.each( function() {
			
			var $book = $( this ),
				$other = $books.not( $book ),
				$parent = $book.parent(),
				$page = $book.children( 'div.bk-page' ),
				$bookview = $parent.find( 'button.bk-bookview' ),
				$content = $page.children( 'div.bk-content' ), current = 0;

			$parent.find( 'button.bk-bookback' ).on( 'click', function() {				
				
				$bookview.removeClass( 'bk-active' );

				if( $book.data( 'flip' ) ) {
					
					$book.data( { opened : false, flip : false } ).removeClass( 'bk-viewback' ).addClass( 'bk-bookdefault' );

				}
				else {
					
					$book.data( { opened : false, flip : true } ).removeClass( 'bk-viewinside bk-bookdefault' ).addClass( 'bk-viewback' );

				}
					
			} );

			$bookview.on( 'click', function() {

				var $this = $( this );			
				
				$other.data( 'opened', false ).removeClass( 'bk-viewinside' ).parent().css( 'z-index', 0 ).find( 'button.bk-bookview' ).removeClass( 'bk-active' );
				if( !$other.hasClass( 'bk-viewback' ) ) {
					$other.addClass( 'bk-bookdefault' );
				}

				if( $book.data( 'opened' ) ) {
					$this.removeClass( 'bk-active' );
					$book.data( { opened : false, flip : false } ).removeClass( 'bk-viewinside' ).addClass( 'bk-bookdefault' );
				}
				else {
					$this.addClass( 'bk-active' );
					$book.data( { opened : true, flip : false } ).removeClass( 'bk-viewback bk-bookdefault' ).addClass( 'bk-viewinside' );
					$parent.css( 'z-index', booksCount );
					current = 0;
					$content.removeClass( 'bk-content-current' ).eq( current ).addClass( 'bk-content-current' );
				}

			} );

			if( $content.length > 1 ) {

				var $navPrev = $( '<span class="bk-page-prev">&lt;</span>' ),
					$navNext = $( '<span class="bk-page-next">&gt;</span>' );
				
				$page.append( $( '<nav></nav>' ).append( $navPrev, $navNext ) );

				$navPrev.on( 'click', function() {
					if( current > 0 ) {
						--current;
						$content.removeClass( 'bk-content-current' ).eq( current ).addClass( 'bk-content-current' );
					}
					return false;
				} );

				$navNext.on( 'click', function() {
					if( current < $content.length - 1 ) {
						++current;
						$content.removeClass( 'bk-content-current' ).eq( current ).addClass( 'bk-content-current' );
					}
					return false;
				} );

			}
			
		} );

	}

	return { init : init };

})();