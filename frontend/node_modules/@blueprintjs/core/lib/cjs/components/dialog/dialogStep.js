"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DialogStep = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2020 Palantir Technologies, Inc. All rights reserved.
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
const common_1 = require("../../common");
const props_1 = require("../../common/props");
/* istanbul ignore next */
/**
 * Dialog step component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialogstep
 */
const DialogStep = props => {
    const { className, id, title, ...htmlProps } = props;
    // this component is never rendered directly; see MultistepDialog#renderDialogStep()
    return ((0, jsx_runtime_1.jsx)("div", { ...htmlProps, className: common_1.Classes.DIALOG_STEP_CONTAINER, role: "tab", children: (0, jsx_runtime_1.jsx)("div", { className: (0, classnames_1.default)(common_1.Classes.DIALOG_STEP, className) }) }));
};
exports.DialogStep = DialogStep;
exports.DialogStep.displayName = `${props_1.DISPLAYNAME_PREFIX}.DialogStep`;
//# sourceMappingURL=dialogStep.js.map