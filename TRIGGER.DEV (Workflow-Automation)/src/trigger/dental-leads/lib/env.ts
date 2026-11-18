/** Read a required env var, or throw a clear error. Never logs the value. */
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value || !value.trim()) {
    throw new Error(
      `Missing environment variable ${name}. Add it to .env and to the Trigger.dev dashboard (Project -> Environment Variables) for staging and prod.`
    );
  }
  return value.trim();
}

export function optionalEnv(name: string): string | undefined {
  const value = process.env[name];
  return value && value.trim() ? value.trim() : undefined;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
