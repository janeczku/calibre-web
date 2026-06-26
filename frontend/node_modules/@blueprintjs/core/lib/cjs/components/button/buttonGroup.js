"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ButtonGroup = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
// this component is simple enough that tests would be purely tautological.
/* istanbul ignore next */
/**
 * Button group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/button-group
 */
exports.ButtonGroup = (0, react_1.forwardRef)((props, ref) => {
    const { alignText, className, fill, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    minimal, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    outlined, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large, size = "medium", variant = "solid", vertical, ...htmlProps } = props;
    const buttonGroupClasses = (0, classnames_1.default)(common_1.Classes.BUTTON_GROUP, {
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.VERTICAL]: vertical,
    }, common_1.Classes.alignmentClass(alignText), common_1.Classes.sizeClass(size, { large }), common_1.Classes.variantClass(variant, { minimal, outlined }), className);
    return ((0, jsx_runtime_1.jsx)("div", { ...htmlProps, ref: ref, className: buttonGroupClasses, children: props.children }));
});
exports.ButtonGroup.displayName = `${props_1.DISPLAYNAME_PREFIX}.ButtonGroup`;
//# sourceMappingURL=buttonGroup.js.map