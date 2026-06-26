"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Hotkey = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
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
const keyComboTag_1 = require("./keyComboTag");
/**
 * Hotkey component used to display a hotkey in the HotkeysDialog.
 * Should not be used by consumers directly.
 */
class Hotkey extends common_1.AbstractPureComponent {
    static displayName = `${common_1.DISPLAYNAME_PREFIX}.Hotkey`;
    static defaultProps = {
        allowInInput: false,
        disabled: false,
        global: false,
        preventDefault: false,
        stopPropagation: false,
    };
    render() {
        const { label, className, ...spreadableProps } = this.props;
        const rootClasses = (0, classnames_1.default)(common_1.Classes.HOTKEY, className);
        return ((0, jsx_runtime_1.jsxs)("div", { className: rootClasses, children: [(0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.HOTKEY_LABEL, children: label }), (0, jsx_runtime_1.jsx)(keyComboTag_1.KeyComboTag, { ...spreadableProps })] }));
    }
    validateProps(props) {
        if (props.global !== true && props.group == null) {
            console.error("non-global Hotkeys must define a group");
        }
    }
}
exports.Hotkey = Hotkey;
//# sourceMappingURL=hotkey.js.map