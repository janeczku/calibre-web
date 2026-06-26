import { type ControlCardProps } from "./controlCard";
export type SwitchCardProps = Omit<ControlCardProps, "controlKind">;
/**
 * Switch Card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/control-card.switch-card
 */
export declare const SwitchCard: React.FC<SwitchCardProps>;
