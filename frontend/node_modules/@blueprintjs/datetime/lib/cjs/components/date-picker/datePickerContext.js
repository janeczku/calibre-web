"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatePickerProvider = exports.DatePickerContext = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
const react_1 = require("react");
/**
 * Context used to pass DatePicker & DateRangePicker props and state down to custom react-day-picker components
 * like DatePickerCaption.
 */
exports.DatePickerContext = (0, react_1.createContext)({
    locale: undefined,
});
const DatePickerProvider = (props) => {
    return (0, jsx_runtime_1.jsx)(exports.DatePickerContext.Provider, { value: props, children: props.children });
};
exports.DatePickerProvider = DatePickerProvider;
//# sourceMappingURL=datePickerContext.js.map