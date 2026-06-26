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
import { AbstractPureComponent } from "@blueprintjs/core";
import { loadDateFnsLocale } from "../common/dateFnsLocaleUtils";
/**
 * Abstract component which accepts a date-fns locale prop and loads the corresponding `Locale` object as necessary.
 *
 * Currently used by DatePicker, DateRangePicker, and DateRangeInput, but we would ideally migrate to the
 * `useDateFnsLocale()` hook once those components are refactored into functional components.
 */
export class DateFnsLocalizedComponent extends AbstractPureComponent {
    // Keeping track of `isMounted` state is generally considered an anti-pattern, but since there is no way to
    // cancel/abort dyanmic ES module `import()` calls to load the date-fns locale, this is the best way to avoid
    // setting state on an unmounted component, which creates noise in the console (especially while running tests).
    // N.B. this cannot be named `isMounted` because that conflicts with a React internal property.
    isComponentMounted = false;
    // HACKHACK: type fix for setState which does not accept partial state objects in our version of
    // @types/react (v16.14.x)
    setState(nextStateOrAction, callback) {
        if (typeof nextStateOrAction === "function") {
            super.setState(nextStateOrAction, callback);
        }
        else {
            super.setState(nextStateOrAction);
        }
    }
    async componentDidMount() {
        this.isComponentMounted = true;
        await this.loadLocale(this.props.locale);
    }
    async componentDidUpdate(prevProps) {
        if (this.props.locale !== prevProps.locale) {
            await this.loadLocale(this.props.locale);
        }
    }
    componentWillUnmount() {
        this.isComponentMounted = false;
    }
    async loadLocale(localeOrCode) {
        if (localeOrCode === undefined) {
            return;
        }
        else if (this.state.locale?.code === localeOrCode) {
            return;
        }
        if (typeof localeOrCode === "string") {
            const loader = this.props.dateFnsLocaleLoader ?? loadDateFnsLocale;
            const locale = await loader(localeOrCode);
            if (this.isComponentMounted) {
                this.setState({ locale });
            }
        }
        else {
            this.setState({ locale: localeOrCode });
        }
    }
}
//# sourceMappingURL=dateFnsLocalizedComponent.js.map