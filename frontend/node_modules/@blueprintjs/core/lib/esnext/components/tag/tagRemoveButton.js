import { jsx as _jsx } from "react/jsx-runtime";
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
import { useCallback } from "react";
import { IconSize, SmallCross } from "@blueprintjs/icons";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
export const TagRemoveButton = (props) => {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const { className, large, onRemove, size, tabIndex } = props;
    const isLarge = large || size === "large" || className?.includes(Classes.LARGE);
    const handleRemoveClick = useCallback((e) => {
        onRemove?.(e, props);
    }, [onRemove, props]);
    return (_jsx("button", { "aria-label": "Remove tag", type: "button", className: Classes.TAG_REMOVE, onClick: handleRemoveClick, tabIndex: tabIndex, children: _jsx(SmallCross, { size: isLarge ? IconSize.LARGE : IconSize.STANDARD }) }));
};
TagRemoveButton.displayName = `${DISPLAYNAME_PREFIX}.TagRemoveButton`;
//# sourceMappingURL=tagRemoveButton.js.map