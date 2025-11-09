/**
 * Determines whether a string is a base64 encoded string
 */
export const maybeBase64 = (str: string, minLen: number = 256): boolean => {
  const base64Pattern =
    /^(?:[A-Za-z0-9+/]{4})*?(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
  return str.length > minLen && base64Pattern.test(str);
};
