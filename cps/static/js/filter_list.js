
var direction = 0;  // Descending order

$("#desc").click(function() {
    if (direction === 0) {
        return;
    }
    var list = $('#list');
    var listItems = list.children(".row");
    list.append(listItems.get().reverse());
    console.log("desc")
    direction = 0;
});


$("#asc").click(function() {
    if (direction === 1) {
        return;
    }
    var list = $('#list');
    var listItems = list.children(".row");
    list.append(listItems.get().reverse());
    console.log("asc")
    direction = 1;
});

$("#all").click(function() {
    $(".row").each(function() {
        $(this).show();
    });
});

$(".char").click(function() {
    console.log(this.innerText);
    var character = this.innerText;
    // var listItems = ;

    $(".row").each(function() {
        if (this.attributes['data-id'].value.charAt(0).toUpperCase() !== character) {
            $(this).hide();
        } else {
            $(this).show();
        }
    });

});
