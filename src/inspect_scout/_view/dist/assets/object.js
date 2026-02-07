const printObject = (val, size = 50) => {
  const envelope = ["{", "}"];
  const ellipsis = "…";
  const separator = ", ";
  const kvSeparator = ": ";
  let remainingSize = size - (envelope[0]?.length || 0) - (envelope[1]?.length || 0);
  const entries = Object.entries(val);
  const headItems = [];
  const tailItems = [];
  let headIdx = 0;
  let tailIdx = entries.length - 1;
  while (headIdx <= tailIdx) {
    const headPair = `${entries[headIdx]?.[0]}${kvSeparator}${JSON.stringify(entries[headIdx]?.[1])}`;
    const tailPair = `${entries[tailIdx]?.[0]}${kvSeparator}${JSON.stringify(entries[tailIdx]?.[1])}`;
    if (headIdx === tailIdx) {
      if (headPair.length <= remainingSize) {
        headItems.push(headPair);
      } else {
        headItems.push(ellipsis);
      }
      break;
    }
    const bothSize = headPair.length + tailPair.length + separator.length;
    if (bothSize <= remainingSize) {
      headItems.push(headPair);
      tailItems.unshift(tailPair);
      remainingSize -= bothSize;
      headIdx++;
      tailIdx--;
    } else if (headPair.length + separator.length + ellipsis.length <= remainingSize) {
      headItems.push(headPair);
      headItems.push(ellipsis);
      break;
    } else {
      headItems.push(ellipsis);
      break;
    }
  }
  if (headItems.length === 0 && entries.length > 0) {
    const firstPair = `${entries[0]?.[0]}${kvSeparator}${JSON.stringify(entries[0]?.[1])}`;
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
export {
  printObject as p
};
//# sourceMappingURL=object.js.map
