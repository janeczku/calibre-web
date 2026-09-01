/**
* Tom Select v2.6.2
* Licensed under the Apache License, Version 2.0 (the "License");
*/
!function(e,t){"object"==typeof exports&&"undefined"!=typeof module?module.exports=t():"function"==typeof define&&define.amd?define(t):(e="undefined"!=typeof globalThis?globalThis:e||self).TomSelect=t()}(this,function(){"use strict"
function e(e,t){e.split(/\s+/).forEach(e=>{t(e)})}class t{constructor(){this._events={}}on(t,i){e(t,e=>{const t=this._events[e]||[]
t.push(i),this._events[e]=t})}off(t,i){var s=arguments.length
0!==s?e(t,e=>{if(1===s)return void delete this._events[e]
const t=this._events[e]
void 0!==t&&(t.splice(t.indexOf(i),1),this._events[e]=t)}):this._events={}}trigger(t,...i){var s=this
e(t,e=>{const t=s._events[e]
void 0!==t&&t.forEach(e=>{e.apply(s,i)})})}}const i=e=>(e=e.filter(Boolean)).length<2?e[0]||"":1==l(e)?"["+e.join("")+"]":"(?:"+e.join("|")+")",s=e=>{if(!o(e))return e.join("")
let t="",i=0
const s=()=>{i>1&&(t+="{"+i+"}")}
return e.forEach((n,o)=>{n!==e[o-1]?(s(),t+=n,i=1):i++}),s(),t},n=e=>{let t=Array.from(e)
return i(t)},o=e=>new Set(e).size!==e.length,r=e=>(e+"").replace(/([\$\(\)\*\+\.\?\[\]\^\{\|\}\\])/gu,"\\$1"),l=e=>e.reduce((e,t)=>Math.max(e,a(t)),0),a=e=>Array.from(e).length,c=e=>{if(1===e.length)return[[e]]
let t=[]
const i=e.substring(1)
return c(i).forEach(function(i){let s=i.slice(0)
s[0]=e.charAt(0)+s[0],t.push(s),s=i.slice(0),s.unshift(e.charAt(0)),t.push(s)}),t},d=[[0,65535]]
let u,p
const h={},g={"/":"⁄∕",0:"߀",a:"ⱥɐɑ",aa:"ꜳ",ae:"æǽǣ",ao:"ꜵ",au:"ꜷ",av:"ꜹꜻ",ay:"ꜽ",b:"ƀɓƃ",c:"ꜿƈȼↄ",d:"đɗɖᴅƌꮷԁɦ",e:"ɛǝᴇɇ",f:"ꝼƒ",g:"ǥɠꞡᵹꝿɢ",h:"ħⱨⱶɥ",i:"ɨı",j:"ɉȷ",k:"ƙⱪꝁꝃꝅꞣ",l:"łƚɫⱡꝉꝇꞁɭ",m:"ɱɯϻ",n:"ꞥƞɲꞑᴎлԉ",o:"øǿɔɵꝋꝍᴑ",oe:"œ",oi:"ƣ",oo:"ꝏ",ou:"ȣ",p:"ƥᵽꝑꝓꝕρ",q:"ꝗꝙɋ",r:"ɍɽꝛꞧꞃ",s:"ßȿꞩꞅʂ",t:"ŧƭʈⱦꞇ",th:"þ",tz:"ꜩ",u:"ʉ",v:"ʋꝟʌ",vy:"ꝡ",w:"ⱳ",y:"ƴɏỿ",z:"ƶȥɀⱬꝣ",hv:"ƕ"}
for(let e in g){let t=g[e]||""
for(let i=0;i<t.length;i++){let s=t.substring(i,i+1)
h[s]=e}}const f=new RegExp(Object.keys(h).join("|")+"|[̀-ͯ·ʾʼ]","gu"),m=(e,t="NFKD")=>e.normalize(t),v=e=>Array.from(e).reduce((e,t)=>e+O(t),""),O=e=>(e=m(e).toLowerCase().replace(f,e=>h[e]||""),m(e,"NFC"))
const b=e=>{const t={},i=(e,i)=>{const s=t[e]||new Set,o=new RegExp("^"+n(s)+"$","iu")
i.match(o)||(s.add(r(i)),t[e]=s)}
for(let t of function*(e){for(const[t,i]of e)for(let e=t;e<=i;e++){let t=String.fromCharCode(e),i=v(t)
i!=t.toLowerCase()&&(i.length>3||0!=i.length&&(yield{folded:i,composed:t,code_point:e}))}}(e))i(t.folded,t.folded),i(t.folded,t.composed)
return t},y=e=>{const t=b(e),s={}
let o=[]
for(let e in t){let i=t[e]
i&&(s[e]=n(i)),e.length>1&&o.push(r(e))}o.sort((e,t)=>t.length-e.length)
const l=i(o)
return p=new RegExp("^"+l,"u"),s},w=(e,t=1)=>(t=Math.max(t,e.length-1),i(c(e).map(e=>((e,t=1)=>{let i=0
return e=e.map(e=>(u[e]&&(i+=e.length),u[e]||e)),i>=t?s(e):""})(e,t)))),S=(e,t=!0)=>{let n=e.length>1?1:0
return i(e.map(e=>{let i=[]
const o=t?e.length():e.length()-1
for(let t=0;t<o;t++)i.push(w(e.substrs[t]||"",n))
return s(i)}))},_=(e,t)=>{for(const i of t){if(i.start!=e.start||i.end!=e.end)continue
if(i.substrs.join("")!==e.substrs.join(""))continue
let t=e.parts
const s=e=>{for(const i of t){if(i.start===e.start&&i.substr===e.substr)return!1
if(1!=e.length&&1!=i.length){if(e.start<i.start&&e.end>i.start)return!0
if(i.start<e.start&&i.end>e.start)return!0}}return!1}
if(!(i.parts.filter(s).length>0))return!0}return!1}
class C{parts
substrs
start
end
constructor(){this.parts=[],this.substrs=[],this.start=0,this.end=0}add(e){e&&(this.parts.push(e),this.substrs.push(e.substr),this.start=Math.min(e.start,this.start),this.end=Math.max(e.end,this.end))}last(){return this.parts[this.parts.length-1]}length(){return this.parts.length}clone(e,t){let i=new C,s=JSON.parse(JSON.stringify(this.parts)),n=s.pop()
for(const e of s)i.add(e)
let o=t.substr.substring(0,e-n.start),r=o.length
return i.add({start:n.start,end:n.start+r,length:r,substr:o}),i}}const x=e=>{void 0===u&&(u=y(d)),e=v(e)
let t="",i=[new C]
for(let s=0;s<e.length;s++){let n=e.substring(s).match(p)
const o=e.substring(s,s+1),r=n?n[0]:null
let l=[],a=new Set
for(const e of i){const t=e.last()
if(!t||1==t.length||t.end<=s)if(r){const t=r.length
e.add({start:s,end:s+t,length:t,substr:r}),a.add("1")}else e.add({start:s,end:s+1,length:1,substr:o}),a.add("2")
else if(r){let i=e.clone(s,t)
const n=r.length
i.add({start:s,end:s+n,length:n,substr:r}),l.push(i)}else a.add("3")}if(l.length>0){l=l.sort((e,t)=>e.length()-t.length())
for(let e of l)_(e,i)||i.push(e)}else if(s>0&&1==a.size&&!a.has("3")){t+=S(i,!1)
let e=new C
const s=i[0]
s&&e.add(s.last()),i=[e]}}return t+=S(i,!0),t},A=(e,t)=>{if(e)return e[t]},I=(e,t)=>{if(e){for(var i,s=t.split(".");(i=s.shift())&&(e=e[i]););return e}},k=(e,t,i)=>{var s,n
return e?(e+="",null==t.regex||-1===(n=e.search(t.regex))?0:(s=t.string.length/e.length,0===n&&(s+=.5),s*i)):0},F=(e,t)=>{var i=e[t]
if("function"==typeof i)return i
i&&!Array.isArray(i)&&(e[t]=[i])},L=(e,t)=>{if(Array.isArray(e))e.forEach(t)
else for(var i in e)e.hasOwnProperty(i)&&t(e[i],i)},E=(e,t)=>"number"==typeof e&&"number"==typeof t?e>t?1:e<t?-1:0:(e=v(e+"").toLowerCase())>(t=v(t+"").toLowerCase())?1:t>e?-1:0
class T{items
settings
constructor(e,t){this.items=e,this.settings=t||{diacritics:!0}}tokenize(e,t,i){if(!e||!e.length)return[]
const s=[],n=e.split(/\s+/)
var o
return i&&(o=new RegExp("^("+Object.keys(i).map(r).join("|")+"):(.*)$")),n.forEach(e=>{let i,n=null,l=null
o&&(i=e.match(o))&&(n=i[1],e=i[2]),e.length>0&&(l=this.settings.diacritics?x(e)||null:r(e),l&&t&&(l="\\b"+l)),s.push({string:e,regex:l?new RegExp(l,"iu"):null,field:n})}),s}getScoreFunction(e,t){var i=this.prepareSearch(e,t)
return this._getScoreFunction(i)}_getScoreFunction(e){const t=e.tokens,i=t.length
if(!i)return function(){return 0}
const s=e.options.fields,n=e.weights,o=s.length,r=e.getAttrFn
if(!o)return function(){return 1}
const l=1===o?function(e,t){const i=s[0].field
return k(r(t,i),e,n[i]||1)}:function(e,t){var i=0
if(e.field){const s=r(t,e.field)
!e.regex&&s?i+=1/o:i+=k(s,e,1)}else L(n,(s,n)=>{i+=k(r(t,n),e,s)})
return i/o}
return 1===i?function(e){return l(t[0],e)}:"and"===e.options.conjunction?function(e){var s,n=0
for(let i of t){if((s=l(i,e))<=0)return 0
n+=s}return n/i}:function(e){var s=0
return L(t,t=>{s+=l(t,e)}),s/i}}getSortFunction(e,t){var i=this.prepareSearch(e,t)
return this._getSortFunction(i)}_getSortFunction(e){var t,i=[]
const s=this,n=e.options,o=!e.query&&n.sort_empty?n.sort_empty:n.sort
if("function"==typeof o)return o.bind(this)
const r=function(t,i){return"$score"===t?i.score:e.getAttrFn(s.items[i.id],t)}
if(o)for(let t of o)(e.query||"$score"!==t.field)&&i.push(t)
if(e.query){t=!0
for(let e of i)if("$score"===e.field){t=!1
break}t&&i.unshift({field:"$score",direction:"desc"})}else i=i.filter(e=>"$score"!==e.field)
return i.length?function(e,t){var s,n
for(let o of i){if(n=o.field,s=("desc"===o.direction?-1:1)*E(r(n,e),r(n,t)))return s}return 0}:null}prepareSearch(e,t){const i={}
var s=Object.assign({},t)
if(F(s,"sort"),F(s,"sort_empty"),s.fields){F(s,"fields")
const e=[]
s.fields.forEach(t=>{"string"==typeof t&&(t={field:t,weight:1}),e.push(t),i[t.field]="weight"in t?t.weight:1}),s.fields=e}return{options:s,query:e.toLowerCase().trim(),tokens:this.tokenize(e,s.respect_word_boundaries,i),total:0,items:[],weights:i,getAttrFn:s.nesting?I:A}}search(e,t){var i,s,n=this
s=this.prepareSearch(e,t),t=s.options,e=s.query
const o=t.score||n._getScoreFunction(s)
e.length?L(n.items,(e,n)=>{i=o(e),(!1===t.filter||i>0)&&s.items.push({score:i,id:n})}):L(n.items,(e,t)=>{s.items.push({score:1,id:t})})
const r=n._getSortFunction(s)
return r&&s.items.sort(r),s.total=s.items.length,"number"==typeof t.limit&&(s.items=s.items.slice(0,t.limit)),s}}const P=e=>null==e?null:N(e),N=e=>"boolean"==typeof e?e?"1":"0":e+"",D=e=>(e+"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"),V=(e,t)=>{var i
return function(s,n){var o=this
i&&(o.loading=Math.max(o.loading-1,0),clearTimeout(i)),i=setTimeout(function(){i=null,o.loadedSearches[s]=!0,e.call(o,s,n)},t)}},j=(e,t,i)=>{var s,n=e.trigger,o={}
for(s of(e.trigger=function(){var i=arguments[0]
if(-1===t.indexOf(i))return n.apply(e,arguments)
o[i]=arguments},i.apply(e,[]),e.trigger=n,t))s in o&&n.apply(e,o[s])},$=(e,t=!1)=>{e&&(e.preventDefault(),t&&e.stopPropagation())},q=(e,t,i,s)=>{e.addEventListener(t,i,s)},R=(e,t)=>!!t&&(!!t[e]&&1===(t.altKey?1:0)+(t.ctrlKey?1:0)+(t.shiftKey?1:0)+(t.metaKey?1:0)),H=(e,t)=>{const i=e.getAttribute("id")
return i||(e.setAttribute("id",t),t)},M=e=>e.replace(/[\\"']/g,"\\$&"),z=(e,t)=>{t&&e.append(t)},B=(e,t)=>{if(Array.isArray(e))e.forEach(t)
else for(var i in e)e.hasOwnProperty(i)&&t(e[i],i)},K=e=>{if(e.jquery)return e[0]
if(e instanceof HTMLElement)return e
if(G(e)){var t=document.createElement("template")
return t.innerHTML=e.trim(),t.content.firstChild}return document.querySelector(e)},G=e=>"string"==typeof e&&e.indexOf("<")>-1,U=(e,t)=>{var i=document.createEvent("HTMLEvents")
i.initEvent(t,!0,!1),e.dispatchEvent(i)},W=(e,t)=>{Object.assign(e.style,t)},Q=(e,...t)=>{var i=X(t);(e=Y(e)).map(e=>{i.map(t=>{e.classList.add(t)})})},J=(e,...t)=>{var i=X(t);(e=Y(e)).map(e=>{i.map(t=>{e.classList.remove(t)})})},X=e=>{var t=[]
return B(e,e=>{"string"==typeof e&&(e=e.trim().split(/[\t\n\f\r\s]/)),Array.isArray(e)&&(t=t.concat(e))}),t.filter(Boolean)},Y=e=>(Array.isArray(e)||(e=[e]),e),Z=(e,t,i)=>{if(!i||i.contains(e))for(;e&&e.matches;){if(e.matches(t))return e
e=e.parentNode}},ee=(e,t=0)=>t>0?e[e.length-1]:e[0],te=(e,t)=>{if(!e)return-1
t=t||e.nodeName
for(var i=0;e=e.previousElementSibling;)e.matches(t)&&i++
return i},ie=(e,t)=>{B(t,(t,i)=>{null==t?e.removeAttribute(i):e.setAttribute(i,""+t)})},se=(e,t)=>{e.parentNode&&e.parentNode.replaceChild(t,e)},ne=(e,t)=>{if(null===t)return
if("string"==typeof t){if(!t.length)return
t=new RegExp(t,"i")}const i=e=>3===e.nodeType?(e=>{var i=e.data.match(t)
if(i&&e.data.length>0){var s=document.createElement("span")
s.className="highlight"
var n=e.splitText(i.index)
n.splitText(i[0].length)
var o=n.cloneNode(!0)
return s.appendChild(o),se(n,s),1}return 0})(e):((e=>{1!==e.nodeType||!e.childNodes||/(script|style)/i.test(e.tagName)||"highlight"===e.className&&"SPAN"===e.tagName||Array.from(e.childNodes).forEach(e=>{i(e)})})(e),0)
i(e)},oe="undefined"!=typeof navigator&&/Mac/.test(navigator.userAgent)?"metaKey":"ctrlKey"
var re={options:[],optgroups:[],plugins:[],delimiter:",",splitOn:null,persist:!0,diacritics:!0,create:null,createOnBlur:!1,createFilter:null,clearAfterSelect:!1,highlight:!0,openOnFocus:!0,shouldOpen:null,maxOptions:50,maxItems:null,hideSelected:null,duplicates:!1,addPrecedence:!1,selectOnTab:!1,preload:null,allowEmptyOption:!1,refreshThrottle:300,loadThrottle:300,loadingClass:"loading",dataAttr:null,optgroupField:"optgroup",valueField:"value",labelField:"text",disabledField:"disabled",optgroupLabelField:"label",optgroupValueField:"value",lockOptgroupOrder:!1,sortField:"$order",searchField:["text"],searchConjunction:"and",mode:null,wrapperClass:"ts-wrapper",controlClass:"ts-control",dropdownClass:"ts-dropdown",dropdownContentClass:"ts-dropdown-content",itemClass:"item",optionClass:"option",dropdownParent:null,controlInput:'<input type="text" autocomplete="off" size="1" />',copyClassesToDropdown:!1,placeholder:null,hidePlaceholder:null,shouldLoad:function(e){return e.length>0},render:{}}
function le(e,t){var i=Object.assign({},re,t),s=i.dataAttr,n=i.labelField,o=i.valueField,r=i.disabledField,l=i.optgroupField,a=i.optgroupLabelField,c=i.optgroupValueField,d=e.tagName.toLowerCase(),u=e.getAttribute("placeholder")||e.getAttribute("data-placeholder")
if(!u&&!i.allowEmptyOption){let t=e.querySelector('option[value=""]')
t&&(u=t.textContent)}var p={placeholder:u,options:[],optgroups:[],items:[],maxItems:null}
return"select"===d?(()=>{var t,d=p.options,u={},h=1
let g=0
var f=e=>{var t=Object.assign({},e.dataset),i=s&&t[s]
return"string"==typeof i&&i.length&&(t=Object.assign(t,JSON.parse(i))),t},m=(e,t)=>{var s=P(e.value)
if(null!=s&&(s||i.allowEmptyOption)){if(u.hasOwnProperty(s)){if(t){var a=u[s][l]
a?Array.isArray(a)?a.push(t):u[s][l]=[a,t]:u[s][l]=t}}else{var c=f(e)
c[n]=c[n]||e.textContent,c[o]=c[o]||s,c[r]=c[r]||e.disabled,c[l]=c[l]||t,c.$option=e,c.$order=c.$order||++g,u[s]=c,d.push(c)}e.selected&&p.items.push(s)}}
p.maxItems=e.hasAttribute("multiple")?null:1,B(e.children,e=>{var i,s,n
"optgroup"===(t=e.tagName.toLowerCase())?((n=f(i=e))[a]=n[a]||i.getAttribute("label")||"",n[c]=n[c]||h++,n[r]=n[r]||i.disabled,n.$order=n.$order||++g,p.optgroups.push(n),s=n[c],B(i.children,e=>{m(e,s)})):"option"===t&&m(e)})})():(()=>{const t=e.getAttribute(s)
if(t)p.options=JSON.parse(t),B(p.options,e=>{p.items.push(e[o])})
else{var r,l,a=null!=(r=null==e||null==(l=e.value)?void 0:l.trim())?r:""
if(!i.allowEmptyOption&&!a.length)return
const t=a.split(i.delimiter)
B(t,e=>{const t={}
t[n]=e,t[o]=e,p.options.push(t)}),p.items=t}})(),Object.assign({},re,p,t)}var ae=0
class ce extends(function(e){return e.plugins={},class extends e{constructor(...e){super(...e),this.plugins={names:[],settings:{},requested:{},loaded:{}}}static define(t,i){e.plugins[t]={name:t,fn:i}}initializePlugins(e){var t,i
const s=this,n=[]
if(Array.isArray(e))e.forEach(e=>{"string"==typeof e?n.push(e):(s.plugins.settings[e.name]=e.options,n.push(e.name))})
else if(e)for(t in e)e.hasOwnProperty(t)&&(s.plugins.settings[t]=e[t],n.push(t))
for(;i=n.shift();)s.require(i)}loadPlugin(t){var i=this,s=i.plugins,n=e.plugins[t]
if(!e.plugins.hasOwnProperty(t))throw new Error('Unable to find "'+t+'" plugin')
s.requested[t]=!0,s.loaded[t]=n.fn.apply(i,[i.plugins.settings[t]||{}]),s.names.push(t)}require(e){var t=this,i=t.plugins
if(!t.plugins.loaded.hasOwnProperty(e)){if(i.requested[e])throw new Error('Plugin has circular dependency ("'+e+'")')
t.loadPlugin(e)}return i.loaded[e]}}}(t)){constructor(e,t){var i
super(),this.order=0,this.isOpen=!1,this.isDisabled=!1,this.isReadOnly=!1,this.isInvalid=!1,this.isValid=!0,this.isLocked=!1,this.isFocused=!1,this.isInputHidden=!1,this.isSetup=!1,this.isDropdownContentStale=!0,this.ignoreFocus=!1,this.ignoreHover=!1,this.hasOptions=!1,this.lastValue="",this.caretPos=0,this.loading=0,this.loadedSearches={},this.activeOption=null,this.activeItems=[],this.optgroups={},this.options={},this.userOptions={},this.items=[],this.refreshTimeout=null,ae++
var s=K(e)
if(s.tomselect)throw new Error("Tom Select already initialized on this element")
s.tomselect=this,i=(window.getComputedStyle&&window.getComputedStyle(s,null)).getPropertyValue("direction")
const n=le(s,t)
this.settings=n,this.input=s,this.tabIndex=s.tabIndex||0,this.is_select_tag="select"===s.tagName.toLowerCase(),this.rtl=/rtl/i.test(i),this.inputId=H(s,"tomselect-"+ae),this.isRequired=s.required,this.sifter=new T(this.options,{diacritics:n.diacritics}),n.mode=n.mode||(1===n.maxItems?"single":"multi"),"boolean"!=typeof n.hideSelected&&(n.hideSelected="multi"===n.mode),"boolean"!=typeof n.hidePlaceholder&&(n.hidePlaceholder="multi"!==n.mode)
var o=n.createFilter
"function"!=typeof o&&("string"==typeof o&&(o=new RegExp(o)),o instanceof RegExp?n.createFilter=e=>o.test(e):n.createFilter=e=>this.settings.duplicates||!this.options[e]),this.initializePlugins(n.plugins),this.setupCallbacks(),this.setupTemplates()
const r=K("<div>"),l=K("<div>"),a=this._render("dropdown"),c=K('<div role="listbox" tabindex="-1">'),d=this.input.getAttribute("class")||"",u=n.mode
var p
if(Q(r,n.wrapperClass,d,u),Q(l,n.controlClass),z(r,l),Q(a,n.dropdownClass,u),n.copyClassesToDropdown&&Q(a,d),Q(c,n.dropdownContentClass),z(a,c),K(n.dropdownParent||r).appendChild(a),G(n.controlInput)){p=K(n.controlInput)
B(["autocorrect","autocapitalize","autocomplete","spellcheck","aria-label"],e=>{s.getAttribute(e)&&ie(p,{[e]:s.getAttribute(e)})}),p.tabIndex=-1,l.appendChild(p),this.focus_node=p}else n.controlInput?(p=K(n.controlInput),this.focus_node=p):(p=K("<input/>"),this.focus_node=l)
this.wrapper=r,this.dropdown=a,this.dropdown_content=c,this.control=l,this.control_input=p,this.setup()}setup(){const e=this,t=e.settings,i=e.control_input,s=e.dropdown,n=e.dropdown_content,o=e.wrapper,l=e.control,a=e.input,c=e.focus_node,d={passive:!0},u=e.inputId+"-ts-dropdown"
ie(n,{id:u}),ie(c,{role:"combobox","aria-haspopup":"listbox","aria-expanded":"false","aria-controls":u})
const p=H(c,e.inputId+"-ts-control"),h="label[for='"+(e=>e.replace(/['"\\]/g,"\\$&"))(e.inputId)+"']",g=document.querySelector(h),f=e.focus.bind(e)
if(g){q(g,"click",f),ie(g,{for:p})
const t=H(g,e.inputId+"-ts-label")
ie(c,{"aria-labelledby":t}),ie(n,{"aria-labelledby":t})}if(o.style.width=a.style.width,o.style.minWidth=a.style.minWidth,o.style.maxWidth=a.style.maxWidth,e.plugins.names.length){const t="plugin-"+e.plugins.names.join(" plugin-")
Q([o,s],t)}(null===t.maxItems||t.maxItems>1)&&e.is_select_tag&&ie(a,{multiple:"multiple"}),t.placeholder&&ie(i,{placeholder:t.placeholder}),!t.splitOn&&t.delimiter&&(t.splitOn=new RegExp("\\s*"+r(t.delimiter)+"+\\s*")),t.load&&t.loadThrottle&&(t.load=V(t.load,t.loadThrottle)),q(s,"mousemove",()=>{e.ignoreHover=!1}),q(s,"mouseenter",t=>{var i=Z(t.target,"[data-selectable]",s)
i&&e.onOptionHover(t,i)},{capture:!0}),q(s,"click",t=>{const i=Z(t.target,"[data-selectable]")
i&&(e.onOptionSelect(t,i),$(t,!0))}),q(l,"click",t=>{var s=Z(t.target,"[data-ts-item]",l)
s&&e.onItemSelect(t,s)?$(t,!0):""==i.value&&(e.onClick(),$(t,!0))}),q(c,"keydown",t=>e.onKeyDown(t)),q(i,"keypress",t=>e.onKeyPress(t)),q(i,"input",t=>e.onInput(t)),q(c,"blur",t=>e.onBlur(t)),q(c,"focus",t=>e.onFocus(t)),q(i,"paste",t=>e.onPaste(t))
const m=t=>{const n=t.composedPath()[0]
if(!o.contains(n)&&!s.contains(n))return e.isFocused&&e.blur(),void e.inputState()
n==i&&e.isOpen?t.stopPropagation():$(t,!0)},v=()=>{e.isOpen&&e.positionDropdown()},O=()=>{e.isValid&&(e.isValid=!1,e.isInvalid=!0,e.refreshState())}
q(a,"invalid",O),q(document,"mousedown",m),q(window,"scroll",v,d),q(window,"resize",v,d),this._destroy=()=>{a.removeEventListener("invalid",O),document.removeEventListener("mousedown",m),window.removeEventListener("scroll",v),window.removeEventListener("resize",v),g&&g.removeEventListener("click",f)},this.revertSettings={innerHTML:a.innerHTML,tabIndex:a.tabIndex},a.tabIndex=-1,a.insertAdjacentElement("afterend",e.wrapper),e.sync(!1),t.items=[],delete t.optgroups,delete t.options,e.refreshItems(),e.close(!1),e.inputState(),e.isSetup=!0,e.on("change",this.onChange),Q(a,"tomselected","ts-hidden-accessible"),e.trigger("initialize"),!0===t.preload&&e.preload()}setupOptions(e=[],t=[]){this.addOptions(e),B(t,e=>{this.registerOptionGroup(e)})}setupTemplates(){var e=this,t=e.settings.labelField,i=e.settings.optgroupLabelField,s={optgroup:e=>{let t=document.createElement("div")
return t.className="optgroup",t.appendChild(e.options),t},optgroup_header:(e,t)=>'<div class="optgroup-header">'+t(e[i])+"</div>",option:(e,i)=>"<div>"+i(e[t])+"</div>",item:(e,i)=>"<div>"+i(e[t])+"</div>",option_create:(e,t)=>'<div class="create">Add <strong>'+t(e.input)+"</strong>&hellip;</div>",no_results:()=>'<div class="no-results">No results found</div>',loading:()=>'<div class="spinner"></div>',not_loading:()=>{},dropdown:()=>"<div></div>"}
e.settings.render=Object.assign({},s,e.settings.render)}setupCallbacks(){var e,t,i={initialize:"onInitialize",change:"onChange",item_add:"onItemAdd",item_remove:"onItemRemove",item_select:"onItemSelect",clear:"onClear",option_add:"onOptionAdd",option_remove:"onOptionRemove",option_clear:"onOptionClear",optgroup_add:"onOptionGroupAdd",optgroup_remove:"onOptionGroupRemove",optgroup_clear:"onOptionGroupClear",dropdown_open:"onDropdownOpen",dropdown_close:"onDropdownClose",type:"onType",load:"onLoad",focus:"onFocus",blur:"onBlur"}
for(e in i)(t=this.settings[i[e]])&&this.on(e,t)}sync(e=!0){const t=this,i=e?le(t.input,{delimiter:t.settings.delimiter,allowEmptyOption:t.settings.allowEmptyOption}):t.settings
t.setupOptions(i.options,i.optgroups),t.setValue(i.items||[],!0),t.input.disabled?t.disable():t.input.readOnly?t.setReadOnly(!0):t.enable(),t.lastQuery=null}onClick(){var e=this
if(e.activeItems.length>0)return e.clearActiveItems(),void e.focus()
e.isFocused&&e.isOpen?e.blur():e.focus()}onMouseDown(){}onChange(){U(this.input,"input"),U(this.input,"change")}onPaste(e){var t=this
t.isInputHidden||t.isLocked?$(e):t.settings.splitOn&&setTimeout(()=>{var e=t.inputValue()
if(e.match(t.settings.splitOn)){var i=e.trim().split(t.settings.splitOn)
B(i,e=>{P(e)&&(this.options[e]?t.addItem(e):t.createItem(e))})}},0)}onKeyPress(e){var t=this
if(!t.isLocked){var i=String.fromCharCode(e.keyCode||e.which)
return t.settings.create&&"multi"===t.settings.mode&&i===t.settings.delimiter?(t.createItem(),void $(e)):void 0}$(e)}onKeyDown(e){var t=this
if(t.ignoreHover=!0,t.isLocked)9!==e.keyCode&&$(e)
else{switch(e.keyCode){case 65:if(R(oe,e)&&""==t.control_input.value)return $(e),void t.selectAll()
break
case 27:return t.isOpen&&($(e,!0),t.close()),void t.clearActiveItems()
case 40:if(!t.isOpen&&t.hasOptions)t.open()
else if(t.activeOption){let e=t.getAdjacent(t.activeOption,1)
e&&t.setActiveOption(e)}return void $(e)
case 38:if(t.activeOption){let e=t.getAdjacent(t.activeOption,-1)
e&&t.setActiveOption(e)}return void $(e)
case 13:return void(t.canSelect(t.activeOption)?(t.onOptionSelect(e,t.activeOption),$(e)):(t.settings.create&&t.createItem()||document.activeElement==t.control_input&&t.isOpen)&&$(e))
case 37:return void t.advanceSelection(-1,e)
case 39:return void t.advanceSelection(1,e)
case 9:return void(t.settings.selectOnTab&&(t.canSelect(t.activeOption)?(t.onOptionSelect(e,t.activeOption),$(e)):t.settings.create&&t.createItem()&&$(e)))
case 8:case 46:return void t.deleteSelection(e)}t.isInputHidden&&!R(oe,e)&&$(e)}}onInput(e){if(this.isLocked)return
const t=this.inputValue()
this.lastValue!==t&&(this.lastValue=t,""!=t?(this.refreshTimeout&&window.clearTimeout(this.refreshTimeout),this.refreshTimeout=((e,t)=>t>0?window.setTimeout(e,t):(e.call(null),null))(()=>{this.refreshTimeout=null,this._onInput()},this.settings.refreshThrottle)):this._onInput())}_onInput(){const e=this.lastValue
this.settings.shouldLoad.call(this,e)&&this.load(e),this.refreshOptions(),this.trigger("type",e)}onOptionHover(e,t){this.ignoreHover||this.setActiveOption(t,!1)}onFocus(e){var t=this,i=t.isFocused
if(t.isDisabled||t.isReadOnly)return t.blur(),void $(e)
t.ignoreFocus||(t.isFocused=!0,"focus"===t.settings.preload&&t.preload(),i||t.trigger("focus"),t.activeItems.length||(t.inputState(),t.refreshOptions(!!t.settings.openOnFocus)),t.refreshState())}onBlur(e){if(!1!==document.hasFocus()){var t=this
if(t.isFocused){t.isFocused=!1,t.ignoreFocus=!1
var i=()=>{t.close(),t.setActiveItem(),t.setCaret(t.items.length),t.trigger("blur")}
t.settings.create&&t.settings.createOnBlur?t.createItem(null,i):i()}}}onOptionSelect(e,t){var i,s=this
t.parentElement&&t.parentElement.matches("[data-disabled]")||(t.classList.contains("create")?s.createItem(null,()=>{s.settings.closeAfterSelect?s.close():s.settings.clearAfterSelect&&s.setTextboxValue()}):void 0!==(i=t.dataset.value)&&(s.isDropdownContentStale=s.settings.hideSelected,s.addItem(i),s.settings.closeAfterSelect?s.close():s.settings.clearAfterSelect&&s.setTextboxValue(),!s.settings.hideSelected&&e.type&&/click/.test(e.type)&&s.setActiveOption(t)))}canSelect(e){return!!(this.isOpen&&e&&this.dropdown_content.contains(e))}onItemSelect(e,t){var i=this
return!i.isLocked&&"multi"===i.settings.mode&&($(e),i.setActiveItem(t,e),!0)}canLoad(e){return!!this.settings.load&&!this.loadedSearches.hasOwnProperty(e)}load(e){const t=this
if(!t.canLoad(e))return
Q(t.wrapper,t.settings.loadingClass),t.loading++
const i=t.loadCallback.bind(t)
t.settings.load.call(t,e,i)}loadCallback(e,t){const i=this
i.loading=Math.max(i.loading-1,0),i.isDropdownContentStale=!0,i.clearActiveOption(),i.setupOptions(e,t),i.refreshOptions(i.isFocused&&!i.isInputHidden),i.loading||J(i.wrapper,i.settings.loadingClass),i.trigger("load",e,t)}preload(){var e=this.wrapper.classList
e.contains("preloaded")||(e.add("preloaded"),this.load(""))}setTextboxValue(e=""){var t=this.control_input
t.value!==e&&(t.value=e,U(t,"update"),this.lastValue=e)}getValue(){return this.is_select_tag&&this.input.hasAttribute("multiple")?this.items:this.items.join(this.settings.delimiter)}setValue(e,t){j(this,t?[]:["change"],()=>{this.clear(t),this.addItems(e,t)})}setMaxItems(e){0===e&&(e=null),this.settings.maxItems=e,this.refreshState()}setActiveItem(e,t){var i,s,n,o,r,l,a=this
if("single"!==a.settings.mode){if(!e)return a.clearActiveItems(),void(a.isFocused&&a.inputState())
if("click"===(i=t&&t.type.toLowerCase())&&R("shiftKey",t)&&a.activeItems.length){for(l=a.getLastActive(),(n=Array.prototype.indexOf.call(a.control.children,l))>(o=Array.prototype.indexOf.call(a.control.children,e))&&(r=n,n=o,o=r),s=n;s<=o;s++)e=a.control.children[s],-1===a.activeItems.indexOf(e)&&a.setActiveItemClass(e)
$(t)}else"click"===i&&R(oe,t)||"keydown"===i&&R("shiftKey",t)?e.classList.contains("active")?a.removeActiveItem(e):a.setActiveItemClass(e):(a.clearActiveItems(),a.setActiveItemClass(e))
a.inputState(),a.isFocused||a.focus()}}setActiveItemClass(e){const t=this,i=t.control.querySelector(".last-active")
i&&J(i,"last-active"),Q(e,"active last-active"),t.trigger("item_select",e),-1==t.activeItems.indexOf(e)&&t.activeItems.push(e)}removeActiveItem(e){var t=this.activeItems.indexOf(e)
this.activeItems.splice(t,1),J(e,"active")}clearActiveItems(){J(this.activeItems,"active"),this.activeItems=[]}setActiveOption(e,t=!0){e!==this.activeOption&&(this.clearActiveOption(),e&&(this.activeOption=e,ie(this.focus_node,{"aria-activedescendant":e.getAttribute("id")}),ie(e,{"aria-selected":"true"}),Q(e,"active"),t&&this.scrollToOption(e)))}scrollToOption(e,t){if(!e)return
const i=this.dropdown_content,s=i.clientHeight,n=i.scrollTop||0,o=e.offsetHeight,r=e.getBoundingClientRect().top-i.getBoundingClientRect().top+n
r+o>s+n?this.scroll(r-s+o,t):r<n&&this.scroll(r,t)}scroll(e,t){const i=this.dropdown_content
t&&(i.style.scrollBehavior=t),i.scrollTop=e,i.style.scrollBehavior=""}clearActiveOption(){this.activeOption&&(J(this.activeOption,"active"),ie(this.activeOption,{"aria-selected":null})),this.activeOption=null,ie(this.focus_node,{"aria-activedescendant":null})}selectAll(){const e=this
if("single"===e.settings.mode)return
const t=e.controlChildren()
t.length&&(e.inputState(),e.close(),e.activeItems=t,B(t,t=>{e.setActiveItemClass(t)}))}inputState(){var e=this
e.control.contains(e.control_input)&&(ie(e.control_input,{placeholder:e.settings.placeholder}),e.activeItems.length>0||!e.isFocused&&e.settings.hidePlaceholder&&e.items.length>0?(e.setTextboxValue(),e.isInputHidden=!0):(e.settings.hidePlaceholder&&e.items.length>0&&ie(e.control_input,{placeholder:""}),e.isInputHidden=!1),e.wrapper.classList.toggle("input-hidden",e.isInputHidden))}inputValue(){return this.control_input.value.trim()}focus(){var e=this
if(e.isDisabled||e.isReadOnly)return
e.ignoreFocus=!0
const t=this.control_input.offsetWidth?this.control_input:this.focus_node
t.focus(),setTimeout(()=>{e.ignoreFocus=!1
t.getRootNode().activeElement===t&&this.onFocus()},0)}blur(){this.focus_node.blur(),this.onBlur()}getScoreFunction(e){return this.sifter.getScoreFunction(e,this.getSearchOptions())}getSearchOptions(){var e=this.settings,t=e.sortField
return"string"==typeof e.sortField&&(t=[{field:e.sortField}]),{fields:e.searchField,conjunction:e.searchConjunction,sort:t,nesting:e.nesting}}search(e){var t,i,s=this,n=this.getSearchOptions()
if(s.settings.score&&"function"!=typeof(i=s.settings.score.call(s,e)))throw new Error('Tom Select "score" setting must be a function that returns a function')
return s.isDropdownContentStale||e!==s.lastQuery?(s.lastQuery=e,/(.)\1{15,}/.test(e)&&(e=""),t=s.sifter.search(e,Object.assign(n,{score:i})),s.currentResults=t):t=Object.assign({},s.currentResults),s.settings.hideSelected&&(t.items=t.items.filter(e=>{let t=P(e.id)
return!(null!==t&&-1!==s.items.indexOf(t))})),t}refreshOptions(e=!0){var t,i,s,n,o,r,l,a,c,d
const u={},p=[]
var h=this,g=h.inputValue()
const f=g===h.lastQuery||""==g&&null==h.lastQuery
var m=h.search(g),v=null,O=h.settings.shouldOpen||!1,b=h.dropdown_content
f&&(v=h.activeOption)&&(c=v.closest("[data-group]")),n=m.items.length,"number"==typeof h.settings.maxOptions&&(n=Math.min(n,h.settings.maxOptions)),n>0&&(O=!0)
const y=(e,t)=>{let i=u[e]
if(void 0!==i){let e=p[i]
if(void 0!==e)return[i,e.fragment]}let s=document.createDocumentFragment()
return i=p.length,p.push({fragment:s,order:t,optgroup:e}),[i,s]}
for(t=0;t<n;t++){let e=m.items[t]
if(!e)continue
let n=e.id,l=h.options[n]
if(void 0===l)continue
let a=N(n),d=h.getOption(a,!0)
for(h.settings.hideSelected||d.classList.toggle("selected",h.items.includes(a)),o=l[h.settings.optgroupField]||"",i=0,s=(r=Array.isArray(o)?o:[o])&&r.length;i<s;i++){o=r[i]
let e=l.$order,t=h.optgroups[o]
var w
if(void 0===t&&"function"==typeof h.settings.optionGroupRegister)(w=h.settings.optionGroupRegister.apply(h,[o]))&&h.registerOptionGroup(w)
t=h.optgroups[o],void 0===t?o="":e=t.$order
const[s,a]=y(o,e)
i>0&&(d=d.cloneNode(!0),ie(d,{id:l.$id+"-clone-"+i,"aria-selected":null}),d.classList.add("ts-cloned"),J(d,"active"),h.activeOption&&h.activeOption.dataset.value==n&&c&&c.dataset.group===o.toString()&&(v=d)),a.appendChild(d),""!=o&&(u[o]=s)}}var S
h.settings.lockOptgroupOrder&&p.sort((e,t)=>e.order-t.order),l=document.createDocumentFragment(),B(p,e=>{let t=e.fragment,i=e.optgroup
if(!t||!t.children.length)return
let s=h.optgroups[i]
if(void 0!==s){let e=document.createDocumentFragment(),i=h.render("optgroup_header",s)
z(e,i),z(e,t)
let n=h.render("optgroup",{group:s,options:e})
z(l,n)}else z(l,t)}),b.innerHTML="",z(b,l),h.isDropdownContentStale=!1,h.settings.highlight&&(S=b.querySelectorAll("span.highlight"),Array.prototype.forEach.call(S,function(e){var t=e.parentNode
t.replaceChild(e.firstChild,e),t.normalize()}),m.query.length&&m.tokens.length&&B(m.tokens,e=>{ne(b,e.regex)}))
var _=e=>{let t=h.render(e,{input:g})
return t&&(O=!0,b.insertBefore(t,b.firstChild)),t}
if(h.loading?_("loading"):h.settings.shouldLoad.call(h,g)?0===m.items.length&&_("no_results"):_("not_loading"),(a=h.canCreate(g))&&(d=_("option_create")),h.hasOptions=m.items.length>0||a,O){if(m.items.length>0){if(v||"single"!==h.settings.mode||null==h.items[0]||(v=h.getOption(h.items[0])),!b.contains(v)){let e=0
d&&!h.settings.addPrecedence&&(e=1),v=h.selectable()[e]}}else d&&(v=d)
e&&!h.isOpen&&(h.open(),h.scrollToOption(v,"auto")),h.setActiveOption(v)}else h.clearActiveOption(),e&&h.isOpen&&h.close(!1)}selectable(){return this.dropdown_content.querySelectorAll("[data-selectable]")}addOption(e,t=!1){const i=this
if(Array.isArray(e))return i.addOptions(e,t),!1
const s=P(e[i.settings.valueField])
return null===s||i.options.hasOwnProperty(s)?(i.updateOption(e[i.settings.valueField],e),!1):(e.$order=e.$order||++i.order,e.$id=i.inputId+"-opt-"+e.$order,i.options[s]=e,i.isDropdownContentStale=!0,t&&(i.userOptions[s]=t,i.trigger("option_add",s,e)),s)}addOptions(e,t=!1){B(e,e=>{this.addOption(e,t)})}registerOption(e){return this.addOption(e)}registerOptionGroup(e){var t=P(e[this.settings.optgroupValueField])
return null!==t&&(e.$order=e.$order||++this.order,this.optgroups[t]=e,t)}addOptionGroup(e,t){var i
t[this.settings.optgroupValueField]=e,(i=this.registerOptionGroup(t))&&this.trigger("optgroup_add",i,t)}removeOptionGroup(e){this.optgroups.hasOwnProperty(e)&&(delete this.optgroups[e],this.clearCache(),this.trigger("optgroup_remove",e))}clearOptionGroups(){this.optgroups={},this.clearCache(),this.trigger("optgroup_clear")}updateOption(e,t){const i=this
var s,n
const o=P(e),r=P(t[i.settings.valueField])
if(null===o)return
const l=i.options[o]
if(null==l)return
if("string"!=typeof r)throw new Error("Value must be set in option data")
const a=i.getOption(o),c=i.getItem(o)
if(t.$order=t.$order||l.$order,delete i.options[o],i.uncacheValue(r),i.options[r]=t,a){if(i.dropdown_content.contains(a)){const e=i._render("option",t)
se(a,e),i.activeOption===a&&i.setActiveOption(e)}a.remove()}c&&(-1!==(n=i.items.indexOf(o))&&i.items.splice(n,1,r),s=i._render("item",t),c.classList.contains("active")&&Q(s,"active"),se(c,s)),i.isDropdownContentStale=!0}removeOption(e,t){const i=this
e=N(e),i.uncacheValue(e),delete i.userOptions[e],delete i.options[e],i.isDropdownContentStale=!0,i.trigger("option_remove",e),i.removeItem(e,t)}clearOptions(e){const t=(e||this.clearFilter).bind(this)
this.loadedSearches={},this.userOptions={},this.clearCache()
const i={}
B(this.options,(e,s)=>{t(e,s)&&(i[s]=e)}),this.options=this.sifter.items=i,this.isDropdownContentStale=!0,this.trigger("option_clear")}clearFilter(e,t){return this.items.indexOf(t)>=0}getOption(e,t=!1){const i=P(e)
if(null===i)return null
const s=this.options[i]
if(null!=s){if(s.$div)return s.$div
if(t)return this._render("option",s)}return null}getAdjacent(e,t,i="option"){var s
if(!e)return null
s="item"==i?this.controlChildren():this.dropdown_content.querySelectorAll("[data-selectable]")
for(let i=0;i<s.length;i++)if(s[i]==e)return t>0?s[i+1]:s[i-1]
return null}getItem(e){if("object"==typeof e)return e
var t=P(e)
return null!==t?this.control.querySelector(`[data-value="${M(t)}"]`):null}addItems(e,t){var i=this,s=Array.isArray(e)?e:[e]
const n=(s=s.filter(e=>-1===i.items.indexOf(e)))[s.length-1]
s.forEach(e=>{i.isPending=e!==n,i.addItem(e,t)})}addItem(e,t){j(this,t?[]:["change","dropdown_close"],()=>{var i,s
const n=this,o=n.settings.mode,r=P(e)
if((!r||-1===n.items.indexOf(r)||("single"===o&&n.close(),"single"!==o&&n.settings.duplicates))&&null!==r&&n.options.hasOwnProperty(r)&&("single"===o&&n.clear(t),"multi"!==o||!n.isFull())){if(i=n._render("item",n.options[r]),n.control.contains(i)&&(i=i.cloneNode(!0)),s=n.isFull(),n.items.splice(n.caretPos,0,r),n.insertAtCaret(i),n.isSetup){if(!n.isPending&&n.settings.hideSelected){let e=n.getOption(r),t=n.getAdjacent(e,1)
t&&n.setActiveOption(t)}n.settings.clearAfterSelect&&n.setTextboxValue(),n.isPending||n.settings.closeAfterSelect||n.refreshOptions(n.isFocused&&"single"!==o),0!=n.settings.closeAfterSelect&&n.isFull()?n.close():n.isPending||n.positionDropdown(),n.trigger("item_add",r,i),n.isPending||n.updateOriginalInput({silent:t})}(!n.isPending||!s&&n.isFull())&&(n.inputState(),n.refreshState())}})}removeItem(e=null,t){const i=this
if(!(e=i.getItem(e)))return
var s,n
const o=e.dataset.value
s=te(e),e.remove(),e.classList.contains("active")&&(n=i.activeItems.indexOf(e),i.activeItems.splice(n,1),J(e,"active")),i.items.splice(s,1),i.isDropdownContentStale=!0,!i.settings.persist&&i.userOptions.hasOwnProperty(o)&&i.removeOption(o,t),s<i.caretPos&&i.setCaret(i.caretPos-1),i.updateOriginalInput({silent:t}),i.refreshState(),i.positionDropdown(),i.trigger("item_remove",o,e)}createItem(e=null,t=()=>{}){3===arguments.length&&(t=arguments[2]),"function"!=typeof t&&(t=()=>{})
var i,s=this,n=s.caretPos
if(e=e||s.inputValue(),!s.canCreate(e)){return P(e)&&this.options[e]&&s.addItem(e),t(),!1}s.lock()
var o=!1,r=e=>{if(s.unlock(),!e||"object"!=typeof e)return t()
var i=P(e[s.settings.valueField])
if("string"!=typeof i)return t()
s.setTextboxValue(),s.addOption(e,!0),s.setCaret(n),s.addItem(i),t(e),o=!0}
return i="function"==typeof s.settings.create?s.settings.create.call(this,e,r):{[s.settings.labelField]:e,[s.settings.valueField]:e},o||r(i),!0}refreshItems(){var e=this
e.isDropdownContentStale=!0,e.isSetup&&e.addItems(e.items),e.updateOriginalInput(),e.refreshState()}refreshState(){const e=this
e.refreshValidityState()
const t=e.isFull(),i=e.isLocked
e.wrapper.classList.toggle("rtl",e.rtl)
const s=e.wrapper.classList
var n
s.toggle("focus",e.isFocused),s.toggle("disabled",e.isDisabled),s.toggle("readonly",e.isReadOnly),s.toggle("required",e.isRequired),s.toggle("invalid",!e.isValid),s.toggle("locked",i),s.toggle("full",t),s.toggle("input-active",e.isFocused&&!e.isInputHidden),s.toggle("dropdown-active",e.isOpen),s.toggle("has-options",(n=e.options,0===Object.keys(n).length)),s.toggle("has-items",e.items.length>0)}refreshValidityState(){var e=this
e.input.validity&&(e.isValid=e.input.validity.valid,e.isInvalid=!e.isValid)}isFull(){return null!==this.settings.maxItems&&this.items.length>=this.settings.maxItems}updateOriginalInput(e={}){const t=this
var i,s
const n=t.input.querySelector('option[value=""]')
if(t.is_select_tag){const o=[],r=t.input.querySelectorAll("option:checked").length
function l(e,i,s){return e||(e=K('<option value="'+D(i)+'">'+D(s)+"</option>")),e!=n&&t.input.append(e),o.push(e),(e!=n||r>0||"multi"==t.settings.mode)&&(e.selected=!0),e}t.input.querySelectorAll("option:checked").forEach(e=>{e.selected=!1}),0==t.items.length&&"single"==t.settings.mode?l(n,"",""):t.items.forEach(e=>{if(i=t.options[e],s=i[t.settings.labelField]||"",o.includes(i.$option)){l(t.input.querySelector(`option[value="${M(e)}"]:not(:checked)`),e,s)}else i.$option=l(i.$option,e,s)})}else t.input.value=t.getValue()
t.isSetup&&(e.silent||t.trigger("change",t.getValue()))}open(){var e=this
e.isLocked||e.isOpen||"multi"===e.settings.mode&&e.isFull()||(e.isOpen=!0,ie(e.focus_node,{"aria-expanded":"true"}),e.refreshState(),W(e.dropdown,{visibility:"hidden",display:"block"}),e.positionDropdown(),W(e.dropdown,{visibility:"visible",display:"block"}),e.focus(),e.trigger("dropdown_open",e.dropdown))}close(e=!0){var t=this,i=t.isOpen
e&&(t.setTextboxValue(),"single"===t.settings.mode&&t.items.length&&t.inputState()),t.isOpen=!1,ie(t.focus_node,{"aria-expanded":"false"}),W(t.dropdown,{display:"none"}),t.settings.hideSelected&&t.clearActiveOption(),t.refreshState(),i&&t.trigger("dropdown_close",t.dropdown)}positionDropdown(){if("body"===this.settings.dropdownParent){var e=this.control,t=e.getBoundingClientRect(),i=e.offsetHeight+t.top+window.scrollY,s=t.left+window.scrollX
W(this.dropdown,{width:t.width+"px",top:i+"px",left:s+"px"})}}clear(e){var t=this
if(t.items.length){var i=t.controlChildren()
B(i,e=>{t.removeItem(e,!0)}),t.inputState(),e||t.updateOriginalInput(),t.trigger("clear")}}insertAtCaret(e){const t=this,i=t.caretPos,s=t.control
s.insertBefore(e,s.children[i]||null),t.setCaret(i+1)}deleteSelection(e){var t,i,s,n,o,r=this
t=e&&8===e.keyCode?-1:1,i={start:(o=r.control_input).selectionStart||0,length:(o.selectionEnd||0)-(o.selectionStart||0)}
const l=[]
if(r.activeItems.length)n=ee(r.activeItems,t),s=te(n),t>0&&s++,B(r.activeItems,e=>l.push(e))
else if((r.isFocused||"single"===r.settings.mode)&&r.items.length){const e=r.controlChildren()
let s
t<0&&0===i.start&&0===i.length?s=e[r.caretPos-1]:t>0&&i.start===r.inputValue().length&&(s=e[r.caretPos]),void 0!==s&&l.push(s)}if(!r.shouldDelete(l,e))return!1
for($(e,!0),void 0!==s&&r.setCaret(s);l.length;)r.removeItem(l.pop())
return r.inputState(),r.positionDropdown(),r.refreshOptions(!1),!0}shouldDelete(e,t){const i=e.map(e=>e.dataset.value)
return!(!i.length||"function"==typeof this.settings.onDelete&&!1===this.settings.onDelete.call(this,i,t))}advanceSelection(e,t){var i,s,n=this
n.rtl&&(e*=-1),n.inputValue().length||(R(oe,t)||R("shiftKey",t)?(s=(i=n.getLastActive(e))?i.classList.contains("active")?n.getAdjacent(i,e,"item"):i:e>0?n.control_input.nextElementSibling:n.control_input.previousElementSibling)&&(s.classList.contains("active")&&n.removeActiveItem(i),n.setActiveItemClass(s)):n.moveCaret(e))}moveCaret(e){}getLastActive(e){let t=this.control.querySelector(".last-active")
if(t)return t
var i=this.control.querySelectorAll(".active")
return i?ee(i,e):void 0}setCaret(e){this.caretPos=this.items.length}controlChildren(){return Array.from(this.control.querySelectorAll("[data-ts-item]"))}lock(){this.setLocked(!0)}unlock(){this.setLocked(!1)}setLocked(e=this.isReadOnly||this.isDisabled){this.isLocked=e,this.refreshState()}disable(){this.setDisabled(!0),this.close()}enable(){this.setDisabled(!1)}setDisabled(e){this.focus_node.tabIndex=e?-1:this.tabIndex,this.isDisabled=e,this.input.disabled=e,this.control_input.disabled=e,this.setLocked()}setReadOnly(e){this.isReadOnly=e,this.input.readOnly=e,this.control_input.readOnly=e,this.setLocked()}destroy(){var e=this,t=e.revertSettings
e.trigger("destroy"),e.off(),e.wrapper.remove(),e.dropdown.remove(),e.input.innerHTML=t.innerHTML,e.input.tabIndex=t.tabIndex,J(e.input,"tomselected","ts-hidden-accessible"),e._destroy(),delete e.input.tomselect}render(e,t){var i,s
const n=this
if("function"!=typeof this.settings.render[e])return null
if(!(s=n.settings.render[e].call(this,t,D)))return null
if(s=K(s),"option"===e||"option_create"===e?t[n.settings.disabledField]?ie(s,{"aria-disabled":"true"}):ie(s,{"data-selectable":""}):"optgroup"===e&&(i=t.group[n.settings.optgroupValueField],ie(s,{"data-group":i}),t.group[n.settings.disabledField]&&ie(s,{"data-disabled":""})),"option"===e||"item"===e){const i=N(t[n.settings.valueField])
ie(s,{"data-value":i}),"item"===e?(Q(s,n.settings.itemClass),ie(s,{"data-ts-item":""})):(Q(s,n.settings.optionClass),ie(s,{role:"option",id:t.$id}),t.$div=s,n.options[i]=t)}return s}_render(e,t){const i=this.render(e,t)
if(null==i)throw"HTMLElement expected"
return i}clearCache(){B(this.options,e=>{e.$div&&(e.$div.remove(),delete e.$div)})}uncacheValue(e){const t=this.getOption(e)
t&&t.remove()}canCreate(e){return this.settings.create&&e.length>0&&this.settings.createFilter.call(this,e)}hook(e,t,i){var s=this,n=s[t]
s[t]=function(){var t,o
return"after"===e&&(t=n.apply(s,arguments)),o=i.apply(s,arguments),"instead"===e?o:("before"===e&&(t=n.apply(s,arguments)),t)}}}return ce.define("change_listener",function(){q(this.input,"change",()=>{this.sync()})}),ce.define("checkbox_options",function(e){var t=this,i=t.onOptionSelect
t.settings.hideSelected=!1
const s=Object.assign({className:"tomselect-checkbox",checkedClassNames:void 0,uncheckedClassNames:void 0},e)
var n=function(e,t){t?(e.checked=!0,s.uncheckedClassNames&&e.classList.remove(...s.uncheckedClassNames),s.checkedClassNames&&e.classList.add(...s.checkedClassNames)):(e.checked=!1,s.checkedClassNames&&e.classList.remove(...s.checkedClassNames),s.uncheckedClassNames&&e.classList.add(...s.uncheckedClassNames))},o=function(e){setTimeout(()=>{var t=e.querySelector("input."+s.className)
t instanceof HTMLInputElement&&n(t,e.classList.contains("selected"))},1)}
t.hook("after","setupTemplates",()=>{var e=t.settings.render.option
t.settings.render.option=(i,o)=>{var r=K(e.call(t,i,o)),l=document.createElement("input")
s.className&&l.classList.add(s.className),l.addEventListener("click",function(e){$(e)}),l.type="checkbox"
const a=P(i[t.settings.valueField])
return n(l,!!(a&&t.items.indexOf(a)>-1)),r.prepend(l),r}}),t.on("item_remove",e=>{var i=t.getOption(e)
i&&(i.classList.remove("selected"),o(i))}),t.on("item_add",e=>{var i=t.getOption(e)
i&&o(i)}),t.hook("instead","onOptionSelect",(e,s)=>{if(s.classList.contains("selected"))return s.classList.remove("selected"),t.removeItem(s.dataset.value),t.refreshOptions(),void $(e,!0)
i.call(t,e,s),o(s)})}),ce.define("clear_button",function(e){const t=this,i=Object.assign({className:"clear-button",title:"Clear All",role:"button",tabindex:0,html:e=>`<div class="${e.className}" title="${e.title}" role="${e.role}" tabindex="${e.tabindex}">&times;</div>`},e)
t.on("initialize",()=>{var e=K(i.html(i))
e.addEventListener("click",e=>{t.isLocked||(t.clear(),"single"===t.settings.mode&&t.settings.allowEmptyOption&&t.addItem(""),t.refreshOptions(!1),e.preventDefault(),e.stopPropagation())}),t.control.appendChild(e)})}),ce.define("drag_drop",function(){var e=this
if("multi"!==e.settings.mode)return
var t=e.lock,i=e.unlock
let s,n=!0
e.hook("after","setupTemplates",()=>{var t=e.settings.render.item
e.settings.render.item=(i,o)=>{const r=K(t.call(e,i,o))
ie(r,{draggable:"true"})
const l=e=>{e.preventDefault(),r.classList.add("ts-drag-over"),a(r,s)},a=(e,t)=>{var i,s,n
void 0!==t&&(((e,t)=>{do{var i
if(e==(t=null==(i=t)?void 0:i.previousElementSibling))return!0}while(t&&t.previousElementSibling)
return!1})(t,r)?(s=t,null==(n=(i=e).parentNode)||n.insertBefore(s,i.nextSibling)):((e,t)=>{var i
null==(i=e.parentNode)||i.insertBefore(t,e)})(e,t))}
return q(r,"mousedown",e=>{n||$(e),e.stopPropagation()}),q(r,"dragstart",e=>{s=r,setTimeout(()=>{r.classList.add("ts-dragging")},0)}),q(r,"dragenter",l),q(r,"dragover",l),q(r,"dragleave",()=>{r.classList.remove("ts-drag-over")}),q(r,"dragend",()=>{var t
document.querySelectorAll(".ts-drag-over").forEach(e=>e.classList.remove("ts-drag-over")),null==(t=s)||t.classList.remove("ts-dragging"),s=void 0
var i=[]
e.control.querySelectorAll("[data-value]").forEach(e=>{if(e.dataset.value){let t=e.dataset.value
t&&i.push(t)}}),e.setValue(i)}),r}}),e.hook("instead","lock",()=>(n=!1,t.call(e))),e.hook("instead","unlock",()=>(n=!0,i.call(e)))}),ce.define("dropdown_header",function(e){const t=this,i=Object.assign({title:"Untitled",headerClass:"dropdown-header",titleRowClass:"dropdown-header-title",labelClass:"dropdown-header-label",closeClass:"dropdown-header-close",html:e=>'<div class="'+e.headerClass+'"><div class="'+e.titleRowClass+'"><span class="'+e.labelClass+'">'+e.title+'</span><a class="'+e.closeClass+'">&times;</a></div></div>'},e)
t.on("initialize",()=>{var e=K(i.html(i)),s=e.querySelector("."+i.closeClass)
s&&s.addEventListener("click",e=>{$(e,!0),t.close()}),t.dropdown.insertBefore(e,t.dropdown.firstChild)})}),ce.define("caret_position",function(){var e=this
e.hook("instead","setCaret",t=>{"single"!==e.settings.mode&&e.control.contains(e.control_input)?(t=Math.max(0,Math.min(e.items.length,t)))==e.caretPos||e.isPending||e.controlChildren().forEach((i,s)=>{s<t?e.control_input.insertAdjacentElement("beforebegin",i):e.control.appendChild(i)}):t=e.items.length,e.caretPos=t}),e.hook("instead","moveCaret",t=>{if(!e.isFocused)return
const i=e.getLastActive(t)
if(i){const s=te(i)
e.setCaret(t>0?s+1:s),e.setActiveItem(),J(i,"last-active")}else e.setCaret(e.caretPos+t)})}),ce.define("dropdown_input",function(){const e=this
e.settings.shouldOpen=!0,e.hook("before","setup",()=>{var t
e.focus_node=e.control,Q(e.control_input,"dropdown-input")
const i=K('<div class="dropdown-input-wrap">')
i.append(e.control_input),e.dropdown.insertBefore(i,e.dropdown.firstChild)
const s=K('<input class="items-placeholder" tabindex="-1" />')
s.placeholder=e.settings.placeholder||"",e.control.append(s)
const n=null==(t=e.input)?void 0:t.getAttribute("aria-label")
n&&s.setAttribute("aria-label",n)}),e.on("initialize",()=>{e.control_input.addEventListener("keydown",t=>{switch(t.keyCode){case 27:return e.isOpen&&($(t,!0),e.close()),void e.clearActiveItems()
case 9:e.focus_node.tabIndex=-1}return e.onKeyDown.call(e,t)}),e.on("blur",()=>{e.focus_node.tabIndex=e.isDisabled?-1:e.tabIndex}),e.on("dropdown_open",()=>{e.control_input.focus()})
const t=e.onBlur
e.hook("instead","onBlur",i=>{if(!i||i.relatedTarget!=e.control_input)return t.call(e)}),q(e.control_input,"blur",()=>e.onBlur()),e.hook("before","close",()=>{e.isOpen&&e.focus_node.focus({preventScroll:!0})})})}),ce.define("input_autogrow",function(){var e=this
e.on("initialize",()=>{var t=document.createElement("span"),i=e.control_input
t.style.cssText="position:absolute; top:-99999px; left:-99999px; width:auto; padding:0; white-space:pre; ",e.wrapper.appendChild(t)
for(const e of["letterSpacing","fontSize","fontFamily","fontWeight","textTransform"])t.style[e]=i.style[e]
var s=()=>{t.textContent=i.value,i.style.width=t.clientWidth+"px"}
s(),e.on("update item_add item_remove",s),q(i,"input",s),q(i,"keyup",s),q(i,"blur",s),q(i,"update",s)})}),ce.define("no_backspace_delete",function(){var e=this,t=e.deleteSelection
this.hook("instead","deleteSelection",i=>!!e.activeItems.length&&t.call(e,i))}),ce.define("no_active_items",function(){this.hook("instead","setActiveItem",()=>{}),this.hook("instead","selectAll",()=>{})}),ce.define("optgroup_columns",function(){var e=this,t=e.onKeyDown
e.hook("instead","onKeyDown",i=>{var s,n,o,r
if(!e.isOpen||37!==i.keyCode&&39!==i.keyCode)return t.call(e,i)
e.ignoreHover=!0,r=Z(e.activeOption,"[data-group]"),s=te(e.activeOption,"[data-selectable]"),r&&(r=37===i.keyCode?r.previousSibling:r.nextSibling)&&(n=(o=r.querySelectorAll("[data-selectable]"))[Math.min(o.length-1,s)])&&e.setActiveOption(n)})}),ce.define("remove_button",function(e){const t=this,i=Object.assign({label:"×",title:"Remove",className:"remove",tabindex:-1,role:"button",html:e=>{var t
const i=document.createElement("div")
return i.className=e.className||"",i.title=e.title||"",i.setAttribute("role",e.role||"button"),i.tabIndex=null!=(t=e.tabindex)?t:-1,i.textContent=e.label||"",i}},e)
t.hook("after","setupTemplates",()=>{var e=t.settings.render.item
t.settings.render.item=(s,n)=>{var o=K(e.call(t,s,n)),r=K(i.html(i))
return o.appendChild(r),q(r,"mousedown",e=>{$(e,!0)}),q(r,"click",e=>{t.isLocked||($(e,!0),t.isLocked||t.shouldDelete([o],e)&&(t.removeItem(o),t.refreshOptions(!1),t.inputState()))}),o}})}),ce.define("restore_on_backspace",function(e){const t=this,i=Object.assign({text:e=>e[t.settings.labelField]},e)
t.on("item_remove",function(e){if(t.isFocused&&""===t.control_input.value.trim()){var s=t.options[e]
s&&t.setTextboxValue(i.text.call(t,s))}})}),ce.define("virtual_scroll",function(){const e=this,t=e.canLoad,i=e.clearActiveOption,s=e.loadCallback
var n,o,r,l={},a=!1,c=[],d=!1,u=[],p=[]
if(e.settings.shouldLoadMore||(e.settings.shouldLoadMore=()=>{if(n.clientHeight/(n.scrollHeight-n.scrollTop)>.9)return!0
if(e.activeOption){var t=e.selectable()
if(Array.from(t).indexOf(e.activeOption)>=t.length-2)return!0}return!1}),!e.settings.firstUrl)throw"virtual_scroll plugin requires a firstUrl() method"
e.settings.sortField=[{field:"$order"},{field:"$score"}]
const h=t=>!(null!==e.settings.maxOptions&&"number"==typeof e.settings.maxOptions&&n.children.length>=e.settings.maxOptions)&&!(!(t in l)||!l[t]),g=(t,i)=>e.items.indexOf(i)>=0||c.indexOf(i)>=0
e.setNextUrl=(e,t)=>{l[e]=t},e.getUrl=t=>{if(t in l){const e=l[t]
return l[t]=!1,e}return e.clearPagination(),e.settings.firstUrl.call(e,t)},e.clearPagination=()=>{l={}},e.hook("instead","clearActiveOption",()=>{if(!a)return i.call(e)}),e.hook("instead","canLoad",i=>i in l?h(i):t.call(e,i)),e.hook("instead","loadCallback",(t,i)=>{if(a){if(o){const i=t[0]
void 0!==i&&(o.dataset.value=i[e.settings.valueField])}}else{const t=""!==e.lastValue?(t,i)=>e.items.indexOf(i)>=0||p.indexOf(i)>=0:g
e.clearOptions(t)}s.call(e,t,i),a||d||(d=!0,""===e.lastValue&&(c=Object.keys(e.options),r=l[""],u=Object.values(e.options))),a=!1}),e.hook("before","refreshOptions",()=>{e.activeOption&&"option"!==e.activeOption.getAttribute("role")&&e.setActiveOption(e.activeOption.previousElementSibling)}),e.hook("after","refreshOptions",()=>{const t=e.lastValue
var i
h(t)?(i=e.render("loading_more",{query:t}))&&(i.setAttribute("data-selectable",""),o=i):t in l&&!n.querySelector(".no-results")&&(i=e.render("no_more_results",{query:t})),i&&(Q(i,e.settings.optionClass),n.append(i))})
const f=()=>{d&&(e.addOptions(u),e.clearOptions(g),r&&(l[""]=r))}
e.on("type",t=>{""===t&&(f(),e.refreshOptions(!1))}),e.on("dropdown_close",f),e.on("initialize",()=>{p=Object.keys(e.options),c=Object.keys(e.options),n=e.dropdown_content,e.settings.render=Object.assign({},{loading_more:()=>'<div class="loading-more-results">Loading more results ... </div>',no_more_results:()=>'<div class="no-more-results">No more results</div>'},e.settings.render),n.addEventListener("scroll",()=>{e.settings.shouldLoadMore.call(e)&&h(e.lastValue)&&(a||(a=!0,e.load.call(e,e.lastValue)))})})}),ce})
var tomSelect=function(e,t){return new TomSelect(e,t)}
//# sourceMappingURL=tom-select.complete.min.js.map
