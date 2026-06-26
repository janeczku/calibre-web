import type { IconName } from "@blueprintjs/icons";
import type { Intent } from "./intent";
export declare const DISPLAYNAME_PREFIX = "Blueprint6";
/**
 * Alias for all valid HTML props for `<div>` element.
 * Does not include React's `ref` or `key`.
 */
export type HTMLDivProps = React.HTMLAttributes<HTMLDivElement>;
/**
 * Alias for all valid HTML props for `<input>` element.
 * Does not include React's `ref` or `key`.
 */
export type HTMLInputProps = React.InputHTMLAttributes<HTMLInputElement>;
/**
 * Alias for all valid HTML props for `<textarea>` element.
 * Does not include React's `ref` or `key`.
 */
export type HTMLTextAreaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;
/**
 * Alias for a `React.JSX.Element` or a value that renders nothing.
 *
 * In React, `boolean`, `null`, and `undefined` do not produce any output.
 */
export type MaybeElement = React.JSX.Element | false | null | undefined;
/**
 * A shared base interface for all Blueprint component props.
 */
export interface Props {
    /** A space-delimited list of class names to pass along to a child element. */
    className?: string;
}
export interface IntentProps {
    /** Visual intent color to apply to element. */
    intent?: Intent;
}
/**
 * Interface for a clickable action, such as a button or menu item.
 * These props can be spready directly to a `<Button>` or `<MenuItem>` element.
 *
 * @template T type of the DOM element rendered by this component
 */
export interface ActionProps<T extends HTMLElement = HTMLElement> extends IntentProps, Props {
    /** Whether this action is non-interactive. */
    disabled?: boolean;
    /** Name of a Blueprint UI icon (or an icon element) to render before the text. */
    icon?: IconName | MaybeElement;
    /** Click event handler. */
    onClick?: (event: React.MouseEvent<T>) => void;
    /** Focus event handler. */
    onFocus?: (event: React.FocusEvent<T>) => void;
    /** Action text. Can be any single React renderable. */
    text?: React.ReactNode;
}
/** Interface for a link, with support for customizing target window. */
export interface LinkProps {
    /** Link URL. */
    href?: string;
    /** Link target attribute. Use `"_blank"` to open in a new window. */
    target?: React.HTMLAttributeAnchorTarget;
}
/**
 * Interface for a controlled or uncontrolled component, typically a form control.
 */
export interface ControlledValueProps<T, E extends HTMLElement = HTMLElement> {
    /**
     * Initial value for uncontrolled usage. Mutually exclusive with `value` prop.
     */
    defaultValue?: T;
    /**
     * Controlled value. Mutually exclusive with `defaultValue` prop.
     */
    value?: T;
    /**
     * Callback invoked when the component value changes, typically via user interaction, in both controlled and
     * uncontrolled mode.
     *
     * Using this prop instead of `onChange` can help avoid common bugs in React 16 related to Event Pooling
     * where developers forget to save the text value from a change event or call `event.persist()`.
     *
     * @see https://legacy.reactjs.org/docs/legacy-event-pooling.html
     */
    onValueChange?: (value: T, targetElement: E | null) => void;
}
export interface OptionProps<T extends string | number = string | number> extends Props {
    /** Whether this option is non-interactive. */
    disabled?: boolean;
    /** Label text for this option. If omitted, `value` is used as the label. */
    label?: string;
    /** Value of this option. */
    value: T;
}
/**
 * Typically applied to HTMLElements to filter out disallowed props. When applied to a Component,
 * can filter props from being passed down to the children. Can also filter by a combined list of
 * supplied prop keys and the denylist (only appropriate for HTMLElements).
 *
 * @param props The original props object to filter down.
 * @param {string[]} invalidProps If supplied, overwrites the default denylist.
 * @param {boolean} shouldMerge If true, will merge supplied invalidProps and denylist together.
 */
export declare function removeNonHTMLProps(props: {
    [key: string]: any;
}, invalidProps?: string[], shouldMerge?: boolean): {
    [key: string]: any;
};
