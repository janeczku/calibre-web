"use strict";
/*
 * Copyright 2017 Palantir Technologies, Inc. All rights reserved.
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.Text = void 0;
const tslib_1 = require("tslib");
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const useIsomorphicLayoutEffect_1 = require("../../hooks/useIsomorphicLayoutEffect");
/**
 * Text component.
 *
 * @see https://blueprintjs.com/docs/#core/components/text
 */
exports.Text = (0, react_1.forwardRef)(({ children, tagName = "div", title, className, ellipsize = false, ...htmlProps }, forwardedRef) => {
    const contentMeasuringRef = (0, react_1.useRef)();
    const textRef = (0, react_1.useMemo)(() => (0, common_1.mergeRefs)(contentMeasuringRef, forwardedRef), [forwardedRef]);
    const [textContent, setTextContent] = (0, react_1.useState)("");
    const [isContentOverflowing, setIsContentOverflowing] = (0, react_1.useState)();
    // try to be conservative about running this effect, since querying scrollWidth causes the browser to reflow / recalculate styles,
    // which can be very expensive for long lists (for example, in long Menus)
    (0, useIsomorphicLayoutEffect_1.useIsomorphicLayoutEffect)(() => {
        if (contentMeasuringRef.current?.textContent != null) {
            setIsContentOverflowing(ellipsize && contentMeasuringRef.current.scrollWidth > contentMeasuringRef.current.clientWidth);
            setTextContent(contentMeasuringRef.current.textContent);
        }
    }, [contentMeasuringRef, children, ellipsize]);
    return (0, react_1.createElement)(tagName, {
        ...htmlProps,
        className: (0, classnames_1.default)({
            [common_1.Classes.TEXT_OVERFLOW_ELLIPSIS]: ellipsize,
        }, className),
        ref: textRef,
        title: title ?? (isContentOverflowing ? textContent : undefined),
    }, children);
});
exports.Text.displayName = `${props_1.DISPLAYNAME_PREFIX}.Text`;
//# sourceMappingURL=text.js.map