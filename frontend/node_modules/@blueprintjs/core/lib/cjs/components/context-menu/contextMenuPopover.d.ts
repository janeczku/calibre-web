import type { ContextMenuPopoverOptions, Offset } from "./contextMenuShared";
export interface ContextMenuPopoverProps extends ContextMenuPopoverOptions {
    isOpen: boolean;
    isDarkTheme?: boolean;
    content: React.JSX.Element;
    onClose?: () => void;
    targetOffset: Offset | undefined;
}
/**
 * A floating popover which is positioned at a given target offset inside its parent element container.
 * Used to display context menus. Note that this behaves differently from other popover components like
 * Popover and Tooltip, which wrap their children with interaction handlers -- if you're looking for the whole
 * interaction package, use ContextMenu instead.
 *
 * @see https://blueprintjs.com/docs/#core/components/context-menu-popover
 */
export declare const ContextMenuPopover: import("react").NamedExoticComponent<ContextMenuPopoverProps>;
