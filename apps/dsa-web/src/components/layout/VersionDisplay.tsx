import type React from 'react';
import { useEffect, useState } from 'react';
import { versionApi } from '../../api/version';

interface VersionInfo {
  version: string;
  commit: string | null;
  buildTime: string | null;
}

export const VersionDisplay: React.FC = () => {
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    versionApi
      .getVersion()
      .then((v) => {
        if (mounted) setVersion(v);
      })
      .catch(() => {
        if (mounted) setError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (error || !version) {
    return (
      <div className="text-[10px] text-muted-foreground/40 px-2 py-1">
        DSA
      </div>
    );
  }

  return (
    <div
      className="text-[10px] text-muted-foreground/50 px-2 py-1 select-none"
      title={`Build: ${version.buildTime ?? 'unknown'}`}
    >
      v{version.version}
      {version.commit ? ` · ${version.commit}` : ''}
    </div>
  );
};
