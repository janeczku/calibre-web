var threadregexp = /(?:^| - )(\[[^\]]*\]):/;

var colors = ["#ffa", "#aaf", "#afa", "#aff", "#faf", "#aaa", "#fd8", "#f80", "#4df", "#4fc", "#76973c", "#7e56d8", "#99593d", "#37778a", "#4068fc"];
var screenlines = 1;

var file = null;
var text;

var current, nextFilterId = 1;
var shl = null;
var hl = [];
var groupwith = false;
var filterswitch = true;

var selectedlineid = -1;
var selectedthread = null;
var reachedbottom = false;
var reachedtop = false;


function wheelscroll(event)
{
  renderincremental(event.deltaY);
}

function keypress(event)
{
  if (event.key == "PageDown") {
    _render(screenlines - 1);
    event.preventDefault();
  }
  if (event.key == "PageUp") {
    _render(-(screenlines - 1));
    event.preventDefault();
  }
  if (event.key == "Home" && event.ctrlKey) {
    selectedlineid = 0;
    render();
    event.preventDefault();
  }
  if (event.key == "End" && event.ctrlKey) {
    selectedlineid = text.length - 1;
    render();
    event.preventDefault();
  }
  if (event.key == "ArrowUp") {
    renderincremental(-1);
    event.preventDefault();
  }
  if (event.key == "ArrowDown") {
    renderincremental(1);
    event.preventDefault();
  }
}

function init(filename) {
  document.addEventListener("wheel", wheelscroll, false);
  document.addEventListener("keypress", keypress, false);
  window.addEventListener("resize", resize, false);

  _resize();

  var s = document.getElementById("search");
  s.value = "";
  selectfilter(0);
  reload(filename);
}

function _resize()
{
  var d = document.getElementById("renderer");
  var t = document.getElementById("toobar");
  screenlines = Math.floor((window.innerHeight - t.offsetHeight) / d.firstChild.offsetHeight) - 1;
}

function resize()
{
  _resize();
  repaint();
}

function reload(filename)
{
  if (shl) shl.cache = {};
  for (_hl of hl) _hl.cache = {};

  var q = filename;
  document.title = "Log: " + (q || "none loaded");
  if (!q)
    return;

  var d = document.getElementById("renderer");
  d.innerHTML = "loading " + q + "...";

  var r = new XMLHttpRequest();
  r.open("GET", "/ajax/accesslog", true);
  r.responseType = 'text';
  r.onload = function() {
    console.log("prepare");
    prepare(r.responseText);
    if (selectedlineid > text.length) {
      selectedlineid = -1;
    }
    console.log("render");
    render();
  };
  r.send();
}

