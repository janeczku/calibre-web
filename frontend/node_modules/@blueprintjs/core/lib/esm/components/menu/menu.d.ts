import { type Props } from "../../common/props";
import type { Size } from "../../common/size";
export interface MenuProps extends Props, React.HTMLAttributes<HTMLUListElement> {
    /** Menu items. */
    children?: React.ReactNode;
    /**
     * Whether the menu items in this menu should use a large appearance.
     *
     * @deprecated use `size="large"` instead.
     * @default false
     */
    large?: boolean;
    /**
     * Whether the menu items in this menu should use a small appearance.
     *
     * @deprecated use `size="small"` instead.
     * @default false
     */
    small?: boolean;
    /**
     * The size of the items in this menu.
     *
     * @default "medium"
     */
    size?: Size;
    /** Ref handler that receives the HTML `<ul>` element backing this component. */
    ulRef?: React.Ref<HTMLUListElement>;
}
/**
 * Menu component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu
 */
export declare const Menu: React.FC<MenuProps>;
