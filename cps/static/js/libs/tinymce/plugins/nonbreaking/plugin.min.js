/**
 * Copyright (c) Tiny Technologies, Inc. All rights reserved.
 * Licensed under the LGPL or a commercial license.
 * For LGPL see License.txt in the project root for license information.
 * For commercial licenses see https://www.tiny.cloud/
 *
 * Version: 5.0.3 (2019-03-19)
 */
!function(){"use strict";var n=tinymce.util.Tools.resolve("tinymce.PluginManager"),t=function(n,e){var o,t=(o=n).plugins.visualchars&&o.plugins.visualchars.isEnabled()?'<span class="mce-nbsp">&nbsp;</span>':"&nbsp;";n.insertContent(function(n,e){for(var o="",t=0;t<e;t++)o+=n;return o}(t,e)),n.dom.setAttrib(n.dom.select("span.mce-nbsp"),"data-mce-bogus","1")},e=function(n){n.addCommand("mceNonBreaking",function(){t(n,1)})},i=tinymce.util.Tools.resolve("tinymce.util.VK"),a=function(n){var e=n.getParam("nonbreaking_force_tab",0);return"boolean"==typeof e?!0===e?3:0:e},o=function(e){var o=a(e);0<o&&e.on("keydown",function(n){if(n.keyCode===i.TAB&&!n.isDefaultPrevented()){if(n.shiftKey)return;n.preventDefault(),n.stopImmediatePropagation(),t(e,o)}})},r=function(n){n.ui.registry.addButton("nonbreaking",{icon:"non-breaking",tooltip:"Nonbreaking space",onAction:function(){return n.execCommand("mceNonBreaking")}}),n.ui.registry.addMenuItem("nonbreaking",{icon:"non-breaking",text:"Nonbreaking space",onAction:function(){return n.execCommand("mceNonBreaking")}})};n.add("nonbreaking",function(n){e(n),r(n),o(n)}),function c(){}}();