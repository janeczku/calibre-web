"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RadioGroup = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
/*
 * Copyright 2025 Palantir Technologies, Inc. All rights reserved.
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
const common_1 = require("../../common");
const Errors = tslib_1.__importStar(require("../../common/errors"));
const utils_1 = require("../../common/utils");
const useValidateProps_1 = require("../../hooks/useValidateProps");
const radioCard_1 = require("../control-card/radioCard");
const controls_1 = require("./controls");
/**
 * Radio group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/radio.radiogroup
 */
const RadioGroup = props => {
    const { children, className, disabled, inline, label, name, onChange, options, selectedValue, ...htmlProps } = props;
    // a unique name for this group, which can be overridden by `name` prop.
    const autoGroupName = (0, react_2.useMemo)(() => nextName(), []);
    const labelId = (0, react_2.useMemo)(() => (0, utils_1.uniqueId)("label"), []);
    (0, useValidateProps_1.useValidateProps)(() => {
        if (children != null && options != null) {
            console.warn(Errors.RADIOGROUP_WARN_CHILDREN_OPTIONS_MUTEX);
        }
    }, [children, options]);
    const getRadioProps = (0, react_2.useCallback)((optionProps) => {
        const { className: optionClassName, disabled: optionDisabled, value } = optionProps;
        return {
            checked: value === selectedValue,
            className: optionClassName,
            disabled: optionDisabled || disabled,
            inline,
            name: name == null ? autoGroupName : name,
            onChange,
            value,
        };
    }, [autoGroupName, disabled, inline, name, onChange, selectedValue]);
    const renderChildren = () => {
        return react_2.Children.map(children, child => {
            if ((0, utils_1.isElementOfType)(child, controls_1.Radio) || (0, utils_1.isElementOfType)(child, radioCard_1.RadioCard)) {
                return (0, react_2.cloneElement)(
                // Need this cast here to suppress a TS error caused by differing `ref` types for the Radio and
                // RadioCard components. We aren't injecting a ref, so we don't need to be strict about that
                // incompatibility.
                child, getRadioProps(child.props));
            }
            return child;
        });
    };
    const renderOptions = () => {
        return options?.map(option => ((0, react_1.createElement)(controls_1.Radio, { ...getRadioProps(option), key: option.value, labelElement: option.label || option.value })));
    };
    return ((0, jsx_runtime_1.jsxs)("div", { role: "radiogroup", "aria-labelledby": label ? labelId : undefined, ...(0, common_1.removeNonHTMLProps)(htmlProps), className: (0, classnames_1.default)(common_1.Classes.RADIO_GROUP, className), children: [label && ((0, jsx_runtime_1.jsx)("label", { className: common_1.Classes.LABEL, id: labelId, children: label })), Array.isArray(options) ? renderOptions() : renderChildren()] }));
};
exports.RadioGroup = RadioGroup;
exports.RadioGroup.displayName = `${common_1.DISPLAYNAME_PREFIX}.RadioGroup`;
let counter = 0;
function nextName() {
    return `${exports.RadioGroup.displayName}-${counter++}`;
}
//# sourceMappingURL=radioGroup.js.map