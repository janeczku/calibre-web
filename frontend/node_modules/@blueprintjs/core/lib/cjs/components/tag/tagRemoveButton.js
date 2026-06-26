"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TagRemoveButton = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
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
const react_1 = require("react");
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const TagRemoveButton = (props) => {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const { className, large, onRemove, size, tabIndex } = props;
    const isLarge = large || size === "large" || className?.includes(common_1.Classes.LARGE);
    const handleRemoveClick = (0, react_1.useCallback)((e) => {
        onRemove?.(e, props);
    }, [onRemove, props]);
    return ((0, jsx_runtime_1.jsx)("button", { "aria-label": "Remove tag", type: "button", className: common_1.Classes.TAG_REMOVE, onClick: handleRemoveClick, tabIndex: tabIndex, children: (0, jsx_runtime_1.jsx)(icons_1.SmallCross, { size: isLarge ? icons_1.IconSize.LARGE : icons_1.IconSize.STANDARD }) }));
};
exports.TagRemoveButton = TagRemoveButton;
exports.TagRemoveButton.displayName = `${common_1.DISPLAYNAME_PREFIX}.TagRemoveButton`;
//# sourceMappingURL=tagRemoveButton.js.map