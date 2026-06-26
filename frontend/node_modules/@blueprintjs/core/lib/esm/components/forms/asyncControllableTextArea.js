import { jsx as _jsx } from "react/jsx-runtime";
/* !
 * (c) Copyright 2023 Palantir Technologies Inc. All rights reserved.
 */
import { forwardRef } from "react";
import { DISPLAYNAME_PREFIX } from "../../common";
import { useAsyncControllableValue } from "../../hooks/useAsyncControllableValue";
/**
 * A wrapper around the low-level <textarea> component which works around a React bug
 * the same way <AsyncControllableInput> does.
 */
export const AsyncControllableTextArea = forwardRef(function AsyncControllableTextArea(props, ref) {
    const { value: parentValue, onChange: parentOnChange, onCompositionStart: parentOnCompositionStart, onCompositionEnd: parentOnCompositionEnd, ...restProps } = props;
    const { value, onChange, onCompositionStart, onCompositionEnd } = useAsyncControllableValue({
        onChange: parentOnChange,
        onCompositionEnd: parentOnCompositionEnd,
        onCompositionStart: parentOnCompositionStart,
        value: parentValue,
    });
    return (_jsx("textarea", { ...restProps, value: value, onChange: onChange, onCompositionStart: onCompositionStart, onCompositionEnd: onCompositionEnd, ref: ref }));
});
AsyncControllableTextArea.displayName = `${DISPLAYNAME_PREFIX}.AsyncControllableTextArea`;
//# sourceMappingURL=asyncControllableTextArea.js.map