"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Hotkeys = void 0;
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
const react_1 = require("react");
const common_1 = require("../../common");
const errors_1 = require("../../common/errors");
const utils_1 = require("../../common/utils");
const html_1 = require("../html/html");
const hotkey_1 = require("./hotkey");
/**
 * Hotkeys component used to display a list of hotkeys in the HotkeysDialog.
 * Should not be used by consumers directly.
 */
class Hotkeys extends common_1.AbstractPureComponent {
    static displayName = `${common_1.DISPLAYNAME_PREFIX}.Hotkeys`;
    static defaultProps = {
        tabIndex: 0,
    };
    render() {
        if (!(0, utils_1.isReactChildrenElementOrElements)(this.props.children)) {
            return null;
        }
        const hotkeys = react_1.Children.map(this.props.children, (child) => child.props);
        // sort by group label alphabetically, prioritize globals
        hotkeys.sort((a, b) => {
            if (a.global === b.global && a.group && b.group) {
                return a.group.localeCompare(b.group);
            }
            return a.global ? -1 : 1;
        });
        let lastGroup;
        const elems = [];
        for (const hotkey of hotkeys) {
            const groupLabel = hotkey.group;
            if (groupLabel !== lastGroup) {
                elems.push((0, jsx_runtime_1.jsx)(html_1.H4, { children: groupLabel }, `group-${elems.length}`));
                lastGroup = groupLabel;
            }
            elems.push((0, jsx_runtime_1.jsx)(hotkey_1.Hotkey, { ...hotkey }, elems.length));
        }
        const rootClasses = (0, classnames_1.default)(common_1.Classes.HOTKEY_COLUMN, this.props.className);
        return (0, jsx_runtime_1.jsx)("div", { className: rootClasses, children: elems });
    }
    validateProps(props) {
        if (!(0, utils_1.isReactChildrenElementOrElements)(props.children)) {
            return;
        }
        react_1.Children.forEach(props.children, (child) => {
            if (!(0, utils_1.isElementOfType)(child, hotkey_1.Hotkey)) {
                throw new Error(errors_1.HOTKEYS_HOTKEY_CHILDREN);
            }
        });
    }
}
exports.Hotkeys = Hotkeys;
//# sourceMappingURL=hotkeys.js.map