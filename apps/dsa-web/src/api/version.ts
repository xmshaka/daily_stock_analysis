import apiClient from './index';
import { toCamelCase } from './utils';

export interface VersionInfo {
  version: string;
  commit: string | null;
  buildTime: string | null;
}

export const versionApi = {
  /**
   * 获取后端版本信息
   */
  getVersion: async (): Promise<VersionInfo> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/version');
    return toCamelCase<VersionInfo>(response.data);
  },
};
