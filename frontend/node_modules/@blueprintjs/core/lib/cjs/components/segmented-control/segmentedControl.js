"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SegmentedControl = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
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
const react_2 = require("react");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const buttons_1 = require("../button/buttons");
/**
 * Segmented control component.
 *
 * @see https://blueprintjs.com/docs/#core/components/segmented-control
 */
exports.SegmentedControl = (0, react_2.forwardRef)((props, ref) => {
    const { className, defaultValue, disabled, fill, inline, intent = common_1.Intent.NONE, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large, onValueChange, options, role = "radiogroup", size = "medium", 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    small, value: controlledValue, ...htmlProps } = props;
    const [localValue, setLocalValue] = (0, react_2.useState)(defaultValue);
    const selectedValue = controlledValue ?? localValue;
    const outerRef = (0, react_2.useRef)(null);
    const handleOptionClick = (0, react_2.useCallback)((newSelectedValue, targetElement) => {
        setLocalValue(newSelectedValue);
        onValueChange?.(newSelectedValue, targetElement);
    }, [onValueChange]);
    const handleKeyDown = (0, react_2.useCallback)((e) => {
        if (role === "radiogroup" || role === "menu") {
            // in a `radiogroup`, arrow keys select next item, not tab key.
            const direction = common_1.Utils.getArrowKeyDirection(e, ["ArrowLeft", "ArrowUp"], ["ArrowRight", "ArrowDown"]);
            const outerElement = outerRef.current;
            if (direction === undefined || !outerElement)
                return;
            const focusedElement = common_1.Utils.getActiveElement(outerElement)?.closest("button");
            if (!focusedElement)
                return;
            // must rely on DOM state because we have no way of mapping `focusedElement` to a React.JSX.Element
            const enabledOptionElements = Array.from(outerElement.querySelectorAll("button:not(:disabled)"));
            const focusedIndex = enabledOptionElements.indexOf(focusedElement);
            if (focusedIndex < 0)
                return;
            e.preventDefault();
            // auto-wrapping at 0 and `length`
            const newIndex = (focusedIndex + direction + enabledOptionElements.length) % enabledOptionElements.length;
            const newOption = enabledOptionElements[newIndex];
            newOption.click();
            newOption.focus();
        }
    }, [outerRef, role]);
    const classes = (0, classnames_1.default)(common_1.Classes.SEGMENTED_CONTROL, className, {
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.INLINE]: inline,
    });
    const isAnySelected = options.some(option => selectedValue === option.value);
    const buttonRole = {
        /* eslint-disable sort-keys */
        radiogroup: "radio",
        menu: "menuitemradio",
        group: undefined,
        toolbar: undefined,
        /* eslint-enable sort-keys */
    }[role];
    return ((0, jsx_runtime_1.jsx)("div", { ...(0, props_1.removeNonHTMLProps)(htmlProps), role: role, onKeyDown: handleKeyDown, className: classes, ref: (0, common_1.mergeRefs)(ref, outerRef), children: options.map((option, index) => {
            const isSelected = selectedValue === option.value;
            return ((0, react_1.createElement)(SegmentedControlOption, { ...option, disabled: option.disabled || disabled, intent: intent, isSelected: isSelected, key: option.value, 
                // eslint-disable-next-line @typescript-eslint/no-deprecated
                large: large, onClick: handleOptionClick, size: size, 
                // eslint-disable-next-line @typescript-eslint/no-deprecated
                small: small, role: buttonRole, ...(role === "radiogroup" || role === "menu"
                    ? {
                        "aria-checked": isSelected,
                        // "roving tabIndex" on a radiogroup: https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/#kbd_roving_tabindex
                        // `!isAnySelected` accounts for case where no value is currently selected
                        // (passed value/defaultValue is not one of the values of the passed options.)
                        // In this case, set first item to be tabbable even though it's unselected.
                        tabIndex: isSelected || (index === 0 && !isAnySelected) ? 0 : -1,
                    }
                    : {
                        "aria-pressed": isSelected,
                    }) }));
        }) }));
});
exports.SegmentedControl.displayName = `${props_1.DISPLAYNAME_PREFIX}.SegmentedControl`;
function SegmentedControlOption({ isSelected, label, onClick, value, ...buttonProps }) {
    const handleClick = (0, react_2.useCallback)((event) => onClick?.(value, event.currentTarget), [onClick, value]);
    return ((0, jsx_runtime_1.jsx)(buttons_1.Button, { ...buttonProps, onClick: handleClick, text: label ?? value, variant: !isSelected ? "minimal" : undefined }));
}
SegmentedControlOption.displayName = `${props_1.DISPLAYNAME_PREFIX}.SegmentedControlOption`;
//# sourceMappingURL=segmentedControl.js.map