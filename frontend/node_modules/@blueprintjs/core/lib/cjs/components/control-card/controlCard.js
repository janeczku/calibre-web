"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ControlCard = void 0;
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
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const card_1 = require("../card/card");
const controls_1 = require("../forms/controls");
const useCheckedControl_1 = require("./useCheckedControl");
/**
 * ControlCard component, used to render a {@link Card} with a form control.
 *
 * @internal
 */
exports.ControlCard = (0, react_1.forwardRef)((props, ref) => {
    const { alignIndicator = common_1.Alignment.END, checked: _checked, children, className, controlKind, defaultChecked: _defaultChecked, disabled, inputProps, inputRef, label, onChange: _onChange, showAsSelectedWhenChecked = true, value, ...cardProps } = props;
    const { checked, onChange } = (0, useCheckedControl_1.useCheckedControl)(props);
    // use a container element to achieve a good flex layout
    const labelElement = (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.CONTROL_CARD_LABEL, children: children ?? label });
    const controlProps = {
        alignIndicator,
        checked,
        disabled,
        inline: true,
        inputRef,
        labelElement,
        onChange,
        value,
        ...inputProps,
    };
    const classes = (0, classnames_1.default)(common_1.Classes.CONTROL_CARD, className, {
        [common_1.Classes.SELECTED]: showAsSelectedWhenChecked && checked,
    });
    return ((0, jsx_runtime_1.jsx)(card_1.Card, { interactive: !disabled, className: classes, ref: ref, ...cardProps, children: controlKind === "switch" ? ((0, jsx_runtime_1.jsx)(controls_1.Switch, { ...controlProps })) : controlKind === "checkbox" ? ((0, jsx_runtime_1.jsx)(controls_1.Checkbox, { ...controlProps })) : controlKind === "radio" ? ((0, jsx_runtime_1.jsx)(controls_1.Radio, { ...controlProps })) : (labelElement) }));
});
exports.ControlCard.displayName = `${props_1.DISPLAYNAME_PREFIX}.ControlCard`;
//# sourceMappingURL=controlCard.js.map