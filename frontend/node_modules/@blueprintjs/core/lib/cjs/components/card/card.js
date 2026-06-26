"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Card = void 0;
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
/**
 * Card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/card
 */
exports.Card = (0, react_1.forwardRef)((props, ref) => {
    const { className, elevation = common_1.Elevation.ZERO, interactive = false, selected, compact, ...htmlProps } = props;
    const classes = (0, classnames_1.default)(className, common_1.Classes.CARD, common_1.Classes.elevationClass(elevation), {
        [common_1.Classes.INTERACTIVE]: interactive,
        [common_1.Classes.COMPACT]: compact,
        [common_1.Classes.SELECTED]: selected,
    });
    return (0, jsx_runtime_1.jsx)("div", { className: classes, ref: ref, ...htmlProps });
});
exports.Card.displayName = `${props_1.DISPLAYNAME_PREFIX}.Card`;
//# sourceMappingURL=card.js.map