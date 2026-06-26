import { jsx as _jsx } from "react/jsx-runtime";
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
import classNames from "classnames";
import { forwardRef } from "react";
import { Classes, DISPLAYNAME_PREFIX, Elevation } from "../../common";
import { Card } from "../card/card";
export const CardList = forwardRef((props, ref) => {
    const { bordered = true, className, children, compact = false, ...htmlProps } = props;
    const classes = classNames(className, Classes.CARD_LIST, {
        [Classes.CARD_LIST_BORDERED]: bordered,
        [Classes.COMPACT]: compact,
    });
    return (_jsx(Card, { role: "list", elevation: Elevation.ZERO, className: classes, ...htmlProps, ref: ref, children: children }));
});
CardList.displayName = `${DISPLAYNAME_PREFIX}.CardList`;
//# sourceMappingURL=cardList.js.map