import { type ContextMenuPopoverProps } from "./contextMenuPopover";
/**
 * Options for specifying how an imperatively created context menu should be rendered to the DOM.
 */
export interface ShowContextMenuOptions {
    /**
     * A new DOM element will be created and appended to this container.
     *
     * @default document.body
     */
    container?: HTMLElement;
    /**
     * A function render the React component onto a newly created DOM element. This should return a function which
     * unmounts the rendered element from the DOM.
     *
     * By default this creates a react DOM client root, renders the element into that node and returns a function
     * which unmounts the root.
     */
    render?: ShowContextMenuDOMRenderer;
}
type ShowContextMenuDOMRenderer = (element: React.ReactElement<ContextMenuPopoverProps>, container: Element | DocumentFragment) => ShowContextMenuDOMUnmounter;
type ShowContextMenuDOMUnmounter = () => void;
/**
 * Show a context menu at a particular offset from the top-left corner of the document.
 * The menu will appear below-right of this point and will flip to below-left if there is not enough
 * room onscreen. Additional props like `onClose`, `isDarkTheme`, etc. can be forwarded to the `<ContextMenuPopover>`.
 *
 * Context menus created with this API will automatically close when a user clicks outside the popover.
 * You may force them to close by using `hideContextMenu()`.
 *
 * Note that this API relies on global state in the @blueprintjs/core package, and should be used with caution,
 * especially if your build system allows multiple copies of Blueprint libraries to be bundled into an application at
 * once.
 *
 * Alternative APIs to consider which do not have the limitations of global state:
 *  - `<ContextMenu>`
 *  - `<ContextMenuPopover>`
 *
 * @see https://blueprintjs.com/docs/#core/components/context-menu-popover.imperative-api
 */
export declare function showContextMenu(props: Omit<ContextMenuPopoverProps, "isOpen">, options?: ShowContextMenuOptions): void;
/**
 * Hide a context menu that was created using `showContextMenu()`.
 *
 * Note that this API relies on global state in the @blueprintjs/core package, and should be used with caution.
 *
 * @see https://blueprintjs.com/docs/#core/components/context-menu-popover.imperative-api
 */
export declare function hideContextMenu(): void;
export {};
