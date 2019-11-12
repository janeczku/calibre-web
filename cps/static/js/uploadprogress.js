/*
 * bootstrap-uploadprogress
 * github: https://github.com/jakobadam/bootstrap-uploadprogress
 *
 * Copyright (c) 2015 Jakob Aarøe Dam
 * Version 1.0.0
 * Licensed under the MIT license.
 */

(function($) {
    "use strict";

    $.support.xhrFileUpload = !!(window.FileReader && window.ProgressEvent);
    $.support.xhrFormData = !!window.FormData;

    if (!$.support.xhrFileUpload || !$.support.xhrFormData) {
        // skip decorating form
        return;
    }

    var template = "<div class=\"modal fade\" id=\"file-progress-modal\">" +
    "<div class=\"modal-dialog upload-modal-dialog\">" +
    "  <div class=\"modal-content\">" +
    "    <div class=\"modal-header\">" +
    "      <button type=\"button\" class=\"close\" data-dismiss=\"modal\" aria-label=\"Close\"><span aria-hidden=\"true\">&times;</span></button>" +
    "      <h4 class=\"modal-title\">Uploading</h4>" +
    "    </div>" +
    "    <div class=\"modal-body\">" +
    "      <div class=\"modal-message\"></div>" +
    "      <div class=\"progress\">" +
    "        <div class=\"progress-bar progress-bar-striped active\" role=\"progressbar\" aria-valuenow=\"0\" aria-valuemin=\"0\"" +
    "             aria-valuemax=\"100\" style=\"width: 0%;min-width: 2em;\">" +
    "          0%" +
    "        </div>" +
    "     </div>" +
    "   </div>" +
    "   <div class=\"modal-footer\" style=\"display:none\">" +
    "     <button type=\"button\" class=\"btn btn-default\" data-dismiss=\"modal\">Close</button>" +
    "   </div>" +
    "   </div>" +
    "  </div>" +
    "</div>";

    var UploadProgress = function(element, options) {
        this.options = options;
        this.$element = $(element);
    };

    UploadProgress.prototype = {

        constructor: function() {
            this.$form = this.$element;
            this.$form.on("submit", $.proxy(this.submit, this));
            this.$modal = $(this.options.template);
            this.$modalTitle = this.$modal.find(".modal-title");
            this.$modalFooter = this.$modal.find(".modal-footer");
            this.$modalBar = this.$modal.find(".progress-bar");

            // Translate texts
            this.$modalTitle.text(this.options.modalTitle);
            this.$modalFooter.children("button").text(this.options.modalFooter);

            this.$modal.on("hidden.bs.modal", $.proxy(this.reset, this));
        },

        reset: function() {
            this.$modalTitle.text(this.options.modalTitle);
            this.$modalFooter.hide();
            this.$modalBar.addClass("progress-bar-success");
            this.$modalBar.removeClass("progress-bar-danger");
            if (this.xhr) {
                this.xhr.abort();
            }
        },

        submit: function(e) {
            e.preventDefault();

            this.$modal.modal({
                backdrop: "static",
                keyboard: false
            });

            // We need the native XMLHttpRequest for the progress event
            var xhr = new XMLHttpRequest();
            this.xhr = xhr;

            xhr.addEventListener("load", $.proxy(this.success, this, xhr));
            xhr.addEventListener("error", $.proxy(this.error, this, xhr));

            xhr.upload.addEventListener("progress", $.proxy(this.progress, this));

            var form = this.$form;

            xhr.open(form.attr("method"), form.attr("action"));
            xhr.setRequestHeader("X-REQUESTED-WITH", "XMLHttpRequest");

            var data = new FormData(form.get(0));
            xhr.send(data);
        },

        success: function(xhr) {
            if (xhr.status === 0 || xhr.status >= 400) {
                // HTTP 500 ends up here!?!
                return this.error(xhr);
            }
            this.setProgress(100);
            var url;
            var contentType = xhr.getResponseHeader("Content-Type");

            // make it possible to return the redirect URL in
            // a JSON response
            if (contentType.indexOf("application/json") !== -1) {
                var response = $.parseJSON(xhr.responseText);
                url = response.location;
            } else {
                url = this.options.redirect_url;
            }
            window.location.href = url;
        },

        // handle form error
        // we replace the form with the returned one
        error: function(xhr) {
            this.$modalTitle.text(this.options.modalTitleFailed);

            this.$modalBar.removeClass("progress-bar-success");
            this.$modalBar.addClass("progress-bar-danger");
            this.$modalFooter.show();

            var contentType = xhr.getResponseHeader("Content-Type");
            // Write the error response to the document.
            if (contentType || xhr.status === 422) {
                var responseText = xhr.responseText;
                if (contentType.indexOf("text/plain") !== -1) {
                    responseText = "<pre>" + responseText + "</pre>";
                    document.write(responseText);
                } else {
                    this.$modalBar.text(responseText);
                }
            } else {
                this.$modalBar.text(this.options.modalTitleFailed);
            }
        },

        setProgress: function(percent) {
            var txt = percent + "%";
            if (percent === 100) {
                txt = this.options.uploadedMsg;
            }
            this.$modalBar.attr("aria-valuenow", percent);
            this.$modalBar.text(txt);
            this.$modalBar.css("width", percent + "%");
        },

        progress: function(/*ProgressEvent*/e) {
            var percent = Math.round((e.loaded / e.total) * 100);
            this.setProgress(percent);
        },

        // replaceForm replaces the contents of the current form
        // with the form in the html argument.
        // We use the id of the current form to find the new form in the html
        replaceForm: function(html) {
            var newForm;
            var formId = this.$form.attr("id");
            if ( typeof formId !== "undefined") {
                newForm = $(html).find("#" + formId);
            } else {
                newForm = $(html).find("form");
            }
            // add the filestyle again
            newForm.find(":file").filestyle({buttonBefore: true});
            this.$form.html(newForm.children());
        }
    };

    $.fn.uploadprogress = function(options) {
        return this.each(function() {
            var _options = $.extend({}, $.fn.uploadprogress.defaults, options);
            var fileProgress = new UploadProgress(this, _options);
            fileProgress.constructor();
        });
    };

    $.fn.uploadprogress.defaults = {
        template: template,
        uploadedMsg: "Upload done, processing, please wait...",
        modalTitle: "Uploading",
        modalFooter: "Close",
        modalTitleFailed: "Upload failed"
        //redirect_url: ...
        // need to customize stuff? Add here, and change code accordingly.
    };

})(window.jQuery);
