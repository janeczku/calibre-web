/**
 * Copyright (c) Tiny Technologies, Inc. All rights reserved.
 * Licensed under the LGPL or a commercial license.
 * For LGPL see License.txt in the project root for license information.
 * For commercial licenses see https://www.tiny.cloud/
 *
 * Version: 5.0.3 (2019-03-19)
 */
!function(){"use strict";var n=tinymce.util.Tools.resolve("tinymce.PluginManager"),t=function(n){n.addCommand("mcePrint",function(){n.getWin().print()})},i=function(n){n.ui.registry.addButton("print",{icon:"print",tooltip:"Print",onAction:function(){return n.execCommand("mcePrint")}}),n.ui.registry.addMenuItem("print",{text:"Print...",icon:"print",onAction:function(){return n.execCommand("mcePrint")}})};n.add("print",function(n){t(n),i(n),n.addShortcut("Meta+P","","mcePrint")}),function r(){}}();