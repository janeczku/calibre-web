"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Link = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/* !
 * (c) Copyright 2025 Palantir Technologies Inc. All rights reserved.
 */
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const common_1 = require("../../common");
/**
 * Link component.
 *
 * @see https://blueprintjs.com/docs/#core/components/link
 */
exports.Link = (0, react_1.forwardRef)(({ children, className, underline = "always", color = common_1.Intent.PRIMARY, ...htmlProps }, ref) => {
    const classes = (0, classnames_1.default)(common_1.Classes.LINK, {
        [common_1.Classes.LINK_UNDERLINE_ALWAYS]: underline === "always",
        [common_1.Classes.LINK_UNDERLINE_HOVER]: underline === "hover",
        [common_1.Classes.LINK_UNDERLINE_NONE]: underline === "none",
        [common_1.Classes.LINK_COLOR_INHERIT]: color === "inherit",
    }, color !== "inherit" ? common_1.Classes.intentClass(color) : undefined, className);
    return ((0, jsx_runtime_1.jsx)("a", { ...htmlProps, className: classes, ref: ref, children: children }));
});
exports.Link.displayName = `${common_1.DISPLAYNAME_PREFIX}.Link`;
//# sourceMappingURL=link.js.map