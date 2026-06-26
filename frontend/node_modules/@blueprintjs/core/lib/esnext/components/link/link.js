import { jsx as _jsx } from "react/jsx-runtime";
/* !
 * (c) Copyright 2025 Palantir Technologies Inc. All rights reserved.
 */
import classNames from "classnames";
import { forwardRef } from "react";
import { Classes, DISPLAYNAME_PREFIX, Intent } from "../../common";
/**
 * Link component.
 *
 * @see https://blueprintjs.com/docs/#core/components/link
 */
export const Link = forwardRef(({ children, className, underline = "always", color = Intent.PRIMARY, ...htmlProps }, ref) => {
    const classes = classNames(Classes.LINK, {
        [Classes.LINK_UNDERLINE_ALWAYS]: underline === "always",
        [Classes.LINK_UNDERLINE_HOVER]: underline === "hover",
        [Classes.LINK_UNDERLINE_NONE]: underline === "none",
        [Classes.LINK_COLOR_INHERIT]: color === "inherit",
    }, color !== "inherit" ? Classes.intentClass(color) : undefined, className);
    return (_jsx("a", { ...htmlProps, className: classes, ref: ref, children: children }));
});
Link.displayName = `${DISPLAYNAME_PREFIX}.Link`;
//# sourceMappingURL=link.js.map