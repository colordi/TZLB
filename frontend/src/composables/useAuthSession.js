import { computed, reactive } from "vue";

import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from "../api/auth.js";

const authState = reactive({
  initialized: false,
  loading: false,
  user: null,
});

let pendingSessionPromise = null;

function applyUser(user) {
  authState.user = user || null;
  authState.initialized = true;
  return authState.user;
}

async function loadCurrentUser() {
  authState.loading = true;
  try {
    const user = await fetchCurrentUser();
    return applyUser(user);
  } catch {
    return applyUser(null);
  } finally {
    authState.loading = false;
  }
}

export async function ensureSessionLoaded() {
  if (authState.initialized) {
    return authState.user;
  }

  if (!pendingSessionPromise) {
    pendingSessionPromise = loadCurrentUser().finally(() => {
      pendingSessionPromise = null;
    });
  }

  return pendingSessionPromise;
}

export function clearSession() {
  authState.user = null;
  authState.initialized = true;
}

export async function signIn(credentials) {
  const payload = await loginRequest(credentials);
  applyUser(payload.user || null);
  return authState.user;
}

export async function signOut() {
  try {
    await logoutRequest();
  } finally {
    clearSession();
  }
}

export function resetAuthSessionState() {
  authState.initialized = false;
  authState.loading = false;
  authState.user = null;
  pendingSessionPromise = null;
}

export function useAuthSession() {
  return {
    user: computed(() => authState.user),
    isAuthenticated: computed(() => Boolean(authState.user)),
    isInitializing: computed(() => authState.loading),
    ensureSessionLoaded,
    signIn,
    signOut,
    clearSession,
  };
}
