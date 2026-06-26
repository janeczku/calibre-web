import { jsx as _jsx } from "react/jsx-runtime";
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
import classNames from "classnames";
import { forwardRef } from "react";
import { Classes } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
// this component is simple enough that tests would be purely tautological.
/* istanbul ignore next */
/**
 * Control group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/control-group
 */
export const ControlGroup = forwardRef((props, ref) => {
    const { children, className, fill, vertical, ...htmlProps } = props;
    const rootClasses = classNames(Classes.CONTROL_GROUP, {
        [Classes.FILL]: fill,
        [Classes.VERTICAL]: vertical,
    }, className);
    return (_jsx("div", { role: "group", ...htmlProps, ref: ref, className: rootClasses, children: children }));
});
ControlGroup.displayName = `${DISPLAYNAME_PREFIX}.ControlGroup`;
//# sourceMappingURL=controlGroup.js.map