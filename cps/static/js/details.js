/* global _ */

$(function() {
    $("#have_read_form").ajaxForm();
});

$("#have_read_cb").on("change", function() {
    $(this).closest("form").submit();
});

(function() {
    var templates = {
        add: _.template(
            $("#template-shelf-add").html()
        ),
        remove: _.template(
            $("#template-shelf-remove").html()
        )
    };

    $("#shelf-actions").on("click", "[data-shelf-action]", function (e) {
        e.preventDefault();

        $.get(this.href)
            .done(function() {
                var $this = $(this);
                switch ($this.data("shelf-action")) {
                    case "add":
                        $("#remove-from-shelves").append(
                            templates.remove({
                                add: this.href,
                                remove: $this.data("remove-href"),
                                content: this.textContent
                            })
                        );
                        break;
                    case "remove":
                        $("#add-to-shelves").append(
                            templates.add({
                                add: $this.data("add-href"),
                                remove: this.href,
                                content: this.textContent
                            })
                        );
                        break;
                }
                this.parentNode.removeChild(this);
            }.bind(this))
            .fail(function(xhr) {
                var $msg = $("<span/>", { "class": "text-danger"}).text(xhr.responseText);
                $("#shelf-action-status").html($msg);

                setTimeout(function() {
                    $msg.remove();
                }, 10000);
            });
    });
})();
