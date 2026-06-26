"use strict";
/*
 * Copyright 2020 Palantir Technologies, Inc. All rights reserved.
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
exports.HotkeysTarget2 = exports.HotkeysTarget = exports.parseKeyCombo = exports.getKeyComboString = exports.getKeyCombo = exports.comboMatches = exports.KeyComboTag = exports.Hotkeys = exports.Hotkey = void 0;
var hotkey_1 = require("./hotkey");
Object.defineProperty(exports, "Hotkey", { enumerable: true, get: function () { return hotkey_1.Hotkey; } });
var hotkeys_1 = require("./hotkeys");
Object.defineProperty(exports, "Hotkeys", { enumerable: true, get: function () { return hotkeys_1.Hotkeys; } });
var keyComboTag_1 = require("./keyComboTag");
Object.defineProperty(exports, "KeyComboTag", { enumerable: true, get: function () { return keyComboTag_1.KeyComboTag; } });
var hotkeyParser_1 = require("./hotkeyParser");
Object.defineProperty(exports, "comboMatches", { enumerable: true, get: function () { return hotkeyParser_1.comboMatches; } });
Object.defineProperty(exports, "getKeyCombo", { enumerable: true, get: function () { return hotkeyParser_1.getKeyCombo; } });
Object.defineProperty(exports, "getKeyComboString", { enumerable: true, get: function () { return hotkeyParser_1.getKeyComboString; } });
Object.defineProperty(exports, "parseKeyCombo", { enumerable: true, get: function () { return hotkeyParser_1.parseKeyCombo; } });
var hotkeysTarget_1 = require("./hotkeysTarget");
Object.defineProperty(exports, "HotkeysTarget", { enumerable: true, get: function () { return hotkeysTarget_1.HotkeysTarget; } });
// eslint-disable-next-line @typescript-eslint/no-deprecated
Object.defineProperty(exports, "HotkeysTarget2", { enumerable: true, get: function () { return hotkeysTarget_1.HotkeysTarget2; } });
//# sourceMappingURL=index.js.map