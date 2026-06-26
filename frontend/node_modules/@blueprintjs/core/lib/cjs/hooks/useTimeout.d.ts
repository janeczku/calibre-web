/**
 * React hook wrapper for setTimeout(), adapted from usehooks-ts.
 * The provided callback is invoked after the specified delay in milliseconds.
 * If the delay is null or the component is unmounted, any pending timeout is cleared.
 *
 * @see https://usehooks-ts.com/react-hook/use-timeout
 */
export declare function useTimeout(callback: () => void, delay: number | null): void;
