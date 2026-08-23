export type DiagnosticSeverity = "info" | "warning" | "error";

export interface AdrKitDiagnostic {
  readonly code: string;
  readonly message: string;
  readonly severity: DiagnosticSeverity;
  readonly path?: string;
}

export class AdrKitError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = new.target.name;
    this.code = code;
  }
}

export class ContractValidationError extends AdrKitError {
  readonly diagnostics: readonly AdrKitDiagnostic[];
  constructor(message: string, diagnostics: readonly AdrKitDiagnostic[] = []) {
    super("contract.validation", message);
    this.diagnostics = Object.freeze([...diagnostics]);
  }
}

export class UnsupportedContractVersionError extends AdrKitError {
  readonly contractVersion: string;
  constructor(contractVersion: string) {
    super("contract.unsupported_version", `Unsupported ADR-Kit contract version: ${contractVersion}`);
    this.contractVersion = contractVersion;
  }
}

export class RepositoryError extends AdrKitError {
  constructor(code: string, message: string) { super(code, message); }
}

export class RepositoryPathError extends RepositoryError {
  constructor(message: string) { super("repository.path", message); }
}

export class AmbiguousAliasError extends RepositoryError {
  constructor(alias: string) { super("repository.ambiguous_alias", `Alias resolves to multiple entities: ${alias}`); }
}

export class LinkageError extends AdrKitError {
  constructor(code: string, message: string) { super(code, message); }
}
