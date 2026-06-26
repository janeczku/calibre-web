import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { Classes } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
const NS = Classes.getClassNamespace();
// this is a simple component, unit tests would be mostly tautological
/* istanbul ignore next */
/**
 * File input component.
 *
 * @see https://blueprintjs.com/docs/#core/components/file-input
 */
export const FileInput = (props) => {
    const { buttonText, className, disabled, fill, hasSelection = false, inputProps = {}, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large = false, onInputChange, size = "medium", 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    small = false, text = "Choose file...", ...htmlProps } = props;
    const rootClasses = classNames(className, Classes.FILE_INPUT, {
        [Classes.DISABLED]: disabled,
        [Classes.FILL]: fill,
        [Classes.FILE_INPUT_HAS_SELECTION]: hasSelection,
    }, Classes.sizeClass(size, { large, small }));
    const uploadProps = {
        [`${NS}-button-text`]: buttonText,
        className: classNames(Classes.FILE_UPLOAD_INPUT, {
            [Classes.FILE_UPLOAD_INPUT_CUSTOM_TEXT]: !!buttonText,
        }),
    };
    const handleInputChange = (e) => {
        onInputChange?.(e);
        inputProps?.onChange?.(e);
    };
    return (_jsxs("label", { ...htmlProps, className: rootClasses, children: [_jsx("input", { ...inputProps, onChange: handleInputChange, type: "file", disabled: disabled }), _jsx("span", { ...uploadProps, children: text })] }));
};
FileInput.displayName = `${DISPLAYNAME_PREFIX}.FileInput`;
//# sourceMappingURL=fileInput.js.map