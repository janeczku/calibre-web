"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MultistepDialog = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2020 Palantir Technologies, Inc. All rights reserved.
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
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
const dialog_1 = require("./dialog");
const dialogFooter_1 = require("./dialogFooter");
const dialogStep_1 = require("./dialogStep");
const dialogStepButton_1 = require("./dialogStepButton");
const PADDING_BOTTOM = 0;
const MIN_WIDTH = 800;
/**
 * Multi-step dialog component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.multistep-dialog
 */
class MultistepDialog extends common_1.AbstractPureComponent {
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.MultistepDialog`;
    static defaultProps = {
        canOutsideClickClose: true,
        isOpen: false,
        navigationPosition: "left",
        resetOnClose: true,
        showCloseButtonInFooter: false,
    };
    state = this.getInitialIndexFromProps(this.props);
    render() {
        const { className, navigationPosition, showCloseButtonInFooter, isCloseButtonShown, ...otherProps } = this.props;
        return ((0, jsx_runtime_1.jsx)(dialog_1.Dialog, { isCloseButtonShown: isCloseButtonShown, ...otherProps, className: (0, classnames_1.default)({
                [common_1.Classes.MULTISTEP_DIALOG_NAV_RIGHT]: navigationPosition === "right",
                [common_1.Classes.MULTISTEP_DIALOG_NAV_TOP]: navigationPosition === "top",
            }, className), style: this.getDialogStyle(), children: (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.MULTISTEP_DIALOG_PANELS, children: [this.renderLeftPanel(), this.maybeRenderRightPanel()] }) }));
    }
    componentDidUpdate(prevProps) {
        if ((prevProps.resetOnClose || prevProps.initialStepIndex !== this.props.initialStepIndex) &&
            !prevProps.isOpen &&
            this.props.isOpen) {
            this.setState(this.getInitialIndexFromProps(this.props));
        }
    }
    getDialogStyle() {
        return { minWidth: MIN_WIDTH, paddingBottom: PADDING_BOTTOM, ...this.props.style };
    }
    renderLeftPanel() {
        return ((0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.MULTISTEP_DIALOG_LEFT_PANEL, role: "tablist", "aria-label": "steps", children: this.getDialogStepChildren().filter(isDialogStepElement).map(this.renderDialogStep) }));
    }
    renderDialogStep = (step, index) => {
        const stepNumber = index + 1;
        const hasBeenViewed = this.state.lastViewedIndex >= index;
        const currentlySelected = this.state.selectedIndex === index;
        const handleClickDialogStep = index > this.state.lastViewedIndex ? undefined : this.getDialogStepChangeHandler(index);
        return ((0, jsx_runtime_1.jsx)("div", { className: (0, classnames_1.default)(common_1.Classes.DIALOG_STEP_CONTAINER, {
                [common_1.Classes.ACTIVE]: currentlySelected,
                [common_1.Classes.DIALOG_STEP_VIEWED]: hasBeenViewed,
            }), "aria-disabled": !currentlySelected && !hasBeenViewed, "aria-selected": currentlySelected, role: "tab", children: (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.DIALOG_STEP, onClick: handleClickDialogStep, tabIndex: handleClickDialogStep ? 0 : -1, 
                // enable enter key to take effect on the div as if it were a button
                onKeyDown: (0, utils_1.clickElementOnKeyPress)(["Enter", " "]), role: "button", children: [(0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DIALOG_STEP_ICON, children: stepNumber }), (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DIALOG_STEP_TITLE, children: step.props.title })] }) }, index));
    };
    maybeRenderRightPanel() {
        const steps = this.getDialogStepChildren();
        if (steps.length <= this.state.selectedIndex) {
            return null;
        }
        const { className, panel, panelClassName } = steps[this.state.selectedIndex].props;
        return ((0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.MULTISTEP_DIALOG_RIGHT_PANEL, className, panelClassName), children: [panel, this.renderFooter()] }));
    }
    renderFooter() {
        const { closeButtonProps, showCloseButtonInFooter, onClose } = this.props;
        const maybeCloseButton = !showCloseButtonInFooter ? undefined : ((0, jsx_runtime_1.jsx)(dialogStepButton_1.DialogStepButton, { text: "Close", onClick: onClose, ...closeButtonProps }));
        return (0, jsx_runtime_1.jsx)(dialogFooter_1.DialogFooter, { actions: this.renderButtons(), children: maybeCloseButton });
    }
    renderButtons() {
        const { selectedIndex } = this.state;
        const steps = this.getDialogStepChildren();
        const buttons = [];
        if (this.state.selectedIndex > 0) {
            const backButtonProps = steps[selectedIndex].props.backButtonProps ?? this.props.backButtonProps;
            buttons.push((0, jsx_runtime_1.jsx)(dialogStepButton_1.DialogStepButton, { onClick: this.getDialogStepChangeHandler(selectedIndex - 1), text: "Back", ...backButtonProps }, "back"));
        }
        if (selectedIndex === this.getDialogStepChildren().length - 1) {
            buttons.push((0, jsx_runtime_1.jsx)(dialogStepButton_1.DialogStepButton, { intent: "primary", text: "Submit", ...this.props.finalButtonProps }, "final"));
        }
        else {
            const nextButtonProps = steps[selectedIndex].props.nextButtonProps ?? this.props.nextButtonProps;
            buttons.push((0, jsx_runtime_1.jsx)(dialogStepButton_1.DialogStepButton, { intent: "primary", onClick: this.getDialogStepChangeHandler(selectedIndex + 1), text: "Next", ...nextButtonProps }, "next"));
        }
        return buttons;
    }
    getDialogStepChangeHandler(index) {
        return (event) => {
            if (this.props.onChange !== undefined) {
                const steps = this.getDialogStepChildren();
                const prevStepId = steps[this.state.selectedIndex].props.id;
                const newStepId = steps[index].props.id;
                this.props.onChange(newStepId, prevStepId, event);
            }
            this.setState({
                lastViewedIndex: Math.max(this.state.lastViewedIndex, index),
                selectedIndex: index,
            });
        };
    }
    /** Filters children to only `<DialogStep>`s */
    getDialogStepChildren(props = this.props) {
        return react_1.Children.toArray(props.children).filter(isDialogStepElement);
    }
    getInitialIndexFromProps(props) {
        if (props.initialStepIndex !== undefined) {
            const boundedInitialIndex = Math.max(0, Math.min(props.initialStepIndex, this.getDialogStepChildren(props).length - 1));
            return {
                lastViewedIndex: boundedInitialIndex,
                selectedIndex: boundedInitialIndex,
            };
        }
        else {
            return {
                lastViewedIndex: 0,
                selectedIndex: 0,
            };
        }
    }
}
exports.MultistepDialog = MultistepDialog;
function isDialogStepElement(child) {
    return common_1.Utils.isElementOfType(child, dialogStep_1.DialogStep);
}
//# sourceMappingURL=multistepDialog.js.map