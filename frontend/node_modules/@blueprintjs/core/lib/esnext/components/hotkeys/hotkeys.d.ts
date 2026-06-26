import { AbstractPureComponent, type Props } from "../../common";
export interface HotkeysProps extends Props {
    /**
     * In order to make local hotkeys work on elements that are not normally
     * focusable, such as `<div>`s or `<span>`s, we add a `tabIndex` attribute
     * to the hotkey target, which makes it focusable. By default, we use `0`,
     * but you can override this value to change the tab navigation behavior
     * of the component. You may even set this value to `null`, which will omit
     * the `tabIndex` from the component decorated by `HotkeysTarget`.
     */
    tabIndex?: number;
    /**
     * An array of `Hotkey` components that define the hotkeys to be used.
     */
    children?: React.ReactNode;
}
/**
 * Hotkeys component used to display a list of hotkeys in the HotkeysDialog.
 * Should not be used by consumers directly.
 */
export declare class Hotkeys extends AbstractPureComponent<HotkeysProps> {
    static displayName: string;
    static defaultProps: {
        tabIndex: number;
    };
    render(): import("react/jsx-runtime").JSX.Element | null;
    protected validateProps(props: HotkeysProps & {
        children: React.ReactNode;
    }): void;
}
