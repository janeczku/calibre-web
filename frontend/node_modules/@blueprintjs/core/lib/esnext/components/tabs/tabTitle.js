import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { AbstractPureComponent, Classes, Intent } from "../../common";
import { DISPLAYNAME_PREFIX, removeNonHTMLProps } from "../../common/props";
import { Icon } from "../icon/icon";
import { Tag } from "../tag/tag";
export class TabTitle extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.TabTitle`;
    render() {
        const { className, children, disabled, id, parentId, selected, title, icon, tagContent, tagProps, ...htmlProps } = this.props;
        const intent = selected ? Intent.PRIMARY : Intent.NONE;
        const { tabPanelId, tabTitleId } = generateTabIds(parentId, id);
        return (
        // eslint-disable-next-line jsx-a11y/interactive-supports-focus, jsx-a11y/click-events-have-key-events
        _jsxs("div", { ...removeNonHTMLProps(htmlProps), "aria-controls": tabPanelId, "aria-disabled": disabled, "aria-expanded": selected, "aria-selected": selected, className: classNames(Classes.TAB, className), "data-tab-id": id, id: tabTitleId, onClick: disabled ? undefined : this.handleClick, role: "tab", tabIndex: disabled ? undefined : selected ? 0 : -1, children: [icon != null && _jsx(Icon, { icon: icon, intent: intent, className: Classes.TAB_ICON }), title, children, tagContent != null && (_jsx(Tag, { minimal: true, intent: intent, ...tagProps, className: classNames(Classes.TAB_TAG, tagProps?.className), children: tagContent }))] }));
    }
    handleClick = (e) => this.props.onClick(this.props.id, e);
}
export function generateTabIds(parentId, tabId) {
    return {
        tabPanelId: `${Classes.TAB_PANEL}_${parentId}_${tabId}`,
        tabTitleId: `${Classes.TAB}-title_${parentId}_${tabId}`,
    };
}
//# sourceMappingURL=tabTitle.js.map