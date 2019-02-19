/*
 * bootstrap-uploadprogress
 * github: https://github.com/jakobadam/bootstrap-uploadprogress
 *
 * Copyright (c) 2015 Jakob Aarøe Dam
 * Version 1.0.0
 * Licensed under the MIT license.
 */
(function($){
    "use strict";

    $.support.xhrFileUpload = !!(window.FileReader && window.ProgressEvent);
    $.support.xhrFormData = !!window.FormData;

    if(!$.support.xhrFileUpload || !$.support.xhrFormData){
        // skip decorating form
        return;
    }

    var template = '<div class="modal fade" id="file-progress-modal">\
  <div class="modal-dialog">\
    <div class="modal-content">\
      <div class="modal-header">\
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>\
        <h4 class="modal-title">Uploading</h4>\
      </div>\
      <div class="modal-body">\
        <div class="modal-message"></div>\
        <div class="progress">\
          <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0"\
               aria-valuemax="100" style="width: 0%;min-width: 2em;">\
            0%\
          </div>\
        </div>\
      </div>\
      <div class="modal-footer" style="display:none">\
        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>\
      </div>\
    </div>\
  </div>\
</div>';

    var UploadProgress = function(element, options){
        this.options = options;
        this.$element = $(element);
    };

    UploadProgress.prototype = {

        constructor: function() {
            this.$form = this.$element;
            this.$form.on('submit', $.proxy(this.submit, this));
            this.$modal = $(this.options.template);
            this.$modal_message = this.$modal.find('.modal-message');
            this.$modal_title = this.$modal.find('.modal-title');
            this.$modal_footer = this.$modal.find('.modal-footer');
            this.$modal_bar = this.$modal.find('.progress-bar');

            this.$modal.on('hidden.bs.modal', $.proxy(this.reset, this));
        },

        reset: function(){
            this.$modal_title = this.$modal_title.text('Uploading');
            this.$modal_footer.hide();
            this.$modal_bar.addClass('progress-bar-success');
            this.$modal_bar.removeClass('progress-bar-danger');
            if(this.xhr){
                this.xhr.abort();
            }
        },

        submit: function(e) {
            e.preventDefault();

            this.$modal.modal({
                backdrop: 'static',
                keyboard: false
            });

            // We need the native XMLHttpRequest for the progress event
            var xhr = new XMLHttpRequest();
            this.xhr = xhr;

            xhr.addEventListener('load', $.proxy(this.success, this, xhr));
            xhr.addEventListener('error', $.proxy(this.error, this, xhr));
            //xhr.addEventListener('abort', function(){});

            xhr.upload.addEventListener('progress', $.proxy(this.progress, this));

            var form = this.$form;
            
            xhr.open(form.attr('method'), form.attr("action"));
            xhr.setRequestHeader('X-REQUESTED-WITH', 'XMLHttpRequest');

            var data = new FormData(form.get(0));
            xhr.send(data);
        },

        success: function(xhr) {
            if(xhr.status == 0 || xhr.status >= 400){
                // HTTP 500 ends up here!?!
                return this.error(xhr);
            }
            this.set_progress(100);
            var url;
            var content_type = xhr.getResponseHeader('Content-Type');

            // make it possible to return the redirect URL in
            // a JSON response
            if(content_type.indexOf('application/json') !== -1){
                var response = $.parseJSON(xhr.responseText);
                console.log(response);
                url = response.location;
            }
            else{
                url = this.options.redirect_url;
            }
            window.location.href = url;
        },

        // handle form error
        // we replace the form with the returned one
        error: function(xhr){
            this.$modal_title.text('Upload failed');

            this.$modal_bar.removeClass('progress-bar-success');
            this.$modal_bar.addClass('progress-bar-danger');
            this.$modal_footer.show();

            var content_type = xhr.getResponseHeader('Content-Type');

            // Replace the contents of the form, with the returned html
            if(xhr.status === 422){
                var new_html = $.parseHTML(xhr.responseText);
                this.replace_form(new_html);
                this.$modal.modal('hide');
            }
            // Write the error response to the document.
            else{
                var response_text = xhr.responseText;
                if(content_type.indexOf('text/plain') !== -1){
                    response_text = '<pre>' + response_text + '</pre>';
                }
                document.write(xhr.responseText);
            }
        },

        set_progress: function(percent){
            var txt = percent + '%';
            if (percent == 100) {
                txt = this.options.uploaded_msg;
            }
            this.$modal_bar.attr('aria-valuenow', percent);
            this.$modal_bar.text(txt);
            this.$modal_bar.css('width', percent + '%');
        },

        progress: function(/*ProgressEvent*/e){
            var percent = Math.round((e.loaded / e.total) * 100);
            this.set_progress(percent);
        },

        // replace_form replaces the contents of the current form
        // with the form in the html argument.
        // We use the id of the current form to find the new form in the html
        replace_form: function(html){
            var new_form;
            var form_id = this.$form.attr('id');
            if(form_id !== undefined){
                new_form = $(html).find('#' + form_id);
            }
            else{
                new_form = $(html).find('form');
            }

            // add the filestyle again
            new_form.find(':file').filestyle({buttonBefore: true});
            this.$form.html(new_form.children());
        }
    };

    $.fn.uploadprogress = function(options, value){
        return this.each(function(){
            var _options = $.extend({}, $.fn.uploadprogress.defaults, options);
            var file_progress = new UploadProgress(this, _options);
            file_progress.constructor();
        });
    };

    $.fn.uploadprogress.defaults = {
        template: template,
        uploaded_msg: "Upload done, processing, please wait..."
        //redirect_url: ...

        // need to customize stuff? Add here, and change code accordingly.
    };

})(window.jQuery);
