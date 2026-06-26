import { Alignment } from "../../common";
import { type HTMLDivProps, type Props } from "../../common/props";
export interface NavbarGroupProps extends Props, HTMLDivProps {
    /**
     * The side of the navbar on which the group should appear.
     * The `Alignment` enum provides constants for these values.
     *
     * @default Alignment.START
     */
    align?: Alignment;
    children?: React.ReactNode;
}
export declare const NavbarGroup: React.FC<NavbarGroupProps>;
