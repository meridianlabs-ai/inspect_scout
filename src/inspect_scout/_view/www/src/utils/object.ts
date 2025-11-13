export const printObject = (val: object, size: number = 50): string => {
  const envelope = ["{", "}"];
  const ellipsis = "…";
  const separator = ", ";
  const kvSeparator = ": ";

  let remainingSize = size - envelope[0].length - envelope[1].length;

  const entries = Object.entries(val);
  const headItems: string[] = [];
  const tailItems: string[] = [];

  let headIdx = 0;
  let tailIdx = entries.length - 1;

  while (headIdx <= tailIdx) {
    const headPair = `${entries[headIdx][0]}${kvSeparator}${String(entries[headIdx][1])}`;
    const tailPair = `${entries[tailIdx][0]}${kvSeparator}${String(entries[tailIdx][1])}`;

    // If we're at the same entry (middle of odd-length object)
    if (headIdx === tailIdx) {
      if (headPair.length <= remainingSize) {
        headItems.push(headPair);
      } else {
        headItems.push(ellipsis);
      }
      break;
    }

    // Try to fit both head and tail entries (with separator between them)
    const bothSize = headPair.length + tailPair.length + separator.length;

    if (bothSize <= remainingSize) {
      headItems.push(headPair);
      tailItems.unshift(tailPair);
      remainingSize -= bothSize;
      headIdx++;
      tailIdx--;
    } else if (
      headPair.length + separator.length + ellipsis.length <=
      remainingSize
    ) {
      // Can't fit both, but can fit head item plus ellipsis
      headItems.push(headPair);
      headItems.push(ellipsis);
      break;
    } else {
      // Can't even fit head item
      headItems.push(ellipsis);
      break;
    }
  }

  // If the first entry is too large, middle truncate it
  if (headItems.length === 0 && entries.length > 0) {
    const firstPair = `${entries[0][0]}${kvSeparator}${String(entries[0][1])}`;
    const truncateSize = remainingSize - ellipsis.length - separator.length;
    if (truncateSize > 0) {
      headItems.push(firstPair.slice(0, truncateSize) + ellipsis);
      headItems.push(ellipsis);
    } else {
      headItems.push(ellipsis);
    }
  }

  const allItems = [...headItems, ...tailItems];
  return envelope[0] + allItems.join(separator) + envelope[1];
};
