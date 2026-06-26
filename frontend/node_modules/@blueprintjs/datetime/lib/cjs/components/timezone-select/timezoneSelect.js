"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimezoneSelect = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2022 Palantir Technologies, Inc. All rights reserved.
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
const core_1 = require("@blueprintjs/core");
const select_1 = require("@blueprintjs/select");
const common_1 = require("../../common");
const timezoneDisplayFormat_1 = require("../../common/timezoneDisplayFormat");
const timezoneItems_1 = require("../../common/timezoneItems");
const timezoneNameUtils_1 = require("../../common/timezoneNameUtils");
/**
 * Timezone select component.
 *
 * @see https://blueprintjs.com/docs/#datetime/timezone-select
 */
class TimezoneSelect extends core_1.AbstractPureComponent {
    static displayName = `${core_1.DISPLAYNAME_PREFIX}.TimezoneSelect`;
    static defaultProps = {
        date: new Date(),
        disabled: false,
        fill: false,
        inputProps: {},
        placeholder: "Select timezone...",
        popoverProps: {},
        showLocalTimezone: false,
    };
    timezoneItems;
    initialTimezoneItems;
    constructor(props) {
        super(props);
        const { showLocalTimezone, inputProps = {}, date } = props;
        this.state = { query: inputProps.value || "" };
        this.timezoneItems = (0, timezoneNameUtils_1.mapTimezonesWithNames)(date, timezoneItems_1.TIMEZONE_ITEMS);
        this.initialTimezoneItems = (0, timezoneNameUtils_1.getInitialTimezoneItems)(date, showLocalTimezone);
    }
    render() {
        const { children, className, disabled, fill, inputProps, popoverProps } = this.props;
        const { query } = this.state;
        return ((0, jsx_runtime_1.jsx)(select_1.Select, { className: (0, classnames_1.default)(common_1.Classes.TIMEZONE_SELECT, className), disabled: disabled, fill: fill, inputProps: {
                placeholder: "Search for timezones...",
                ...inputProps,
            }, itemListPredicate: this.filterItems, itemRenderer: this.renderItem, items: query ? this.timezoneItems : this.initialTimezoneItems, noResults: (0, jsx_runtime_1.jsx)(core_1.MenuItem, { disabled: true, roleStructure: "listoption", text: "No matching timezones." }), onItemSelect: this.handleItemSelect, onQueryChange: this.handleQueryChange, popoverProps: {
                ...popoverProps,
                popoverClassName: (0, classnames_1.default)(common_1.Classes.TIMEZONE_SELECT_POPOVER, popoverProps?.popoverClassName),
            }, popoverTargetProps: { "aria-label": "timezone" }, resetOnClose: true, resetOnSelect: true, children: children ?? this.renderButton() }));
    }
    componentDidUpdate(prevProps, prevState) {
        super.componentDidUpdate(prevProps, prevState);
        const { date: nextDate } = this.props;
        if (this.props.showLocalTimezone !== prevProps.showLocalTimezone) {
            this.initialTimezoneItems = (0, timezoneNameUtils_1.getInitialTimezoneItems)(nextDate, this.props.showLocalTimezone);
        }
        if (nextDate != null && nextDate.getTime() !== prevProps.date?.getTime()) {
            this.initialTimezoneItems = (0, timezoneNameUtils_1.mapTimezonesWithNames)(nextDate, this.initialTimezoneItems);
            this.timezoneItems = (0, timezoneNameUtils_1.mapTimezonesWithNames)(nextDate, this.timezoneItems);
        }
    }
    renderButton() {
        const { buttonProps = {}, disabled, fill, placeholder, value, valueDisplayFormat } = this.props;
        const selectedTimezone = this.timezoneItems.find(tz => tz.ianaCode === value);
        const buttonContent = selectedTimezone !== undefined ? ((0, timezoneDisplayFormat_1.formatTimezone)(selectedTimezone, valueDisplayFormat ?? timezoneDisplayFormat_1.TimezoneDisplayFormat.COMPOSITE)) : ((0, jsx_runtime_1.jsx)("span", { className: core_1.Classes.TEXT_MUTED, children: placeholder }));
        return (0, jsx_runtime_1.jsx)(core_1.Button, { endIcon: "caret-down", disabled: disabled, text: buttonContent, fill: fill, ...buttonProps });
    }
    filterItems = (query, items) => {
        // using list predicate so only one RegExp instance is needed
        // escape bad regex characters, let spaces act as any separator
        const expr = new RegExp(query.replace(/([[()+*?])/g, "\\$1").replace(" ", "[ _/\\(\\)]+"), "i");
        return items.filter(item => expr.test(item.ianaCode) ||
            expr.test(item.label) ||
            expr.test(item.longName) ||
            expr.test(item.shortName));
    };
    renderItem = (item, { handleClick, modifiers }) => {
        if (!modifiers.matchesPredicate) {
            return null;
        }
        return ((0, jsx_runtime_1.jsx)(core_1.MenuItem, { selected: modifiers.active, text: `${item.label}, ${item.longName}`, onClick: handleClick, label: item.shortName }, item.ianaCode));
    };
    handleItemSelect = (timezone) => this.props.onChange?.(timezone.ianaCode);
    handleQueryChange = (query) => this.setState({ query });
}
exports.TimezoneSelect = TimezoneSelect;
//# sourceMappingURL=timezoneSelect.js.map