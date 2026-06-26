"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ResizableInput = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
/* !
 * (c) Copyright 2022 Palantir Technologies Inc. All rights reserved.
 */
const react_1 = require("react");
const common_1 = require("../../common");
exports.ResizableInput = (0, react_1.forwardRef)(function ResizableInput(props, ref) {
    const [content, setContent] = (0, react_1.useState)("");
    const [width, setWidth] = (0, react_1.useState)(0);
    const span = (0, react_1.useRef)(null);
    (0, react_1.useEffect)(() => {
        if (span.current != null) {
            setWidth(span.current.offsetWidth);
        }
    }, [content]);
    const { onChange, style, ...otherProps } = props;
    const handleInputChange = evt => {
        onChange?.(evt);
        setContent(evt?.target?.value ?? "");
    };
    return ((0, jsx_runtime_1.jsxs)(jsx_runtime_1.Fragment, { children: [(0, jsx_runtime_1.jsx)("span", { ref: span, className: common_1.Classes.RESIZABLE_INPUT_SPAN, "aria-hidden": true, children: content.replace(/ /g, "\u00a0") }), (0, jsx_runtime_1.jsx)("input", { ...otherProps, type: "text", style: { ...style, width }, onChange: handleInputChange, ref: ref })] }));
});
exports.ResizableInput.displayName = `${common_1.DISPLAYNAME_PREFIX}.ResizableInput`;
//# sourceMappingURL=resizableInput.js.map