function _sanitize(t)
{
  t = t
    .replace(/&/g, "&amp;")
    .replace(/ /g, "&nbsp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return t;
}

function _prepare(t)
{
  // sanitization happens in render, since otherwise it eats enormous amount of memory.
  /*
  var t = t.split('\n');
  for (var i in t) {
    t[i] = _sanitize(t[i]);
  }
  return t;
  */
  return /*_sanitize*/(t).split('\n');
}

function prepare(t)
{
  text = _prepare(t);
}

function render()
{
  _render(0, false); // completely redraws the view from the current scroll position
}

function repaint()
{
  _render(0, true); // completely redraws the view, but centers the selected line
}

function renderincremental(difference)
{
  _render(difference);  // "scrolls" the view
}

function _render(increment, repaintonly)
{
  var epoch  = new Date();

  var d = document.getElementById("renderer");
  var filter = _gfilteron();

  function process(i, append)
  {
    var t = _sanitize(text[i]);

    var lhl = false;
    function dohl(_hl)
    {
      if (_hl.cache[i] === false) {
        // lhl is here unaffected
        return t;
      }

      var t2 = t.replace(new RegExp("(" + _hl.text_r + ")", "g"), "<span style='background-color:" + _hl.color + ";'>$1</span>");
      var affecting = (t != t2);
      _hl.cache[i] = affecting;
      lhl = lhl || (affecting && (!filter || _hl.filter));
      return t2;
    }

    for (var h in hl)
      t = dohl(hl[h]);
    if (shl)
      t = dohl(shl);

    if (filter && !lhl && i != selectedlineid) {
      return false;
    }

    lhl = lhl && !filter;
    var div = document.createElement("div");
    div.id = i;
    if (lhl) div.className = 'lhl';
    div.onclick = function() { selectline(this); };
    div.innerHTML = t;
    if (t.match(new RegExp(selectedthread, "g"))) div.className += ' thread';

    if (append)
      d.appendChild(div);
    else
      d.insertBefore(div, d.firstChild);

    return true;
  }

  var lefttodraw = Math.floor(Math.abs(increment));

  if (increment < 0) {
    // scroll up
    reachedbottom = false;
    if (reachedtop) {
      _hint("reached top of the file");
      return;
    }
    for (var i = parseInt(d.firstChild.id) - 1; lefttodraw && i >= 0 && i < text.length; --i) {
      if (process(i, false)) {
        --lefttodraw;
        if (d.childNodes.length > screenlines)
          d.removeChild(d.lastChild);
      }
    }
    if (lefttodraw) {
      _hint("reached top of the file");
      reachedtop = true;
    }
  } else if (increment > 0) {
    // scroll down
    reachedtop = false;
    if (reachedbottom) {
      _hint("reached bottom of the file");
      return;
    }
    for (var i = parseInt(d.lastChild.id) + 1; lefttodraw && i < text.length; ++i) {
      if (process(i, true)) {
        --lefttodraw;
        if (d.childNodes.length > screenlines)
          d.removeChild(d.firstChild);
      }
    }
    if (lefttodraw) {
      _hint("reached bottom of the file");
      reachedbottom = true;
    }
  } else { // == 0
    // redraw all
    reachedbottom = false;
    reachedtop = false;
    lefttodraw = screenlines;
    var i = repaintonly ? parseInt(d.firstChild.id) : selectedlineid;
    if (i < 0) i = 0;

    d.innerHTML = "";
    for (; lefttodraw && i < text.length; ++i) {
      if (process(i, true)) {
        --lefttodraw;
      }
    }

    if (!repaintonly && selectedlineid > -1) {
      // center the selected line in the middle of screen!
      _render(-(screenlines / 2));
    }
  }

  selectline(selectedlineid);

  var now = new Date();
  console.log("rendered in " + (now.getTime() - epoch.getTime()) + "ms");

  var pos = document.getElementById("position");
  pos.textContent = Math.round((parseInt(d.firstChild.id) / text.length) * 1000) / 10 + "%";
}

function _hint(h)
{
  document.getElementById("hint").innerHTML = h;
}

function _gfilteron()
{
  if (!filterswitch)
    return false;

  if (shl && shl.filter)
    return true;

  for (var h in hl)
  {
    if (hl[h].filter)
      return true;
  }

  return false;
}

function _getfilterelement(filter)
{
  if (filter == 0)
    return document.getElementById("search");

  return document.getElementById("filter" + filter);
}

function _setfilterelementstate(p0, _hl)
{
  p0.style.textDecoration = _hl.filter ? "underline" : "";
}

function _triminput(t)
{
  t = t
    .replace(/^\s+/, "")
    .replace(/\s+$/, "")
  ;
  return t;
}

function _regexpescape(t)
{
  t = t
    .replace(/\\/g, "\\\\")
    .replace(/\?/g, "\\?")
    .replace(/\./g, "\\.")
    .replace(/\+/g, "\\+")
    .replace(/\*/g, "\\*")
    .replace(/\^/g, "\\^")
    .replace(/\$/g, "\\$")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)")
    .replace(/\[/g, "\\[")
    .replace(/\]/g, "\\]")
    .replace(/\|/g, "\\|")
  ;
  return t;
}

function resetuistate()
{
  groupwith = false;
  _hint("");
}

function newhl(t, p, persistent)
{
  return {
    id: persistent ? nextFilterId++ : 0,
    text: t,
    text_r: _sanitize(_regexpescape(t)),
    color: p ? p.color : colors[0],
    filter: p ? p.filter : false,
    cache: {}
  };
}

function selectline(id)
{
  var l0 = document.getElementById(selectedlineid);
  if (l0)
    l0.style.backgroundColor = "";

  var l1 = null;
  if (typeof(id) == "object") {
    l1 = id;
    id = parseInt(l1.id);
  } else {
    l1 = document.getElementById(id);
  }

  selectedlineid = id;
  if (selectedlineid > -1)
    _hint("line # " + (selectedlineid + 1));

  if (l1) {
    l1.style.background = "#faa";
  }

  var thread = null;
  var m = text[selectedlineid].match(threadregexp);
  if (m) thread = _regexpescape(_sanitize(m[1]));
  if (thread != selectedthread) {
    selectedthread = thread;
    repaint();
  }

  return l1;
}

