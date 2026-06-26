"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Tab = void 0;
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
const utils_1 = require("../../common/utils");
/**
 * Tab component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tabs.tab
 */
class Tab extends common_1.AbstractPureComponent {
    static defaultProps = {
        disabled: false,
    };
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.Tab`;
    // this component is never rendered directly; see Tabs#renderTabPanel()
    /* istanbul ignore next */
    render() {
        const { className, panel } = this.props;
        return ((0, jsx_runtime_1.jsx)("div", { className: (0, classnames_1.default)(common_1.Classes.TAB_PANEL, className), role: "tablist", children: (0, utils_1.isFunction)(panel) ? panel({ tabPanelId: "", tabTitleId: "" }) : panel }));
    }
}
exports.Tab = Tab;
//# sourceMappingURL=tab.js.map