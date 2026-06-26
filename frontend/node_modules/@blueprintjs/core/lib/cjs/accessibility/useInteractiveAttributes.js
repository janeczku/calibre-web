"use strict";
/* !
 * (c) Copyright 2024 Palantir Technologies Inc. All rights reserved.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.useInteractiveAttributes = useInteractiveAttributes;
const react_1 = require("react");
const common_1 = require("../common");
const DEFAULT_OPTIONS = { defaultTabIndex: undefined, disabledTabIndex: -1 };
function useInteractiveAttributes(interactive, props, ref, options = DEFAULT_OPTIONS) {
    const { defaultTabIndex, disabledTabIndex } = options;
    const { active, onClick, onFocus, onKeyDown, onKeyUp, onBlur, tabIndex = defaultTabIndex } = props;
    // the current key being pressed
    const [currentKeyPressed, setCurrentKeyPressed] = (0, react_1.useState)();
    // whether the button is in "active" state
    const [isActive, setIsActive] = (0, react_1.useState)(false);
    // our local ref for the interactive element, merged with the consumer's own ref in this hook's return value
    const elementRef = (0, react_1.useRef)(null);
    const handleBlur = (0, react_1.useCallback)((e) => {
        if (isActive) {
            setIsActive(false);
        }
        onBlur?.(e);
    }, [isActive, onBlur]);
    const handleKeyDown = (0, react_1.useCallback)((e) => {
        if (common_1.Utils.isKeyboardClick(e)) {
            e.preventDefault();
            if (e.key !== currentKeyPressed) {
                setIsActive(true);
            }
        }
        setCurrentKeyPressed(e.key);
        onKeyDown?.(e);
    }, [currentKeyPressed, onKeyDown]);
    const handleKeyUp = (0, react_1.useCallback)((e) => {
        if (common_1.Utils.isKeyboardClick(e)) {
            setIsActive(false);
            elementRef.current?.click();
        }
        setCurrentKeyPressed(undefined);
        onKeyUp?.(e);
    }, [onKeyUp, elementRef]);
    const resolvedActive = interactive && (active || isActive);
    return [
        resolvedActive,
        {
            onBlur: handleBlur,
            onClick: interactive ? onClick : undefined,
            onFocus: interactive ? onFocus : undefined,
            onKeyDown: handleKeyDown,
            onKeyUp: handleKeyUp,
            ref: (0, common_1.mergeRefs)(elementRef, ref),
            tabIndex: interactive ? tabIndex : disabledTabIndex,
        },
    ];
}
//# sourceMappingURL=useInteractiveAttributes.js.map