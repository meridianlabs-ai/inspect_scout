import { describe, expect, it } from "vitest";

import { toRelativePath } from "./path";

describe("toRelativePath", () => {
  it.each<[string | undefined, string | undefined, string, string]>([
    // [absolutePath, basePath, expected, description]
    ["/a/b/c/file.txt", "/a/b/", "c/file.txt", "basic extraction"],
    [
      "/a/b/c/file.txt",
      "/a/b",
      "c/file.txt",
      "basePath without trailing slash",
    ],
    [
      "file:///a/b/c/file.txt",
      "/a/b/",
      "c/file.txt",
      "file:// in absolutePath",
    ],
    ["/a/b/c/file.txt", "file:///a/b/", "c/file.txt", "file:// in basePath"],
    ["/x/y/z/file.txt", "/a/b/", "/x/y/z/file.txt", "path not under basePath"],
    ["", "/a/b/", "", "empty absolutePath"],
    ["/a/b/c", "", "/a/b/c", "empty basePath"],
    ["", "", "", "both empty"],
    [undefined, "/a/b/", "", "undefined absolutePath"],
    ["/a/b/c", undefined, "/a/b/c", "undefined basePath"],
    [undefined, undefined, "", "both undefined"],
  ])("%s + %s → %s (%s)", (absolutePath, basePath, expected) => {
    expect(toRelativePath(absolutePath, basePath)).toBe(expected);
  });
});
