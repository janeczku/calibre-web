"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Section = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
const card_1 = require("../card/card");
const collapse_1 = require("../collapse/collapse");
const html_1 = require("../html/html");
const icon_1 = require("../icon/icon");
/**
 * Section component.
 *
 * @see https://blueprintjs.com/docs/#core/components/section
 */
exports.Section = (0, react_1.forwardRef)((props, ref) => {
    const { children, className, collapseProps, collapsible, compact = false, elevation = common_1.Elevation.ZERO, icon, rightElement, subtitle, title, titleRenderer = html_1.H6, ...htmlProps } = props;
    // Determine whether to use controlled or uncontrolled state.
    const isControlled = collapseProps?.isOpen != null;
    // The initial useState value is negated in order to conform to the `isCollapsed` expectation.
    const [isCollapsedUncontrolled, setIsCollapsed] = (0, react_1.useState)(!(collapseProps?.defaultIsOpen ?? true));
    const isCollapsed = isControlled ? !collapseProps?.isOpen : isCollapsedUncontrolled;
    const toggleIsCollapsed = (0, react_1.useCallback)(() => {
        if (isControlled) {
            collapseProps?.onToggle?.();
        }
        else {
            setIsCollapsed(!isCollapsed);
        }
    }, [collapseProps, isCollapsed, isControlled]);
    const isHeaderRightContainerVisible = rightElement != null || collapsible;
    const sectionId = (0, utils_1.uniqueId)("section");
    const sectionTitleId = title ? (0, utils_1.uniqueId)("section-title") : undefined;
    return ((0, jsx_runtime_1.jsxs)(card_1.Card, { className: (0, classnames_1.default)(className, common_1.Classes.SECTION, {
            [common_1.Classes.COMPACT]: compact,
            [common_1.Classes.SECTION_COLLAPSED]: (collapsible && isCollapsed) || common_1.Utils.isReactNodeEmpty(children),
        }), elevation: elevation, ref: ref, "aria-labelledby": sectionTitleId, ...htmlProps, id: sectionId, children: [title && (
            // keyboard interaction handled by nested button element
            // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
            (0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.SECTION_HEADER, {
                    [common_1.Classes.INTERACTIVE]: collapsible,
                }), onClick: collapsible ? toggleIsCollapsed : undefined, children: [(0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.SECTION_HEADER_LEFT, children: [icon && (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon, "aria-hidden": true, tabIndex: -1, className: common_1.Classes.TEXT_MUTED }), (0, jsx_runtime_1.jsxs)("div", { children: [(0, react_1.createElement)(titleRenderer, { className: common_1.Classes.SECTION_HEADER_TITLE, id: sectionTitleId }, title), subtitle && ((0, jsx_runtime_1.jsx)("div", { className: (0, classnames_1.default)(common_1.Classes.TEXT_MUTED, common_1.Classes.SECTION_HEADER_SUB_TITLE), children: subtitle }))] })] }), isHeaderRightContainerVisible && ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.SECTION_HEADER_RIGHT, children: [rightElement, collapsible && ((0, jsx_runtime_1.jsx)("span", { role: "button", tabIndex: 0, "aria-pressed": isCollapsed, "aria-expanded": isCollapsed, "aria-controls": sectionId, "aria-label": isCollapsed ? "expand section" : "collapse section", 
                                // no OnClick, click event triggers header below
                                onKeyDown: (0, utils_1.clickElementOnKeyPress)(["Enter", " "]), className: (0, classnames_1.default)(common_1.Classes.TEXT_MUTED, common_1.Classes.SECTION_HEADER_COLLAPSE_CARET), children: isCollapsed ? (0, jsx_runtime_1.jsx)(icons_1.ChevronDown, {}) : (0, jsx_runtime_1.jsx)(icons_1.ChevronUp, {}) }))] }))] })), collapsible ? ((0, jsx_runtime_1.jsx)(collapse_1.Collapse, { ...collapseProps, isOpen: !isCollapsed, children: children })) : (children)] }));
});
exports.Section.displayName = `${props_1.DISPLAYNAME_PREFIX}.Section`;
//# sourceMappingURL=section.js.map