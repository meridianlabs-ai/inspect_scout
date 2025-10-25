export interface Scan {
    complete: boolean;
    location: string;
    scanners: Record<string, Scanner>;
    summary: Record<string, ScannerResultSummary>;
}

export interface Scanner {
    name: string;
    file: string;
    params: Record<string, unknown>;
}

export interface ScannerResultSummary{
    scans: number;
    results: number;
    errors: number;
    tokens: number;
}