"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.InputGroup = void 0;
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
const react_1 = require("react");
const common_1 = require("../../common");
const errors_1 = require("../../common/errors");
const props_1 = require("../../common/props");
const icon_1 = require("../icon/icon");
const asyncControllableInput_1 = require("./asyncControllableInput");
const NON_HTML_PROPS = ["inputSize", "onValueChange"];
/**
 * Input group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/input-group
 */
class InputGroup extends common_1.AbstractPureComponent {
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.InputGroup`;
    state = {};
    leftElement = null;
    rightElement = null;
    refHandlers = {
        leftElement: (ref) => (this.leftElement = ref),
        rightElement: (ref) => (this.rightElement = ref),
    };
    render() {
        const { asyncControl = false, className, disabled, fill, inputClassName, inputRef, inputSize, intent, 
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        large, readOnly, round, size = "medium", 
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        small, tagName = "div", } = this.props;
        const inputGroupClasses = (0, classnames_1.default)(common_1.Classes.INPUT_GROUP, common_1.Classes.intentClass(intent), {
            [common_1.Classes.DISABLED]: disabled,
            [common_1.Classes.READ_ONLY]: readOnly,
            [common_1.Classes.FILL]: fill,
            [common_1.Classes.ROUND]: round,
        }, common_1.Classes.sizeClass(size, { large, small }), className);
        const style = {
            ...this.props.style,
            paddingLeft: this.state.leftElementWidth,
            paddingRight: this.state.rightElementWidth,
        };
        const inputProps = {
            type: "text",
            ...(0, props_1.removeNonHTMLProps)(this.props, NON_HTML_PROPS, true),
            "aria-disabled": disabled,
            className: (0, classnames_1.default)(common_1.Classes.INPUT, inputClassName),
            onChange: this.handleInputChange,
            size: inputSize,
            style,
        };
        const inputElement = asyncControl ? ((0, jsx_runtime_1.jsx)(asyncControllableInput_1.AsyncControllableInput, { ...inputProps, inputRef: inputRef })) : ((0, jsx_runtime_1.jsx)("input", { ...inputProps, ref: inputRef }));
        return (0, react_1.createElement)(tagName, { className: inputGroupClasses }, this.maybeRenderLeftElement(), inputElement, this.maybeRenderRightElement());
    }
    componentDidMount() {
        this.updateInputWidth();
    }
    componentDidUpdate(prevProps) {
        const { leftElement, rightElement } = this.props;
        if (prevProps.leftElement !== leftElement || prevProps.rightElement !== rightElement) {
            this.updateInputWidth();
        }
    }
    validateProps(props) {
        if (props.leftElement != null && props.leftIcon != null) {
            console.warn(errors_1.INPUT_WARN_LEFT_ELEMENT_LEFT_ICON_MUTEX);
        }
    }
    handleInputChange = (event) => {
        const value = event.target.value;
        this.props.onChange?.(event);
        this.props.onValueChange?.(value, event.target);
    };
    maybeRenderLeftElement() {
        const { leftElement, leftIcon } = this.props;
        if (leftElement != null) {
            return ((0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.INPUT_LEFT_CONTAINER, ref: this.refHandlers.leftElement, children: leftElement }));
        }
        else if (leftIcon != null) {
            return (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: leftIcon, "aria-hidden": true, tabIndex: -1 });
        }
        return undefined;
    }
    maybeRenderRightElement() {
        const { rightElement } = this.props;
        if (rightElement == null) {
            return undefined;
        }
        return ((0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.INPUT_ACTION, ref: this.refHandlers.rightElement, children: rightElement }));
    }
    updateInputWidth() {
        const { leftElementWidth, rightElementWidth } = this.state;
        if (this.leftElement != null) {
            const { clientWidth } = this.leftElement;
            // small threshold to prevent infinite loops
            if (leftElementWidth === undefined || Math.abs(clientWidth - leftElementWidth) > 2) {
                this.setState({ leftElementWidth: clientWidth });
            }
        }
        else {
            this.setState({ leftElementWidth: undefined });
        }
        if (this.rightElement != null) {
            const { clientWidth } = this.rightElement;
            // small threshold to prevent infinite loops
            if (rightElementWidth === undefined || Math.abs(clientWidth - rightElementWidth) > 2) {
                this.setState({ rightElementWidth: clientWidth });
            }
        }
        else {
            this.setState({ rightElementWidth: undefined });
        }
    }
}
exports.InputGroup = InputGroup;
//# sourceMappingURL=inputGroup.js.map