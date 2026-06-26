"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TagInput = void 0;
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
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
const icon_1 = require("../icon/icon");
const tag_1 = require("../tag/tag");
const resizableInput_1 = require("./resizableInput");
/** special value for absence of active tag */
const NONE = -1;
/**
 * Tag input component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tag-input
 */
class TagInput extends common_1.AbstractPureComponent {
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.TagInput`;
    static defaultProps = {
        addOnBlur: false,
        addOnPaste: true,
        autoResize: false,
        inputProps: {},
        separator: /[,\n\r]/,
        tagProps: {},
    };
    static getDerivedStateFromProps(props, state) {
        if (props.inputValue !== state.prevInputValueProp) {
            return {
                inputValue: props.inputValue,
                prevInputValueProp: props.inputValue,
            };
        }
        return null;
    }
    state = {
        activeIndex: NONE,
        inputValue: this.props.inputValue || "",
        isInputFocused: false,
    };
    inputElement = null;
    handleRef = (0, common_1.refHandler)(this, "inputElement", this.props.inputRef);
    render() {
        const { autoResize, className, disabled, fill, inputProps, intent, 
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        large, leftIcon, placeholder, size = "medium", values, } = this.props;
        const classes = (0, classnames_1.default)(common_1.Classes.INPUT, common_1.Classes.TAG_INPUT, {
            [common_1.Classes.ACTIVE]: this.state.isInputFocused,
            [common_1.Classes.DISABLED]: disabled,
            [common_1.Classes.FILL]: fill,
        }, common_1.Classes.intentClass(intent), common_1.Classes.sizeClass(size, { large }), className);
        const isLarge = classes.indexOf(common_1.Classes.LARGE) > NONE;
        // use placeholder prop only if it's defined and values list is empty or contains only falsy values
        const isSomeValueDefined = values.some(val => !!val);
        const resolvedPlaceholder = placeholder == null || isSomeValueDefined ? inputProps?.placeholder : placeholder;
        // final props that may be sent to <input> or <ResizableInput>
        const resolvedInputProps = {
            value: this.state.inputValue,
            ...inputProps,
            className: (0, classnames_1.default)(common_1.Classes.INPUT_GHOST, inputProps?.className),
            disabled,
            onChange: this.handleInputChange,
            onFocus: this.handleInputFocus,
            onKeyDown: this.handleInputKeyDown,
            onKeyUp: this.handleInputKeyUp,
            onPaste: this.handleInputPaste,
            placeholder: resolvedPlaceholder,
            ref: this.handleRef,
        };
        return (
        // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- container delegates interaction to input element
        (0, jsx_runtime_1.jsxs)("div", { className: classes, onBlur: this.handleContainerBlur, onClick: this.handleContainerClick, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { className: common_1.Classes.TAG_INPUT_ICON, icon: leftIcon, size: isLarge ? icons_1.IconSize.LARGE : icons_1.IconSize.STANDARD }), (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.TAG_INPUT_VALUES, children: [values.map(this.maybeRenderTag), this.props.children, autoResize ? (0, jsx_runtime_1.jsx)(resizableInput_1.ResizableInput, { ...resolvedInputProps }) : (0, jsx_runtime_1.jsx)("input", { ...resolvedInputProps })] }), this.props.rightElement] }));
    }
    componentDidUpdate(prevProps) {
        if (prevProps.inputRef !== this.props.inputRef) {
            (0, common_1.setRef)(prevProps.inputRef, null);
            this.handleRef = (0, common_1.refHandler)(this, "inputElement", this.props.inputRef);
            (0, common_1.setRef)(this.props.inputRef, this.inputElement);
        }
    }
    addTags = (value, method = "default") => {
        const { inputValue, onAdd, onChange, values } = this.props;
        const newValues = this.getValues(value);
        let shouldClearInput = onAdd?.(newValues, method) !== false && inputValue === undefined;
        // avoid a potentially expensive computation if this prop is omitted
        if (common_1.Utils.isFunction(onChange)) {
            shouldClearInput = onChange([...values, ...newValues]) !== false && shouldClearInput;
        }
        // only explicit return false cancels text clearing
        if (shouldClearInput) {
            this.setState({ inputValue: "" });
        }
    };
    maybeRenderTag = (tag, index) => {
        if (!tag) {
            return null;
        }
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        const { large, size, tagProps } = this.props;
        const props = common_1.Utils.isFunction(tagProps) ? tagProps(tag, index) : tagProps;
        return ((0, jsx_runtime_1.jsx)(tag_1.Tag, { active: index === this.state.activeIndex, "data-tag-index": index, 
            // eslint-disable-next-line @typescript-eslint/no-deprecated
            large: large, onRemove: this.props.disabled ? undefined : this.handleRemoveTag, size: size, ...props, children: tag }, tag + "__" + index));
    };
    getNextActiveIndex(direction) {
        const { activeIndex } = this.state;
        if (activeIndex === NONE) {
            // nothing active & moving left: select last defined value. otherwise select nothing.
            return direction < 0 ? this.findNextIndex(this.props.values.length, -1) : NONE;
        }
        else {
            // otherwise, move in direction and clamp to bounds.
            // note that upper bound allows going one beyond last item
            // so focus can move off the right end, into the text input.
            return this.findNextIndex(activeIndex, direction);
        }
    }
    findNextIndex(startIndex, direction) {
        const { values } = this.props;
        let index = startIndex + direction;
        while (index > 0 && index < values.length && !values[index]) {
            index += direction;
        }
        return common_1.Utils.clamp(index, 0, values.length);
    }
    /**
     * Splits inputValue on separator prop,
     * trims whitespace from each new value,
     * and ignores empty values.
     */
    getValues(inputValue) {
        const { separator } = this.props;
        // NOTE: split() typings define two overrides for string and RegExp.
        // this does not play well with our union prop type, so we'll just declare it as a valid type.
        return (separator === false ? [inputValue] : inputValue.split(separator))
            .map(val => val.trim())
            .filter(val => val.length > 0);
    }
    handleContainerClick = () => {
        this.inputElement?.focus();
    };
    handleContainerBlur = ({ currentTarget }) => {
        this.requestAnimationFrame(() => {
            // we only care if the blur event is leaving the container.
            // defer this check using rAF so activeElement will have updated.
            const isFocusInsideContainer = currentTarget.contains((0, utils_1.getActiveElement)(this.inputElement));
            if (!isFocusInsideContainer) {
                if (this.props.addOnBlur && this.state.inputValue !== undefined && this.state.inputValue.length > 0) {
                    this.addTags(this.state.inputValue, "blur");
                }
                this.setState({ activeIndex: NONE, isInputFocused: false });
            }
        });
    };
    handleInputFocus = (event) => {
        this.setState({ isInputFocused: true });
        this.props.inputProps?.onFocus?.(event);
    };
    handleInputChange = (event) => {
        this.setState({ activeIndex: NONE, inputValue: event.currentTarget.value });
        this.props.onInputChange?.(event);
        this.props.inputProps?.onChange?.(event);
    };
    handleInputKeyDown = (event) => {
        const { selectionEnd, value } = event.currentTarget;
        const { activeIndex } = this.state;
        let activeIndexToEmit = activeIndex;
        // do not add a new tag if the user is composing (e.g. for Japanese or Chinese)
        if (event.key === "Enter" && !event.nativeEvent.isComposing && value.length > 0) {
            this.addTags(value, "default");
        }
        else if (selectionEnd === 0 && this.props.values.length > 0) {
            // cursor at beginning of input allows interaction with tags.
            // use selectionEnd to verify cursor position and no text selection.
            const direction = common_1.Utils.getArrowKeyDirection(event, ["ArrowLeft"], ["ArrowRight"]);
            if (direction !== undefined) {
                const nextActiveIndex = this.getNextActiveIndex(direction);
                if (nextActiveIndex !== activeIndex) {
                    event.stopPropagation();
                    activeIndexToEmit = nextActiveIndex;
                    this.setState({ activeIndex: nextActiveIndex });
                }
            }
            else if (event.key === "Backspace") {
                this.handleBackspaceToRemove(event);
            }
            else if (event.key === "Delete") {
                this.handleDeleteToRemove(event);
            }
        }
        this.invokeKeyPressCallback("onKeyDown", event, activeIndexToEmit);
    };
    handleInputKeyUp = (event) => {
        this.invokeKeyPressCallback("onKeyUp", event, this.state.activeIndex);
    };
    handleInputPaste = (event) => {
        const { separator } = this.props;
        const value = event.clipboardData.getData("text");
        if (!this.props.addOnPaste || value.length === 0) {
            return;
        }
        // special case as a UX nicety: if the user pasted only one value with no delimiters in it, leave that value in
        // the input field so that the user can refine it before converting it to a tag manually.
        if (separator === false || value.split(separator).length === 1) {
            return;
        }
        event.preventDefault();
        this.addTags(value, "paste");
    };
    handleRemoveTag = (event) => {
        // using data attribute to simplify callback logic -- one handler for all children
        const index = +event.currentTarget.parentElement.getAttribute("data-tag-index");
        this.removeIndexFromValues(index);
    };
    handleBackspaceToRemove(event) {
        const previousActiveIndex = this.state.activeIndex;
        // always move leftward one item (this will focus last item if nothing is focused)
        this.setState({ activeIndex: this.getNextActiveIndex(-1) });
        // delete item if there was a previous valid selection (ignore first backspace to focus last item)
        if (this.isValidIndex(previousActiveIndex)) {
            event.stopPropagation();
            this.removeIndexFromValues(previousActiveIndex);
        }
    }
    handleDeleteToRemove(event) {
        const { activeIndex } = this.state;
        if (this.isValidIndex(activeIndex)) {
            event.stopPropagation();
            this.removeIndexFromValues(activeIndex);
        }
    }
    /** Remove the item at the given index by invoking `onRemove` and `onChange` accordingly. */
    removeIndexFromValues(index) {
        const { onChange, onRemove, values } = this.props;
        onRemove?.(values[index], index);
        onChange?.(values.filter((_, i) => i !== index));
    }
    invokeKeyPressCallback(propCallbackName, event, activeIndex) {
        this.props[propCallbackName]?.(event, activeIndex === NONE ? undefined : activeIndex);
        this.props.inputProps[propCallbackName]?.(event);
    }
    /** Returns whether the given index represents a valid item in `this.props.values`. */
    isValidIndex(index) {
        return index !== NONE && index < this.props.values.length;
    }
}
exports.TagInput = TagInput;
//# sourceMappingURL=tagInput.js.map