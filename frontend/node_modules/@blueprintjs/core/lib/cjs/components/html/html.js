"use strict";
/*
 * Copyright 2018 Palantir Technologies, Inc. All rights reserved.
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.UL = exports.OL = exports.Label = exports.Pre = exports.Code = exports.Blockquote = exports.H6 = exports.H5 = exports.H4 = exports.H3 = exports.H2 = exports.H1 = void 0;
const tslib_1 = require("tslib");
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const classes_1 = require("../../common/classes");
function htmlElement(tagName, tagClassName) {
    /* eslint-disable-next-line react/display-name */
    return (0, react_1.forwardRef)((props, ref) => {
        const { className, children, ...htmlProps } = props;
        return (0, react_1.createElement)(tagName, {
            ...htmlProps,
            className: (0, classnames_1.default)(tagClassName, className),
            ref,
        }, children);
    });
}
// the following components are linted by blueprint-html-components because
// they should rarely be used without the Blueprint classes/styles:
exports.H1 = htmlElement("h1", classes_1.HEADING);
exports.H2 = htmlElement("h2", classes_1.HEADING);
exports.H3 = htmlElement("h3", classes_1.HEADING);
exports.H4 = htmlElement("h4", classes_1.HEADING);
exports.H5 = htmlElement("h5", classes_1.HEADING);
exports.H6 = htmlElement("h6", classes_1.HEADING);
exports.Blockquote = htmlElement("blockquote", classes_1.BLOCKQUOTE);
exports.Code = htmlElement("code", classes_1.CODE);
exports.Pre = htmlElement("pre", classes_1.CODE_BLOCK);
exports.Label = htmlElement("label", classes_1.LABEL);
// these two are not linted by blueprint-html-components because there are valid
// uses of these elements without Blueprint styles:
exports.OL = htmlElement("ol", classes_1.LIST);
exports.UL = htmlElement("ul", classes_1.LIST);
//# sourceMappingURL=html.js.map