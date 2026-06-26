"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SwitchCard = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
const controlCard_1 = require("./controlCard");
/**
 * Switch Card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/control-card.switch-card
 */
exports.SwitchCard = (0, react_1.forwardRef)((props, ref) => {
    const className = (0, classnames_1.default)(props.className, common_1.Classes.SWITCH_CONTROL_CARD);
    return (0, jsx_runtime_1.jsx)(controlCard_1.ControlCard, { ...props, className: className, controlKind: "switch", ref: ref });
});
exports.SwitchCard.displayName = `${props_1.DISPLAYNAME_PREFIX}.SwitchCard`;
//# sourceMappingURL=switchCard.js.map