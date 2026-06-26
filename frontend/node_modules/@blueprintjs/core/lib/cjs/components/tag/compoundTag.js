"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CompoundTag = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2024 Palantir Technologies, Inc. All rights reserved.
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
const common_1 = require("../../common");
const utils_1 = require("../../common/utils");
const icon_1 = require("../icon/icon");
const text_1 = require("../text/text");
const tagRemoveButton_1 = require("./tagRemoveButton");
/**
 * Compound tag component.
 *
 * @see https://blueprintjs.com/docs/#core/components/compound-tag
 */
exports.CompoundTag = (0, react_1.forwardRef)((props, ref) => {
    const { active = false, children, className, endIcon, fill = false, icon, intent, interactive = false, leftContent, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large = false, minimal = false, onRemove, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    rightIcon, round = false, size = "medium", tabIndex = 0, ...htmlProps } = props;
    const isRemovable = common_1.Utils.isFunction(onRemove);
    const tagClasses = (0, classnames_1.default)(common_1.Classes.TAG, common_1.Classes.COMPOUND_TAG, common_1.Classes.intentClass(intent), common_1.Classes.sizeClass(size, { large }), {
        [common_1.Classes.ACTIVE]: active,
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.INTERACTIVE]: interactive,
        [common_1.Classes.MINIMAL]: minimal,
        [common_1.Classes.ROUND]: round,
    }, className);
    return ((0, jsx_runtime_1.jsxs)("span", { ...htmlProps, className: tagClasses, tabIndex: interactive ? tabIndex : undefined, ref: ref, children: [(0, jsx_runtime_1.jsxs)("span", { className: common_1.Classes.COMPOUND_TAG_LEFT, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon }), (0, jsx_runtime_1.jsx)(text_1.Text, { className: (0, classnames_1.default)(common_1.Classes.COMPOUND_TAG_LEFT_CONTENT, common_1.Classes.FILL), tagName: "span", children: leftContent })] }), (0, jsx_runtime_1.jsxs)("span", { className: common_1.Classes.COMPOUND_TAG_RIGHT, children: [!(0, utils_1.isReactNodeEmpty)(children) && ((0, jsx_runtime_1.jsx)(text_1.Text, { className: (0, classnames_1.default)(common_1.Classes.COMPOUND_TAG_RIGHT_CONTENT, common_1.Classes.FILL), tagName: "span", children: children })), (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: endIcon ?? rightIcon }), isRemovable && (0, jsx_runtime_1.jsx)(tagRemoveButton_1.TagRemoveButton, { ...props })] })] }));
});
exports.CompoundTag.displayName = `${common_1.DISPLAYNAME_PREFIX}.CompoundTag`;
//# sourceMappingURL=compoundTag.js.map