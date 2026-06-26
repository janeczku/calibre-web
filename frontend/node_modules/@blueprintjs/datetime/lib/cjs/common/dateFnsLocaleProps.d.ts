import type { Locale } from "date-fns";
/**
 * @param localeCode - ISO 639-1 + optional country code
 * @returns date-fns `Locale` object
 */
export type DateFnsLocaleLoader = (localeCode: string) => Promise<Locale | undefined>;
export interface DateFnsLocaleProps {
    /**
     * Optional custom loader function for the date-fns `Locale` which will be used to localize the date picker.
     * This is useful in test environments or in build systems where you wish to customize module loading behavior.
     * If not provided, a default loader will be used which uses dynamic imports to load `date-fns/locale/${localeCode}`
     * modules.
     */
    dateFnsLocaleLoader?: DateFnsLocaleLoader;
    /**
     * date-fns `Locale` object or locale code string ((ISO 639-1 + optional country code) which will be used
     * to localize the date picker.
     *
     * If you provide a locale code string and receive a loading error, please make sure it is included in the list of
     * date-fns' [supported locales](https://github.com/date-fns/date-fns/tree/main/src/locale).
     * See date-fns [Locale](https://date-fns.org/v2.28.0/docs/Locale).
     *
     * @default "en-US"
     */
    locale?: Locale | string;
}
export declare function getLocaleCodeFromProps(localeOrCode: DateFnsLocaleProps["locale"]): string | undefined;
