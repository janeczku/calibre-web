"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.HTMLSelect = void 0;
const tslib_1 = require("tslib");
const react_1 = require("react");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2018 Palantir Technologies, Inc. All rights reserved.
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
const react_2 = require("react");
const icons_1 = require("@blueprintjs/icons");
const classes_1 = require("../../common/classes");
const props_1 = require("../../common/props");
// this component is simple enough that tests would be purely tautological.
/* istanbul ignore next */
/**
 * HTML select component
 *
 * @see https://blueprintjs.com/docs/#core/components/html-select
 */
exports.HTMLSelect = (0, react_2.forwardRef)((props, ref) => {
    const { className, children, disabled, fill, iconName = "double-caret-vertical", iconProps, large, minimal, options = [], value, ...htmlProps } = props;
    const classes = (0, classnames_1.default)(classes_1.HTML_SELECT, {
        [classes_1.DISABLED]: disabled,
        [classes_1.FILL]: fill,
        [classes_1.LARGE]: large,
        [classes_1.MINIMAL]: minimal,
    }, className);
    const iconTitle = "Open dropdown";
    const endIcon = iconName === "double-caret-vertical" ? ((0, jsx_runtime_1.jsx)(icons_1.DoubleCaretVertical, { title: iconTitle, ...iconProps })) : ((0, jsx_runtime_1.jsx)(icons_1.CaretDown, { title: iconTitle, ...iconProps }));
    const optionChildren = options.map(option => {
        const optionProps = typeof option === "object" ? option : { value: option };
        return (0, react_1.createElement)("option", { ...optionProps, key: optionProps.value, children: optionProps.label || optionProps.value });
    });
    return ((0, jsx_runtime_1.jsxs)("div", { className: classes, children: [(0, jsx_runtime_1.jsxs)("select", { disabled: disabled, ref: ref, value: value, ...htmlProps, multiple: false, children: [optionChildren, children] }), endIcon] }));
});
exports.HTMLSelect.displayName = `${props_1.DISPLAYNAME_PREFIX}.HTMLSelect`;
//# sourceMappingURL=htmlSelect.js.map