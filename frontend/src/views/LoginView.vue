<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useToast } from "../composables/useToast.js";
import { signIn } from "../composables/useAuthSession.js";

const REMEMBERED_USERNAME_KEY = "tzlb.rememberedUsername";

const router = useRouter();
const route = useRoute();
const { error, info, success } = useToast();

const username = ref("");
const password = ref("");
const rememberMe = ref(false);
const submitting = ref(false);

const targetPath = computed(() => {
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "";
  if (redirect.startsWith("/") && redirect !== "/login") {
    return redirect;
  }
  return "/map";
});

function readRememberedUsername() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(REMEMBERED_USERNAME_KEY) || "";
}

function persistRememberedUsername(value) {
  if (typeof window === "undefined") {
    return;
  }

  if (rememberMe.value) {
    window.localStorage.setItem(REMEMBERED_USERNAME_KEY, value);
    return;
  }

  window.localStorage.removeItem(REMEMBERED_USERNAME_KEY);
}

function handleForgotPassword() {
  info("请联系系统管理员协助重置密码。", "忘记密码");
}

function handleRequestAccess() {
  info("请联系林业调查局管理员申请账号开通。", "申请加入");
}

async function handleSubmit() {
  const normalizedUsername = username.value.trim();
  const normalizedPassword = password.value.trim();

  if (!normalizedUsername || !normalizedPassword) {
    error("请输入完整的用户名和密码后再继续。", "登录信息不完整");
    return;
  }

  submitting.value = true;

  try {
    await signIn({
      username: normalizedUsername,
      password: normalizedPassword,
      remember_me: rememberMe.value,
    });
    persistRememberedUsername(normalizedUsername);
    success(`欢迎回来，${normalizedUsername}。`, "登录成功");
    await router.push(targetPath.value);
  } catch (submitError) {
    error(`${submitError.message || submitError}`, "登录失败");
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  const rememberedUsername = readRememberedUsername();
  if (!rememberedUsername) {
    return;
  }

  username.value = rememberedUsername;
  rememberMe.value = true;
});
</script>

<template>
  <section class="login-page" data-testid="login-page">
    <!-- Warm background with subtle pattern -->
    <div class="login-bg" aria-hidden="true">
      <div class="login-bg__gradient"></div>
      <div class="login-bg__pattern"></div>
    </div>

    <main class="login-content">
      <div class="login-card">
        <!-- Brand header -->
        <div class="login-brand">
          <div class="login-brand__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3v18M12 3l-4 4M12 3l4 4M8 7l-4 4M16 7l4 4M8 7v4M16 7v4M8 11l-4 4M16 11l4 4M8 11v4M16 11v4M8 15l-4 4M16 15l4 4"/>
            </svg>
          </div>
          <h1 class="login-brand__title">林业调查工作台</h1>
          <p class="login-brand__subtitle">Forest Survey Workbench</p>
        </div>

        <!-- Login form -->
        <form class="login-form" @submit.prevent="handleSubmit">
          <div class="login-field">
            <label for="login-username">用户名</label>
            <div class="login-input-wrapper">
              <span class="login-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="8" r="4"/>
                  <path d="M5 20c0-4 3.5-7 7-7s7 3 7 7"/>
                </svg>
              </span>
              <input
                id="login-username"
                v-model.trim="username"
                :disabled="submitting"
                autocomplete="username"
                name="username"
                placeholder="请输入用户名"
                type="text"
              />
            </div>
          </div>

          <div class="login-field">
            <label for="login-password">密码</label>
            <div class="login-input-wrapper">
              <span class="login-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="5" y="11" width="14" height="10" rx="2"/>
                  <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
                  <circle cx="12" cy="16" r="1"/>
                </svg>
              </span>
              <input
                id="login-password"
                v-model.trim="password"
                :disabled="submitting"
                autocomplete="current-password"
                name="password"
                placeholder="请输入密码"
                type="password"
              />
            </div>
          </div>

          <div class="login-options">
            <label class="login-checkbox" for="remember-me">
              <input
                id="remember-me"
                v-model="rememberMe"
                :disabled="submitting"
                type="checkbox"
              />
              <span>记住我</span>
            </label>

            <button
              type="button"
              class="login-link"
              :disabled="submitting"
              @click="handleForgotPassword"
            >
              忘记密码？
            </button>
          </div>

          <button type="submit" class="login-submit" :disabled="submitting">
            <span>{{ submitting ? "正在登录" : "立即登录" }}</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        </form>

        <!-- Footer -->
        <div class="login-card__foot">
          <p>
            还没有账号？
            <button
              type="button"
              class="login-link login-link--accent"
              :disabled="submitting"
              @click="handleRequestAccess"
            >
              申请加入
            </button>
          </p>
        </div>
      </div>
    </main>
  </section>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-body);
  background: var(--color-bg);
}

