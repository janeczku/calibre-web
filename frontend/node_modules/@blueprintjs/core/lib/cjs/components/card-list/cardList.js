"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CardList = void 0;
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
const card_1 = require("../card/card");
exports.CardList = (0, react_1.forwardRef)((props, ref) => {
    const { bordered = true, className, children, compact = false, ...htmlProps } = props;
    const classes = (0, classnames_1.default)(className, common_1.Classes.CARD_LIST, {
        [common_1.Classes.CARD_LIST_BORDERED]: bordered,
        [common_1.Classes.COMPACT]: compact,
    });
    return ((0, jsx_runtime_1.jsx)(card_1.Card, { role: "list", elevation: common_1.Elevation.ZERO, className: classes, ...htmlProps, ref: ref, children: children }));
});
exports.CardList.displayName = `${common_1.DISPLAYNAME_PREFIX}.CardList`;
//# sourceMappingURL=cardList.js.map