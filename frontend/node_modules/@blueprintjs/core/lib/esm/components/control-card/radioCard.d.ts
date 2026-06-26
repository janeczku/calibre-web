import { type ControlCardProps } from "./controlCard";
export type RadioCardProps = Omit<ControlCardProps, "controlKind">;
/**
 * Radio Card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/control-card.radio-card
 */
export declare const RadioCard: React.FC<RadioCardProps>;
