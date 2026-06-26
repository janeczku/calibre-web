import { jsx as _jsx } from "react/jsx-runtime";
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
import { createContext } from "react";
/**
 * Context used to pass DatePicker & DateRangePicker props and state down to custom react-day-picker components
 * like DatePickerCaption.
 */
export const DatePickerContext = createContext({
    locale: undefined,
});
export const DatePickerProvider = (props) => {
    return _jsx(DatePickerContext.Provider, { value: props, children: props.children });
};
//# sourceMappingURL=datePickerContext.js.map