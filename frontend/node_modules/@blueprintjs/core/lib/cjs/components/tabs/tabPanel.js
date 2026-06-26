"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TabPanel = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2024 Palantir Technologies, Inc. All rights reserved.
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
const tabTitle_1 = require("./tabTitle");
/**
 * Wraps the passed `panel`.
 */
class TabPanel extends common_1.AbstractPureComponent {
    render() {
        const { className, id, parentId, selectedTabId, panel, renderActiveTabPanelOnly } = this.props;
        const isSelected = id === selectedTabId;
        if (panel === undefined || (renderActiveTabPanelOnly && !isSelected)) {
            return undefined;
        }
        const { tabTitleId, tabPanelId } = (0, tabTitle_1.generateTabIds)(parentId, id);
        return ((0, jsx_runtime_1.jsx)("div", { "aria-labelledby": tabTitleId, "aria-hidden": !isSelected, className: (0, classnames_1.default)(common_1.Classes.TAB_PANEL, className), id: tabPanelId, role: "tabpanel", children: common_1.Utils.isFunction(panel) ? panel({ tabPanelId, tabTitleId }) : panel }));
    }
}
exports.TabPanel = TabPanel;
//# sourceMappingURL=tabPanel.js.map