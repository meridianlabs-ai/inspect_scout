const ATTACHMENT_PREFIX = "attachment://";
const ATTACHMENT_PATTERN = /attachment:\/\/([a-f0-9]{32})/g;

const resolveString = (
  text: string,
  attachments: Record<string, string>
): string =>
  text.includes(ATTACHMENT_PREFIX)
    ? text.replace(
        ATTACHMENT_PATTERN,
        (match, id: string) => attachments[id] ?? match
      )
    : text;

const resolveDictAttachmentsImpl = (
  obj: unknown,
  resolveFunc: (s: string) => string
): unknown => {
  if (typeof obj === "string") return resolveFunc(obj);
  if (typeof obj === "object" && obj !== null) {
    if (Array.isArray(obj))
      return obj.map((item) => resolveDictAttachmentsImpl(item, resolveFunc));
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [
        k,
        resolveDictAttachmentsImpl(v, resolveFunc),
      ])
    );
  }
  return obj;
};

export const resolveDictAttachments = <T>(
  obj: T,
  attachments: Record<string, string>
): T =>
  resolveDictAttachmentsImpl(obj, (s) => resolveString(s, attachments)) as T;