/* ── Background ── */
.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.login-bg__gradient {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse at 20% 20%, rgba(242, 217, 220, 0.4), transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(217, 242, 216, 0.3), transparent 50%),
    var(--color-bg);
}

.login-bg__pattern {
  position: absolute;
  inset: 0;
  opacity: 0.03;
  background-image: 
    radial-gradient(circle at 1px 1px, var(--color-ink) 1px, transparent 0);
  background-size: 32px 32px;
}

/* ── Content ── */
.login-content {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
}

/* ── Card ── */
.login-card {
  width: min(100%, 24rem);
  padding: var(--space-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-raised);
}

/* ── Brand ── */
.login-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: var(--space-8);
}

.login-brand__mark {
  width: 4rem;
  height: 4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  background: var(--color-primary);
  color: var(--color-ink-soft);
  margin-bottom: var(--space-5);
}

.login-brand__mark svg {
  width: 2rem;
  height: 2rem;
}

.login-brand__title {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-ink);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-display);
}

.login-brand__subtitle {
  margin-top: var(--space-2);
  color: var(--color-muted);
  font-size: var(--text-sm);
  font-weight: 500;
}

/* ── Form ── */
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.login-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.login-field label {
  color: var(--color-ink-soft);
  font-size: var(--text-sm);
  font-weight: 600;
}

.login-input-wrapper {
  position: relative;
}

.login-input-icon {
  position: absolute;
  left: var(--space-4);
  top: 50%;
  transform: translateY(-50%);
  width: 1.125rem;
  height: 1.125rem;
  color: var(--color-muted);
  pointer-events: none;
}

.login-input-icon svg {
  width: 100%;
  height: 100%;
}

.login-input-wrapper :deep(input) {
  padding-left: 2.75rem;
  min-height: 3rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-size: var(--text-base);
  transition: border-color var(--motion-fast) var(--ease-standard), box-shadow var(--motion-fast) var(--ease-standard);
}

.login-input-wrapper :deep(input:focus) {
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

/* ── Options row ── */
.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-sm);
}

.login-checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-ink-soft);
  cursor: pointer;
}

.login-checkbox :deep(input[type="checkbox"]) {
  width: 1rem;
  height: 1rem;
  min-height: 0;
  accent-color: var(--color-accent);
}

.login-link {
  min-height: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-accent);
  box-shadow: none;
  font-size: var(--text-sm);
  font-weight: 600;
}

.login-link:hover {
  transform: none;
  box-shadow: none;
  color: var(--color-ink);
}

/* ── Submit ── */
.login-submit {
  min-height: 3rem;
  margin-top: var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-accent-on);
  font-weight: 700;
  gap: var(--space-2);
  transition: all var(--motion-fast) var(--ease-standard);
}

.login-submit:hover {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--elev-raised);
}

.login-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.login-submit svg {
  width: 1rem;
  height: 1rem;
}

/* ── Footer ── */
.login-card__foot {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
  text-align: center;
  color: var(--color-ink-soft);
  font-size: var(--text-sm);
}

.login-link--accent {
  color: var(--color-accent);
  font-weight: 700;
}

/* ── Responsive ── */
@media (max-width: 640px) {
  .login-content {
    padding: var(--space-4);
  }

  .login-card {
    padding: var(--space-6);
    border-radius: var(--radius-md);
  }

  .login-brand__mark {
    width: 3.25rem;
    height: 3.25rem;
  }

  .login-options {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-3);
  }
}
</style>
