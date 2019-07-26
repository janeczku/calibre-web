output_list = Array();

/* Level - 0: Summary; 1: Failed; 2: All; 3: Skipped 4: Error*/
function showCase(level) {
    table_rows = document.getElementsByTagName("tr");
    for (var i = 0; i < table_rows.length; i++) {
        row = table_rows[i];
        id = row.id;
        // Show failed if all or failed or summary problems selected
        if (id.substr(0,2) == 'ft') {
            if (level == 2|| level == 1 || level == 5 ) {                
                row.classList.remove('hiddenRow');                
            }
            else {
                row.classList.add('hiddenRow');                
            }
        }
        // Show passed if all selected
        if (id.substr(0,2) == 'pt') {
            if (level == 2 ) {
                row.classList.remove('hiddenRow');
            }
            else {
                row.classList.add('hiddenRow');
            }
        }
        // Show skipped if all or skipped or summary problems selected
        if (id.substr(0,2) == 'st') {
            if (level ==2 || level ==3 || level == 5) { 
                row.classList.remove('hiddenRow');
            }
            else {
                row.classList.add('hiddenRow');
            }
        }
        // Show error if all or error or summary problems  selected
        if (id.substr(0,2) == 'et') {
            if (level ==4 || level == 2 || level == 5 ) { 
                row.classList.remove('hiddenRow');
            }
            else {
                row.classList.add('hiddenRow');
            }
        }
		
    }
}


function showClassDetail(class_id, count) {
    var testcases_list = Array(count);
    var all_hidden = true;
    for (var i = 0; i < count; i++) {
        testcase_postfix_id = 't' + class_id.substr(1) + '.' + (i+1);
        testcase_id = 'f' + testcase_postfix_id;
        testcase = document.getElementById(testcase_id);
        if (!testcase) {
            testcase_id = 'p' + testcase_postfix_id;
            testcase = document.getElementById(testcase_id);
        }
        if (!testcase) {
            testcase_id = 's' + testcase_postfix_id;
            testcase = document.getElementById(testcase_id);
        }
        if (!testcase) {
            testcase_id = 'e' + testcase_postfix_id;
            testcase = document.getElementById(testcase_id);
        }
        testcases_list[i] = testcase;
        if (testcase.classList.contains('hiddenRow')) {
            all_hidden = false;
        }
    }
    for (var i = 0; i < count; i++) {
        testcase = testcases_list[i];
        if (!all_hidden) {
            testcase.classList.remove('hiddenRow');
        }
        else {
            testcase.classList.add('hiddenRow');
        }
    }
}


function showTestDetail(div_id){
    var details_div = document.getElementById(div_id)
    var displayState = details_div.style.display
    // alert(displayState)
    if (displayState != 'block' ) {
        displayState = 'block'
        details_div.style.display = 'block'
    }
    else {
        details_div.style.display = 'none'
    }
}


function html_escape(s) {
    s = s.replace(/&/g,'&amp;');
    s = s.replace(/</g,'&lt;');
    s = s.replace(/>/g,'&gt;');
    return s;
}

// rgb(38, 154, 188)#31b0d5
function drawCircle(pass, fail, error, skip){
    var color = ["#5cb85c","#d9534f","#31b0d5","#f0ad4e"];
    var data = [pass,fail,error,skip];
    var text_arr = ["pass", "fail", "error","skip"];

    var canvas = document.getElementById("circle");  
    var ctx = canvas.getContext("2d");  
    var startPoint=0;
    var width = 20, height = 10;
    var posX = 112 * 2 + 20, posY = 30;
    var textX = posX + width + 5, textY = posY + 10;
    for(var i=0;i<data.length;i++){  
        ctx.fillStyle = color[i];  
        ctx.beginPath();  
        ctx.moveTo(112,84);   
        ctx.arc(112,84,84,startPoint,startPoint+Math.PI*2*(data[i]/(data[0]+data[1]+data[2]+data[3])),false);
        ctx.fill();  
        startPoint += Math.PI*2*(data[i]/(data[0]+data[1]+data[2]+data[3]));
        ctx.fillStyle = color[i];  
        ctx.fillRect(posX, posY + 20 * i, width, height);  
        ctx.moveTo(posX, posY + 20 * i);  
        ctx.font = 'bold 14px';
        ctx.fillStyle = color[i];
        var percent = text_arr[i] + ":"+data[i];  
        ctx.fillText(percent, textX, textY + 20 * i);  

    }
}


function show_img(obj) {
    var obj1 = obj.nextElementSibling
    obj1.style.display='block'
    var index = 0;
    var len = obj1.getElementsByTagName('img').length;
    var imgyuan = obj1.getElementsByClassName('imgyuan')[0]
    //var start=setInterval(autoPlay,500);
    obj1.onmouseover=function(){
        clearInterval(start);
    }
    obj1.onmouseout=function(){
        start=setInterval(autoPlay,1000);
    }    
    for (var i = 0; i < len; i++) {
        var font = document.createElement('font')
        imgyuan.appendChild(font)
    }
    var lis = obj1.getElementsByTagName('font');
    changeImg(0)
    var funny = function (i) {
        lis[i].onmouseover = function () {
            index=i
            changeImg(i)
        }
    }
    for (var i = 0; i < lis.length; i++) {
        funny(i);
    }
    
    function autoPlay(){
        if(index>len-1){
            index=0;
            clearInterval(start); 
        }
        changeImg(index++);
    }
    imgyuan.style.width= 25*len +"px";
    
    function changeImg(index) {
        var list = obj1.getElementsByTagName('img');
        var list1 = obj1.getElementsByTagName('font');
        for (i = 0; i < list.length; i++) {
            list[i].style.display = 'none';
            list1[i].style.backgroundColor = 'white';
        }
        list[index].style.display = 'block';
        list1[index].style.backgroundColor = 'blue';
    }

}
function hide_img(obj){
    obj.parentElement.style.display = "none";
    obj.parentElement.getElementsByClassName('imgyuan')[0].innerHTML = "";
}