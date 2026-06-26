import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import classNames from "classnames";
import { AbstractPureComponent, Classes, DISPLAYNAME_PREFIX } from "../../common";
import { KeyComboTag } from "./keyComboTag";
/**
 * Hotkey component used to display a hotkey in the HotkeysDialog.
 * Should not be used by consumers directly.
 */
export class Hotkey extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.Hotkey`;
    static defaultProps = {
        allowInInput: false,
        disabled: false,
        global: false,
        preventDefault: false,
        stopPropagation: false,
    };
    render() {
        const { label, className, ...spreadableProps } = this.props;
        const rootClasses = classNames(Classes.HOTKEY, className);
        return (_jsxs("div", { className: rootClasses, children: [_jsx("div", { className: Classes.HOTKEY_LABEL, children: label }), _jsx(KeyComboTag, { ...spreadableProps })] }));
    }
    validateProps(props) {
        if (props.global !== true && props.group == null) {
            console.error("non-global Hotkeys must define a group");
        }
    }
}
//# sourceMappingURL=hotkey.js.map