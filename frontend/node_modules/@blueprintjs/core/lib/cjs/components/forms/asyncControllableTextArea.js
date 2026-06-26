"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AsyncControllableTextArea = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
/* !
 * (c) Copyright 2023 Palantir Technologies Inc. All rights reserved.
 */
const react_1 = require("react");
const common_1 = require("../../common");
const useAsyncControllableValue_1 = require("../../hooks/useAsyncControllableValue");
/**
 * A wrapper around the low-level <textarea> component which works around a React bug
 * the same way <AsyncControllableInput> does.
 */
exports.AsyncControllableTextArea = (0, react_1.forwardRef)(function AsyncControllableTextArea(props, ref) {
    const { value: parentValue, onChange: parentOnChange, onCompositionStart: parentOnCompositionStart, onCompositionEnd: parentOnCompositionEnd, ...restProps } = props;
    const { value, onChange, onCompositionStart, onCompositionEnd } = (0, useAsyncControllableValue_1.useAsyncControllableValue)({
        onChange: parentOnChange,
        onCompositionEnd: parentOnCompositionEnd,
        onCompositionStart: parentOnCompositionStart,
        value: parentValue,
    });
    return ((0, jsx_runtime_1.jsx)("textarea", { ...restProps, value: value, onChange: onChange, onCompositionStart: onCompositionStart, onCompositionEnd: onCompositionEnd, ref: ref }));
});
exports.AsyncControllableTextArea.displayName = `${common_1.DISPLAYNAME_PREFIX}.AsyncControllableTextArea`;
//# sourceMappingURL=asyncControllableTextArea.js.map