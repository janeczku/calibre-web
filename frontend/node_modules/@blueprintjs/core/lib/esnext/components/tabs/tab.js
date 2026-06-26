import { jsx as _jsx } from "react/jsx-runtime";
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
import classNames from "classnames";
import { AbstractPureComponent, Classes } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { isFunction } from "../../common/utils";
/**
 * Tab component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tabs.tab
 */
export class Tab extends AbstractPureComponent {
    static defaultProps = {
        disabled: false,
    };
    static displayName = `${DISPLAYNAME_PREFIX}.Tab`;
    // this component is never rendered directly; see Tabs#renderTabPanel()
    /* istanbul ignore next */
    render() {
        const { className, panel } = this.props;
        return (_jsx("div", { className: classNames(Classes.TAB_PANEL, className), role: "tablist", children: isFunction(panel) ? panel({ tabPanelId: "", tabTitleId: "" }) : panel }));
    }
}
//# sourceMappingURL=tab.js.map