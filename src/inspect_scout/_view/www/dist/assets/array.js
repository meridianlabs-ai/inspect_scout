const printArray = (arr, size = 50) => {
  const envelope = ["[", "]"];
  const ellipsis = "…";
  const separator = ", ";
  let remainingSize = size - (envelope[0]?.length || 0) - (envelope[1]?.length || 0) - separator.length;
  const headItems = [];
  const tailItems = [];
  let headIdx = 0;
  let tailIdx = arr.length - 1;
  while (headIdx <= tailIdx) {
    const headStr = String(arr[headIdx]);
    const tailStr = String(arr[tailIdx]);
    if (headIdx === tailIdx) {
      if (headStr.length <= remainingSize) {
        headItems.push(headStr);
      } else {
        headItems.push(ellipsis);
      }
      break;
    }
    const bothSize = headStr.length + tailStr.length + separator.length;
    if (bothSize <= remainingSize) {
      headItems.push(headStr);
      tailItems.unshift(tailStr);
      remainingSize -= bothSize;
      headIdx++;
      tailIdx--;
    } else {
      headItems.push(ellipsis);
      break;
    }
  }
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
export {
  printArray as p
};
//# sourceMappingURL=array.js.map
