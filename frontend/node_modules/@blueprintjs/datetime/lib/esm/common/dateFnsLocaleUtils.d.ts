import type { Locale } from "date-fns";
import type { DateFnsLocaleLoader } from "./dateFnsLocaleProps";
/**
 * Lazy-loads a date-fns locale for use in a datetime class component.
 */
export declare function loadDateFnsLocale(localeCode: string): Promise<Locale | undefined>;
/**
 * Lazy-loads a date-fns locale for use in a datetime function component.
 */
export declare function useDateFnsLocale(localeOrCode: Locale | string | undefined, dateFnsLocaleLoader?: DateFnsLocaleLoader): globalThis.Locale | undefined;
