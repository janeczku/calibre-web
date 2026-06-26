"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FileInput = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const NS = common_1.Classes.getClassNamespace();
// this is a simple component, unit tests would be mostly tautological
/* istanbul ignore next */
/**
 * File input component.
 *
 * @see https://blueprintjs.com/docs/#core/components/file-input
 */
const FileInput = (props) => {
    const { buttonText, className, disabled, fill, hasSelection = false, inputProps = {}, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large = false, onInputChange, size = "medium", 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    small = false, text = "Choose file...", ...htmlProps } = props;
    const rootClasses = (0, classnames_1.default)(className, common_1.Classes.FILE_INPUT, {
        [common_1.Classes.DISABLED]: disabled,
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.FILE_INPUT_HAS_SELECTION]: hasSelection,
    }, common_1.Classes.sizeClass(size, { large, small }));
    const uploadProps = {
        [`${NS}-button-text`]: buttonText,
        className: (0, classnames_1.default)(common_1.Classes.FILE_UPLOAD_INPUT, {
            [common_1.Classes.FILE_UPLOAD_INPUT_CUSTOM_TEXT]: !!buttonText,
        }),
    };
    const handleInputChange = (e) => {
        onInputChange?.(e);
        inputProps?.onChange?.(e);
    };
    return ((0, jsx_runtime_1.jsxs)("label", { ...htmlProps, className: rootClasses, children: [(0, jsx_runtime_1.jsx)("input", { ...inputProps, onChange: handleInputChange, type: "file", disabled: disabled }), (0, jsx_runtime_1.jsx)("span", { ...uploadProps, children: text })] }));
};
exports.FileInput = FileInput;
exports.FileInput.displayName = `${props_1.DISPLAYNAME_PREFIX}.FileInput`;
//# sourceMappingURL=fileInput.js.map