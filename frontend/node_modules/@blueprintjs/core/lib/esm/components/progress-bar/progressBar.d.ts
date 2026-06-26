import { type HTMLDivProps, type IntentProps, type Props } from "../../common/props";
export interface ProgressBarProps extends Props, IntentProps, HTMLDivProps {
    /**
     * Whether the background should animate.
     *
     * @default true
     */
    animate?: boolean;
    /**
     * Whether the background should be striped.
     *
     * @default true
     */
    stripes?: boolean;
    /**
     * A value between 0 and 1 (inclusive) representing how far along the operation is.
     * Values below 0 or above 1 will be interpreted as 0 or 1, respectively.
     * Omitting this prop will result in an "indeterminate" progress meter that fills the entire bar.
     */
    value?: number;
}
/**
 * Progress bar component.
 *
 * @see https://blueprintjs.com/docs/#core/components/progress-bar
 */
export declare const ProgressBar: React.FC<ProgressBarProps>;
