import { jsx as _jsx } from "react/jsx-runtime";
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
import classNames from "classnames";
import { Classes } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
/* istanbul ignore next */
/**
 * Dialog step component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialogstep
 */
export const DialogStep = props => {
    const { className, id, title, ...htmlProps } = props;
    // this component is never rendered directly; see MultistepDialog#renderDialogStep()
    return (_jsx("div", { ...htmlProps, className: Classes.DIALOG_STEP_CONTAINER, role: "tab", children: _jsx("div", { className: classNames(Classes.DIALOG_STEP, className) }) }));
};
DialogStep.displayName = `${DISPLAYNAME_PREFIX}.DialogStep`;
//# sourceMappingURL=dialogStep.js.map