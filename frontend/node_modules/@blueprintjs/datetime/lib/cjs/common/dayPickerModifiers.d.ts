import type { DayModifiers } from "react-day-picker";
export declare const DISABLED_MODIFIER = "disabled";
export declare const HOVERED_RANGE_MODIFIER = "hovered-range";
export declare const OUTSIDE_MODIFIER = "outside";
export declare const SELECTED_MODIFIER = "selected";
export declare const SELECTED_RANGE_MODIFIER = "selected-range";
export declare const DISALLOWED_MODIFIERS: string[];
export declare function combineModifiers(baseModifiers: DayModifiers, userModifiers: DayModifiers | undefined): DayModifiers;
