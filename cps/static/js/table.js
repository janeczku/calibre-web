/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018 OzzieIsaacs
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

/* exported TableActions */

$(function() {

    $("#domain_allow_submit").click(function(event) {
        event.preventDefault();
        $("#domain_add_allow").ajaxForm();
        $(this).closest("form").submit();
        $.ajax ({
            method:"get",
            url: window.location.pathname + "/../../ajax/domainlist/1",
            async: true,
            timeout: 900,
            success:function(data) {
                $("#domain-allow-table").bootstrapTable("load", data);
            }
        });
    });
    $("#domain-allow-table").bootstrapTable({
        formatNoMatches: function () {
            return "";
        },
        striped: false
    });
    $("#domain_deny_submit").click(function(event) {
        event.preventDefault();
        $("#domain_add_deny").ajaxForm();
        $(this).closest("form").submit();
        $.ajax ({
            method:"get",
            url: window.location.pathname + "/../../ajax/domainlist/0",
            async: true,
            timeout: 900,
            success:function(data) {
                $("#domain-deny-table").bootstrapTable("load", data);
            }
        });
    });
    $("#domain-deny-table").bootstrapTable({
        formatNoMatches: function () {
            return "";
        },
        striped: false
    });
    $("#btndeletedomain").click(function() {
        //get data-id attribute of the clicked element
        var domainId = $(this).data("domainId");
        $.ajax({
            method:"post",
            url: window.location.pathname + "/../../ajax/deletedomain",
            data: {"domainid":domainId}
        });
        $("#DeleteDomain").modal("hide");
        $.ajax({
            method:"get",
            url: window.location.pathname + "/../../ajax/domainlist/1",
            async: true,
            timeout: 900,
            success:function(data) {
                $("#domain-allow-table").bootstrapTable("load", data);
            }
        });
        $.ajax({
            method:"get",
            url: window.location.pathname + "/../../ajax/domainlist/0",
            async: true,
            timeout: 900,
            success:function(data) {
                $("#domain-deny-table").bootstrapTable("load", data);
            }
        });
    });
    //triggered when modal is about to be shown
    $("#DeleteDomain").on("show.bs.modal", function(e) {
        //get data-id attribute of the clicked element and store in button
        var domainId = $(e.relatedTarget).data("domain-id");
        $(e.currentTarget).find("#btndeletedomain").data("domainId", domainId);
    });

    $('#restrictModal').on('hidden.bs.modal', function () {
        // Destroy table and remove hooks for buttons
        $("#restrict-elements-table").unbind();
        $('#restrict-elements-table').bootstrapTable('destroy');
        $("[id^=submit_]").unbind();
        $('#h1').addClass('hidden');
        $('#h2').addClass('hidden');
        $('#h3').addClass('hidden');
        $('#h4').addClass('hidden');
    });
    function startTable(type){
        var pathname = document.getElementsByTagName("script"), src = pathname[pathname.length-1].src;
        var path = src.substring(0,src.lastIndexOf("/"));
        $("#restrict-elements-table").bootstrapTable({
            formatNoMatches: function () {
                return "";
            },
            url: path + "/../../ajax/listrestriction/" + type,
            rowStyle: function(row, index) {
                console.log('Reihe :' + row + ' Index :'+ index);
                if (row.id.charAt(0) == 'a') {
                    return {classes: 'bg-primary'}
                }
                else {
                    return {classes: 'bg-dark-danger'}
                }
            },
            onClickCell: function (field, value, row, $element) {
                if(field == 3){
                    console.log("element")
                    $.ajax ({
                        type: 'Post',
                        data: 'id=' + row.id + '&type=' + row.type + "&Element=" + row.Element,
                        url: path + "/../../ajax/deleterestriction/" + type,
                        async: true,
                        timeout: 900,
                        success:function(data) {
                            $.ajax({
                                method:"get",
                                url: path + "/../../ajax/listrestriction/"+type,
                                async: true,
                                timeout: 900,
                                success:function(data) {
                                    $("#restrict-elements-table").bootstrapTable("load", data);
                                }
                            });
                        }
                    });
                }
            },
            striped: false
        });
        $("#restrict-elements-table").removeClass('table-hover');
        $("#restrict-elements-table").on('editable-save.bs.table', function (e, field, row, old, $el) {
            console.log("Hallo");
            $.ajax({
                url: path + "/../../ajax/editrestriction/"+type,
                type: 'Post',
                data: row //$(this).closest("form").serialize() + "&" + $(this)[0].name + "=",
            });
        });
        $("[id^=submit_]").click(function(event) {
            // event.stopPropagation();
            // event.preventDefault();
            $(this)[0].blur();
            console.log($(this)[0].name);
            $.ajax({
                url: path + "/../../ajax/addrestriction/"+type,
                type: 'Post',
                data: $(this).closest("form").serialize() + "&" + $(this)[0].name + "=",
                success: function () {
                $.ajax ({
                    method:"get",
                    url: path + "/../../ajax/listrestriction/"+type,
                    async: true,
                    timeout: 900,
                    success:function(data) {
                        $("#restrict-elements-table").bootstrapTable("load", data);
                       }
                    });
                }
            });
            return;
        });
    }
    $('#get_column_values').on('click',function()
    {
        startTable(1);
        $('#h2').removeClass('hidden');
    });

    $('#get_tags').on('click',function()
    {
        startTable(0);
        $('#h1').removeClass('hidden');
    });
    $('#get_user_column_values').on('click',function()
    {
        startTable(3);
        $('#h4').removeClass('hidden');
    });

    $('#get_user_tags').on('click',function()
    {
        startTable(2);
        $(this)[0].blur();
        $('#h3').removeClass('hidden');
    });

});

/* Function for deleting domain restrictions */
function TableActions (value, row, index) {
    return [
        "<a class=\"danger remove\" data-toggle=\"modal\" data-target=\"#DeleteDomain\" data-domain-id=\"" + row.id
        + "\" title=\"Remove\">",
        "<i class=\"glyphicon glyphicon-trash\"></i>",
        "</a>"
    ].join("");
}

/* Function for deleting domain restrictions */
function RestrictionActions (value, row, index) {
    return [
        "<div class=\"danger remove\" data-restriction-id=\"" + row.id + "\" title=\"Remove\">",
        "<i class=\"glyphicon glyphicon-trash\"></i>",
        "</div>"
    ].join("");
}
