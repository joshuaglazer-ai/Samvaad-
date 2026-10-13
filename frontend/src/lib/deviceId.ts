/** A random id for this phone (no personal data). Lets a two-phone family session tell the devices apart. */
let memory: string | null = null;

function randomId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `d-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  }
}

export function getDeviceId(): string {
  try {
    const saved = localStorage.getItem("samvaad.device");
    if (saved) return saved;
    const id = randomId();
    localStorage.setItem("samvaad.device", id);
    return id;
  } catch {
    memory = memory ?? randomId(); // storage blocked: keep one id for this visit
    return memory;
  }
}
