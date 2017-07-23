$( document ).ready(function() {
    $("#have_read_form").ajaxForm();
});

$("#have_read_cb").on("change", function() {
    $(this).closest("form").submit();
});

$("#shelf-actions").on("click", "[data-shelf-action]", function (e) {
    e.preventDefault();

    $.get(this.href)
        .done(() => {
            const $this = $(this);
            switch ($this.data("shelf-action")) {
                case "add":
                    $("#remove-from-shelves").append(`<a href="${$this.data("remove-href")}"
                       data-add-href="${this.href}"
                       class="btn btn-sm btn-default" data-shelf-action="remove"
                    ><span class="glyphicon glyphicon-remove"></span> ${this.textContent}</a>`);
                    break;
                case "remove":
                    $("#add-to-shelves").append(`<li><a href="${$this.data("add-href")}"
                      data-remove-href="${this.href}"
                      data-shelf-action="add"
                    >${this.textContent}</a></li>`);
                    break;
            }
            this.parentNode.removeChild(this);
        })
        .fail((xhr) => {
            const $msg = $("<span/>", { "class": "text-danger"}).text(xhr.responseText);
            $("#shelf-action-status").html($msg);

            setTimeout(() => {
                $msg.remove();
            }, 10000);
        });
});