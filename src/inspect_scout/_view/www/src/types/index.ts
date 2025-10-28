export interface Scan {
    complete: boolean;
    location: string;
    scanners: Record<string, Scanner>;
    summary: Record<string, ScannerResultSummary>;
    errors: Array<unknown>;
    spec: ScanSpec;
}
export interface Model {
    model: string;
    config: Record<string, unknown>;
    args: Record<string, unknown>;
}

export interface Transcript {
    type: string;
    count: number;
    data: string;
    fields: Array<Record<string, string>>
}

export interface ScanSpec {
    scan_file: string;
    scan_id: string;
    scan_name: string;
    scan_args: Record<string, unknown>;
    timestamp: string;

    model: Model;

    metadata: Record<string, unknown>;
    options: Record<string, unknown>;
    packages: Record<string, unknown>;
    revision: Record<string, unknown>;

    scanners: Record<string, Scanner>
    transcripts: Transcript;
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