(function ($) {
    "use strict";

    function callAi(url, $output) {
        var $loading = $("#ai-loading");
        $loading.show();
        $output.hide().empty();

        $.getJSON(url)
            .done(function (data) {
                if (data && data.content) {
                    var html = (data.content || "").replace(/\n/g, "<br>");
                    $output.html(html).show();
                } else if (data && data.error) {
                    var msg = "AI 调用失败: " + data.error;
                    if (data.detail) {
                        msg += "（" + data.detail + "）";
                    }
                    $output.html(msg).show();
                } else {
                    $output.html("AI 返回了未知结果。").show();
                }
            })
            .fail(function (xhr, status, err) {
                var msg = "AI 请求出错";
                if (xhr && xhr.responseText) {
                    msg += "：" + xhr.responseText;
                } else if (err) {
                    msg += "：" + err;
                }
                $output.html(msg).show();
            })
            .always(function () {
                $loading.hide();
            });
    }

    $(function () {
        $("#ai-summary-btn").on("click", function () {
            var bookId = $(this).data("book-id");
            if (!bookId) {
                return;
            }
            callAi("/ajax/ai/book_summary/" + bookId, $("#ai-summary-result"));
        });

        $("#ai-related-btn").on("click", function () {
            var bookId = $(this).data("book-id");
            if (!bookId) {
                return;
            }
            callAi("/ajax/ai/book_recommendations/" + bookId, $("#ai-related-result"));
        });
    });

})(jQuery);