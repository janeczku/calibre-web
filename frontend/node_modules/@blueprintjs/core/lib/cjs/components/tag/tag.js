"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Tag = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
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
const useInteractiveAttributes_1 = require("../../accessibility/useInteractiveAttributes");
const common_1 = require("../../common");
const utils_1 = require("../../common/utils");
const icon_1 = require("../icon/icon");
const text_1 = require("../text/text");
const tagRemoveButton_1 = require("./tagRemoveButton");
/**
 * Tag component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tag
 */
exports.Tag = (0, react_1.forwardRef)((props, ref) => {
    const { children, className, endIcon, fill = false, icon, intent, interactive, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large = false, minimal = false, multiline, onRemove, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    rightIcon, round = false, size = "medium", tabIndex = 0, htmlTitle, ...htmlProps } = props;
    const isRemovable = common_1.Utils.isFunction(onRemove);
    const isInteractive = interactive ?? htmlProps.onClick != null;
    const [active, interactiveProps] = (0, useInteractiveAttributes_1.useInteractiveAttributes)(isInteractive, props, ref, {
        defaultTabIndex: 0,
        disabledTabIndex: undefined,
    });
    const tagClasses = (0, classnames_1.default)(common_1.Classes.TAG, common_1.Classes.intentClass(intent), common_1.Classes.sizeClass(size, { large }), {
        [common_1.Classes.ACTIVE]: active,
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.INTERACTIVE]: isInteractive,
        [common_1.Classes.MINIMAL]: minimal,
        [common_1.Classes.ROUND]: round,
    }, className);
    return ((0, jsx_runtime_1.jsxs)("span", { ...(0, common_1.removeNonHTMLProps)(htmlProps), ...interactiveProps, className: tagClasses, role: isInteractive ? "button" : undefined, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon }), !(0, utils_1.isReactNodeEmpty)(children) && ((0, jsx_runtime_1.jsx)(text_1.Text, { className: common_1.Classes.FILL, ellipsize: !multiline, tagName: "span", title: htmlTitle, children: children })), (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: endIcon ?? rightIcon }), isRemovable && (0, jsx_runtime_1.jsx)(tagRemoveButton_1.TagRemoveButton, { ...props })] }));
});
exports.Tag.displayName = `${common_1.DISPLAYNAME_PREFIX}.Tag`;
//# sourceMappingURL=tag.js.map