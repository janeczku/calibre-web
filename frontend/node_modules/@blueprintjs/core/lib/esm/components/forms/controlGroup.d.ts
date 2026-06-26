import { type HTMLDivProps, type Props } from "../../common/props";
export interface ControlGroupProps extends Props, HTMLDivProps, React.RefAttributes<HTMLDivElement> {
    /** Group contents. */
    children?: React.ReactNode;
    /**
     * Whether the control group should take up the full width of its container.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * Whether the control group should appear with vertical styling.
     *
     * @default false
     */
    vertical?: boolean;
}
/**
 * Control group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/control-group
 */
export declare const ControlGroup: React.FC<ControlGroupProps>;
