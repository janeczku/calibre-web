$(function() {

    $("#domain_submit").click(function(event){
        event.preventDefault();
        $("#domain_add").ajaxForm();
        $(this).closest("form").submit();
        $.ajax({
            method:"get",
            url: window.location.pathname + "/../../ajax/domainlist",
            async: true,
            timeout: 900,
            success:function(data){
                $('#domain-table').bootstrapTable("load", data);
            }
        });
    });
    $('#domain-table').bootstrapTable({
       formatNoMatches: function () {
        return '';
        },
        striped: false
    });
    $("#btndeletedomain").click(function() {
        //get data-id attribute of the clicked element
        var domainId = $(this).data('domainId');
        $.ajax({
            method:"post",
            url: window.location.pathname + "/../../ajax/deletedomain",
            data: {"domainid":domainId}
        });
        $('#DeleteDomain').modal('hide');
        $.ajax({
            method:"get",
            url: window.location.pathname + "/../../ajax/domainlist",
            async: true,
            timeout: 900,
            success:function(data){
                $('#domain-table').bootstrapTable("load", data);
            }
        });

    });
    //triggered when modal is about to be shown
    $('#DeleteDomain').on('show.bs.modal', function(e) {
        //get data-id attribute of the clicked element and store in button
        var domainId = $(e.relatedTarget).data('domain-id');
        $(e.currentTarget).find("#btndeletedomain").data('domainId',domainId);
    });
});

function TableActions (value, row, index) {
    return [
        '<a class="danger remove" data-toggle="modal" data-target="#DeleteDomain" data-domain-id="'+row.id+'" title="Remove">',
        '<i class="glyphicon glyphicon-trash"></i>',
        '</a>'
    ].join('');
}