function mouseup(event)
{
  if (event.ctrlKey)
    return;

  resetuistate();

  var s = window.getSelection();
  var t = _triminput(s.toString());
  if (!t)
    return;

  s = document.getElementById("search");
  s.value = t;

  t = _prepare(t)[0];

  shl = newhl(t, shl);
  selectfilter(0);
  repaint();
}

function persist()
{
  resetuistate();

  var dorender = false;
  if (!shl)
  {
    _apply();
    dorender = true;
  }

  if (!shl)
    return;

  selectfilter(0);

  var _hl = newhl(shl.text, shl, true);
  _hl.cache = shl.cache; // hope this is right, shl is updated in _apply, that always creates an empty cache
  hl.push(_hl);

  var p = document.getElementById("persistents");
  var p0 = document.createElement("div");
  p0.id = "filter" + _hl.id;
  p0.className = "persistent";
  p0.style.backgroundColor = _hl.color;
  p0.innerHTML = _hl.text;
  p0.onclick = function() {selectfilter(_hl.id)};
  _setfilterelementstate(p0, _hl);
  p.appendChild(p0);

  _restartshl();
  selectfilter(_hl.id);
  if (dorender)
    render();

  colors.push(colors.shift());
}

function _apply()
{
  s = document.getElementById("search");
  var t = _triminput(s.value);

  if (!t)
  {
    shl = null;
  }
  else
  {
    t = _prepare(t)[0];
    shl = newhl(t, shl);
  }
}

function highlight()
{
  resetuistate();

  _apply();

  repaint();
  selectfilter(0);
}

function filter()
{
  resetuistate();

  if ((!shl && !hl.length) || (current == shl))
  {
    _apply();
    selectfilter(0);
  }

  if (current) {
    current.filter = !current.filter;
    _setfilterelementstate(_getfilterelement(current.id), current);
    if (filterswitch)
      render();
    else
      repaint();
  }
}

function group()
{
  resetuistate();

  // the code it self happens in selectfilter() function

  if (!shl)
  {
    _hint("press higlight or filter first");
    return;
  }

  if (hl.length)
  {
    groupwith = true;
    _hint("-&gt; now select a pinned filter to group the current highlight with");
  }
  else
  {
    _hint("you have to pin a filter with the 'pin' button first");
  }
}

function _restartshl()
{
  var s = document.getElementById("search");
  s.value = "";
  s.style.backgroundColor = "";
  s.style.textDecoration = "";
  current = shl = null;
}

function restart()
{
  resetuistate();

  var filtered = _gfilteron(); // was: = current && current.filter

  if (current == shl)
  {
    _restartshl();
  }
  else
  {
    var p0 = _getfilterelement(current.id);

    for (var h in hl)
      if (hl[h].id == current.id) {
        hl.splice(h, 1);
        break;
      }

    if (current.text) {
      shl = newhl(current.text, current);
      var s = document.getElementById("search");
      s.value = current.text;
      _setfilterelementstate(s, shl);
    }
    selectfilter(0);

    var p = document.getElementById("persistents");
    p.removeChild(p0);
  }

  if (!shl) // means: filter could not be switched back to shl or directly shl was reset
    render();
}

function selectfilter(filter)
{
  var el0 = _getfilterelement(current ? current.id : 0);
  var el1 = _getfilterelement(filter);

  el0.style.border = "";
  el0.style.margin = "";
  el1.style.border = "solid 2px #3ad";
  el1.style.margin = "0px";

  function filterbyid(id)
  {
    for (var h in hl)
      if (hl[h].id == id)
        return hl[h];
  }

  if (groupwith && filter)
  {
    el1.innerHTML += "+" + shl.text;
    var _hl = filterbyid(filter);
    _hl.text = ""; // not backward compatible
    _hl.text_r += "|" + shl.text_r;
    _hl.cache = {};
    resetuistate();
    _restartshl();
    render();
  }
  else
    resetuistate();

  current = (filter == 0) ? shl : filterbyid(filter);

  // A bit hacky redraw of the search box color :)
  if (filter === 0 && shl)
  {
    var s = document.getElementById("search");
    s.style.backgroundColor = shl.color;
  }
}

function flipfilter(event)
{
  filterswitch = !filterswitch;
  event.target.innerHTML = (filterswitch ? "filters on" : "filters off");
  render();

  event.stopPropagation();
}
