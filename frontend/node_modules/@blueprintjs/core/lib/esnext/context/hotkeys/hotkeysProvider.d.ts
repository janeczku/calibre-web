import { type HotkeysDialogProps } from "../../components/hotkeys/hotkeysDialog";
import type { HotkeyConfig } from "../../hooks";
interface HotkeysContextState {
    /**
     * Whether the context instance is being used within a tree which has a <HotkeysProvider>.
     * It's technically ok if this is false, but not recommended, since that means any hotkeys
     * bound with that context instance will not show up in the hotkeys help dialog.
     */
    hasProvider: boolean;
    /** List of hotkeys accessible in the current scope, registered by currently mounted components, can be global or local. */
    hotkeys: HotkeyConfig[];
    /** Whether the global hotkeys dialog is open. */
    isDialogOpen: boolean;
}
type HotkeysAction = {
    type: "ADD_HOTKEYS" | "REMOVE_HOTKEYS";
    payload: HotkeyConfig[];
} | {
    type: "CLOSE_DIALOG" | "OPEN_DIALOG";
};
export type HotkeysContextInstance = readonly [HotkeysContextState, React.Dispatch<HotkeysAction>];
/**
 * A React context used to register and deregister hotkeys as components are mounted and unmounted in an application.
 * Users should take care to make sure that only _one_ of these is instantiated and used within an application, especially
 * if using global hotkeys.
 *
 * You will likely not be using this HotkeysContext directly, except in cases where you need to get a direct handle on an
 * existing context instance for advanced use cases involving nested HotkeysProviders.
 *
 * For more information, see the [HotkeysProvider documentation](https://blueprintjs.com/docs/#core/context/hotkeys-provider).
 */
export declare const HotkeysContext: import("react").Context<HotkeysContextInstance>;
export interface HotkeysProviderProps {
    /** Optional props to customize the rendered hotkeys dialog. */
    dialogProps?: Partial<Omit<HotkeysDialogProps, "hotkeys">>;
    /** If provided, this dialog render function will be used in place of the default implementation. */
    renderDialog?: (state: HotkeysContextState, contextActions: {
        handleDialogClose: () => void;
    }) => React.JSX.Element;
    /** If provided, we will use this context instance instead of generating our own. */
    value?: HotkeysContextInstance;
}
/**
 * Hotkeys context provider, necessary for the `useHotkeys` hook.
 *
 * @see https://blueprintjs.com/docs/#core/context/hotkeys-provider
 */
export declare const HotkeysProvider: ({ children, dialogProps, renderDialog, value, }: React.PropsWithChildren<HotkeysProviderProps>) => import("react/jsx-runtime").JSX.Element;
export {};
