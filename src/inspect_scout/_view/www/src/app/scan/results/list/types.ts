export interface ScannerRow {
  inputType: "transcript" | "message" | "messages" | "event" | "events";
  id: string;
  input: unknown;
  value: string;
  valueType: string;
  explanation: string;
  answer: string;
}
