import { r as reactExports, q as loading } from "./index.js";
function useMapAsyncData(input, transform, errorTransform) {
  return reactExports.useMemo(() => {
    const isArray = Array.isArray(input);
    const mapped = (isArray ? input : [input]).map(
      (item) => {
        if (item.error) {
          const error = item.error;
          return { loading: false, error };
        }
        if (item.loading) return loading;
        try {
          return { loading: false, data: transform(item.data) };
        } catch (error) {
          if (!(error instanceof Error))
            throw Error(
              `useMapAsyncData only supports catching Error's: ${JSON.stringify(error)}`
            );
          return { loading: false, error };
        }
      }
    );
    if (!isArray) {
      const [onlyItem] = mapped;
      if (!onlyItem) throw Error("useMapAsyncData: Array must have one item.");
      return onlyItem;
    }
    return mapped;
  }, [input, transform, errorTransform]);
}
export {
  useMapAsyncData as u
};
//# sourceMappingURL=useMapAsyncData.js.map
