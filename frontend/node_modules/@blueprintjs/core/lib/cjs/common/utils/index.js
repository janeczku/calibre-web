"use strict";
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRef = exports.setRef = exports.isDarkTheme = exports.isFunction = exports.throttleReactEventCallback = exports.throttleEvent = exports.throttle = exports.getFocusableElements = exports.getActiveElement = exports.elementIsTextInput = exports.elementIsOrContains = exports.clickElementOnKeyPress = void 0;
const tslib_1 = require("tslib");
tslib_1.__exportStar(require("./compareUtils"), exports);
var domUtils_1 = require("./domUtils");
Object.defineProperty(exports, "clickElementOnKeyPress", { enumerable: true, get: function () { return domUtils_1.clickElementOnKeyPress; } });
Object.defineProperty(exports, "elementIsOrContains", { enumerable: true, get: function () { return domUtils_1.elementIsOrContains; } });
Object.defineProperty(exports, "elementIsTextInput", { enumerable: true, get: function () { return domUtils_1.elementIsTextInput; } });
Object.defineProperty(exports, "getActiveElement", { enumerable: true, get: function () { return domUtils_1.getActiveElement; } });
Object.defineProperty(exports, "getFocusableElements", { enumerable: true, get: function () { return domUtils_1.getFocusableElements; } });
Object.defineProperty(exports, "throttle", { enumerable: true, get: function () { return domUtils_1.throttle; } });
Object.defineProperty(exports, "throttleEvent", { enumerable: true, get: function () { return domUtils_1.throttleEvent; } });
Object.defineProperty(exports, "throttleReactEventCallback", { enumerable: true, get: function () { return domUtils_1.throttleReactEventCallback; } });
var functionUtils_1 = require("./functionUtils");
Object.defineProperty(exports, "isFunction", { enumerable: true, get: function () { return functionUtils_1.isFunction; } });
tslib_1.__exportStar(require("./jsUtils"), exports);
tslib_1.__exportStar(require("./reactUtils"), exports);
tslib_1.__exportStar(require("./keyboardUtils"), exports);
var isDarkTheme_1 = require("./isDarkTheme");
Object.defineProperty(exports, "isDarkTheme", { enumerable: true, get: function () { return isDarkTheme_1.isDarkTheme; } });
// ref utils used to live in this folder, but got refactored and moved elsewhere.
// we keep this export here for backwards compatibility
var refs_1 = require("../refs");
Object.defineProperty(exports, "setRef", { enumerable: true, get: function () { return refs_1.setRef; } });
Object.defineProperty(exports, "getRef", { enumerable: true, get: function () { return refs_1.getRef; } });
//# sourceMappingURL=index.js.map