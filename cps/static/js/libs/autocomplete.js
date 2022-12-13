
const client = new MeiliSearch({
    host: host,
    apiKey: masterKey,
})
const index = client.index('books')

async function search_product() {

    let keySearch = document.getElementById("query").value;
    const search = await index.search(keySearch, {
        attributesToHighlight: ['title', 'author_sort'],
        attributesToRetrieve: ['title', 'author_sort'],
    });
    const result = [];
    console.log("search", search);
    let formattedList = search.hits;
    formattedList.forEach(function (formatedItem) {
        let key_result = null;
        for (const [key, value] of Object.entries(formatedItem._formatted)) {
            if (value.includes("<em>")) {
                key_result = key;
                break
            }
        }
        console.log("key_result", key_result);
        console.log("formatedItem", formatedItem);
        if (key_result) {
            result.push(formatedItem[key_result]);
        }

    });
    $("#query").autocomplete({
        source: result,
        appendTo: '#menu-container',
        open: function () {
            $("ul.ui-menu").width($(this).innerWidth());
        }
    });
    // document.getElementById('query').value=result.join(" & ");
};