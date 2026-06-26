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
exports.Divider = void 0;
const tslib_1 = require("tslib");
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
// this component is simple enough that tests would be purely tautological.
/* istanbul ignore next */
/**
 * Divider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/divider
 */
const Divider = ({ className, compact = false, tagName = "div", ...htmlProps }) => {
    const classes = (0, classnames_1.default)(common_1.Classes.DIVIDER, { [common_1.Classes.COMPACT]: compact }, className);
    return (0, react_1.createElement)(tagName, {
        ...htmlProps,
        className: classes,
    });
};
exports.Divider = Divider;
exports.Divider.displayName = `${props_1.DISPLAYNAME_PREFIX}.Divider`;
//# sourceMappingURL=divider.js.map