# Frontend Architecture Notes

## Loading State Pattern

**Important**: Loading states are handled at the **panel level**, not within child components.

### How It Works

- `ResultPanel` checks if data is available before rendering `ResultBody`
- `ResultBody` expects its props to be fully resolved (non-optional)
- If data is loading or unavailable, the parent panel handles the UI (loading spinner, "No data" message, etc.)

### Example

```tsx
// CORRECT: Parent handles the undefined case
export const ResultPanel: FC<ResultPanelProps> = ({
  resultData,
  inputData,
}) => (
  <div>
    <ResultSidebar resultData={resultData} />
    {inputData ? (
      <ResultBody resultData={resultData} inputData={inputData} />
    ) : (
      <div>No Input Available</div>
    )}
  </div>
);

// ResultBody expects data to exist
export interface ResultBodyProps {
  resultData: ScanResultData; // Required, not optional
  inputData: ScanResultInputData; // Required, not optional
}
```

### Why This Pattern?

1. **Simpler child components** - Don't need to handle loading/error states internally
2. **Consistent UX** - Loading states handled uniformly at panel boundaries
3. **Easier testing** - Child components can assume valid data

### What NOT To Do

Don't add loading state props to child components:

```tsx
// AVOID: Adding loading props to children
interface ResultBodyProps {
  resultData?: ScanResultData;
  inputData?: ScanResultInputData;
  inputLoading?: boolean; // Don't do this
}
```

Instead, have the parent component not render the child until data is ready.
