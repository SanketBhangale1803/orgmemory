type RunbookLogoProps = {
  className?: string;
  compact?: boolean;
  inverted?: boolean;
};

export function RunbookMark({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`runbook-mark ${className}`.trim()}
      viewBox="0 0 80 80"
      role="img"
      aria-label="OrgMemory"
    >
      <path d="M12 45V31L25 18h34l13 13-20 20-9-9 14-14H29L12 45Z" />
      <path d="m8 68 20-20h22l21 20H55L44 58H33L23 68H8Z" />
    </svg>
  );
}

export default function RunbookLogo({ className = "", compact = false, inverted = false }: RunbookLogoProps) {
  return (
    <span className={`runbook-logo ${compact ? "compact" : ""} ${inverted ? "inverted" : ""} ${className}`.trim()}>
      <RunbookMark />
      {!compact && (
        <span className="runbook-wordmark">
          <strong>ORGMEMORY</strong>
          <small>Company Memory</small>
        </span>
      )}
    </span>
  );
}
