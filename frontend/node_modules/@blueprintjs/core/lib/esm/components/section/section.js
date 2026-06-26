import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
import { createElement, forwardRef, useCallback, useState } from "react";
import { ChevronDown, ChevronUp } from "@blueprintjs/icons";
import { Classes, Elevation, Utils } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { clickElementOnKeyPress, uniqueId } from "../../common/utils";
import { Card } from "../card/card";
import { Collapse } from "../collapse/collapse";
import { H6 } from "../html/html";
import { Icon } from "../icon/icon";
/**
 * Section component.
 *
 * @see https://blueprintjs.com/docs/#core/components/section
 */
export const Section = forwardRef((props, ref) => {
    const { children, className, collapseProps, collapsible, compact = false, elevation = Elevation.ZERO, icon, rightElement, subtitle, title, titleRenderer = H6, ...htmlProps } = props;
    // Determine whether to use controlled or uncontrolled state.
    const isControlled = collapseProps?.isOpen != null;
    // The initial useState value is negated in order to conform to the `isCollapsed` expectation.
    const [isCollapsedUncontrolled, setIsCollapsed] = useState(!(collapseProps?.defaultIsOpen ?? true));
    const isCollapsed = isControlled ? !collapseProps?.isOpen : isCollapsedUncontrolled;
    const toggleIsCollapsed = useCallback(() => {
        if (isControlled) {
            collapseProps?.onToggle?.();
        }
        else {
            setIsCollapsed(!isCollapsed);
        }
    }, [collapseProps, isCollapsed, isControlled]);
    const isHeaderRightContainerVisible = rightElement != null || collapsible;
    const sectionId = uniqueId("section");
    const sectionTitleId = title ? uniqueId("section-title") : undefined;
    return (_jsxs(Card, { className: classNames(className, Classes.SECTION, {
            [Classes.COMPACT]: compact,
            [Classes.SECTION_COLLAPSED]: (collapsible && isCollapsed) || Utils.isReactNodeEmpty(children),
        }), elevation: elevation, ref: ref, "aria-labelledby": sectionTitleId, ...htmlProps, id: sectionId, children: [title && (
            // keyboard interaction handled by nested button element
            // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
            _jsxs("div", { className: classNames(Classes.SECTION_HEADER, {
                    [Classes.INTERACTIVE]: collapsible,
                }), onClick: collapsible ? toggleIsCollapsed : undefined, children: [_jsxs("div", { className: Classes.SECTION_HEADER_LEFT, children: [icon && _jsx(Icon, { icon: icon, "aria-hidden": true, tabIndex: -1, className: Classes.TEXT_MUTED }), _jsxs("div", { children: [createElement(titleRenderer, { className: Classes.SECTION_HEADER_TITLE, id: sectionTitleId }, title), subtitle && (_jsx("div", { className: classNames(Classes.TEXT_MUTED, Classes.SECTION_HEADER_SUB_TITLE), children: subtitle }))] })] }), isHeaderRightContainerVisible && (_jsxs("div", { className: Classes.SECTION_HEADER_RIGHT, children: [rightElement, collapsible && (_jsx("span", { role: "button", tabIndex: 0, "aria-pressed": isCollapsed, "aria-expanded": isCollapsed, "aria-controls": sectionId, "aria-label": isCollapsed ? "expand section" : "collapse section", 
                                // no OnClick, click event triggers header below
                                onKeyDown: clickElementOnKeyPress(["Enter", " "]), className: classNames(Classes.TEXT_MUTED, Classes.SECTION_HEADER_COLLAPSE_CARET), children: isCollapsed ? _jsx(ChevronDown, {}) : _jsx(ChevronUp, {}) }))] }))] })), collapsible ? (_jsx(Collapse, { ...collapseProps, isOpen: !isCollapsed, children: children })) : (children)] }));
});
Section.displayName = `${DISPLAYNAME_PREFIX}.Section`;
//# sourceMappingURL=section.js.map