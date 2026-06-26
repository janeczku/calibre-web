import { type Props } from "../../common";
export interface MenuDividerProps extends Props {
    /** This component does not support children. */
    children?: never;
    /** Optional header title. */
    title?: React.ReactNode;
    /** Optional `id` prop for the header title. */
    titleId?: string;
}
/**
 * Menu divider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu.menu-divider
 */
export declare const MenuDivider: React.FC<MenuDividerProps>;
