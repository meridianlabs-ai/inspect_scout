
import JSON5 from 'json5';

import { Scan } from '../types';
import { ScanApi, ScansInfo } from './api';
import { kMethodGetScan, kMethodGetScans } from './jsonrpc';

export const apiVscode = (
  rpcClient: (method: string, params?: any) => Promise<any>
): ScanApi => {
  return {
    getScan: async (scanLocation: string): Promise<Scan> => {
      const response = await rpcClient(kMethodGetScan, [scanLocation]) as string;
      if (response) {
        return JSON5.parse<Scan>(response);
      } else {
        throw new Error(`Invalid response for getScan for scan: ${scanLocation}`);
      }
      
    },
    getScans: async (): Promise<ScansInfo> => {
      console.log({rpcClient});
      const response = await rpcClient(kMethodGetScans, []) as string;
      console.log({response});
      if (response) {
        return JSON5.parse<ScansInfo>(response);
      } else {
        throw new Error('Invalid response for getScans');
      }
    },
  };
};
