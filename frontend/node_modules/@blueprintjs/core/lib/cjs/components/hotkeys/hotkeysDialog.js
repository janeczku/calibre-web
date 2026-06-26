"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.HotkeysDialog = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2021 Palantir Technologies, Inc. All rights reserved.
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const common_1 = require("../../common");
const dialog_1 = require("../dialog/dialog");
const dialogBody_1 = require("../dialog/dialogBody");
const hotkey_1 = require("./hotkey");
const hotkeys_1 = require("./hotkeys");
const HotkeysDialog = ({ globalGroupName = "Global", hotkeys, ...props }) => {
    return ((0, jsx_runtime_1.jsx)(dialog_1.Dialog, { ...props, className: (0, classnames_1.default)(common_1.Classes.HOTKEY_DIALOG, props.className), children: (0, jsx_runtime_1.jsx)(dialogBody_1.DialogBody, { children: (0, jsx_runtime_1.jsx)(hotkeys_1.Hotkeys, { children: hotkeys.map((hotkey, index) => ((0, jsx_runtime_1.jsx)(hotkey_1.Hotkey, { ...hotkey, group: hotkey.global === true && hotkey.group == null ? globalGroupName : hotkey.group }, index))) }) }) }));
};
exports.HotkeysDialog = HotkeysDialog;
//# sourceMappingURL=hotkeysDialog.js.map