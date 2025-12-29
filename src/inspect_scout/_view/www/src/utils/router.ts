import { useParams } from "react-router-dom";

export function useRequiredParams<T extends string>(
  ...keys: T[]
): Record<T, string> {
  const params = useParams();
  const result = {} as Record<T, string>;

  for (const key of keys) {
    const value = params[key];
    if (!value) {
      throw new Error(`Missing required route param: ${key}`);
    }
    result[key] = value;
  }

  return result;
}
