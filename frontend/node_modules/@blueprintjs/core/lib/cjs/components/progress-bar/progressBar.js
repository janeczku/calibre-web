"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ProgressBar = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
/**
 * Progress bar component.
 *
 * @see https://blueprintjs.com/docs/#core/components/progress-bar
 */
const ProgressBar = props => {
    const { animate = true, className, intent, stripes = true, value, ...htmlProps } = props;
    const classes = (0, classnames_1.default)(common_1.Classes.PROGRESS_BAR, common_1.Classes.intentClass(intent), {
        [common_1.Classes.PROGRESS_NO_ANIMATION]: !animate,
        [common_1.Classes.PROGRESS_NO_STRIPES]: !stripes,
    }, className);
    const percent = value == null ? undefined : 100 * (0, utils_1.clamp)(value, 0, 1);
    // don't set width if value is null (rely on default CSS value)
    const width = percent == null ? undefined : percent + "%";
    return ((0, jsx_runtime_1.jsx)("div", { ...htmlProps, "aria-valuemax": 100, "aria-valuemin": 0, "aria-valuenow": percent == null ? undefined : Math.round(percent), className: classes, role: "progressbar", children: (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.PROGRESS_METER, style: { width } }) }));
};
exports.ProgressBar = ProgressBar;
exports.ProgressBar.displayName = `${props_1.DISPLAYNAME_PREFIX}.ProgressBar`;
//# sourceMappingURL=progressBar.js.map