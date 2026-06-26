import type { Locale } from "date-fns";
import { AbstractPureComponent } from "@blueprintjs/core";
import type { DateFnsLocaleProps } from "../common/dateFnsLocaleProps";
interface DateFnsLocaleState {
    locale?: Locale | undefined;
}
/**
 * Abstract component which accepts a date-fns locale prop and loads the corresponding `Locale` object as necessary.
 *
 * Currently used by DatePicker, DateRangePicker, and DateRangeInput, but we would ideally migrate to the
 * `useDateFnsLocale()` hook once those components are refactored into functional components.
 */
export declare abstract class DateFnsLocalizedComponent<P extends DateFnsLocaleProps, S extends DateFnsLocaleState> extends AbstractPureComponent<P, S> {
    private isComponentMounted;
    setState<K extends keyof S>(nextStateOrAction: ((prevState: S, prevProps: P) => Pick<S, K> | null) | Pick<S, K> | Partial<S> | null, callback?: () => void): void;
    componentDidMount(): Promise<void>;
    componentDidUpdate(prevProps: DateFnsLocaleProps): Promise<void>;
    componentWillUnmount(): void;
    private loadLocale;
}
export {};
