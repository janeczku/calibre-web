"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TabTitle = void 0;
exports.generateTabIds = generateTabIds;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const icon_1 = require("../icon/icon");
const tag_1 = require("../tag/tag");
class TabTitle extends common_1.AbstractPureComponent {
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.TabTitle`;
    render() {
        const { className, children, disabled, id, parentId, selected, title, icon, tagContent, tagProps, ...htmlProps } = this.props;
        const intent = selected ? common_1.Intent.PRIMARY : common_1.Intent.NONE;
        const { tabPanelId, tabTitleId } = generateTabIds(parentId, id);
        return (
        // eslint-disable-next-line jsx-a11y/interactive-supports-focus, jsx-a11y/click-events-have-key-events
        (0, jsx_runtime_1.jsxs)("div", { ...(0, props_1.removeNonHTMLProps)(htmlProps), "aria-controls": tabPanelId, "aria-disabled": disabled, "aria-expanded": selected, "aria-selected": selected, className: (0, classnames_1.default)(common_1.Classes.TAB, className), "data-tab-id": id, id: tabTitleId, onClick: disabled ? undefined : this.handleClick, role: "tab", tabIndex: disabled ? undefined : selected ? 0 : -1, children: [icon != null && (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon, intent: intent, className: common_1.Classes.TAB_ICON }), title, children, tagContent != null && ((0, jsx_runtime_1.jsx)(tag_1.Tag, { minimal: true, intent: intent, ...tagProps, className: (0, classnames_1.default)(common_1.Classes.TAB_TAG, tagProps?.className), children: tagContent }))] }));
    }
    handleClick = (e) => this.props.onClick(this.props.id, e);
}
exports.TabTitle = TabTitle;
function generateTabIds(parentId, tabId) {
    return {
        tabPanelId: `${common_1.Classes.TAB_PANEL}_${parentId}_${tabId}`,
        tabTitleId: `${common_1.Classes.TAB}-title_${parentId}_${tabId}`,
    };
}
//# sourceMappingURL=tabTitle.js.map