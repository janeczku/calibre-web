import { type HTMLDivProps, type Props } from "../../common/props";
import { NavbarDivider } from "./navbarDivider";
import { NavbarGroup } from "./navbarGroup";
import { NavbarHeading } from "./navbarHeading";
export interface NavbarProps extends Props, HTMLDivProps {
    children?: React.ReactNode;
    /**
     * Whether this navbar should be fixed to the top of the viewport (using CSS `position: fixed`).
     */
    fixedToTop?: boolean;
}
/**
 * Navbar component.
 *
 * @see https://blueprintjs.com/docs/#core/components/navbar
 */
export declare const Navbar: React.FC<NavbarProps> & {
    Divider: typeof NavbarDivider;
    Group: typeof NavbarGroup;
    Heading: typeof NavbarHeading;
};
