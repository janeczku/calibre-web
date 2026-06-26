import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import classNames from "classnames";
import { AbstractPureComponent, Classes } from "../../common";
import { DISPLAYNAME_PREFIX, } from "../../common/props";
import { clamp } from "../../common/utils";
const BUFFER_WIDTH_DEFAULT = 5;
/**
 * EditableText component.
 *
 * @see https://blueprintjs.com/docs/#core/components/editable-text
 */
export class EditableText extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.EditableText`;
    static defaultProps = {
        alwaysRenderInput: false,
        confirmOnEnterKey: false,
        defaultValue: "",
        disabled: false,
        maxLines: Infinity,
        minLines: 1,
        minWidth: 80,
        multiline: false,
        placeholder: "Click to Edit",
        type: "text",
    };
    inputElement = null;
    valueElement = null;
    refHandlers = {
        content: (spanElement) => {
            this.valueElement = spanElement;
        },
        input: (input) => {
            if (input != null) {
                this.inputElement = input;
                // temporary fix for #3882
                if (!this.props.alwaysRenderInput) {
                    this.inputElement.focus();
                }
                if (this.state != null && this.state.isEditing) {
                    const supportsSelection = inputSupportsSelection(input);
                    if (supportsSelection) {
                        const { length } = input.value;
                        input.setSelectionRange(this.props.selectAllOnFocus ? 0 : length, length);
                    }
                    if (!supportsSelection || !this.props.selectAllOnFocus) {
                        input.scrollLeft = input.scrollWidth;
                    }
                }
            }
        },
    };
    constructor(props) {
        super(props);
        const value = props.value == null ? props.defaultValue : props.value;
        this.state = {
            inputHeight: 0,
            inputWidth: 0,
            isEditing: props.isEditing === true && props.disabled === false,
            lastValue: value,
            value,
        };
    }
    render() {
        const { alwaysRenderInput, disabled, elementRef, multiline, contentId } = this.props;
        const value = this.props.value ?? this.state.value;
        const hasValue = value != null && value !== "";
        const classes = classNames(Classes.EDITABLE_TEXT, Classes.intentClass(this.props.intent), {
            [Classes.DISABLED]: disabled,
            [Classes.EDITABLE_TEXT_EDITING]: this.state.isEditing,
            [Classes.EDITABLE_TEXT_PLACEHOLDER]: !hasValue,
            [Classes.MULTILINE]: multiline,
        }, this.props.className);
        let contentStyle;
        if (multiline) {
            // set height only in multiline mode when not editing
            // otherwise we're measuring this element to determine appropriate height of text
            contentStyle = { height: !this.state.isEditing ? this.state.inputHeight : undefined };
        }
        else {
            // minWidth only applies in single line mode (multiline == width 100%)
            contentStyle = {
                height: this.state.inputHeight,
                lineHeight: this.state.inputHeight != null ? `${this.state.inputHeight}px` : undefined,
                minWidth: this.props.minWidth,
            };
        }
        // If we are always rendering an input, then NEVER make the container div focusable.
        // Otherwise, make container div focusable when not editing, so it can still be tabbed
        // to focus (when the input is rendered, it is itself focusable so container div doesn't need to be)
        const tabIndex = alwaysRenderInput || this.state.isEditing || disabled ? undefined : 0;
        // we need the contents to be rendered while editing so that we can measure their height
        // and size the container element responsively
        const shouldHideContents = alwaysRenderInput && !this.state.isEditing;
        const spanProps = contentId != null ? { id: contentId } : {};
        return (_jsxs("div", { className: classes, onFocus: this.handleFocus, tabIndex: tabIndex, ref: elementRef, children: [alwaysRenderInput || this.state.isEditing ? this.renderInput(value) : undefined, shouldHideContents ? undefined : (_jsx("span", { ...spanProps, className: Classes.EDITABLE_TEXT_CONTENT, ref: this.refHandlers.content, style: contentStyle, children: hasValue ? value : this.props.placeholder }))] }));
    }
    componentDidMount() {
        this.updateInputDimensions();
    }
    componentDidUpdate(prevProps, prevState) {
        const newState = {};
        // allow setting the value to undefined/null in controlled mode
        if (this.props.value !== prevProps.value && (prevProps.value != null || this.props.value != null)) {
            newState.value = this.props.value;
        }
        if (this.props.isEditing != null && this.props.isEditing !== prevProps.isEditing) {
            newState.isEditing = this.props.isEditing;
        }
        if (this.props.disabled || (this.props.disabled == null && prevProps.disabled)) {
            newState.isEditing = false;
        }
        this.setState(newState);
        if (this.state.isEditing && !prevState.isEditing) {
            this.props.onEdit?.(this.state.value);
        }
        // updateInputDimensions is an expensive method. Call it only when the props
        // it depends on change
        if (this.state.value !== prevState.value ||
            this.props.alwaysRenderInput !== prevProps.alwaysRenderInput ||
            this.props.maxLines !== prevProps.maxLines ||
            this.props.minLines !== prevProps.minLines ||
            this.props.minWidth !== prevProps.minWidth ||
            this.props.multiline !== prevProps.multiline ||
            this.props.placeholder !== prevProps.placeholder) {
            this.updateInputDimensions();
        }
    }
    cancelEditing = () => {
        const { lastValue, value } = this.state;
        this.setState({ isEditing: false, value: lastValue });
        if (value !== lastValue) {
            this.props.onChange?.(lastValue);
        }
        this.props.onCancel?.(lastValue);
    };
    toggleEditing = () => {
        if (this.state.isEditing) {
            const { value } = this.state;
            this.setState({ isEditing: false, lastValue: value });
            this.props.onConfirm?.(value);
        }
        else if (!this.props.disabled) {
            this.setState({ isEditing: true });
        }
    };
    handleFocus = () => {
        const { alwaysRenderInput, disabled, selectAllOnFocus } = this.props;
        if (!disabled) {
            this.setState({ isEditing: true });
        }
        if (alwaysRenderInput && selectAllOnFocus && this.inputElement != null) {
            const { length } = this.inputElement.value;
            this.inputElement.setSelectionRange(0, length);
        }
    };
    handleTextChange = (event) => {
        const value = event.target.value;
        // state value should be updated only when uncontrolled
        if (this.props.value == null) {
            this.setState({ value });
        }
        this.props.onChange?.(value);
    };
    handleKeyEvent = (event) => {
        // During IME composition, Enter and Escape has special meanings that we will not override
        if (event.nativeEvent.isComposing) {
            return;
        }
        const { altKey, ctrlKey, metaKey, shiftKey } = event;
        if (event.key === "Escape") {
            this.cancelEditing();
            return;
        }
        const hasModifierKey = altKey || ctrlKey || metaKey || shiftKey;
        if (event.key === "Enter") {
            // prevent browsers (Edge?) from full screening with alt + enter
            // shift + enter adds a newline by default
            if (altKey || shiftKey) {
                event.preventDefault();
            }
            if (this.props.confirmOnEnterKey && this.props.multiline) {
                if (event.target != null && hasModifierKey) {
                    insertAtCaret(event.target, "\n");
                    this.handleTextChange(event);
                }
                else {
                    this.toggleEditing();
                }
            }
            else if (!this.props.multiline || hasModifierKey) {
                this.toggleEditing();
            }
        }
    };
    renderInput(value) {
        const { disabled, maxLength, multiline, type, placeholder, customInputAttributes } = this.props;
        const props = {
            className: Classes.EDITABLE_TEXT_INPUT,
            disabled,
            maxLength,
            onBlur: this.toggleEditing,
            onChange: this.handleTextChange,
            onKeyDown: this.handleKeyEvent,
            placeholder,
            value,
        };
        const { inputHeight, inputWidth } = this.state;
        if (inputHeight !== 0 && inputWidth !== 0) {
            props.style = {
                height: inputHeight,
                lineHeight: !multiline && inputHeight != null ? `${inputHeight}px` : undefined,
                width: multiline ? "100%" : inputWidth,
            };
        }
        return multiline ? (_jsx("textarea", { ref: this.refHandlers.input, ...props, ...customInputAttributes })) : (_jsx("input", { ref: this.refHandlers.input, type: type, ...props, ...customInputAttributes }));
    }
    updateInputDimensions() {
        if (this.valueElement != null) {
            const { maxLines, minLines, minWidth, multiline } = this.props;
            const { parentElement, textContent } = this.valueElement;
            let { scrollHeight, scrollWidth } = this.valueElement;
            const lineHeight = getLineHeight(this.valueElement);
            // add one line to computed <span> height if text ends in newline
            // because <span> collapses that trailing whitespace but <textarea> shows it
            if (multiline && this.state.isEditing && /\n$/.test(textContent ?? "")) {
                scrollHeight += lineHeight;
            }
            if (lineHeight > 0) {
                // line height could be 0 if the isNaN block from getLineHeight kicks in
                scrollHeight = clamp(scrollHeight, minLines * lineHeight, maxLines * lineHeight);
            }
            // Chrome's input caret height misaligns text so the line-height must be larger than font-size.
            // The computed scrollHeight must also account for a larger inherited line-height from the parent.
            scrollHeight = Math.max(scrollHeight, getFontSize(this.valueElement) + 1, getLineHeight(parentElement));
            // Need to add a small buffer so text does not shift prior to resizing, causing an infinite loop.
            scrollWidth += BUFFER_WIDTH_DEFAULT;
            this.setState({
                inputHeight: scrollHeight,
                inputWidth: Math.max(scrollWidth, minWidth),
            });
            // synchronizes the ::before pseudo-element's height while editing for Chrome 53
            if (multiline && this.state.isEditing) {
                this.setTimeout(() => (parentElement.style.height = `${scrollHeight}px`));
            }
        }
    }
}
function getFontSize(element) {
    const fontSize = getComputedStyle(element).fontSize;
    return fontSize === "" ? 0 : parseInt(fontSize.slice(0, -2), 10);
}
function getLineHeight(element) {
    // getComputedStyle() => 18.0001px => 18
    let lineHeight = parseInt(getComputedStyle(element).lineHeight.slice(0, -2), 10);
    // this check will be true if line-height is a keyword like "normal"
    if (isNaN(lineHeight)) {
        // @see http://stackoverflow.com/a/18430767/6342931
        const line = document.createElement("span");
        line.innerHTML = "<br>";
        element.appendChild(line);
        const singleLineHeight = element.offsetHeight;
        line.innerHTML = "<br><br>";
        const doubleLineHeight = element.offsetHeight;
        element.removeChild(line);
        // this can return 0 in edge cases
        lineHeight = doubleLineHeight - singleLineHeight;
    }
    return lineHeight;
}
function insertAtCaret(el, text) {
    const { selectionEnd, selectionStart, value } = el;
    if (selectionStart >= 0) {
        const before = value.substring(0, selectionStart);
        const after = value.substring(selectionEnd, value.length);
        const len = text.length;
        el.value = `${before}${text}${after}`;
        el.selectionStart = selectionStart + len;
        el.selectionEnd = selectionStart + len;
    }
}
function inputSupportsSelection(input) {
    switch (input.type) {
        // HTMLTextAreaElement
        case "textarea":
            return true;
        // HTMLInputElement
        // see https://html.spec.whatwg.org/multipage/input.html#do-not-apply
        case "text":
        case "search":
        case "tel":
        case "url":
        case "password":
            return true;
        default:
            return false;
    }
}
//# sourceMappingURL=editableText.js.map