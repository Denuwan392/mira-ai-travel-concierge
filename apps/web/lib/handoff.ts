let pending: string | undefined;

export function queuePrompt(prompt: string) {
  pending = prompt;
}

export function takePrompt() {
  const value = pending;
  pending = undefined;
  return value;
}
