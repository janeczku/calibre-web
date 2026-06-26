"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TextArea = void 0;
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
const asyncControllableTextArea_1 = require("./asyncControllableTextArea");
// this component is simple enough that tests would be purely tautological.
/* istanbul ignore next */
/**
 * Text area component.
 *
 * @see https://blueprintjs.com/docs/#core/components/text-area
 */
class TextArea extends common_1.AbstractPureComponent {
    static defaultProps = {
        autoResize: false,
        fill: false,
        large: false,
        size: "medium",
        small: false,
    };
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.TextArea`;
    state = {};
    // used to measure and set the height of the component on first mount
    textareaElement = null;
    handleRef = (0, common_1.refHandler)(this, "textareaElement", this.props.inputRef);
    maybeSyncHeightToScrollHeight = () => {
        const { autoResize } = this.props;
        if (this.textareaElement != null) {
            const { scrollHeight } = this.textareaElement;
            if (autoResize) {
                // set height to 0 to force scrollHeight to be the minimum height to fit
                // the content of the textarea
                this.textareaElement.style.height = "0px";
                this.textareaElement.style.height = scrollHeight.toString() + "px";
                this.setState({ height: scrollHeight });
            }
        }
        if (this.props.autoResize && this.textareaElement != null) {
            // set height to 0 to force scrollHeight to be the minimum height to fit
            // the content of the textarea
            this.textareaElement.style.height = "0px";
            const { scrollHeight } = this.textareaElement;
            this.textareaElement.style.height = scrollHeight.toString() + "px";
            this.setState({ height: scrollHeight });
        }
    };
    componentDidMount() {
        this.maybeSyncHeightToScrollHeight();
    }
    componentDidUpdate(prevProps) {
        if (prevProps.inputRef !== this.props.inputRef) {
            (0, common_1.setRef)(prevProps.inputRef, null);
            this.handleRef = (0, common_1.refHandler)(this, "textareaElement", this.props.inputRef);
            (0, common_1.setRef)(this.props.inputRef, this.textareaElement);
        }
        if (prevProps.value !== this.props.value || prevProps.style !== this.props.style) {
            this.maybeSyncHeightToScrollHeight();
        }
    }
    render() {
        const { asyncControl, autoResize, className, fill, inputRef, intent, 
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        large, size = "medium", 
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        small, ...htmlProps } = this.props;
        const rootClasses = (0, classnames_1.default)(common_1.Classes.INPUT, common_1.Classes.TEXT_AREA, common_1.Classes.intentClass(intent), common_1.Classes.sizeClass(size, { large, small }), {
            [common_1.Classes.FILL]: fill,
            [common_1.Classes.TEXT_AREA_AUTO_RESIZE]: autoResize,
        }, className);
        // add explicit height style while preserving user-supplied styles if they exist
        let { style = {} } = htmlProps;
        if (autoResize && this.state.height != null) {
            // this style object becomes non-extensible when mounted (at least in the enzyme renderer),
            // so we make a new one to add a property
            style = {
                ...style,
                height: `${this.state.height}px`,
            };
        }
        const TextAreaComponent = asyncControl ? asyncControllableTextArea_1.AsyncControllableTextArea : "textarea";
        return ((0, jsx_runtime_1.jsx)(TextAreaComponent, { ...htmlProps, className: rootClasses, onChange: this.handleChange, style: style, ref: this.handleRef }));
    }
    handleChange = (e) => {
        this.maybeSyncHeightToScrollHeight();
        this.props.onChange?.(e);
    };
}
exports.TextArea = TextArea;
//# sourceMappingURL=textArea.js.map