export const printArray = (arr: unknown[], size: number = 50): string => {
  // Create a truncated display of the array by trying to fit it into specific size
  const envelope = ["[", "]"];
  const ellipsis = "…";
  const separator = ", ";
  let remainingSize =
    size - envelope[0].length - envelope[1].length - separator.length;

  // Iterate from the outside in, building the list of items to display
  const headItems: string[] = [];
  const tailItems: string[] = [];

  // Walk through the array from both ends, adding items until we run out of space
  let headIdx = 0;
  let tailIdx = arr.length - 1;

  while (headIdx <= tailIdx) {
    const headStr = String(arr[headIdx]);
    const tailStr = String(arr[tailIdx]);

    // If we're at the same item (middle of odd-length array)
    if (headIdx === tailIdx) {
      if (headStr.length <= remainingSize) {
        headItems.push(headStr);
      } else {
        headItems.push(ellipsis);
      }
      break;
    }

    // Try to fit both head and tail items
    const bothSize = headStr.length + tailStr.length + separator.length;

    if (bothSize <= remainingSize) {
      headItems.push(headStr);
      tailItems.unshift(tailStr);
      remainingSize -= bothSize;
      headIdx++;
      tailIdx--;
    } else {
      // Can't fit both, add ellipsis
      headItems.push(ellipsis);
      break;
    }
  }

  // If the first item is too large, middle truncate it and place the separator in the middle
  if (headItems.length === 0 && arr.length > 0) {
    const firstStr = String(arr[0]);
    const truncateSize = remainingSize - ellipsis.length;
    if (truncateSize > 0) {
      headItems.push(firstStr.slice(0, truncateSize) + ellipsis);
      headItems.push(ellipsis);
    } else {
      headItems.push(ellipsis);
    }
  }

  const allItems = [...headItems, ...tailItems];
  return envelope[0] + allItems.join(separator) + envelope[1];
};
