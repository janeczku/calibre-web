Sortable.create(sortTrue, {
  group: "sorting",
  sort: true
});

function sendData(path){
    var elements;
    var counter;
    var maxElements;
    var tmp=[];

    elements=Sortable.utils.find(sortTrue,"div");
    maxElements=elements.length;

    var form = document.createElement("form");
    form.setAttribute("method", "post");
    form.setAttribute("action", path);


    for(counter=0;counter<maxElements;counter++){
      tmp[counter]=elements[counter].getAttribute("id");
      var hiddenField = document.createElement("input");
      hiddenField.setAttribute("type", "hidden");
      hiddenField.setAttribute("name", elements[counter].getAttribute("id"));
      hiddenField.setAttribute("value", counter+1);
      form.appendChild(hiddenField);
    }
    document.body.appendChild(form);
    form.submit();
}
